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



DEFAULT_MODEL_TEMPLATE = """
class Model():

    def gen_log_pdf(self, state):
        log_pdf = 0
        {log_pdf_code}
        return log_pdf

    def gen_sample(self):
        state = {}
        {sampling_code}
        return state
"""


class GraphFactory(object):

    def __init__(self, code_generator=None):
        if code_generator is None:
            code_generator = CodeGenerator()
            code_generator.state_object = 'state'
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

    def create_sample_node(self, dist: AstNode, size: int, parents: set):
        name = self.generate_symbol('x')
        code = self._generate_code_for_node(dist)
        result = Vertex(name, ancestors=parents, dist_code=code, sample_size=size)
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

    def generate_code(self, model_template: str = None):
        if model_template is None:
            model_template = DEFAULT_MODEL_TEMPLATE

        def get_indent(pos):
            i = pos
            while i > 0 and model_template[i-1] in ('\t', ' '):
                i -= 1
            return model_template[i:pos]

        distribution = None
        log_pdf_code = []
        sampling_code = []
        state = self.code_generator.state_object
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                code = "dst_ = {}".format(node.get_code())
                if code != distribution:
                    log_pdf_code.append(code)
                    sampling_code.append(code)
                    distribution = code
                log_pdf_code.append("log_pdf += _dst_.log_pdf({})".format(name))
                if node.sample_size > 1:
                    sampling_code.append("{} = dst_.sample(sample_size={})".format(name, node.sample_size))
                else:
                    sampling_code.append("{} = dst_.sample()".format(name))

            else:
                code = "{} = {}".format(name, node.get_code())
                log_pdf_code.append(code)
                sampling_code.append(code)

        logpdf_index = model_template.index("{log_pdf_code}")
        logpdf_indent = get_indent(logpdf_index)
        sample_index = model_template.index("{sampling_code}")
        sample_indent = get_indent(sample_index)

        log_pdf_code = ('\n' + logpdf_indent).join(log_pdf_code)
        sampling_code = ('\n' + sample_indent).join(sampling_code)

        model_template = model_template.replace("{log_pdf_code}", log_pdf_code)
        model_template = model_template.replace("{sampling_code}", sampling_code)
        return model_template
