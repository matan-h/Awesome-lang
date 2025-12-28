from types import FunctionType
from typing import Type, get_origin, get_args,TypeVar

T = TypeVar('T')

def external_to_python(value, target_type:Type[T])->T:
    """
    Convert a value from the restricted external representation
    into a Python value of target_type.

    External space supports only:
      - int
      - list
      - function (not handled here)
    """
    origin = get_origin(target_type)
    args = get_args(target_type)

    # ---------- str ----------
    # list[int] -> str (ASCII)
    if target_type is str:
        if not isinstance(value, list) or not all(isinstance(x, int) for x in value):
            raise TypeError(f"Expected list[int] for str. instead we got {type(value)}")
        return ''.join(chr(x) for x in value)

    # ---------- int ----------
    if target_type is int:
        if not isinstance(value, int):
            raise TypeError("Expected int")
        return value

    # ---------- bool ----------
    if target_type is bool:
        if not isinstance(value, int):
            raise TypeError("Expected int for bool")
        return bool(value)

    # ---------- float ----------
    # [[digits], decimal_pos] -> float
    if target_type is float:
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not isinstance(value[0], list)
            or not isinstance(value[1], int)
        ):
            raise TypeError("Expected [[digits], decimal_pos] for float")

        digits, decimal_pos = value
        if not all(isinstance(d, int) for d in digits):
            raise TypeError("Digits must be int")

        if not digits:
            return 0.0

        if decimal_pos < 0:
            decimal_pos = len(digits) + decimal_pos
        if not (0 <= decimal_pos <= len(digits)):
            raise ValueError("Invalid decimal position")

        s = ''.join(str(d) for d in digits)
        if decimal_pos == 0:
            return float(f"0.{s}")
        if decimal_pos == len(digits):
            return float(s)
        return float(f"{s[:decimal_pos]}.{s[decimal_pos:]}")

    # ---------- list[T] ----------
    if origin is list and args:
        if not isinstance(value, list):
            raise TypeError("Expected list")
        inner = args[0]
        return [external_to_python(v, inner) for v in value]

    raise TypeError(f"Unsupported target type: {target_type}")


def python_to_external(value, target_type):
    """
    Convert a Python value into its restricted external representation.
    """
    origin = get_origin(target_type)
    args = get_args(target_type)

    # ---------- str ----------
    # str -> list[int]
    if target_type is str:
        if not isinstance(value, str):
            raise TypeError("Expected str")
        return [ord(c) for c in value]

    # ---------- int ----------
    if target_type is int:
        if not isinstance(value, int):
            raise TypeError("Expected int")
        return value
    if target_type is FunctionType:
        if not isinstance(value, FunctionType):
            raise TypeError("Expected function")
        return value

    # ---------- bool ----------
    if target_type is bool:
        if not isinstance(value, bool):
            raise TypeError("Expected bool")
        return 1 if value else 0

    # ---------- float ----------
    # float -> [[digits], decimal_pos]
    if target_type is float:
        if not isinstance(value, (int, float)):
            raise TypeError("Expected float")

        if value == 0:
            return [[], 0]

        s = format(float(value), 'f').rstrip('0').rstrip('.')
        if '.' in s:
            decimal_pos = s.index('.')
        else:
            decimal_pos = len(s)

        digits = [int(c) for c in s if c.isdigit()]
        return [digits, decimal_pos]

    # ---------- list[T] ----------
    if origin is list and args:
        if not isinstance(value, list):
            raise TypeError("Expected list")
        inner = args[0]
        return [python_to_external(v, inner) for v in value]

    if origin is tuple and args:
        if not isinstance(value, tuple):
            raise TypeError("Expected tuple")
        l = []
        for i, inner in enumerate(args):
            v = value[i]
            l.append(python_to_external(v, inner))
        return list(l)


    raise TypeError(f"Unsupported target type: {target_type} (origin={origin}, args={args})")

pythonic = external_to_python
ext = python_to_external