"""Template tags used by django-optimizations."""

import re
from functools import wraps

from django import template


RE_KWARG = re.compile(u"([a-z][a-z0-9_]*)=(.*)", re.IGNORECASE)


def parse_token(token):
    """Parses the given token into a tuple of (args, kwargs and alias)."""
    parts = token.split_contents()[1:]
    args = []
    kwargs = {}
    # Parse the alias.
    if len(parts) >= 2 and parts[-2] == "as":
        alias = parts[-1]
        parts = parts[:-2]
    else:
        alias = None
    # Parse the args.
    parts_iter = iter(parts)
    for part in parts_iter:
        kwarg_match = RE_KWARG.match(part)
        if kwarg_match:
            kwargs[kwarg_match.group(1)] = template.Variable(kwarg_match.group(2))
        else:
            if kwargs:
                raise template.TemplateSyntaxError("Keyword arguments cannot follow position arguments")
            args.append(template.Variable(part))
    # All done!
    return args, kwargs, alias


class ParameterNode(template.Node):

    """A node for a paramter tag."""
    
    def __init__(self, takes_context, func, args, kwargs, alias):
        """Initializes the parameter node."""
        self._takes_context = takes_context
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._alias = alias
        
    def render(self, context):
        """Renders the parameter node."""
        # Resolve all variables.
        args = [arg.resolve(context) for arg in self._args]
        kwargs = {
            name: value.resolve(context)
            for name, value
            in self._kwargs.iteritems()
        }
        # Add in the context.
        if self._takes_context:
            args.insert(0, context)
        # Run the tag.
        result = self._func(*args, **kwargs)
        # Alias if required.
        if self._alias:
            context[self._alias] = result
            return ""
        # Render the result.
        return unicode(result)
    
    
def parameter_tag(takes_context=False):
    """A decorator for a function that should be converted to a parameter tag."""
    def decorator(func):
        @wraps(func)
        def compiler(parser, token):
            args, kwargs, alias = parse_token(token)
            return ParameterNode(takes_context, func, args, kwargs, alias)
        return compiler
    # Adapt to no arguments.
    if callable(takes_context):
        func = takes_context
        takes_context = False
        return decorator(func)
    return decorator