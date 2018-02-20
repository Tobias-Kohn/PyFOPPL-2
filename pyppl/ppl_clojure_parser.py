#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Feb 2018, Tobias Kohn
#
from ast import copy_location as _cl
from .ppl_ast import *
from . import ppl_clojure_forms as clj

#######################################################################################################################

class ClojureParser(clj.Visitor):

    def visit_form(self, node:clj.Form):
        raise NotImplementedError("forms are not supported, yet")

    def visit_symbol(self, node:clj.Symbol):
        return _cl(AstSymbol(node.name), node)

    def visit_value(self, node:clj.Value):
        return _cl(AstValue(node.value), node)

    def visit_vector(self, node:clj.Vector):
        items = [item.visit(self) for item in node.items]
        return _cl(makeVector(items), node)


#######################################################################################################################
from . import lexer
from .lexer import CatCode, TokenType

def _str_to_ast(text:str):

    def make_form(token_stream):
        result = []
        while token_stream.has_next and token_stream.peek()[1] != TokenType.RIGHT_BRACKET:
            token = token_stream.next()
            tt = token[1]
            if tt == TokenType.LEFT_BRACKET:
                lineno = source.get_line_from_pos(token[0])
                left = token[2]
                form = make_form(token_stream)
                right = token_stream.next()
                right = right[2] if right is not None else '<EOF>'
                if left == '(' and right == ')':
                    result.append(clj.Form(form, lineno=lineno))
                elif left == '[' and right == ']':
                    result.append(clj.Vector(form, lineno=lineno))
                else:
                    raise SyntaxError("mismatched parentheses: '{}' and '{}' (line {})".format(left, right, lineno))

            elif tt in [TokenType.NUMBER, TokenType.STRING]:
                result.append(clj.Value(token[2], lineno=source.get_line_from_pos(token[0])))

            elif tt == TokenType.SYMBOL:
                result.append(clj.Symbol(token[2], lineno=source.get_line_from_pos(token[0])))

            else:
                raise SyntaxError("invalid token: '{}' (line {})".format(token[1], source.get_line_from_pos(token[0])))

        return result

    source = lexer.CharacterStream(text)
    clj_lexer = lexer.Lexer(source)
    clj_lexer.catcodes['\n'] = CatCode.WHITESPACE
    clj_lexer.catcodes['!':'@'] = CatCode.ALPHA
    result = make_form(lexer.BufferedIterator(clj_lexer))
    if len(result) == 1:
        return result[0]
    else:
        return clj.Form(result, lineno=0)


#######################################################################################################################

def parse(source):
    clj_ast = _str_to_ast(source)
    ppl_ast = ClojureParser().visit(clj_ast)
    return ppl_ast
