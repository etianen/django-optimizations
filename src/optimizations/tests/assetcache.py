"""Tests for the asset cache."""

import random, os.path, hashlib

from django.test import TestCase
from django.contrib.staticfiles import finders
from django.core.files.base import File

from optimizations.assetcache import default_asset_cache, StaticAsset, FileAsset


class AssetCacheTest(TestCase):

    def setUp(self):
        # Pick a random asset.
        assets = []
        for finder in finders.get_finders():
            assets.extend(finder.list(()))
        path, storage = random.choice(assets)
        if getattr(storage, 'prefix', None):
            path = os.path.join(storage.prefix, path)
        self.static_asset = StaticAsset(path)
    
    def assertAssetWorks(self, asset):
        # Does the path exist?
        path = default_asset_cache.get_path(asset)
        self.assertTrue(os.path.exists(path))
        # Is the path different?
        self.assertNotEqual(path, asset.get_path())
        # Has the asset been copied successfully?
        with open(path, "rb") as handle1, open(asset.get_path(), "rb") as handle2:
            self.assertEqual(hashlib.sha1(handle1.read()).hexdigest(), hashlib.sha1(handle2.read()).hexdigest())
        # Does the URL work?
        self.assertTrue(default_asset_cache.get_url(asset).endswith(default_asset_cache.get_name(asset)))
    
    def testStaticAsset(self):
        self.assertAssetWorks(self.static_asset)
        
    def testFileAsset(self):
        asset = FileAsset(File(open(self.static_asset.get_path(), "rb")))
        self.assertAssetWorks(asset)