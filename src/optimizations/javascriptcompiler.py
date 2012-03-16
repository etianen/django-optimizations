"""A general-purpose javascript compiler."""

import os.path, subprocess

from django.conf import settings

import optimizations


class JavascriptError(Exception):
    
    """Something went wrong with javascript compilation."""
    
    def __init__(self, message, detail_message):
        """Initializes the javascript error."""
        super(JavascriptError, self).__init__(message)
        self.detail_message = detail_message


class JavascriptCompiler(object):
    
    """A compiler of javascript code."""
    
    def __init__(self, cache_name="optimizations.javascriptcompiler"):
        """Initializes the JavascriptCompiler."""
        self._compressor_path = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
        
    def compile(self, source, force_compile=None):
        """Compiles the given javascript source code."""
        if force_compile is None:
            force_compile = not settings.DEBUG
        # Convert to string.
        if isinstance(source, unicode):
            source = source.encode("utf-8")
        # Don't compile in debug mode.
        if not force_compile:
            return source
        # Compile the source.
        process = subprocess.Popen(
            ("java", "-jar", self._compressor_path, "--type", "js", "--charset", "utf-8", "-v"),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
        )
        stdoutdata, stderrdata = process.communicate(source)
        # Check it all worked.
        if process.returncode != 0:
            raise JavascriptError("Error while compiling javascript.", stderrdata)
        return stdoutdata
    
    
default_javascript_compiler = JavascriptCompiler()