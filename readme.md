# Awesome: The Logical Language

> Everyone need just one simple, logical language

At Awesome (AKA `>4`), we believe programming language should be minimal. It should not get in the way.


There is only one keyword for looping, only over lists: `loop`.
And since Awesome has infinite lists from day 0, loops can be infinite by design.
```ruby
loop i&[0,0,..]
    ...
pool i
```
Vars are written as you think, not as you define in math
```ruby
1+2 -> a
a+8 -> b
```
Speaking of as you think, not as math, operations expressions are evaluated left to right. Unless the user use whitespace to tell it otherwise (`1+2*3`, will be `9`, while `1+ 2*3` will result in `7`)

Numbers are not constant, they are mutable vars.
```
a+b -> 2
```
From now, 2 will be a+b, so 3+8=11, so `2+1` would be `12`

instead of separating lines by enter, you can also use `:` instead:
```ruby
1+2 -> a: a+8 -> b
```
## Types
In Awesome, we believe in simplicity and minimalism. No need for two dozen types. There are only 3 Types: numbers, list and functions. Nothing more is needed.

## Functions
`()` is used only to define functions

for example
```ruby
() name
    loop _&[0,0,..]
        a-2 -> a
        a&[0] ?%> pool
    pool _
name ()
```

Keywords:
* `&` -> `in`
* `%?>`apply the next keyword if condition is true.
* pool - `'loop'` block end. When used as apply, it does `break` from the loop

Then to call it, you do
`name %> ()`
or if it gets arguments
`[1,2,3](name) %> ()`

If you want to specify return type, use `$`, for example:
```ruby
($list$int) name $int
```
Would be a function that get `list[int]` and return `int`

## Lists
Lists look like `[1,2,3]`
They can be assigned to variables and passed around freely.

If a list contains `..`, it is assumed to be **infinite**:
```ruby
[1,2,..]
[2,4,6,..]
[2,4,8,..]
[0,0,..]   :# infinite zeros
```
To access the list use the simple `[]>`, like so `4 []> [1,2,3,..]` (will output `5`, as index start at `0`, and yes, if you reassign `0`, it changes the indexing)

For more advanced arrays you can also You can also generate infinite lists from functions: `[name,..] %> ()` (will only be called when you need to access that. More on that later)


## Printing
> In Awesome it is super simple to print.

* adding one `?` (also `%>?` works here) at the end of an expression, will print the last result of the expression.
`[ 1+ 6*3 -> i ]( 4 []> [name,..] ) %>() ?`

> In Awesome it is super simple to debug.

* two `??`, expands and prints sub-expression result in the current one
* three `???`, expands all variables that are referenced in the current expression (including what numbers currently mean)
* four `????`, same as both the effect of ?? And ???.
* five `?????` same, but with terminal colors
* six  `??????` same, but only with bold red.
* more than six (`?????? + n`), will apply the same AND skip the next `n` lines

`@` is always an empty expression (i.e. `@?` will not print anything)

# strings:
`print` is a function that gets an array of ASCII numbers as the first argument.
`[ [65] ](print) %>() :# will print "A"`.

`""` and `''` are shortcuts to write strings:
```ruby
"AB" -> [65,66]
'AB' -> [66,65]
```

`tnirp` is a function that returns an array of numbers, ASCII. You can use `$` to specify type.
```ruby
tnirp %> ()  -> a $n
```
Using `<var> $<type>` will convert an array automatically to that type (note that `a<var>$n` is NOT the same, it will define a var named `a$n`)

Note that
lists can be added (`"A"+"A"` is `[65,65]`), subtracted (`"Asuf"-"suf"` is `[65]`), multiplied by list `[1,2,3]*[4,5,6]` is `[4,10,18]`, and multiply by number `"A"*3` is `[65,65,65]`

## Comments
`# comment`

A comment can only start at a new line. (no spaces allowed before,` #` is actually a codeblock, see later)

## Multiline comments:
to multiline comment the next 4 lines:
```ruby
(line)_: "#"+line : *() : [*  , 4]%> macro
```
its a bit complicated, so we have made it much simpler, using a function named `^mlc`.
```ruby
# comment the next 4 lines
[^mlc,4]%>macro
```

`mlc` second argument default is `~8`, which is infinity, so if you want the whole program from now on to be multiline comment, it's just
```ruby
[^mlc]%>macro
```

