"""
An asset cache stores a copy of slow-to-obtain website assets
on a fast file storage. Assets are stored based on a hash of their
path and mtime, so it's safe to update the source and have the asset cache
automatically cleared.

A classic use of an asset cache is to copy static files from a server with
a short expiry header to a server with an extremely long expiry header.
"""

import hashlib, os.path, glob
from abc import ABCMeta, abstractmethod
from contextlib import closing

from django.contrib.staticfiles.finders import find as find_static_path
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.conf import settings


def freeze_dict(params):
    """Returns an invariant version of the dictionary, suitable for hashing."""
    return tuple(sorted((params).iteritems()))


class Asset(object):

    """An asset that is available to the asset cache."""

    __metaclass__ = ABCMeta
    
    @abstractmethod
    def get_name(self):
        """
        Returns the name of this asset.
        
        It does not have to be globally unique.
        """
        raise NotImplementedError
    
    def get_path(self):
        """Returns the filesystem path of this asset."""
        raise NotImplementedError("This asset does not support absolute paths")
    
    def get_url(self):
        """Returns the frontend URL of this asset."""
        raise NotImplementedError("This asset does not have a URL")
    
    def get_mtime(self):
        """Returns the last modified time of this asset."""
        return os.path.getmtime(self.get_path())
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = {}
        # Add the path.
        try:
            params["path"] = self.get_path()
        except NotImplementedError:
            pass
        # Add the URL.
        try:
            params["url"] = self.get_url()
        except NotImplementedError:
            pass
        # All done!
        return params
    
    def _get_and_check_id_params(self):
        """Retrieves the id params, and checks that some exist."""
        params = self.get_id_params()
        if not params:
            raise NotImplementedError("This asset does not have a path or a url.")
        return params
    
    def get_id(self):
        """Returns a globally unique id for this asset."""
        return freeze_dict(self._get_and_check_id_params())
        
    def open(self):
        """Returns an open File for this asset."""
        return File(open(self.get_path()), "rb")
    
    def get_hash_params(self):
        """Returns the params which should be used to generate the hash."""
        params = self._get_and_check_id_params()
        params["mtime"] = self.get_mtime()
        return params
        
    def get_hash(self):
        """Returns the sha1 hash of this asset's contents."""
        return hashlib.sha1(
            u"&".join(
                u"{key}={value}".format(
                    key = key,
                    value = value,
                )
                for key, value in freeze_dict(self.get_hash_params())
            )
        ).hexdigest()
        
    def save(self, storage, name):
        """Saves this asset to the given storage."""
        with closing(self.open()) as handle:
            storage.save(name, handle)


class StaticAsset(Asset):

    """An asset that wraps a Django static file."""
    
    def __init__(self, name):
        """Initializes the static asset."""
        self._name = name
        
    def get_name(self):
        """Returns the name of this static asset."""
        return self._name
    
    @staticmethod
    def get_static_path(name):
        """Returns the full static path of the given name."""
        if settings.DEBUG:
            path = find_static_path(name)
            if path is None:
                path = os.path.join(settings.STATIC_ROOT, name)
        else:
            path = os.path.join(settings.STATIC_ROOT, name)
        return os.path.abspath(path)
        
    def get_path(self):
        """Returns the path of this static asset."""
        return StaticAsset.get_static_path(self._name)
        
    def get_url(self):
        """Returns the URL of this static asset."""
        return settings.STATIC_URL + self._name
        
    def get_mtime(self):
        """Returns the mtime of this static asset."""
        return os.path.getmtime(self.get_path())
        
        
