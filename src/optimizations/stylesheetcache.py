"""A cache of javascipt files, optionally compressed."""

import re, logging, os.path, urlparse
from contextlib import closing

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.http import urlencode
from django.utils import simplejson as json
from django.contrib.staticfiles.finders import find as find_static_path

from optimizations.assetcache import default_asset_cache, GroupedAsset


logger = logging.getLogger("optimizations.stylesheet")


RE_URLS = (
    re.compile(u"url\(([^\)]+)\)", re.IGNORECASE),
    re.compile(u"url\('([^']+)'\)", re.IGNORECASE),
    re.compile(u"url\(\"([^\"]+)'\"\)", re.IGNORECASE),
)

RE_WHITESPACE = re.compile(u"\s{2,}")

RE_IGNORABLE_WHITESPACE = (
    re.compile(u"\s*({char})\s*".format(char=re.escape(char)), re.IGNORECASE)
    for char in u"{};,"
)

RE_LINEBREAKS = re.compile(u"(.{1000,}?\})", re.IGNORECASE)

RE_HEX = re.compile(u"#[a-f0-9]{6}", re.IGNORECASE)


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
                        url = match.group(1).strip().replace(u" ", "%20")
                        # Resolve relative URLs.
                        url = urlparse.urljoin(host_url, url)
                        # Compile static urls.
                        if url.startswith(settings.STATIC_URL):
                            url = default_asset_cache.get_url(url[len(settings.STATIC_URL):], force_save=True)
                        return u"url({url})".format(
                            url = url,
                        )
                    source = re_url.sub(do_url_replacement, source)
                # Compress hex codes.
                def do_hex_replacement(match):
                    hex = match.group(0)
                    if hex[1] == hex[2] and hex[3] == hex[4] and hex[5] == hex[6]:
                        return u"#{0}{1}{2}".format(hex[1], hex[3], hex[5])
                    return hex
                source = RE_HEX.sub(do_hex_replacement, source)
                # Reduce whitespace.
                source = RE_WHITESPACE.sub(u" ", source)
                for re_ignorable in RE_IGNORABLE_WHITESPACE:
                    source = re_ignorable.sub(ur"\1", source)
                # Add occasional linebreaks.
                source = RE_LINEBREAKS.sub(ur"\1\n", source)
                # Add to the files.
                file_parts.append(source.encode("utf-8"))
            # Save the code.
            file = ContentFile(self.join_str.join(file_parts))
            storage.save(name, file)
        else:
            # Just save the joined code.
            super(StylesheetAsset, self).save(storage, name)
            
            
class StylesheetCache(object):
    
    """A cache of stylesheet files."""
    
    def __init__(self, asset_cache=default_asset_cache):
        """Initializes the thumbnail cache."""
        self._asset_cache = asset_cache
    
    def get_urls(self, assets, compile=True, force_save=(not settings.DEBUG)):
        """Returns a sequence of style URLs for the given assets."""
        if force_save:
            if assets:
                return [self._asset_cache.get_url(StylesheetAsset(assets, compile))]    
            return []
        return [self._asset_cache.get_url(asset) for asset in assets]
        
        
# The default stylesheet cache.
default_stylesheet_cache = StylesheetCache()