
from ._utils import fn,builtin_funcs,builtin_vars
import sys

from .importpy import convert4,pythonic,python_to_external

from . import system,inf,errors

# system
@fn("print")
@convert4()
def builtin_print(inp: str) -> None:
    print(inp)
    return None

@fn("uppercase")
def builtin_uppercase(s: list[int]) -> list[int]:
    # print("uppercase:", chr(s[0]), "->", chr(s[0]).upper())
    return [ord(chr(c).upper()) for c in s]

# math

def pi_digits():
    """
    Generator that yields the digits of π one at a time using using a spigot algorithm.
    First yield is '3', then '.', then digits.
    """
    q, r, t, k, n, l = 1, 0, 1, 1, 3, 3

    yield '3'
    yield '.'

    while True:
        if 4*q + r - t < n*t:
            yield n
            r = 10 * (r - n*t)
            n = (10 * (3*q + r)) // t - 10*n
            q *= 10
        else:
            r = (2*q + r) * l
            n = (q * (7*k) + 2 + r) // (t * l)
            q *= k
            t *= l
            l += 2
            k += 1

builtin_vars.pi = pi_digits()

builtin_vars.args = python_to_external(sys.argv[1:],list[str])