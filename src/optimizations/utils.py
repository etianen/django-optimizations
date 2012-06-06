"""Random utility functions."""

from django.core.cache import get_cache, InvalidCacheBackendError, cache as default_cache


def resolve_namespaced_cache(name):
    """Finds the best-matching named cache that exists."""
    try:
        return get_cache(name)
    except (InvalidCacheBackendError, ValueError):
        if "." in name:
            return resolve_namespaced_cache(name.rsplit(".", 1)[0])
        return default_cache