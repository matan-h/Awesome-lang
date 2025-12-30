package colors

import "core:fmt"
import "core:os"
import "core:terminal/ansi"
import "core:terminal"


RED_SEQ   :: Color{ansi.CSI + ansi.FG_RED    + ansi.SGR}
YELLOW_SEQ :: ansi.CSI + ansi.FG_YELLOW + ansi.SGR
CYAN_SEQ   :: ansi.CSI + ansi.FG_CYAN   + ansi.SGR
GREEN_SEQ  :: ansi.CSI + ansi.FG_GREEN  + ansi.SGR
RESET_SEQ  :: ansi.CSI + ansi.RESET     + ansi.SGR

colors_enabled: bool = false

enable :: proc() {
    // require context
	colors_enabled = terminal.is_terminal(os.stdout)
}
seq :: proc(c: Color) -> string {
	if !colors_enabled { return "" }
	return c.seq
}

ColorArg :: union {
	Color,
	string,
}

print :: proc(args: ..ColorArg) {
	for arg in args {
		switch a in arg {
		case Color:
			fmt.print(seq(a))
		case string:
			fmt.print(a)
		}
	}
}

