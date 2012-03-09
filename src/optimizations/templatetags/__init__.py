"""Template tags used by django-optimizations."""


def simple_tag(register, takes_context=False, name=None):
    """Annotation for a Django 1.4 style simple tag."""
    def decorator(func):
        # Use the django-supplied tag, if available.
        if hasattr(register, "assignment_tag"):
            return register.simple_tag(takes_context=takes_context, name=name)(func)
        # Otherwise, use the compatibility function.
        from optimizations.templatetags._compatibility import simple_tag_compat
        return simple_tag_compat(register, takes_context, func, name)
    return decorator


def inclusion_tag(register, file_name, takes_context=False, name=None):
    """Annotation for a Django 1.4 style inclusion tag."""
    def decorator(func):
        # Use the django-supplied tag, if available.
        if hasattr(register, "assignment_tag"):
            return register.inclusion_tag(file_name, takes_context=takes_context, name=name)(func)
        # Otherwise, use the compatibility function.
        from optimizations.templatetags._compatibility import inclusion_tag_compat
        return inclusion_tag_compat(register, file_name, takes_context, func, name)
    return decorator


def assignment_tag(register, takes_context=False, name=None):
    """Annotation for a Django-1.4 style assignment tag."""
    def decorator(func):
        # Use the django-supplied tag, if available.
        if hasattr(register, "assignment_tag"):
            return register.assignment_tag(takes_context=takes_context, name=name)(func)
        # Otherwise, use the compatibility function.
        from optimizations.templatetags._compatibility import assignment_tag_compat
        return assignment_tag_compat(register, takes_context, func, name)
    return decorator