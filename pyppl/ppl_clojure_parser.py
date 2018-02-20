#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Feb 2018, Tobias Kohn
#
from ast import copy_location as _cl
from .ppl_ast import *
from . import ppl_clojure_forms as clj

#######################################################################################################################

class ClojureParser(clj.Visitor):

    def visit_form(self, node:clj.Form):
        raise NotImplementedError("forms are not supported, yet")

    def visit_symbol(self, node:clj.Symbol):
        return _cl(AstSymbol(node.name), node)

    def visit_value(self, node:clj.Value):
        return _cl(AstValue(node.value), node)

    def visit_vector(self, node:clj.Vector):
        items = [item.visit(self) for item in node.items]
        return _cl(makeVector(items), node)


#######################################################################################################################

def parse(source):
    ppl_ast = ClojureParser().visit(None)
    return ppl_ast