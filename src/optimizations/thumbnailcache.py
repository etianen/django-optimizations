"""A cache for thumbnailed images."""

import collections, sys, os.path
from cStringIO import StringIO

from PIL import Image

from django.core.files.base import File

from optimizations.assetcache import default_asset_cache, Asset, AdaptiveAsset
from optimizations.propertycache import cached_property


class Size(collections.namedtuple("SizeBase", ("width", "height",))):

    """Represents the size of an image."""
    
    def __new__(cls, width, height):
        """Creats a new Size."""
        if width is not None:
            width = int(width)
        if height is not None:
            height = int(height)
        return tuple.__new__(cls, (width, height))
    
    @property
    def aspect(self):
        """Returns the aspect ratio of this size."""
        return float(self.width) / float(self.height)
    
    def intersect(self, size):
        """
        Returns a Size that represents the intersection of this and another
        Size.
        """
        return Size(min(self.width, size.width), min(self.height, size.height))
    
    def constrain(self, reference):
        """
        Returns a new Size that is this Size shrunk to fit inside.
        """
        reference_aspect = reference.aspect
        width = min(round(self.height * reference_aspect), self.width)
        height = min(round(self.width / reference_aspect), self.height)
        return Size(width, height)
    
    def scale(self, x_scale, y_scale):
        """Returns a new Size with it's width and height scaled."""
        return Size(float(self.width) * x_scale, float(self.height) * y_scale)


# Size adjustment callbacks. These are used to determine the display and data size of the thumbnail.

def _replace_null(value, fallback):
    """Replaces a null value with a fallback."""
    if value is None:
        return fallback
    return value

def _size(reference, size):
    """Ignores the reference size, and just returns the desired size."""
    return Size(
        _replace_null(size.width, reference.width),
        _replace_null(size.height, reference.height),
    )

def _size_proportional(reference, size):
    """Adjusts the desired size to match the aspect ratio of the reference."""
    if size.width is None and size.height is None:
        return _size(reference, size)
    return Size(
        _replace_null(size.width, sys.maxint),
        _replace_null(size.height, sys.maxint),
    ).constrain(reference)


# Resize callbacks. These are used to actually resize the image data.

def _resize(image, image_size, thumbnail_display_size, thumbnail_image_size):
    """
    Resizes the image to exactly match the desired data size, ignoring aspect
    ratio.
    """
    return image.resize(thumbnail_image_size, Image.ANTIALIAS)

def _resize_cropped(image, image_size, thumbnail_display_size, thumbnail_image_size):
    """
    Resizes the image to fit the desired size, preserving aspect ratio by
    cropping, if required.
    """
    # Resize with nice filter.
    image_aspect = image_size.aspect
    if image_aspect > thumbnail_image_size.aspect:
        # Too wide.
        pre_cropped_size = Size(thumbnail_image_size.height * image_aspect, thumbnail_image_size.height)
    else:
        # Too tall.
        pre_cropped_size = Size(thumbnail_image_size.width, thumbnail_image_size.width / image_aspect)
    # Crop.
    image = image.resize(pre_cropped_size, Image.ANTIALIAS)
    source_x = (pre_cropped_size.width - thumbnail_image_size.width) / 2
    source_y = (pre_cropped_size.height - thumbnail_image_size.height) / 2
    return image.crop((
        source_x,
        source_y,
        source_x + thumbnail_image_size.width,
        source_y + thumbnail_image_size.height,
    ))


# Methods of generating thumbnails.

PROPORTIONAL = "proportional"
RESIZE = "resize"
CROP = "crop"

ResizeMethod = collections.namedtuple("ResizeMethod", ("get_display_size", "get_data_size", "do_resize", "hash_key",))

_methods = {
    PROPORTIONAL: ResizeMethod(_size_proportional, _size, _resize, "resize"),
    RESIZE: ResizeMethod(_size, _size, _resize, "resize"),
    CROP: ResizeMethod(_size, _size_proportional, _resize_cropped, "crop"),
}


class ThumbnailError(Exception):
    
    """Something went wrong with thumbnail generation."""


