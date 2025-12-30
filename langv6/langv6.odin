package awesome

import "core:fmt"
import "core:mem"
import "core:os"
import "core:strconv"
import "core:strings"
import "core:unicode"
import "core:unicode/utf8"

// --- Types ---

ValueType :: enum {
	Integer,
	List,
	LazyGen,
	Function,
	Void,
}

Value :: struct {
	type:  ValueType,
	i_val: int,
	l_val: [dynamic]Value,
	f_val: ^Function,
	g_val: ^LazyGenerator,
}
MValues :: struct {
	values: []Value,
}

Function :: struct {
	name:      string,
	arg_names: [dynamic]string,
	body:      ^Node,
}

LazyGenerator :: struct {
	// [start, step] OR [func_name, seed1, seed2...]
	is_func:   bool,

	// Arithmetic State
	current:   int,
	step:      int,

	// Function State
	func_name: string,
	seeds:     [dynamic]Value, // Acts as the rolling window/cache for args

	// Common
	cache:     [dynamic]Value,
}

NodeType :: enum {
	Program,
	Block,
	// Statements
	Assignment,
	Print,
	Loop,
	Conditional,
	FuncDef,
	CodeBlockDef,
	CodeBlockRun,
	SkipOp,
	// Expressions
	Literal,
	Var,
	BinOpExpr,
	ListLit,
	GeneratorLit,
	Call,
	PrepFunc,
}

Node :: struct {
	kind:     NodeType,
	children: [dynamic]^Node,
	// Metadata
	name_val: string, // for vars, funcs, ops
	int_val:  int, // for skip counts
	token:    Token, // location data
}

// --- Lexer ---

TokenType :: enum {
	EOF,
	Identifier,
	Number,
	String,
	Loop,
	Pool,
	Arrow, // ->
	Apply, // %>
	Conditional, // ?%>
	Index, // []>
	Ampersand, // &
	Question, // ?
	Colon,
	Hash,
	At,
	Range, // : # @ ..
	LPar,
	RPar,
	LBrack,
	RBrack,
	LBrace,
	RBrace,
	Comma,
	Plus,
	Minus,
	Star,
	Slash,
	Equals,
	Dollar,
}

Token :: struct {
	type:  TokenType,
	text:  string,
	line:  int,
	no_ws: bool, // True if NOT followed by whitespace (tight binding)
}

Lexer :: struct {
	src:  string,
	pos:  int,
	line: int,
}

dump_node :: proc(n: ^Node, indent := 0) {
	for i := 0; i < indent; i += 1 {fmt.print("  ")}
	fmt.printf("%v (%v) name=%q int=%d\n", n.kind, n.token.type, n.name_val, n.int_val)

	for c in n.children {
		dump_node(c, indent + 1)
	}
}

