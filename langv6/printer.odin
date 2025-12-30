package awesome;
import "core:strconv"
import "core:math/big"
import "core:strings"
import "colors"

itoa :: proc(val: int) -> string {
    // Allocate 32 bytes on the temporary allocator
    buf := make([]u8, 32, context.temp_allocator)

    // write_int returns the sub-slice of buf that was actually used
    return strconv.write_int(buf, i64(val), 10)
}

get_func_name :: proc(v: Value) -> string {
    // Initialize builder using the temp_allocator
    b := strings.builder_make(context.temp_allocator)

    strings.write_string(&b, "<function ")
    strings.write_string(&b, v.f_val.name)
    strings.write_string(&b, ">")

    return strings.to_string(b)
}

value_to_string :: proc(v: Value,depth:int=0) -> string {
    if (depth>15){return "[[more then 15 depth]]"}
	switch v.type {
	case .Integer:
		return itoa(v.i_val)

	case .List:
		return list_to_string(v.l_val[:],depth)

	case .Function:
		if v.f_val == nil {
			return "<function>"
		}
		return get_func_name(v)

	case .LazyGen:
		return lazygen_to_string(v.g_val)

	case .Void:
		return "(Void)"

    }

	return "<unknown>"
}
list_to_string :: proc(list: []Value,depth:int) -> string {
    if len(list) == 0 do return "[]"

    // Initialize builder with temp_allocator
    b := strings.builder_make(context.temp_allocator)

    strings.write_byte(&b, '[')
    for val, i in list {
        if i > 0 {
            strings.write_string(&b, ", ")
        }
        // Assuming value_to_string also uses temp_allocator
        s := value_to_string(val,depth+1)
        strings.write_string(&b, s)
    }
    strings.write_byte(&b, ']')

    return strings.to_string(b)
}


lazygen_to_string :: proc(g: ^LazyGenerator) -> string {
    if g == nil do return "<generator>"

    b := strings.builder_make(context.temp_allocator)

    if g.is_func {
        strings.write_string(&b, "<generator ")
        strings.write_string(&b, g.func_name)
        strings.write_string(&b, "()>")
    } else {
        // A small local buffer for the digits
        buf: [32]u8

        strings.write_string(&b, "<generator start=")
        // write_int returns a string slice pointing into 'buf'
        strings.write_string(&b, strconv.write_int(buf[:], i64(g.current), 10))

        strings.write_string(&b, " step=")
        strings.write_string(&b, strconv.write_int(buf[:], i64(g.step), 10))

        strings.write_string(&b, ">")
    }
    return strings.to_string(b)
}