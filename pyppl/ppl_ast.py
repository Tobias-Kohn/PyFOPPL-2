#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 22. Feb 2018, Tobias Kohn
#
from typing import Optional

class AstNode(object):
    """
    The `AstNode` is the base-class for all AST-nodes. You will typically not instantiate an object of this class,
    but derive a specific AST-node from it.
    """

    _attributes = {'col_offset', 'lineno'}
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

    def __get_envelop_method_names(self):
        """
        Returns a list of two names `enter_XXX` and `leave_XXX`, where the `XXX` stands for the name of the class.
        This is used inside the `visit`-method.

        :return:  A list with exactly two strings.
        """
        name = self.__class__.__name__
        if name.startswith("Ast"):
            name = name[3:]
        elif name.endswith("Node"):
            name = name[:-4]
        name = name.lower()
        return ['enter_' + name, 'leave_' + name]

    def visit(self, visitor):
        """
        The visitor-object given as argument must provide at least one `visit_XXX`-method to be called by this method.
        Possible names for the `visit_XXX`-method are given by `get_visitor_names()`. Override that method in order
        to control which visitor-method is actually called.

        If the visitor does not provide any specific `visit_XXX`-method to be called, the method will try and call
        `visit_node` or `generic_visit`, respectively.

        It is possible to provide, in addition to a `visit_XXX`-method, two methods `enter_XXX` and `leave_XXX`, which
        are called right before, and right after, respectively, the `visit_XXX`-method itself is called. They do not
        replace but supplement the `visit_XXX`-method.

        :param visitor: An object with a `visit_XXX`-method.
        :return:        The result returned by the `visit_XXX`-method of the visitor.
        """
        visit_children_first = getattr(visitor, '__visit_children_first__', False) is True
        method_names = self.get_visitor_names() + ['visit_node', 'generic_visit']
        methods = [getattr(visitor, name, None) for name in method_names]
        methods = [name for name in methods if name is not None]
        env_methods = [getattr(visitor, name, None) for name in self.__get_envelop_method_names()]
        env_methods = [name for name in env_methods if name is not None]
        if len(methods) == 0 and callable(visitor):
            if visit_children_first:
                self.visit_children(visitor)
            return visitor(self)
        elif len(methods) > 0:
            if len(env_methods) == 2:
                env_methods[0](self)
                try:
                    if visit_children_first:
                        self.visit_children(visitor)
                    result = methods[0](self)
                finally:
                    env_methods[1](self)
                return result
            else:
                if visit_children_first:
                    self.visit_children(visitor)
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
        assert type(attr_name) is str
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
        if ast is None:
            return None
        elif isinstance(ast, AstNode):
            return ast.visit(self)
        elif hasattr(ast, '__iter__'):
            return [self.visit(item) for item in ast]
        else:
            raise TypeError("cannot walk/visit an object of type '{}'".format(type(ast)))

    def visit_node(self, node:AstNode):
        node.visit_children(self)
        return node


#######################################################################################################################

class Scope(object):

    def __init__(self, prev, name:Optional[str]=None, lineno:Optional[int]=None):
        self.prev = prev
        self.name = name
        self.lineno = lineno
        self.bindings = {}
        assert prev is None or isinstance(prev, Scope)
        assert name is None or type(name) is str
        assert lineno is None or type(lineno) is int

    def define(self, name:str, value):
        assert type(name) is str and str != ''
        self.bindings[name] = value

    def resolve(self, name:str):
        if name in self.bindings:
            return self.bindings[name]
        elif self.prev is not None:
            return self.prev.find(name)
        else:
            return None


class ScopedVisitor(Visitor):

    def __init__(self):
        self.scope = Scope(None)

    def enter_scope(self, name:Optional[str]=None):
        self.scope = Scope(self.scope, name)

    def leave_scope(self):
        self.scope = self.scope.prev
        assert(self.scope is not None)

    def define(self, name:str, value):
        self.scope.define(name, value)

    def resolve(self, name:str):
        return self.scope.resolve(name)

    def enter_def(self, node):
        pass

    def leave_def(self, node):
        self.define(node.name, node.value)

    def enter_import(self, node):
        pass

    def leave_import(self, node):
        if node.imported_names is not None:
            for name in node.imported_names:
                self.define(name, AstSymbol(name, import_source=node.module_name))
        else:
            self.define(node.module_name, AstSymbol(node.module_name, import_source=node.module_name))

    def enter_let(self, node):
        self.enter_scope()
        for target, source in zip(node.targets, node.sources):
            self.define(target, source)

    def leave_let(self, node):
        self.leave_scope()


