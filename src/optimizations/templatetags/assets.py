"""Template tags used for optimizing assets."""

from django import template
from django.utils.html import escape, escapejs

from optimizations.assetcache import default_asset_cache
from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.javascriptcache import default_javascript_cache
from optimizations.templatetags import parameter_tag


register = template.Library()


# Escape functions for the asset tag.
asset_escapers = {
    "html": escape,
    "js": escapejs,
}


@parameter_tag(register)
def asset(src, escape="html"):
    """Returns the cached asset URL of the given asset."""
    url = default_asset_cache.get_url(src)
    return asset_escapers[escape](url)
    


class ThumbnailRenderer(object):

    """Renders a thumbnail object."""
    
    def __init__(self, thumbnail, alt, attrs):
        """Initializes the renderer."""
        self._thumbnail = thumbnail
        self.width = thumbnail.width
        self.height = thumbnail.height
        self.url = thumbnail.url
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
def img(src, width=None, height=None, alt="", **attrs):
    """Renders an image tag."""
    thumbnail = default_thumbnail_cache.get_thumbnail(
        src,
        width = width,
        height = height,
    )
    return ThumbnailRenderer(thumbnail, alt, attrs)
    
    
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
    
    
@parameter_tag(register, takes_context=True)
def script(context, src):
    """Renders one or more script tags."""
    return ScriptRenderer(default_javascript_cache.get_urls((src,))[0])
    
    
@parameter_tag(register, takes_context=True, takes_body=True)
def compress(context, body):
    """Joins and compresses all contained assets."""
    return body.render(context)