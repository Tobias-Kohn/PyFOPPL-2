#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 19. Jan 2018, Tobias Kohn
#

# We try to import `networkx` and `matplotlib`. If present, these packages can be used to get a visual
# representation of the graph. But neither of these packages is actually needed.
try:
    import networkx as nx
except ModuleNotFoundError:
    nx = None

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

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

    def create_network_graph(self):
        if nx:
            G = nx.DiGraph()
            for v in self.vertices:
                G.add_node(v.name)
                for a in v.ancestors:
                    G.add_edge(a.name, v.name)
            return G
        else:
            return None

    def display_network_graph(self):
        G = self.create_network_graph()
        if nx and plt and G:
            try:
                from networkx.drawing.nx_agraph import graphviz_layout
                pos = graphviz_layout(G, prog='dot')
            except ModuleNotFoundError:
                from networkx.drawing.layout import shell_layout
                pos = shell_layout(G)
            plt.subplot(111)
            plt.axis('off')
            nx.draw_networkx_nodes(G, pos,
                                   node_color='r', alpha=0.75,
                                   node_size=1200,
                                   nodelist=[v.name for v in self.vertices if v.is_sampled])
            nx.draw_networkx_nodes(G, pos,
                                   node_color='b', alpha=0.75,
                                   node_size=1250,
                                   nodelist=[v.name for v in self.vertices if v.is_observed])
            nx.draw_networkx_edges(G, pos, arrows=True)
            nx.draw_networkx_labels(G, pos)
            plt.show()
            return True
        else:
            return False

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
