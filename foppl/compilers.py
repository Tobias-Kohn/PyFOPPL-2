#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Dec 2017, Tobias Kohn
# 18. Jan 2018, Tobias Kohn
#
import math
from . import foppl_objects
from . import foppl_parser
from . import py_parser
from .foppl_ast import *
from .code_objects import *
from .graphs import *


class Scope(object):
    """
    The scope is basically a stack of dictionaries, implemented as a simply
    linked list of Scope-classes. Functions and other symbols/values are
    stored in distinct dictionaries, and hence also have distinct namespaces.

    If the value of a symbol is of type AstValue, we store this ast-node as
    well. This is then used by the optimizer.
    """

    def __init__(self, prev=None):
        self.prev = prev
        self.symbols = {}
        self.functions = {}

    def find_function(self, name: str):
        if name in self.functions:
            return self.functions[name]
        elif self.prev:
            return self.prev.find_function(name)
        else:
            return None

    def find_symbol(self, name: str):
        if name in self.symbols:
            return self.symbols[name]
        elif self.prev:
            return self.prev.find_symbol(name)
        else:
            return None

    def add_function(self, name: str, value):
        self.functions[name] = value

    def add_symbol(self, name: str, value):
        self.symbols[name] = value

    @property
    def is_global_scope(self):
        return self.prev is None

    def __repr__(self):
        symbols = ', '.join(['{} -> {}'.format(u, self.symbols[u][1]) for u in self.symbols])
        return "Scope\n\tSymbols: {}\n\tFunctions: {}".format(symbols, repr(self.functions))


class ConditionalScope(object):
    """
    Conditional scope
    """

    def __init__(self, prev=None, condition=None, ancestors=None):
        self.prev = prev
        self.condition = condition
        self.ancestors = ancestors
        self.truth_value = True
        cond = self.condition
        if isinstance(cond, CodeUnary) and cond.op == 'not':
            cond = cond.item
            self.condition = cond
            self.truth_value = not self.truth_value
        if isinstance(cond, CodeCompare) and cond.is_normalized:
            func = cond.left
            self.cond_node = ConditionNode(condition=self.condition, function=func, ancestors=self.ancestors)
        else:
            self.cond_node = ConditionNode(condition=self.condition, ancestors=self.ancestors)

    def invert(self):
        self.truth_value = not self.truth_value

    def get_condition(self):
        return self.cond_node, self.truth_value


