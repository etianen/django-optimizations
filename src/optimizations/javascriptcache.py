"""A cache of javascipt files, optionally compressed."""

from django.conf import settings
from django.core.files.base import ContentFile

from optimizations.assetcache import default_asset_cache, GroupedAsset, AdaptiveAsset
from optimizations.assetcompiler import default_asset_compiler, AssetCompilerPluginBase
from optimizations.javascriptcompiler import default_javascript_compiler


class JavascriptAsset(GroupedAsset):

    """An asset that represents one or more javascript files."""
    
    join_str = ";"
    
    def __init__(self, assets, compile, rescope):
        """Initializes the asset."""
        super(JavascriptAsset, self).__init__(assets)
        self._compile = compile
        self._rescope = rescope
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(JavascriptAsset, self).get_id_params()
        params["compile"] = self._compile
        params["rescope"] = self._rescope
        return params
            
    def save(self, storage, name, meta):
        """Saves this asset to the given storage."""
        if self._compile:
            contents = self.get_contents()
            if self._rescope:
                contents = "(function(window){%s}(window));" % contents
            compiled_contents = default_javascript_compiler.compile(contents, force_compile=True)
            # Write the output.
            storage.save(name, ContentFile(compiled_contents))
        else:
            # Just save the joined code.
            super(JavascriptAsset, self).save(storage, name, meta)
            
            
class JavascriptCache(object):
    
    """A cache of javascript files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, rescope=False, force_save=None):
        """Returns a sequence of script URLs for the given assets."""
        if force_save is None:
            force_save = not settings.DEBUG
        if force_save:
            if assets:
                return [self._asset_cache.get_url(JavascriptAsset(map(AdaptiveAsset, assets), compile, rescope), force_save=True)]
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