#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 07. Feb 2018, Tobias Kohn
#
class AstNode(object):
    """
    The `AstNode` is the base-class for all AST-nodes. You will typically not instantiate an object of this class,
    but derive a specific AST-node from it.
    """

    tag = None

    def get_fields(self):
        fields = set(self.__dict__).difference(set(AstNode.__dict__))
        fields = [name for name in fields if len(name) > 0 and not name.startswith('_')]
        return fields

    def set_field_values(self, source):
        if isinstance(source, self.__class__):
            for field in self.get_fields():
                setattr(self, field, getattr(source, field))
        elif type(source) is dict:
            for field in source:
                if hasattr(self, field):
                    setattr(self, field, source[field])
        else:
            raise RuntimeError("cannot set fields from source '{}'".format(repr(source)))

    def get_children(self):
        """
        Returns a list of all fields, which are either `AstNode`-objects, or sequences (list/tuples) of such objects.

        :return: A list of strings denoting fields, which are `AstNode`-objects or sequences thereof.
        """
        def is_valid(name):
            field = getattr(self, name, None)
            if isinstance(field, AstNode):
                return True
            elif hasattr(field, '__iter__') and all([isinstance(item, AstNode) for item in field]):
                return True
            else:
                return False

        return [item for item in self.get_fields() if is_valid(item)]

    def get_type(self):
        """
        Returns the type of this node.

        :return: Either an instance of `Type` (see `ppl_types`), or `None`.
        """
        return getattr(self, '__type__', None)

    def get_visitor_names(self):
        """
        Returns an ordered list of possible names for the visit-methods to be called by `visit`.

        We want to be flexible and provide a hierarchy of method names to try out. Take, for instance, an AST-node
        for a FOR-loop. The visit-method to call might then be called `visit_ForLoop`, `visit_for_loop`, or we might
        end up having a more generic `visit_loop` to call.

        The default implementation given here provides various possibilities based on the name of the instance's class.
        If, say, the node is of class `AstForLoop`, then we try the following names:
        `visit_AstForLoop`, `visit_astforloop`, `visit_for_loop`, `visit_forloop`
        Be overriding this method, you might change the names altogether, or insert a more general name such as
        `visit_loop` or `visit_compound_statement`.

        :return:   A list of strings with possible method names.
        """
        name = self.__class__.__name__
        if name.startswith("Ast"):
            name = name[3:]
        elif name.endswith("Node"):
            name = name[:-4]
        if name.islower():
            result = ['visit_' + name]
        else:
            name2 = ''.join([n if n.islower() else "_" + n.lower() for n in name])
            result = ['visit_' + name, 'visit_' + name.lower(), 'visit_' + name2]
        return result

    def visit(self, visitor):
        """
        The visitor-object given as argument must provide at least one `visit_XXX`-method to be called by this method.
        Possible names for the `visit_XXX`-method are given by `_get_visitor_names()`. Override that method in order
        to control which visitor-method is actually called.

        If the visitor does not provide any specific `visit_XXX`-method to be called, the method will try and call
        `visit_node` or `generic_visit`, respectively.

        :param visitor: An object with a `visit_XXX`-method.
        :return:        The result returned by the `visit_XXX`-method of the visitor.
        """
        method_names = self.get_visitor_names() + ['visit_node', 'generic_visit']
        methods = [getattr(visitor, name, None) for name in method_names]
        methods = [name for name in methods if name is not None]
        if len(methods) == 0 and callable(visitor):
            return visitor(self)
        elif len(methods) > 0:
            return methods[0](self)
        else:
            raise RuntimeError("visitor '{}' has no visit-methods to call".format(type(visitor)))

    def visit_children(self, visitor):
        """
        Goes through all fields provided by the method `get_fields`, which are objects derived from `AstNode`.
        For each such object, the `visit`-method (see above) is called.

        :param visitor: An object with `visit_XXX`-methods to be called by the children of this node.
        :return:        A list with the values returned by the called `visit_XXX`-methods.
        """
        result = []
        for name in self.get_fields():
            item = getattr(self, name, None)
            if isinstance(item, AstNode):
                result.append(item.visit(visitor))
            elif hasattr(item, '__iter__'):
                result.append([node.visit(visitor) for node in item if isinstance(node, AstNode)])
        return result

    def visit_attribute(self, visitor, attr_name:str):
        """
        Sets an attribute on each node in the AST, based on the provided visitor (see `visit`-method above).

        :param visitor:    An object with `visit_XXX`-methods to be called.
        :param attr_name:  The name of the attribute to set, must be a string.
        :return:           The value of the attribute set.
        """
        assert(type(attr_name) is str)
        for name in self.get_fields():
            item = getattr(self, name, None)
            if isinstance(item, AstNode):
                item.visit_attribute(visitor, attr_name)
            elif hasattr(item, '__iter__'):
                for node in item:
                    if isinstance(node, AstNode):
                        node.visit_attribute(visitor, attr_name)
        result = self.visit(visitor)
        result = result if result is not self else None
        setattr(self, attr_name, result)
        return result


