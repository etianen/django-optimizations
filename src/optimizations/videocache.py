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
    if width is not None and height is not None:
        return ("-vf", r"scale=min({width}\,iw):min({height}\,ih)".format(width=width, height=height))
    elif width is not None:
        return ("-vf", r"scale=min({width}\,iw):-1".format(width=width))
    elif height is not None:
        return ("-vf", r"scale=-1:min({height}\,ih)".format(height=height))
    

def _size_proportional(width, height):
    """Performs a proportional resize."""
    if width is not None and height is not None:
        return ("-vf", r"scale=min(min({height}\,ih)*(iw/ih)\,min({width}\,iw)):min(min({width}\,iw)/(iw/ih)\,min({height}\,ih))".format(width=width, height=height))
    elif width is not None:
        return ("-vf", r"scale=min({width}\,iw):-1".format(width=width))
    elif height is not None:
        return ("-vf", r"scale=-1:min({height}\,ih)".format(height=height))
    
    
def _size_crop(width, height):
    """Performs a cropping resize."""
    if width is None:
        width = "iw"
    if height is  None:
        height = "ih"
    return (
        "-vf",
        r"scale=max(min({height}\,ih)*(iw/ih)\,min({width}\,iw)):max(min({width}\,iw)/(iw/ih)\,min({height}\,ih)),crop={width}:{height}".format(width=width, height=height),
    )
    

def _size_pad(width, height):
    """Performs a padded resize."""
    if width is None:
        width = "iw"
    if height is  None:
        height = "ih"
    return (
        "-vf",
        r"scale=min(min({height}\,ih)*(iw/ih)\,min({width}\,iw)):min(min({width}\,iw)/(iw/ih)\,min({height}\,ih)),pad={width}:{height}:({width}-iw)/2:({height}-ih)/2".format(width=width, height=height),
    )
    
    
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
    

# The video thumbnail asset.    
    
class VideoThumbnailAsset(Asset):
    
    """A video thumbnail asset."""
    
    def __init__(self, asset, width, height, method, position=None):
        """Initializes the video thumbnail asset."""
        self._asset = asset
        self._width = width
        self._height = height
        self._method = method
        self._position = position
        
    def get_name(self):
        """Returns the name of this asset."""
        return self._asset.get_name()
        
    def get_path(self):
        """Returns the filesystem path of this asset."""
        return self._asset.get_path()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(VideoThumbnailAsset, self).get_id_params()
        params["width"] = self._width is None and -1 or self._width
        params["height"] = self._height is None and -1 or self._height
        params["method"] = self._method.hash_key
        params["position"] = self._position is None and -1 or self._position
        return params
    
    def get_save_extension(self):
        """Returns the file extension to use when saving the asset."""
        return ".jpg"
    
    def save(self, storage, name, meta):
        """Saves the video thumbnail."""
        # Get the input handle.
        try:
            input_handle = open(self._asset.get_path(), "rb")
        except NotImplementedError:
            # We need to buffer the lot in memory...
            input_handle = StringIO(self._asset.get_contents())
        # Process the handles.
        with closing(input_handle):
            # Get the video duration.
            if self._position is None:
                process = subprocess.Popen(
                    ("ffmpeg", "-i", "-"),
                    stdin = input_handle,
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
                position = duration / 4
            else:
                position = self._position
            # Get the output handle.
            try:
                output_path = storage.path(name)
            except NotImplementedError:
                # We need to buffer the output in memory.
                output_handle = StringIO()
                is_streaming = False
            else:
                try:
                    os.makedirs(os.path.dirname(output_path))
                except OSError:
                    pass
                output_handle = open(output_path, "wb")
                is_streaming = True
            with closing(output_handle):
                # Generate the thumbnail.
                input_handle.seek(0)
                # Calculate sizes.
                if self._width is not None or self._height is not None:
                    size_params = self._method.get_size_params(self._width, self._height)
                else:
                    size_params = ()
                process = subprocess.Popen(
                    ("ffmpeg", "-ss", str(position), "-i", "-",) + size_params + ("-vframes", "1", "-an", "-f", "image2", "-",),
                    stdin = input_handle,
                    stdout = output_handle,
                    stderr = subprocess.PIPE,
                )
                stdoutdata, stderrdata = process.communicate()
                if process.returncode != 0:
                    try:
                        raise VideoError("Could not generate video thumbnail due to image processing error", stderrdata)
                    finally:
                        if is_streaming:
                            # Remove an incomplete file, if present.
                            try:
                                os.unlink(output_path)
                            except:
                                pass
                # Save non-streaming data.
                if not is_streaming:
                    output_handle.seek(0, os.SEEK_END)
                    output_handle_length = buffer.tell()
                    output_handle.seek(0)
                    file = File(buffer)
                    file.size = output_handle_length
                    storage.save(name, file)
            
            
class VideoThumbnailCache(object):

    """A cache of thumbnailed videos."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the video thumbnail cache."""
        self._asset_cache = asset_cache
        
    def get_video_thumbnail(self, asset, width=None, height=None, method=PROPORTIONAL, position=None):
        """
        Returns a thumbnail of the given video.
        """
        # Lookup the method.
        try:
            method = _methods[method]
        except KeyError:
            raise ValueError("{method} is not a valid video thumbnail method. Should be one of {methods}.".format(
                method = method,
                methods = ", ".join(_methods.iterkeys())
            ))
        # Adapt the asset.
        asset = AdaptiveAsset(asset)
        # Create the thumbnail.
        return self._asset_cache.get_path(VideoThumbnailAsset(asset, width, height, method, position), force_save=True)
        
        
# The default video thumbnail cache.
default_video_thumbnail_cache = VideoThumbnailCache()