lex_token :: proc(l: ^Lexer) -> Token {
	// Skip whitespace
	for l.pos < len(l.src) {
		r := rune(l.src[l.pos])
		if !unicode.is_white_space(r) {break}
		if r == '\n' {l.line += 1}
		l.pos += 1
	}

	if l.pos >= len(l.src) {return Token{.EOF, "", l.line, false}}

	start := l.pos
	r, w := utf8.decode_rune_in_string(l.src[l.pos:])
	l.pos += w

	// Check for # comment immediately
	if r == '#' && l.pos < len(l.src) {
		// Grammar: comment only if at start of line (handled by parser?) or complex logic.
		// Spec: "# comment ... no spaces allowed before, # is actually a codeblock"
		// Spec: "A comment can only start at a new line."
		// Parser will handle distinctions. Lexer just returns Hash or Comment?
		// Let's assume standard '#' is hash, unless parsing logic decides otherwise.
		// Actually, spec says: "# comment". If we see # followed by space, it might be comment?
		// "To avoid conflict with comments, you can place a space before #"
		// Let's stick to returning Hash token for '#', logic in parser.
	}

	// Double char tokens
	if l.pos < len(l.src) {
		n := l.src[l.pos]
		if r == '-' && n == '>' {l.pos += 1; return mk_tok(l, .Arrow, start)}
		if r == '%' && n == '>' {l.pos += 1; return mk_tok(l, .Apply, start)}
		if r == '[' && n == ']' {
			if l.pos + 1 < len(l.src) && l.src[l.pos + 1] == '>' {
				l.pos += 2; return mk_tok(l, .Index, start)
			}
		}
		if r == '?' && n == '%' {
			if l.pos + 1 < len(l.src) && l.src[l.pos + 1] == '>' {
				l.pos += 2; return mk_tok(l, .Conditional, start)
			}
		}
		if r == '.' && n == '.' {l.pos += 1; return mk_tok(l, .Range, start)}
	}

	switch r {
	case '(':
		return mk_tok(l, .LPar, start)
	case ')':
		return mk_tok(l, .RPar, start)
	case '[':
		return mk_tok(l, .LBrack, start)
	case ']':
		return mk_tok(l, .RBrack, start)
	case '{':
		return mk_tok(l, .LBrace, start)
	case '}':
		return mk_tok(l, .RBrace, start)
	case ':':
		return mk_tok(l, .Colon, start)
	case ',':
		return mk_tok(l, .Comma, start)
	case '&':
		return mk_tok(l, .Ampersand, start)
	case '@':
		return mk_tok(l, .At, start)
	case '#':
		return mk_tok(l, .Hash, start)
	case '$':
		return mk_tok(l, .Dollar, start)
	case '+':
		return mk_tok(l, .Plus, start)
	case '-':
		return mk_tok(l, .Minus, start)
	case '*':
		return mk_tok(l, .Star, start)
	case '/':
		return mk_tok(l, .Slash, start)
	case '=':
		return mk_tok(l, .Equals, start) // Assumed equality op
	case '?':
		return mk_tok(l, .Question, start)
	case '"', '\'':
		// String literal
		q := r
		for l.pos < len(l.src) {
			curr, cw := utf8.decode_rune_in_string(l.src[l.pos:])
			l.pos += cw
			if curr == q {break}
		}
		return mk_tok(l, .String, start)
	}

	if unicode.is_digit(r) {
		for l.pos < len(l.src) && unicode.is_digit(rune(l.src[l.pos])) {l.pos += 1}
		return mk_tok(l, .Number, start)
	}

	if unicode.is_alpha(r) || r == '_' {
		for l.pos < len(l.src) {
			nr := rune(l.src[l.pos])
			if !unicode.is_alpha(nr) && !unicode.is_digit(nr) && nr != '_' {break}
			l.pos += 1
		}
		text := l.src[start:l.pos]
		if text == "loop" {return mk_tok(l, .Loop, start)}
		if text == "pool" {return mk_tok(l, .Pool, start)}
		return mk_tok(l, .Identifier, start)
	}

	return mk_tok(l, .EOF, start)
}

mk_tok :: proc(l: ^Lexer, t: TokenType, start: int) -> Token {
	txt := l.src[start:l.pos]
	// Check Tight Binding (No whitespace immediately after)
	no_ws := true
	if l.pos < len(l.src) {
		if unicode.is_white_space(rune(l.src[l.pos])) {
			no_ws = false
		}
	}
	return Token{t, txt, l.line, no_ws}
}

// --- Parser ---

Parser :: struct {
	tokens: [dynamic]Token,
	curr:   int,
}

parse :: proc(code: string) -> ^Node {
	l := Lexer{code, 0, 1}
	p := Parser{make([dynamic]Token), 0}
	for {
		t := lex_token(&l)
		append(&p.tokens, t)
		if t.type == .EOF {break}
	}

	root := new_node(.Program)
	for p.curr < len(p.tokens) - 1 {
		if peek(&p).type == .Colon {advance(&p); continue} 	// Skip separators
		stmt := parse_statement(&p)
		if stmt != nil {append(&root.children, stmt)} else {break} 	// Stop if cannot parse
	}
	return root
}

peek :: proc(p: ^Parser, offset := 0) -> Token {
	idx := p.curr + offset
	if idx >= len(p.tokens) {return p.tokens[len(p.tokens) - 1]}
	return p.tokens[idx]
}

advance :: proc(p: ^Parser) -> Token {
	t := peek(p)
	if p.curr < len(p.tokens) {p.curr += 1}
	return t
}

check :: proc(p: ^Parser, t: TokenType) -> bool {return peek(p).type == t}
match :: proc(p: ^Parser, t: TokenType) -> bool {
	if check(p, t) {advance(p); return true}
	return false
}

