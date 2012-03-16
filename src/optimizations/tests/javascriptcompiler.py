"""Tests for the javascript compiler."""

from django.test import TestCase

from optimizations.javascriptcompiler import compile_js


class JavascriptCompilerTest(TestCase):
    
    def testJavascriptCompiler(self):
        self.assertEqual(compile_js("function(){var foo = 'foo';}"), 'function(){var a="foo"};')