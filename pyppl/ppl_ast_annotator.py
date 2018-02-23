#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 23. Feb 2018, Tobias Kohn
#
from .ppl_ast import *


def _has_side_effects(*nodes):
    for node in nodes:
        if type(node) in [list, tuple]:
            if _has_side_effects(*node):
                return True
        elif getattr(node, 'has_side_effects', False) is True:
            return True
    return False

def _is_deterministic(*nodes):
    for node in nodes:
        if type(node) in [list, tuple]:
            if not _is_deterministic(*node):
                return False
        elif getattr(node, 'is_deterministic', True) is False:
            return False
    return True

class Annotator(AttributeVisitor):

    def set_attributes(self, dest:AstNode, children:list):
        dest.has_side_effects = _has_side_effects(*children)
        dest.is_deterministic = _is_deterministic(*children)

    def visit_call(self, node:AstCall):
        self.visit(node.function)
        if is_symbol(node.function):
            pass
        self.visit_node(node)

    def visit_observe(self, node:AstObserve):
        self.visit(node.dist)
        self.visit(node.value)
        node.has_side_effects = _has_side_effects(node.dist) or _has_side_effects(node.value)
        node.is_deterministic = False

    def visit_sample(self, node:AstSample):
        self.visit(node.dist)
        node.has_side_effects = _has_side_effects(node.dist)
        node.is_deterministic = False

