"""A cache of javascipt files, optionally compressed."""

import httplib
from contextlib import closing

from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.http import urlencode

from optimizations.assetcache import Asset, AdaptiveAsset, default_asset_cache


class JavascriptAsset(Asset):

    """An asset that represents one or more javascript files."""
    
    def __init__(self, assets, compress):
        """Initializes the asset."""
        self._assets = assets
        self._compress = compress
    
    def get_name(self):
        """Returns the name of this asset."""
        return self._assets[0].get_name()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = {
            "compress": self._compress,
        }
        urls = []
        paths = []
        # Add in the assets.
        for asset in self._assets:
            try:
                urls.append(asset.get_url())
            except NotImplementedError:
                pass
            try:
                paths.append(asset.get_path())
            except NotImplementedError:
                pass
        # Apply the urls and paths.
        if urls:
            params["urls"] = u":".join(urls)
        if paths:
            params["paths"] = u":".join(paths)
        # All done.
        return params
        
    def get_mtime(self):
        """Returns the modified time for this asset."""
        return max(asset.get_mtime() for asset in self._assets)
    
    def _get_js_code(self):
        """Loads all the js code."""
        js_code_parts = []
        for asset in self._assets:
            with closing(asset.open()) as handle:
                js_code_parts.append(handle.read())
        return ";".join(js_code_parts)
    
    def open(self):
        """Returns an open file pointer."""
        return ContentFile(self._get_js_code())
    
    def save(self, storage, name):
        """Saves this asset to the given storage."""
        if self._compress:
            # Format a request to the Google closure compiler service.
            params = [
                ("js_code", self._get_js_code()),
                ("compilation_level", "SIMPLE_OPTIMIZATIONS"),
                ("output_format", "text"),
                ("output_info", "compiled_code"),
            ]
            post_data = urlencode(params, doseq=True)
            # Send the request.
            with closing(httplib.HTTPConnection("closure-compiler.appspot.com", timeout=10)) as connection:
                connection.request("POST", "/compile", post_data, {
                    "Content-Type": "application/x-www-form-urlencoded",
                })
                response = connection.getresponse()
                compressed_js_code = response.read()
            # Save the code.
            file = ContentFile(compressed_js_code)
            storage.save(name, file)
        else:
            # Just save the joined code.
            super(JavascriptAsset, self).save(storage, name)
            
            
class JavascriptCache(object):
    
    """A cache of javascript files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
        
    def get_urls(self, assets, compress=True):
        """Returns a sequence of script URLs for the given assets."""
        assets = [AdaptiveAsset(asset) for asset in assets]
        # If we're in debug, then just return the URLs.
        if settings.DEBUG:
            return [self._asset_cache.get_url(asset) for asset in assets]
        # Actually do the caching.
        return [self._asset_cache.get_url(JavascriptAsset(assets, compress))]
        
        
# The default javascript cache.
default_javascript_cache = JavascriptCache()