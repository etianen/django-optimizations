"""Compiles the javascript assets in this project."""

import logging

from django.core.management.base import NoArgsCommand
from django.conf import settings

from optimizations.javascriptcache import default_javascript_cache, JavascriptError


logger = logging.getLogger("optimizations.javascript")


class Command(NoArgsCommand):
    
    help = "Compiles the javascript assets in this project."
    
    def handle(self, **options):
        verbosity = int(options.get("verbosity", 1))
        # Configure the handler.
        if verbosity > 0:
            handler = logging.StreamHandler()
            if verbosity >= 3:
                handler.setLevel(logging.INFO)
            elif verbosity == 2:
                handler.setLevel(logging.WARNING)
            elif verbosity == 1:
                handler.setLevel(logging.ERROR)
            handler.setFormatter(logging.Formatter(u"Line %(jslineno)s: %(error)s"))
            logger.addHandler(handler)
        # Run the compiler.
        for asset_group in getattr(settings, "ASSETS", {}).iterkeys():
            try:
                default_javascript_cache.get_urls(asset_group, compile=True, force_save=True, fail_silently=False)
            except JavascriptError:
                # The errors have already been logged, so nothing to do here.
                pass