"""A cache of javascipt files, optionally compressed."""

import re, logging, urlparse, os.path, subprocess
from contextlib import closing

from django.conf import settings
from django.core.files.base import ContentFile

import optimizations
from optimizations.assetcache import default_asset_cache, GroupedAsset


logger = logging.getLogger("optimizations.stylesheet")


class StylesheetError(Exception):
    
    """Something went wrong with stylesheet compilation."""


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
    
    def __init__(self, assets, compile, fail_silently):
        """Initializes the asset."""
        super(StylesheetAsset, self).__init__(assets)
        self._compile = compile
        self._fail_silently = fail_silently
    
    def get_id_params(self):
        """"Returns the params which should be used to generate the id."""
        params = super(StylesheetAsset, self).get_id_params()
        params["compile"] = self._compile
        return params
            
    def save(self, storage, name):
        """Saves this asset to the given storage."""
        if self._compile:
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
            # Compress the content.
            compressor_path = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
            process = subprocess.Popen(
                ("java", "-jar", compressor_path, "--type", "css", "--charset", "utf-8", "-v"),
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
            )
            stdoutdata, stderrdata = process.communicate(contents)
            # Check it all worked.
            if process.returncode != 0:
                logger.error(stderrdata)
                if not self._fail_silently:
                    raise StylesheetError("Error while compiling stylesheets.")
                file = ContentFile(self.get_contents())
            else:
                # Write the output.
                file = ContentFile(stdoutdata)
            storage.save(name, file)
        else:
            # Just save the joined code.
            super(StylesheetAsset, self).save(storage, name)
            
            
class StylesheetCache(object):
    
    """A cache of stylesheet files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, force_save=(not settings.DEBUG), fail_silently=True):
        """Returns a sequence of style URLs for the given assets."""
        if force_save:
            if assets:
                return [self._asset_cache.get_url(StylesheetAsset(assets, compile, fail_silently=True), force_save=True)]    
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default stylesheet cache.
default_stylesheet_cache = StylesheetCache()