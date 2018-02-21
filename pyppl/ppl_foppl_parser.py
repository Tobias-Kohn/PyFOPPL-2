#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Feb 2018, Tobias Kohn
# 21. Feb 2018, Tobias Kohn
#
from .ppl_ast import *
from . import ppl_clojure_forms as clj
from .ppl_clojure_lexer import ClojureLexer
from .ppl_clojure_parser import ClojureParser

#######################################################################################################################

class FopplParser(ClojureParser):

    def visit_loop(self, count, initial_data, function, *args):
        pass


#######################################################################################################################

def parse(source):
    clj_ast = list(ClojureLexer(source))
    ppl_ast = FopplParser().visit(clj_ast)
    return ppl_ast
