#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Jan 2018, Tobias Kohn
# 31. Jan 2018, Tobias Kohn
#
import math as _math
import random as _random
####################################################################################################

class dist(object):
    """
    This class is aRefactored distributions. namespace with "stand-in" distributions for testing purposes. They are explicitly not
    meant to be used for actual sampling and evaluation. However, using these test-distributions allows us
    to test the frontend/compiler without the sophisticated backend doing actual inference.
    """

    class Dummy(object):

        def __init__(self, *args, **kwargs):
            pass

        def log_pdf(self, value):
            return 0

        log_prob = log_pdf

        def sample(self):
            return 1

    Binomial = Dummy
    Dirichlet = Dummy
    LogGamma = Dummy
    MultivariateNormal = Dummy
    Poisson = Dummy

    class Categorical(object):

        def __init__(self, ps, **args):
            if type(ps) is list:
                self.ps = ps
            else:
                self.ps = [ps]

        def log_pdf(self, value):
            if type(value) is int and 0 <= value < len(self.ps):
                return _math.log(self.ps[value])
            else:
                return 1

        log_prob = log_pdf

        def sample(self):
            return _random.randint(0, len(self.ps)-1)

    class Gamma(object):

        def __init__(self, *arg, transformed:bool=None, **args):
            pass

        def log_pdf(self, value):
            return 0

        log_prob = log_pdf

        def sample(self):
            return 1

    class Normal(object):

        def __init__(self, loc, **args):
            self.mu = loc
            self.sigma = 1.0

        def log_pdf(self, value):
            return -1/2 * (((value - self.mu)**2 / self.sigma) + _math.log(2 * _math.pi * self.sigma))

        log_prob = log_pdf

        def sample(self):
            return _random.gauss(self.mu, self.sigma)


