#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 12. Mar 2018, Tobias Kohn
#
from typing import Optional


class GraphNode(object):
    """
    The base class for all nodes, including the actual graph vertices, but also conditionals, data, and possibly
    parameters.

    Each node has a name, which is usually generated automatically. The generation of the name is based on a simple
    counter. This generated name (i.e. the counter value inside the name) is used later on to impose a compute order
    on the nodes (see the method `get_ordered_list_of_all_nodes` in the `graph`). Hence, you should not change the
    naming scheme unless you know exactly what you are doing!

    The set of ancestors provides the edges for the graph and the graphical model, respectively. Note that all
    ancestors are always vertices. Conditions, parameters, data, etc. are hold in other fields. This ensures that by
    looking at the ancestors of vertices, we get the pure graphical model.

    Finally, the methods `evaluate`, `update` and `update_pdf` are used by the model to sample values and compute
    log-pdf, etc. Of course, `evaluate` is just a placeholder here so as to define a minimal interface. Usually, you
    will use `update` and `update_pdf` instead of `evaluate`. However, given a `state`-dictionary holding all the
    necessary values, it is save to call `evaluate`.
    """

    def __init__(self, name: str, ancestors: Optional[set]=None):
        if ancestors is None:
            ancestors = set()
        self.ancestors = ancestors
        self.name = name
        self.original_name = name
        assert type(self.ancestors) is set
        assert type(self.name) is str
        assert all([isinstance(item, GraphNode) for item in self.ancestors])

    @property
    def display_name(self):
        if hasattr(self, 'original_name'):
            name = self.original_name
            if name is not None and '.' in name:
                name = name.split('.')[-1]
            if name is not None and len(name) > 0:
                return name.replace('_', '')
        return self.name[-3:]

    def create_repr(self, caption: str, **fields):
        if len(fields) > 0:
            key_len = max(max([len(key) for key in fields]), 9)
            fmt = "  {:" + str(key_len+2) + "}{}"
            result = [fmt.format(key+':', fields[key]) for key in fields]
        else:
            fmt = "  {:11}{}"
            result = []
        result.insert(0, fmt.format("Ancestors:", ', '.join([item.name for item in self.ancestors])))
        result.insert(0, fmt.format("Name:", self.name))
        return "{}\n{}".format(caption, '\n'.join(result))

    def __repr__(self):
        return self.create_repr(self.name)

    def get_code(self):
        raise NotImplemented


####################################################################################################


class ConditionNode(GraphNode):
    """
    A `ConditionNode` represents a condition that depends on stochastic variables (vertices). It is not directly
    part of the graphical model, but you can think of conditions to be attached to a specific vertex.

    Usually, we try to transform all conditions into the form `f(state) >= 0` (this is not possible for `f(X) == 0`,
    through). However, if the condition satisfies this format, the node object has an associated `function`, which
    can be evaluated on its own. In other words: you can not only check if a condition is `True` or `False`, but you
    can also gain information about the 'distance' to the 'border'.
    """

    def __init__(self, name: str, *, ancestors: Optional[set]=None, cond_code: str):
        super().__init__(name, ancestors)
        self.cond_code = cond_code

    def __repr__(self):
        return self.create_repr("Condition", Condition=self.cond_code)

    def gen_log_pdf_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.cond_code
        return "{} = {}".format(target, result)

    def gen_sampling_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.cond_code
        return "{} = {}".format(target, result)

    def get_code(self):
        return self.cond_code


class DataNode(GraphNode):
    """
    Data nodes do not carry out any computation, but provide the data. They are used to keep larger data set out
    of the code, as large lists are replaced by symbols.
    """

    def __init__(self, name: str, *, ancestors: Optional[set]=None, data: str):
        super().__init__(name, ancestors)
        self.data_code = data

    def __repr__(self):
        return self.create_repr("Data", Data=self.data_code)

    def gen_log_pdf_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.data_code
        return "{} = {}".format(target, result)

    def gen_sampling_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.data_code
        return "{} = {}".format(target, result)

    def get_code(self):
        return self.data_code


class Vertex(GraphNode):
    """
    Vertices play the crucial and central role in the graphical model. Each vertex represents either the sampling from
    a distribution, or the observation of such a sampled value.

    You can get the entire graphical model by taking the set of vertices and their `ancestors`-fields, containing all
    vertices, upon which this vertex depends. However, there is a plethora of additional fields, providing information
    about the node and its relationship and status.

    `name`:
      The generated name of the vertex. See also: `original_name`.
    `original_name`:
      In contrast to the `name`-field, this field either contains the name attributed to this value in the original
      code, or `None`.
    `ancestors`:
      The set of all parent vertices. This contains only the ancestors, which are in direct line, and not the parents
      of parents. Use the `get_all_ancestors()`-method to retrieve a full list of all ancestors (including parents of
      parents of parents of ...).
    `dist_ancestors`:
      The set of ancestors used for the distribution/sampling, without those used inside the conditions.
    `cond_ancestors`:
      The set of ancestors, which are linked through conditionals.
    `data`:
      A set of all data nodes, which provide data used in this vertex.
    `distribution`:
      The distribution is an AST/IR-structure, which is usually not used directly, but rather for internal purposes,
      such as extracting the name and type of the distribution.
    `distribution_name`:
      The name of the distribution, such as `Normal` or `Gamma`.
    `distribution_type`:
      Either `"continuous"` or `"discrete"`. You will usually query this field using one of the properties
      `is_continuous` or `is_discrete`.
    `observation`:
      The observation in an AST/IR-structure, which is usually not used directly, but rather for internal purposes.
    `conditions`:
      The set of all conditions under which this vertex is evaluated. Each item in the set is actually a tuple of
      a `ConditionNode` and a boolean value, to which the condition should evaluate. Note that the conditions are
      not owned by a vertex, but might be shared across several vertices.
    `dependent_conditions`:
      The set of all conditions that depend on this vertex. In other words, all conditions which contain this
      vertex in their `get_all_ancestors`-set.
    `sample_size`:
      The dimension of the samples drawn from this distribution.
    `support_size`:
      Used for the 'categorical' distribution; basically the length of the vector/list in the first argument.
    `code`:
      The original code for the `evaluate`-method as a string. This is mostly used for debugging.
    """

    def __init__(self, name: str, *, ancestors: Optional[set]=None, dist_code: str):
        super().__init__(name, ancestors)
        self.dist_code = dist_code

    def __repr__(self):
        return self.create_repr("Vertex", DistCode=self.dist_code)

    def gen_log_pdf_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.dist_code
        return "{}_dist = {}\nlog_pdf += {}_dist.pdf({})".format(self.name, result, self.name, target)

    def gen_sampling_code(self, state_object: Optional[str] = None):
        target = "{}" if state_object is None else state_object + "['{}']"
        target = target.format(self.name)
        result = self.dist_code
        return "{}_dist = {}\n{} = {}_dist.sample()".format(self.name, result, target, self.name)

    def get_code(self):
        return self.dist_code
