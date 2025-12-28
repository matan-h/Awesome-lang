from types import FunctionType
from . import fn

from prebuilt._importpy import wrap_pyfunc,convert4

import importlib
import inspect
from typing import List, Any, Tuple, get_type_hints
from ._convert import external_to_python, python_to_external,pythonic,pythonic

from ._importpy import wrap_pyfunc

@fn("importpy")
@convert4()
def importpy(module_name_list:list[int], function_names_list:list[list[int]]) -> list[FunctionType]:
    """
    Import a Python module from Awesome environment.

    Input: [module_name, [function1, function2, ...]]
    Returns: list of wrapped functions that can be called from Awesome

    In Awesome, module_name is actually list[int] (ASCII)
    """

    # Convert ASCII list to string
    module_name = pythonic(module_name_list,str)
    function_names = pythonic(function_names_list, list[str])


    # Import the module
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Cannot import module '{module_name}': {e}")

    # Wrap and return functions
    wrapped_functions = []
    for func_name in function_names:
        if not hasattr(module, func_name):
            raise AttributeError(f"Module '{module_name}' has no function '{func_name}'")

        func = getattr(module, func_name)

        # Wrap the function for Awesome calling
        wrapped = wrap_pyfunc(func)
        wrapped_functions.append(wrapped)


    return wrapped_functions

@fn("importpyclass")
def importpyclass(
    module_name_list: list,
    class_name_list: list,
    cls_init_args: list,
    cls_methods: list
) -> list:
    """
    Import a Python class, instantiate it, and return a list of wrapped bound methods.

    External inputs:
      - module_name_list: list[int] (ASCII) -> module name string
      - class_name_list: list[int] (ASCII) -> class name string
      - cls_init_args: list of external values (positional constructor args)
                      (each element is in external representation)
      - cls_methods: list[list[int]] (ASCII lists) -> list[str] method names

    Returns:
      - list of wrapped bound methods (callables) that the external environment can call.
    """
    # Convert module/class/method names from ASCII lists to strings
    module_name = external_to_python(module_name_list, str)
    class_name = external_to_python(class_name_list, str)
    method_names = external_to_python(cls_methods, list[str])

    # Import the module and class
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Cannot import module '{module_name}': {e}")

    if not hasattr(module, class_name):
        raise AttributeError(f"Module '{module_name}' has no class '{class_name}'")

    cls = getattr(module, class_name)

    # Prepare constructor signature and type hints (if any)
    try:
        init_sig = inspect.signature(cls.__init__)
        init_params = list(init_sig.parameters.values())
        # Drop 'self' (first parameter) if present
        if init_params and init_params[0].name == 'self':
            init_params = init_params[1:]
    except (ValueError, TypeError):
        # Builtins or unusual objects might not have inspectable signature
        init_params = []

    init_hints = {}
    try:
        # get_type_hints may raise for builtins; swallow that
        init_hints = get_type_hints(cls.__init__)
    except Exception:
        init_hints = {}

    # Convert positional init args using hints if available
    converted_init_args = []
    for i, ext_arg in enumerate(cls_init_args or []):
        if i < len(init_params):
            param = init_params[i]
            target_type = init_hints.get(param.name, None)
            if target_type and target_type is not type(None):
                # use helper to convert from external to Python
                converted = pythonic(ext_arg, target_type)
            else:
                # no hint available — pass raw external value through
                converted = ext_arg
        else:
            # more args provided than annotated parameters: pass raw external value
            converted = ext_arg
        converted_init_args.append(converted)

    # Instantiate the class
    try:
        print(f"Instantiating {class_name} from {module_name} with args {converted_init_args}")
        instance = cls(*converted_init_args)
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate {class_name} from {module_name}: {e}")


    # For each requested method, fetch bound method and wrap it
    wrapped_methods = []
    for mname in method_names:
        if not hasattr(instance, mname):
            raise AttributeError(f"Instance of '{class_name}' has no method '{mname}'")
        bound_method = getattr(instance, mname)
        if not callable(bound_method):
            raise TypeError(f"Attribute '{mname}' of '{class_name}' is not callable")

        # wrap the bound method so external callers can call it
        wrapped = wrap_pyfunc(bound_method)
        wrapped_methods.append(wrapped)

    return wrapped_methods


# Helper functions for direct use in Python (not from Awesome)
def import_py(module_name: str, functions: List[str]) -> List[Any]:
    """Python-side helper for importing modules."""
    return importpy([ord(c) for c in module_name],
                    [[ord(c) for c in f] for f in functions])





# Example usage from Python (for testing):
if __name__ == "__main__":
    # Example 1: Import random module functions
    random_funcs = import_py("random", ["randint", "randrange", "choice"])
    randint_func, randrange_func, choice_func = random_funcs

    # These functions are already wrapped for Awesome calling
    # From Awesome, you would call: [1, 10](randint) %>()?
    print(f"Random int between 1-10: {randint_func(1, 10)}")

    # Example 2: Import a class
    import math

    # Create a custom class for demonstration
    class Calculator:
        def __init__(self, precision: int = 2):
            self.precision = precision

        def add(self, a: int, b: int) -> int:
            return round(a + b, self.precision)

        def multiply(self, a: int, b: int) -> int:
            return round(a * b, self.precision)

    # Simulate importing this class from Awesome
    # Note: In real Awesome, Calculator would be in a module
    calc_methods = importpyclass(
        "__main__",  # Current module
        "Calculator",
        [2],  # init_args: precision=2
        ["add", "multiply"]
    )

    add_func, multiply_func = calc_methods
    print(f"Add with precision 2: {add_func(3, 2)}")  # Should be 5.86
    print(f"Multiply with precision 2: {multiply_func(3, 2)}")  # Should be 6.28