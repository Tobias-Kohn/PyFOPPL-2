#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 05. Mar 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_ast_annotators import *
from ast import copy_location as _cl


# Note: Why do we need to protect all mutable variables?
#   During the optimisation, we regularly visit a part of the AST multiple times, and we might even visit a part of
#   the AST even though it might never actually be executed by the program. With LISP-based code, this is usually not
#   a problem. However, with Python, a problem arises with statements such as `x += 1`. If we do not protect the
#   variable `x`, we might accidentally increase the value of `x` more than once (or, in case of an `if`-statement,
#   more than zero times), leading to wrong results.
#   Hence, whenever we enter a new scope, we scan for all variables that are "defined" more than once, and then
#   protect them, making them kind of "read-only".


# When unrolling a while-loop, we have a maximum number of iterations:
MAX_WHILE_ITERATIONS = 100


def _all_(coll, p):
    return all([p(item) for item in coll])

def _all_equal(coll, f=None):
    if f is not None:
        coll = [f(item) for item in coll]
    if len(coll) > 0:
        return len([item for item in coll if item != coll[0]]) == 0
    else:
        return True

def _all_instances(coll, cls):
    return all([isinstance(item, cls) for item in coll])



class Optimizer(ScopedVisitor):

    def __init__(self):
        super().__init__()

    def parse_args(self, args:list):
        can_factor_out = True
        prefix = []
        result = []
        for arg in args:
            arg = self.visit(arg)
            info = get_info(arg)
            if can_factor_out and isinstance(arg, AstBody) and not info.has_changed_vars:
                if len(arg) == 0:
                    result.append(AstValue(None))
                elif len(arg) == 1:
                    result.append(arg.items[0])
                else:
                    prefix += arg.items[:-1]
                    result.append(arg.items[-1])
            else:
                can_factor_out = can_factor_out and info.is_expr
                result.append(arg)

        return prefix, result

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
            items = [item for item in items[:-1] if not get_info(item).is_expr] + [items[-1]]

        free_vars = [get_info(item).free_vars for item in items]
        i = 0
        while i < len(items):
            item = items[i]
            if isinstance(item, AstDef) and (self.is_global_scope or not item.global_context):
                if all([item.name not in fv for fv in free_vars]):
                    del items[i]
                    continue
            i += 1

        if len(items) == 1:
            return items[0]
        return _cl(AstBody(items), node)

    def visit_call(self, node:AstCall):
        function = self.visit(node.function)
        args = [self.visit(arg) for arg in node.args]
        keywords = { key:self.visit(node.keyword_args[key]) for key in node.keyword_args }
        prefix, args = self.parse_args(args)
        if isinstance(function, AstFunction) and len(keywords) == 0 and \
                all([not get_info(arg).has_changed_vars for arg in args]):
            with self.create_scope(function.name):
                for var in get_info(function.body).change_var(function.param_names).mutable_vars:
                    self.protect(var)
                self.define_all(function.parameters, args, vararg=function.vararg)
                result = self.visit(function.body)

            if get_info(result).return_count == 1:
                if isinstance(result, AstReturn):
                    result = result.value
                    result = result if result is not None else AstValue(None)
                    if len(prefix) > 0:
                        result = AstBody(prefix + [result])
                    return result

                elif isinstance(result, AstBody) and result.last_is_return:
                    items = prefix + result.items[:-1]
                    result = result.items[-1].value
                    result = result if result is not None else AstValue(None)
                    return AstBody(items + [result])

        elif isinstance(function, AstDict):
            if len(args) != 1 or len(keywords) != 0:
                raise TypeError("dict access requires exactly one argument ({} given)".format(len(args) + len(keywords)))
            return self.visit(_cl(AstSubscript(function, args[0]), node))

        result = _cl(AstCall(function, args, keywords), node)
        if len(prefix) > 0:
            result = AstBody(prefix + [result])
        return result

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

    def visit_call_range(self, node:AstCall):
        args = [self.visit(arg) for arg in node.args]
        if 1 <= len(args) <= 2 and all([is_integer(arg) for arg in args]):
            if len(args) == 1:
                result = range(args[0].value)
            else:
                result = range(args[0].value, args[1].value)
            return _cl(AstValueVector(list(result)), node)

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
        if isinstance(value, AstFunction) or get_info(value).can_embed:
            self.define(node.name, value, globally=node.global_context)
        else:
            self.protect(node.name)
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
                for n in get_info(node.body).changed_vars:
                    self.protect(n)
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
        cond = node.cond_tuples()
        if len(cond) > 1:
            cond_test = [self.visit(item[0]) for item in cond]
            cond_body = [self.visit(item[1]) for item in cond]
            if _all_equal(cond_body):
                return self.visit(node.if_node)

            if _all_instances(cond_body, AstObserve):
                if _all_equal([x.dist for x in cond_body]):
                    return self.visit(
                        AstObserve(cond_body[0].dist,
                                   AstIf.from_cond_tuples(list(zip(cond_test, [x.value for x in cond_body]))))
                    )

                elif _all_equal([x.value for x in cond_body]):
                    return self.visit(
                        AstObserve(AstIf.from_cond_tuples(list(zip(cond_test, [x.dist for x in cond_body]))),
                                   cond_body[0].value)
                    )

            if _all_instances(cond_body, AstCall) and _all_equal(cond_body, lambda x: x.function_name) and \
                    _all_equal(cond_body, lambda x: x.arg_count) and all([not x.has_keyword_args for x in cond_body]):
                args = [[item.args[i] for item in cond_body] for i in range(cond_body[0].arg_count)]
                new_args = []
                for arg in args:
                    if _all_equal(arg):
                        new_args.append(arg[0])
                    else:
                        new_args.append(AstIf.from_cond_tuples(list(zip(cond_test, arg))))
                return self.visit(AstCall(cond_body[0].function, new_args))

            if _all_instances(cond_body, AstDef) and _all_equal(cond_body, lambda x: x.name):
                values = [item.value for item in cond_body]
                return self.visit(AstDef(cond_body[0].name, AstIf.from_cond_tuples(list(zip(cond_test, values)))))

            if (all([x.is_equality_const_test if isinstance(x, AstCompare) else False for x in cond_test]) or \
                    (all([x.is_equality_const_test if isinstance(x, AstCompare) else False for x in cond_test[:-1]]) and
                     is_boolean_true(cond_test[-1]))) and all([get_info(x).can_embed for x in cond_body]):
                test_vars = []
                test_values = []
                for item in cond_test:
                    if isinstance(item, AstValue):
                        break
                    elif isinstance(item.left, AstValue) and is_symbol(item.right):
                        test_values.append(item.left)
                        test_vars.append(item.right.name)
                    elif is_symbol(item.left) and isinstance(item.right, AstValue):
                        test_values.append(item.right)
                        test_vars.append(item.left.name)
                    else:
                        break
                if len(test_vars) == len(test_values) == len(cond_test) and len(set(test_vars)) == 1:
                    d = AstDict({ a.value:b for a, b in zip(test_values, cond_body) })
                    return self.visit(AstSubscript(d, AstSymbol(test_vars[0])))

                elif len(test_vars) == len(test_values) == len(cond_test)-1 and len(set(test_vars)) == 1 and \
                        is_boolean_true(cond_test[-1]):
                    d = AstDict({ a.value:b for a, b in zip(test_values, cond_body[:-1]) })
                    return self.visit(AstSubscript(d, AstSymbol(test_vars[0]), default=cond_body[-1]))

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
        if len(node.targets) == 1:
            source = self.visit(node.source)
            if node.target == '_':
                return self.visit(_cl(AstBody(node.sources + [node.body]), node))

            elif isinstance(source, AstBody) and len(node.source) > 1:
                result = _cl(AstLet(node.targets, source.items[-1], node.body), node)
                result = _cl(AstBody(source.items[:-1] + [result]), node.source)
                return self.visit(result)

            elif get_info(source).can_embed:
                if node.is_single_var:
                    with self.create_scope():
                        self.define(node.target, self.visit(node.source))
                        body = self.visit(node.body)
                        return _cl(body, node)

                if is_vector(source) and len(source) == len(node.target):
                    with self.create_scope():
                        for t, v in zip(node.target, source):
                            self.define(t, v)
                        body = self.visit(node.body)
                        return _cl(body, node)

            if isinstance(node.body, AstBody):
                items = [(get_info(item).free_vars, item) for item in node.body.items]
                if len(items) == 0:
                    return source

                elif len(items) == 1:
                    return self.visit(_cl(AstLet(node.targets, node.sources, items[0][1]), node))

                elif node.is_single_var:
                    name = node.target
                    start = 0
                    while start < len(items) and name not in items[start][0]:
                        start += 1
                    stop = len(items)
                    while stop > 0 and name not in items[stop-1][0]:
                        stop -= 1

                    if start >= stop:
                        return self.visit(_cl(AstBody(node.sources + node.body.items), node))

                    elif start > 0 or stop < len(items):
                        prefix = [item[1] for item in items[:start]]
                        suffix = [item[1] for item in items[stop:]]
                        new_body = [item[1] for item in items[start:stop]]
                        if len(new_body) == 1:
                            new_body = new_body[0]
                        else:
                            new_body = AstBody(new_body)
                        result = AstBody(prefix + [_cl(AstLet(node.targets, node.sources, new_body), node)] + suffix)
                        return self.visit(result)

            with self.create_scope():
                self.protect(node.target)
                result = self.visit(node.body)

            if node.is_single_var:
                count = count_variable_usage(node.target, result)
                if count == 0:
                    result = AstBody(node.sources + [result])
                    return self.visit(_cl(result, node))

                elif count == 1:
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
            if node.target == '_':
                result = makeVector([node.expr for _ in source])
            else:
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
        default = self.visit(node.default)
        if is_integer(index):
            if isinstance(base, AstValueVector):
                if 0 <= index.value < len(base) or default is None:
                    return _cl(AstValue(base.items[index.value]), node)
                else:
                    return _cl(default, node)
            elif isinstance(base, AstVector):
                if 0 <= index.value < len(base) or default is None:
                    return _cl(base.items[index.value], node)
                else:
                    return _cl(default, node)

        if isinstance(base, AstDict) and isinstance(index, AstValue):
            return base.items.get(index.value, default)

        return _cl(AstSubscript(base, index, default), node)

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

    def visit_value(self, node:AstValue):
        return node

    def visit_value_vector(self, node:AstValueVector):
        return node

    def visit_vector(self, node:AstVector):
        items = [item.visit(self) for item in node.items]
        return makeVector(items)

    def visit_while(self, node:AstWhile):
        test = self.visit(node.test)
        with self.create_scope():
            for n in get_info(node.body).changed_vars:
                self.protect(n)
            body = self.visit(node.body)

        if is_boolean(test):
            if not test.value:
                return AstBody([])

            if len(set.intersection(get_info(node.test).free_vars, get_info(node.body).changed_vars)) > 0:
                result = []
                while is_boolean_true(self.visit(node.test)) and len(result) < MAX_WHILE_ITERATIONS:
                    result.append(self.visit(node.body))
                if len(result) < MAX_WHILE_ITERATIONS:
                    return AstBody(result)

        if test is node.test and body is node.body:
            return node
        else:
            return _cl(AstWhile(test, body), node)


def optimize(ast):
    if type(ast) is list:
        ast = AstBody(ast)

    opt = Optimizer()
    for name in get_info(ast).mutable_vars:
        opt.protect(name)
    result = opt.visit(ast)

    if isinstance(result, AstBody):
        result = result.items

    # remove definitions that are no longer used
    if type(result) in (list, tuple):
        free_vars = [InfoAnnotator().visit(node).free_vars for node in result]
        i = 0
        while i < len(result):
            if isinstance(result[i], AstDef):
                name = result[i].name
                if all([name not in fv for fv in free_vars]):
                    del result[i]
                    continue
            i += 1

    if type(result) in (list, tuple) and len(result) == 1:
        return result[0]
    elif type(result) in (list, tuple):
        return AstBody(result)
    else:
        return result
