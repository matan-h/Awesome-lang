from types import FunctionType,SimpleNamespace
class NS(SimpleNamespace):
    def set(self, name:str, value):
        setattr(self, name, value)
    def to_dict(self):
        return self.__dict__

builtin_funcs:dict[str,FunctionType] = {}
builtin_vars = NS()

def fn(name:str):
    def decorator(func:FunctionType) -> FunctionType:
        builtin_funcs[name] = func
        return func
    return decorator