#######################################################################################################################

class AstControl(AstNode):
    pass

class AstLeaf(AstNode):
    pass

class AstOperator(AstNode):
    pass

#######################################################################################################################

class AstAttribute(AstNode):

    def __init__(self, base:AstNode, attr:str):
        self.base = base
        self.attr = attr
        assert isinstance(base, AstNode)
        assert type(attr) is str

    def __repr__(self):
        return "{}.{}".format(repr(self.base), self.attr)


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
        '&':  ('bit_and', lambda x, y: x & y),
        '|':  ('bit_or',  lambda x, y: x | y),
        '^':  ('bit-xor', lambda x, y: x ^ y),
        'and': ('and',    lambda x, y: x and y),
        'or':  ('or',     lambda x, y: x or y),
    }

    def __init__(self, left:AstNode, op:str, right:AstNode):
        self.left = left
        self.op = op
        self.right = right
        assert isinstance(left, AstNode) and isinstance(right, AstNode)
        assert op in self.__binary_ops

    def __repr__(self):
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))

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
        if items is None:
            items = []
        self.items = items
        # flatten nested bodies:
        if any(isinstance(item, AstBody) for item in items):
            new_items = []
            for item in items:
                if isinstance(item, AstBody):
                    new_items += item.items
                else:
                    new_items.append(item)
            self.items = new_items
        assert type(items) is list
        assert all([isinstance(item, AstNode) for item in items])

    def __repr__(self):
        return "Body({})".format('; '.join([repr(item) for item in self.items]))


class AstCall(AstNode):

    def __init__(self, function:AstNode, args:list, keyword_args:dict=None):
        if keyword_args is None:
            keyword_args = {}
        self.function = function
        self.args = args
        self.keyword_args = keyword_args # type:dict
        assert isinstance(function, AstNode)
        assert all([isinstance(arg, AstNode) for arg in args])
        assert type(keyword_args) is dict
        assert all([type(key) is str and isinstance(keyword_args[key], AstNode) for key in keyword_args.keys()])

    def __repr__(self):
        args = [repr(arg) for arg in self.args]
        for key in self.keyword_args:
            args.append('{}={}'.format(key, repr(self.keyword_args[key])))
        return "{}({})".format(repr(self.function), ', '.join(args))

    def get_visitor_names(self):
        name = self.function_name
        if name is not None:
            name = 'visit_call_' + name
            return [name] + super(AstCall, self).get_visitor_names()
        else:
            return super(AstCall, self).get_visitor_names()

    @property
    def function_name(self):
        if isinstance(self.function, AstSymbol):
            return self.function.name
        else:
            return None


