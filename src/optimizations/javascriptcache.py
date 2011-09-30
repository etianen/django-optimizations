"""A cache of javascipt files, optionally compressed."""

import httplib, logging, os.path
from contextlib import closing

from django.core.files.base import ContentFile
from django.conf import settings
from django.core.mail import mail_admins
from django.utils.http import urlencode
from django.utils import simplejson as json
from django.contrib.staticfiles.finders import find as find_static_path

from optimizations.assetcache import Asset, AdaptiveAsset, default_asset_cache, StaticAsset


logger = logging.getLogger("optimizations.javascript")


class JavascriptError(Exception):
    
    """Something went wrong with javascript compilation."""


class JavascriptAsset(Asset):

    """An asset that represents one or more javascript files."""
    
    def __init__(self, assets, compile, fail_silently):
        """Initializes the asset."""
        self._assets = assets
        self._compile = compile
        self._fail_silently = fail_silently
    
    def get_name(self):
        """Returns the name of this asset."""
        return self._assets[0].get_name()
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = {
            "compile": self._compile,
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
        if self._compile:
            js_code = self._get_js_code().strip()
            if js_code:
                # Format a request to the Google closure compiler service.
                params = [
                    ("js_code", self._get_js_code()),
                    ("compilation_level", "SIMPLE_OPTIMIZATIONS"),
                    ("output_format", "json"),
                    ("output_info", "compiled_code"),
                    ("output_info", "errors"),
                ]
                post_data = urlencode(params, doseq=True)
                # Send the request.
                with closing(httplib.HTTPConnection("closure-compiler.appspot.com", timeout=10)) as connection:
                    connection.request("POST", "/compile", post_data, {
                        "Content-Type": "application/x-www-form-urlencoded",
                    })
                    response = connection.getresponse()
                    response_str = response.read()
                response_data = json.loads(response_str)
                # Log the errors and warnings.
                def get_extra(extra):
                    extra["jslineno"] = extra.pop("lineno")
                    return extra
                for error in response_data.get("errors", ()):
                    logger.error(error["error"], extra=get_extra(error))
                for warning in response_data.get("warnings", ()):
                    logger.warning(warning["warning"], extra=get_extra(warning))
                # Save the compressed code, if available.
                if len(response_data.get("errors", ())) > 0:
                    if self._fail_silently:
                        compressed_js_code = js_code
                    else:
                        raise JavascriptError(response_data["errors"][0]["error"])
                else:
                    compressed_js_code = response_data["compiledCode"].decode("ascii").encode("utf-8")
            else:
                compressed_js_code = js_code
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
    
    def get_urls(self, assets, compile=True, force_save=(not settings.DEBUG), fail_silently=True):
        """Returns a sequence of script URLs for the given assets."""
        if force_save:
            if assets:
                return [self._asset_cache.get_url(JavascriptAsset(assets, compile, fail_silently=fail_silently))]    
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default javascript cache.
default_javascript_cache = JavascriptCache()