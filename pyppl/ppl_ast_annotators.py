#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 28. Feb 2018, Tobias Kohn
#
from .ppl_ast import *


def _has_true(obj):
    if type(obj) is bool:
        return obj
    elif hasattr(obj, '__iter__'):
        lst = [_has_true(item) for item in obj]
        return any(lst) if len(lst) > 0 else False
    else:
        return False


class SideEffectAnnotator(Visitor):

    def visit_node(self, node:AstNode):
        result = node.visit_children(self)
        return _has_true(result)

    def visit_observe(self, _):
        return True


def has_side_effects(ast):
    return SideEffectAnnotator().visit(ast)
