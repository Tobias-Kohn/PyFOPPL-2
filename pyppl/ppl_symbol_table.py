#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Mar 2018, Tobias Kohn
# 07. Mar 2018, Tobias Kohn
#
from .ppl_ast import *


_symbol_counter = 1000

class Symbol(object):

    def __init__(self, name:str, read_only:bool=False, missing:bool=False):
        global _symbol_counter
        self.name = name            # type:str
        self.usage_count = 0        # type:int
        self.modify_count = 0       # type:int
        self.read_only = read_only  # type:bool
        self.full_name = "{}__sym_{}__".format(name, _symbol_counter)
        _symbol_counter += 1
        if missing:
            self.modify_count = -1
        assert type(self.name) is str
        assert type(self.read_only) is bool

    def use(self):
        self.usage_count += 1

    def modify(self):
        self.modify_count += 1

    def __repr__(self):
        return "{}[{}/{}{}]".format(self.full_name, self.usage_count, self.modify_count, 'R' if self.read_only else '')


class SymbolTableGenerator(ScopedVisitor):
    """
    Walks the AST and records all symbols, their definitions and usages. After walking the AST, the field `symbols`
    is a list of all symbols used in the program.

    Note that nodes of type `AstSymbol` are modified by walking the tree. In particular, the Symbol-Table-Generator
    sets the field `symbol` of `AstSymbol`-nodes and modifies the `name`-field, so that all names in the program are
    guaranteed to be unique.
    By relying on the fact that all names in the program are unique, we can later on use a flat list of symbol values
    without worrying about correct scoping (the scoping is taken care of here).
    """

    def __init__(self):
        super().__init__()
        self.symbols = []
        self.current_lineno = None

    def get_symbols(self):
        for symbol in self.symbols:
            if symbol.modify_count == 0:
                symbol.read_only = True
        return self.symbols

    def create_symbol(self, name:str, read_only:bool=False, missing:bool=False):
        symbol = Symbol(name, read_only=read_only, missing=missing)
        self.symbols.append(symbol)
        return symbol

    def g_def(self, name:str, read_only:bool=False):
        if name == '_':
            return None
        symbol = self.global_scope.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, read_only)
            self.global_scope.define(name, symbol)
        else:
            symbol.modify()
        return symbol

    def l_def(self, name:str, read_only:bool=False):
        if name == '_':
            return None
        symbol = self.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, read_only)
            self.define(name, symbol)
        else:
            symbol.modify()
        return symbol

    def use_symbol(self, name:str):
        if name == '_':
            return None
        symbol = self.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, missing=True)
            self.global_scope.define(name, symbol)
        symbol.use()
        return symbol


    def visit_node(self, node:AstNode):
        node.visit_children(self)

    def visit_def(self, node: AstDef):
        self.visit(node.value)
        sym = self.resolve(node.name)
        if sym is not None and sym.read_only:
            raise TypeError("[line {}] cannot modify '{}'".format(self.current_lineno, node.name))
        if node.global_context:
            self.g_def(node.name, read_only=False)
        else:
            self.l_def(node.name, read_only=False)

    def visit_for(self, node: AstFor):
        self.visit(node.source)
        with self.create_scope():
            self.l_def(node.target, read_only=True)
            self.visit(node.body)

    def visit_function(self, node: AstFunction):
        with self.create_scope():
            for param in node.param_names:
                self.l_def(param)
                self.visit(node.body)

    def visit_import(self, node: AstImport):
        return self.visit_node(node)

    def visit_let(self, node: AstLet):
        self.visit(node.source)
        with self.create_scope():
            self.l_def(node.target, read_only=True)
            self.visit(node.body)

    def visit_list_for(self, node: AstListFor):
        self.visit(node.source)
        with self.create_scope():
            self.l_def(node.target, read_only=True)
            self.visit(node.test)
            self.visit(node.expr)

    def visit_symbol(self, node: AstSymbol):
        symbol = self.use_symbol(node.original_name)
        node.symbol = symbol
        node.name = symbol.full_name

    def visit_while(self, node: AstWhile):
        return self.visit_node(node)