class StaticAssetLoader(object):
    
    """A loader of static assets."""
    
    @staticmethod
    def load(type, assets):
        """Resolves the given asset name into a list of static assets."""
        # Adapt a single asset to a list.
        if isinstance(assets, (basestring, Asset)):
            assets = [assets]
        # Adapt asset names to assets.
        asset_objs = []
        for asset in assets:
            # Leave actual assets as they are.
            if isinstance(asset, Asset):
                asset_obs.append(asset)
            # Convert asset group ids into assets.
            asset_namespace = StaticAssetLoader._cache.get(asset)
            if asset_namespace is not None:
                asset_group = asset_namespace.get(type)
                if asset_group is not None:
                    asset_objs.extend(asset_group.assets)
            else:
                asset_objs.append(StaticAsset(asset))
        return asset_objs
    
    @staticmethod
    def get_namespaces():
        """Returns a list of all namespaces in the static asset loader."""
        return StaticAssetLoader._cache.keys()
    
    @staticmethod
    def initialize():
        """Loads all static assets."""
        cache = StaticAssetLoader._cache = {}
        # Load in all namespaces.
        for namespace, types in getattr(settings, "STATIC_ASSETS", {}).iteritems():
            type_cache = cache[namespace] = {}
            for type, config in types.iteritems():
                type_cache[type] = StaticAssetLoader(type, **config)
    
    def __init__(self, type, dirname="", files=(), pattern=None):
        """Initializes the static asset loader."""
        self.type = type
        self._dirname = dirname
        self._files = files
        # Create the loaded list of assets.
        asset_names = [
            os.path.join(dirname, file)
            for file in files
        ]
        # Scan the directory.
        root_path = StaticAsset.get_static_path(dirname)
        pattern = pattern or "*." + type
        for path in glob.iglob(os.path.join(root_path, pattern)):
            asset_name = os.path.join(dirname, os.path.relpath(path, root_path))
            if not asset_name in asset_names:
                asset_names.append(asset_name)
        # Create the assets.
        self.assets = [StaticAsset(asset_name) for asset_name in asset_names]
        
        
# Create all available asset loaders.
StaticAssetLoader.initialize()
        
        
class FileAsset(Asset):
    
    """An asset that wraps a file."""
    
    def __init__(self, file):
        """Initializes the file asset."""
        self._file = file
        
    def get_name(self):
        """Returns the name of this asset."""
        return self._file.name
        
    def get_path(self):
        """Returns the path of this asset."""
        try:
            return self._file.path
        except AttributeError:
            return os.path.abspath(self._file.name)
    
    def get_url(self):
        """Returns the URL of this asset."""
        try:
            return self._file.url
        except AttributeError:
            raise NotImplementedError("Underlying file does not have a URL.")
    
    def get_mtime(self):
        """Returns the mtime of this asset."""
        storage = getattr(self._file, "storage", None)
        if storage:
            return storage.modified_time(self._file.name)
        return super(FileAsset, self).get_mtime()
    
    def open(self):
        """Opens this asset."""
        self._file.open("rb")
        return self._file
        

class AdaptiveAsset(Asset):

    """An asset that adapts to wrap as many types as possible."""
    
    def __new__(cls, asset):
        """Creates the new asset."""
        if isinstance(asset, Asset):
            return asset
        if isinstance(asset, File):
            return FileAsset(asset)
        if isinstance(asset, basestring):
            return StaticAsset(asset)
        raise TypeError("{!r} is not a valid asset".format(asset))
        
        
class AssetCache(object):
    
    """A cache of assets."""
    
    def __init__(self, storage=default_storage, prefix="assets"):
        """Initializes the asset cache."""
        self._storage = storage
        self._prefix = prefix
        self._name_cache = {}
        
    def get_name(self, asset):
        """Returns the cached name of the given asset."""
        # Get the asset ID.
        asset_id = asset.get_id()
        name = self._name_cache.get(asset_id)
        if name is None:
            # Generate the name.
            asset_name = asset.get_name()
            asset_hash = asset.get_hash()
            _, asset_ext = os.path.splitext(asset_name)
            name = u"{prefix}/{folder}/{hash}{ext}".format(
                prefix = self._prefix,
                folder = asset_hash[:2],
                hash = asset_hash[2:],
                ext = asset_ext,
            )
            # Save the file to the asset cache.
            if not self._storage.exists(name):
                asset.save(self._storage, name)
            # Cache the name.
            self._name_cache[asset_id] = name
        return name
        
    def get_path(self, asset):
        """Returns the cached path of the given asset."""
        asset = AdaptiveAsset(asset)
        if settings.DEBUG:
            try:
                return asset.get_path()
            except NotImplementedError:
                pass
        return self._storage.path(self.get_name(asset))
        
    def get_url(self, asset):
        """Returns the cached url of the given asset."""
        asset = AdaptiveAsset(asset)
        if settings.DEBUG:
            try:
                return asset.get_url()
            except NotImplementedError:
                pass
        return self._storage.url(self.get_name(asset))
        
        
# The default asset cache.
default_asset_cache = AssetCache()