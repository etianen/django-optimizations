"""Template tags used for optimizing assets."""

from urlparse import urlparse

from django import template
from django.utils.html import escape

from optimizations.assetcache import StaticAsset, default_asset_cache, AdaptiveAsset
from optimizations.thumbnailcache import default_thumbnail_cache, PROPORTIONAL, ThumbnailError
from optimizations.javascriptcache import default_javascript_cache
from optimizations.stylesheetcache import default_stylesheet_cache
from optimizations.templatetags import simple_tag, inclusion_tag, assignment_tag
from optimizations.videocache import default_video_cache, PROPORTIONAL as VIDEO_PROPORTIONAL, JPEG_FORMAT, VideoError


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
    except ThumbnailError:
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


@inclusion_tag(register, "assets/img.html")
@assignment_tag(register, name="get_video_img")
def video_img(src, width, height, method=VIDEO_PROPORTIONAL, alt="", **attrs):
    """Renders an image tag from the given video."""
    params = {
        "alt": alt,
        "attrs": attrs,
        "width": width,
        "height": height,
    }
    try:
        url = default_video_cache.get_url(src, width, height, method, format=JPEG_FORMAT)
    except VideoError:
        asset = AdaptiveAsset(src)
        url = asset.get_url()
    params["url"] = url
    return params


def is_url(s):
    """Checks if the given string is a URL."""
    if not isinstance(s, basestring):
        return False
    src_parts = urlparse(s)
    return src_parts.scheme or src_parts.netloc


def resolve_script_src(src, _src):
    """Resolves the given src attribute of the script."""
    all_src = (src,) + _src
    src_urls = filter(is_url, all_src)
    if src_urls:
        if len(src_urls) == len(all_src):
            return all_src  # All are URLs, which is allowed.
        else:
            raise ValueError("Mixed assets and absolute URLs are not allowed in script tags.")
    assets = StaticAsset.load("js", all_src)
    return default_javascript_cache.get_urls(assets)
    
    
@inclusion_tag(register, "assets/script.html")
def script(src="default", *_src, **attrs):
    """Renders one or more script tags."""
    urls = resolve_script_src(src, _src)
    return {
        "urls": urls,
        "attrs": attrs,
    }
    
    
@inclusion_tag(register, "assets/script_async.html")
def script_async(src="default", *_src):
    """Renders an asyncronously-loading script tag."""
    urls = resolve_script_src(src, _src)
    return {
        "urls": urls,
    }
    
    
@inclusion_tag(register, "assets/stylesheet.html")
def stylesheet(href="default", *_href, **attrs):
    """Renders one or more stylesheet tags."""
    compile = attrs.pop("compile", True)
    all_href = (href,) + _href
    href_urls = filter(is_url, all_href)
    if href_urls:
        if len(href_urls) == len(all_href):
            urls = all_href  # All are URLs, which is allowed.
        else:
            raise ValueError("Mixed assets and absolute URLs are not allowed in stylesheet tags.")
    else:
        assets = StaticAsset.load("css", all_href)
        urls = default_stylesheet_cache.get_urls(assets, compile=compile)
    return {
        "urls": urls,
        "attrs": attrs,
    }