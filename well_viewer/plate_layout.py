"""96-well plate row/column constants and shared well palette.

Extracted from ``well_viewer.runtime_app`` so that controllers and views can
reach plate geometry without importing the GUI monolith.
"""

from __future__ import annotations

from ui.theme import (
    CLR_SUCCESS,
    WELL_COLOR_1,
    WELL_COLOR_2,
    WELL_COLOR_3,
    WELL_COLOR_4,
    WELL_COLOR_5,
    WELL_COLOR_6,
    WELL_COLOR_7,
    WELL_COLOR_8,
    WELL_COLOR_9,
)


PLATE_ROWS = list("ABCDEFGH")
PLATE_COLS = [f"{c:02d}" for c in range(1, 13)]  # "01" … "12"

WELL_COLORS = [
    WELL_COLOR_1, WELL_COLOR_2, WELL_COLOR_3, CLR_SUCCESS, WELL_COLOR_4,
    WELL_COLOR_5, WELL_COLOR_6, WELL_COLOR_7, WELL_COLOR_8, WELL_COLOR_9,
]
