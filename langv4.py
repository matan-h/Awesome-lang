import sys
import os
import itertools
from lark import Lark, Tree, Token
from typing import Any, List, Dict, Generator

import prebuilt
# --- The Grammar ---
# Simplified to enforce flat precedence and block structures
GRAMMAR = r"""
    start: (statement | separator)*

    separator: NEWLINE | ":"

    ?statement: func_def
              | loop_block
              | conditional
              | codeblock_def
              | codeblock_run
              | assignment
              | print_stmt
              | expression

    # --- Structures ---
    func_def: "(" NAME ")" block NAME "()"
    loop_block: "loop" NAME "&" expression block "pool" [NAME]
    conditional: expression "?%>" statement
    block: (statement | separator)*

    # --- Macros ---
    # Matches #name{...} or #name@{...}
    codeblock_def: "#" NAME ["@"] "{" block "}"
    codeblock_run: "#" NAME "#"

    # --- Assignment & IO ---
    assignment: expression "->" atom
# Change the print_stmt rules to use a named terminal
print_stmt: expression Q_MARKS -> print_op
          | "@" Q_MARKS        -> print_newline

# Define the terminal at the bottom
Q_MARKS: "?"+
    # --- Expressions (Left-to-Right Flat Structure) ---
    expression: term (OP term | apply_op)*

    apply_op: "%>" "()"

    ?term: list_literal
         | generator
         | string
         | atom
         | infinity
         | "(" expression ")"

    atom: NUMBER -> number_lit
        | NAME   -> variable

    # --- Lists & Generators ---
    list_literal: "[" [expression ("," expression)*] "]"

    # !generator: "[" [expression ("," expression)* ","] NAME "," ".." "]" -> gen_func
    #           | "[" expression "," expression "," ".." "]"            -> gen_arithmetic
    #           | "[" expression "," ".." "]"                         -> gen_const
    ?generator: "[" (expression ",")* NAME "," ".." "]" -> gen_func
          | "[" expression "," expression "," ".." "]" -> gen_arithmetic
          | "[" expression "," ".." "]"                -> gen_const

    string: ESCAPED_STRING
    infinity: "~" NUMBER

    OP: "+" | "-" | "*" | "/" | "[]>" | "&" | "=="

    %import common.CNAME -> NAME
    %import common.SIGNED_NUMBER -> NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %import common.NEWLINE
    %ignore WS
    %ignore /#[^\n{].*/  // Simple comments
"""

class LazyList:
    """A wrapper for generators that caches results for random access."""
    def __init__(self, gen: Generator):
        self.gen = gen
        self.cache = []
        self.is_infinite = True

    def __getitem__(self, index):
        if index < 0: return 0 # Awesome logic
        while len(self.cache) <= index:
            try:
                self.cache.append(next(self.gen))
            except StopIteration:
                self.is_infinite = False
                return 0 # Out of bounds default
        return self.cache[index]

    def __iter__(self):
        # Yield cached items then continue generator
        yield from self.cache
        for item in self.gen:
            self.cache.append(item)
            yield item

    def __len__(self):
        # Only works if fully realized, otherwise we lie
        return len(self.cache)

    def __repr__(self):
        preview = ",".join(map(str, self.cache[:3]))
        return f"[{preview}{',..' if self.is_infinite else ''}]"

