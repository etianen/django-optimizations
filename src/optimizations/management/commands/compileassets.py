"""Compiles the stylesheet assets in this project."""

from django.core.management.base import NoArgsCommand

from optimizations.assetcache import StaticAsset
from optimizations.assetcompiler import default_asset_compiler


class Command(NoArgsCommand):
    
    help = "Compiles the static assets in this project."
    
    def handle(self, **options):
        verbosity = int(options.get("verbosity", 1))
        # Run the compiler.
        for namespace in StaticAsset.get_namespaces():
            if verbosity >= 2:
                self.stdout.write("Compiling assets in {namespace} namespace...".format(namespace=namespace))
                self.stdout.flush()
            try:
                default_asset_compiler.compile(namespace)
            except Exception as ex:
                if hasattr(ex, "detail_message"):
                    self.stdout.write("\n{}\n".format(ex.detail_message))
                raise
            else:
                if verbosity >= 2:
                    self.stdout.write(" done!\n")