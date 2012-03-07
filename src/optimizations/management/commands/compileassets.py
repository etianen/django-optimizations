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
            try:
                for plugin, assets in default_asset_compiler.compile_iter(namespace):
                    if verbosity >= 2:
                        self.stdout.write("Compiled {asset_type} assets in {namespace} namespace\n".format(
                            asset_type = plugin.asset_type,
                            namespace = namespace,
                        ))
                    if verbosity >= 3:
                        for asset in assets:
                            self.stdout.write(" - {asset}\n".format(
                                asset = asset.get_name(),
                            ))
            except Exception as ex:
                if hasattr(ex, "detail_message"):
                    self.stdout.write("\n{}\n".format(ex.detail_message))
                raise
            else:
                if verbosity == 1:
                    self.stdout.write("Compiled assets in {namespace} namespace\n".format(namespace=namespace))