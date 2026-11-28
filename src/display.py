"""
Display game objects and classes.

The game screen is split into four curses windows:

    +----------------------+----------+
    | Map                  | Events   |
    |                      |          |
    +----------------------+          |
    | Stats                |          |
    +----------------------+          |
    | > input              |          |
    +----------------------+----------+

Display code only reads game state; it never modifies a Map.
"""

import curses
import textwrap

import classes
import const

# Text colours as (256-colour index, basic 8-colour fallback). Most terminals
# support 256 colours; the fallback covers ones that only have the basic 8,
# which have no gray, brown or pink.
# 256-colour chart: https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit
DARK_GRAY = (240, curses.COLOR_WHITE)
GRAY = (244, curses.COLOR_WHITE)
SILVER = (250, curses.COLOR_WHITE)
GREEN = (34, curses.COLOR_GREEN)
BLUE = (33, curses.COLOR_BLUE)
BROWN = (130, curses.COLOR_YELLOW)
OLIVE_GREEN = (64, curses.COLOR_GREEN)
DARK_PINK = (162, curses.COLOR_MAGENTA)

# How each land type is drawn: (character, text colour or None for default).
# Characters and colours come from notes/tiles.md.
GLYPHS = {
    const.MOUNTAIN: ("M", DARK_GRAY),
    const.GRASSLAND: (".", GREEN),
    const.FLOWING_WATER: ("≈", BLUE),
    const.WATER_SOURCE: ("O", BLUE),
    const.STONE: ("#", GRAY),
    const.DIRT: (".", BROWN),
    const.OAK_TREES: ("Ʌ", OLIVE_GREEN),
    const.FRUIT_TREES: ("T", DARK_PINK),
    const.GENESIS_TREE: ("@", SILVER),
    const.MAPLE_TREES: ("Y", GREEN),
}
UNKNOWN_GLYPH = ("?", None)


def tile_glyph(tile: classes.Tile):
    """
    Return the (character, colour) pair used to draw a tile.
    """
    return GLYPHS.get(tile.land_type, UNKNOWN_GLYPH)


def map_to_string(map: classes.Map):
    """
    Turns a map object into a string (characters only, no colour).
    """
    return "\n".join(
        "".join(tile_glyph(tile)[0] for tile in row) for row in map.tiles
    )


