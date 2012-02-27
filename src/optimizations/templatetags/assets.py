"""Template tags used for optimizing assets."""

from django import template

from optimizations.assetcache import StaticAsset, default_asset_cache, AdaptiveAsset
from optimizations.thumbnailcache import default_thumbnail_cache, PROPORTIONAL
from optimizations.javascriptcache import default_javascript_cache
from optimizations.stylesheetcache import default_stylesheet_cache
from optimizations.templatetags import parameter_tag


register = template.Library()


@register.filter
def asset_url(src):
    """Returns the cached asset URL of the given asset."""
    return default_asset_cache.get_url(src)


class ThumbnailRenderer(object):

    """Renders a thumbnail object."""
    
    def __init__(self, url, width, height, alt, attrs):
        """Initializes the renderer."""
        self.url = url
        self.width = width
        self.height = height
        self.alt = alt
        self.attrs = attrs
        
    def __unicode__(self):
        """Renders the thumbnail."""
        return template.loader.render_to_string("assets/img.html", {
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "alt": self.alt,
            "attrs": self.attrs,
        })
    

@parameter_tag(register)
def img(src, width=None, height=None, method=PROPORTIONAL, alt="", **attrs):
    """Renders an image tag."""
    try:
        thumbnail = default_thumbnail_cache.get_thumbnail(
            src,
            width = width,
            height = height,
            method = method,
        )
    except IOError:
        asset = AdaptiveAsset(src)
        return ThumbnailRenderer(asset.get_url(), width or "", height or "", alt, attrs)
    else:
        return ThumbnailRenderer(thumbnail.url, thumbnail.width, thumbnail.height, alt, attrs)
    
    
class ScriptRenderer(object):

    """Renders a script tag."""

    def __init__(self, url):
        """Initializes the script renderer."""
        self.url = url
        
    def __unicode__(self):
        """Renders the script tags."""
        return template.loader.render_to_string("assets/script.html", {
            "url": self.url,
        })
        
        
class MultiScriptRenderer(object):

    """Renders multiple script tags."""
    
    def __init__(self, urls):
        """Initializes the multi script renderer."""
        self.urls = urls
        
    def __iter__(self):
        """Iterates over the renderer's script files."""
        return (ScriptRenderer(url) for url in self.urls)
        
    def __unicode__(self):
        """Renders all the script tags."""
        return u"".join(unicode(script) for script in self)
    
    
@parameter_tag(register)
def script(src="default"):
    """Renders one or more script tags."""
    assets = StaticAsset.load("js", src)
    return MultiScriptRenderer(default_javascript_cache.get_urls(assets))
    
    
class StylesheetRenderer(object):

    """Renders a stylesheet tag."""

    def __init__(self, url, attrs):
        """Initializes the stylesheet renderer."""
        self.url = url
        self.attrs = attrs
        
    def __unicode__(self):
        """Renders the script tags."""
        return template.loader.render_to_string("assets/stylesheet.html", {
            "url": self.url,
            "attrs": self.attrs,
        })
        
        
class MultiStylesheetRenderer(object):

    """Renders multiple stylesheet tags."""
    
    def __init__(self, urls, attrs):
        """Initializes the multi stylesheet renderer."""
        self.urls = urls
        self.attrs = attrs
        
    def __iter__(self):
        """Iterates over the renderer's stylesheet files."""
        return (StylesheetRenderer(url, self.attrs) for url in self.urls)
        
    def __unicode__(self):
        """Renders all the stylesheet tags."""
        return u"".join(unicode(stylesheet) for stylesheet in self)
    
    
@parameter_tag(register)
def stylesheet(href="default", **attrs):
    """Renders one or more stylesheet tags."""
    assets = StaticAsset.load("css", href)
    return MultiStylesheetRenderer(default_stylesheet_cache.get_urls(assets), attrs)