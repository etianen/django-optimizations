"""Compatibility shims for the Django 1.4 template tag helpers."""

import re
from functools import wraps

from django import template


RE_KWARG = re.compile(u"([a-z][a-z0-9_]*)=(.*)", re.IGNORECASE)


def parse_token(parser, token):
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
            kwargs[kwarg_match.group(1)] = parser.compile_filter(kwarg_match.group(2))
        else:
            if kwargs:
                raise template.TemplateSyntaxError("Positional arguments cannot follow keyword arguments")
            args.append(parser.compile_filter(part))
    # All done!
    return args, kwargs, alias


class CompatibilityNode(template.Node):

    """A node for the compatibility tags."""
    
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
        kwargs = dict(
            (name, value.resolve(context))
            for name, value
            in self._kwargs.iteritems()
        )
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
    

def simple_tag_compat(register, takes_context, func, name):
    """Compatibility shim for the Django 1.4 simple tab."""
    @register.tag(name=name)
    @wraps(func)
    def compiler(parser, token):
        args, kwargs, alias = parse_token(parser, token)
        if alias:
            raise template.TemplateSyntaxError("Alias not allowed for simple_tag")
        return CompatibilityNode(takes_context, func, args, kwargs, alias)
    return func


def inclusion_tag_compat(register, file_name, takes_context, func, name):
    """Compatibility shim for the Django 1.4 inclusion tab."""
    @wraps(func)
    def do_inclusion_tag_compat(context, *args, **kwargs):
        if takes_context:
            args = (context,) + args
        context_params = func(*args, **kwargs)
        csrf_token = context.get("csrf_token", None)
        if csrf_token is not None:
            context_params["csrf_token"] = csrf_token
        return template.loader.render_to_string(file_name, context_params)
    return simple_tag_compat(register, True, do_inclusion_tag_compat, name)


def assignment_tag_compat(register, takes_context, func, name):
    """Compatibility shim for the Django 1.4 simple tab."""
    @register.tag(name=name)
    @wraps(func)
    def compiler(parser, token):
        args, kwargs, alias = parse_token(parser, token)
        if not alias:
            raise template.TemplateSyntaxError("Alias not provided for assignment_tag")
        return CompatibilityNode(takes_context, func, args, kwargs, alias)
    return func