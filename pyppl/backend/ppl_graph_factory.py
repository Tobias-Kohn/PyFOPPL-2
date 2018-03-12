#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 12. Mar 2018, Tobias Kohn
#
from pyppl.ppl_ast import AstNode
from pyppl.graphs import *
from .ppl_code_generator import CodeGenerator


class GraphFactory(object):

    def __init__(self, code_generator=None):
        if code_generator is None:
            code_generator = CodeGenerator()
        self._counter = 30000
        self.nodes = []
        self.code_generator = code_generator

    def _generate_code_for_node(self, node: AstNode):
        return self.code_generator.visit(node)

    def generate_symbol(self, prefix: str):
        self._counter += 1
        return prefix + str(self._counter)

    def create_node(self, parents: set):
        assert type(parents) is set
        return None

    def create_condition_node(self, test: AstNode, parents: set):
        name = self.generate_symbol('cond_')
        code = self._generate_code_for_node(test)
        result = ConditionNode(name, ancestors=parents, cond_code=code)
        self.nodes.append(result)
        return result

    def create_data_node(self, data: AstNode, parents: set):
        name = self.generate_symbol('data_')
        code = self._generate_code_for_node(data)
        result = DataNode(name, ancestors=parents, data=code)
        self.nodes.append(result)
        return result

    def create_observe_node(self, dist: AstNode, value: AstNode, parents: set):
        name = self.generate_symbol('y')
        d_code = self._generate_code_for_node(dist)
        v_code = self._generate_code_for_node(value)
        result = Vertex(name, ancestors=parents, dist_code=d_code)
        self.nodes.append(result)
        return result

    def create_sample_node(self, dist: AstNode, parents: set):
        name = self.generate_symbol('x')
        code = self._generate_code_for_node(dist)
        result = Vertex(name, ancestors=parents, dist_code=code)
        self.nodes.append(result)
        return result

    def generate_log_pdf_code(self):
        result = [node.gen_log_pdf_code('state') for node in self.nodes]
        result = [item for item in result if item is not None and item != '']
        return '\n'.join(result)

    def generate_sampling_code(self):
        result = [node.gen_sampling_code('state') for node in self.nodes]
        result = [item for item in result if item is not None and item != '']
        return '\n'.join(result)
