"""
An asset cache stores a copy of slow-to-obtain website assets
on a fast file storage. Assets are stored based on a hash of their
path and mtime, so it's safe to update the source and have the asset cache
automatically cleared.

A classic use of an asset cache is to copy static files from a server with
a short expiry header to a server with an extremely long expiry header.
"""

import hashlib, os.path, fnmatch, re
from abc import ABCMeta, abstractmethod
from contextlib import closing

from django.contrib.staticfiles.finders import find as find_static_path, get_finders
from django.contrib.staticfiles import storage
from django.core.files.base import File, ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.storage import get_storage_class

try:
    staticfiles_storage = storage.staticfiles_storage
except AttributeError:
    staticfiles_storage = get_storage_class(settings.STATICFILES_STORAGE)()  # Django 1.3 compatibility.
    
from optimizations.utils import resolve_namespaced_cache 


def freeze_dict(params):
    """Returns an invariant version of the dictionary, suitable for hashing."""
    return hashlib.sha1(u"&".join(
        u"{key}={value}".format(
            key = key,
            value = value,
        )
        for key, value in sorted((params).iteritems())
    )).hexdigest()


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
    
    def get_contents_hash(self):
        """Returns an md5 hash of the file's contents."""
        md5 = hashlib.md5()
        with closing(self.open()) as handle:
            for chunk in handle.chunks():
                md5.update(chunk)
        return md5.hexdigest()
    
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
    
    def get_cache_key(self):
        return u"optimizations:assetcache:{id}".format(
            id = self.get_id(),
        )
        
    def open(self):
        """Returns an open File for this asset."""
        return File(open(self.get_path()), "rb")
    
    def get_contents(self):
        """Returns the contents of this asset as a string."""
        with closing(self.open()) as handle:
            return handle.read()
    
    def get_hash_params(self):
        """Returns the params which should be used to generate the hash."""
        params = self._get_and_check_id_params()
        try:
            params["mtime"] = self.get_mtime()
        except NotImplementedError:
            # Not all backends support mtime, so fall back to md5 of the contents.
            params["md5"] = self.get_contents_hash()
        return params
        
    def get_hash(self):
        """Returns the sha1 hash of this asset's contents."""
        return freeze_dict(self.get_hash_params())
    
    def get_save_meta(self):
        """Returns the meta parameters to associate with the asset in the asset cache."""
        return {}
    
    def get_save_extension(self):
        """Returns the file extension to use when saving the asset."""
        _, asset_ext = os.path.splitext(self.get_name())
        return asset_ext.lower()
        
    def save(self, storage, name, meta):
        """Saves this asset to the given storage."""
        with closing(self.open()) as handle:
            storage.save(name, handle)


