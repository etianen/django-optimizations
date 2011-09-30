"""Compiles the javascript assets in this project."""

import logging

from django.core.management.base import NoArgsCommand
from django.conf import settings

from optimizations.javascriptcache import default_javascript_cache


logger = logging.getLogger("optimizations.javascript")


class Command(NoArgsCommand):
    
    help = "Compiles the javascript assets in this project."
    
    def handle(self, **options):
        verbosity = int(options.get("verbosity", 1))
        # Run the compiler.
        for asset_group in getattr(settings, "ASSETS", {}).iterkeys():
            default_javascript_cache.get_urls(asset_group, compile=True, force_save=True)