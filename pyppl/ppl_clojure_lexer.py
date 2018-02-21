#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 21. Feb 2018, Tobias Kohn
#
from . import ppl_clojure_forms as clj
from . import lexer
from .lexer import CatCode, TokenType


class ClojureLexer(object):
    def __init__(self, text: str):
        self.text = text
        self.lexer = lexer.Lexer(text)
        self.source = lexer.BufferedIterator(self.lexer)
        self.lexer.catcodes['\n', ','] = CatCode.WHITESPACE
        self.lexer.catcodes['!', '$', '%', '&', '*', '+', '-', '.', '/', ':', '<', '>', '=', '?'] = CatCode.ALPHA
        self.lexer.catcodes[';'] = CatCode.LINE_COMMENT
        self.lexer.catcodes['#', '\'', '`', '~', '^', '@'] = CatCode.SYMBOL
        self.lexer.add_symbols('~@', '#\'')
        self.lexer.add_string_prefix('#')

    def __iter__(self):
        return self

    def __next__(self):
        source = self.source
        if source.has_next:
            token = source.next()
            pos, token_type, value = token
            lineno = self.lexer.get_line_from_pos(pos)

            if token_type == TokenType.LEFT_BRACKET:
                left = value
                result = []
                while source.has_next and source.peek()[1] != TokenType.RIGHT_BRACKET:
                    result.append(self.__next__())

                if source.has_next:
                    token = source.next()
                    right = token[2] if token is not None else '<EOF>'
                    if not token[1] == TokenType.RIGHT_BRACKET:
                        raise SyntaxError("expected right parentheses or bracket instead of '{}' (line {})".format(
                            right, self.lexer.get_line_from_pos(token[0])
                        ))
                    if left == '(' and right == ')':
                        return clj.Form(result, lineno=lineno)

                    elif left == '[' and right == ']':
                        return clj.Vector(result, lineno=lineno)

                    elif left == '{' and right == '}':
                        raise NotImplementedError("{} not implemented")

                    else:
                        raise SyntaxError("mismatched parentheses: '{}' amd '{}' (line {})".format(
                            left, right, lineno
                        ))

            elif token_type == TokenType.NUMBER:
                return clj.Value(value, lineno=lineno)

            elif token_type == TokenType.STRING:
                return clj.Value(eval(value), lineno=lineno)

            elif token_type == TokenType.SYMBOL:

                if value == '#':
                    form = self.__next__()
                    if not isinstance(form, clj.Form):
                        raise SyntaxError("'#' requires a form to build a function (line {})".format(lineno))
                    raise NotImplementedError("lambda function are not yet implemented")

                elif value == '@':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('deref', lineno=lineno), form], lineno=lineno)

                elif value == '\'':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('quote', lineno=lineno), form], lineno=lineno)

                elif value == '#\'':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('var', lineno=lineno), form], lineno=lineno)

                return clj.Symbol(value, lineno=lineno)

            else:
                raise SyntaxError("invalid token: '{}' (line {})".format(token_type, lineno))

        raise StopIteration
