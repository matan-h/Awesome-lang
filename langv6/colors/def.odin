package colors
import "core:terminal/ansi"

Color :: struct {
	seq: string, // ANSI sequence (e.g. "\x1b[31m")
}

RESET := Color{ansi.CSI + ansi.RESET + ansi.SGR}

BLACK :: Color{ansi.CSI + ansi.FG_BLACK + ansi.SGR}
RED :: Color{ansi.CSI + ansi.FG_RED + ansi.SGR}
GREEN :: Color{ansi.CSI + ansi.FG_GREEN + ansi.SGR}
YELLOW :: Color{ansi.CSI + ansi.FG_YELLOW + ansi.SGR}
BLUE :: Color{ansi.CSI + ansi.FG_BLUE + ansi.SGR}
MAGENTA :: Color{ansi.CSI + ansi.FG_MAGENTA + ansi.SGR}
CYAN :: Color{ansi.CSI + ansi.FG_CYAN + ansi.SGR}
WHITE :: Color{ansi.CSI + ansi.FG_WHITE + ansi.SGR}
COLOR :: Color{ansi.CSI + ansi.FG_COLOR + ansi.SGR}
COLOR_8_BIT :: Color{ansi.CSI + ansi.FG_COLOR_8_BIT + ansi.SGR}
COLOR_24_BIT :: Color{ansi.CSI + ansi.FG_COLOR_24_BIT + ansi.SGR}
DEFAULT :: Color{ansi.CSI + ansi.FG_DEFAULT + ansi.SGR}

BG_BLACK :: Color{ansi.CSI + ansi.BG_BLACK + ansi.SGR}
BG_RED :: Color{ansi.CSI + ansi.BG_RED + ansi.SGR}
BG_GREEN :: Color{ansi.CSI + ansi.BG_GREEN + ansi.SGR}
BG_YELLOW :: Color{ansi.CSI + ansi.BG_YELLOW + ansi.SGR}
BG_BLUE :: Color{ansi.CSI + ansi.BG_BLUE + ansi.SGR}
BG_MAGENTA :: Color{ansi.CSI + ansi.BG_MAGENTA + ansi.SGR}
BG_CYAN :: Color{ansi.CSI + ansi.BG_CYAN + ansi.SGR}
BG_WHITE :: Color{ansi.CSI + ansi.BG_WHITE + ansi.SGR}
BG_COLOR :: Color{ansi.CSI + ansi.BG_COLOR + ansi.SGR}
BG_COLOR_8_BIT :: Color{ansi.CSI + ansi.BG_COLOR_8_BIT + ansi.SGR}
BG_COLOR_24_BIT :: Color{ansi.CSI + ansi.BG_COLOR_24_BIT + ansi.SGR}
BG_DEFAULT :: Color{ansi.CSI + ansi.BG_DEFAULT + ansi.SGR}

NO_PROPORTIONAL_SPACING :: Color{ansi.CSI + ansi.NO_PROPORTIONAL_SPACING + ansi.SGR}
FRAMED :: Color{ansi.CSI + ansi.FRAMED + ansi.SGR}
ENCIRCLED :: Color{ansi.CSI + ansi.ENCIRCLED + ansi.SGR}
OVERLINED :: Color{ansi.CSI + ansi.OVERLINED + ansi.SGR}
NO_FRAME_ENCIRCLE :: Color{ansi.CSI + ansi.NO_FRAME_ENCIRCLE + ansi.SGR}
NO_OVERLINE :: Color{ansi.CSI + ansi.NO_OVERLINE + ansi.SGR}


BRIGHT_BLACK :: Color{ansi.CSI + ansi.FG_BRIGHT_BLACK + ansi.SGR}
BRIGHT_RED :: Color{ansi.CSI + ansi.FG_BRIGHT_RED + ansi.SGR}
BRIGHT_GREEN :: Color{ansi.CSI + ansi.FG_BRIGHT_GREEN + ansi.SGR}
BRIGHT_YELLOW :: Color{ansi.CSI + ansi.FG_BRIGHT_YELLOW + ansi.SGR}
BRIGHT_BLUE :: Color{ansi.CSI + ansi.FG_BRIGHT_BLUE + ansi.SGR}
BRIGHT_MAGENTA :: Color{ansi.CSI + ansi.FG_BRIGHT_MAGENTA + ansi.SGR}
BRIGHT_CYAN :: Color{ansi.CSI + ansi.FG_BRIGHT_CYAN + ansi.SGR}
BRIGHT_WHITE :: Color{ansi.CSI + ansi.FG_BRIGHT_WHITE + ansi.SGR}

BG_BRIGHT_BLACK :: Color{ansi.CSI + ansi.BG_BRIGHT_BLACK + ansi.SGR}
BG_BRIGHT_RED :: Color{ansi.CSI + ansi.BG_BRIGHT_RED + ansi.SGR}
BG_BRIGHT_GREEN :: Color{ansi.CSI + ansi.BG_BRIGHT_GREEN + ansi.SGR}
BG_BRIGHT_YELLOW :: Color{ansi.CSI + ansi.BG_BRIGHT_YELLOW + ansi.SGR}
BG_BRIGHT_BLUE :: Color{ansi.CSI + ansi.BG_BRIGHT_BLUE + ansi.SGR}
BG_BRIGHT_MAGENTA :: Color{ansi.CSI + ansi.BG_BRIGHT_MAGENTA + ansi.SGR}
BG_BRIGHT_CYAN :: Color{ansi.CSI + ansi.BG_BRIGHT_CYAN + ansi.SGR}
BG_BRIGHT_WHITE :: Color{ansi.CSI + ansi.BG_BRIGHT_WHITE + ansi.SGR}
