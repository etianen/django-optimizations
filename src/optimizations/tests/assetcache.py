"""Tests for the asset cache."""

import random, os.path, hashlib

from django.test import TestCase
from django.contrib.staticfiles import finders

from optimizations.assetcache import default_asset_cache, StaticAsset


class StaticAssetTest(TestCase):

    def setUp(self):
        # Pick a random asset.
        assets = []
        for finder in finders.get_finders():
            assets.extend(finder.list(()))
        path, storage = random.choice(assets)
        if hasattr(storage, "prefix"):
            path = os.path.join(storage.prefix, path)
        self.asset = StaticAsset(path)
                
    def testStaticAsset(self):
        # Does the path exist?
        path = default_asset_cache.get_path(self.asset)
        self.assertTrue(os.path.exists(path))
        # Is the path different?
        self.assertNotEqual(path, self.asset.get_path())
        # Has the asset been copied successfully?
        with open(path, "rb") as handle1, open(self.asset.get_path(), "rb") as handle2:
            self.assertEqual(hashlib.sha1(handle1.read()).hexdigest(), hashlib.sha1(handle2.read()).hexdigest())
        # Does the URL work?
        self.assertTrue(default_asset_cache.get_url(self.asset).endswith(default_asset_cache.get_name(self.asset)))