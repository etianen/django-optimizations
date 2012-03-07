"""Template tags used by django-optimizations."""

from functools import wraps

from django import template


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


def template_tag(register, template_name, takes_context=False, name=None):
    """Annotation for a scoped Django-1.4 style inclusion tag."""
    def decorator(func):
        @simple_tag(register, takes_context=True, name=name)
        @wraps(func)
        def do_template_tag(context, *args, **kwargs):
            # Apply the context.
            if takes_context:
                args = [context] + list(args)
            # Run the tag handler.
            params = func(*args, **kwargs)
            # Render the template.
            context.push()
            try:
                context.update(params)
                return template.loader.render_to_string(template_name, context)
            finally:
                context.pop()
        return func
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