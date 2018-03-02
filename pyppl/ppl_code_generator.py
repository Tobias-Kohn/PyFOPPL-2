#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 02. Mar 2018, Tobias Kohn
# 02. Mar 2018, Tobias Kohn
#
from .ppl_ast import *
from .ppl_ast_annotators import get_info


# TODO: This is work in progress!
# TODO: - import
# TODO: - return/assign/def of 'bodies' (if, while, for, let, ...)

class CodeGenerator(Visitor):

    def __init__(self):
        self.functions = []

    def add_function(self, params:list, body:str):
        name = "__LAMBDA_FUNCTION__{}__".format(len(self.functions) + 1)
        self.functions.append("def {}({}):\n\t{}".format(name, ', '.join(params), body.replace('\n', '\n\t')))
        return name

    def visit_attribute(self, node:AstAttribute):
        result = self.visit(node.base)
        return "{}.{}".format(result, node.attr)

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return "({} {} {})".format(left, node.op, right)

    def visit_body(self, node:AstBody):
        items = [self.visit(item) for item in node.items]
        items = [item for item in items if item != '']
        return '\n'.join(items)

    def visit_break(self, _):
        return "break"

    def visit_call(self, node: AstCall):
        function = self.visit(node.function)
        args = [self.visit(arg) for arg in node.args]
        keyword_args = ["{}={}".format(key, node.keyword_args[key]) for key in node.keyword_args]
        args += keyword_args
        return "{}({})".format(function, ', '.join(args))

    def visit_compare(self, node: AstCompare):
        if node.second_right is None:
            left = self.visit(node.left)
            right = self.visit(node.right)
            return "({} {} {})".format(left, node.op, right)
        else:
            left = self.visit(node.left)
            right = self.visit(node.right)
            second_right = self.visit(node.second_right)
            return "({} {} {} {} {})".format(left, node.op, right, node.second_op, second_right)

    def visit_def(self, node: AstDef):
        if isinstance(node.value, AstFunction):
            function = node.value
            params = function.parameters
            if function.vararg is not None:
                params.append("*" + function.vararg)
            body = self.visit(function.body).replace('\n', '\n\t')
            return "def {}({}):\n\t{}".format(node.name, ', '.join(params), body)

        return "{} = {}".format(node.name, self.visit(node.value))

    def visit_dict(self, node: AstDict):
        result = { key: self.visit(node.items[key]) for key in node.items }
        return repr(result)

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        body = self.visit(node.body).replace('\n', '\n\t')
        return "for {} in {}:\n\t{}".format(str(node.target), source, body)

    def visit_function(self, node: AstFunction):
        params = node.parameters
        if node.vararg is not None:
            params.append("*" + node.vararg)
        body = self.visit(node.body)
        if '\n' in body or get_info(node.body).has_return:
            return self.add_function(params, body)
        else:
            return "(lambda {}: {})".format(', '.join(params), body)

    def visit_if(self, node: AstIf):
        test = self.visit(node.test)
        if_expr = self.visit(node.if_node)
        if node.has_else:
            else_expr = self.visit(node.else_node)
            if node.has_elif:
                return "if {}:\n\t{}\nel{}".format(test, if_expr.replace('\n', '\n\t'), else_expr.replace('\n', '\n\t'))
            elif '\n' in if_expr or '\n' in else_expr:
                return "if {}:\n\t{}\nelse:\n\t{}".format(test, if_expr.replace('\n', '\n\t'),
                                                          else_expr.replace('\n', '\n\t'))
            else:
                return "{} if {} else {}".format(if_expr, test, else_expr)
        else:
            if '\n' in if_expr:
                return "if {}:\n\t{}".format(test, if_expr.replace('\n', '\n\t'))
            else:
                return "{} if {} else None".format(if_expr, test)

    def visit_import(self, node: AstImport):
        return "import {}".format(node.module_name)

    def visit_let(self, node: AstLet):
        result = []
        for t, s in zip(node.targets, node.sources):
            result.append("{} = {}".format(str(t), self.visit(s)))
        result.append(self.visit(node.body))
        return '\n'.join(result)

    def visit_list_for(self, node: AstListFor):
        expr = self.visit(node.expr)
        source = self.visit(node.source)
        test = (' if ' + self.visit(node.test)) if node.test is not None else ''
        return "[{} for {} in {}{}]".format(expr, str(node.target), source, test)

    def visit_observe(self, node: AstObserve):
        dist = self.visit(node.dist)
        return "observe({}, {})".format(dist, self.visit(node.value))

    def visit_return(self, node: AstReturn):
        if node.value is None:
            return "return None"
        elif isinstance(node.value, AstBody):
            items = node.value.items
            return self.visit(AstBody(items[:-1] + [AstReturn(items[-1])]))
        elif isinstance(node.value, AstLet):
            item = node.value
            return self.visit(AstLet(item.targets, item.sources, AstReturn(item.body)))
        else:
            return "return {}".format(self.visit(node.value))

    def visit_sample(self, node: AstSample):
        dist = self.visit(node.dist)
        return "sample({})".format(dist)

    def visit_slice(self, node: AstSlice):
        base = self.visit(node.base)
        start = self.visit(node.start) if node.start is not None else ''
        stop = self.visit(node.stop) if node.stop is not None else ''
        return "{}[{}:{}]".format(base, start, stop)

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        return "{}[{}]".format(base, index)

    def visit_symbol(self, node: AstSymbol):
        return node.name

    def visit_unary(self, node: AstUnary):
        return "{}{}".format(node.op, self.visit(node.item))

    def visit_value(self, node: AstValue):
        return repr(node.value)

    def visit_value_vector(self, node: AstValueVector):
        return repr(node.items)

    def visit_vector(self, node: AstVector):
        return "[{}]".format(', '.join([self.visit(item) for item in node.items]))

    def visit_while(self, node: AstWhile):
        test = self.visit(node.test)
        body = self.visit(node.body).replace('\n', '\n\t')
        return "while {}:\n\t{}".format(test, body)


def generate_code(ast):
    cg = CodeGenerator()
    result = cg.visit(ast)
    if type(result) is list:
        result = cg.functions + result
        result = '\n\n'.join(result)
    elif len(cg.functions) > 0:
        result = cg.functions + [result]
        result = '\n\n'.join(result)
    return result
