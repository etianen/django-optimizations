"""Template tags used for optimizing assets."""

import re

from django import template

from optimizations.thumbnailcache import default_thumbnail_cache


register = template.Library()


RE_KWARG = re.compile(u"([a-z][a-z0-9_]*)=(.*)", re.IGNORECASE)


def parse_token(token):
    """Parses the given token into a tuple of (args, kwargs and alias)."""
    parts = token.split_contents()[1:]
    args = []
    kwargs = {}
    # Parse the alias.
    if len(parts) >= 2 and parts[-2] == "as":
        alias = parts[-1]
        parts = parts[:-2]
    else:
        alias = None
    # Parse the args.
    parts_iter = iter(parts)
    for part in parts_iter:
        kwarg_match = RE_KWARG.match(part)
        if kwarg_match:
            kwargs[kwarg_match.group(1)] = template.Variable(kwarg_match.group(2))
        else:
            if kwargs:
                raise template.TemplateSyntaxError("Keyword arguments cannot follow position arguments")
            args.append(template.Variable(part))
    # All done!
    return args, kwargs, alias


class ThumbnailNode(template.Node):

    """A node used to render a thumbnail."""
    
    def __init__(self, alias, src, **attrs):
        """Initializes the thumbnail node."""
        self._alias = alias
        self._thumbnail_var = src
        self._attr_vars = attrs
        
    def render(self, context):
        """Renders the thumbnail node."""
        # Resolve the variables.
        thumbnail_asset = self._thumbnail_var.resolve(context)
        attrs = {
            name: variable.resolve(context)
            for name, variable
            in self._attr_vars.iteritems()
        }
        # Create the thumbnail.
        thumbnail = default_thumbnail_cache.get_thumbnail(
            thumbnail_asset,
            width = attrs.pop("width", None),
            height = attrs.pop("height", None),
        )
        # Response to alias.
        if self._alias:
            context[self._alias] = thumbnail
            return ""
        # Render the thumbnail.
        return template.loader.render_to_string("assets/img.html", {
            "url": thumbnail.url,
            "width": thumbnail.width,
            "height": thumbnail.height,
            "alt": attrs.pop("alt", ""),
            "attrs": attrs,
        })
    

@register.tag
def img(parser, token):
    """Renders an image tag."""
    args, kwargs, alias = parse_token(token)
    return ThumbnailNode(alias, *args, **kwargs)