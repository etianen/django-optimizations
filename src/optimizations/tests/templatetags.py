"""Tests for the template tags."""

from django.test import TestCase
from django.template import Template, Context

from optimizations.assetcache import default_asset_cache
from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.javascriptcache import default_javascript_cache
from optimizations.tests.base import skipUnlessTestAsset, get_test_asset, skipUnlessTestThumbnailAsset, get_test_thumbnail_asset, skipUnlessTestStylesheetAsset, get_test_stylesheet_asset, skipUnlessTestJavascriptAsset, get_test_javascript_asset
from optimizations.stylesheetcache import default_stylesheet_cache


class OptimizationsTemplateTagsTest(TestCase):
    
    @skipUnlessTestAsset
    def testAssetTag(self):
        asset = get_test_asset()
        url = default_asset_cache.get_url(asset)
        self.assertEqual(
            Template("{% load assets %}{% asset asset %}").render(Context({
                "asset": asset,
            })),
            url,
        )
        
    @skipUnlessTestAsset
    def testGetAssetTag(self):
        asset = get_test_asset()
        url = default_asset_cache.get_url(asset)
        self.assertEqual(
            Template("{% load assets %}{% get_asset asset as asset_url %}{{asset_url}}").render(Context({
                "asset": asset,
            })),
            url,
        )
        
    @skipUnlessTestThumbnailAsset
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
            u'<img src="{src}" width={width} height={height} alt="">'.format(
                src = thumbnail.url,
                width = thumbnail.width,
                height = thumbnail.height,
            ),
        )
        
    @skipUnlessTestThumbnailAsset
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
            u'{src}:{width}:{height}'.format(
                src = thumbnail.url,
                width = thumbnail.width,
                height = thumbnail.height,
            ),
        )
        
    @skipUnlessTestStylesheetAsset
    def testStylesheetTag(self):
        stylesheet = get_test_stylesheet_asset()
        urls = default_stylesheet_cache.get_urls((stylesheet,))
        self.assertEqual(
            Template("{% load assets %}{% stylesheet stylesheet %}").render(Context({
                "stylesheet": stylesheet,
            })),
            u'<link rel="stylesheet" href="{url}">'.format(
                url = urls[0],
            ),
        )
        
    @skipUnlessTestJavascriptAsset
    def testScriptTag(self):
        script = get_test_javascript_asset()
        urls = default_javascript_cache.get_urls((script,))
        self.assertEqual(
            Template("{% load assets %}{% script script %}").render(Context({
                "script": script,
            })),
            u'<script src="{url}"></script>'.format(
                url = urls[0],
            ),
        )
        
    def testScripTagAbsoluteUrl(self):
        self.assertEqual(
            Template("{% load assets %}{% script 'http://www.example.com/example.js' %}").render(Context({})),
            u'<script src="http://www.example.com/example.js"></script>',
        )