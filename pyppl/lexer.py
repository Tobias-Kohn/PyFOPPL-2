#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Feb 2018, Tobias Kohn
#
import enum

#######################################################################################################################

class TokenType(enum.Enum):
    SYMBOL = 1
    NUMBER = 2
    STRING = 3
    KEYWORD = 4
    INDENT = 5
    DEDENT = 6
    LEFT_BRACKET = 7
    RIGHT_BRACKET = 8
    NEWLINE = 9


#######################################################################################################################

class CatCode(enum.Enum):
    INVALID = 0
    IGNORE = 1
    WHITESPACE = 2
    ALPHA = 3
    NUMERIC = 4
    SYMBOL = 5
    DELIMITER = 6
    LEFT_BRACKET = 7
    RIGHT_BRACKET = 8
    NEWLINE = 9
    STRING_DELIMITER = 10
    ESCAPE = 11
    LINE_COMMENT = 12


class CategoryCodes(object):

    def __init__(self, char_range:int=128):
        self.catcodes = [CatCode.INVALID for _ in range(char_range)]
        self.catcodes[ord('\t')] = CatCode.WHITESPACE
        self.catcodes[ord('\n')] = CatCode.NEWLINE
        self.catcodes[ord('\r')] = CatCode.WHITESPACE
        self.catcodes[ord(' ')] = CatCode.WHITESPACE
        self.catcodes[ord('_')] = CatCode.ALPHA
        for i in range(ord('!'), ord('A')):
            self.catcodes[i] = CatCode.SYMBOL
        for i in range(ord('0'), ord('9')+1):
            self.catcodes[i] = CatCode.NUMERIC
        for i in range(ord('A'), ord('Z')+1):
            self.catcodes[i] = CatCode.ALPHA
        for i in range(ord('a'), ord('z')+1):
            self.catcodes[i] = CatCode.ALPHA
        for i in ['(', '[', '{']:
            self.catcodes[ord(i)] = CatCode.LEFT_BRACKET
        for i in [')', ']', '}']:
            self.catcodes[ord(i)] = CatCode.RIGHT_BRACKET
        for i in ['\'', '\"']:
            self.catcodes[ord(i)] = CatCode.STRING_DELIMITER

    def __getitem__(self, item):
        if type(item) is str and len(item) == 1:
            return self.catcodes[ord(item)]
        elif type(item) is int and 0 <= item < len(self.catcodes):
            return self.catcodes[ord(item)]
        else:
            raise TypeError("'{}' is not a valid character".format(item))

    def __setitem__(self, key, value):
        if type(key) is str and len(key) == 1:
            key = ord(key)
        elif type(key) is not int or not 0 <= key < len(self.catcodes):
            raise TypeError("'{}' is not a valid character".format(key))


#######################################################################################################################

