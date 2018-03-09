#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 09. Mar 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_types import *

class TypeInferencer(Visitor):

    __visit_children_first__ = True

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def define(self, name:str, value):
        if name is None or name == '_':
            return
        if self.parent is not None and value is not None:
            result = self.parent.resolve(name)
            if hasattr(result, 'set_type'):
                result.set_type(value)

    def resolve(self, name:str):
        if self.parent is not None:
            result = self.parent.resolve(name)
            if isinstance(result, Type):
                return result
            elif hasattr(result, 'get_type'):
                return result.get_type()
        return None

    def get_value_of(self, node: AstNode):
        if isinstance(node, AstValue):
            return node.value
        else:
            return None


    def visit_binary(self, node: AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return node.op_function(left, right)

    def visit_body(self, node:AstBody):
        if node.is_empty:
            return NullType
        else:
            return node.items[-1].get_type()

    def visit_call(self, node: AstCall):
        return AnyType

    def visit_call_range(self, node: AstCall):
        if node.arg_count == 2:
            a = self.get_value_of(node.args[0])
            b = self.get_value_of(node.args[1])
            if a is not None and b is not None:
                return List[Integer][b-a]
        elif node.arg_count == 1:
            a = self.get_value_of(node.args[0])
            if a is not None:
                return List[Integer][a]
        return List[Integer]

    def visit_compare(self, _):
        return Boolean

    def visit_def(self, node: AstDef):
        result = self.visit(node.value)
        self.define(node.name, result)
        return result

    def visit_dict(self, node: AstDict):
        base = union(*[self.visit(item) for item in node.items.values()])
        return Dict[base][len(node.items)]

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        if isinstance(source, SequenceType):
            self.define(node.target, source.item)
            return self.visit(node.body)
        else:
            return AnyType

    def visit_function(self, node: AstFunction):
        return Function

    def visit_if(self, node: AstIf):
        return union(node.if_node.get_type(), node.else_node.get_type())

    def visit_let(self, node: AstLet):
        self.define(node.target, self.visit(node.source))
        return node.body.get_type()

    def visit_list_for(self, node: AstListFor):
        source = self.visit(node.source)
        if isinstance(source, SequenceType):
            self.define(node.target, source.item)
            result = self.visit(node.expr)
            return List[result][source.size]
        else:
            return AnyType

    def visit_sample(self, node: AstSample):
        return Numeric

    def visit_slice(self, node: AstSlice):
        base = self.visit(node.base)
        if isinstance(base, SequenceType):
            return base.slice(node.start_as_int, node.stop_as_int)
        else:
            return AnyType

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        if isinstance(base, SequenceType):
            return base.item_type
        else:
            return AnyType

    def visit_symbol(self, node: AstSymbol):
        result = self.resolve(node.name)
        return result if result is not None else AnyType

    def visit_unary(self, node: AstUnary):
        if node.op == 'not':
            return Boolean
        else:
            return self.visit(node.item)

    def visit_value(self, node: AstValue):
        return from_python(node.value)

    def visit_value_vector(self, node: AstValueVector):
        return from_python(node.items)

    def visit_vector(self, node: AstVector):
        base_type = union(*[self.visit(item) for item in node.items])
        return List[base_type][len(node.items)]
