"""Tests for the template tags."""

from django.test import TestCase
from django.template import Template, Context

from optimizations.assetcache import default_asset_cache
from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.javascriptcache import default_javascript_cache
from test_optimizations.tests.base import get_test_asset, get_test_thumbnail_asset, get_test_stylesheet_asset, get_test_javascript_asset
from optimizations.stylesheetcache import default_stylesheet_cache


class OptimizationsTemplateTagsTest(TestCase):
    
    def testAssetTag(self):
        asset = get_test_asset()
        url = default_asset_cache.get_url(asset)
        self.assertEqual(
            Template("{% load assets %}{% asset asset %}").render(Context({
                "asset": asset,
            })),
            url,
        )
        
    def testGetAssetTag(self):
        asset = get_test_asset()
        url = default_asset_cache.get_url(asset)
        self.assertEqual(
            Template("{% load assets %}{% get_asset asset as asset_url %}{{asset_url}}").render(Context({
                "asset": asset,
            })),
            url,
        )
        
    def testImgTag(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width /= 2
        height /= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "resize")
        self.assertEqual(
            Template("{% load assets %}{% img asset width=width height=height method='resize' %}").render(Context({
                "asset": asset,
                "width": width,
                "height": height,
            })),
            '<img src="{src}" width={width} height={height} alt="">'.format(
                src = thumbnail.url,
                width = thumbnail.width,
                height = thumbnail.height,
            ),
        )
        
    def testGetImgTag(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width /= 2
        height /= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "resize")
        self.assertEqual(
            Template("{% load assets %}{% get_img asset width=width height=height method='resize' as img %}{{img.url}}:{{img.width}}:{{img.height}}").render(Context({
                "asset": asset,
                "width": width,
                "height": height,
            })),
            '{src}:{width}:{height}'.format(
                src = thumbnail.url,
                width = thumbnail.width,
                height = thumbnail.height,
            ),
        )
        
    def testStylesheetTag(self):
        stylesheet = get_test_stylesheet_asset()
        urls = default_stylesheet_cache.get_urls((stylesheet,))
        self.assertEqual(
            Template("{% load assets %}{% stylesheet stylesheet %}").render(Context({
                "stylesheet": stylesheet,
            })),
            '<link rel="stylesheet" href="{url}">'.format(
                url = urls[0],
            ),
        )
        
    def testScriptTag(self):
        script = get_test_javascript_asset()
        urls = default_javascript_cache.get_urls((script,))
        self.assertEqual(
            Template("{% load assets %}{% script script %}").render(Context({
                "script": script,
            })),
            '<script src="{url}"></script>'.format(
                url = urls[0],
            ),
        )
        
    def testScripTagAbsoluteUrl(self):
        self.assertEqual(
            Template("{% load assets %}{% script 'http://www.example.com/example.js' %}").render(Context({})),
            '<script src="http://www.example.com/example.js"></script>',
        )
