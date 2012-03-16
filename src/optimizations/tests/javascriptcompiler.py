"""Tests for the javascript compiler."""

from django.test import TestCase

from optimizations.javascriptcompiler import default_javascript_compiler


class JavascriptCompilerTest(TestCase):
    
    def testJavascriptCompiler(self):
        self.assertEqual(default_javascript_compiler.compile("function(){var foo = 'foo';}"), 'function(){var a="foo"};')