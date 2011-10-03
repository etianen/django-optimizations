"""A cache for thumbnailed images."""

import hashlib, os.path, os

from PIL import Image

from optimizations.assetcache import default_asset_cache, Asset, AdaptiveAsset


class ThumbnailAsset(Asset):
    
    """An asset representing a thumbnailed file."""
    
    def __init__(self, asset, opener, width, height):
        """Initializes the asset."""
        self._asset = asset
        self._opener = opener
        self._width = width
        self._height = height
    
    def get_name(self):
        """Returns the name of this asset."""
        return self._asset.get_name()
        
    def get_path(self):
        """Returns the filesystem path of this asset."""
        return self._asset.get_path()
    
    # TODO: If the width and height are the same as the source image, don't add them.
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(ThumbnailAsset, self).get_id_params()
        params["width"] = self._width
        params["height"] = self._height
        
    def get_image_data(self):
        """"Returns a PIL image object."""
        return Image.open(self.get_path())
        
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
            os.makedirs(os.path.dirname(thumbnail_path))
        except OSError:
            pass
        try:
            image_data.save(thumbnail_path)
        except Exception as ex:  # HACK: PIL raises all sorts of Exceptions :(
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
    while True:
        yield image_data


class Thumbnail(object):

    """A generated thumbnail."""
    
    def __init__(self, asset_cache, asset, width, height):
        """Initializes the thumbnail."""
        self._asset_cache = asset_cache
        self._asset = asset
        self.name = asset.get_name()
        self.width = width
        self.height = height
        
    @property
    def url(self):
        """The URL of the thumbnail."""
        return self._asset_cache.get_url(self._asset)
        
    @property
    def path(self):
        """The path of the thumbnail."""
        return self._asset_cache.get_path(self._asset)


class ThumbnailCache(object):

    """A cache of thumbnailed images."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
        self._size_cache = {}
        
    def get_thumbnail(self, asset, width=None, height=None):
        """
        Returns a thumbnail of the given size.
        
        Either or both of width and height may be None, in which case the
        image's original size will be used.
        """
        # Adapt the asset.
        asset = AdaptiveAsset(asset)
        # Get the opener.
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
        resize_height = min(height, original_height)
        if resize_width == original_width and resize_height == original_height:
            thumbnail_asset = asset
        else:
            thumbnail_asset = ThumbnailAsset(asset, opener, resize_width, resize_height)
        # Get the cached thumbnail.
        return Thumbnail(self._asset_cache, thumbnail_asset, width, height)
        
        
# The default thumbnail cache.
default_thumbnail_cache = ThumbnailCache()