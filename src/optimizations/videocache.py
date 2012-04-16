"""Video processing and resizing tools using ffmpeg."""

import subprocess, re, os, collections
from contextlib import closing
from cStringIO import StringIO

from django.core.files import File

from optimizations.assetcache import Asset, default_asset_cache, AdaptiveAsset


class VideoError(Exception):
    
    """Something went wrong with video processing."""
    
    def __init__(self, message, detail_message):
        """Initializes the video error."""
        super(VideoError, self).__init__(message)
        self.detail_message = detail_message


RE_DURATION = re.compile("Duration:\s*(\d+):(\d+):(\d+)", re.IGNORECASE)


# Size adjustment callbacks.

def _size(width, height):
    """Performs a non-proportional resize."""
    return ("-vf", r"scale={width}:{height}".format(width=width, height=height))
    

def _size_proportional(width, height):
    """Performs a proportional resize."""
    return ("-vf", r"scale=min({height}*(iw/ih)\,{width}):min({width}/(iw/ih)\,{height})".format(width=width, height=height))
    
    
def _size_crop(width, height):
    """Performs a cropping resize."""
    return ("-vf", r"scale=max({height}*(iw/ih)\,{width}):max({width}/(iw/ih)\,{height}),crop={width}:{height}".format(width=width, height=height),)
    

def _size_pad(width, height):
    """Performs a padded resize."""
    return ("-vf", r"scale=min({height}*(iw/ih)\,{width}):min({width}/(iw/ih)\,{height}),pad={width}:{height}:({width}-iw)/2:({height}-ih)/2".format(width=width, height=height),)
    
    
PROPORTIONAL = "proportional"
RESIZE = "resize"
CROP = "crop"
PAD = "pad"

ResizeMethod = collections.namedtuple("ResizeMethod", ("get_size_params", "hash_key",))

_methods = {
    PROPORTIONAL: ResizeMethod(_size_proportional, "proportional"),
    RESIZE: ResizeMethod(_size, "resize"),
    CROP: ResizeMethod(_size_crop, "crop"),
    PAD: ResizeMethod(_size_pad, "pad"),
}


# Video format callbacks.

def _format_jpeg(input_path, offset):
    """Formats video to a jpeg thumbnail."""
    # Get the video duration.
    if offset is None:
        process = subprocess.Popen(
            ("ffmpeg", "-i", input_path),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
        )
        stdoutdata, stderrdata = process.communicate()
        duration_match = RE_DURATION.search(" ".join((stdoutdata, stderrdata,)))
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            duration = int(hours) * 60 * 60 + int(minutes) * 60 * 60 + int(seconds)
        else:
            # Fallback - we can't parse the time, so assume 0 seconds.
            duration = 0
        offset = duration / 4
    return offset, ("-vframes", "1", "-an", "-f", "image2",)


def _format_mp4(input_path, offset):
    """Formats the video to an MP4."""
    return offset, ("-f", "mp4",)
    
    
JPEG_FORMAT = "jpeg"
MP4_FORMAT = "mp4"

FormatMethod = collections.namedtuple("FormatMethod", ("get_format_params", "extension", "hash_key",))

_formats = {
    JPEG_FORMAT: FormatMethod(_format_jpeg, "jpg", "jpeg"),
    MP4_FORMAT: FormatMethod(_format_mp4, "mp4", "mp4"),
}

    

# The video asset.    
    
class VideoAsset(Asset):
    
    """A video asset."""
    
    def __init__(self, asset, width, height, method, format, offset):
        """Initializes the video asset."""
        self._asset = asset
        self._width = width
        self._height = height
        self._method = method
        self._format = format
        self._offset = offset
        
    def get_name(self):
        """Returns the name of this asset."""
        return self._asset.get_name()
        
    def get_path(self):
        """Returns the filesystem path of this asset."""
        return self._asset.get_path()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(VideoAsset, self).get_id_params()
        params["width"] = self._width is None and -1 or self._width
        params["height"] = self._height is None and -1 or self._height
        params["method"] = self._method.hash_key
        params["format"] = self._format.hash_key
        params["offset"] = self._offset is None and -1 or self._offset
        return params
    
    def get_save_extension(self):
        """Returns the file extension to use when saving the asset."""
        return "." + self._format.extension
    
    def save(self, storage, name, meta):
        """Saves the video."""
        # Get the input handle.
        try:
            input_path = self._asset.get_path()
        except NotImplementedError:
            raise VideoError("Video cache cannot operate on remote filesystems")
        # Calculate sizes.
        if self._width is not None or self._height is not None:
            size_params = self._method.get_size_params(self._width or "iw", self._height or "ih")
        else:
            size_params = ()
        # Calculate offset and format.
        offset, format_params = self._format.get_format_params(input_path, self._offset)
        # Get the output path.
        try:
            output_path = storage.path(name)
        except NotImplementedError:
            raise VideoError("Video cache cannot operate on remote filesystems")
        try:
            os.makedirs(os.path.dirname(output_path))
        except OSError:
            pass
        # Generate the video.
        process = subprocess.Popen(
            ("ffmpeg", "-ss", str(offset or 0), "-i", input_path,) + size_params + format_params + (output_path,),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
        )
        stdoutdata, stderrdata = process.communicate()
        if process.returncode != 0:
            try:
                raise VideoError("Could not generate video due to video processing error", " ".join((stdoutdata, stderrdata,)))
            finally:
                # Remove an incomplete file, if present.
                try:
                    os.unlink(output_path)
                except:
                    pass
        
            
class VideoCache(object):

    """A cache of videos."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the video cache."""
        self._asset_cache = asset_cache
        
    def _get_video_asset(self, asset, width=None, height=None, method=PAD, format=MP4_FORMAT, offset=None):
        """
        Returns a processed video from the given video.
        """
        # Lookup the method.
        try:
            method = _methods[method]
        except KeyError:
            raise ValueError("{method} is not a valid video method. Should be one of {methods}.".format(
                method = method,
                methods = ", ".join(_methods.iterkeys())
            ))
        # Lookup the format.
        try:
            format = _formats[format]
        except KeyError:
            raise ValueError("{format} is not a valid video format. Should be one of {formats}.".format(
                format = format,
                formats = ", ".join(_formats.iterkeys())
            ))
        # Adapt the asset.
        asset = AdaptiveAsset(asset)
        # Create the video.
        return VideoAsset(asset, width, height, method, format, offset)
    
    def get_path(self, *args, **kwargs):
        """Returns the path of the given video asset."""
        return self._asset_cache.get_path(self._get_video_asset(*args, **kwargs), force_save=True)
    
    def get_url(self, *args, **kwargs):
        """Returns the URL of the given video asset."""
        return self._asset_cache.get_url(self._get_video_asset(*args, **kwargs), force_save=True)
        
        
# The default video cache.
default_video_cache = VideoCache()