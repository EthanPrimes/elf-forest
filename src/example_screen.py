"""
Show an example of the four-pane game screen with placeholder data.

Run from src/:  python example_screen.py

Type a line and press Enter to add it to the Events pane.
Type "quit" or press Ctrl-C to exit.
"""

import curses

import classes
from display import GameScreen


def main(stdscr):
    game_map = classes.Map(15, 40)
    stats = {
        "Population": 0,
        "Resources": 0,
        "Lines entered": 0,
    }
    events = [
        "Example event.",
        "Example lore entry, long enough to show how text wraps inside the "
        "Events pane when it is wider than the pane.",
    ]

    screen = GameScreen(stdscr)
    while True:
        screen.draw(game_map, stats, events)
        line = screen.poll_input()
        if line is None:
            continue
        if line == "quit":
            break
        events.append(f"> {line}")
        stats["Lines entered"] += 1


if __name__ == "__main__":
    try:
        # wrapper() sets the terminal up for curses and always restores it
        # afterwards, even if the program crashes.
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
