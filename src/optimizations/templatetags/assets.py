"""Template tags used for optimizing assets."""

from urlparse import urlparse

from django import template
from django.utils.html import escape

from optimizations.assetcache import StaticAsset, default_asset_cache, AdaptiveAsset
from optimizations.thumbnailcache import default_thumbnail_cache, PROPORTIONAL
from optimizations.javascriptcache import default_javascript_cache
from optimizations.stylesheetcache import default_stylesheet_cache
from optimizations.templatetags import simple_tag, inclusion_tag, assignment_tag


register = template.Library()


@simple_tag(register)
def asset(src):
    """Returns the cached asset URL of the given asset."""
    url = default_asset_cache.get_url(src)
    return escape(url)


@assignment_tag(register)
def get_asset(src):
    return default_asset_cache.get_url(src)
    

@inclusion_tag(register, "assets/img.html")
@assignment_tag(register, name="get_img")
def img(src, width=None, height=None, method=PROPORTIONAL, alt="", **attrs):
    """Renders an image tag."""
    params = {
        "alt": alt,
        "attrs": attrs,
    }
    try:
        thumbnail = default_thumbnail_cache.get_thumbnail(
            src,
            width = width,
            height = height,
            method = method,
        )
    except IOError:
        asset = AdaptiveAsset(src)
        params.update({
            "url": asset.get_url(),
            "width": width or "",
            "height": height or "",
        })
    else:
        params.update({
            "url": thumbnail.url,
            "width": thumbnail.width,
            "height": thumbnail.height,
            
        })
    return params


def resolve_script_src(src):
    """Resolves the given src attribute of the script."""
    if isinstance(src, basestring):
        src_parts = urlparse(src)
        if src_parts.scheme or src_parts.netloc:
            return (src,)
    assets = StaticAsset.load("js", src)
    return default_javascript_cache.get_urls(assets)
    
    
@inclusion_tag(register, "assets/script.html")
def script(src="default", **attrs):
    """Renders one or more script tags."""
    urls = resolve_script_src(src)
    return {
        "urls": urls,
        "attrs": attrs,
    }
    
    
@inclusion_tag(register, "assets/script_async.html")
def script_async(src="default"):
    """Renders an asyncronously-loading script tag."""
    urls = resolve_script_src(src)
    return {
        "urls": urls,
    }
    
    
@inclusion_tag(register, "assets/stylesheet.html")
def stylesheet(href="default", **attrs):
    """Renders one or more stylesheet tags."""
    assets = StaticAsset.load("css", href)
    urls = default_stylesheet_cache.get_urls(assets)
    return {
        "urls": urls,
        "attrs": attrs,
    }