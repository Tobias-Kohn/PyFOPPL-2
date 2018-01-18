#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 18. Jan 2018, Tobias Kohn
#
from . import Options
from .foppl_distributions import discrete_distributions, continuous_distributions

_LAMBDA_PATTERN_ = "lambda state: {}"

class GraphNode(object):
    """
    """

    name = ""
    ancestors = set()

    __symbol_counter__ = 30000

    @classmethod
    def __gen_symbol__(cls, prefix:str):
        cls.__base__.__symbol_counter__ += 1
        return "{}{}".format(prefix, cls.__base__.__symbol_counter__)

    def evaluate(self, state):
        raise NotImplemented()

    def update(self, state: dict):
        result = self.evaluate(state)
        state[self.name] = result
        return result

    def update_pdf(self, state: dict):
        self.update(state)
        return 0.0


class ConditionNode(GraphNode):
    """
    Condition
    """

    def __init__(self, *, name:str=None, condition=None, ancestors:set=None, op:str='?', function=None):
        from .code_objects import CodeCompare, CodeValue
        if name is None:
            name = self.__class__.__gen_symbol__('cond_')
        if ancestors is None:
            ancestors = set()
        if function:
            if op == '?':
                op = '>='
            if condition is None:
                condition = CodeCompare(function, op, CodeValue(0))
        self.name = name
        self.ancestors = ancestors
        self.op = op
        self.condition = condition
        self.function = function
        self.code = _LAMBDA_PATTERN_.format(condition.to_py() if condition else "None") + Options.conditional_suffix
        self.function_code = _LAMBDA_PATTERN_.format(function.to_py() if function else "None")
        self.evaluate = eval(self.code)
        self.evaluate_function = eval(self.function_code)
        for a in ancestors:
            if isinstance(a, Vertex):
                a._add_dependent_condition(self)

    def __repr__(self):
        if self.function:
            result = "{f} {o} 0\n\tFunction: {f}".format(f=repr(self.function), o=self.op)
        elif self.condition:
                result = repr(self.condition)
        else:
            result = "???"
        ancestors = ', '.join([v.name for v in self.ancestors])
        return "{}:\n\tAncestors: {}\n\tCondition: {}".format(self.name, ancestors, result)

    @property
    def has_function(self):
        return self.function is not None

    def update(self, state: dict):
        if self.function:
            f_result = self.evaluate_function(state)
            result = f_result >= 0
            state[self.name + ".function"] = f_result
        else:
            result = self.evaluate(state)
        state[self.name] = result
        return result


class DataNode(GraphNode):
    """
    Data
    """

    def __init__(self, *, name:str=None, data):
        if name is None:
            name = self.__class__.__gen_symbol__('data_')
        self.name = name
        self.data = data
        self.ancestors = set()
        self.code = _LAMBDA_PATTERN_.format(repr(self.data))
        self.evaluate = eval(self.code)

    def __repr__(self):
        return "{} = {}".format(self.name, repr(self.data))


class Parameter(GraphNode):
    """
    A parameter
    """

    def __init__(self, *, name:str=None, value):
        if name is None:
            name = self.__class__.__gen_symbol__('param_')
        self.name = name
        self.ancestors = set()
        self.value = value
        self.code = _LAMBDA_PATTERN_.format(value)
        self.evaluate = eval(self.code)

    def __repr__(self):
        return "{}: {}".format(self.name, self.value)


