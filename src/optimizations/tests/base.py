"""Base test helpers."""

import os.path
from functools import partial

from django.utils.unittest import skipUnless
from django.contrib.staticfiles import finders

from optimizations.assetcache import default_asset_cache, StaticAsset
from optimizations.thumbnailcache import open_image


def iter_test_assets(valid_extensions):
    for finder in finders.get_finders():
        for path, storage in finder.list(()):
            extension = os.path.splitext(path)[1].lower()
            if not valid_extensions or extension in valid_extensions:
                if getattr(storage, "prefix", None):
                    path = os.path.join(storage.prefix, path)
                asset = StaticAsset(path)
                try:
                    default_asset_cache.get_name(asset)
                except:
                    continue
                else:
                    yield asset


def get_test_asset(*valid_extensions):
    for asset in iter_test_assets(valid_extensions):
        return asset
    return None


skipUnlessTestAsset = skipUnless(get_test_asset(), "No static assets could be found in the static files storage.")


get_test_javascript_asset = partial(get_test_asset, ".js")
skipUnlessTestJavascriptAsset = skipUnless(get_test_javascript_asset(), "No static javascript assets could be found in the static files storage.")


get_test_stylesheet_asset = partial(get_test_asset, ".css")
skipUnlessTestStylesheetAsset = skipUnless(get_test_stylesheet_asset(), "No static stylesheet assets could be found in the static files storage.")


def get_test_thumbnail_asset():
    for asset in iter_test_assets((".jpg", ".jpeg", ".png")):
        try:
            image_size = open_image(asset).size
        except:
            continue
        else:
            return asset, image_size
    return None
    
    
skipUnlessTestThumbnailAsset = skipUnless(get_test_thumbnail_asset(), "No static image assets could be found in the static files storage.")