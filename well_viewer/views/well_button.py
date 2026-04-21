"""WellButton + build_plate_grid for the Qt port.

WellButton is a QPushButton subclass with a dynamic ``state`` property used by
the QSS stylesheet to color plate-map wells. It replaces the legacy
``WellLabel(tk.Label)`` workaround (which existed only because macOS tk.Button
ignored bg).

Wells are rendered as small fixed-size circles (the shape of real multi-well
plate wells). The well token is stored as an instance attribute and surfaced
as a tooltip rather than as a visible text label.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QSizePolicy, QWidget


# Well button dimensions (px). Square so border-radius = WELL_SIZE/2 renders a
# true circle.
WELL_SIZE = 18


class WellButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        # Keep the button text empty so the plate-map shows pure circles; the
        # token lives as an attribute and a tooltip for accessibility.
        super().__init__("", parent)
        self._tok = text
        self.setObjectName("WellButton")
        self.setFlat(True)
        self.setCursor(Qt.ArrowCursor)
        self.setFixedSize(WELL_SIZE, WELL_SIZE)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolTip(text)
        self._state = "empty"
        self.setProperty("state", self._state)

    @property
    def tok(self) -> str:
        return self._tok

    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def state(self) -> str:  # type: ignore[override]
        return self._state


def build_plate_grid(
    parent: QWidget,
    btn_store: Dict[str, WellButton],
    *,
    row_start: int = 1,
    col_header_row: int = 0,
    on_click: Optional[Callable[[str], None]] = None,
) -> QGridLayout:
    """Populate *parent* with an 8×12 header + well-button grid.

    Returns the layout for further configuration by the caller.
    """
    from well_viewer.runtime_app import _PLATE_ROWS, _PLATE_COLS

    layout = parent.layout()
    if layout is None:
        layout = QGridLayout(parent)
        parent.setLayout(layout)
    # Uniform padding around every plate-map (sidebar, replicate, bar-group,
    # stats, preview). Keep this the only place that sets plate-map margins
    # so the visual padding stays consistent across tabs.
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setHorizontalSpacing(2)
    layout.setVerticalSpacing(2)

    # corner
    layout.addWidget(QLabel("", parent), col_header_row, 0)
    # column headers
    for ci, col in enumerate(_PLATE_COLS):
        lbl = QLabel(str(int(col)), parent)
        lbl.setObjectName("Muted")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl, col_header_row, ci + 1)

    # row headers + wells
    for ri, row_ltr in enumerate(_PLATE_ROWS):
        rl = QLabel(row_ltr, parent)
        rl.setObjectName("Muted")
        rl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(rl, ri + row_start, 0)
        for ci, col in enumerate(_PLATE_COLS):
            tok = f"{row_ltr}{col}"
            btn = WellButton(tok, parent)
            btn.setEnabled(False)
            if on_click is not None:
                btn.clicked.connect(lambda _=False, t=tok: on_click(t))
            layout.addWidget(btn, ri + row_start, ci + 1, Qt.AlignCenter)
            btn_store[tok] = btn

    layout.setColumnStretch(0, 0)
    for ci in range(1, len(_PLATE_COLS) + 1):
        layout.setColumnStretch(ci, 1)
    return layout
