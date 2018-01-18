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
        V = '  '.join(sorted([repr(v) for v in self.vertices]))
        A = ', '.join(['({}, {})'.format(u.name, v.name) for (u, v) in self.arcs]) if len(self.arcs) > 0 else "-"
        C = '\n  '.join(sorted([repr(v) for v in self.conditionals])) if len(self.conditionals) > 0 else "-"
        D = '\n  '.join([repr(u) for u in self.data]) if len(self.data) > 0 else "-"
        graph = "Vertices V:\n  {V}\nArcs A:\n  {A}\n\nConditions C:\n  {C}\n\nData D:\n  {D}\n".format(V=V, A=A, C=C, D=D)
        model = "\nContinuous:  {}\nDiscrete:    {}\nConditional: {}\n".format(
            ', '.join(sorted([v.name for v in self.gen_cont_vars()])),
            ', '.join(sorted([v.name for v in self.gen_disc_vars()])),
            ', '.join(sorted([v.name for v in self.gen_if_vars()])),
        )
        return graph + model

    def index_of_node(self, node):
        return self.compute_nodes.index(node)

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