class Compiler(Walker):
    """
    The Compiler
    """

    __binary_ops = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y,
        '**': lambda x, y: x ** y,
        'and': lambda x, y: x & y,
        'or':  lambda x, y: x | y,
        'xor': lambda x, y: x ^ y
    }

    def __init__(self):
        self.scope = Scope()
        self.cond_scope = None

    def begin_scope(self):
        self.scope = Scope(prev=self.scope)

    def end_scope(self):
        if not self.scope.is_global_scope:
            self.scope = self.scope.prev
        else:
            raise RuntimeError('[stack underflow] ending global scope')

    def begin_conditional_scope(self, condition, ancestors):
        self.cond_scope = ConditionalScope(self.cond_scope, condition, ancestors)

    def end_conditional_scope(self):
        if self.cond_scope:
            self.cond_scope = self.cond_scope.prev
        else:
            raise RuntimeError('[stack underflow] ending conditional scope')

    def invert_conditional_scope(self):
        if self.cond_scope:
            self.cond_scope.invert()

    def current_conditions(self):
        result = []
        c = self.cond_scope
        while c:
            result.append(c.get_condition())
            c = c.prev
        return result

    def define(self, name, value):
        if isinstance(name, AstSymbol):
            name = name.name
        if isinstance(name, foppl_objects.Symbol):
            name = name.name
        if isinstance(value, AstFunction):
            self.scope.add_function(name, value)
        else:
            graph, expr = value.walk(self)
            if isinstance(expr, CodeSample):
                v = graph.get_vertex_for_distribution(expr.distribution)
                if v: v.original_name = name
            self.scope.add_symbol(name, (graph, expr))

    def resolve_function(self, name):
        return self.scope.find_function(name)

    def resolve_symbol(self, name):
        return self.scope.find_symbol(name)

    def visit_node(self, node: Node):
        raise NotImplementedError(node)

    def visit_binary(self, node: AstBinary):
        graph_l, code_l = node.left.walk(self)
        graph_r, code_r = node.right.walk(self)
        graph = merge(graph_l, graph_r)

        if isinstance(code_l, CodeValue) and isinstance(code_r, CodeValue) and node.op in self.__binary_ops:
            return CodeValue(self.__binary_ops[node.op](code_l.value, code_r.value))

        elif isinstance(code_l, CodeValue):
            value = code_l.value
            if value == 0:
                if node.op == '+':
                    return code_r
                elif node.op == '-':
                    return AstUnary('-', node.right).walk(self)
                elif node.op in ['*', '/']:
                    return code_l
            elif value == 1:
                if node.op == '*':
                    return code_r

        elif isinstance(code_r, CodeValue):
            value = code_r.value
            if value == 0:
                if node.op in ['+', '-']:
                    return code_l
                elif node.op == '*':
                    return code_r
            elif value == 1:
                if node.op in ['*', '/']:
                    return code_l


        code = CodeBinary(code_l, node.op, code_r)
        return graph, code

    def visit_body(self, node: AstBody):
        graph = Graph.EMPTY
        code = CodeValue(None)
        for item in node.body:
            g, code = item.walk(self)
            graph = graph.merge(g)
        return graph, code

    def visit_compare(self, node: AstCompare):
        graph_l, code_l = node.left.walk(self)
        graph_r, code_r = node.right.walk(self)
        graph = merge(graph_l, graph_r)
        code = CodeCompare(code_l, node.op, code_r)
        return graph, code

    def visit_def(self, node: AstDef):
        if self.scope.is_global_scope:
            self.define(node.name, node.value)
            return Graph.EMPTY, CodeValue(None)
        else:
            raise SyntaxError("'def' must be on the global level")

    def visit_distribution(self, node: AstDistribution):
        args = self.walk_all(node.args)
        graph = merge(*[g for g, _ in args])
        return graph, CodeDistribution(node.name, [a for _, a in args])

    def visit_if(self, node: AstIf):
        cond_graph, cond = node.cond.walk(self)
        self.begin_conditional_scope(cond, cond_graph.vertices)
        try:
            graph, if_code = node.if_body.walk(self)
            if node.else_body:
                self.invert_conditional_scope()
                else_graph, else_code = node.else_body.walk(self)
                graph = merge(graph, else_graph)
            else:
                else_code = None
        finally:
            self.end_conditional_scope()
        graph = merge(cond_graph, graph)
        return graph, CodeIf(cond, if_code, else_code)

    def visit_let(self, node: AstLet):
        self.begin_scope()
        try:
            for (name, value) in node.bindings:
                self.define(name, value)
            result = node.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_observe(self, node: AstObserve):
        graph, dist = node.distribution.walk(self)
        obs_graph, obs_value = node.value.walk(self)
        vertex = Vertex(ancestor_graph=merge(graph, obs_graph), distribution=dist, observation=obs_value,
                        conditions=self.current_conditions())
        return Graph({vertex}).merge(graph), CodeObserve(vertex)

    def visit_sample(self, node: AstSample):
        graph, dist = node.distribution.walk(self)
        vertex = Vertex(ancestor_graph=graph, distribution=dist, conditions=self.current_conditions())
        return Graph({vertex}).merge(graph), CodeSample(vertex)

    def visit_sqrt(self, node: AstSqrt):
        graph, code = node.item.walk(self)
        if isinstance(code, CodeValue) and type(code.value) in [int, float]:
            return graph, CodeValue(math.sqrt(code.value))
        else:
            return graph, CodeSqrt(code)

    def visit_symbol(self, node: AstSymbol):
        return self.resolve_symbol(node.name)

    def visit_unary(self, node: AstUnary):
        if isinstance(node.item, AstUnary) and node.op == node.item.op:
            return node.item.item.walk(self)
        elif node.op == '+':
            return node.item.walk(self)
        else:
            graph, code = node.item.walk(self)

            if isinstance(code, CodeUnary) and code.op == node.op:
                return graph, code.item

            elif isinstance(code, CodeValue):
                value = code.value
                if node.op == '-':
                    return graph, CodeValue(-value)
                elif node.op == 'not':
                    return graph, CodeValue(not value)

            return graph, CodeUnary(node.op, code)

    def visit_value(self, node: AstValue):
        value = node.value
        if type(value) is list:
            value = DataNode(data=value)
            return Graph(set(), data={value}), CodeDataSymbol(value)
        else:
            return Graph.EMPTY, CodeValue(node.value)

    def visit_vector(self, node: AstVector):
        items = self.walk_all(node.items)
        graph = merge(*[g for g, _ in items])
        code = CodeVector([i for _, i in items])
        return graph, code


def _detect_language(source:str):
    i = 0
    while i < len(source) and source[i] <= ' ': i += 1
    if i < len(source):
        c = source[i]
        if c in [';', '(']:
            return 'clj'
        elif c in ['#'] or 'A' <= c <= 'Z' or 'a' <= c <= 'z':
            return 'py'
    return None


def compile(source):
    if type(source) is str:
        lang = _detect_language(source)
        if lang == 'py':
            ast = py_parser.parse(source)
        elif lang == 'clj':
            ast = foppl_parser.parse(source)
        else:
            ast = None

    elif isinstance(source, Node):
        ast = source

    else:
        ast = None

    if ast:
        compiler = Compiler()
        return compiler.walk(ast)
    else:
        raise RuntimeError("cannot parse '{}'".format(source))
