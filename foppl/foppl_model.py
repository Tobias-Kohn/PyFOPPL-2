#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 18. Jan 2018, Tobias Kohn
#
class Model(object):

    def __init__(self, *, vertices: set, arcs: set, data: set, conditionals: set, compute_nodes: list):
        self.vertices = vertices
        self.arcs = arcs
        self.data = data
        self.conditionals = conditionals
        self.compute_nodes = compute_nodes

    def __repr__(self):
        V = "Vertices V:\n  " + '  '.join(sorted([repr(v) for v in self.vertices]))
        if len(self.arcs) > 0:
            A = "Arcs A:\n  " + ', '.join(['({}, {})'.format(u.name, v.name) for (u, v) in self.arcs]) + "\n"
        else:
            A = "Arcs A: -\n"
        if len(self.conditionals) > 0:
            C = "Conditions C:\n  " +'\n  '.join(sorted([repr(v) for v in self.conditionals])) + "\n"
        else:
            C = "Conditions C: -\n"
        if len(self.data) > 0:
            D = "Data D:\n  " + '\n  '.join([repr(u) for u in self.data])
        else:
            D = "Data D: -\n"
        return "\n".join([V, A, C, D])

    def get_vertices(self):
        return self.vertices

    def get_arcs(self):
        return self.arcs

    def gen_if_vars(self):
        return [v for v in self.vertices if v.is_conditional]

    def gen_cont_vars(self):
        return [v for v in self.vertices if v.is_continuous and not v.is_conditional]

    def gen_disc_vars(self):
        return [v for v in self.vertices if v.is_discrete and not v.is_conditional]

    def gen_vars(self):
        return [v for v in self.vertices if v.is_sampled]

    def gen_prior_samples(self):
        state = {}
        for node in self.compute_nodes:
            node.update(state)
        return state

    def gen_pdf(self, state):
        for node in self.compute_nodes:
            node.update_pdf(state)
        if 'log_pdf' in state:
            return state['log_pdf']
        else:
            return 0.0
