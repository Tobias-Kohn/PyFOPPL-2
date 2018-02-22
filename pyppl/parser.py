#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 22. Feb 2018, Tobias Kohn
#
from . import ppl_foppl_parser, ppl_python_parser, ppl_optimizers

def _detect_language(s:str):
    for char in s:
        if char in ['#']:
            return 'py'

        elif char in [';', '(']:
            return 'clj'

        elif 'A' <= char <= 'Z' or 'a' <= char <= 'z' or char == '_':
            return 'py'

        elif char > ' ':
            return 'py'

    return None

def parse(source:str, optimize:bool=True):
    result = None
    if type(source) is str and str != '':
        lang = _detect_language(source)
        if lang == 'py':
            result = ppl_python_parser.parse(source)

        elif lang == 'clj':
            result = ppl_foppl_parser.parse(source)

    if optimize and result is not None:
        opt = ppl_optimizers.Optimizer()
        result = opt.visit(result)

    return result