new_node :: proc(k: NodeType) -> ^Node {
	n := new(Node)
	n.kind = k
	n.children = make([dynamic]^Node)
	return n
}

parse_statement :: proc(p: ^Parser) -> ^Node {
	t := peek(p)

	// Comment check (Naive: if # at start of line/stmt)
	// Spec: "# comment". Hash token.
	// We handle Hash as Codeblock usually.

	// Loop: loop i & [0,1] ... pool i
	if match(p, .Loop) {
		n := new_node(.Loop)
		n.name_val = advance(p).text // iterator name
		match(p, .Ampersand)
		append(&n.children, parse_expr(p)) // iterable

		block := new_node(.Block)
		for !check(p, .Pool) && !check(p, .EOF) {
			if check(p, .Colon) {advance(p); continue}
			s := parse_statement(p)
			if s != nil {append(&block.children, s)}
		}
		append(&n.children, block)
		match(p, .Pool)
		if check(p, .Identifier) {advance(p)} 	// Optional name
		return n
	}

	// CodeBlock Definition: #name{ or #name@{
	if t.type == .Hash {
		// If the '#' token was followed by whitespace (no_ws == false), treat as a comment.
		// We will consume tokens until we reach a different line (skip the comment).
		if peek(p).no_ws == false {
			// consume the hash
			h := advance(p)
			curr_line := h.line
			// skip tokens on the same line
			for peek(p).line == curr_line && peek(p).type != .EOF {
				advance(p)
			}
			// return nil to indicate a skipped statement (or continue parsing loop)
			return nil
		}

		// Now '#' is "tight" (no_ws true): could be codeblock def or codeblock run
		// Look for pattern: '#' Identifier [@] '{'  (codeblock def)
		// or '#' Identifier '#' (codeblock run)
		if peek(p, 1).type == .Identifier {
			// Peek further to see if this is a def with brace
			// Check for optional '@' then '{'
			if (peek(p, 2).type == .At && peek(p, 3).type == .LBrace) ||
			   (peek(p, 2).type == .LBrace) {
				// It's a codeblock definition
				advance(p) // consume '#'
				name := advance(p).text
				n := new_node(.CodeBlockDef)
				n.name_val = name

				is_delayed := false
				if match(p, .At) {is_delayed = true}

				match(p, .LBrace)
				block := new_node(.Block)
				for !check(p, .RBrace) && !check(p, .EOF) {
					if check(p, .Colon) {advance(p); continue}
					s := parse_statement(p)
					if s != nil {append(&block.children, s)}
				}
				match(p, .RBrace)

				append(&n.children, block)
				n.int_val = is_delayed ? 1 : 0
				return n
			}

			// CodeBlockRun: `#name#`
			if peek(p, 2).type == .Hash {
				advance(p) // '#'
				name := advance(p).text
				advance(p) // trailing '#'
				n := new_node(.CodeBlockRun)
				n.name_val = name
				return n
			}
		}

		// If we reach here, it's a '#' that doesn't match codeblock forms.
		// Treat it as a comment: consume the rest of the line.
		advance(p) // consume '#'
		curr_line := t.line
		for peek(p).line == curr_line && peek(p).type != .EOF {
			advance(p)
		}
		return nil
	}


	// CodeBlock Run: #name#
	if t.type == .Hash && peek(p, 1).type == .Identifier && peek(p, 2).type == .Hash {
		advance(p); name := advance(p).text; advance(p)
		n := new_node(.CodeBlockRun)
		n.name_val = name
		return n
	}

	// Function Definition: (params) name block name ()
	// or Expression.
	// Distinguish: `(a) name ...` vs `(1+2)`
	// Heuristic: If we see `(` then params then `)` then `Identifier` then `Identifier` or loop/etc (start of block)?
	if t.type == .LPar {
		// Lookahead
		is_func := false
		idx := 1
		for idx < 20 { 	// Scan ahead a bit
			pk := peek(p, idx)
			if pk.type == .RPar {
				if peek(p, idx + 1).type == .Identifier {
					// Found (..) Name. Likely func def.
					// Expression `(1) + 2` -> `(1)` is term, `+` is op.
					// Func def `(a) my_func ...`
					// If next token is Start of Block or Identifier?
					is_func = true
				}
				break
			}
			if pk.type == .EOF {break}
			idx += 1
		}

		if is_func {
			advance(p) // (
			params := new_node(.ListLit)
			for !check(p, .RPar) {
				if check(p, .Identifier) {
					v := new_node(.Var); v.name_val = advance(p).text
					if match(p, .Dollar) {advance(p)} 	// skip type
					append(&params.children, v)
					match(p, .Comma)
				} else {break}
			}
			match(p, .RPar)
			name := advance(p).text

			// Block
			block := new_node(.Block)
			// Parse until `name ()`
			// This is tricky. We need to consume statements until we see `NAME ()`
			for {
				if check(p, .EOF) {break}
				if check(p, .Identifier) && peek(p, 1).type == .LPar && peek(p, 2).type == .RPar {
					if peek(p).text == name {
						break // Found end
					}
				}
				if check(p, .Colon) {advance(p); continue}
				s := parse_statement(p)

				if s != nil {append(&block.children, s)}
			}

			match(p, .Identifier) // Name
			match(p, .LPar); match(p, .RPar)

			n := new_node(.FuncDef)
			n.name_val = name
			append(&n.children, params)
			append(&n.children, block)
			return n
		}
	}

	// Default: Expression-based statement
	expr := parse_expr(p)

	// Assignment: expr -> target
	if match(p, .Arrow) {
		target := advance(p).text // Could be Number or Name
		n := new_node(.Assignment)
		n.name_val = target
		append(&n.children, expr)
		return n
	}

	// Conditional: expr ?%> KEYWORD
	if match(p, .Conditional) {
		kw := advance(p).text
		n := new_node(.Conditional)
		n.name_val = kw
		append(&n.children, expr)
		return n
	}

	// Print / Skip / Debug: expr ? ? ?
	if check(p, .Question) {
		count := 0
		for match(p, .Question) {count += 1}

		if count > 6 {
			// Skip lines
			n := new_node(.SkipOp)
			n.int_val = count - 6 // Spec: ?????? + n
			return n
		}

		// Print (1 '?') or Debug (2-6 '?')
		// For this implementation, treat all as Print/Debug
		n := new_node(.Print)
		n.int_val = count
		append(&n.children, expr)
		return n
	}

	return expr
}

