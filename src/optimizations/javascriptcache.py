"""A cache of javascipt files, optionally compressed."""

import subprocess, os.path

from django.conf import settings
from django.core.files.base import ContentFile

import optimizations
from optimizations.assetcache import default_asset_cache, GroupedAsset
from optimizations.assetcompiler import default_asset_compiler, AssetCompilerPluginBase


class JavascriptError(Exception):
    
    """Something went wrong with javascript compilation."""
    
    def __init__(self, message, detail_message):
        """Initializes the javascript error."""
        super(JavascriptError, self).__init__(message)
        self.detail_message = detail_message


class JavascriptAsset(GroupedAsset):

    """An asset that represents one or more javascript files."""
    
    join_str = ";"
    
    def __init__(self, assets, compile):
        """Initializes the asset."""
        super(JavascriptAsset, self).__init__(assets)
        self._compile = compile
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(JavascriptAsset, self).get_id_params()
        params["compile"] = self._compile
        return params
            
    def save(self, storage, name, meta):
        """Saves this asset to the given storage."""
        if self._compile:
            contents = self.get_contents()
            compressor_path = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
            process = subprocess.Popen(
                ("java", "-jar", compressor_path, "--type", "js", "--charset", "utf-8", "-v"),
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
            )
            stdoutdata, stderrdata = process.communicate(contents)
            # Check it all worked.
            if process.returncode != 0:
                raise JavascriptError("Error while compiling javascript.", stderrdata)
            # Write the output.
            storage.save(name, ContentFile(stdoutdata))
        else:
            # Just save the joined code.
            super(JavascriptAsset, self).save(storage, name, meta)
            
            
class JavascriptCache(object):
    
    """A cache of javascript files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, force_save=None):
        """Returns a sequence of script URLs for the given assets."""
        if force_save is None:
            force_save = not settings.DEBUG
        if force_save:
            if assets:
                return [self._asset_cache.get_url(JavascriptAsset(assets, compile), force_save=True)]
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default javascript cache.
default_javascript_cache = JavascriptCache()


# Asset compiler plugin.

class JavascriptAssetCompilerPlugin(AssetCompilerPluginBase):
    
    """An asset compiler plugin for javascript files."""
    
    asset_type = "javascript"
    
    def __init__(self, javascript_cache=default_javascript_cache):
        """Initialzies the javascript asset compiler plugin."""
        self._javascript_cache = javascript_cache
        
    def compile_assets(self, assets):
        """Compiles the given javascript assets."""
        self._javascript_cache.get_urls(assets, force_save=True)
        

default_asset_compiler.register_plugin("js", JavascriptAssetCompilerPlugin())