#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 21. Feb 2018, Tobias Kohn
#
from .ppl_ast import *
from . import ppl_clojure_forms as clj
from .ppl_clojure_lexer import ClojureLexer

#######################################################################################################################

class ClojureParser(clj.Visitor):

    def visit_def_(self, target, source):
        pass

    def visit_defn_(self, name, bindings, *body):
        pass

    def visit_for_(self, bindings, *body):
        pass

    def visit_let_(self, bindings, *body):
        pass

    def visit_map_(self, function, *args):
        pass

    def visit_observe(self, dist, value):
        return AstObserve(dist.visit(self), value.visit(self))

    def visit_repeat(self, count, value):
        count = count.visit(self)
        value = value.visit(self)
        if clj.is_integer(count):
            n = count.value
            return makeVector([value] * n)
        else:
            return AstBinary(value, '*', count)

    def visit_sample(self, dist):
        return AstSample(dist.visit(self))

    def visit_vector(self, *items):
        items = [item.visit(self) for item in items]
        return makeVector(items)

    def visit_form_form(self, node:clj.Form):
        function = node.head.visit(self)
        args = [item.visit(self) for item in node.tail]
        return AstCall(function, args)

    def visit_symbol_form(self, node:clj.Symbol):
        return AstSymbol(node.name)

    def visit_value_form(self, node:clj.Value):
        return AstValue(node.value)

    def visit_vector_form(self, node:clj.Vector):
        items = [item.visit(self) for item in node.items]
        return makeVector(items)


#######################################################################################################################

def parse(source):
    clj_ast = list(ClojureLexer(source))
    ppl_ast = ClojureParser().visit(clj_ast)
    return ppl_ast
