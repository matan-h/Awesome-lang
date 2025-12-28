from types import FunctionType,SimpleNamespace

builtin_funcs:dict[str,FunctionType] = {}
builtin_vars = SimpleNamespace()

def fn(name:str):
    def decorator(func:FunctionType) -> FunctionType:
        builtin_funcs[name] = func
        return func
    return decorator

