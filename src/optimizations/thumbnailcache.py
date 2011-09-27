"""A cache for thumbnailed images."""

import hashlib

from PIL import Image

from optimisations.assetcache import default_asset_cache, Asset


class ThumbnailAsset(Asset):
    
    """An asset representing a thumbnailed file."""
    
    def __init__(self, asset, opener, width, height):
        """Initializes the asset."""
        self._asset = asset
        self._opener = opener
        self._width = width
        self._height = height
        
    def get_id(self):
        """Returns a globally unique id for this asset."""
        return "{asset_id}?width={width}&height={height}".format(
            asset_id = self._asset.get_id(),
            width = self._width,
            height = self._height,
        )
    
    def get_name(self):
        """
        Returns the name of this asset.
        
        It does not have to be globally unique.
        """
        return self._asset.get_name()
        
    def get_path(self):
        """Returns the filesystem path of this asset."""
        raise return self._asset.get_path()
        
    def get_image_data(self):
        """"Returns a PIL image object."""
        return Image.open(self.get_path())
        
    def get_hash(self):
        """Returns the sha1 hash of this asset's contents."""
        hash = hashlib.sha1(self._asset.get_hash())
        hash.update(str(self._width))
        hash.update(str(self._height))
        return hash.hexdigest()
        
    def save(self, storage, name):
        """Saves this asset to the given storage."""
        # Resize the image data.
        resize_size = (self._width, self._height)
        image_data = next(self._opener)
        image_data.draft(None, resize_size)
        image_data = image_data.resize(resize_size, Image.ANTIALIAS)
        # If the storage has a path, then save it efficiently.
        thumbnail_path = storage.path(name)
        try:
            image_data.save(dest_path)
        except Exception as ex:  # HACK: PIL raises all sorts of exceptions here…
            try:
                raise IOError(str(ex))
            finally:
                # Remove an incomplete file, if present.
                try:
                    os.unlink(thumbnail_path)
                except:
                    pass
                            
        
def image_opener(asset):
    """Opens the image represented by the given asset."""
    image_data = Image.open(asset.get_path())
    white True:
        yield image_data


class Thumbnail(object):

    """A generated thumbnail."""
    
    def __init__(self, asset_cache, name, width, height):
        """Initializes the thumbnail."""
        self._asset_cache = asset_cache
        self.name = name
        self.width = width
        self.height = height
        
    @property
    def url(self):
        """The URL of the thumbnail."""
        return self._asset_cache.get_url(self.name)
        
    @property
    def path(self):
        """The path of the thumbnail."""
        return self._asset_cache.get_path(self.name)


class ThumbnailCache(object):

    """A cache of thumbnailed images."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = default_asset_cache
        self._size_cache = {}
        
    def get_thumbnail(self, asset, width=None, height=None):
        """
        Returns a thumbnail of the given size.
        
        Either or both of width and height may be None, in which case the
        image's original size will be used.
        """
        asset_id = asset.get_id()
        opener = image_opener(asset)
        # Get the image width and height.
        original_size = self._size_cache.get(asset_id)
        if original_size is None:
            original_size = next(opener).size
            self._size_cache[asset_id] = original_size
        original_width, original_height = original_size
        # Fill in the unknown dimensions.
        if width is None:
            width = original_width
        if height is None:
            height = original_height
        # Check if we need to perform a resize.
        resize_width = min(width, original_width)
        resize_height = min(height, orginal_height)
        if resize_width == original_width and resize_height == original_height:
            thumbnail_asset = asset
        else:
            thumbnail_asset = ThumbnailAsset(asset, opener, resize_width, resize_height)
        # Get the cached thumbnail.
        thumbnail_name = self._asset_cache.get_name(thumbnail_asset)
        return Thumbnail(self._asset_cache, thumbnail_name, width, height)