"""
Generate the starting map, following notes/map_generation.md.

Corners are given as the (row, col) of the corner mountain tile, e.g. (0, 0)
for the top left.
"""

import math
import random
from dataclasses import dataclass

import classes
import const

# Tunable layout values. These shape the map; they are not from the notes.
FOREST_RADIUS_FRACTION = 0.6  # forest arc reaches this fraction of the map's height/width
GENESIS_DISTANCE_FRACTION = 0.3  # genesis tree sits this far from the corner, along the arc's diagonal
FRUIT_TREE_COUNT_RANGE = (3, 5)  # inclusive
GRASSLAND_FRACTION = 0.3  # chance each forest tile stays grassland
MAPLE_FRACTION = 0.3  # chance each tree tile in the forest is maple rather than oak
HUMAN_ENTRANCE_DELAY_SECONDS = 5  # when open_human_entrance() should be called

WATER_FRACTION = 0.05  # share of the map interior that is water (source included)
STREAM_COUNT_RANGE = (3, 4)  # inclusive; how many streams the river splits into
LAST_FORK_FRACTION = 0.45  # all forks happen before the river uses this share of its water
FORK_ANGLE = math.pi / 4  # each branch of a fork turns this far from the parent's heading
WIND_STEP = 0.5  # radians a stream's heading may turn per tile
WIND_LIMIT = 1.2  # radians a stream may drift from the heading it started with

NEIGHBOUR_OFFSETS = [
    (d_row, d_col)
    for d_row in (-1, 0, 1)
    for d_col in (-1, 0, 1)
    if (d_row, d_col) != (0, 0)
]


def corners(game_map):
    """
    Return the (row, col) of all four corner tiles.
    """
    last_row, last_col = game_map.height - 1, game_map.width - 1
    return [(0, 0), (0, last_col), (last_row, 0), (last_row, last_col)]


def opposite_corner(game_map, corner):
    row, col = corner
    return (game_map.height - 1 - row, game_map.width - 1 - col)


def generate_map(height, width, rng=None):
    """
    Build the starting map: a mountain border, grassland interior, a river,
    and the elves' forest in a random corner.

    Returns (game_map, elf_corner). Pass a seeded random.Random as `rng` to
    get the same map every time.
    """
    rng = rng or random.Random()
    game_map = classes.Map(height, width)  # mountain border, grassland inside
    elf_corner = rng.choice(corners(game_map))
    genesis = _genesis_position(game_map, elf_corner)
    # The river goes first so the forest grows around it.
    _add_river(game_map, elf_corner, genesis, rng)
    _grow_forest(game_map, elf_corner, genesis, rng)
    return game_map, elf_corner


# Forest


def _forest_radii(game_map):
    """
    Radii of the forest's quarter-ellipse, so the arc scales with the map's
    shape rather than being a circle on a wide map.
    """
    return (
        FOREST_RADIUS_FRACTION * game_map.height,
        FOREST_RADIUS_FRACTION * game_map.width,
    )


def _genesis_position(game_map, corner):
    """
    The genesis tree sits part-way along the diagonal from the corner into
    the forest.
    """
    corner_row, corner_col = corner
    radius_rows, radius_cols = _forest_radii(game_map)
    row_step = 1 if corner_row == 0 else -1  # direction from the corner inwards
    col_step = 1 if corner_col == 0 else -1
    return (
        _clamp(corner_row + row_step * round(GENESIS_DISTANCE_FRACTION * radius_rows), game_map.height),
        _clamp(corner_col + col_step * round(GENESIS_DISTANCE_FRACTION * radius_cols), game_map.width),
    )


