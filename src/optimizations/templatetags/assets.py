"""Template tags used for optimizing assets."""

import os.path, glob

from django import template
from django.utils.html import escape, escapejs
from django.contrib.staticfiles.finders import find as find_static_path
from django.conf import settings

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
    assets = getattr(settings, "ASSETS", {}).get(src)
    if assets:
        # Get the script list.
        scripts = list(assets.get("scripts", ()))
        # Process the script dir.
        script_dir = assets.get("script_dir")
        if script_dir:
            if settings.DEBUG:
                script_path = find_static_path(script_dir)
            else:
                script_path = os.path.join(settings.STATIC_ROOT, script_dir)
            scripts.extend(
                os.path.join(script_dir, os.path.relpath(path, script_path))
                for path in glob.iglob(os.path.join(script_path, "*.js"))
            )
    else:
        scripts = (src,)
    return MultiScriptRenderer(default_javascript_cache.get_urls(scripts))