"""Tests for the asset cache."""

import os.path, hashlib

from django.test import TestCase
from django.utils.unittest import skipUnless
from django.contrib.staticfiles import finders
from django.core.files.storage import default_storage

from optimizations.assetcache import StaticAsset, default_asset_cache
from optimizations.thumbnailcache import open_image, default_thumbnail_cache


def get_test_thumbnail_asset():
    # Pick a random asset.
    for finder in finders.get_finders():
        for path, storage in finder.list(()):
            lower_path = path.lower()
            if lower_path.endswith(".jpg") or lower_path.endswith(".jpeg") or lower_path.endswith(".png"):
                if getattr(storage, "prefix", None):
                    path = os.path.join(storage.prefix, path)
                asset = StaticAsset(path)
                try:
                    image_size = open_image(asset).size
                except:
                    continue
                else:
                    return asset, image_size
    return None


skipUnlessTestThumbnailAsset = skipUnless(get_test_thumbnail_asset(), "No static image assets could be found in the static files storage.")


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