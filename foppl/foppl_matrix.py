#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Jan 2018, Tobias Kohn
# 22. Jan 2018, Tobias Kohn
#
from .code_objects import *

def _is_vector(item):
    return isinstance(item, CodeVector) or (isinstance(item, CodeValue) and type(item.value) is list)

def _are_vectors(items):
    return all([_is_vector(item) for item in items])

def add(items):
    if _are_vectors(items):
        pass
    else:
        raise TypeError("Applicable ")