class StaticAsset(Asset):

    """An asset that wraps a Django static file."""
    
    @staticmethod
    def get_static_path(name):
        """Returns the full static path of the given name."""
        path = find_static_path(name)
        if path is None:
            path = staticfiles_storage.path(name)
        return os.path.abspath(path)
        
    @staticmethod
    def load(type, assets="default"):
        """Resolves the given asset name into a list of static assets."""
        namespaces = StaticAsset._load_namespaces()
        # Adapt a single asset to a list.
        if isinstance(assets, (basestring, Asset)):
            assets = [assets]
        # Adapt asset names to assets.
        asset_objs = []
        for asset in assets:
            # Leave actual assets as they are.
            if isinstance(asset, Asset):
                asset_objs.append(asset)
            else:
                # Convert asset group ids into assets.
                asset_namespace = namespaces.get(asset)
                if asset_namespace is not None:
                    asset_group = asset_namespace.get(type)
                    if asset_group is not None:
                        asset_objs.extend(asset_group)
                else:
                    asset_objs.append(StaticAsset(asset))
        return asset_objs
        
    @staticmethod
    def get_namespaces():
        """Returns a list of all namespaces in the static asset loader."""
        return StaticAsset._load_namespaces().keys()
    
    @staticmethod
    def get_urls(type, assets="default"):
        """Returns a list of cached urls for the given static assets."""
        return [
            default_asset_cache.get_url(asset)
            for asset in StaticAsset.load(type, assets)
        ]
    
    @staticmethod
    def _load_namespaces():
        namespaces = getattr(StaticAsset, "_namespace_cache", None)
        if namespaces is None:
            namespaces = {}
            # Find all the assets.
            all_asset_names = []
            for finder in get_finders():
                for path, storage in finder.list(()):
                    if getattr(storage, "prefix", None):
                        path = os.path.join(storage.prefix, path)
                    all_asset_names.append(path)
            all_asset_names.sort()
            # Loads the assets.
            def do_load(type, include=(), exclude=()):
                include = [re.compile(fnmatch.translate(pattern)) for pattern in include]
                exclude = [re.compile(fnmatch.translate(pattern)) for pattern in exclude]
                # Create the loaded list of assets.
                asset_names = []
                seen_asset_names = set()
                for pattern in include:
                    new_asset_names = [a for a in all_asset_names if pattern.match(a) and not a in seen_asset_names]
                    asset_names.extend(new_asset_names)
                    seen_asset_names.update(new_asset_names)
                for pattern in exclude:
                    asset_names = [a for a in asset_names if not pattern.match(a)]
                # Create the assets.
                return [StaticAsset(asset_name) for asset_name in asset_names]
            # Load in all namespaces.
            for namespace, types in getattr(settings, "STATIC_ASSETS", {}).iteritems():
                type_cache = namespaces[namespace] = {}
                for type, config in types.iteritems():
                    type_cache[type] = do_load(type, **config)
            # Save in the cache.
            StaticAsset._namespace_cache = namespaces
        return namespaces
    
    def __init__(self, name):
        """Initializes the static asset."""
        self._name = name
        
    def open(self):
        return staticfiles_storage.open(self._name)
        
    def get_name(self):
        """Returns the name of this static asset."""
        return self._name
        
    def get_path(self):
        """Returns the path of this static asset."""
        return StaticAsset.get_static_path(self._name)
        
    def get_url(self):
        """Returns the URL of this static asset."""
        return staticfiles_storage.url(self._name)
    
    def get_mtime(self):
        """Returns the last modified time of this asset."""
        if settings.DEBUG:
            return os.path.getmtime(self.get_path())
        return staticfiles_storage.modified_time(self.get_name())
        
        
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
        
        
class GroupedAsset(Asset):

    """An asset composed of multiple sub-assets."""
    
    join_str = ""
    
    def __init__(self, assets):
        """Initializes the grouped asset."""
        self._assets = assets
        
    def get_name(self):
        """Returns the name of this asset."""
        return self._assets[0].get_name()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = {}
        # Add in the assets.
        for n, asset in enumerate(self._assets):
            params.update(
                (u"{n}_{key}".format(
                    n = n,
                    key = key,
                ), value)
                for key, value
                in asset._get_and_check_id_params().iteritems()
            )
        # All done.
        return params
        
    def get_mtime(self):
        """Returns the modified time for this asset."""
        return max(asset.get_mtime() for asset in self._assets)
    
    def get_contents(self):
        """Loads all the js code."""
        return self.join_str.join(asset.get_contents() for asset in self._assets)
    
    def get_hash(self):
        """Returns the sha1 hash of this asset's contents."""
        return hashlib.sha1("".join(asset.get_hash() for asset in self._assets)).hexdigest()
    
    def open(self):
        """Returns an open file pointer."""
        return ContentFile(self.get_contents())
        

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
    
    def __init__(self, storage=default_storage, prefix="assets", cache_name="optimizations.assetcache"):
        """Initializes the asset cache."""
        self._storage = storage
        self._prefix = prefix
        self._cache = resolve_namespaced_cache(cache_name)
    
    def get_name_and_meta(self, asset):
        """Returns the name and associated parameters of an asset."""
        # Get the asset ID.
        asset_cache_key = asset.get_cache_key()
        name_and_meta = self._cache.get(asset_cache_key)
        if name_and_meta is None:
            # Generate the name.
            asset_hash = asset.get_hash()
            asset_ext = asset.get_save_extension()
            name = u"{prefix}/{folder}/{hash}{ext}".format(
                prefix = self._prefix,
                folder = asset_hash[:2],
                hash = asset_hash[2:],
                ext = asset_ext,
            )
            # Save the asset's params.
            meta = asset.get_save_meta()
            # Save the file to the asset cache.
            if not self._storage.exists(name):
                asset.save(self._storage, name, meta)
            # Cache the name.
            name_and_meta = (name, meta)
            self._cache.set(asset_cache_key, name_and_meta)
        return name_and_meta
        
    def get_name(self, asset):
        """Returns the cached name of the given asset."""
        return self.get_name_and_meta(asset)[0]
    
    def get_meta(self, asset):
        """Returns the cached meta of the given asset."""
        return self.get_name_and_meta(asset)[1]
        
    def get_path(self, asset, force_save=None):
        """Returns the cached path of the given asset."""
        if force_save is None:
            force_save = not settings.DEBUG
        asset = AdaptiveAsset(asset)
        if not force_save:
            try:
                return asset.get_path()
            except NotImplementedError:
                pass
        return self._storage.path(self.get_name(asset))
        
    def get_url(self, asset, force_save=None):
        """Returns the cached url of the given asset."""
        if force_save is None:
            force_save = not settings.DEBUG
        asset = AdaptiveAsset(asset)
        if not force_save:
            try:
                return asset.get_url()
            except NotImplementedError:
                pass
        return self._storage.url(self.get_name(asset))
        
        
# The default asset cache.
default_asset_cache = AssetCache()