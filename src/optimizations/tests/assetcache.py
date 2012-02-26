"""Tests for the asset cache."""

import os.path, hashlib

from django.test import TestCase
from django.utils.unittest import skipUnless
from django.contrib.staticfiles import finders
from django.core.files.base import File

from optimizations.assetcache import default_asset_cache, StaticAsset, FileAsset


def get_test_asset():
    # Pick a random asset.
    for finder in finders.get_finders():
        for path, storage in finder.list(()):
            if getattr(storage, "prefix", None):
                path = os.path.join(storage.prefix, path)
            asset = StaticAsset(path)
            try:
                default_asset_cache.get_path(asset)
            except:
                continue
            else:
                return asset
    return None


skipUnlessTestAsset = skipUnless(get_test_asset(), "No static assets could be found on the local STATIC ROOT.")


class AssetCacheTest(TestCase):
    
    @skipUnlessTestAsset
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
    
    @skipUnlessTestAsset
    def testStaticAsset(self):
        self.assertAssetWorks(get_test_asset())
    
    @skipUnlessTestAsset    
    def testFileAsset(self):
        asset = FileAsset(File(open(get_test_asset().get_path(), "rb")))
        self.assertAssetWorks(asset)