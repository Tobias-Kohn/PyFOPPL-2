#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 02. Mar 2018, Tobias Kohn
#
from typing import Optional
from .ppl_ast import *


class NodeInfo(object):

    def __init__(self, *, base=None,
                 changed_vars:Optional[set]=None,
                 free_vars:Optional[set]=None,
                 has_observe:bool=False,
                 has_return:bool=False,
                 has_sample:bool=False,
                 has_side_effects:bool=False,
                 is_expr:bool=False,
                 return_count:int=0):

        if changed_vars is None:
            changed_vars = set()
        if free_vars is None:
            free_vars = set()

        if base is None:
            bases = []
        elif isinstance(base, NodeInfo):
            bases = [base]
        elif type(base) in (list, set, tuple) and all([item is None or isinstance(item, NodeInfo) for item in base]):
            bases = [item for item in base if item is not None]
        else:
            raise TypeError("NodeInfo(): wrong type of 'base': '{}'".format(type(base)))

        self.changed_vars = changed_vars            # type:set
        self.free_vars = free_vars                  # type:set
        self.has_observe = has_observe              # type:bool
        self.has_return = has_return                # type:bool
        self.has_sample = has_sample                # type:bool
        self.has_side_effects = has_side_effects    # type:bool
        self.is_expr = is_expr                      # type:bool
        self.return_count = return_count            # type:int
        for item in bases:
            self.changed_vars = set.union(self.changed_vars, item.changed_vars)
            self.free_vars = set.union(self.free_vars, item.free_vars)
            self.has_observe = self.has_observe or item.has_observe
            self.has_return = self.has_return or item.has_return
            self.has_sample = self.has_sample or item.has_sample
            self.has_side_effects = self.has_side_effects or item.has_side_effects
            self.is_expr = self.is_expr and item.is_expr
            self.return_count += item.return_count

        self.has_changed_vars = len(self.changed_vars) > 0
        self.can_embed = self.is_expr and not (self.has_observe or self.has_return or self.has_sample or
                                               self.has_side_effects or self.has_changed_vars)

        assert type(self.changed_vars) is set and all([type(item) is str for item in self.changed_vars])
        assert type(self.free_vars) is set and all([type(item) is str for item in self.free_vars])
        assert type(self.has_observe) is bool
        assert type(self.has_return) is bool
        assert type(self.has_sample) is bool
        assert type(self.has_side_effects) is bool
        assert type(self.is_expr) is bool
        assert type(self.return_count) is int


    def clone(self, **kwargs):
        result = NodeInfo(base=self)
        for key in kwargs:
            setattr(result, key, kwargs[key])
        return result


    def bind_var(self, name):
        if type(name) is str:
            return self.clone(changed_vars=set.difference(self.free_vars, { name }),
                              free_vars=set.difference(self.free_vars, { name }))

        elif type(name) in (list, set, tuple) and all([type(item) is str for item in name]):
            return self.clone(changed_vars=set.difference(self.free_vars, set(name)),
                              free_vars=set.difference(self.free_vars, set(name)))

        elif name is not None:
            raise TypeError("NodeInfo(): cannot bind '{}'".format(name))

        else:
            return self


    def change_var(self, name):
        if type(name) is str:
            return NodeInfo(base=self, changed_vars={ name })

        elif type(name) in (list, set, tuple) and all([type(item) is str for item in name]):
            return NodeInfo(base=self, changed_vars=set(name))

        elif name is not None:
            raise TypeError("NodeInfo(): cannot add var-name '{}'".format(name))


    def union(self, *other):
        other = [item for item in other if item is not None]
        if len(other) == 0:
            return self
        elif all([isinstance(item, NodeInfo) for item in other]):
            return NodeInfo(base=[self] + other)
        else:
            raise TypeError("NodeInfo(): cannot build union with '{}'"
                            .format([item for item in other if not isinstance(item, NodeInfo)]))


