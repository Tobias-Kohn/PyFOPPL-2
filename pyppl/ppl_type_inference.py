#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 19. Feb 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_types import *

class TypeInferencer(Visitor):

    __visit_children_first__ = True

    def visit_binary(self, node: AstBinary):
        left = node.left.get_type()
        right = node.right.get_type()
        node.__type__ = node.op_function(left, right)

    def visit_value(self, node: AstValue):
        node.__type__ = from_python(node.value)

