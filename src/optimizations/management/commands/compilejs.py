"""Compiles the javascript assets in this project."""

import logging

from django.core.management.base import NoArgsCommand

from optimizations.assetcache import StaticAsset
from optimizations.javascriptcache import default_javascript_cache, JavascriptError


logger = logging.getLogger("optimizations.javascript")


class Command(NoArgsCommand):
    
    help = "Compiles the javascript assets in this project."
    
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
            assets = StaticAsset.load("js", namespace);
            try:
                default_javascript_cache.get_urls(assets, compile=True, force_save=True)
            except JavascriptError:
                logger.error("Error while compiling javascript in namespace {namespace!r}.\n".format(namespace=namespace))
            else:
                logger.info("Compiled javascript in namespace {namespace!r}.\n".format(namespace=namespace))