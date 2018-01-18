#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 17. Jan 2018, Tobias Kohn
# 18. Jan 2018, Tobias Kohn
#
from .code_types import *

class DistributionTypes(object):

    @classmethod
    def __cont_dist__(cls, args: list, index: int):
        arg = args[index]
        if isinstance(arg, SequenceType):
            return ListType(FloatType, arg.size)
        else:
            return FloatType()

    @classmethod
    def categorical(cls, args: list):
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, SequenceType):
                return arg.item_type
        raise TypeError("wrong number or type of arguments for 'categorical': {}".format(len(args)))

    @classmethod
    def gamma(cls, args: list):
        if len(args) == 2:
            return cls.__cont_dist__(args, 0)
        else:
            raise TypeError("wrong number of arguments for 'gamma': {}".format(len(args)))

    @classmethod
    def normal(cls, args: list):
        if len(args) == 2:
            return cls.__cont_dist__(args, 0)
        else:
            raise TypeError("wrong number of arguments for 'normal': {}".format(len(args)))


def get_result_type(name: str, args: list):
    if hasattr(DistributionTypes, name.lower()):
        method = getattr(DistributionTypes, name.lower())
        return method(args)
    return AnyType()
