"""A programmatic compiler of static assets."""

import abc

from optimizations.assetcache import StaticAsset


class AssetCompilerPluginRegistrationError(Exception):
    
    """An error occured while registering asset compiler plugins."""


class AssetCompilerPluginBase(object):
    
    """Base class for asset compiler plugins."""
    
    __metaclass__ = abc.ABCMeta
    
    asset_type = "various"
    
    @abc.abstractmethod
    def compile_assets(self, assets):
        """Compiles the given assets."""
        raise NotImplementedError


class AssetCompiler(object):
    
    """A programmatic compiler of static assets."""
    
    def __init__(self):
        """Initializes the asset compiler."""
        self._plugins = {}
        
    # Registration.
    
    def register_plugin(self, name, plugin):
        """Registers the given plugin with the asset compiler."""
        if name in self._plugins:
            raise AssetCompilerPluginRegistrationError("{name} is already registered with this asset compiler.".format(name=name))
        if not isinstance(plugin, AssetCompilerPluginBase):
            raise AssetCompilerPluginRegistrationError("{plugin} is not an instance of AssetCompilerPluginBase.".format(plugin=plugin))
        self._plugins[name] = plugin
        
    def unregister_plugin(self, name):
        """Unregisters the given plugin."""
        try:
            del self._plugins[name]
        except KeyError:
            raise AssetCompilerPluginRegistrationError("{name} is already registered with this asset compiler.".format(name=name))
        
    def has_plugin(self, name):
        """Tests whether the given plugin is registered with this asset compiler."""
        return name in self._plugins
    
    # Compilation.
    
    def compile_iter(self, namespace="default"):
        """Iterates over all assets in the given namespace, compiling as it goes."""
        for plugin_name, plugin in self._plugins.iteritems():
            assets = StaticAsset.load(plugin_name, namespace)
            plugin.compile_assets(assets)
            yield plugin, assets
    
    def compile(self, namespace="default"):
        """Compiles all assets in the given namespace."""
        return list(self.compile_iter(namespace))


# A shared, global asset compiler.
default_asset_compiler = AssetCompiler()