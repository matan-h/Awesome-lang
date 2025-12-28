import importlib
import inspect
import functools
from typing import Optional, get_type_hints, get_origin, get_args
from types import FunctionType

from ._convert import python_to_external, pythonic
def positional_arg_limits(sig: inspect.Signature):
    """
    Returns (min_positional, max_positional)

    max_positional is None if *args is present (unbounded)
    """
    min_pos = 0
    max_pos = 0

    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_POSITIONAL:
            return min_pos, None

        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            max_pos += 1
            if p.default is inspect._empty:
                min_pos += 1

    return min_pos, max_pos


def wrap_pyfunc(
    func: FunctionType,
    param_types: Optional[list[str]] = None,
    return_type_str: Optional[str] = None
):
    """
    Wrap a Python function to convert between external types (int, list, function)
    and Python types using external_to_python and python_to_external.
    """

    if param_types is not None and return_type_str is None:
        raise ValueError("If param_types is provided, return_type_str must also be provided")

    # Get function signature
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Parse or get type hints
    if param_types is not None:
        param_type_hints = [parse_type_string(t) for t in param_types]
        param_type_map = {p.name: t for p, t in zip(params, param_type_hints)}
        return_type = parse_type_string(return_type_str)
    else:
        hints = get_type_hints(func)
        param_type_map = {p.name: hints.get(p.name, type(None)) for p in params}
        return_type = hints.get('return', type(None))

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        min_pos, max_pos = positional_arg_limits(sig)
        given = len(args)

        if max_pos is not None and given > max_pos:
            raise TypeError(
                f"{func.__name__} takes {max_pos} positional arguments "
                f"but {given} were given"
            )

        if given < min_pos:
            raise TypeError(
                f"{func.__name__} takes at least {min_pos} positional arguments "
                f"but {given} were given"
            )

        # Bind and apply defaults
        try:
            bound_args = sig.bind(*args, **kwargs)
        except TypeError as e:
            raise TypeError(f"{func.__name__}: {e}") from None
        bound_args.apply_defaults()

        # Convert arguments from external to Python
        converted = {}
        for param_name, value in bound_args.arguments.items():
            target_type = param_type_map.get(param_name)
            if target_type and target_type != type(None):
                converted[param_name] = pythonic(value, target_type,f"{func.__name__}::{param_name}")
            else:
                converted[param_name] = value

        # Call function
        result = func(**converted)

        # Convert return value from Python to external
        if return_type and return_type != type(None):
            result = python_to_external(result, return_type)

        return result

    return wrapper



def parse_type_string(type_str: str):
    """Convert type string to Python type object."""
    if type_str == 'int':
        return int
    elif type_str == 'str':
        return str
    elif type_str == 'float':
        return float
    elif type_str == 'bool':
        return bool

    # Handle list types
    if type_str.startswith('list['):
        inner = type_str[5:-1]  # Remove 'list[' and ']'
        if inner == 'int':
            return list[int]
        elif inner == 'str':
            return list[str]
        elif inner == 'float':
            return list[float]
        elif inner == 'bool':
            return list[bool]
        elif inner.startswith('list['):
            # Nested list
            return list[parse_type_string(inner)]

    return type(None)



# Clean decorator
def convert4(    param_types: Optional[list[str]] = None,
    return_type: Optional[str] = None
):
    """Decorator for functions that will be called from external environment."""
    def decorator(func):
        return wrap_pyfunc(func, param_types, return_type)
    return decorator