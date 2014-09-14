"""Tests for the asset cache."""

import hashlib

from django.test import TestCase
from django.core.files.base import File
from django.core.files.storage import default_storage

from optimizations.assetcache import default_asset_cache, FileAsset, staticfiles_storage
from test_optimizations.tests.base import get_test_asset


class AssetCacheTest(TestCase):
    
    def assertAssetWorks(self, asset, file):
        # Does the path exist?
        name = default_asset_cache.get_name(asset)
        self.assertTrue(default_storage.exists(name))
        # Is the name different?
        self.assertNotEqual(name, asset.get_name())
        # Has the asset been copied successfully?
        self.assertEqual(
            hashlib.sha1(file.read()).hexdigest(),
            hashlib.sha1(default_storage.open(name).read()).hexdigest(),
        )
    
    def testStaticAsset(self):
        asset = get_test_asset()
        self.assertAssetWorks(asset, staticfiles_storage.open(asset.get_name()))
    
    def testFileAsset(self):
        asset = get_test_asset()
        file = open(asset.get_path(), "rb")
        asset = FileAsset(File(open(asset.get_path(), "rb")))
        self.assertAssetWorks(asset, file)
