from lark import Lark, Tree, Token
from dataclasses import dataclass
from typing import List, Any

# --- Grammar ---
ALL_GRAMMAR = r"""
    ?start: (function_def | main_statement)+

    function_def: "(" NAME ")" NAME body NAME "()"
    body: (statement)*

    ?main_statement: assignment | print_query | expression "?" -> direct_print

    assignment: expression "%> () ->" NAME
    print_query: expression "[]>" NAME "?"

    ?expression: addition
    ?addition: term ( "+" term )*

    ?term: list_literal
         | generator_literal
         | NUMBER -> lit
         | NAME   -> var

    list_literal: "[" [NUMBER ("," NUMBER)*] "]"
    generator_literal: "[" NAME ",.." "]"

    ?statement: extract_to_var
              | expression

    extract_to_var: NUMBER "[]>" NAME "->" NAME

    %import common.CNAME -> NAME
    %import common.SIGNED_NUMBER -> NUMBER
    %import common.WS
    %ignore WS
    COMMENT: /#[^\n]*/
    %ignore COMMENT
"""

@dataclass
class Generator:
    seed: List[int]
    func_name: str

class AwesomeInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}

    def run(self, tree):
        for child in tree.children:
            if child.data == 'function_def':
                arg_name, func_name, body, _ = child.children
                self.functions[str(func_name)] = (str(arg_name), body)
            elif child.data == 'assignment':
                expr, var_name = child.children
                self.variables[str(var_name)] = self.evaluate(expr)
            elif child.data == 'print_query':
                idx_expr, var_name = child.children
                idx = int(self.evaluate(idx_expr))
                data = self.variables.get(str(var_name))
                if isinstance(data, Generator):
                    data = self._expand_generator(data, idx)
                    self.variables[str(var_name)] = data
                print(data[idx])
            elif child.data == 'direct_print':
                print(self.evaluate(child.children[0]))

    def evaluate(self, node, env=None):
        if env is None: env = self.variables

        # 1. Handle Tokens (Raw values/strings from Lexer)
        if isinstance(node, Token):
            if node.type == 'NUMBER': return int(node)
            return str(node)

        # 2. Handle Recursive Tree Nodes
        if not hasattr(node, 'data'): return node

        if node.data == 'lit':
            return int(node.children[0])
        elif node.data == 'var':
            var_name = str(node.children[0])
            return env.get(var_name, self.variables.get(var_name, 0))
        elif node.data == 'list_literal':
            # Children are already tokens of numbers
            return [int(c) for c in node.children]
        elif node.data == 'generator_literal':
            return Generator(seed=[], func_name=str(node.children[0]))
        elif node.data == 'addition':
            items = [self.evaluate(c, env) for c in node.children]
            res = items[0]
            for other in items[1:]:
                if isinstance(res, list) and isinstance(other, Generator):
                    other.seed = res
                    return other
                res = res + other
            return res
        return None

    def _expand_generator(self, gen: Generator, target_idx: int) -> List[int]:
        seq = list(gen.seed)
        arg_name, body_tree = self.functions[gen.func_name]

        while len(seq) <= target_idx:
            local_env = {arg_name: seq}
            step_result = None
            for stmt in body_tree.children:
                if stmt.data == 'extract_to_var':
                    # Extract values: -1 []> array -> a
                    idx = int(self.evaluate(stmt.children[0], local_env))
                    src = str(stmt.children[1])
                    target = str(stmt.children[2])
                    # Lookup src in local_env (the array)
                    source_list = local_env.get(src, [])
                    local_env[target] = source_list[idx]
                    step_result = local_env[target]
                else:
                    step_result = self.evaluate(stmt, local_env)
            seq.append(step_result)
        return seq

# --- Execution ---
script = """
(array) fib
    # return last + second last
    -1 []> array -> a
    -2 []> array -> b
    a + b
fib ()
[0,1] + [fib,..] %> () -> fibs

10 []> fibs?
"""

parser = Lark(ALL_GRAMMAR, parser='earley')
tree = parser.parse(script)
interpreter = AwesomeInterpreter()
interpreter.run(tree)