#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 05. Mar 2018, Tobias Kohn
# 05. Mar 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_ast_annotators import *
from ast import copy_location as _cl

# When unrolling a while-loop, we have a maximum number of iterations:
MAX_WHILE_ITERATIONS = 100


class PartialEvaluator(ScopedVisitor):

    def visit_attribute(self, node:AstAttribute):
        return node

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(left, AstValue) and isinstance(right, AstValue):
            value = node.op_function(left.value, right.value)
            return _cl(AstValue(value), node)

        return _cl(AstBinary(left, node.op, right), node)

    def visit_body(self, node:AstBody):
        items = [self.visit(item) for item in node.items]
        return _cl(AstBody(items), node)

    def visit_break(self, node: AstBreak):
        return node

    def visit_call(self, node: AstCall):
        function = node.function
        args = [self.visit(arg) for arg in node.args]
        if not node.has_keyword_args and isinstance(function, AstFunction):
            with self.create_scope():
                self.define_all(function.parameters, args, vararg=function.vararg)
                result = self.visit(function.body)

            if get_info(result).return_count == 1:
                if isinstance(result, AstReturn):
                    result = result.value
                    result = result if result is not None else AstValue(None)
                    return result

        return _cl(AstCall(function, args), node)

        # return node

    def visit_compare(self, node: AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        second_right = self.visit(node.second_right)

        if second_right is None and isinstance(left, AstValue) and isinstance(right, AstValue):
            return AstValue(node.op_function(left.value, right.value))

        return AstCompare(left, node.op, right, node.second_op, second_right)

    def visit_def(self, node: AstDef):
        value = self.visit(node.value)
        self.define(node.name, value)
        return _cl(AstDef(node.name, value), node)

    def visit_dict(self, node: AstDict):
        return node

    def visit_for(self, node: AstFor):
        return node

    def visit_function(self, node: AstFunction):
        return node

    def visit_if(self, node: AstIf):
        test = self.visit(node.test)
        if is_boolean(test):
            if test.value is True:
                return self.visit(node.if_node)
            elif test.value is False:
                return self.visit(node.else_node) if node.has_else else AstValue(None)
        return _cl(AstIf(test, node.if_node, node.else_node), node)

    def visit_import(self, node: AstImport):
        return node

    def visit_let(self, node: AstLet):
        return node

    def visit_list_for(self, node: AstListFor):
        return node

    def visit_observe(self, node: AstObserve):
        return _cl(AstObserve(self.visit(node.dist), self.visit(node.value)), node)

    def visit_return(self, node: AstReturn):
        return node

    def visit_sample(self, node: AstSample):
        return node

    def visit_slice(self, node: AstSlice):
        return node

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        default = self.visit(node.default)
        if isinstance(base, AstDict) and isinstance(index, AstValue):
            return base.items.get(index.value, default)

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

        return _cl(AstSubscript(base, index, default), node)

    def visit_symbol(self, node: AstSymbol):
        result = self.resolve(node.name)
        if result is not None:
            return result
        else:
            return node

    def visit_unary(self, node: AstUnary):
        return node

    def visit_value(self, node: AstValue):
        return node

    def visit_value_vector(self, node: AstValueVector):
        return node

    def visit_vector(self, node: AstVector):
        return node

    def visit_while(self, node: AstWhile):
        if len(set.intersection(get_info(node.test).free_vars, get_info(node.body).changed_vars)) > 0:
            result = []
            while True:
                test = self.visit(node.test)
                if not is_boolean(test) or len(result) > MAX_WHILE_ITERATIONS:
                    raise RuntimeError("could not unroll 'while'-loop")
                if test.value is False:
                    break
                result.append(self.visit(node.body))
            return AstBody(result)

        raise RuntimeError("could not unroll 'while'-loop")
