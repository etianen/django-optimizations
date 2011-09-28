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
    
    def __init__(self, takes_context, func, args, kwargs, alias, body):
        """Initializes the parameter node."""
        self._takes_context = takes_context
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._alias = alias
        self._body = body
        
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
        # Add in the body.
        if self._body is not None:
            kwargs["body"] = self._body
        # Run the tag.
        result = self._func(*args, **kwargs)
        # Alias if required.
        if self._alias:
            context[self._alias] = result
            return ""
        # Render the result.
        return unicode(result)
    
    
def parameter_tag(register, takes_context=False, takes_body=False):
    """A decorator for a function that should be converted to a parameter tag."""
    def decorator(func):
        @register.tag
        @wraps(func)
        def compiler(parser, token):
            # Parse the token.
            args, kwargs, alias = parse_token(token)
            # Parse the body.
            if takes_body:
                end_tag_name = u"end{name}".format(name=func.__name__)
                body = parser.parse((end_tag_name,))
                parser.delete_first_token()
            else:
                body = None
            # Create the parameter node.
            return ParameterNode(takes_context, func, args, kwargs, alias, body)
        return compiler
    return decorator
    
    
def template_tag(register, template_name, takes_context=False):
    """A decorator for a function that should be converted into a template tag."""
    def decorator(func):
        @parameter_tag(register, takes_context=True)
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
        return do_template_tag
    return decorator