alternatively,
```ruby
:@????????? :# 6 '?' on empty expression then 4 '?' to skip the next four lines
```
prefix with `@` to force empty-expression context.

**Update: users told us they want block-scoped multiline comments:**
```
comment
anything
tnemmoc
```
It's actually very simple to implement in the awesome language:

```ruby
0->$c
(line)_
$c&[1] ?%> @???????:@???????
"#"+line -> line

line&["comment"] ?%> @??????? :# note the 7 '?', that on empty xpression, so if its true it skip the next line
@???????? :# skip the next 2 lines if this line was not skipped. note that empty lines/comments does not count
1->$c:[]->line

line&['comment'] ?%> @???????:@????????
0->$c:[]->line

line
_()
[_] %> macro
```
## About the logic
```ruby
$c&[1] ?%> @???????:@???????
```
Is the same as `if $c==1` in most languages, just more logically correct:

If `$c` is `0`, for example,
`0?%> @???????:@???????`
the second skip is skipped, so the line after it will execute. If `$c` is true, it won't.


## Codeblocks '#'. no repeated code, ever again
We believe programmers should not repeat code. You've already written it, right?

Even in the examples above. It does have some repeated code. What if we could define a block of text, that the language will simply copy/paste automatically. For that, we have `#`.
Defining a Codeblock
```less
#j{code}
```
This does:
1. run `code` immediately, as if it was written alone
2. Defines a codeblock named j

Use it later:
```less
#j#
```

Conceptually, assume the language just blindly `replace("#{name}#",code)`.

To avoid conflict with comments, you can place a space before `#`, and Since comments start only at the beginning of a line, it will prevent it from becoming a comment

Here is the previous function rewritten using codeblocks:
```less
0->$c
(line)_
$c&[1] #?2>{?%> @???????:@???????}
"#"+line -> line

line&["comment"] #?2>#
1->#[]line{$c:[]->line}

line&['comment'] #?2>#
0->$[]line

line
_()
[_] %> macro
```
We do not recommend using codeblocks for very small or simple expressions as overusing them can increase boilerplate instead of reducing it.
For example: `#]{]}` then `#]#`, is worse than just writing `]`

Sometimes you want to define a block without executing it.
To do this, prefix the `{` (not the `#`) with `@`:
```less
#j@{???}
```

This work well with loops:

