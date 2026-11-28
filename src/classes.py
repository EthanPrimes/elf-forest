"""
A file for storing all objects in the game.
"""

import const


class Cell:
    """
    Store data related to a cell of land.
    """

    def __init__(self, land_type: str, secondary_type: str = ""):
        self.land_type = land_type
        self.secondary_type = secondary_type

    def set_land_type(self, new_land_type):
        self.land_type = new_land_type

    def set_secondary_type(self, new_secondary_type):
        self.secondary_type = new_secondary_type


class Map:
    """
    Store Cells in a 2D grid of nested lists, indexed as cells[row][col].
    """

    def __init__(self, height: int, width: int, cells=None):
        assert height > 2 and width > 2
        self.height = height
        self.width = width
        if cells is None:
            self._generate_map(height, width)
        else:
            self.cells = cells

    def _generate_map(self, height, width):
        # Each Map is bordered by mountains; the interior defaults to grassland.
        # The border test goes in the value (a conditional expression), not as
        # a comprehension filter, so every row gets exactly `width` cells.
        self.cells = [
            [
                Cell(
                    const.MOUNTAIN
                    if i in (0, width - 1) or j in (0, height - 1)
                    else const.GRASSLAND
                )
                for i in range(width)
            ]
            for j in range(height)
        ]
