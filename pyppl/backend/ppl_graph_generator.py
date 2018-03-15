#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 15. Mar 2018, Tobias Kohn
#
from pyppl.ppl_ast import *
from .ppl_graph_factory import GraphFactory


class ConditionScope(object):

    def __init__(self, prev, condition: AstNode):
        self.prev = prev
        self.condition = condition
        self.truth_value = True

    def switch_branch(self):
        if is_unary_not(self.condition):
            self.condition = self.condition.item
        elif isinstance(self.condition, AstNode):
            self.condition = AstUnary('not', self.condition)
        else:
            self.truth_value = not self.truth_value


class ConditionScopeContext(object):

    def __init__(self, visitor):
        self.visitor = visitor

    def __enter__(self):
        return self.visitor.conditions

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visitor.leave_condition()


class GraphGenerator(ScopedVisitor):

    def __init__(self, factory: GraphFactory):
        super().__init__()
        if factory is None:
            factory = GraphFactory()
        self.factory = factory
        self.nodes = []
        self.conditions = None  # type: ConditionScope

    def enter_condition(self, condition):
        self.conditions = ConditionScope(self.conditions, condition)

    def leave_condition(self):
        self.conditions = self.conditions.prev

    def switch_condition(self):
        self.conditions.switch_branch()

    def create_condition(self, condition):
        self.enter_condition(condition)
        return ConditionScopeContext(self)

    def _visit_dict(self, items):
        result = {}
        parents = set()
        for key in items.keys():
            item, parent = self.visit(items[key])
            result[key] = item
            parents = set.union(parents, parent)
        return result, parents

    def _visit_items(self, items):
        result = []
        parents = set()
        for item, parent in (self.visit(item) for item in items):
            result.append(item)
            parents = set.union(parents, parent)
        return result, parents

    def visit_node(self, node: AstNode):
        raise RuntimeError("cannot compile '{}'".format(node))

    def visit_attribute(self, node:AstAttribute):
        return self.visit_node(node)

    def visit_binary(self, node:AstBinary):
        left, l_parents = self.visit(node.left)
        right, r_parents = self.visit(node.right)
        return AstBinary(left, node.op, right), set.union(l_parents, r_parents)

    def visit_body(self, node:AstBody):
        items, parents = self._visit_items(node.items)
        return makeBody(items), parents

    def visit_call(self, node: AstCall):
        args, parents = self._visit_items(node.args)
        return AstCall(node.function, args, node.keywords), parents

    def visit_compare(self, node: AstCompare):
        left, l_parents = self.visit(node.left)
        right, r_parents = self.visit(node.right)
        if node.second_right is not None:
            second_right, sc_parents = self.visit(node.second_right)
            parents = set.union(l_parents, r_parents)
            parents = set.union(parents, sc_parents)
            return AstCompare(left, node.op, right, node.second_op, second_right), parents
        else:
            return AstCompare(left, node.op, right), set.union(l_parents, r_parents)

    def visit_def(self, node: AstDef):
        self.define(node.name, self.visit(node.value))
        return AstValue(None), set()

    def visit_dict(self, node: AstDict):
        items, parents = self._visit_dict(node.items)
        return AstDict(items), parents

    def visit_for(self, node: AstFor):
        source, s_parents = self.visit(node.source)
        body, b_parents = self.visit(node.body)
        parents = set.union(s_parents, b_parents)
        return AstFor(node.target, source, body), parents

    def visit_if(self, node: AstIf):
        test, parents = self.visit(node.test)
        cond_node = self.factory.create_condition_node(test, parents)
        if cond_node is not None:
            self.nodes.append(cond_node)
            name = getattr(cond_node, 'name', 'cond_???')
            test = AstSymbol(name, node=cond_node)

        with self.create_condition(cond_node):
            a_node, a_parents = self.visit(node.if_node)
            parents = set.union(parents, a_parents)
            self.switch_condition()
            b_node, b_parents = self.visit(node.else_node)
            parents = set.union(parents, b_parents)

        return AstIf(test, a_node, b_node), parents

    def visit_import(self, _):
        return AstValue(None), set()

    def visit_let(self, node: AstLet):
        self.define(node.target, self.visit(node.source))
        return self.visit(node.body)

    def visit_list_for(self, node: AstListFor):
        source, s_parents = self.visit(node.source)
        expr, e_parents = self.visit(node.expr)
        parents = set.union(s_parents, e_parents)
        if node.test is not None:
            test, t_parents = self.visit(node.test)
            parents = set.union(parents, t_parents)
        else:
            test = None
        return AstListFor(node.target, source, expr, test), parents

    def visit_observe(self, node: AstObserve):
        dist, d_parents = self.visit(node.dist)
        value, v_parents = self.visit(node.value)
        parents = set.union(d_parents, v_parents)
        node = self.factory.create_observe_node(dist, value, parents)
        name = getattr(node, 'name', 'y???')
        self.nodes.append(node)
        return AstSymbol(name, node=node), set()

    def visit_sample(self, node: AstSample):
        dist, parents = self.visit(node.dist)
        node = self.factory.create_sample_node(dist, parents)
        name = getattr(node, 'name', 'x???')
        self.nodes.append(node)
        return AstSymbol(name, node=node), { node }

    def visit_slice(self, node: AstSlice):
        base, parents = self.visit(node.base)
        if node.start is not None:
            start, a_parents = self.visit(node.start)
            parents = set.union(parents, a_parents)
        else:
            start = None
        if node.stop is not None:
            stop, a_parents = self.visit(node.stop)
            parents = set.union(parents, a_parents)
        else:
            stop = None
        return AstSlice(base, start, stop), parents

    def visit_subscript(self, node: AstSubscript):
        base, b_parents = self.visit(node.base)
        index, i_parents = self.visit(node.index)
        if is_vector(base) and is_integer(index):
            return self.visit(base[index.value])
        return makeSubscript(base, index), set.union(b_parents, i_parents)

    def visit_symbol(self, node: AstSymbol):
        item = self.resolve(node.name)
        if item is not None:
            return item
        elif node.node is not None:
            return node, { node.node }
        else:
            raise RuntimeError("symbol not found: '{}'".format(node.original_name))

    def visit_unary(self, node: AstUnary):
        item, parents = self.visit(node.item)
        return AstUnary(node.op, item), parents

    def visit_value(self, node: AstValue):
        return node, set()

    def visit_value_vector(self, node: AstValueVector):
        if len(node) > 3:
            node = self.factory.create_data_node(node, set())
            if node is not None:
                name = getattr(node, 'name', 'data_???')
                self.nodes.append(node)
                return AstSymbol(name, node=node), set()
        return node, set()

    def visit_vector(self, node: AstVector):
        items, parents = self._visit_items(node.items)
        result = makeVector(items)
        return result, parents

    def generate_code(self, model_template: str = None):
        return self.factory.generate_code(model_template=model_template)
