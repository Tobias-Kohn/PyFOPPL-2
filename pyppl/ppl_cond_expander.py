#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Mar 2018, Tobias Kohn
# 07. Mar 2018, Tobias Kohn
#
from ast import copy_location as _cl
from .ppl_ast import *


class ConditionExpander(Visitor):

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(left, AstIf):
            else_node = AstBinary(left.else_node, node.op, right) if left.has_else else None
            return AstIf(left.test, _cl(AstBinary(left.if_node, node.op, right), node), else_node)

        elif isinstance(left, AstIf):
            else_node = AstBinary(left.else_node, node.op, right) if left.has_else else None
            return AstIf(left.test, _cl(AstBinary(left.if_node, node.op, right), node), else_node)

        else:
            return node

    def visit_body(self, node:AstBody):
        return self.visit_node(node)

    def visit_call(self, node: AstCall):
        args = [self.visit(arg) for arg in node.args]
        for i in range(len(args)):
            arg = args[i]
            if isinstance(arg, AstIf):
                if arg.has_else:
                    args[i] = arg.else_node
                    else_node = AstCall(node.function, args[:], keyword_args=node.keyword_args)
                else:
                    else_node = None
                args[i] = arg.if_node
                return AstIf(arg.test,
                             self.visit(_cl(AstCall(node.function, args[:], keyword_args=node.keyword_args), node)),
                             else_node)

        return node

    def visit_def(self, node: AstDef):
        value = self.visit(node.value)
        if isinstance(value, AstIf):
            else_node = AstDef(node.name, value.else_node) if value.has_else else None
            return AstIf(value.test, _cl(AstDef(node.name, value.if_node), node), else_node)

        return node

    def visit_let(self, node: AstLet):
        body = self.visit(node.body)
        return self.visit_node(node)

    def visit_unary(self, node: AstUnary):
        item = self.visit(node.item)
        if isinstance(item, AstIf):
            else_node = AstUnary(node.op, item.else_node) if item.has_else else None
            return AstIf(item.test, _cl(AstUnary(node.op, item.if_node), node), else_node)
        return self.visit_node(node)
