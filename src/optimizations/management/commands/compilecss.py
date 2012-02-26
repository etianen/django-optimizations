"""Compiles the stylesheet assets in this project."""

import logging

from django.core.management.base import NoArgsCommand

from optimizations.assetcache import StaticAsset
from optimizations.stylesheetcache import default_stylesheet_cache, StylesheetError


logger = logging.getLogger("optimizations.stylesheet")


class Command(NoArgsCommand):
    
    help = "Compiles the stylesheet assets in this project."
    
    def handle(self, **options):
        verbosity = int(options.get("verbosity", 1))
        # Configure the handler.
        handler = logging.StreamHandler(self.stdout)
        if verbosity >= 3:
            handler.setLevel(logging.INFO)
            logger.setLevel(logging.INFO)
        elif verbosity == 2:
            handler.setLevel(logging.WARNING)
            logger.setLevel(logging.WARNING)
        elif verbosity == 1:
            handler.setLevel(logging.ERROR)
            logger.setLevel(logging.ERROR)
        logger.addHandler(handler)
        # Run the compiler.
        for namespace in StaticAsset.get_namespaces():
            assets = StaticAsset.load("css", namespace);
            try:
                default_stylesheet_cache.get_urls(assets, compile=True, force_save=True, fail_silently=False)
            except StylesheetError:
                logger.error("Error when compiling css in namespace {namespace!r}.\n".format(namespace=namespace))
            else:
                logger.info("Compiled css in namespace {namespace!r}.\n".format(namespace=namespace))