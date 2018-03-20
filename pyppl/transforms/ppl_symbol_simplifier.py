#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Mar 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..aux.ppl_transform_visitor import TransformVisitor


class SymbolSimplifier(TransformVisitor):

    def __init__(self):
        super().__init__()
        self.names_map = {}
        self.name_count = {}

    def simplify_symbol(self, name: str):
        if name.startswith('__'):
            if '____' in name:
                short = name[:name.index('____')+2]
                if short not in self.name_count:
                    self.name_count[short] = 1
                else:
                    self.name_count[short] += 1
                    short += "_{}".format(self.name_count[short])
                self.names_map[name] = short
                return short
            else:
                return name
        elif name in self.names_map:
            return self.names_map[name]
        elif '__' in name:
            short = name[:name.index('__')]
            if short not in self.name_count:
                self.name_count[short] = 1
            else:
                self.name_count[short] += 1
                short += "_{}".format(self.name_count[short])
            self.names_map[name] = short
            return short
        else:
            return name

    def visit_def(self, node: AstDef):
        name = self.simplify_symbol(node.name)
        value = self.visit(node.value)
        if name != node.name or value is not node.value:
            return node.clone(name=name, value=value)
        else:
            return node

    def visit_let(self, node: AstLet):
        source = self.visit(node.source)
        name = self.simplify_symbol(node.target)
        body = self.visit(node.body)
        if name == node.target and source is node.source and body is node.body:
            return node
        else:
            return node.clone(target=name, source=source, body=body)

    def visit_symbol(self, node: AstSymbol):
        name = self.simplify_symbol(node.name)
        if name != node.name:
            return node.clone(name=name)
        else:
            return node
