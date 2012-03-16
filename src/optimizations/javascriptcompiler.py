"""A general-purpose javascript compiler."""

import os.path, subprocess

import optimizations


class JavascriptError(Exception):
    
    """Something went wrong with javascript compilation."""
    
    def __init__(self, message, detail_message):
        """Initializes the javascript error."""
        super(JavascriptError, self).__init__(message)
        self.detail_message = detail_message


COMPRESSOR_PATH = os.path.join(os.path.abspath(os.path.dirname(optimizations.__file__)), "resources", "yuicompressor.jar")
        
        
def compile_js(source):
    """Compiles the given javascript source string."""
    if isinstance(source, unicode):
        source = source.encode("utf-8")
    process = subprocess.Popen(
        ("java", "-jar", COMPRESSOR_PATH, "--type", "js", "--charset", "utf-8", "-v"),
        stdin = subprocess.PIPE,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
    )
    stdoutdata, stderrdata = process.communicate(source)
    # Check it all worked.
    if process.returncode != 0:
        raise JavascriptError("Error while compiling javascript.", stderrdata)
    return stdoutdata