class GameScreen:
    """
    Owns the curses windows and draws game state into them.

    Call draw() every frame, then poll_input(), which waits briefly for a key
    and returns a completed line when the user presses Enter.
    """

    INPUT_HEIGHT = 3  # border + one line of text + border
    STATS_HEIGHT = 7  # border + five lines of stats + border
    MIN_HEIGHT = INPUT_HEIGHT + STATS_HEIGHT + 4
    MIN_WIDTH = 40
    INPUT_TIMEOUT_MS = 100  # how long poll_input() waits for a key

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.input_buffer = ""
        self._color_attrs = {}
        self._setup_curses()
        self._build_windows()

    def _setup_curses(self):
        try:
            curses.curs_set(1)  # show the cursor in the input pane
        except curses.error:
            pass  # some terminals can't change cursor visibility

        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1  # -1 means the terminal's own background
            except curses.error:
                background = curses.COLOR_BLACK
            # curses colours are used in numbered "pairs" (foreground and
            # background), so register one pair per colour in GLYPHS.
            colors = sorted({c for _, c in GLYPHS.values() if c is not None})
            for pair_id, color in enumerate(colors, start=1):
                color_256, color_8 = color
                foreground = color_256 if curses.COLORS >= 256 else color_8
                curses.init_pair(pair_id, foreground, background)
                self._color_attrs[color] = curses.color_pair(pair_id)

        # stdscr reads keys while the terminal is too small for the layout.
        self.stdscr.keypad(True)
        self.stdscr.timeout(self.INPUT_TIMEOUT_MS)

    def _build_windows(self):
        """
        Create the four windows sized to the current terminal. Called again
        whenever the terminal is resized.
        """
        height, width = self.stdscr.getmaxyx()
        self.stdscr.clear()  # wipe leftovers from the previous layout
        self.stdscr.noutrefresh()

        self.too_small = height < self.MIN_HEIGHT or width < self.MIN_WIDTH
        if self.too_small:
            return

        left_width = width * 2 // 3
        map_height = height - self.STATS_HEIGHT - self.INPUT_HEIGHT

        # curses.newwin(rows, cols, top_y, left_x)
        self.map_win = curses.newwin(map_height, left_width, 0, 0)
        self.stats_win = curses.newwin(
            self.STATS_HEIGHT, left_width, map_height, 0
        )
        self.input_win = curses.newwin(
            self.INPUT_HEIGHT, left_width, map_height + self.STATS_HEIGHT, 0
        )
        self.events_win = curses.newwin(height, width - left_width, 0, left_width)

        # keypad() turns arrow, backspace and resize keys into single codes.
        self.input_win.keypad(True)
        # timeout() makes getch() give up after a moment instead of blocking,
        # so the screen keeps updating while nobody is typing.
        self.input_win.timeout(self.INPUT_TIMEOUT_MS)

    # Drawing

    def draw(self, game_map: classes.Map, stats: dict, events: list):
        """
        Redraw every pane from the given game state.
        """
        if self.too_small:
            self._draw_too_small()
            return

        self._draw_map(game_map)
        self._draw_stats(stats)
        self._draw_events(events)
        self._draw_input()

        # noutrefresh() stages each window and doupdate() pushes them to the
        # terminal in one go, which avoids flicker. The input window goes
        # last so the cursor ends up there.
        for win in (self.map_win, self.stats_win, self.events_win, self.input_win):
            win.noutrefresh()
        curses.doupdate()

    @staticmethod
    def _frame(win, title):
        """
        Clear a window, draw its border and title, and return its inner size.
        """
        win.erase()
        win.box()
        win.addstr(0, 2, f" {title} ")
        height, width = win.getmaxyx()
        return height - 2, width - 2

    def _draw_map(self, game_map):
        rows, cols = self._frame(self.map_win, "Map")
        # Maps larger than the window are clipped at the bottom and right.
        for y, row in enumerate(game_map.tiles[:rows]):
            for x, tile in enumerate(row[:cols]):
                char, color = tile_glyph(tile)
                self.map_win.addch(y + 1, x + 1, char, self._color_attrs.get(color, 0))

    def _draw_stats(self, stats):
        rows, cols = self._frame(self.stats_win, "Stats")
        for y, (name, value) in enumerate(list(stats.items())[:rows]):
            self.stats_win.addstr(y + 1, 1, f"{name}: {value}"[:cols])

    def _draw_events(self, events):
        rows, cols = self._frame(self.events_win, "Events")
        lines = []
        for event in events:
            lines.extend(textwrap.wrap(event, cols) or [""])
        # Show the newest lines, with the latest at the bottom.
        for y, line in enumerate(lines[-rows:]):
            self.events_win.addstr(y + 1, 1, line)

    def _draw_input(self):
        _, cols = self._frame(self.input_win, "Input")
        # Keep the end of a long line in view, leaving a column for the cursor.
        visible = ("> " + self.input_buffer)[-(cols - 1):]
        self.input_win.addstr(1, 1, visible)
        self.input_win.move(1, 1 + len(visible))

    def _draw_too_small(self):
        message = f"Terminal too small: need {self.MIN_WIDTH}x{self.MIN_HEIGHT}"
        height, width = self.stdscr.getmaxyx()
        self.stdscr.erase()
        if height > 0 and width > 1:
            self.stdscr.addstr(0, 0, message[: width - 1])
        self.stdscr.refresh()

    # Input

    def poll_input(self):
        """
        Wait up to INPUT_TIMEOUT_MS for one key and update the input line.

        Returns the typed line when Enter is pressed, otherwise None.
        """
        win = self.stdscr if self.too_small else self.input_win
        key = win.getch()  # -1 means no key arrived before the timeout

        if key == curses.KEY_RESIZE:
            curses.update_lines_cols()
            self._build_windows()
        elif key in (curses.KEY_ENTER, 10, 13):
            line = self.input_buffer.strip()
            self.input_buffer = ""
            return line or None
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.input_buffer = self.input_buffer[:-1]
        elif 32 <= key < 127:  # printable ASCII
            self.input_buffer += chr(key)
        return None
