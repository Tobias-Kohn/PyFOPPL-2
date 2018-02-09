#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 09. Feb 2018, Tobias Kohn
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

class AstControl(AstNode):
    pass

class AstLeaf(AstNode):
    pass

class AstOperator(AstNode):
    pass

#######################################################################################################################

class AstBinary(AstOperator):

    __binary_ops = {
        '+':  ('add',  lambda x, y: x + y),
        '-':  ('sub',  lambda x, y: x - y),
        '*':  ('mul',  lambda x, y: x * y),
        '/':  ('div',  lambda x, y: x / y),
        '%':  ('mod',  lambda x, y: x % y),
        '//': ('idiv', lambda x, y: x // y),
        '**': ('pow',  lambda x, y: x ** y),
        '<<': ('shl',  lambda x, y: x << y),
        '>>': ('shr',  lambda x, y: x >> y),
        '&':  ('and',  lambda x, y: x & y),
        '|':  ('or',   lambda x, y: x | y),
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
        name = 'visit_binary_' + self.op_name
        return [name] + super(AstBinary, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__binary_ops[self.op][1]

    @property
    def op_name(self):
        return self.__binary_ops[self.op][0]


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
        self.function_name = function if type(function) is str else function.name # type:str
        assert(type(function) is str or isinstance(function, AstFunction))
        assert(all([isinstance(arg, AstNode) for arg in args]))

    def __repr__(self):
        function = self.function if type(self.function) is str else repr(self.function)
        args = [repr(arg) for arg in self.args]
        return "{}({})".format(function, ', '.join(args))


class AstCompare(AstOperator):

    __cmp_ops = {
        '==': ('eq', lambda x, y: x == y),
        '!=': ('ne', lambda x, y: x != y),
        '<':  ('lt', lambda x, y: x < y),
        '<=': ('le', lambda x, y: x <= y),
        '>':  ('gt', lambda x, y: x > y),
        '>=': ('ge', lambda x, y: x >= y),
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
        name = 'visit_binary_' + self.op_name
        return [name] + super(AstCompare, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__cmp_ops[self.op][1]

    @property
    def op_name(self):
        return self.__cmp_ops[self.op][0]


class AstDef(AstNode):

    def __init__(self, name:str, value:AstNode):
        self.name = name
        self.value = value
        assert(type(name) is str)
        assert(isinstance(value, AstNode))

    def __repr__(self):
        return "{} := {}".format(self.name, repr(self.value))


class AstFor(AstControl):

    def __init__(self, target:str, source:AstNode, body:AstNode):
        self.target = target
        self.source = source
        self.body = body
        assert(type(target) is str)
        assert(isinstance(source, AstNode))
        assert(isinstance(body, AstNode))

    def __repr__(self):
        return "for {} in {}: ({})".format(self.target, repr(self.source), repr(self.body))


class AstFunction(AstNode):

    def __init__(self, name:str, parameters:list, body:AstNode):
        if name is None:
            name = '__lambda__'
        self.name = name
        self.parameters = parameters
        self.body = body
        assert(type(name) is str and name != '')
        assert(type(parameters) is list and all([type(p) is str for p in parameters]))
        assert(isinstance(body, AstNode))

    def __repr__(self):
        return "{}({}): ({})".format(self.name, ', '.join(self.parameters), repr(self.body))


class AstIf(AstControl):

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


class AstLet(AstNode):

    def __init__(self, targets:list, sources:list, body:AstNode):
        self.targets = targets
        self.sources = sources
        self.body = body
        assert(type(targets) is list and all([type(target) in (str, tuple) for target in targets]))
        assert(type(sources) is list and all([isinstance(source, AstNode) for source in sources]))
        assert(len(targets) == len(sources) and len(targets) > 0)
        assert(isinstance(body, AstNode))

    def __repr__(self):
        bindings = ['{} := {}'.format(target, repr(source)) for target, source in zip(self.targets, self.sources)]
        return "let [{}] in ({})".format('; '.join(bindings), repr(self.body))


class AstUnary(AstOperator):

    __unary_ops = {
        '+':   ('plus',  lambda x: x),
        '-':   ('minus', lambda x: -x),
        'not': ('not',   lambda x: not x),
    }

    def __init__(self, op:str, item:AstNode):
        self.op = op
        self.item = item
        assert(op in self.__unary_ops)
        assert(isinstance(item, AstNode))

    def __repr__(self):
        return "{}{}".format(self.op, repr(self.item))

    def get_visitor_names(self):
        name = 'visit_unary_' + self.op_name
        return [name] + super(AstUnary, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__unary_ops[self.op][1]

    @property
    def op_name(self):
        return self.__unary_ops[self.op][0]


class AstSymbol(AstLeaf):

    def __init__(self, name:str):
        self.name = name
        assert(type(name) is str)

    def __repr__(self):
        return self.name


class AstValue(AstLeaf):

    def __init__(self, value):
        self.value = value
        assert(type(value) in [bool, float, int, str])

    def __repr__(self):
        return repr(self.value)


class AstValueVector(AstLeaf):

    def __init__(self, items:list):
        self.items = items

        def is_value_vector(v):
            if type(v) in (list, tuple):
                return all([is_value_vector(w) for w in v])
            else:
                return type(v) in [bool, float, int, str]

        assert(type(items) is list and is_value_vector(items))

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return repr(self.items)


class AstVector(AstNode):

    def __init__(self, items:list):
        self.items = items
        assert(type(items) is list and all([isinstance(item, AstNode) for item in items]))

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return "[{}]".format(', '.join([repr(item) for item in self.items]))
