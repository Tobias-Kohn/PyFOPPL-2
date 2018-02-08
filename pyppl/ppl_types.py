#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 07. Feb 2018, Tobias Kohn
#
class Type(object):

    def __init__(self, *, name:str, base=None):
        assert(type(name) is str)
        assert(base is None or isinstance(base, Type))
        self.name = name # type:str
        self.base = base # type:Type

    def __contains__(self, item):
        if item is self:
            return True
        elif isinstance(item, Type):
            return item.base in self
        elif hasattr(item, 'get_type'):
            return self.__contains__(getattr(item, 'get_type')())
        elif hasattr(item, '__type__'):
            return self.__contains__(getattr(item, '__type__'))
        else:
            return False

    def __eq__(self, other):
        return other is self

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name

    def union(self, other):
        if isinstance(other, Type):
            if other in self:
                return self
            elif self in other:
                return other
            elif self.base is not None and other.base is not None:
                return self.base.union(other.base)
            else:
                return AnyType
        else:
            raise RuntimeError("must be a type: '{}'".format(type(other)))

    @property
    def dimension(self):
        return None


#######################################################################################################################

class SequenceType(Type):

    def __init__(self, *, name:str, base=None, item_type:Type=None, size:int=None,
                 recursive:bool=False):
        super(SequenceType, self).__init__(name=name, base=base)
        if recursive:
            assert(item_type is None)
            assert(size is None)
            self.item_type = self
        else:
            self.item_type = item_type
        self.size = size
        self.recursive = recursive
        self._sub_types = {}
        self._sequence_type = base._sequence_type if isinstance(base, SequenceType) else self
        assert(self.item_type is None or isinstance(self.item_type, Type))
        assert(size is None or (type(size) is int and size >= 0))

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, SequenceType) and self._sequence_type is other._sequence_type:
            return other.item_type == self.item_type and other.size == self.size
        else:
            return False

    def __hash__(self):
        if self.item_type is None:
            return hash(self.name)
        elif self.size is None:
            return hash((self.name, hash(self.item_type)))
        else:
            return hash((self.name, hash(self.item_type), self.size))

    def __repr__(self):
        if self.item_type is None or self.recursive:
            return self.name
        elif self.size is None:
            return "{}[{}]".format(self.name, repr(self.item_type))
        else:
            return "{}[{};{}]".format(self.name, repr(self.item_type), self.size)

    def __getitem__(self, item):
        if self.recursive:
            raise TypeError("recursive sequence-type cannot have specialized type")

        if self.item_type is None:
            if type(item) is tuple and len(item) == 2 and isinstance(item[0], Type) and type(item[1]) is int:
                result = self.__getitem__(item[0])
                return result.__getitem__(item[1])

            elif isinstance(item, SequenceType):
                return SequenceType(name=self.name, base=self, item_type=item)

            elif isinstance(item, Type):
                if item not in self._sub_types:
                    self._sub_types[item] = SequenceType(name=self.name, base=self, item_type=item)
                return self._sub_types[item]

        elif self.size is None:
            if type(item) is int and item >= 0:
                if 0 <= item <= 3:
                    if item not in self._sub_types:
                        self._sub_types[item] = SequenceType(name=self.name, base=self,
                                                             item_type=self.item_type, size=item)
                    return self._sub_types[item]
                else:
                    return SequenceType(name=self.name, base=self, item_type=self.item_type, size=item)

        raise TypeError("cannot construct '{}'-subtype of '{}'".format(item, self))

    def __contains__(self, item):
        if item is self:
            return True

        elif isinstance(item, SequenceType) and item._sequence_type is self._sequence_type:
            if self.item_type is None:
                return True
            elif item.item_type in self.item_type and (self.size is None or self.size == item.size):
                return True
            else:
                return False

        elif isinstance(item, Type):
            return item is NullType

        elif hasattr(item, 'get_type'):
            return self.__contains__(getattr(item, 'get_type')())

        elif hasattr(item, '__type__'):
            return self.__contains__(getattr(item, '__type__'))

        else:
            return False

    @property
    def item(self):
        return self.item_type if self.item_type is not None else AnyType

    @property
    def dimension(self):
        if isinstance(self.item_type, SequenceType) and self.size is not None:
            dim = self.item_type.dimension
            if type(dim) is tuple:
                return (self.size, *dim)
            elif type(dim) is int:
                return self.size, dim
            else:
                return self.size

        elif self.size is not None:
            return self.size

        else:
            return None

#######################################################################################################################

class FunctionType(Type):

    pass


#######################################################################################################################

AnyType  = Type(name='Any')
NullType = Type(name='Null', base=AnyType)

Numeric = Type(name='Numeric', base=AnyType)
Float   = Type(name='Float',   base=Numeric)
Integer = Type(name='Integer', base=Float)
Boolean = Type(name='Boolean', base=Integer)

List   = SequenceType(name='List',   base=AnyType)
Tuple  = SequenceType(name='Tuple',  base=AnyType)
String = SequenceType(name='String', base=AnyType, recursive=True)

#######################################################################################################################

_types = {
    bool: Boolean,
    float: Float,
    int: Integer,
    list: List,
    str: String,
    tuple: Tuple,
}

def from_python(value):
    if value in _types:
        return _types[value]

    t = type(value)
    if t in [list, tuple]:
        item = union(*[from_python(item) for item in value])
        if t is list:
            return List[item][len(value)]

        elif t is tuple:
            return Tuple[item][len(value)]

    elif t in _types:
        return _types[t]

    else:
        return AnyType

def union(*types):
    if len(types) > 0:
        result = types[0]
        for t in types[1:]:
            result = result.union(t)
        return result

    else:
        return AnyType
