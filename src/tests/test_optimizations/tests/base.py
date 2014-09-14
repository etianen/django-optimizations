"""Base test helpers."""

import os.path
from functools import partial

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


get_test_javascript_asset = partial(get_test_asset, ".js")


get_test_stylesheet_asset = partial(get_test_asset, ".css")


def get_test_thumbnail_asset():
    for asset in iter_test_assets((".jpg", ".jpeg", ".png")):
        try:
            image_size = open_image(asset).size
        except:
            continue
        else:
            return asset, image_size
    return None
