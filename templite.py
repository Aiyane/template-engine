#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Aiyane'

import re


class TempliteSyntaxError(ValueError):
    """
    抛出模板语法错误
    """
    pass


class CodeBuilder(object):
    """新建代码块"""

    def __init__(self, indent=0):
        """构造函数
        :indent: 缩进, 默认为0
        """
        self._indent = indent
        self.code = []

    def __str__(self):
        return ''.join(str(c) for c in self.code)

    def add_line(self, line):
        """
        增加一行代码
        """
        self.code.extend([" " * self._indent, line, "\n"])

    def add_section(self):
        """增加一段
        """
        section = CodeBuilder(self._indent)
        self.code.append(section)
        return section

    INDENT_STEP = 4  #  pep8标准

    def indent(self):
        """
        增加最近的缩进
        """
        self._indent += self.INDENT_STEP

    def dedent(self):
        """
        删除最近的缩进
        """
        self._indent -= self.INDENT_STEP

    def get_globals(self):
        """
        执行代码, 返回全局默认字典
        """
        assert self._indent == 0
        python_source = str(self)
        global_namespace = {}
        # 这个exec函数会执行复杂的Python代码, 但是没有返回值, 默认返回None
        # 这里的global_namespace是全局变量, 在编译成python代码时, 我们会将
        # 代码编译成一个python的函数, 可以通过全局变量名来保存这个函数的名字
        # 我们可以通过这个函数名的名字当作键值返回函数的索引, 在之后的渲染的
        # 阶段执行函数
        exec(python_source, global_namespace)
        return global_namespace


class Templite(object):
    """模板渲染的类, 符合Django的模板语法"""

    def __init__(self, text, *contexts):
        """构造函数

        :text: 全文
        :*contexts: 上下文

        """
        self.context = {}  # 这里保存的默认的上下文键值对
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()  # 这是全局变量, 是模板中所有的变量的集合
        self.loop_vars = set()  # 这是循环中的变量, 是循环体中变量, 所以并不是由上下文所提供

        code = CodeBuilder()  # 类的对象

        # 这里增加的代码是初始代码
        code.add_line("def render_function(context, do_dots):")
        code.indent()  # 增加缩进
        vars_code = code.add_section()  # 增加一段
        code.add_line("result = []")  # 增加一个list变量
        code.add_line("append_result = result.append")  # 增加append函数
        code.add_line("extend_result = result.extend")  # 增加extent函数
        code.add_line("to_str = str")  # 增加str变量

        buffered = []  # 缓冲

        def flush_output():
            """
            缓冲输出, 缓冲内容为一行就调用append_result函数
            超过一行就调用extend_result函数
            """
            if len(buffered) == 1:
                code.add_line("append_result(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("extend_result([%s])" % ", ".join(buffered))
            del buffered[:]

        ops_stack = []

        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:
            if token.startswith('{#'):
                # 注释: 忽略注释符中的内容
                continue
            elif token.startswith('{{'):
                # 替换上下文的变量
                expr = self._expr_code(token[2:-2].strip())
                buffered.append("to_str(%s)" % expr)
            elif token.startswith('{%'):
                # 这里是简单的逻辑部分
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    # if表达式 用来处理条件语句, 但是这个表达式需要以 endif结尾, 并且只支持简单逻辑, 不支持复杂 逻辑.
                    ops_stack.append('if')

                    # 扩展if语句
                    _content = []
                    for word in words[1:]:
                        if re.match(r"[_a-zA-Z][_a-zA-Z0-9]*(\.[_a-zA-Z][_a-zA-Z0-9]*)*$", word):
                            _content.append(self._expr_code(word))
                            continue
                        _content.append(word)

                    code.add_line("if %s:" % ' '.join(_content))
                    code.indent()
                elif words[0] == 'for':
                    # for循环, 以endfor结尾
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line(
                        "for c_%s in %s:" % (
                            words[1],
                            self._expr_code(words[3])
                        )
                    )
                    code.indent()
                elif words[0].startswith('end'):
                    # 结束符, 用来结束逻辑语句
                    if len(words) != 1:
                        self._syntax_error("Don't understand end", token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error("Too many ends", token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()
                else:
                    self._syntax_error("Don't understand tag", words[0])
            else:
                # 否则存入缓冲区
                if token:
                    buffered.append(repr(token))
        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        flush_output()

        # 选出上下文的变量
        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        """
        生成python表达式
        """
        if "|" in expr:
            pipes = expr.split("|")
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = "c_%s(%s)" % (func, code)
        elif "." in expr:
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
            self._variable(expr, self.all_vars)
            code = "c_%s" % expr
        return code

    def _syntax_error(self, msg, thing):
        """
        抛出错误
        """
        raise TempliteSyntaxError("%s: %r" % (msg, thing))

    def _variable(self, name, vars_set):
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)

    def render(self, context=None):
        """
        渲染函数
        """
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        """
        处理点操作符
        参数:
            :value: 是点操作符的左值
            :dots: 点操作符的后一个变量, 如果最初的value中有这个属性, 则返回这个属性
                如果这个是一个字典中的key, 就返回这个字典的键值, 如果这是一个可以回调
                的函数, 则返回这个函数的调用结果
        """
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value
