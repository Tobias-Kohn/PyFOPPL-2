#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 01. Mar 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_ast_annotators import *
from ast import copy_location as _cl


# TODO: CALL is BROKEN!
# TODO: Implement Expr-With-Prefix

class AstExprWithPrefix(AstNode):

    def __init__(self, expr:AstNode, prefix:AstNode):
        self.expr = expr
        self.prefix = prefix
        assert type(self.expr) is AstNode
        assert type(self.prefix) is AstNode

    def __repr__(self):
        return "ExprWithPrefix(PREFIX:{}, EXPR:{})".format(repr(self.prefix), repr(self.expr))


class Optimizer(ScopedVisitor):

    def get_info(self, node:AstNode):
        return InfoAnnotator().visit(node)

    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        if base is node.base:
            return node
        else:
            return _cl(AstAttribute(base, node.attr), node)

    def visit_binary(self, node:AstBinary):
        if is_symbol(node.left) and is_symbol(node.right) and \
                        node.op in ('-', '/', '//') and node.left.name == node.right.name:
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
                if op in ('+', '|', '^'):
                    return right
                elif op == '-':
                    return _cl(AstUnary('-', right).visit(self), node)
                elif op in ('*', '/', '//', '%', '&', '<<', '>>', '**'):
                    return left

            elif value == 1:
                if op == '*':
                    return right

            elif value == -1:
                if op == '*':
                    return _cl(AstUnary('-', right).visit(self), node)

            if isinstance(right, AstBinary) and is_number(right.left):
                r_value = right.left.value
                if op == right.op and op in ('+', '-', '*', '&', '|'):
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
                if op in ('+', '-', '|', '^'):
                    return left
                elif op == '**':
                    return AstValue(1)
                elif op == '*':
                    return right

            elif value == 1:
                if op in ('*', '/', '**'):
                    return left

            elif value == -1:
                if op in ('*', '/'):
                    return _cl(AstUnary('-', right).visit(self), node)

            if op == '-':
                op = '+'
                value = -value
                right = AstValue(value)
            elif op == '/' and value != 0:
                op = '*'
                value = 1 / value
                right = AstValue(value)

            if isinstance(left, AstBinary) and is_number(left.right):
                l_value = left.right.value
                if op == left.op and op in ('+', '*', '|', '&'):
                    return _cl(AstBinary(left.left, op, AstValue(node.op_function(l_value, value))).visit(self), node)

                elif op == left.op and op == '-':
                    return _cl(AstBinary(left.left, '-', AstValue(l_value + value)).visit(self), node)

                elif op == left.op and op in ('/', '**'):
                    return _cl(AstBinary(left.left, '/', AstValue(l_value * value)).visit(self), node)

                elif op in ['+', '-'] and left.op in ('+', '-'):
                    return _cl(AstBinary(left.left, left.op, AstValue(l_value - value)).visit(self), node)

            if op in ('<<', '>>') and type(value) is int:
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
            return _cl(AstBinary(left, op, right), node)

    def visit_body(self, node:AstBody):
        items = [item.visit(self) for item in node.items]
        items = AstBody(items).items
        if len(items) > 1:
            items = [item for item in items[:-1] if not self.get_info(item).is_expr] + [items[-1]]
        if len(items) == 1:
            return items[0]
        return _cl(AstBody(items), node)

    def visit_call(self, node:AstCall):
        function = self.visit(node.function)
        args = [self.visit(arg) for arg in node.args]
        keywords = { key:self.visit(node.keyword_args[key]) for key in node.keyword_args }
        if isinstance(function, AstFunction):
            with self.create_scope(function.name):
                self.define_all(function.parameters, args, vararg=function.vararg)
                result = self.visit(function.body)

            if self.get_info(result).return_count == 1:
                if isinstance(result, AstReturn) and not result.has_prefix_body:
                    result = result.value
                    return result if result is not None else AstValue(None)

        elif isinstance(function, AstDict):
            if len(args) != 1 or len(keywords) != 0:
                raise TypeError("dict access requires exactly one argument ({} given)".format(len(args) + len(keywords)))
            return self.visit(_cl(AstSubscript(function, args[0]), node))

        return _cl(AstCall(function, args, keywords), node)

    def visit_call_clojure_core_concat(self, node:AstCall):
        import itertools
        if len(node.keyword_args) == 0:
            args = [self.visit(arg) for arg in node.args]
            if all([is_string(item) for item in args]):
                return _cl(AstValue(''.join([item.value for item in args])), node)

            elif all([isinstance(item, AstValueVector) for item in args]):
                return _cl(AstValue(list(itertools.chain([item.value for item in args]))), node)

            elif all([is_vector(item) for item in args]):
                args = [item if isinstance(item, AstVector) else item.to_vector() for item in args]
                return _cl(AstValue(list(itertools.chain([item.value for item in args]))), node)

        return self.visit_call(node)

    def visit_call_clojure_core_conj(self, node:AstCall):
        if len(node.keyword_args) == 0:
            args = [self.visit(arg) for arg in node.args]
            if len(args) > 1 and is_vector(args[0]):
                sequence = args[0]
                for arg in reversed(args[1:]):
                    sequence = sequence.conj(arg)
                return sequence
        return self.visit_call(node)

    def visit_call_clojure_core_cons(self, node:AstCall):
        if len(node.keyword_args) == 0:
            args = [self.visit(arg) for arg in node.args]
            if len(args) > 1 and is_vector(args[-1]):
                sequence = args[-1]
                for arg in reversed(args[:-1]):
                    sequence = sequence.cons(arg)
                return sequence
        return self.visit_call(node)

    def visit_compare(self, node:AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        second_right = self.visit(node.second_right)

        if second_right is None:
            if is_unary_neg(left) and is_unary_neg(right):
                left, right = right.item, left.item
            elif is_unary_neg(left) and is_number(right):
                left, right = AstValue(-right.value), left.item
            elif is_number(left) and is_unary_neg(right) :
                right, left = AstValue(-left.value), right.item

            if is_binary_add_sub(left) and is_number(right):
                left = self.visit(AstBinary(left, '-', right))
                right = AstValue(0)
            elif is_binary_add_sub(right) and is_number(left):
                right = self.visit(AstBinary(right, '-', left))
                left = AstValue(0)

        if is_number(left) and is_number(right):
            result = node.op_function(left.value, right.value)
            if second_right is None:
                return _cl(AstValue(result), node)

            elif is_number(second_right):
                result = result and node.op_function_2(right.value, second_right.value)
                return _cl(AstValue(result), node)

        if node.op in ('in', 'not in') and is_vector(right) and second_right is None:
            op = node.op
            for item in right:
                if left == item:
                    return AstValue(True if op == 'in' else False)
            return AstValue(False if op == 'in' else True)

        return _cl(AstCompare(left, node.op, right, node.second_op, second_right), node)

    def visit_def(self, node:AstDef):
        value = self.visit(node.value)
        self.define(node.name, value, globally=node.global_context)
        if value is not node.value:
            return _cl(AstDef(node.name, value, global_context=node.global_context), node)
        else:
            return node

    def visit_dict(self, node:AstDict):
        items = { key: self.visit(node.items[key]) for key in node.items }
        return _cl(AstDict(items), node)

    def visit_for(self, node:AstFor):
        source = self.visit(node.source)
        if is_vector(source):
            result = AstBody([AstLet([node.target], [item], node.body) for item in source])
            return self.visit(_cl(result, node))
        else:
            with self.create_scope():
                self.protect(node.target)
                body = self.visit(node.body)
                if body is not node.body:
                    return _cl(AstFor(node.target, source, body), node)
        return node

    def visit_function(self, node:AstFunction):
        with self.create_scope(node.name):
            for param in node.parameters:
                self.protect(param)
            self.protect(node.vararg)
            body = self.visit(node.body)
            return _cl(AstFunction(node.name, node.parameters, body,
                                   vararg=node.vararg, doc_string=node.doc_string), node)

    def visit_if(self, node:AstIf):
        if node.has_else and is_unary_not(node.test):
            test = self.visit(node.test.item)
            else_node = self.visit(node.if_node)
            if_node = self.visit(node.else_node)
        else:
            test = self.visit(node.test)
            if_node = self.visit(node.if_node)
            else_node = self.visit(node.else_node)

        if else_node is not None:
            if is_unary_not(test):
                test = test.item
                if_node, else_node = else_node, if_node

        if is_boolean(test):
            if test.value is True:
                return if_node
            elif test.value is False:
                return else_node

        return _cl(AstIf(test, if_node, else_node), node)

    def visit_let(self, node:AstLet):
        if len(node.targets) == 1 and self.get_info(node.source).can_embed:
            if node.is_single_var:
                with self.create_scope():
                    self.define(node.target, self.visit(node.source))
                    body = self.visit(node.body)
                    return _cl(body, node)

            source = self.visit(node.source)
            if is_vector(source) and len(source) == len(node.target):
                with self.create_scope():
                    for t, v in zip(node.target, source):
                        self.define(t, v)
                    body = self.visit(node.body)
                    return _cl(body, node)

        elif len(node.targets) == 1:
            source = self.visit(node.source)
            with self.create_scope():
                self.protect(node.target)
                result = self.visit(node.body)

            if node.is_single_var:
                count = count_variable_usage(node.target, result)
                if count == 1:
                    with self.create_scope():
                        self.define(node.target, source)
                        result = self.visit(result)
                    return _cl(result, node)

            return _cl(AstLet(node.targets, [source], result), node)

        elif len(node.targets) > 1:
            result = node.body
            for target, source in zip(reversed(node.targets), reversed(node.sources)):
                result = self.visit(_cl(AstLet([target], [source], result), node))
            return result

        return node

    def visit_list_for(self, node:AstListFor):
        source = self.visit(node.source)
        if is_vector(source) and node.test is None:
            result = makeVector([AstLet([node.target], [item], node.expr) for item in source])
            return self.visit(_cl(result, node))
        return node

    def visit_observe(self, node:AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        if dist is node.dist and value is node.value:
            return node
        else:
            return _cl(AstObserve(dist, value), node)

    def visit_return(self, node:AstReturn):
        value = self.visit(node.value)
        if isinstance(value, AstBody):
            items = value.items
            ret = self.visit(_cl(AstReturn(items[-1]), node))
            return _cl(AstBody(items[:-1] + [ret]), value)
        elif isinstance(value, AstLet):
            ret = self.visit(_cl(AstReturn(value.body), node))
            return _cl(AstLet(value.targets, value.sources, ret), value)

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

        if isinstance(base, AstDict) and isinstance(index, AstValue):
            default = self.visit(node.default)
            return base.items.get(index.value, default)

        return _cl(AstSubscript(base, index), node)

    def visit_symbol(self, node:AstSymbol):
        if node.protected:
            return node
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

        if op == 'not':
            if isinstance(item, AstCompare) and item.second_right is None:
                return _cl(AstCompare(item.left, item.neg_op, item.right), node)

            if isinstance(item, AstBinary) and item.op in ('and', 'or'):
                return self.visit(_cl(AstBinary(AstUnary('not', item.left), 'and' if item.op == 'or' else 'or',
                                                AstUnary('not', item.right)), node))

            if is_boolean(item):
                return _cl(AstValue(not item.value), node)

        if item is node.item:
            return node
        else:
            return _cl(AstUnary(node.op, item), node)

    def visit_vector(self, node:AstVector):
        items = [item.visit(self) for item in node.items]
        return makeVector(items)

    def visit_while(self, node:AstWhile):
        # We must be very careful with optimizing a while-loop because
        # variables might change during the execution of the loop.
        test = self.visit(node.test)
        if is_boolean(test) and not test.value:
            return AstBody([])
        return node


def optimize(ast):
    opt = Optimizer()
    result = opt.visit(ast)
    if type(result) in (list, tuple) and len(result) == 1:
        return result[0]
    else:
        return result