class Vertex(GraphNode):
    """
    A vertex in the graph
    """

    def __init__(self, *, name:str=None, ancestors:set=None, data:set=None, distribution=None, observation=None,
                 ancestor_graph=None, conditions:list=None):
        if name is None:
            name = self.__class__.__gen_symbol__('y' if observation else 'x')
        if ancestor_graph:
            if ancestors:
                ancestors = ancestors.union(ancestor_graph.vertices)
            else:
                ancestors = ancestor_graph.vertices
        if ancestors is None:
            ancestors = set()
        if data is None:
            data = set()
        if conditions is None:
            conditions = []
        self.name = name
        self.ancestors = ancestors
        self.data = data
        self.distribution = distribution
        self.observation = observation
        self.conditions = conditions
        self.dependent_conditions = set()
        self.distribution_name = distribution.name
        if distribution.name in continuous_distributions:
            self.distribution_type = 'continuous'
        elif distribution.name in discrete_distributions:
            self.distribution_type = 'discrete'
        else:
            self.distribution_type = 'unknown'
        self.code = _LAMBDA_PATTERN_.format(self.distribution.to_py())
        self.evaluate = eval(self.code)
        if self.observation:
            obs = self.observation.to_py()
            self.evaluate_observation = eval(_LAMBDA_PATTERN_.format(obs))
            self.evaluate_observation_pdf = eval("lambda state, dist: dist.log_pdf({})".format(obs))
        else:
            self.evaluate_observation = None
            self.evaluate_observation_pdf = None

    def __repr__(self):
        result = "{}:\n" \
                 "\tAncestors: {}\n" \
                 "\tDistribution: {}\n".format(self.name,
                                               ', '.join(sorted([v.name for v in self.ancestors])),
                                               repr(self.distribution))
        if len(self.conditions) > 0:
            result += "\tConditions: {}\n".format(', '.join(["{} == {}".format(c.name, v) for c, v in self.conditions]))
        if self.observation:
            result += "\tObservation: {}\n".format(repr(self.observation))
        return result

    def _add_dependent_condition(self, cond: ConditionNode):
        self.dependent_conditions.add(cond)
        for a in self.ancestors:
            a._add_dependent_condition(cond)

    def get_all_ancestors(self):
        result = []
        for a in self.ancestors:
            if a not in result:
                result.append(a)
                result += list(a.get_all_ancestors())
        return set(result)

    @property
    def is_conditional(self):
        return len(self.dependent_conditions) > 0

    @property
    def is_continuous(self):
        return self.distribution_type == 'continuous'

    @property
    def is_discrete(self):
        return self.distribution_type == 'discrete'

    @property
    def is_observed(self):
        return self.observation is not None

    @property
    def is_sampled(self):
        return self.observation is None

    def update(self, state: dict):
        if self.evaluate_observation:
            result = self.evaluate_observation(state)
        else:
            result = self.evaluate(state).sample()
        state[self.name] = result
        return result

    def update_pdf(self, state: dict):
        for cond, truth_value in self.conditions:
            if state[cond.name] != truth_value:
                return 0.0

        dist = self.evaluate(state)
        if self.evaluate_observation_pdf:
            log_pdf = self.evaluate_observation_pdf(state, dist)
        elif self.name in state:
            log_pdf = dist.log_pdf(state[self.name])
        else:
            log_pdf = 0.0

        state['log_pdf'] = state.get('log_pdf', 0.0) + log_pdf
        return log_pdf


class Graph(object):
    """
    The graph
    """

    EMPTY = None

    def __init__(self, vertices:set, data:set=None):
        if data is None:
            data = set()
        arcs = []
        conditions = []
        for v in vertices:
            for a in v.ancestors:
                arcs.append((a, v))
            for c, _ in v.conditions:
                conditions.append(c)
        self.vertices = vertices
        self.data = data
        self.arcs = set(arcs)
        self.conditions = set(conditions)

    def __repr__(self):
        V = '  '.join(sorted([repr(v) for v in self.vertices]))
        A = ', '.join(['({}, {})'.format(u.name, v.name) for (u, v) in self.arcs]) if len(self.arcs) > 0 else "-"
        C = '\n  '.join(sorted([repr(v) for v in self.conditions])) if len(self.conditions) > 0 else "-"
        D = '\n  '.join([repr(u) for u in self.data]) if len(self.data) > 0 else "-"
        return "Vertices V:\n  {V}\nArcs A:\n  {A}\n\nConditions C:\n  {C}\n\nData D:\n  {D}\n".format(V=V, A=A, C=C, D=D)

    @property
    def is_empty(self):
        """
        Returns `True` if the graph is empty (contains no vertices).
        """
        return len(self.vertices) == 0

    def merge(self, other):
        """
        Merges this graph with another graph and returns the result. The original graphs are not modified, but
        a new object is instead created and returned.

        :param other: The second graph to merge with the current one.
        :return:      A new graph-object.
        """
        if other:
            return Graph(set.union(self.vertices, other.vertices), set.union(self.data, other.data))
        else:
            return self

    def get_ordered_list_of_all_nodes(self):
        def extract_number(s):
            result = 0
            for c in s:
                if '0' <= c <= '9':
                    result = result * 10 + ord(c) - ord('0')
            return result

        nodes = {}
        for v in self.vertices:
            nodes[extract_number(v.name)] = v
        for d in self.data:
            nodes[extract_number(d.name)] = d
        for c in self.conditions:
            nodes[extract_number(c.name)] = c
        result = []
        for key in sorted(nodes.keys()):
            result.append(nodes[key])
        return result

    def create_model(self):
        from .foppl_model import Model
        compute_nodes = self.get_ordered_list_of_all_nodes()
        return Model(vertices=self.vertices, arcs=self.arcs, data=self.data,
                     conditionals=self.conditions, compute_nodes=compute_nodes)


Graph.EMPTY = Graph(vertices=set())


def merge(*graphs):
    result = Graph.EMPTY
    for g in graphs:
        result = result.merge(g)
    return result
