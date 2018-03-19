#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 19. Mar 2018, Tobias Kohn
#
from pyppl.graphs import *
from pyppl.ppl_ast import *


DEFAULT_MODEL_TEMPLATE = """
class Model(object):

    def gen_log_pdf(self, state):
        log_pdf = 0
        {LOGPDF-CODE}
        return log_pdf

    def gen_sample(self):
        state = {}
        {SAMPLE-CODE}
        return state
"""


class GraphCodeGenerator(object):

    def __init__(self, nodes: list, state_object: Optional[str]=None):
        self.nodes = nodes
        self.state_object = state_object

    def gen_logpdf_code(self) -> str:
        distribution = None
        logpdf_code = []
        state = self.state_object
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                code = "dst_ = {}".format(node.get_code())
                if code != distribution:
                    logpdf_code.append(code)
                    distribution = code
                logpdf_code.append("log_pdf += dst_.log_pdf({})".format(name))

            elif isinstance(node, DataNode):
                pass

            else:
                code = "{} = {}".format(name, node.get_code())
                logpdf_code.append(code)

        return '\n'.join(logpdf_code)

    def gen_sample_code(self) -> str:
        distribution = None
        sample_code = []
        state = self.state_object
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                if node.has_observation:
                    sample_code.append("{} = {}".format(name, node.observation))
                else:
                    code = "dst_ = {}".format(node.get_code())
                    if code != distribution:
                        sample_code.append(code)
                        distribution = code
                    if node.sample_size > 1:
                        sample_code.append("{} = dst_.sample(sample_size={})".format(name, node.sample_size))
                    else:
                        sample_code.append("{} = dst_.sample()".format(name))

            else:
                code = "{} = {}".format(name, node.get_code())
                sample_code.append(code)

        return '\n'.join(sample_code)

    def generate_model_code(self) -> str:
        model_template = DEFAULT_MODEL_TEMPLATE

        def get_indent(pos):
            i = pos
            while i > 0 and model_template[i-1] in ('\t', ' '):
                i -= 1
            return model_template[i:pos]

        # get the code...
        logpdf_code = self.gen_logpdf_code()
        sample_code = self.gen_sample_code()

        # glue everything together...
        logpdf_index = model_template.index("{LOGPDF-CODE}")
        logpdf_indent = get_indent(logpdf_index)
        sample_index = model_template.index("{SAMPLE-CODE}")
        sample_indent = get_indent(sample_index)

        logpdf_code = logpdf_code.replace('\n', '\n' + logpdf_indent)
        sample_code = sample_code.replace('\n', '\n' + sample_indent)

        model_template = model_template.replace("{LOGPDF-CODE}", logpdf_code)
        model_template = model_template.replace("{SAMPLE-CODE}", sample_code)
        return model_template
