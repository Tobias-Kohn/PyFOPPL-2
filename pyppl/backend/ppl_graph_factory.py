#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 12. Mar 2018, Tobias Kohn
#
from pyppl.ppl_ast import AstNode


class GraphFactory(object):

    def __init__(self):
        self._counter = 3000

    def generate_symbol(self, prefix: str):
        self._counter += 1
        return prefix + str(self._counter)

    def create_node(self, parents: set):
        assert type(parents) is set
        return None

    def create_condition_node(self, test: AstNode, parents: set):
        return self.create_node(parents)

    def create_data_node(self, data: AstNode, parents: set):
        return self.create_node(parents)

    def create_observe_node(self, dist: AstNode, value: AstNode, parents: set):
        return self.create_node(parents)

    def create_sample_node(self, dist: AstNode, parents: set):
        return self.create_node(parents)
