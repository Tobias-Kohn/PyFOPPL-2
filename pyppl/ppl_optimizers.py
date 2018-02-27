#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 27. Feb 2018, Tobias Kohn
#
from .ppl_ast import *
from ast import copy_location as _cl

class Optimizer(ScopedVisitor):

    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        if base is node.base:
            return node
        else:
            return _cl(AstAttribute(base, node.attr), node)

    def visit_binary(self, node:AstBinary):
        if is_symbol(node.left) and is_symbol(node.right) and \
                        node.op in ['-', '/', '//'] and node.left.name == node.right.name:
            return AstValue(0 if node.op == '-' else 1)

        left = node.left.visit(self)
        right = node.right.visit(self)
        op = node.op
        if is_number(left) and is_number(right):
            return AstValue(node.op_function(left.value, right.value))

        elif op == '+' and is_string(left) and is_string(right):
            return _cl(AstValue(left.value + right.value), node)

        elif op == '+' and isinstance(left, AstValueVector) and isinstance(right, AstValueVector):
            return _cl(AstValueVector(left.items + right.items), node)

        elif op == '*' and (is_string(left) and is_integer(right)) or (is_integer(left) and is_string(right)):
            return _cl(AstValue(left.value * right.value), node)

        elif op == '*' and isinstance(left, AstValueVector) and is_integer(right):
            return _cl(AstValueVector(left.items * right.value), node)

        elif op == '*' and is_integer(left) and isinstance(right, AstValueVector):
            return _cl(AstValueVector(left.value * right.items), node)

        elif is_number(left):
            value = left.value
            if value == 0:
                if op in ['+', '|', '^']:
                    return right
                elif op == '-':
                    return _cl(AstUnary('-', right).visit(self), node)
                elif op in ['*', '/', '//', '%', '&', '<<', '>>', '**']:
                    return left

            elif value == 1:
                if op == '*':
                    return right

            elif value == -1:
                if op == '*':
                    return _cl(AstUnary('-', right).visit(self), node)

            if isinstance(right, AstBinary) and is_number(right.left):
                r_value = right.left.value
                if op == right.op and op in ['+', '-', '*', '&', '|']:
                    return _cl(AstBinary(AstValue(node.op_function(value, r_value)),
                                     '+' if op == '-' else op,
                                     right.right).visit(self), node)

                elif op == right.op and op == '/':
                    return _cl(AstBinary(AstValue(value / r_value), '*', right.right).visit(self), node)

                elif op in ['+', '-'] and right.op in ['+', '-']:
                    return _cl(AstBinary(AstValue(node.op_function(value, r_value)), '-', right.right).visit(self), node)

        elif is_number(right):
            value = right.value
            if value == 0:
                if op in ['+', '-', '|', '^']:
                    return left
                elif op == '**':
                    return AstValue(1)
                elif op == '*':
                    return right

            elif value == 1:
                if op in ['*', '/', '**']:
                    return left

            elif value == -1:
                if op in ['*', '/']:
                    return _cl(AstUnary('-', right).visit(self), node)

            if isinstance(left, AstBinary) and is_number(left.right):
                l_value = left.right.value
                if op == left.op and op in ['+', '*', '|', '&']:
                    return _cl(AstBinary(left.left, op, AstValue(node.op_function(l_value, value))).visit(self), node)

                elif op == left.op and op == '-':
                    return _cl(AstBinary(left.left, '-', AstValue(l_value + value)).visit(self), node)

                elif op == left.op and op in ['/', '**']:
                    return _cl(AstBinary(left.left, '/', AstValue(l_value * value)).visit(self), node)

                elif op in ['+', '-'] and left.op in ['+', '-']:
                    return _cl(AstBinary(left.left, left.op, AstValue(l_value - value)).visit(self), node)

            if op in ['<<', '>>'] and type(value) is int:
                base = 2 if op == '<<' else 0.5
                return _cl(AstBinary(left, '*', AstValue(base ** value)), node)

        elif is_boolean(left) and is_boolean(right):
            return _cl(AstValue(node.op_function(left.value, right.value)), node)

        elif is_boolean(left):
            if op == 'and':
                return right if left.value else AstValue(False)
            if op == 'or':
                return right if not left.value else AstValue(True)

        elif is_boolean(right):
            if op == 'and':
                return left if right.value else AstValue(False)
            if op == 'or':
                return left if not right.value else AstValue(True)

        if op == '-' and isinstance(right, AstUnary) and right.op == '-':
            return _cl(AstBinary(left, '+', right.item).visit(self), node)

        if left is node.left and right is node.right:
            return node
        else:
            return _cl(AstBinary(left, node.op, right), node)

    def visit_body(self, node:AstBody):
        items = [item.visit(self) for item in node.items]
        items = [item for item in items if item is not None]
        if len(items) == 1:
            return items[0]
        return _cl(AstBody(items), node)

    def visit_call(self, node:AstCall):
        # TODO: make sure we do not get rid of side-effects
        # TODO: what about the 'return'-statement...?
        function = self.visit(node.function)
        args = [self.visit(arg) for arg in node.args]
        keywords = { key:self.visit(node.keyword_args[key]) for key in node.keyword_args }
        if isinstance(function, AstFunction):
            self.enter_scope(function.name)
            try:
                self.define_all(function.parameters, args, vararg=function.vararg)
                result = self.visit(function.body)
            finally:
                self.leave_scope()
            if result is not None:
                return result

        return _cl(AstCall(function, args, keywords), node)

    def visit_compare(self, node:AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        second_right = self.visit(node.second_right)

        if is_number(left) and is_number(right):
            result = node.op_function(left.value, right.value)
            if second_right is None:
                return _cl(AstValue(result), node)

            elif is_number(second_right):
                result = result and node.op_function_2(right.value, second_right.value)
                return _cl(AstValue(result), node)

        return _cl(AstCompare(left, node.op, right, node.second_op, second_right), node)

    def visit_def(self, node:AstDef):
        value = self.visit(node.value)
        if value is not node.value:
            return _cl(AstDef(node.name, value), node)
        else:
            return node

    def visit_dict(self, node:AstDict):
        items = { key: self.visit(node.items[key]) for key in node.items }
        return _cl(AstDict(items), node)

    def visit_for(self, node:AstFor):
        source = self.visit(node.source)
        body = self.visit(node.body)
        return _cl(AstFor(node.target, source, body), node)

    def visit_function(self, node:AstFunction):
        body = self.visit(node.body)
        return _cl(AstFunction(node.name, node.parameters, body,
                               vararg=node.vararg, doc_string=node.doc_string), node)

    def visit_if(self, node:AstIf):
        test = self.visit(node.test)
        if_node = self.visit(node.if_node)
        else_node = self.visit(node.else_node)

        if is_boolean(test):
            if test.value is True:
                return if_node
            elif test.value is False:
                return else_node

        return _cl(AstIf(test, if_node, else_node), node)

    def visit_let(self, node:AstLet):
        sources = [self.visit(item) for item in node.sources]
        body = self.visit(node.body)
        return _cl(AstLet(node.targets, sources, body), node)

    def visit_list_for(self, node:AstListFor):
        source = self.visit(node.source)
        expr = self.visit(node.expr)
        test = self.visit(node.test)
        return _cl(AstListFor(node.target, source, expr, test), node)

    def visit_observe(self, node:AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        if dist is node.dist and value is node.value:
            return node
        else:
            return _cl(AstObserve(dist, value), node)

    def visit_return(self, node:AstReturn):
        value = self.visit(node.value)
        if value is not node.value:
            return _cl(AstReturn(value), node)
        else:
            return node

    def visit_sample(self, node:AstSample):
        dist = self.visit(node.dist)
        if dist is not node.dist:
            return _cl(AstSample(dist), node)
        else:
            return node

    def visit_slice(self, node:AstSlice):
        base = self.visit(node.base)
        start = self.visit(node.start)
        stop = self.visit(node.stop)

        if (is_integer(start) or start is None) and (is_integer(stop) or stop is None):
            if isinstance(base, AstValueVector) or isinstance(base, AstVector):
                start = start.value if start is not None else None
                stop = stop.value if stop is not None else None
                if start is not None and stop is not None:
                    return _cl(makeVector(base.items[start:stop]), node)
                elif start is not None:
                    return _cl(makeVector(base.items[start:]), node)
                elif stop is not None:
                    return _cl(makeVector(base.items[:stop]), node)
                else:
                    return _cl(makeVector(base.items), node)

        return _cl(AstSlice(base, start, stop), node)

    def visit_subscript(self, node:AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        if is_integer(index):
            if isinstance(base, AstValueVector):
                return _cl(AstValue(base.items[index.value]), node)
            elif isinstance(base, AstVector):
                return _cl(base.items[index.value], node)

        return _cl(AstSubscript(base, index), node)

    def visit_symbol(self, node:AstSymbol):
        value = self.resolve(node.name)
        if value is not None:
            return value
        else:
            return node

    def visit_unary(self, node:AstUnary):
        item = node.item.visit(self)
        op = node.op
        if op == '+':
            return item

        if isinstance(item, AstUnary) and op == item.op:
            return item.item

        if is_number(item):
            if op == '-':
                return _cl(AstValue(-item.value), node)

        if item is node.item:
            return node
        else:
            return _cl(AstUnary(node.op, item), node)

    def visit_vector(self, node:AstVector):
        items = [item.visit(self) for item in node.items]
        return makeVector(items)

    def visit_while(self, node:AstWhile):
        test = self.visit(node.test)
        body = self.visit(node.body)
        if is_boolean(test) and not test.value:
            return AstBody([])
        return _cl(AstWhile(test, body), node)