class Visitor(object):
    """
    There is no strict need to derive a visitor or walker from this base class. It does, however, provide a
    default implementation for `visit` as well as `visit_node`.
    """

    def visit(self, ast):
        if isinstance(ast, AstNode):
            return ast.visit(self)
        elif hasattr(ast, '__iter__'):
            return [self.visit(item) for item in ast]
        else:
            raise TypeError("cannot walk/visit an object of type '{}'".format(type(ast)))

    def visit_node(self, node: AstNode):
        node.visit_children(self)
        return node

#######################################################################################################################

class AstBinary(AstNode):

    __binary_ops = {
        '+':  'add',
        '-':  'sub',
        '*':  'mul',
        '/':  'div',
        '%':  'mod',
        '//': 'idiv',
        '**': 'pow',
        '<<': 'shl',
        '>>': 'shr',
        '&':  'and',
        '|':  'or'
    }

    def __init__(self, left:AstNode, op:str, right:AstNode):
        self.left = left
        self.op = op
        self.right = right
        assert(isinstance(left, AstNode) and isinstance(right, AstNode))
        assert(op in self.__binary_ops)

    def __repr__(self):
        return "({}{}{})".format(repr(self.left), self.op, repr(self.right))

    def get_visitor_names(self):
        name = 'visit_binary_' + self.__binary_ops[self.op]
        return [name] + super(AstBinary, self).get_visitor_names()

    @property
    def op_name(self):
        return self.__binary_ops[self.op]


class AstBody(AstNode):

    def __init__(self, items:list):
        self.items = items
        assert(type(items) is list)
        assert(all([isinstance(item, AstNode) for item in items]))

    def __repr__(self):
        return "Body({})".format('; '.join([repr(item) for item in self.items]))


class AstCall(AstNode):

    def __init__(self, function, args:list):
        self.function = function
        self.args = args
        assert(type(function) is str)
        assert(all([isinstance(arg, AstNode) for arg in args]))

    def __repr__(self):
        function = self.function
        args = [repr(arg) for arg in self.args]
        return "{}({})".format(function, ', '.join(args))


class AstCompare(AstNode):

    __cmp_ops = {
        '==': 'eq',
        '!=': 'ne',
        '<':  'lt',
        '<=': 'le',
        '>':  'gt',
        '>=': 'ge',
    }

    def __init__(self, left:AstNode, op:str, right:AstNode):
        if op == '=': op = '=='
        self.left = left
        self.op = op
        self.right = right
        assert(isinstance(left, AstNode))
        assert(isinstance(right, AstNode))
        assert(op in self.__cmp_ops)

    def __repr__(self):
        return "({}{}{})".format(repr(self.left), self.op, repr(self.right))

    def get_visitor_names(self):
        name = 'visit_binary_' + self.__cmp_ops[self.op]
        return [name] + super(AstCompare, self).get_visitor_names()

    @property
    def op_name(self):
        return self.__cmp_ops[self.op]


class AstIf(AstNode):

    def __init__(self, compare:AstCompare, if_node:AstNode, else_node:AstNode):
        self.compare = compare
        self.if_node = if_node
        self.else_node = else_node
        assert(isinstance(compare, AstCompare))
        assert(isinstance(if_node, AstNode))
        assert(else_node is None or isinstance(else_node, AstNode))

    def __repr__(self):
        if self.else_node is None:
            return "if {} then {}".format(repr(self.compare), repr(self.if_node))
        else:
            return "if {} then {} else {}".format(repr(self.compare), repr(self.if_node), repr(self.else_node))


class AstUnary(AstNode):

    __unary_ops = {
        '+': 'plus',
        '-': 'minus',
        'not': 'not',
    }

    def __init__(self, op:str, item:AstNode):
        self.op = op
        self.item = item
        assert(op in self.__unary_ops)
        assert(isinstance(item, AstNode))

    def __repr__(self):
        return "{}{}".format(self.op, repr(self.item))

    def get_visitor_names(self):
        name = 'visit_unary_' + self.__unary_ops[self.op]
        return [name] + super(AstUnary, self).get_visitor_names()

    @property
    def op_name(self):
        return self.__unary_ops[self.op]


class AstSymbol(AstNode):

    def __init__(self, name:str):
        self.name = name
        assert(type(name) is str)

    def __repr__(self):
        return self.name


class AstValue(AstNode):

    def __init__(self, value):
        self.value = value
        assert(type(value) in [bool, float, int, str])

    def __repr__(self):
        return repr(self.value)
