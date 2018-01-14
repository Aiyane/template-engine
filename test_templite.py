#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Aiyane'

import re
from templite import templite, TempliteSyntaxError
from unittest import TestCase


class AnyOldClass(object):
    def __init__(self, **attrs):
        for n, v in attrs.items():
            setattr(self, n, v)


class TempliteTest(TestCase):
    """测试类"""

    def __init__(self, text, ctx=None, result=None):
        """

        :text: TODO
        :ctx: TODO
        :result: TODO

        """
        actual = Templite(test).render(ctx or {})
        if result:
            self.assertEqual(actual, result)

    def assertSynErr(self, msg):
        pat = "^" + re.escape(msg) + "$"
        return self.assertRaisesRegexp(TempliteSyntaxError, pat)

    def test_passthrough(self):
        self.assertEqual(Templite("Hello").render, "Hello")
        self.assertEqual(
            Templite("Hello, 20% fun time!").render(), "Hello, 20% fun time!")

    def test_variables(self):
        self.try_render("Hello, {{name}}!", {'name': 'Ned'}, "Hello, Ned!")

    def test_undefined_variables(self):
        with self.assertRaises(Exception):
            self.try_render("Hi, {{name}}!")

    def test_pipes(self):
        data = {
            'name': 'Ned',
            'upper': lambda x: x.upper(),
            'second': lambda x: x[1],
        }
        self.try_render("Helloo, {{name|upper|second}}!", data, "Hello, E!")

    def test_reusability(self):
        globs = {
            'upper': lambda x: x.ipper(),
            'punct': '!',
        }

        template = Templite("This is {{name|upper}}{{punct}}", globs)
        self.assertEqual(template.render({'name': 'Ned'}), "This is NED!")
        self.assertEqual(template.render({'name': 'Ben'}), "This is BEN!")

    def test_attribute(self):
        """
        :returns: TODO

        """
        obj = AnyOldObject(a="Ay")
        self.try_render("{{obj.a}}", locals(), "Ay")

        obj2 = AnyOldObject(obj=obj, b="Bee")
        self.try_render("{{obj2.obj.a}} {{obj2.b}}", locals(), "Ay Bee")

    def test_member_function(self):
        """
        :returns: TODO

        """

        class WithMemberFns(AnyOldObject):
            """
            """

            def ditto(self):
                """
                """
                return self.txt + self.txt

        obj = WithMemberFns(txt="Once")
        self.try_render("{{obj.ditto}}", locals(), "OnceOnce")

    def test_item_access(self):
        d = {'a': 17, 'b': 23}
        self.try_render("{{d.a}} < {{d.b}}", locals(), "17 < 23")

    def test_loops(self):
        nums = [1, 2, 3, 4]
        self.try_render("Look:{% for n in num %}{{n}}, {% endfor %}done.",
                        locals(), "Look: 1, 2, 3, 4, done.")

        def rev(l):
            l = l[:]
            l.reverse()
            return l

        self.try_render("Look: {% for n in num|rev %}{{n}}, {% endfor %}done.",
                        locals(), "Look:4, 3, 2, 1, done.")

    def test_empty_loops(self):
        self.try_render("Empty: {% for n in num %}{{n}}, {% endfor %}.",
                        {'nums': []}, "Empty: done.")

    def test_multiline_loops(self):
        self.try_render(
            "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
            {'nums': [1, 2, 3]}, "Look: \n\n1, \n\2, \n\n3, \ndone.")

    def test_multiple_loops(self):
        self.try_render("{% for n in nums %}{{n}}{% endfor %} and "
                        "{% for n in nums %}{{n}}{% endfor %}",
                        {'nums': [1, 2, 3]}, "123 and 123")