// Expression Parsing with Flattening for Precedence
parse_expr :: proc(p: ^Parser) -> ^Node {
	// Parse sequence: term (OP term)*
	lhs := parse_term(p)

	// If not an operator, return lhs
	if !is_bin_op(peek(p).type) {return lhs}

	// Collect chain
	chain := new_node(.BinOpExpr)
	append(&chain.children, lhs)

	for is_bin_op(peek(p).type) {
		op_tok := advance(p)
		rhs := parse_term(p)

		// Wrap Op in Node to preserve 'no_ws' meta
		op_node := new_node(.Literal)
		op_node.name_val = op_tok.text
		op_node.token = op_tok // Crucial for evaluation

		append(&chain.children, op_node)
		append(&chain.children, rhs)
	}
	return chain
}

is_bin_op :: proc(t: TokenType) -> bool {
	#partial switch t {
	case .Plus, .Minus, .Star, .Slash, .Ampersand, .Equals, .Index:
		return true
	}
	return false
}

parse_term :: proc(p: ^Parser) -> ^Node {
	t := peek(p)

	if match(p, .LPar) {
		e := parse_expr(p)
		match(p, .RPar)
		return e
	}

	if t.type == .Number {
		advance(p)
		n := new_node(.Literal)
		n.name_val = t.text
		return n
	}

	if t.type == .Identifier {
		name := advance(p).text
		// Check for Apply: name %> ()
		if match(p, .Apply) {
			match(p, .LPar); match(p, .RPar)
			// Call
			n := new_node(.Call)
			n.name_val = name
			return n
		}
		n := new_node(.Var)
		n.name_val = name
		return n
	}

	if t.type == .String {
		advance(p)
		n := new_node(.Literal)
		n.name_val = t.text
		return n
	}

	if match(p, .LBrack) {
		// List: [a, b, ..]
		list_node := new_node(.ListLit)
		is_inf := false

		for !check(p, .RBrack) {
			if match(p, .Range) {
				is_inf = true
				break
			}
			e := parse_expr(p)
			append(&list_node.children, e)
			match(p, .Comma)
		}
		match(p, .RBrack)

		if is_inf {
			// Check for Generator Func: [seeds, func, ..] %> ()
			if check(p, .Apply) {
				match(p, .Apply); match(p, .LPar); match(p, .RPar)
				list_node.kind = .GeneratorLit
				// Last child is function var
				return list_node
			}
			// Arithmetic/Const Generator
			list_node.kind = .GeneratorLit
			return list_node
		}

		// Check for Prep Call: [args](name) %> ()
		if match(p, .LPar) {
			func_name := advance(p).text
			match(p, .RPar)

			// [args](name) is a "Prep"
			// Check for %> ()
			if match(p, .Apply) {
				match(p, .LPar); match(p, .RPar)
				// It's a Call
				n := new_node(.Call)
				n.name_val = func_name
				// args is the list_node
				append(&n.children, list_node)
				return n
			}
		}

		return list_node
	}

	// Unary Minus (Simple hack: 0 - x)
	if match(p, .Minus) {
		term := parse_term(p)
		n := new_node(.BinOpExpr)
		zero := new_node(.Literal); zero.name_val = "0"
		op := new_node(.Literal); op.name_val = "-"
		op.token.no_ws = true // Bind tight
		append(&n.children, zero)
		append(&n.children, op)
		append(&n.children, term)
		return n
	}

	// Empty expression @
	if match(p, .At) {
		n := new_node(.Literal)
		n.name_val = "@"
		return n
	}

	advance(p)
	return new_node(.Literal) // Fallback
}

