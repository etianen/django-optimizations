"""
Optimizations for the django web framework.

Developed by Dave Hall.

<http://www.etianen.com/>
"""

from optimizations.propertycache import cached_property
from optimizations.assetcache import default_asset_cache
from optimizations.thumbnailcache import default_thumbnail_cache
from optimizations.stylesheetcache import default_stylesheet_cache
from optimizations.javascriptcache import default_javascript_cache


get_url = default_asset_cache.get_url
get_thumbnail = default_thumbnail_cache.get_thumbnail