def _grow_forest(game_map, corner, genesis, rng):
    corner_row, corner_col = corner
    radius_rows, radius_cols = _forest_radii(game_map)

    trees = []
    for row in range(1, game_map.height - 1):  # interior only; skip the border
        for col in range(1, game_map.width - 1):
            distance = (
                ((row - corner_row) / radius_rows) ** 2
                + ((col - corner_col) / radius_cols) ** 2
            )
            if distance > 1 or game_map.tiles[row][col].land_type != const.GRASSLAND:
                continue  # outside the arc, or already water
            # Some forest tiles stay grassland; the rest become oak or maple.
            if rng.random() < GRASSLAND_FRACTION:
                continue
            tree = const.MAPLE_TREES if rng.random() < MAPLE_FRACTION else const.OAK_TREES
            game_map.tiles[row][col].set_land_type(tree)
            trees.append((row, col))

    game_map.tiles[genesis[0]][genesis[1]].set_land_type(const.GENESIS_TREE)

    # Fruit trees: replace a few random oak or maple tiles.
    tree_tiles = [position for position in trees if position != genesis]
    fruit_count = rng.randint(*FRUIT_TREE_COUNT_RANGE)
    if len(tree_tiles) < fruit_count:
        raise ValueError("Map is too small to fit the starting forest")
    for row, col in rng.sample(tree_tiles, fruit_count):
        game_map.tiles[row][col].set_land_type(const.FRUIT_TREES)


def _clamp(index, size):
    """
    Keep an index inside the map interior (never on the mountain border).
    """
    return max(1, min(index, size - 2))


# River


@dataclass
class _Stream:
    """
    One branch of the river while it is being carved.
    """

    path: list  # recent (row, col) tiles, oldest first; the last is the stream's head
    heading: float  # current direction in radians: 0 = right, pi/2 = down
    start_heading: float  # heading the branch began with; limits how far it winds
    length: int = 0  # tiles of river from the source to this stream's head


