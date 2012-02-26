"""Tests for the asset cache."""

import os.path, hashlib

from django.test import TestCase
from django.utils.unittest import skipUnless
from django.contrib.staticfiles import finders
from django.core.files.base import File
from django.core.files.storage import default_storage

from optimizations.assetcache import default_asset_cache, StaticAsset, FileAsset, staticfiles_storage


def get_test_asset():
    # Pick a random asset.
    for finder in finders.get_finders():
        for path, storage in finder.list(()):
            if getattr(storage, "prefix", None):
                path = os.path.join(storage.prefix, path)
            asset = StaticAsset(path)
            try:
                default_asset_cache.get_name(asset)
            except:
                continue
            else:
                return asset
    return None


skipUnlessTestAsset = skipUnless(get_test_asset(), "No static assets could be found in the static files storage.")


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