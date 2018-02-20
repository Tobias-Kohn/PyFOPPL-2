#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Feb 2018, Tobias Kohn
#
from typing import Optional

class ClojureObject(object):

    _attributes = {'col_offset', 'lineno'}
    tag = None

    def visit(self, visitor):
        """
        The visitor-object given as argument must provide at least one `visit_XXX`-method to be called by this method.
        If the visitor does not provide any specific `visit_XXX`-method to be called, the method will try and call
        `visit_node` or `generic_visit`, respectively.

        :param visitor: An object with a `visit_XXX`-method.
        :return:        The result returned by the `visit_XXX`-method of the visitor.
        """
        name = self.__class__.__name__.lower()
        method_names = ['visit_' + name, 'visit_node', 'generic_visit']
        methods = [getattr(visitor, name, None) for name in method_names]
        methods = [name for name in methods if name is not None]
        if len(methods) == 0 and callable(visitor):
            return visitor(self)
        elif len(methods) > 0:
            return methods[0](self)
        else:
            raise RuntimeError("visitor '{}' has no visit-methods to call".format(type(visitor)))


#######################################################################################################################

class Form(ClojureObject):

    def __init__(self, items:list, lineno:Optional[int]=None):
        self.items = items
        if lineno is not None:
            self.lineno = lineno
        assert type(items) in [list, tuple]
        assert all([isinstance(item, ClojureObject) for item in items])
        assert lineno is None or type(lineno) is int

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "({})".format(' '.join([repr(item) for item in self.items]))

    def visit(self, visitor):
        name = self.name
        if name is not None:
            name = name.replace('-', '_').replace('.', '_').replace('/', '_')
            method = getattr(visitor, 'visit_' + name, None)
            if method is not None:
                return method(*self.items[1:])
        return super(Form, self).visit(visitor)

    @property
    def head(self):
        return self.items[0]

    @property
    def tail(self):
        return Form(self.items[1:])

    @property
    def name(self):
        if len(self.items) > 0 and isinstance(self.items[0], Symbol):
            return self.items[0].name
        else:
            return None

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) > 0

    @property
    def length(self):
        return len(self.items)


class Symbol(ClojureObject):

    def __init__(self, name:str, lineno:Optional[int]=None):
        self.name = name
        if lineno is not None:
            self.lineno = lineno
        assert type(name) is str
        assert lineno is None or type(lineno) is int

    def __repr__(self):
        return self.name


class Value(ClojureObject):

    def __init__(self, value, lineno:Optional[int]=None):
        self.value = value
        if lineno is not None:
            self.lineno = lineno
        assert type(value) in [bool, complex, float, int, str]
        assert lineno is None or type(lineno) is int

    def __repr__(self):
        return repr(self.value)


class Vector(ClojureObject):

    def __init__(self, items:list, lineno:Optional[int]=None):
        self.items = items
        if lineno is not None:
            self.lineno = lineno
        assert type(items) in [list, tuple]
        assert all([isinstance(item, ClojureObject) for item in items])
        assert lineno is None or type(lineno) is int

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "[{}]".format(' '.join([repr(item) for item in self.items]))

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) > 0

    @property
    def length(self):
        return len(self.items)

#######################################################################################################################

class Visitor(object):

    def visit(self, ast):
        if isinstance(ast, ClojureObject):
            return ast.visit(self)
        elif hasattr(ast, '__iter__'):
            return [self.visit(item) for item in ast]
        else:
            raise TypeError("cannot walk/visit an object of type '{}'".format(type(ast)))

    def visit_node(self, node:ClojureObject):
        return node
