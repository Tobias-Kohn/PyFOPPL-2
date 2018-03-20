#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Mar 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..aux.ppl_transform_visitor import TransformVisitor


class Symbol(object):

    def __init__(self, name):
        self.name = name
        self.counter = 0

    def get_new_instance(self):
        self.counter += 1
        return self.get_current_instance()

    def get_current_instance(self):
        if self.counter == 1:
            return self.name
        else:
            return self.name + str(self.counter)


class SymbolScope(object):

    def __init__(self, prev):
        self.prev = prev
        self.bindings = {}

    def get_current_symbol(self, name: str):
        if name in self.bindings:
            return self.bindings[name]
        elif self.prev is not None:
            return self.prev.get_current_symbol(name)
        else:
            return name

    def has_current_symbol(self, name: str):
        if name in self.bindings:
            return True
        elif self.prev is not None:
            return self.prev.has_current_symbol(name)
        else:
            return False

    def set_current_symbol(self, name: str, instance_name: str):
        self.bindings[name] = instance_name


class StaticAssignments(TransformVisitor):

    def __init__(self):
        super().__init__()
        self.symbols = {}
        self.symbol_scope = SymbolScope(None)

    def new_symbol_instance(self, name: str):
        if name not in self.symbols:
            self.symbols[name] = Symbol(name)
        result = self.symbols[name].get_new_instance()
        self.symbol_scope.set_current_symbol(name, result)
        return result

    def access_symbol(self, name: str):
        return self.symbol_scope.get_current_symbol(name)

    def has_symbol(self, name: str):
        return self.symbol_scope.has_current_symbol(name)

    def begin_scope(self):
        self.symbol_scope = SymbolScope(self.symbol_scope)

    def end_scope(self):
        scope = self.symbol_scope
        self.symbol_scope = scope.prev
        return scope.bindings

    def split_body(self, node: AstNode):
        if isinstance(node, AstBody):
            if len(node) == 0:
                return None, AstValue(None)
            elif len(node) == 1:
                return None, node[0]
            else:
                return node.items[:-1], node.items[-1]
        else:
            return None, node

    def visit_and_split(self, node: AstNode):
        return self.split_body(self.visit(node))

    def visit_in_scope(self, node: AstNode):
        self.begin_scope()
        result = self.visit(node)
        symbols = self.end_scope()
        return symbols, result


    def visit_attribute(self, node:AstAttribute):
        prefix, base = self.visit_and_split(node.base)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(base=base)))
        if base is node.base:
            return node
        else:
            return node.clone(base=base)

    def visit_binary(self, node:AstBinary):
        prefix, left = self.visit_and_split(node.left)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(left=left)))
        prefix, right = self.visit_and_split(node.right)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(right=right)))

        if left is node.left and right is node.right:
            return node
        else:
            return node.clone(left=left, right=right)

    def visit_call(self, node: AstCall):
        prefix = []
        args = []
        for item in node.args:
            p, a = self.visit_and_split(item)
            if p is not None:
                prefix += p
            args.append(a)

        if len(prefix) > 0:
            return self.visit(makeBody(prefix, node.clone(args=args)))
        else:
            return node.clone(args=args)

    def visit_compare(self, node: AstCompare):
        prefix, left = self.visit_and_split(node.left)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(left=left)))
        prefix, right = self.visit_and_split(node.right)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(right=right)))

        if node.second_right is not None:
            prefix, second_right = self.visit_and_split(node.second_right)
            if prefix is not None:
                return self.visit(makeBody(prefix, node.clone(second_right=second_right)))
        else:
            second_right = None

        if left is node.left and right is node.right and second_right is node.second_right:
            return node
        else:
            return node.clone(left=left, right=right, second_right=second_right)

    def visit_def(self, node: AstDef):
        if isinstance(node.value, AstObserve):
            # We can never assign an observe to something!
            return self.visit(node.value)

        elif isinstance(node.value, AstSample):
            # We need to handle this as a special case in order to avoid an infinite loop
            prefix, dist = self.visit_and_split(node.value.dist)
            if prefix is not None:
                return self.visit(makeBody(prefix, node.clone(value=node.value.clone(dist=dist))))
            if dist is node.value.dist:
                return node
            else:
                return node.clone(value=node.value.clone(dist=dist))

        prefix, value = self.visit_and_split(node.value)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(value=value)))

        elif isinstance(value, AstFunction):
            return AstBody([])

        name = self.new_symbol_instance(node.name)
        if name is node.name and value is node.value:
            return node
        else:
            return node.clone(name=name, value=value)

    def visit_dict(self, node: AstDict):
        prefix = []
        items = {}
        for key in node.items:
            item = node.items[key]
            p, i = self.visit_and_split(item)
            if p is not None:
                prefix += p
            items[key] = i
        if len(prefix) > 0:
            return self.visit(makeBody(prefix, AstDict(items)))
        else:
            return AstDict(items)

    def visit_for(self, node: AstFor):
        prefix, source = self.visit_and_split(node.source)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(source=source)))

        body = self.visit(node.body)
        if source is node.source and body is node.body:
            return node
        else:
            return node.clone(source=source, body=body)

    def visit_if(self, node: AstIf):

        def phi(key, cond, left, right):
            return AstDef(key, AstIf(cond, AstSymbol(left), AstSymbol(right)))

        prefix, test = self.visit_and_split(node.test)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(test=test)))

        if isinstance(test, AstValue):
            if test.value is True:
                return self.visit(node.if_node)
            elif test.value is False or test.value is None:
                return self.visit(node.else_node)

        if_symbols, if_node = self.visit_in_scope(node.if_node)
        else_symbols, else_node = self.visit_in_scope(node.else_node)
        keys = set.union(set(if_symbols.keys()), set(else_symbols.keys()))
        if len(keys) == 0:
            if test is node.test and if_node is node.if_node and else_node is node.else_node:
                return node
            else:
                return node.clone(test=node.test, if_node=if_node, else_node=else_node)
        else:
            result = []
            if not isinstance(test, AstSymbol):
                tmp = generate_temp_var()
                result.append(AstDef(tmp, test))
                test = AstSymbol(tmp)
            result.append(node.clone(test=test, if_node=if_node, else_node=else_node))
            for key in keys:
                if key in if_symbols and key in else_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, if_symbols[key], else_symbols[key]))
                elif not self.has_symbol(key):
                    pass
                elif key in if_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, if_symbols[key], self.access_symbol(key)))
                elif key in else_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, self.access_symbol(key), else_symbols[key]))
            return makeBody(result)

    def visit_let(self, node: AstLet):
        if node.target == '_':
            result = makeBody(node.source, node.body)
        else:
            result = makeBody(AstDef(node.target, node.source), node.body)
        return self.visit(result)

    def visit_list_for(self, node: AstListFor):
        prefix, source = self.visit_and_split(node.source)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(source=source)))

        expr = self.visit(node.expr)
        if source is node.source and expr is node.expr:
            return node
        else:
            return node.clone(source=source, expr=expr)

    def visit_observe(self, node: AstObserve):
        prefix, dist = self.visit_and_split(node.dist)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(dist=dist)))
        prefix, value = self.visit_and_split(node.value)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(value=value)))
        return node

    def visit_sample(self, node: AstSample):
        prefix, dist = self.visit_and_split(node.dist)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(dist=dist)))
        tmp = generate_temp_var()
        return self.visit(makeBody([AstDef(tmp, node), AstSymbol(tmp)]))

    def visit_symbol(self, node: AstSymbol):
        name = self.access_symbol(node.name)
        if name != node.name:
            return node.clone(name=name)
        else:
            return node

    def visit_unary(self, node: AstUnary):
        prefix, item = self.visit_and_split(node.item)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(item=item)))
        if item is node.item:
            return node
        else:
            return node.clone(item=item)

    def visit_vector(self, node: AstVector):
        prefix = []
        items = []
        for item in node.items:
            p, i = self.visit_and_split(item)
            if p is not None:
                prefix += p
            items.append(i)
        if len(prefix) > 0:
            return self.visit(makeBody(prefix, makeVector(items)))
        else:
            return makeVector(items)

    def visit_while(self, node: AstWhile):
        prefix, test = self.visit_and_split(node.test)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(test=test)))

        body = self.visit(node.body)
        if test is node.test and body is node.body:
            return node
        else:
            return node.clone(test=test, body=body)
