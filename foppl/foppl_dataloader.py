#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 24. Jan 2018, Tobias Kohn
# 24. Jan 2018, Tobias Kohn
#
import os.path

def load_from_source(source: str):
    """
    Loads the data from the specified source and returns either a plain Python-list or `None`.
    :param source:  The name of the source, such as a file name.
    :return:        Either a Python `list` or `None`.
    """
    if os.path.exists(source):
        with open(source) as source_file:
            result = []
            for line in source_file.readlines():
                values = parse_line(line)
                if values is not None:
                    result.append(values)
            return result
    return None


def find_path(source):
    possible_locations = [
        '',
        'foppl-src/',
        'foppl_src/',
        'foppl-models/',
        'foppl_models/',
        'models',
        'examples/'
    ]
    for ext in ['.dat', '.csv', '.idx1-ubyte', '.idx3-ubyte']:
        for loc in possible_locations:
            name = loc + source + ext
            if os.path.exists(name):
                return name
    return None


def parse_line(line):

    def _is_int(s):
        if len(s) > 0 and s[0] in ['+', '-']:
            return _is_int(s[1:])
        else:
            return all(['0' <= c <= '9' for c in s])

    result = []
    i = 0
    while i < len(line):
        if '0' <= line[i] <= '9' or line[i] in ['+', '-', '.']:
            value = ''
            while i < len(line) and line[i] > ' ' and line[i] not in [',', ';']:
                value += line[i]
                i += 1
            value = value.lower()
            try:
                if value in ['true', 'false']:
                    result.append(int(value == 'true'))
                elif _is_int(value):
                    result.append(int(value))
                else:
                    result.append(float(value))
            except ValueError:
                result.append(None)
        else:
            i += 1

    if len(result) == 1:
        return result[0]
    else:
        return result