def _add_river(game_map, elf_corner, genesis, rng):
    """
    Place a water source at the middle of one of the two walls beside the
    elf corner, then carve flowing water away from it. The river forks into
    3-4 streams spread along its length. Streams end at a wall, or when the
    water budget runs out.
    """
    height, width = game_map.height, game_map.width
    corner_row, corner_col = elf_corner
    if rng.random() < 0.5:  # the top or bottom wall
        source = (1 if corner_row == 0 else height - 2, width // 2)
        inward = (1 if corner_row == 0 else -1, 0)
    else:  # the left or right wall
        source = (height // 2, 1 if corner_col == 0 else width - 2)
        inward = (0, 1 if corner_col == 0 else -1)
    game_map.tiles[source[0]][source[1]].set_land_type(const.WATER_SOURCE)

    water = {source}
    budget = max(2, round(WATER_FRACTION * (height - 2) * (width - 2)))
    stream_count = rng.randint(*STREAM_COUNT_RANGE)
    # Each fork adds one stream. Forks are evenly spaced over the first
    # LAST_FORK_FRACTION of the water, leaving the rest for the final streams
    # to grow. (Spacing them over all the water left the last streams tiny.)
    fork_count = stream_count - 1
    fork_at = [
        round(budget * LAST_FORK_FRACTION * k / fork_count)
        for k in range(1, fork_count + 1)
    ]

    heading = math.atan2(*inward)
    streams = [_Stream([source], heading, heading)]
    while streams and len(water) < budget:
        if fork_at and len(water) >= fork_at[0]:
            if _fork(game_map, rng.choice(streams), streams, water, genesis, rng):
                fork_at.pop(0)
        for stream in list(streams):  # copy: streams can end mid-loop
            if len(water) >= budget:
                break
            stream.heading = _wind(stream, rng)
            options = _next_tiles(game_map, stream, stream.heading, water, genesis)
            if not options:
                streams.remove(stream)  # boxed in; this stream ends here
                continue
            tiles, weights = zip(*options)
            next_tile = rng.choices(tiles, weights)[0]
            _flow(game_map, stream.path[-1], next_tile, water)
            stream.path = stream.path[-2:] + [next_tile]
            stream.length += 1
            # The source starts beside a wall, so ignore walls for a few tiles.
            if stream.length > 2 and _touches_wall(game_map, next_tile):
                streams.remove(stream)  # reached the valley wall


def _wind(stream, rng):
    """
    Nudge a stream's heading randomly, within WIND_LIMIT of where it started,
    which makes it meander.
    """
    heading = stream.heading + rng.uniform(-WIND_STEP, WIND_STEP)
    low, high = stream.start_heading - WIND_LIMIT, stream.start_heading + WIND_LIMIT
    return max(low, min(heading, high))


def _next_tiles(game_map, stream, heading, water, genesis):
    """
    Return [(tile, weight)] for each tile the stream could flow into next.

    A tile qualifies if it is in the interior, is not water or the genesis
    tree, lies ahead of `heading`, and touches no water except this stream's
    own recent tiles (so streams never merge or run alongside each other).
    Tiles closer to straight ahead get higher weights.
    """
    head_row, head_col = stream.path[-1]
    own_recent = set(stream.path)
    options = []
    for d_row, d_col in NEIGHBOUR_OFFSETS:
        tile = (head_row + d_row, head_col + d_col)
        row, col = tile
        if not (1 <= row <= game_map.height - 2 and 1 <= col <= game_map.width - 2):
            continue
        if tile in water or tile == genesis:
            continue
        alignment = math.cos(math.atan2(d_row, d_col) - heading)
        if alignment <= 0:  # sideways or backwards
            continue
        neighbours = {(row + r, col + c) for r, c in NEIGHBOUR_OFFSETS}
        if (neighbours & water) - own_recent:
            continue
        options.append((tile, alignment ** 3))
    return options


def _fork(game_map, stream, streams, water, genesis, rng):
    """
    Split `stream` into two branches turning FORK_ANGLE left and right.
    Returns False, changing nothing, if there is no room to fork here.
    """
    head = stream.path[-1]
    branches = []
    for turn in (-FORK_ANGLE, FORK_ANGLE):
        heading = stream.heading + turn
        options = _next_tiles(game_map, stream, heading, water, genesis)
        branches.append((heading, [tile for tile, _ in options]))

    (left_heading, left_tiles), (right_heading, right_tiles) = branches
    # The two branch tiles must not touch each other, or they would merge.
    pairs = [
        (left, right)
        for left in left_tiles
        for right in right_tiles
        if max(abs(left[0] - right[0]), abs(left[1] - right[1])) >= 2
    ]
    if not pairs:
        return False

    left, right = rng.choice(pairs)
    streams.remove(stream)
    for tile, heading in ((left, left_heading), (right, right_heading)):
        _flow(game_map, head, tile, water)
        streams.append(
            _Stream(stream.path[-2:] + [tile], heading, heading, stream.length + 1)
        )
    return True


def _flow(game_map, from_tile, to_tile, water):
    """
    Make `to_tile` flowing water and point `from_tile` at it.
    """
    game_map.tiles[to_tile[0]][to_tile[1]].set_land_type(const.FLOWING_WATER)
    direction = (to_tile[0] - from_tile[0], to_tile[1] - from_tile[1])
    game_map.tiles[from_tile[0]][from_tile[1]].flow_directions.append(direction)
    water.add(to_tile)


def _touches_wall(game_map, tile):
    row, col = tile
    return row in (1, game_map.height - 2) or col in (1, game_map.width - 2)


# Events


def open_human_entrance(game_map, corner):
    """
    Turn 3 mountain tiles at `corner` into stone: the corner tile and its two
    neighbours along the walls. Call this with the corner opposite the elves,
    HUMAN_ENTRANCE_DELAY_SECONDS into the game.

    Returns the (row, col) positions that changed.
    """
    row, col = corner
    row_step = 1 if row == 0 else -1
    col_step = 1 if col == 0 else -1
    positions = [(row, col), (row + row_step, col), (row, col + col_step)]
    for r, c in positions:
        game_map.tiles[r][c].set_land_type(const.STONE)
    return positions