class AstCompare(AstOperator):

    __cmp_ops = {
        '==': ('eq', lambda x, y: x == y),
        '!=': ('ne', lambda x, y: x != y),
        '<':  ('lt', lambda x, y: x < y),
        '<=': ('le', lambda x, y: x <= y),
        '>':  ('gt', lambda x, y: x > y),
        '>=': ('ge', lambda x, y: x >= y),
        'is': ('is', lambda x, y: x is y),
        'in': ('in', lambda x, y: x in y),
        'is not': ('is_not', lambda x, y: x is not y),
        'not in': ('not_in', lambda x, y: x not in y),
    }

    def __init__(self, left:AstNode, op:str, right:AstNode,
                 second_op:Optional[str]=None, second_right:Optional[AstNode]=None):
        if op == '=': op = '=='
        self.left = left
        self.op = op
        self.right = right
        self.second_op = op
        self.second_right = second_right
        assert isinstance(left, AstNode)
        assert isinstance(right, AstNode)
        assert op in self.__cmp_ops
        assert ((second_op is None and second_right is None) or
                (second_op in self.__cmp_ops and isinstance(second_right, AstNode)))

    def __repr__(self):
        if self.second_op is not None:
            return "({} {} {} {} {})".format(
                repr(self.left), self.op, repr(self.right),
                self.second_op, repr(self.second_right)
            )
        else:
            return "({} {} {})".format(repr(self.left), self.op, repr(self.right))

    def get_visitor_names(self):
        if self.second_op is not None:
            name = 'visit_ternary_' + self.op_name + '_' + self.op_name_2
        else:
            name = 'visit_binary_' + self.op_name
        return [name] + super(AstCompare, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__cmp_ops[self.op][1]

    @property
    def op_name(self):
        return self.__cmp_ops[self.op][0]

    @property
    def op_function_2(self):
        return self.__cmp_ops[self.second_op][1] if self.second_op is not None else None

    @property
    def op_name_2(self):
        return self.__cmp_ops[self.second_op][0] if self.second_op is not None else None


class AstDef(AstNode):

    def __init__(self, name, value:AstNode):
        self.name = name
        self.value = value
        assert type(name) is str or (type(name) is tuple and all(type(item) is str for item in name))
        assert isinstance(value, AstNode)

    def __repr__(self):
        name = "({})".format(', '.join(self.name)) if type(self.name) is tuple else self.name
        return "{} := {}".format(name, repr(self.value))


class AstFor(AstControl):

    def __init__(self, target, source:AstNode, body:AstNode):
        self.target = target
        self.source = source
        self.body = body
        assert type(target) is str or (type(target) is tuple and all(type(item) is str for item in target))
        assert isinstance(source, AstNode)
        assert isinstance(body, AstNode)

    def __repr__(self):
        return "for {} in {}: ({})".format(self.target, repr(self.source), repr(self.body))


class AstFunction(AstNode):

    def __init__(self, name:Optional[str], parameters:list, body:AstNode, *, vararg:Optional[str]=None,
                 doc_string:Optional[str]=None):
        if name is None:
            name = '__lambda__'
        self.name = name
        self.parameters = parameters
        self.body = body
        self.vararg = vararg
        self.doc_string = doc_string
        assert type(name) is str and name != ''
        assert type(parameters) is list and all([type(p) is str for p in parameters])
        assert isinstance(body, AstNode)
        assert vararg is None or type(vararg) is str
        assert doc_string is None or type(doc_string) is str

    def __repr__(self):
        params = self.parameters
        if self.vararg is not None:
            params.append('*' + self.vararg)
        return "{}({}): ({})".format(self.name, ', '.join(params), repr(self.body))


class AstIf(AstControl):

    def __init__(self, test:AstNode, if_node:AstNode, else_node:Optional[AstNode]):
        self.test = test
        self.if_node = if_node
        self.else_node = else_node
        assert isinstance(test, AstNode)
        assert isinstance(if_node, AstNode)
        assert else_node is None or isinstance(else_node, AstNode)

    def __repr__(self):
        if self.else_node is None:
            return "if {} then {}".format(repr(self.test), repr(self.if_node))
        else:
            return "if {} then {} else {}".format(repr(self.test), repr(self.if_node), repr(self.else_node))


class AstImport(AstNode):

    def __init__(self, module_name:str, imported_names:Optional[list], alias:Optional[str]=None):
        self.module_name = module_name
        self.imported_names = imported_names
        self.alias = alias
        assert type(module_name) is str and module_name != ''
        assert (imported_names is None or
                (type(imported_names) is list and all([type(item) is str for item in imported_names])))
        assert alias is None or (type(alias) is str and alias != '')
        assert alias is None or (imported_names is None or len(imported_names) == 1)

    def __repr__(self):
        alias = "as {}".format(self.alias) if self.alias is not None else ""
        if self.imported_names is None:
            return "import {}{}".format(self.module_name, alias)
        else:
            return "from {} import {}{}".format(self.module_name, ','.join(self.imported_names), alias)


class AstLet(AstNode):

    def __init__(self, targets:list, sources:list, body:AstNode):
        self.targets = targets
        self.sources = sources
        self.body = body
        assert type(targets) is list and all([type(target) in (str, tuple) for target in targets])
        assert type(sources) is list and all([isinstance(source, AstNode) for source in sources])
        assert len(targets) == len(sources) and len(targets) > 0
        assert isinstance(body, AstNode)

    def __repr__(self):
        bindings = ['{} := {}'.format(target, repr(source)) for target, source in zip(self.targets, self.sources)]
        return "let [{}] in ({})".format('; '.join(bindings), repr(self.body))


class AstListFor(AstNode):

    def __init__(self, target, source: AstNode, expr: AstNode, test: AstNode = None):
        self.target = target
        self.source = source
        self.expr = expr
        self.test = test
        assert type(target) is str or (type(target) is tuple and all(type(item) is str for item in target))
        assert isinstance(source, AstNode)
        assert isinstance(expr, AstNode)
        assert test is None or isinstance(test, AstNode)

    def __repr__(self):
        if self.test is not None:
            return "[{} for {} in {} if {}]".format(repr(self.expr), self.target, repr(self.source), repr(self.test))
        else:
            return "[{} for {} in {}]".format(repr(self.expr), self.target, repr(self.source))


class AstObserve(AstNode):

    def __init__(self, dist:AstNode, observed_value:AstNode):
        self.dist = dist
        self.value = observed_value
        assert isinstance(self.dist, AstNode)
        assert isinstance(self.value, AstNode)

    def __repr__(self):
        return "observe({}, {})".format(repr(self.dist), repr(self.value))


class AstReturn(AstNode):

    def __init__(self, value:AstNode):
        if value is None:
            value = AstValue(None)
        self.value = value
        assert isinstance(self.value, AstNode)

    def __repr__(self):
        return "return {}".format(repr(self.value))


class AstSample(AstNode):
    def __init__(self, dist: AstNode):
        self.dist = dist
        assert isinstance(dist, AstNode)

    def __repr__(self):
        return "sample({})".format(repr(self.dist))


class AstSlice(AstNode):

    def __init__(self, base:AstNode, start:Optional[AstNode], stop:Optional[AstNode]):
        self.base = base
        self.start = start
        self.stop = stop
        assert isinstance(base, AstNode)
        assert start is None or isinstance(start, AstNode)
        assert stop is None or isinstance(stop, AstNode)

    def __repr__(self):
        return "{}[{}:{}]".format(
            repr(self.base),
            repr(self.start) if self.start is not None else '',
            repr(self.stop) if self.stop is not None else ''
        )

    @property
    def start_as_int(self):
        if isinstance(self.start, AstValue) and type(self.start.value) is int:
            return self.start.value
        else:
            return None

    @property
    def stop_as_int(self):
        if isinstance(self.stop, AstValue) and type(self.stop.value) is int:
            return self.stop.value
        else:
            return None


class AstSubscript(AstNode):

    def __init__(self, base:AstNode, index:AstNode):
        self.base = base
        self.index = index
        if isinstance(index, AstValue):
            self.index_n = int(index.value) if type(index.value) in [int, bool] else None
        else:
            self.index_n = None
        assert isinstance(base, AstNode)
        assert isinstance(index, AstNode)

    def __repr__(self):
        return "{}[{}]".format(repr(self.base), repr(self.index))

    @property
    def index_as_int(self):
        if isinstance(self.index, AstValue):
            return self.index.value if type(self.index.value) is int else None
        else:
            return None


class AstSymbol(AstLeaf):

    def __init__(self, name:str, import_source:Optional[str]=None):
        self.name = name
        self.import_source = import_source
        assert type(name) is str
        assert import_source is None or type(import_source) is str

    def __repr__(self):
        return self.name


class AstUnary(AstOperator):

    __unary_ops = {
        '+':   ('plus',  lambda x: x),
        '-':   ('minus', lambda x: -x),
        'not': ('not',   lambda x: not x),
    }

    def __init__(self, op:str, item:AstNode):
        self.op = op
        self.item = item
        assert op in self.__unary_ops
        assert isinstance(item, AstNode)

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


class AstValue(AstLeaf):

    def __init__(self, value):
        self.value = value
        assert type(value) in [bool, complex, float, int, str]

    def __repr__(self):
        return repr(self.value)


class AstValueVector(AstLeaf):

    def __init__(self, items:list):
        self.items = items

        def is_value_vector(v):
            if type(v) in (list, tuple):
                return all([is_value_vector(w) for w in v])
            else:
                return type(v) in [bool, complex, float, int, str]

        assert type(items) is list and is_value_vector(items)

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
        assert type(items) is list and all([isinstance(item, AstNode) for item in items])

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return "[{}]".format(', '.join([repr(item) for item in self.items]))


class AstWhile(AstControl):

    def __init__(self, test:AstCompare, body:AstNode):
        self.test = test
        self.body = body
        assert isinstance(test, AstCompare)
        assert isinstance(body, AstNode)

    def __repr__(self):
        return "while {} do {}".format(repr(self.test), repr(self.body))


#######################################################################################################################

def makeVector(items):
    if all([isinstance(item, AstValue) for item in items]):
        return AstValueVector([item.value for item in items])
    elif all([type(item) in [bool, complex, float, int, str] for item in items]):
        return AstValueVector(items)
    else:
        return AstVector(items)

#######################################################################################################################

def is_boolean(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is bool
    else:
        return False

def is_integer(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is int
    else:
        return False

def is_number(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) in [complex, float, int]
    else:
        return False

def is_string(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is str
    else:
        return False
