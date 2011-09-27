"""
An asset cache stores a copy of slow-to-obtain website assets
on a fast file storage. Assets are stored based on a hash of their
contents, so it's safe to update the source and have the asset cache
automatically cleared.

A classic use of an asset cache is to copy static files from a server with
a short expiry header to a server with an extremely long expiry header.
"""

import hashlib, os.path
from abc import ABCMeta, abstractmethod
from contextlib import closing

from django.contrib.staticfiles.finders import find as find_static_path
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils._os import safe_join


class Asset(object):

    """An asset that is available to the asset cache."""

    __metaclass__ = ABCMeta
    
    def get_id(self):
        """Returns a globally unique id for this asset."""
        return u"file://".format(
            path = self.get_path()
        )
    
    @abstractmethod
    def get_name(self):
        """
        Returns the name of this asset.
        
        It does not have to be globally unique.
        """
        raise NotImplementedError
    
    # Optional helper that makes all of the other methods easier.    
    def get_path(self):
        """Returns the filesystem path of this asset."""
        raise NotImplementedError("This asset does not support absolute paths")
        
    def open(self):
        """Returns an open File for this asset."""
        return File(open(self.get_path(), "rb"))
        
    def get_hash(self):
        """Returns the sha1 hash of this asset's contents."""
        hash = hashlib.sha1()
        with closing(self.open()) as handle:
            for chunk in handle.chunks():
                hash.update(chunk)
        return hash.hexdigest()
        
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
        
    def get_path(self):
        """Returns the path of this static asset."""
        if settings.DEBUG:
            return find_static_asset(self._name)
        return safe_join(settings.STATIC_ROOT, self._name)
        
        
class FieldFileAsset(Asset):
    
    """An asset that wraps an uploaded field file."""
    
    def __init__(self, field_file):
        """Initializes the field file asset."""
        self._field_file = field_file
        
    def get_name(self):
        """Returns the name of this asset."""
        return self._field_file.name
        
    def get_path(self):
        """Returns the path of this asset."""
        return self._field_file.path
        
    def open(self):
        """Opens this asset."""
        return self._field_file.open("rb")
        
        
class AssetCache(object):
    
    """A cache of assets."""
    
    def __init__(self, storage=default_storage, prefix="assets"):
        """Initializes the asset cache."""
        self._storage = storage
        self._prefix = prefix
        self._name_cache = {}
        
    def get_name(self, asset):
        """Returns the cached name of the given asset."""
        asset_id = asset.get_id()
        name = self._name_cache.get(asset_id)
        if name is None:
            # Generate the name.
            asset_name = asset.get_name()
            asset_hash = asset.get_hash()
            _, asset_ext = os.path.splitext(asset_name)
            name = u"{prefix}/{folder}/{hash}.{ext}".format(
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
        return self._storage.path(self.get_name(asset))
        
    def get_url(self, asset):
        """Returns the cached url of the given asset."""
        return self._storage.url(self.get_name(asset))
        
        
# The default asset cache.
default_asset_cache = AssetCache()