class CharacterStream(object):

    def __init__(self, source:str):
        self.source = source # type:str
        self._pos = 0        # type:int
        self.default_char = '\u0000'  # type:str

    def __getitem__(self, item):
        if 0 <= item < len(self.source):
            return self.source[item]
        else:
            return self.default_char

    def __len__(self):
        return len(self.source)

    def __get_predicate(self, p):
        if len(p) == 1 and callable(p[0]):
            return p[0]
        elif len(p) == 1 and type(p[0]) in [list, tuple]:
            return lambda c: c in p[0]
        else:
            return lambda c: c in p

    def drop(self, count:int):
        if count > 0:
            p = self._pos + count
            self._pos = min(p, len(self.source))

    def drop_if(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        result = i < len(s) and p(s[i])
        if result:
            self._pos += 1
        return result

    def drop_while(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        while i < len(s) and p(s[i]):
            i += 1
        self._pos = i

    def eof(self):
        return self._pos >= len(self.source)

    def get_line_from_pos(self, pos):
        return self.source.count('\n', 0, pos)

    def next(self):
        i = self._pos
        s = self.source
        if i < len(s):
            self._pos += 1
            return s[i]
        else:
            return self.default_char

    def peek(self, index=0):
        return self.__getitem__(self._pos + index)

    def peek_string(self, count:int):
        if self._pos < len(self.source):
            return self.source[self._pos:self._pos+count]
        else:
            return ''

    def skip(self, count:int):
        self._pos = min(len(self.source), self._pos + count)

    def take(self, count:int):
        if count > 0:
            p = self._pos
            result = self.source[p:p+count]
            self._pos = min(len(self.source), p+count)
            return result
        else:
            return ''

    def take_if(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        if i < len(s) and p(s[i]):
            self._pos += 1
            return s[i]
        else:
            return ''

    def take_while(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        while i < len(s) and p(s[i]):
            i += 1
        result = s[self._pos:i]
        self._pos = i
        return result

    def test(self, s):
        if s is None:
            return False
        p = self._pos
        source = self.source
        if p >= len(source):
            return False
        if len(s) == 1:
            return source[p] == s
        else:
            return source[p:p+len(s)] == s

    @property
    def current(self):
        return self.__getitem__(self._pos)

    @property
    def current_line(self):
        return self.get_line_from_pos(self._pos)

    @property
    def current_pos(self):
        return self._pos

    @classmethod
    def from_file(cls, filename:str):
        with open(filename, 'r') as f:
            source = ''.join(list(f.readlines()))
        return CharacterStream(source)

    @classmethod
    def from_string(cls, text:str):
        return CharacterStream(text)


#######################################################################################################################

class Lexer(object):

    def __init__(self, source:CharacterStream):
        self.source = source
        self.catcodes = CategoryCodes()
        self.keywords = set()                   # type:set
        self.ext_symbols = {
            '+=', '-=', '*=', '/=', '%=',
            '<=', '>=', '==', '!=',
            '<<', '>>', '**', '//',
            '&&', '||', '&=', '|='
            '===', '<<=', '>>=', '**=', '//=',
            '..', '...',
            '<~', '~>',
        }
        self.line_comment = None
        self.block_comment_start = None
        self.block_comment_end = None
        assert isinstance(source, CharacterStream)

    def __iter__(self):
        return self

    def __next__(self):
        source = self.source
        pos = source.current_pos
        if source.eof():
            raise StopIteration

        if source.test(self.line_comment):
            source.drop_while(lambda c: c != '\n')
            return self.__next__()
        if source.test(self.block_comment_start):
            source.drop(len(self.block_comment_start))
            while not source.eof() and not source.test(self.block_comment_end):
                source.drop(1)
            return self.__next__()

        cc = self.catcodes[source.current]
        if cc == CatCode.IGNORE:
            source.drop(1)
            return self.__next__()

        elif cc == CatCode.INVALID:
            raise SyntaxError("invalid character in input stream: {}/'{}'".format(
                hex(ord(source.current)), source.current
            ))

        elif cc == CatCode.LINE_COMMENT:
            source.drop_while(lambda c: c != '\n')
            return self.__next__()

        elif cc == CatCode.WHITESPACE:
            source.drop_while(lambda c: self.catcodes[c] == CatCode.WHITESPACE)
            return self.__next__()

        elif cc == CatCode.STRING_DELIMITER:
            return pos, TokenType.STRING, self.read_string()

        elif cc in [CatCode.SYMBOL, CatCode.DELIMITER]:
            return pos, TokenType.SYMBOL, self.read_symbol()

        elif cc in [CatCode.LEFT_BRACKET, CatCode.RIGHT_BRACKET]:
            tt = TokenType.LEFT_BRACKET if cc == CatCode.LEFT_BRACKET else TokenType.RIGHT_BRACKET
            return pos, tt, source.next()

        elif '0' <= source.current <= '9' or cc == CatCode.NUMERIC:
            return pos, TokenType.NUMBER, self.read_number()

        elif cc == CatCode.ALPHA:
            name = self.read_name()
            tt = TokenType.KEYWORD if name in self.keywords else TokenType.SYMBOL
            return pos, tt, name

        elif cc == CatCode.NEWLINE:
            return pos, TokenType.NEWLINE, source.next()

        else:
            raise SyntaxError("invalid character in input stream: {}/'{}'".format(
                hex(ord(source.current)), source.current
            ))

    def read_name(self):
        source = self.source
        return source.take_while(lambda c: self.catcodes[c] in [CatCode.ALPHA, CatCode.NUMERIC])

    def read_number(self):
        source = self.source
        if source.current == '0' and source.peek(1) in ('x', 'X', 'b','B', 'o', 'O'):
            base = { 'x': 16, 'o': 8, 'b': 2 }[source.peek(1).lower()]
            if base == 16:
                is_digit = lambda c: '0' <= c <= '9' or 'A' <= c <= 'F' or 'a' <= c <= 'f'
            elif base == 8:
                is_digit = lambda c: '0' <= c <= '7'
            else:
                is_digit = lambda c: c in ('0', '1')
            source.drop(2)
            result = source.take_while(is_digit)
            return int(result, base)

        else:
            is_digit = lambda c: '0' <= c <= '9'
            result = source.take_while(is_digit)
            if source.current == '.' and is_digit(source.peek(1)):
                result += source.next()
                result += source.take_while(is_digit)

            if source.current in ['e', 'E'] and (is_digit(source.peek(1)) or
                                                     (source.peek(1) in ['+', '-'] and is_digit(source.peek(2)))):
                result += source.next()
                if source.current in ['+', '-']:
                    result += source.next()
                result += source.take_while(is_digit)

            if all([is_digit(c) for c in result]):
                return int(result)
            else:
                return float(result)

    def read_string(self):
        source = self.source
        delimiter = source.current
        i = 1
        while source.peek(i) not in [delimiter, '\u0000']:
            i += 2 if source.peek(i) == '\\' else 1
        if source.peek(i) == delimiter:
            i += 1
        return source.take(i)

    def read_symbol(self):
        source = self.source
        result = source.next()
        nc = source.current
        pc = source.peek(1)
        if self.catcodes[nc] == CatCode.SYMBOL:
            if self.catcodes[pc] == CatCode.SYMBOL:
                s = result + nc + pc
                if s in self.ext_symbols:
                    return result + source.take(2)
            s = result + nc
            if s in self.ext_symbols:
                return result + source.next()
        return result

    def add_keyword(self, keyword):
        self.keywords.add(keyword)

    def add_keywords(self, *keywords):
        for keyword in keywords:
            self.add_keyword(keyword)