// --- Interpreter ---

Interpreter :: struct {
	vars:            map[string]Value,
	literal_patches: map[string]Value, // "2" -> 11
	codeblocks:      map[string]^Node,
	skip_lines:      int,
	should_break:    bool,
}

interp_init :: proc() -> Interpreter {
	return Interpreter {
		make(map[string]Value),
		make(map[string]Value),
		make(map[string]^Node),
		0,
		false,
	}
}

// Values

v_int :: proc(i: int) -> Value {return Value{type = .Integer, i_val = i}}
v_list :: proc(v: []Value) -> Value {
	d := make([dynamic]Value)
	append(&d, ..v)
	return Value{type = .List, l_val = d}
}

get_val_str :: proc(i: ^Interpreter, s: string) -> Value {
	if s == "@" {return Value{type = .Void}}

	// Strings
	if s[0] == '"' || s[0] == '\'' {
		content := s[1:len(s) - 1]
		d := make([dynamic]Value)
		if s[0] == '\'' { 	// Rev
			for x := len(content) - 1; x >= 0; x -= 1 {append(&d, v_int(int(content[x])))}
		} else {
			for c in content {append(&d, v_int(int(c)))}
		}
		return Value{type = .List, l_val = d}
	}

	// Mutable Number Check
	if s in i.literal_patches {return i.literal_patches[s]}

	// Number
	if unicode.is_digit(rune(s[0])) || (s[0] == '-' && len(s) > 1) {
		val, _ := strconv.parse_int(s)
		return v_int(val)
	}
	return v_int(0)
}

// Execution

// run_block :: proc(i: ^Interpreter, node: ^Node) {
// 	for child in node.children {
// 		if i.should_break { break }

// 		// Line Skipping Logic
// 		if i.skip_lines > 0 {
// 			// Naive: We skip statements. Spec says "skip lines".
// 			// Since parser grouped statements, let's treat statements as lines for simplicity,
// 			// or try to track line numbers.
// 			// Accurate way: Check child line number.
// 			i.skip_lines -= 1
// 			continue
// 		}

// 		eval_node(i, child)
// 	}
// }

