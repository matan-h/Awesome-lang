import sys
import os
import itertools
from types import FunctionType
from lark import Lark, Tree, Token
from typing import Any, List, Dict, Generator

import prebuilt
# --- The Grammar ---
# Rule: uppercase are named, lowercase are anonymous
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
              | func_call_stmt

    func_def: "(" NAME ")" block NAME "()"
    loop_block: "loop" NAME "&" simple_expression block "pool" [NAME]
    conditional: simple_expression "?%>" statement
    block: (statement | separator)*

    codeblock_def: "#" NAME ["@"] "{" block "}"
    codeblock_run: "#" NAME "#"

    assignment: complete_expression "->" ASSIGN_TARGET -> assignment
    ASSIGN_TARGET: /[^\s?]+/

    print_stmt: complete_expression "?"+ -> print_op
              | "@" "?"+                 -> print_newline

    func_call_stmt: complete_expression -> expr_stmt

    complete_expression: func_call
                       | simple_expression

    func_call: list_literal "(" NAME ")" "%>" "()" -> func_call
             | list_literal "(" NAME ")"           -> func_prep

    ?simple_expression: term ((OP | OP_WS) term)*

    ?term: list_literal
         | generator
         | string
         | REV_STRING
         | atom
         | infinity
         | "(" complete_expression ")"

    atom: NUMBER -> number_lit
        | NAME   -> variable

    list_literal: "[" [complete_expression ("," complete_expression)*] "]"

    ?generator: "[" (complete_expression ",")* NAME "," ".." "]" -> gen_func
              | "[" complete_expression "," complete_expression "," ".." "]" -> gen_arithmetic
              | "[" complete_expression "," ".." "]" -> gen_const

    string: ESCAPED_STRING

