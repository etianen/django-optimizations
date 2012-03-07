"""Tests for the asset cache."""

import hashlib

from django.test import TestCase
from django.core.files.base import File
from django.core.files.storage import default_storage

from optimizations.assetcache import default_asset_cache, FileAsset, staticfiles_storage
from optimizations.tests.base import skipUnlessTestAsset, get_test_asset


class AssetCacheTest(TestCase):
    
    @skipUnlessTestAsset
    def assertAssetWorks(self, asset):
        # Does the path exist?
        name = default_asset_cache.get_name(asset)
        self.assertTrue(default_storage.exists(name))
        # Is the name different?
        self.assertNotEqual(name, asset.get_name())
        # Has the asset been copied successfully?
        self.assertEqual(hashlib.sha1(staticfiles_storage.open(asset.get_name()).read()).hexdigest(), hashlib.sha1(default_storage.open(name).read()).hexdigest())
    
    @skipUnlessTestAsset
    def testStaticAsset(self):
        self.assertAssetWorks(get_test_asset())
    
    @skipUnlessTestAsset    
    def testFileAsset(self):
        asset = FileAsset(File(open(get_test_asset().get_path(), "rb")))
        self.assertAssetWorks(asset)