eval_node :: proc(i: ^Interpreter, n: ^Node) -> Value {
	if n == nil {return v_int(0)}

	#partial switch n.kind {
	case .Literal:
		return get_val_str(i, n.name_val)
	case .Var:
		// Check vars, then patches
		if n.name_val in i.vars {return i.vars[n.name_val]}
		if n.name_val in i.literal_patches {return i.literal_patches[n.name_val]}
		// fmt.println("Undef var:", n.name_val)
		return v_int(0)

	case .Assignment:
		val := eval_node(i, n.children[0])
		tgt := n.name_val
		// Check if target is number-like
		is_num := true
		if len(tgt) > 0 {
			if tgt[0] == '-' && len(tgt) > 1 {} else // neg number
			if !unicode.is_digit(rune(tgt[0])) {is_num = false}
		}
		if is_num {i.literal_patches[tgt] = val} else {i.vars[tgt] = val}
		return val

	case .ListLit:
		d := make([dynamic]Value)
		for c in n.children {append(&d, eval_node(i, c))}
		return Value{type = .List, l_val = d}

	case .GeneratorLit:
		return create_generator(i, n)

	case .BinOpExpr:
		return eval_binop(i, n)

	case .Print:
		val := eval_node(i, n.children[0])
		if n.int_val == 1 {
			// Plain print
			if val.type != .Void {
				// Special case: string list print? Spec says print expr.
				print_value(val)
				fmt.println("")
			}
		} else {
			// Debug (??)
			fmt.print("DEBUG: ")
			print_value(val)
			fmt.println("")
		}
		return val

	case .SkipOp:
		i.skip_lines = n.int_val
		return v_int(0)

	case .Loop:
		iterable := eval_node(i, n.children[0])
		var_name := n.name_val
		body := n.children[1]

		if iterable.type == .List {
			for v in iterable.l_val {
				i.vars[var_name] = v
				run_block(i, body)
				if i.should_break {i.should_break = false; break}
			}
		} else if iterable.type == .LazyGen {
			gen := iterable.g_val
			idx := 0
			for {
				v := get_gen_idx(i, gen, idx)
				i.vars[var_name] = v
				run_block(i, body)
				if i.should_break {i.should_break = false; break}
				idx += 1
				if idx > 10000 {break} 	// Sanity limit for infinite loop
			}
		}
		return v_int(0)

	case .Conditional:
		cond := eval_node(i, n.children[0])
		is_true := false
		if cond.type == .Integer && cond.i_val != 0 {is_true = true}
		if cond.type == .List && len(cond.l_val) > 0 {is_true = true}

		if is_true {
			if n.name_val == "pool" {i.should_break = true} else {
				// Apply function?
				// Spec: "apply the next keyword"
				// e.g. cond ?%> macro
				// We need to run the thing named n.name_val
				// It could be a CodeBlock or a Function?
				if n.name_val in i.codeblocks {
					run_block(i, i.codeblocks[n.name_val])
				}
				// TODO: func call
			}
		}
		return v_int(0)

	case .FuncDef:
		f := new(Function)
		f.name = n.name_val
		f.body = n.children[1]
		f.arg_names = make([dynamic]string)
		// Params in children[0]
		for p in n.children[0].children {
			append(&f.arg_names, p.name_val)
		}
		i.vars[f.name] = Value {
			type  = .Function,
			f_val = f,
		}
		return v_int(0)

	case .Call:
		// children[0] might be args list
		args: []Value
		if len(n.children) > 0 {
			args = eval_node(i, n.children[0]).l_val[:]
		} else {
			args = []Value{}
		}
		return call_func(i, n.name_val, args)

	case .CodeBlockDef:
		i.codeblocks[n.name_val] = n.children[0] // The block
		if n.int_val == 0 { 	// Run immediately
			run_block(i, n.children[0])
		}
		return v_int(0)

	case .CodeBlockRun:
		if n.name_val in i.codeblocks {
			run_block(i, i.codeblocks[n.name_val])
		}
		return v_int(0)
	}
	return v_int(0)
}

// Logic: Operator Precedence
// "Evaluated Left to Right. Unless user use whitespace... 1+2*3 = 9, 1+ 2*3 = 7"
eval_binop :: proc(i: ^Interpreter, n: ^Node) -> Value {
	// children: [Val, Op, Val, Op, Val...]
	// Pass 1: Handle "Tight" operators (no_ws = true)
	// We build a new list of values/ops where tight ops are collapsed.

	vals := make([dynamic]Value)
	ops := make([dynamic]string) // only loose ops remain

	curr_val := eval_node(i, n.children[0])

	idx := 1
	for idx < len(n.children) {
		op_node := n.children[idx]
		rhs_val := eval_node(i, n.children[idx + 1])

		if op_node.token.no_ws {
			// Bind immediately
			curr_val = do_op(i, curr_val, op_node.name_val, rhs_val)
		} else {
			// Push current accumulator and this loose op
			append(&vals, curr_val)
			append(&ops, op_node.name_val)
			curr_val = rhs_val
		}
		idx += 2
	}
	append(&vals, curr_val)

	// Pass 2: Left to Right on remaining
	acc := vals[0]
	for k := 0; k < len(ops); k += 1 {
		acc = do_op(i, acc, ops[k], vals[k + 1])
	}
	return acc
}