REV_STRING: /'[^']*'/
        # rev_string: "'" revchar* "'"
    # revchar: /[^']/


    infinity: "~" NUMBER

    NUMBER: /-?\d+/

    # OP_WS: operator that is followed by whitespace in the source (user signaled precedence)
    OP_WS: /(\+|-|\*|\/|\[\]>|&|==)(?=\s)/

    # OP: operator that is NOT followed by whitespace (default left-to-right)
    OP: /(\+|-|\*|\/|\[\]>|&|==)(?=\S)/

    NAME: /[^\s\[\]\(\)\{\},:"@%#?>]+/


    %import common.CNAME
    %import common.SIGNED_NUMBER
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
            elif node.type == 'ESCAPED_STRING':
                return [ord(c) for c in node.value[1:-1]]
            elif node.type == 'REV_STRING':
                return [ord(c) for c in node.value[1:-1]][::-1]
            else:
                self.error(f"Unknown token type for get_val: {node.type} {node}", RuntimeError)
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

            # Handle expr_stmt - function calls or expressions as statements
            if op == 'expr_stmt':
                self.eval_expr(child.children[0])

            elif op == 'assignment':
                val = self.eval_expr(child.children[0])
                target = child.children[1]
                # Check if target is a number literal string
                if target.value.isdigit():
                    # x -> 2 (Modify what "2" means)
                    lit_key = target.value
                    self.literal_patches[lit_key] = val
                else:
                    # x -> a (Standard variable)
                    var_name = target.value
                    self.vars[var_name] = val


            elif op == 'print_op':
                val = self.eval_expr(child.children[0])
                # Count is now the number of '?' tokens after the expression
                count = len([c for c in child.children if isinstance(c, Token) and c.type == 'QMARK'])
                # Logic for ??, ??? can be expanded here.
                # ? = print result.
                print(f">> {val}" if count > 1 else val)

            elif op == 'print_newline':
                count = len([c for c in child.children if isinstance(c, Token) and c.type == 'QMARK'])
                for _ in range(count):
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
                # Check for '@' token
                is_delayed = len(child.children) > 2 and child.children[1] == "@"
                body = child.children[-1]
                self.macros[name] = body
                # If not delayed (no @), run immediately per spec
                if not is_delayed:
                    self.run(body)

            elif op == 'codeblock_run':
                name = child.children[0].value
                if name in self.macros:
                    self.run(self.macros[name])
            elif op in ["separator","start"]:
                # Ignore separators at this level
                pass
            else:
                self.error(f"Unknown statement type: {op}", RuntimeError)


    # --- Expression Evaluator (Left-to-Right) ---
    def eval_expr(self, node):
        self.current_node = node

        if not isinstance(node, Tree):
            return self.get_val(node)

        # Base terms
        elif node.data == 'number_lit':
            return self.get_val(node.children[0])
        elif node.data == 'variable':
            return self.vars.get(node.children[0].value, 0)
        elif node.data == 'string':
            return self.get_val(node.children[0])
        elif node.data == 'rev_string':
            return self.get_val(node.children[0])

        elif node.data == 'infinity':
            return self.get_infinities(node.children[0].value)
        elif node.data == 'list_literal':
            return [self.eval_expr(c) for c in node.children]

        # Handle complete_expression - just evaluate its child
        elif node.data == 'complete_expression':
            return self.eval_expr(node.children[0])

        # Handle simple_expression - the old expression without apply_op
        elif node.data == 'simple_expression':
            return self.eval_simple_expression(node)

        # Handle function calls
        elif node.data == 'func_call':
            # Evaluate the list literal to get arguments
            args = self.eval_expr(node.children[0])
            func_name = node.children[1].value
            # Call the function immediately
            return self.call_func(func_name, args)

        elif node.data == 'func_prep':
            # Prepare function for later application
            args = self.eval_expr(node.children[0])
            func_name = node.children[1].value
            # Return a tuple that can be called later
            return (func_name, args)

        # Infinite Generators
        elif node.data == 'gen_arithmetic':
            start = self.eval_expr(node.children[0])
            second = self.eval_expr(node.children[1])
            step = second - start
            return LazyList(itertools.count(start, step))

        elif node.data == 'gen_const':
            val = self.eval_expr(node.children[0])
            return LazyList(itertools.repeat(val))

        elif node.data == 'gen_func':
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
        else:
            self.error(f"Unknown expression type: {node.data}", RuntimeError)

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
                name = target.value
                if name.isdigit():
                    self.literal_patches[name] = last_val
                else:
                    self.vars[name] = last_val

            elif op == 'expr_stmt':
                last_val = self.eval_expr(child.children[0])

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

    def call_funcType(self,fn,args:list):
        # TODO: verify types
        return fn(*args)



    def call_func(self, name:str, args:list):
        if name in prebuilt.builtin_funcs:
            # print(  f"Calling prebuilt function: {name} with args {args}"  )
            return prebuilt.builtin_funcs[name](*args)

        if name not in self.funcs:
            if name in self.vars and isinstance(self.vars[name], FunctionType) :
                fn = self.vars[name]
                return self.call_funcType(fn,args)
            else:
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

    def eval_simple_expression(self, node):
        """
        node is the parse tree node for simple_expression.
        This function evaluates the node according to:
        - default: left-to-right
        - if any operator token is OP_WS: evaluate using normal operator precedence
        """
        # print("Evaluating simple_expression:", node.pretty())
        # Build flattened lists: values and operator tokens
        values = []
        ops = []
        # first value
        values.append(self.eval_expr(node.children[0]))

        i = 1
        has_ws_op = False
        while i < len(node.children):
            op_token = node.children[i]   # a Token object
            rhs = self.eval_expr(node.children[i+1])

            # operator text (like "+", "*", "[]>", etc.)
            op_text = str(op_token)

            # record
            ops.append((op_text, getattr(op_token, 'type', None)))
            values.append(rhs)

            if getattr(op_token, 'type', None) == 'OP_WS':
                has_ws_op = True
            i += 2

        # Helper to apply operator using existing methods
        def apply_op(a, op, b):
            if op == "+":
                return self.add(a, b)
            elif op == "-":
                return self.sub(a, b)
            elif op == "*":
                return self.mul(a, b)
            elif op == "/":
                return (a // b) if b != 0 else 0
            elif op == "==":
                return 1 if a == b else 0
            elif op == "[]>":
                return self.get_index(a, b)
            elif op == "&":
                # choose semantics you already use for '&' if any; example bitwise-like:
                return a & b
            else:
                raise RuntimeError(f"Unknown operator {op}")

        # 1) No OP_WS: do strict left-to-right
        if not has_ws_op:
            left = values[0]
            for idx, (op_text, _op_type) in enumerate(ops):
                right = values[idx+1]
                left = apply_op(left, op_text, right)
            return left

        # 2) If OP_WS present: evaluate using normal precedence
        # Precedence map: higher number = higher precedence
        precedence = {
            '[]>': 4,
            '*': 3,
            '/': 3,
            '+': 2,
            '-': 2,
            '&': 2,   # adjust if you want different
            '==': 1
        }

        # Shunting-yard style evaluation operating on the already-evaluated values list
        val_stack = []
        op_stack = []

        # We'll iterate tokens in order: value0, op0, value1, op1, value2, ...
        # Start with first value
        val_stack.append(values[0])

        for idx, (op_text, _op_type) in enumerate(ops):
            # push next value and decide operator stack actions
            # while there is an operator on op_stack with >= precedence, pop and apply it
            while op_stack and precedence.get(op_stack[-1], 0) >= precedence.get(op_text, 0):
                op_to_apply = op_stack.pop()
                b = val_stack.pop()
                a = val_stack.pop()
                val_stack.append(apply_op(a, op_to_apply, b))
            # push current operator and next value
            op_stack.append(op_text)
            val_stack.append(values[idx+1])

        # flush remaining ops
        while op_stack:
            op_to_apply = op_stack.pop()
            b = val_stack.pop()
            a = val_stack.pop()
            val_stack.append(apply_op(a, op_to_apply, b))

        if len(val_stack) != 1:
            raise RuntimeError("Evaluation error: value stack ended with multiple values")
        return val_stack[0]



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


    def error(self, message,cls=callable):
        # meta.line is available because of propagate_positions=True

        # Format the Awesome Error
        raise cls(f"[Line {self.line}] Awesome Error: {message}")

# --- Running ---

def run_awesome(code:str):


    parser = Lark(GRAMMAR, start='start', parser='earley',propagate_positions=True)
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
        # print(tree.pretty());
        interpreter.run(tree)
    except Exception as e:
        print(f"Awesome Error: {e}")
        print("Node:", interpreter.current_node)

        print("Line:", code.split("\n")[interpreter.line-1] if isinstance(interpreter.line,int) and interpreter.line>0 else "")
        raise

# --- Test Script ---


if __name__ == "__main__":
    import sys
    run_awesome(open(sys.argv[1]).read())