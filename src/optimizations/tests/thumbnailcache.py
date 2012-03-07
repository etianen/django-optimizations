"""Tests for the asset cache."""

import hashlib

from django.test import TestCase
from django.core.files.storage import default_storage

from optimizations.assetcache import default_asset_cache
from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.tests.base import skipUnlessTestThumbnailAsset, get_test_thumbnail_asset


class ThumbnailCacheTest(TestCase):
    
    @skipUnlessTestThumbnailAsset
    def testImageCacheForSameSizeImageLeavesImageUnmodified(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "resize")
        self.assertEqual(thumbnail.width, width)
        self.assertEqual(thumbnail.height, height)
        # Make sure the assets are identical.
        self.assertEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())
        
    @skipUnlessTestThumbnailAsset
    def testImageCacheResizeSmaller(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width /= 2
        height /= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "resize")
        self.assertEqual(thumbnail.width, width)
        self.assertEqual(thumbnail.height, height)
        # Make sure the file contents are not identical.
        self.assertNotEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())
        
    @skipUnlessTestThumbnailAsset
    def testImageCacheResizeLarger(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width *= 2
        height *= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "resize")
        self.assertEqual(thumbnail.width, width)
        self.assertEqual(thumbnail.height, height)
        # Make sure the file contents are identical.
        self.assertEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())
        
    @skipUnlessTestThumbnailAsset
    def testImageCacheCrop(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width /= 3
        height /= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "crop")
        self.assertEqual(thumbnail.width, width)
        self.assertEqual(thumbnail.height, height)
        # Make sure the file contents are not identical.
        self.assertNotEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())
        
    @skipUnlessTestThumbnailAsset
    def testImageCacheThumbnailSmaller(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width /= 3
        height /= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "proportional")
        self.assertEqual(thumbnail.width, width)
        self.assertNotEqual(thumbnail.height, height)
        # Make sure the file contents are not identical.
        self.assertNotEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())
        
    @skipUnlessTestThumbnailAsset
    def testImageCacheThumbnailLarger(self):
        asset, image_size = get_test_thumbnail_asset()
        width, height = image_size
        width *= 3
        height *= 2
        thumbnail = default_thumbnail_cache.get_thumbnail(asset, width, height, "proportional")
        self.assertNotEqual(thumbnail.width, width)
        self.assertEqual(thumbnail.height, height)
        # Make sure the file contents are not identical.
        self.assertEqual(hashlib.sha1(default_storage.open(default_asset_cache.get_name(asset)).read()).hexdigest(), hashlib.sha1(default_storage.open(default_asset_cache.get_name(thumbnail._asset)).read()).hexdigest())