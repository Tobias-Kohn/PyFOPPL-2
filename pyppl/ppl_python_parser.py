#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 22. Feb 2018, Tobias Kohn
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
        ast.Is:     'is',
        ast.IsNot:  'is not',
        ast.In:     'in',
        ast.NotIn:  'not in',
    }

    def _visit_body(self, body:list, require_return:bool=False):
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            if require_return:
                return _cl(AstReturn(AstValue(None)), body[0])
            else:
                return _cl(AstBody([]), body[0])

        result = []
        for item in body:
            v_item = self.visit(item)
            if isinstance(v_item, AstBody):
                result += v_item.items
            elif v_item is not None:
                result.append(v_item)

        if require_return:
            if len(result) == 0:
                return AstReturn(AstValue(None))
            elif not isinstance(result[-1], AstReturn):
                result.append(AstReturn(AstValue(None)))

        if len(result) == 1:
            return result[0]
        else:
            return AstBody(result)

    def generic_visit(self, node):
        raise NotImplementedError("cannot compile '{}'".format(ast.dump(node)))

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

    def visit_Attribute(self, node:ast.Attribute):
        base = self.visit(node.value)
        return _cl(AstAttribute(base, node.attr), node)

    def visit_BinOp(self, node:ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.__ast_ops__[node.op.__class__]
        return _cl(AstBinary(left, op, right), node)

    def visit_Break(self, node:ast.Break):
        return _cl(AstBreak(), node)

    def visit_Call(self, node:ast.Call):
        def _check_arg_arity(name, args, arg_count):
            if len(args) != arg_count:
                if arg_count == 0:
                    s = "no arguments"
                elif arg_count == 1:
                    s = "one argument"
                elif arg_count == 2:
                    s = "two arguments"
                elif arg_count == 3:
                    s = "three arguments"
                else:
                    s = "{} arguments".format(arg_count)
                raise TypeError("{}() takes exactly {} ({} given)".format(name, s, len(args)))

        if isinstance(node.func, ast.Attribute):
            attr_base = self.visit(node.func.value)
            attr_name = node.func.attr
            args = [self.visit(arg) for arg in node.args]
            keywords = { kw.arg: self.visit(kw.value) for kw in node.keywords }
            if attr_name in ['append']:
                return _cl(AstCall(AstAttribute(AstSymbol('list'), attr_name), [attr_base] + args, keywords), node)
            return _cl(AstCall(AstAttribute(attr_base, attr_name), args, keywords), node)

        elif isinstance(node.func, ast.Name):
            name = node.func.id
            args = [self.visit(arg) for arg in node.args]
            keywords = { kw.arg: self.visit(kw.value) for kw in node.keywords }
            if name == 'sample':
                _check_arg_arity(name, args, 1)
                result = AstSample(args[0])
            elif name == 'observe':
                _check_arg_arity(name, args, 2)
                result = AstObserve(args[0], args[1])
            else:
                result = AstCall(AstSymbol(name), args, keywords)
            return _cl(result, node)

        #elif isinstance(node.func, ast.Lambda):
        #    pass

        else:
            raise NotImplementedError("a function call needs a function name, not '{}'".format(ast.dump(node.func)))

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

    def visit_For(self, node:ast.For):
        if len(node.orelse) > 0:
            raise NotImplementedError("'else' is not supported for for-loops")

        iter_ = self.visit(node.iter)
        body = self._visit_body(node.body)
        if isinstance(node.target, ast.Name):
            return _cl(AstFor(node.target.id, iter_, body), node)

        elif isinstance(node.target, ast.Tuple) and all([isinstance(t, ast.Name) for t in node.target.elts]):
            return _cl(AstFor(tuple(t.id for t in node.target.elts), iter_, body), node)

        raise NotImplementedError("cannot compile for-loop: '{}'".format(ast.dump(node)))

    def visit_FunctionDef(self, node:ast.FunctionDef):
        # TODO: Support default and keyword arguments
        # node.name: str
        # node.args: arguments(arg, varargs, kwonlyargs, kw_defaults, kwarg, defaults
        if len(node.decorator_list) > 0:
            raise NotImplementedError("cannot compile decorators: '{}'".format(ast.dump(node)))
        name = node.name
        arg_names = [arg.arg for arg in node.args.args]
        body = self._visit_body(node.body, require_return=True)
        return _cl(AstFunction(name, arg_names, body), node)

    def visit_If(self, node:ast.If):
        test = self.visit(node.test)
        body = self._visit_body(node.body)
        else_body = self._visit_body(node.orelse) if len(node.orelse) > 0 else None
        return _cl(AstIf(test, body, else_body), node)

    def visit_IfExp(self, node:ast.IfExp):
        test = self.visit(node.test)
        body = self.visit(node.body)
        else_body = self.visit(node.orelse)
        return _cl(AstIf(test, body, else_body), node)

    def visit_Import(self, node:ast.Import):
        result = []
        for alias in node.names:
            result.append( _cl(AstImport(alias.name, None, alias.asname), node) )
        if len(result) == 1:
            return _cl(result[0], node)
        else:
            return _cl(AstBody(result), node)

    def visit_ImportFrom(self, node:ast.ImportFrom):
        if node.level != 0:
            raise NotImplementedError("cannot import with level != 0: '{}'".format(ast.dump(node)))
        module = node.module
        if len(node.names) == 1 and node.names[0].name == '*':
            if module in ['math', 'cmath']:
                names = [n for n in dir(__import__(module)) if not n.startswith('_')]
                return _cl(AstImport(module, names), node)
            else:
                raise NotImplementedError("cannot import '{}'".format(ast.dump(node)))

        elif all([n.asname is None for n in node.names]):
            return _cl(AstImport(module, [n.name for n in node.names]), node)

        else:
            result = []
            for alias in node.names:
                result.append(_cl(AstImport(module, [alias.name], alias.asname), node))
            return _cl(AstBody(result), node)

    def visit_Lambda(self, node: ast.Lambda):
        arg_names = [arg.arg for arg in node.args.args]
        body = AstReturn(self.visit(node.body))
        return _cl(AstFunction(None, arg_names, body), node)

    def visit_List(self, node:ast.List):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_ListComp(self, node:ast.ListComp):
        if len(node.generators) != 1:
            raise NotImplementedError("a list comprehension must have exactly one generator: '{}'".format(ast.dump(node)))
        if len(node.generators[0].ifs) > 1:
            raise NotImplementedError("a list comprehension must have at most one if: '{}'".format(ast.dump(node)))

        generator = node.generators[0]
        expr = self.visit(node.elt)
        test = self.visit(generator.ifs[0]) if len(generator.ifs) > 0 else None
        target = generator.target
        source = self.visit(generator.iter)
        if isinstance(target, ast.Name):
            return _cl(AstListFor(target.id, source, expr, test), node)

        elif isinstance(target, ast.Tuple) and all([isinstance(t, ast.Name) for t in node.target.elts]):
            return _cl(AstListFor(tuple(t.id for t in node.target.elts), source, expr, test), node)

        raise NotImplementedError("cannot compile list comprehension: '{}'".format(ast.dump(node)))

    def visit_Module(self, node:ast.Module):
        body = self._visit_body(node.body)
        return _cl(body, node)

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

    def visit_Subscript(self, node:ast.Subscript):
        base = self.visit(node.value)
        if isinstance(node.slice, ast.Index):
            index = self.visit(node.slice.value)
            return _cl(AstSubscript(base, index), node)
        elif isinstance(node.slice, ast.Slice) and node.slice.step is None:
            start = self.visit(node.slice.lower)
            stop = self.visit(node.slice.upper)
            return _cl(AstSlice(base, start, stop), node)
        raise NotImplementedError("cannot compile subscript '{}'".format(ast.dump(node)))

    def visit_Tuple(self, node:ast.Tuple):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_UnaryOp(self, node:ast.UnaryOp):
        op = self.__ast_ops__[node.op.__class__]
        if isinstance(node.operand, ast.Num) and op in ['+', '-']:
            n = -node.operand.n if op == '-' else node.operand.n
            return _cl(AstValue(n), node)
        else:
            return _cl(AstUnary(op, self.visit(node.operand)), node)

    def visit_While(self, node:ast.While):
        if len(node.orelse) > 0:
            raise NotImplementedError("'else' is not supported for while-loops")

        test = self.visit(node.test)
        body = self._visit_body(node.body)
        return AstWhile(test, body)


#######################################################################################################################

def parse(source):
    py_ast = ast.parse(source)
    ppl_ast = PythonParser().visit(py_ast)
    return ppl_ast