class ThumbnailAsset(Asset):
    
    """An asset representing a thumbnailed file."""
    
    def __init__(self, asset, width, height, method):
        """Initializes the asset."""
        self._asset = asset
        self._width = width
        self._height = height
        self._method = method
    
    def get_name(self):
        """Returns the name of this asset."""
        return self._asset.get_name()
        
    def get_path(self):
        """Returns the filesystem path of this asset."""
        return self._asset.get_path()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(ThumbnailAsset, self).get_id_params()
        params["width"] = self._width is None and -1 or self._width
        params["height"] = self._height is None and -1 or self._height
        params["method"] = self._method.hash_key
        return params
    
    @cached_property
    def _image_data_and_size(self):
        """Returns the image data used by this thumbnail asset."""
        image_data = open_image(self._asset)
        return image_data, Size(*image_data.size)
    
    def get_save_meta(self):
        """Returns the meta parameters to associate with the asset in the asset cache."""
        method = self._method
        requested_size = Size(self._width, self._height)
        _, original_size = self._image_data_and_size
        # Calculate the final width and height of the thumbnail.
        display_size = method.get_display_size(original_size, requested_size)
        return {
            "size": display_size 
        }
    
    def save(self, storage, name, meta):
        """Saves this asset to the given storage."""
        method = self._method
        # Calculate sizes.
        display_size = meta["size"]
        image_data, original_size = self._image_data_and_size
        data_size = method.get_data_size(display_size, display_size.intersect(original_size))
        # Check whether we need to make a thumbnail.
        if data_size == original_size:
            super(ThumbnailAsset, self).save(storage, name, meta)
        else:
            # Use efficient image loading.
            image_data.draft(None, data_size)
            # Resize the image data.
            try:
                image_data = method.do_resize(image_data, original_size, display_size, data_size)
            except Exception as ex:  # HACK: PIL raises all sorts of Exceptions :(
                raise ThumbnailError(str(ex))
            # Parse the image format.
            _, extension = os.path.splitext(name)
            format = extension.lstrip(".").upper().replace("JPG", "JPEG") or "PNG"
            # If we're saving to PNG, make sure we're not in CMYK.
            if image_data.mode == "CMYK" and format == "PNG":
                image_data = image_data.convert("RGB")
            # If the storage has a path, then save it efficiently.
            try:
                thumbnail_path = storage.path(name)
            except NotImplementedError:
                # No path for the storage, so save it in a memory buffer.
                buffer = StringIO()
                try:
                    image_data.save(buffer, format)
                except Exception as ex:    # HACK: PIL raises all sorts of Exceptions :(
                    raise ThumbnailError(str(ex))
                # Write the file.
                buffer.seek(0, os.SEEK_END)
                buffer_length = buffer.tell()
                buffer.seek(0)
                file = File(buffer)
                file.size = buffer_length
                storage.save(name, file)
            else:
                # We can do an efficient streaming save.
                try:
                    os.makedirs(os.path.dirname(thumbnail_path))
                except OSError:
                    pass
                try:
                    image_data.save(thumbnail_path, format)
                except Exception as ex:  # HACK: PIL raises all sorts of Exceptions :(
                    try:
                        raise ThumbnailError(str(ex))
                    finally:
                        # Remove an incomplete file, if present.
                        try:
                            os.unlink(thumbnail_path)
                        except:
                            pass
                            
        
def open_image(asset):
    """Opens the image represented by the given asset."""
    try:
        asset_path = asset.get_path()
    except NotImplementedError:
        return Image.open(StringIO(asset.get_contents()))
    else:
        return Image.open(asset_path)
    

class Thumbnail(object):

    """A generated thumbnail."""
    
    def __init__(self, asset_cache, asset):
        """Initializes the thumbnail."""
        self._asset_cache = asset_cache
        self._asset = asset
        self.name = asset.get_name()
    
    @cached_property
    def _asset_name_and_meta(self):
        return self._asset_cache.get_name_and_meta(self._asset)
        
    @property
    def width(self):
        """The width of the thumbnail."""
        return self._asset_name_and_meta[1]["size"][0]
    
    @property
    def height(self):
        """The width of the thumbnail."""
        return self._asset_name_and_meta[1]["size"][1]
        
    @property
    def url(self):
        """The URL of the thumbnail."""
        return self._asset_cache._storage.url(self._asset_name_and_meta[0])
        
    @property
    def path(self):
        """The path of the thumbnail."""
        return self._asset_cache._storage.path(self._asset_name_and_meta[0])


class ThumbnailCache(object):

    """A cache of thumbnailed images."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
        
    def get_thumbnail(self, asset, width=None, height=None, method=PROPORTIONAL):
        """
        Returns a thumbnail of the given size.
        
        Either or both of width and height may be None, in which case the
        image's original size will be used.
        """
        # Lookup the method.
        try:
            method = _methods[method]
        except KeyError:
            raise ValueError("{method} is not a valid thumbnail method. Should be one of {methods}.".format(
                method = method,
                methods = ", ".join(_methods.iterkeys())
            ))
        # Adapt the asset.
        asset = AdaptiveAsset(asset)
        # Create the thumbnail.
        return Thumbnail(self._asset_cache, ThumbnailAsset(asset, width, height, method))
        
        
# The default thumbnail cache.
default_thumbnail_cache = ThumbnailCache()