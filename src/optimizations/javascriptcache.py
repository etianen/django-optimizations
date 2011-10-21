"""A cache of javascipt files, optionally compressed."""

import logging, subprocess, os.path

from django.conf import settings
from django.core.files.base import ContentFile

import optimizations
from optimizations.assetcache import default_asset_cache, GroupedAsset


logger = logging.getLogger("optimizations.javascript")


class JavascriptError(Exception):
    
    """Something went wrong with javascript compilation."""


class JavascriptAsset(GroupedAsset):

    """An asset that represents one or more javascript files."""
    
    join_str = ";"
    
    def __init__(self, assets, compile, fail_silently):
        """Initializes the asset."""
        super(JavascriptAsset, self).__init__(assets)
        self._compile = compile
        self._fail_silently = fail_silently
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(JavascriptAsset, self).get_id_params()
        params["compile"] = self._compile
        return params
            
    def save(self, storage, name):
        """Saves this asset to the given storage."""
        if self._compile:
            compressor_path = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
            process = subprocess.Popen(
                ("java", "-jar", compressor_path, "--type", "js", "--charset", "utf-8", "-v"),
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
            )
            stdoutdata, stderrdata = process.communicate(self.get_contents())
            # Check it all worked.
            if process.returncode != 0:
                logger.error(stderrdata)
                raise JavascriptError("Error while compiling javascript.")
            # Write the output.
            file = ContentFile(stdoutdata)
            storage.save(name, file)
        else:
            # Just save the joined code.
            super(JavascriptAsset, self).save(storage, name)
            
            
class JavascriptCache(object):
    
    """A cache of javascript files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, force_save=(not settings.DEBUG), fail_silently=True):
        """Returns a sequence of script URLs for the given assets."""
        if force_save:
            if assets:
                return [self._asset_cache.get_url(JavascriptAsset(assets, compile, fail_silently=fail_silently))]    
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default javascript cache.
default_javascript_cache = JavascriptCache()