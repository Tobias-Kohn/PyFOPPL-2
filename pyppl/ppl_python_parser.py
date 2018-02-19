#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 19. Feb 2018, Tobias Kohn
#
from .ppl_ast import *
import ast


_cl = ast.copy_location

class PythonParser(ast.NodeVisitor):

    __ast_ops__ = {
        ast.Add:    '+',
        ast.Sub:    '-',
        ast.Mult:   '*',
        ast.Div:    '/',
        ast.FloorDiv: '//',
        ast.Mod:    '%',
        ast.Pow:    '**',
        ast.LShift: '<<',
        ast.RShift: '>>',
        ast.UAdd:   '+',
        ast.USub:   '-',
        ast.Eq:     '==',
        ast.NotEq:  '!=',
        ast.Lt:     '<',
        ast.Gt:     '>',
        ast.LtE:    '<=',
        ast.GtE:    '>=',
        ast.And:    'and',
        ast.Or:     'or',
        ast.Not:    'not',
        ast.BitAnd: '&',
        ast.BitOr:  '|',
    }

    def visit_Assign(self, node:ast.Assign):
        source = self.visit(node.value)
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                return _cl(AstDef(target.id, source), node)

            elif isinstance(target, ast.Tuple) and all([isinstance(t, ast.Name) for t in target.elts]):
                return _cl(AstDef(tuple(t.id for t in target.elts), source), node)

        elif len(node.targets) > 1 and all(isinstance(target, ast.Name) for target in node.targets):
            result = []
            base = node.targets[-1].id
            result.append(_cl(AstDef(base, source), node))
            base_name = AstSymbol(base)
            for target in node.targets[:-1]:
                result.append(AstDef(target.id, base_name))
            return AstBody(result)

        raise NotImplementedError("cannot compile assignment '{}'".format(ast.dump(node)))

    def visit_BinOp(self, node:ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.__ast_ops__[node.op.__class__]
        return _cl(AstBinary(left, op, right), node)

    def visit_Call(self, node:ast.Call):
        # TODO: Keywords!
        if not isinstance(node.func, ast.Name):
            raise NotImplementedError("a function call needs a function name, not '{}'".format(ast.dump(node.func)))
        name = node.func.id
        args = [self.visit(arg) for arg in node.args]
        return _cl(AstCall(name, args), node)

    def visit_Compare(self, node:ast.Compare):
        if len(node.ops) == 1:
            op = self.__ast_ops__[node.ops[0].__class__]
            left = self.visit(node.left)
            right = self.visit(node.comparators[0])
            return _cl(AstCompare(left, op, right), node)

        elif len(node.ops) == 2:
            op1 = self.__ast_ops__[node.ops[0].__class__]
            op2 = self.__ast_ops__[node.ops[1].__class__]
            if (op1 in ['<', '<='] and op2 in ['<', '<=']) or \
               (op1 in ['>', '>='] and op2 in ['>', '>=']):
                pass

        raise NotImplementedError("cannot compile compare '{}'".format(ast.dump(node)))

    def visit_Expr(self, node:ast.Expr):
        return self.visit(node.value)

    def visit_FunctionDef(self, node:ast.FunctionDef):
        # node.name: str
        # node.args: arguments(arg, varargs, kwonlyargs, kw_defaults, kwarg, defaults
        # node.body
        # node.decorator_list
        pass

    def visit_If(self, node:ast.If):
        test = self.visit(node.test)
        body = AstBody([self.visit(item) for item in node.body])
        else_body = AstBody([self.visit(item) for item in node.orelse]) if len(node.orelse) > 0 else None
        return _cl(AstIf(test, body, else_body), node)

    def visit_Lambda(self, node: ast.Lambda):
        # node.args
        # node.body
        pass

    def visit_List(self, node:ast.List):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_Module(self, node:ast.Module):
        body = [self.visit(item) for item in node.body]
        return _cl(AstBody(body), node)

    def visit_Name(self, node:ast.Name):
        return _cl(AstSymbol(node.id), node)

    def visit_NameConstant(self, node: ast.NameConstant):
        return _cl(AstValue(node.value), node)

    def visit_Num(self, node:ast.Num):
        return _cl(AstValue(node.n), node)

    def visit_Return(self, node:ast.Return):
        return _cl(AstReturn(self.visit(node.value)), node)

    def visit_Str(self, node:ast.Str):
        return _cl(AstValue(node.s), node)

    def visit_Tuple(self, node:ast.Tuple):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_UnaryOp(self, node:ast.UnaryOp):
        op = self.__ast_ops__[node.op.__class__]
        if isinstance(node.operand, ast.Num) and op in ['+', '-']:
            n = -ast.Num.n if op == '-' else ast.Num.n
            return _cl(AstValue(n), node)
        else:
            return _cl(AstUnary(op, self.visit(node.operand)), node)


#######################################################################################################################

def parse(source):
    py_ast = ast.parse(source)
    ppl_ast = PythonParser().visit(py_ast)
    return ppl_ast