do_op :: proc(i: ^Interpreter, left: Value, op: string, right: Value) -> Value {
	if op == "+" {
		if left.type == .Integer && right.type == .Integer {return v_int(left.i_val + right.i_val)}
		if left.type == .List && right.type == .List {
			d := make([dynamic]Value)
			append(&d, ..left.l_val[:]); append(&d, ..right.l_val[:])
			return Value{type = .List, l_val = d}
		}
	}
	if op == "-" {
		if left.type == .Integer && right.type == .Integer {return v_int(left.i_val - right.i_val)}
		// List subtract? "Asuf" - "suf" = "A".
		// Naive implementation:
		if left.type == .List && right.type == .List {
			// If left ends with right, trim it? Or set diff? Spec implies string sub.
			// Let's assume strict suffix removal for string-lists.
			if len(left.l_val) >= len(right.l_val) {
				// Check suffix
				match := true
				off := len(left.l_val) - len(right.l_val)
				for k := 0; k < len(right.l_val); k += 1 {
					if left.l_val[off + k].i_val != right.l_val[k].i_val {match = false; break}
				}
				if match {
					d := make([dynamic]Value)
					for k := 0; k < off; k += 1 {append(&d, left.l_val[k])}
					return Value{type = .List, l_val = d}
				}
			}
		}
	}
	if op == "*" {
		if left.type == .Integer && right.type == .Integer {return v_int(left.i_val * right.i_val)}
		// List mul
		if left.type == .List && right.type == .List {
			// Spec: [1,2,3]*[4,5,6] -> [4,10,18] (Zip)
			d := make([dynamic]Value)
			sz := min(len(left.l_val), len(right.l_val))
			for k := 0; k < sz; k += 1 {
				v := left.l_val[k].i_val * right.l_val[k].i_val
				append(&d, v_int(v))
			}
			return Value{type = .List, l_val = d}
		}
		if left.type == .List && right.type == .Integer {
			// Repeat: "A" * 3
			d := make([dynamic]Value)
			for k := 0; k < right.i_val; k += 1 {append(&d, ..left.l_val[:])}
			return Value{type = .List, l_val = d}
		}
	}
	if op == "==" {
		// Basic deep eq
		eq := false
		if left.type == right.type {
			if left.type == .Integer {eq = (left.i_val == right.i_val)}
			// Simplified list eq
			if left.type == .List && len(left.l_val) == len(right.l_val) {eq = true} 	// Lazy
		}
		return v_int(eq ? 1 : 0)
	}
	if op == "&" {
		// In operator
		// a & list
		if right.type == .List {
			found := false
			for x in right.l_val {
				if x.type == .Integer &&
				   left.type == .Integer &&
				   x.i_val == left.i_val {found = true; break}
				// String check...
			}
			return v_int(found ? 1 : 0)
		}
	}
	if op == "[]>" {
		// Index
		idx := left.i_val
		if right.type == .List {
			n := len(right.l_val)
			// Support negative indices
			if idx < 0 {
				idx += n // e.g.: list of length 5, idx = -1; -1 + 5 = 4 -> last element.
			}
			if idx >= 0 && idx < n {
				return right.l_val[idx]
			}
			return v_int(0) // Safe out of bounds
		}
		if right.type == .LazyGen {
			return get_gen_idx(i, right.g_val, idx)
		}
	}
	return v_int(0)
}

// Generator Logic