class InfoAnnotator(Visitor):

    __expr_functions__ = {
        'abs',
        'max',
        'min',
        'clojure.core.concat',
        'clojure.core.conj',
        'clojure.core.cons',
        'math.cos',
        'math.sin',
        'math.sqrt',
    }

    def visit_node(self, node:AstNode):
        return NodeInfo()

    def visit_attribute(self, node: AstAttribute):
        return NodeInfo(base=self.visit(node.base), free_vars={node.attr}, is_expr=True)

    def visit_binary(self, node: AstBinary):
        return NodeInfo(base=(self.visit(node.left), self.visit(node.right)), is_expr=True)

    def visit_body(self, node: AstBody):
        return NodeInfo(base=[self.visit(item) for item in node.items])

    def visit_call(self, node: AstCall):
        is_expr = node.function_name in self.__expr_functions__
        base = [self.visit(node.function)]
        args = [self.visit(arg) for arg in node.args]
        kw_args = [self.visit(node.keyword_args[key]) for key in node.keyword_args]
        return NodeInfo(base=base + args + kw_args, is_expr=is_expr)

    def visit_compare(self, node: AstCompare):
        return NodeInfo(base=[self.visit(node.left), self.visit(node.right), self.visit(node.second_right)], is_expr=True)

    def visit_def(self, node: AstDef):
        result = self.visit(node.value)
        return result.change_var(node.name)

    def visit_dict(self, node: AstDict):
        return NodeInfo(base=[self.visit(node.items[key]) for key in node.items], is_expr=True)

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        body = self.visit(node.body).bind_var(node.target)
        return NodeInfo(base=[body, source])

    def visit_function(self, node: AstFunction):
        body = self.visit(node.body)
        return body.bind_var(node.parameters).bind_var(node.vararg)

    def visit_if(self, node: AstIf):
        if node.has_else:
            base = [self.visit(node.if_node), self.visit(node.else_node)]
        else:
            base = [self.visit(node.if_node)]
        return NodeInfo(base=base + [self.visit(node.test)], is_expr=True)

    def visit_import(self, node: AstImport):
        return NodeInfo()

    def visit_let(self, node: AstLet):
        result = self.visit(node.body)
        for t, s in zip(reversed(node.targets), reversed(node.sources)):
            result = result.bind_var(t)
            result = result.union(self.visit(s))
        return result

    def visit_list_for(self, node: AstListFor):
        source = self.visit(node.source)
        expr = self.visit(node.expr).bind_var(node.target)
        return NodeInfo(base=[expr, source], is_expr=True)

    def visit_observe(self, node: AstObserve):
        return NodeInfo(base=[self.visit(node.dist), self.visit(node.value)], has_observe=True)

    def visit_return(self, node: AstReturn):
        return NodeInfo(base=self.visit(node.value), has_return=True, return_count=1)

    def visit_sample(self, node: AstSample):
        return NodeInfo(base=self.visit(node.dist), has_sample=True)

    def visit_slice(self, node: AstSlice):
        base = [self.visit(node.base),
                self.visit(node.start),
                self.visit(node.stop)]
        return NodeInfo(base=base, is_expr=True)

    def visit_subscript(self, node: AstSubscript):
        base = [self.visit(node.base), self.visit(node.index)]
        return NodeInfo(base=base, is_expr=True)

    def visit_symbol(self, node: AstSymbol):
        return NodeInfo(free_vars={node.name}, is_expr=True)

    def visit_unary(self, node: AstUnary):
        return self.visit(node.item)

    def visit_value(self, _):
        return NodeInfo(is_expr=True)

    def visit_value_vector(self, _):
        return NodeInfo(is_expr=True)

    def visit_vector(self, node: AstVector):
        return NodeInfo(base=[self.visit(item) for item in node.items], is_expr=True)

    def visit_while(self, node: AstWhile):
        base = [self.visit(node.test), self.visit(node.body)]
        return NodeInfo(base=base)


class VarCountVisitor(Visitor):

    __visit_children_first__ = True

    def __init__(self, name:str):
        super().__init__()
        self.count = 0
        self.name = name
        assert type(self.name) is str and self.name != ''

    def visit_node(self, node:AstNode):
        return node

    def visit_symbol(self, node:AstSymbol):
        if node.name == self.name:
            self.count += 1
        return node



def get_info(ast:AstNode):
    return InfoAnnotator().visit(ast)

def count_variable_usage(name:str, ast:AstNode):
    vcv = VarCountVisitor(name)
    vcv.visit(ast)
    return vcv.count