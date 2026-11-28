"""
Show an example of the four-pane game screen with placeholder data.

Run from src/:  python example_screen.py
Shows a generated starting map; the human entrance opens after 60 seconds.
Add --tiles to show a map containing every land type instead.

Type a line and press Enter to add it to the Events pane.
Type "quit" or press Ctrl-C to exit.
"""

import curses
import random
import sys
import time

import classes
import const
import map_generation
from display import GameScreen

STONE_GAP_LENGTH = 3


def build_example_map(height=15, width=40):
    """
    Build a map showing every land type in const.LAND_TYPES.

    Mountains border the map with a 3-tile stone gap at a random spot, the
    interior is grassland, and every other land type is placed in the upper
    left, each with one tile of grassland around it.
    """
    game_map = classes.Map(height, width)  # mountain border, grassland inside
    _add_stone_gap(game_map)

    remaining = [
        land_type
        for land_type in const.LAND_TYPES
        if land_type not in (const.MOUNTAIN, const.GRASSLAND, const.STONE)
    ]
    # Start at (2, 2): row/column 0 is mountain and row/column 1 is the
    # grassland spacer. Stepping by 2 leaves one grassland tile between each.
    row, col = 2, 2
    for land_type in remaining:
        if col > width - 3:  # would touch the right-hand mountains; wrap
            row, col = row + 2, 2
        if row > height - 3:
            raise ValueError(f"A {height}x{width} map is too small for every land type")
        game_map.tiles[row][col].set_land_type(land_type)
        col += 2
    return game_map


def _add_stone_gap(game_map):
    """
    Replace 3 consecutive mountain tiles on a random side with stone.
    Corners are never used, so the gap always sits on a single straight wall.
    """
    height, width = game_map.height, game_map.width
    side = random.choice(["top", "bottom", "left", "right"])
    side_length = width if side in ("top", "bottom") else height
    if side_length - 2 < STONE_GAP_LENGTH:
        raise ValueError("Map is too small for the stone gap")

    # The gap's last tile must stop before the far corner (index side_length - 1).
    start = random.randint(1, side_length - 1 - STONE_GAP_LENGTH)
    for offset in range(start, start + STONE_GAP_LENGTH):
        if side == "top":
            tile = game_map.tiles[0][offset]
        elif side == "bottom":
            tile = game_map.tiles[height - 1][offset]
        elif side == "left":
            tile = game_map.tiles[offset][0]
        else:
            tile = game_map.tiles[offset][width - 1]
        tile.set_land_type(const.STONE)


def main(stdscr, show_all_tiles=False):
    if show_all_tiles:
        game_map, entrance_corner = build_example_map(), None
    else:
        game_map, elf_corner = map_generation.generate_map(15, 40)
        entrance_corner = map_generation.opposite_corner(game_map, elf_corner)
    start_time = time.monotonic()
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
        elapsed = time.monotonic() - start_time
        if entrance_corner and elapsed >= map_generation.HUMAN_ENTRANCE_DELAY_SECONDS:
            opened = map_generation.open_human_entrance(game_map, entrance_corner)
            events.append(f"Mountain tiles at {opened} turned to stone.")
            entrance_corner = None  # only happens once

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
        curses.wrapper(main, "--tiles" in sys.argv[1:])
    except KeyboardInterrupt:
        pass