class AwesomeInterpreter:
    def __init__(self):
        self.vars = {}
        self.funcs = {}
        self.macros = {}
        # Mutable numbers: Maps the string "2" to the value 5, etc.
        self.literal_patches = {}
        self.should_break = False
        self.current_node = None # Track the node being executed


    # --- Core Helpers ---
    def get_val(self, node):
        """Resolves atoms, numbers, strings to Python primitives/LazyLists."""
        if isinstance(node, Token):
            if node.type == 'NUMBER':
                # Mutable Number Logic
                return self.literal_patches.get(node.value, int(node.value))
            if node.type == 'ESCAPED_STRING':
                return [ord(c) for c in node.value[1:-1]]
        return node

    def get_infinities(self, code):
        """Resolves specific ~N infinities."""
        code = int(code)
        mapping = {
            8: float('inf'),
            0: 0, # The void
            1: -1,
            3: os.getpid(),
            7: sys.maxsize, # Crypto/Arch infinity
            2: 10**22 # Approx stars
        }
        return mapping.get(code, float('inf'))

    # --- Execution Loop ---
    def run(self, node):
        self.current_node = node
        if self.should_break: return

        # Handle list of statements
        children = node.children if isinstance(node, Tree) else [node]

        for child in children:
            if self.should_break: break
            if isinstance(child, Token): continue

            op = child.data
            if op == 'assignment':
                val = self.eval_expr(child.children[0])
                target = child.children[1]
                if target.data == 'number_lit':
                    # x -> 2 (Modify what "2" means)
                    lit_key = target.children[0].value
                    self.literal_patches[lit_key] = val
                else:
                    # x -> a (Standard variable)
                    var_name = target.children[0].value
                    self.vars[var_name] = val

            elif op == 'expression':
                self.eval_expr(child)

            elif op == 'print_op':
                val = self.eval_expr(child.children[0])
                count = len(child.children[1]) # Number of '?'
                # Logic for ??, ??? can be expanded here.
                # ? = print result.
                print(f">> {val}" if count > 1 else val)

            elif op == 'print_newline':
                print()

            elif op == 'loop_block':
                var_name = child.children[0].value
                iterable = self.eval_expr(child.children[1])
                body = child.children[2]

                # Handle Python list or LazyList
                iterator = iter(iterable) if hasattr(iterable, '__iter__') else []

                for item in iterator:
                    self.vars[var_name] = item
                    self.run(body)
                    if self.should_break:
                        self.should_break = False
                        break

            elif op == 'conditional':
                # expr ?%> stmt
                val = self.eval_expr(child.children[0])
                # Truthiness: Non-zero number or non-empty list
                is_true = (isinstance(val, int) and val != 0) or (isinstance(val, list) and len(val) > 0)
                if is_true:
                    stmt = child.children[1]
                    # Check for "pool" keyword acting as break
                    if isinstance(stmt, Token) and stmt.type == 'POOL':
                        self.should_break = True
                    else:
                        self.run(stmt)

            elif op == 'func_def':
                arg_name = child.children[0].value
                body = child.children[1]
                func_name = child.children[2].value
                self.funcs[func_name] = (arg_name, body)

            elif op == 'codeblock_def':
                name = child.children[0].value
                is_delayed = child.children[1] == "@" # Optional '@' token logic
                body = child.children[-1]
                self.macros[name] = body
                # If not delayed (no @), run immediately per spec
                if not is_delayed:
                    self.run(body)

            elif op == 'codeblock_run':
                name = child.children[0].value
                if name in self.macros:
                    self.run(self.macros[name])

    # --- Expression Evaluator (Left-to-Right) ---
    def eval_expr(self, node):
        if not isinstance(node, Tree): return self.get_val(node)

        # Base terms
        if node.data == 'number_lit': return self.get_val(node.children[0])
        if node.data == 'variable':   return self.vars.get(node.children[0].value, 0)
        if node.data == 'string':     return self.get_val(node.children[0])
        if node.data == 'infinity':   return self.get_infinities(node.children[0].value)
        if node.data == 'list_literal': return [self.eval_expr(c) for c in node.children]

        # Infinite Generators
        if node.data == 'gen_arithmetic':
            start = self.eval_expr(node.children[0])
            second = self.eval_expr(node.children[1])
            step = second - start
            return LazyList(itertools.count(start, step))
        if node.data == 'gen_const':
            val = self.eval_expr(node.children[0])
            return LazyList(itertools.repeat(val))
        if node.data == 'gen_func':
            # children[-1] is the NAME of the function
            # children[:-1] are the seed values
            func_name = node.children[-1].value
            seed_nodes = node.children[:-1]
            seeds = [self.eval_expr(s) for s in seed_nodes]

            def func_gen():
                acc = list(seeds)
                # First, yield the seeds
                for s in seeds:
                    yield s
                # Then, start calling the function to generate new elements
                while True:
                    # Pass the current state of the list to the generator function
                    val = self.call_func(func_name, list(acc))
                    acc.append(val)
                    yield val

            return LazyList(func_gen())

        # The Expression Chain: term (OP term)*
        if node.data == 'expression':
            # 1. Get the starting value
            left = self.eval_expr(node.children[0])

            i = 1
            while i < len(node.children):
                current_node = node.children[i]

                # --- CASE A: Function Application (Tree) ---
                # Check if it's a Tree before looking for .data
                if isinstance(current_node, Tree) and current_node.data == 'apply_op':
                    if isinstance(left, tuple) and len(left) == 2:
                        left = self.call_func(left[0], left[1])
                    elif isinstance(left, str):
                        left = self.call_func(left, [])
                    i += 1
                    continue

                # --- CASE B: Regular Operator (Token) ---
                # This handles '+', '-', '[]>', etc.
                op = str(current_node)
                right = self.eval_expr(node.children[i+1])

                if op == "+":   left = self.add(left, right)
                elif op == "-": left = self.sub(left, right)
                elif op == "*": left = self.mul(left, right)
                elif op == "/": left = (left // right) if right != 0 else 0
                elif op == "==": left = 1 if left == right else 0
                elif op == "[]>": left = self.get_index(left, right)

                i += 2
            return left
    def execute_block(self, node):
        """Executes a list of statements and returns the value of the last expression."""
        last_val = 0
        children = node.children if isinstance(node, Tree) else [node]

        for child in children:
            if self.should_break: break
            if isinstance(child, Token): continue

            op = child.data
            # Handle all statement types
            if op == 'print_op':
                last_val = self.eval_expr(child.children[0])
                print(last_val) # Simplified print logic

            elif op == 'assignment':
                last_val = self.eval_expr(child.children[0])
                target = child.children[1]
                name = target.children[0].value
                if target.data == 'number_lit':
                    self.literal_patches[name] = last_val
                else:
                    self.vars[name] = last_val

            elif op == 'expression':
                last_val = self.eval_expr(child)

            elif op == 'conditional':
                cond = self.eval_expr(child.children[0])
                if cond: # Awesome truthy logic
                    stmt = child.children[1]
                    if isinstance(stmt, Token) and stmt.type == 'POOL':
                        self.should_break = True
                    else:
                        self.execute_block(stmt)

            elif op in ('loop_block', 'func_def', 'codeblock_def', 'codeblock_run'):
                # Route these back through the main run logic
                self.run(child)

        return last_val

    def call_func(self, name:str, args:list):
        if name in prebuilt.builtin_funcs:
            # TODO: check signature, and print error
            return prebuilt.builtin_funcs[name](*args)

        if name not in self.funcs:
            self.error(f"Function '{name}' not defined.",NameError)
        arg_var, body = self.funcs[name]

        # Scope Management
        prev = self.vars.get(arg_var)
        self.vars[arg_var] = args

        # Now 8? will work because execute_block handles print_op!
        ret = self.execute_block(body)

        if prev is not None: self.vars[arg_var] = prev
        else: self.vars.pop(arg_var, None)
        return ret


    # --- Polymorphic Math Helpers ---
    def add(self, a, b):
        if isinstance(a, list) and isinstance(b, list): return a + b
        return a + b

    def sub(self, a, b):
        # String subtraction "Asuf" - "suf" -> "A" (simplified as list removal?)
        # Spec implies normal math mostly.
        return a - b

    def mul(self, a, b):
        # [1,2] * [3,4] -> [3, 8] (Zip mult? Spec says [1,2,3]*[4,5,6] -> [4,10,18])
        if isinstance(a, list) and isinstance(b, list):
            return [x*y for x,y in zip(a,b)]
        # "A" * 3 -> [65,65,65]
        if isinstance(a, list) and isinstance(b, int):
            return a * b
        return a * b

    def get_index(self, left, right):
        """Handles the 'index []> list' operation."""
        idx = int(left)
        # If it's a LazyList, use its custom __getitem__ (which handles infinite caching)
        if isinstance(right, (LazyList, list)):
            # Awesome logic: index 0 is start, out of bounds is 0
            try:
                return right[idx]
            except (IndexError, TypeError):
                return 0
        return 0

    @property
    def line(self):
        """Returns the current line number being executed."""
        if self.current_node and hasattr(self.current_node, 'meta'):
            return self.current_node.meta.line
        return "unknown"


    def error(self, message,cls=NameError):
        # meta.line is available because of propagate_positions=True

        # Format the Awesome Error
        raise cls(f"[Line {self.line}] Awesome Error: {message}")

# --- Running ---

def run_awesome(code):
    # Pre-process: Logic for [args](func) needs to be parsed as an expression.
    # The grammar ?term: "(" expression ")" handles grouping.
    # We need a rule for function prep: list_literal "(" NAME ")"
    # We add this dynamically to grammar or just treat it as term adjacency?
    # To keep it "Much simpler", we treat function prep as a specific expression pattern.
    # We added `term` rule, let's just use the interpreter logic to detect tuple return.

    # Note on (name) syntax in grammar:
    # term: "(" expression ")" is standard grouping.
    # We need: list_literal "(" NAME ")" -> func_prep
    # Let's adjust grammar slightly in `term` for this specific feature if needed,
    # or rely on the user writing `[args] (name)` which parses as two terms?
    # No, `(name)` parses as expression grouping.
    # Let's add specific rule to term:

    extended_grammar = GRAMMAR.replace(
        "?term: list_literal",
        "?term: list_literal \"(\" NAME \")\" -> func_prep \n         | list_literal"
    )

    parser = Lark(extended_grammar, start='start', parser='earley',propagate_positions=True)
    interpreter = AwesomeInterpreter()

    # Patch the evaluator to handle func_prep
    original_eval = interpreter.eval_expr
    def patched_eval(node):
        if isinstance(node, Tree) and node.data == 'func_prep':
            args = interpreter.eval_expr(node.children[0])
            name = node.children[1].value
            return (name, args) # Return tuple for apply_op to catch
        return original_eval(node)
    interpreter.eval_expr = patched_eval

    try:
        tree = parser.parse(code)
        # print(tree.pretty());return
        interpreter.run(tree)
    except Exception as e:
        print(f"Awesome Error: {e}")
        raise

# --- Test Script ---


if __name__ == "__main__":
    import sys
    run_awesome(open(sys.argv[1]).read())