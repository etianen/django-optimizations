"""Template tags used for optimizing assets."""

from django import template

from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.templatetags import parameter_tag


register = template.Library()


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