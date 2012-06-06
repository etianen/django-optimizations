"""A cache of javascipt files, optionally compressed."""

import re, urlparse, os.path, subprocess
from contextlib import closing

from django.conf import settings
from django.core.files.base import ContentFile

import optimizations
from optimizations.assetcache import default_asset_cache, GroupedAsset, AdaptiveAsset
from optimizations.assetcompiler import AssetCompilerPluginBase, default_asset_compiler


class StylesheetError(Exception):
    
    """Something went wrong with stylesheet compilation."""
    
    def __init__(self, message, detail_message):
        """Initializes the stylesheet error."""
        super(StylesheetError, self).__init__(message)
        self.detail_message = detail_message


RE_URLS = (
    re.compile(u"url\('([^']+)'\)", re.IGNORECASE),
    re.compile(u"url\(\"([^\"]+)\"\)", re.IGNORECASE),
    re.compile(u"url\(([^\)]+)\)", re.IGNORECASE),
    re.compile(u"@import\s*\('([^']+)'\)", re.IGNORECASE),
    re.compile(u"@import\s*\(\"([^\"]+)\"\)", re.IGNORECASE),
    re.compile(u"@import\s*\(([^\)]+)\)", re.IGNORECASE),
)


class StylesheetAsset(GroupedAsset):

    """An asset that represents one or more stylesheet files."""
    
    def __init__(self, assets, compile):
        """Initializes the asset."""
        super(StylesheetAsset, self).__init__(assets)
        self._compile = compile
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(StylesheetAsset, self).get_id_params()
        params["compile"] = self._compile
        return params
            
    def save(self, storage, name, meta):
        """Saves this asset to the given storage."""
        file_parts = []
        # Compile the assets.
        for asset in self._assets:
            # Load the asset source.
            with closing(asset.open()) as handle:
                source = handle.read().decode("utf-8")
            # Get the asset URL.
            host_url = asset.get_url()
            for re_url in RE_URLS:
                def do_url_replacement(match):
                    url = match.group(1).strip()
                    # Resolve relative URLs.
                    url = urlparse.urljoin(host_url, url)
                    # Strip off query and fragment.
                    url_parts = urlparse.urlparse(url)
                    # Compile static urls.
                    if url.startswith(settings.STATIC_URL):
                        simple_url = urlparse.urlunparse(url_parts[:3] + ("", "", "",))
                        static_url = default_asset_cache.get_url(simple_url[len(settings.STATIC_URL):], force_save=True)
                        url = urlparse.urlunparse(urlparse.urlparse(static_url)[:3] + url_parts[3:])
                    return u"url({url})".format(
                        url = url,
                    )
                source = re_url.sub(do_url_replacement, source)
            file_parts.append(source.encode("utf-8"))
        # Consolidate the content.
        contents = self.join_str.join(file_parts)
        if self._compile:
            # Compress the content.
            compressor_path = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
            process = subprocess.Popen(
                ("java", "-jar", compressor_path, "--type", "css", "--charset", "utf-8", "-v"),
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
            )
            contents, stderrdata = process.communicate(contents)
            # Check it all worked.
            if process.returncode != 0:
                raise StylesheetError("Error while compiling stylesheets.", stderrdata)
        # Write the output.
        storage.save(name, ContentFile(contents))
            
            
class StylesheetCache(object):
    
    """A cache of stylesheet files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, force_save=None):
        """Returns a sequence of style URLs for the given assets."""
        if force_save is None:
            force_save = not settings.DEBUG
        if force_save:
            if assets:
                return [self._asset_cache.get_url(StylesheetAsset(map(AdaptiveAsset, assets), compile), force_save=True)]    
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default stylesheet cache.
default_stylesheet_cache = StylesheetCache()


# Asset compiler plugin.

class StylesheetAssetCompilerPlugin(AssetCompilerPluginBase):
    
    """An asset compiler plugin for stylesheet files."""
    
    asset_type = "stylesheet"
    
    def __init__(self, stylesheet_cache=default_stylesheet_cache):
        """Initialzies the stylesheet asset compiler plugin."""
        self._stylesheet_cache = stylesheet_cache
        
    def compile_assets(self, assets):
        """Compiles the given stylesheet assets."""
        self._stylesheet_cache.get_urls(assets, force_save=True)
        

default_asset_compiler.register_plugin("css", StylesheetAssetCompilerPlugin())