create_generator :: proc(i: ^Interpreter, n: ^Node) -> Value {
	g := new(LazyGenerator)
	g.cache = make([dynamic]Value)

	// Check type
	// If [seeds, func, ..]
	// Last child in list-lit before Range is the func name?
	// Parser stored seeds... then FuncName?
	// Actually parser puts expressions.
	// We need to look at children.
	// [a, b, ..]

	seeds := make([dynamic]Value)
	for c in n.children {append(&seeds, eval_node(i, c))}

	// If the last seed is a Function Var?
	// Spec: [0,1,fib,..]
	last_idx := len(seeds) - 1
	if last_idx >= 0 && seeds[last_idx].type == .Function {
		// Function Generator
		g.is_func = true
		g.func_name = seeds[last_idx].f_val.name
		// Initial cache is seeds except func
		for k := 0; k < last_idx; k += 1 {append(&g.cache, seeds[k])}
	} else if len(seeds) >= 2 {
		// Arithmetic [0, 1, ..]
		v1 := seeds[0].i_val
		v2 := seeds[1].i_val
		g.current = v1
		g.step = v2 - v1
		// We don't fill cache for arith, we compute on fly?
		// Or we just fill cache as requested.
		// For [0,1,..], idx 0 -> 0, idx 1 -> 1.
		// Let's use cache for consistency.
		append(&g.cache, seeds[0])
		append(&g.cache, seeds[1])
		g.current = v2
	} else {
		// Const [0, ..]
		append(&g.cache, seeds[0])
		g.step = 0
		g.current = seeds[0].i_val
	}

	return Value{type = .LazyGen, g_val = g}
}

get_gen_idx :: proc(i: ^Interpreter, g: ^LazyGenerator, idx: int) -> Value {
	// If computed
	if idx < len(g.cache) {return g.cache[idx]}

	// Compute until idx
	for len(g.cache) <= idx {
		if g.is_func {
			// Call func with current list (cache)
			// Spec: [fib,..] -> calls fib(current_list)
			// Actually spec: "define a function that get a list (finite) and return the new element"

			// We need to pass the FULL cache so far? Or window?
			// Spec example: "-1 []> array". Suggests full array passed.
			inner_list := v_list(g.cache[:])

			// 2. Wrap it in a slice to represent the "Arguments List"
			// This results in: [ [1, 2, 3, ...] ]
			args_to_pass := []Value{inner_list}

			next_val := call_func(i, g.func_name, args_to_pass)
			append(&g.cache, next_val)
		} else {
			// Arith / Const
			g.current += g.step
			append(&g.cache, v_int(g.current))
		}
	}
	return g.cache[idx]
}

// Functions

call_func :: proc(i: ^Interpreter, name: string, args: []Value) -> Value {
	// Builtins
	if name == "print" {
		print_values(args) // print list as string
		fmt.println("")
		return v_int(0)
	}
	if name == "!" {
		// System command
		// args should be ['cmd', 'arg']
		return v_int(0) // Not implemented for safety/brevity
	}

	if name in i.vars {
		fn_val := i.vars[name]
		if fn_val.type == .Function {
			fn := fn_val.f_val

			// Scope Management (using map to save current state)
			saved := make(map[string]Value, context.temp_allocator)

			for pname, k in fn.arg_names {
				// 1. Save existing variable to restore later (Scope Management)
				if val, exists := i.vars[pname]; exists {
					saved[pname] = val
				}

				// 2. Assign the argument if it exists, otherwise default to 0
				if k < len(args) {
					i.vars[pname] = args[k]
				} else {
					i.vars[pname] = v_int(0) // Handle missing arguments
				}
			}

			// The last value evaluated in the body is the return value
			ret := run_block(i, fn.body)

			// Restore Scope
			for k, v in saved {i.vars[k] = v}
			// Note: Clear temp vars added that weren't in 'saved'
			for pname in fn.arg_names {
				if _, was_saved := saved[pname]; !was_saved {
					delete_key(&i.vars, pname)
				}
			}

			return ret
		}
	}
	return v_int(0)
}

run_block :: proc(i: ^Interpreter, node: ^Node) -> Value {
	last := v_int(0)
	for child in node.children {
		if i.should_break {break}
		if i.skip_lines > 0 {i.skip_lines -= 1; continue}
		last = eval_node(i, child)
	}
	return last
}

print_value :: proc(v: Value) {
	fmt.print(value_to_string(v))
	return
}
print_values :: proc(vs: []Value) {
	for v in vs {
		print_value(v)
	}
	return
}
// --- Main ---

main :: proc() {
	if len(os.args) < 2 {
		fmt.println("Usage: awesome <file>")
		return
	}
	data, _ := os.read_entire_file(os.args[1])
	code := string(data)

	ast := parse(code)
	dump_node(ast)

	interp := interp_init()
	run_block(&interp, ast)
}
