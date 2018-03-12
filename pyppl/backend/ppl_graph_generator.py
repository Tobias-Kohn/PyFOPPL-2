#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 12. Mar 2018, Tobias Kohn
#
from pyppl.ppl_ast import *
from .ppl_graph_factory import GraphFactory


class GraphGenerator(ScopedVisitor):

    def __init__(self, factory: GraphFactory):
        super().__init__()
        self.factory = factory
        self.nodes = []

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

    def visit_builtin(self, node: AstCallBuiltin):
        args, parents = self._visit_items(node.args)
        return AstCallBuiltin(node.function_name, args), parents

    def visit_call(self, node: AstCall):
        args, parents = self._visit_items(node.args)
        kw_args, kw_parents = self._visit_dict(node.keyword_args)
        parents = set.union(parents, kw_parents)
        return AstCall(node.function, args, kw_args), parents

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
        _ = self.factory.create_condition_node(node.test, parents)

        # TODO: implement
        return self.visit_node(node)

    def visit_import(self, node: AstImport):
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
        return AstSymbol(name, node=node), set(node)

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
        return makeSubscript(base, index), set.union(b_parents, i_parents)

    def visit_symbol(self, node: AstSymbol):
        item = self.resolve(node.name)
        if item is not None:
            return item
        elif node.node is not None:
            return node, set(node.node)
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
                name = getattr(node, 'name', 'd???')
                self.nodes.append(node)
                return AstSymbol(name, node=node), set()
        return node, set()

    def visit_vector(self, node: AstVector):
        items, parents = self._visit_items(node.items)
        result = makeVector(items)
        if is_vector(result) and len(result) > 3:
            node = self.factory.create_data_node(result, parents)
            if node is not None:
                name = getattr(node, 'name', 'd???')
                self.nodes.append(node)
                return AstSymbol(name, node=node), parents
        return result, parents
