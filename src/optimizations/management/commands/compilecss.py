"""Compiles the stylesheet assets in this project."""

import logging

from django.core.management.base import NoArgsCommand
from django.conf import settings

from optimizations.assetcache import StaticAsset
from optimizations.stylesheetcache import default_stylesheet_cache


logger = logging.getLogger("optimizations.stylesheet")


class Command(NoArgsCommand):
    
    help = "Compiles the stylesheet assets in this project."
    
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
        for namespace in StaticAsset.get_namespaces():
            assets = StaticAsset.load("css", namespace);
            default_stylesheet_cache.get_urls(assets, compile=True, force_save=True)
            if verbosity >= 1:
                self.stdout.write("Compiled css in namespace {!r}.\n".format(namespace))