```less
# define a codeblock named '10?' thats '?'*10
 #10?@{}
loop ;&[1,..]
 #10?@{#10?#?}
 ;&[10] ?%> pool
pool
```
(We recommend using `;` in loops, compared to the boring `i`. You also don't need to change much, they look almost the same)

## Infinite lists
to build infinite list, you need to define a function that get a list (finite) and return the new element
```less
[fib,..] %> ()
```
you can also specify a starting array with this syntax
```less
[0,1,fib,..] %> ()
```

```less
(array) fib
    # return last + second last
    -1 []>array -> a
    -2 []>array -> b
    a+b
fib ()
[0,1,fib,..] %> () -> fibs
10 []>fibs? :# get the 10th number
```

## Infinity
Not all infinities are the same, so we offer you a bunch of infinities to choose from:
`~999`: The number of seconds until the Sun becomes a red giant and engulfs (about 1.577e17 seconds)

* `~8` The most basic one, stay `~8` and positive no matter what
* `~7` Cryptographic Infinity, resolve to `2^256` on Windows, and `2^512` on Linux/mac
* `~6` The full number of files on this disk. Dangerous! Using it might take a lot of time.
* `~5` The amount of space left on this disk. Counted as MB
* `~4` The amount of used left on this disk. Counted as MB
* `~3` The current process PID.
* `~2` The current number of stars in the observable universe, according to NASA.
* `~1` Stay `~1` and negative no matter what.
* `~0` Stay `~0` and make all the other numbers equal `~0`.

## Imports
you can import awesome files like so
```less
`"mylib" %> import`
```
This will look for a file named `mylib.awesome-logical-language-program-file`, named `mylib.elif-margorp-egaugnal-lacigol-emosewa` ,or named `mylib.^%>` and include it.

If the file cannot be found, the language does a recursive check in all folders in the current directory, if you have a file named like that. The depth by default is `~2`

## References, multiline string
We think that in any case, multiline string make the code harder to read, and make maintainability of the code harder. if you need a multiline string, just read it from a file:
```less
[ "program.txt","r" ](readfile) %>() > program
```
we acknowledge that some users want to keep their programs portable, and moving multiple files is a problem, so we have a solution:
You can, at the bottom of the program, write in this syntax
```ruby
------- program.txt --------
mystring
------- anotherprogram --------
```
**Notice it is *exactly* 7 '-' on the start of the line, then 8 after filename. It specifies the amount of read/write allowed**

Then before that, you can use the references:
```less
[ "program.txt","r" ](readfile) %>() -> program
```

If you write 7+n `-` at the start, you can write it `n` times

If you write 7+n `-` after the name, you can read it `n` times

In the example, we specify one read, so after the usage one time, we could read the actual program.txt, so it does not block the user.

## builtins
*functions:*
* `($list$int) escape $int`/`epacse` - when you write a string, we don't expand `\n..` automatically, instead, use `epacse` function for that. Notice that if you pass `[5,13]` it will simply delete both, and return an empty array. That's because 13 is `\r`, which deletes the last character
* `($list$int) l2i $int` - convert `[3,1,4,1,5,9,2]` into `3141592` number, so you can operate
* `($int) i2l $list$int` - convert `3141592` back into list

* `($list$int,$int) l2b $list$int` - base encode list, gets two parameters, list and base (e.g. 64)
* `($list$int,$int) b2l $list$int` - base64 decode `list[int]`, gets two parameters, list and base (e.g. 64).
* `($list,$int) limit $list` Return list from 0 until n. very useful for infinite lists (e.g. to get a list that's the first 10 of pi you simply call this function with (pi,10))
* `($list,$int) timil $list` Return list with the n last elements removed, does not work on infinite lists.
* `($list$int,$int) e2l $list$int` find the `n`st likely possible options for error (see later)
* `($list$list$int) ! $list$list$int` - execute a system command, return three lists, first is stdout,second is stderr, the third contain only the status code

*vars:*
* `pi $list$int` - in Awesome, we don't believe float numbers should exist (they do not make sense, all you need is ints). Therefore, `pi` is simply an infinite list of pi digits. the float of `pi` is `[[pi],1]` to specify the first digit is before the `.`
* `args $list$list$int`: Command line arguments. Each argument as its own list.

## Errors
by default, the language assumes you are in production, so it will display errors, while trying to take as little space as possible. So to save space, the error is XOR-ed (while forcing it to be readable) with the line number. For example, here is the error message `NameError: Function 'fib' not defined.` at line 1
```less
O`ldDssns;!Gtobuhno!&ghc&!onu!edghode/
```
Then it's very simple to check what in the 255 options is your error and what isn't.
If the line number is more than `255`, we add `|` at the start, and `|n` at the end (`n` is the `n` in 255*n+g) number, so It's possible to get the right line number.

To get the error from the XOR-ed, we have a simple command line to find the most likely error:
```bash
awesome -c "1 []> args -> a : [ a,1 ](e2l) %>()?" "<error-here>"
```
That will get the (`1`st) most likely error option, and print it.


To opt-out of this behavior, at the very first line of the program, write this line:
```ruby
:'srorre esu':
```
(you can also reverse it, and use `"`, if you want)

## Using python libraries
We acknowledge that there are more than 710,108 internet packages and 188 libraries written in the non-logical language python. We believe it is better to not reinvent the wheel, and even creating all built-in libraries would take years of unnecessary work (estimated about 0.37yr for Linux, 3 for mac, and 10 for Windows, for each module support).

We allow you to use your favorite python modules using `importpy` function
```ruby
[ "random",["randint","randrange"] ](importpy) %>() -> random
0 []>random -> randint : 1 []>random -> randrange
[1,10](randint) %>()? :# for example, output 7
[1,10](randrange) %>()? :# for example, output [[7,3,6,8],1]
```
`class` are just a module that's not declared proparly. To import a class, use `importpyclass`, that get `(modName,clsname,cls_init_args,cls_methods)`
```ruby
0.77 -> seed
[ "random","Random",[seed],["randint"] ](importpyclass) %>() -> random
0 []>random -> randint
[1,10](randint) %>()? :# output 0.3
```

## More examples
running system command (using `'` to allow `"` inside the string)
```ruby
[ 'ohce','"ih"' ](!) %>() -> info
0 []> info -> out
[ out ](print) %>() :# print "hi"
```


## Inspired by
* Dreamberd, for the mutable numbers, and the idea.
* Casio calculator for the `2->x:x+2->y:y` language.
* Bash, for the `block, kcolb` system
* Javascript for code that look simple when you are not looking at it
