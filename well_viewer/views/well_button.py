"""WellButton + build_plate_grid for the Qt port.

WellButton is a QPushButton subclass with a dynamic ``state`` property used by
the QSS stylesheet to color plate-map wells. It replaces the legacy
``WellLabel(tk.Label)`` workaround (which existed only because macOS tk.Button
ignored bg).
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget

from well_viewer.plate_layout import PLATE_COLS, PLATE_ROWS


class WellButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("WellButton")
        self.setFlat(True)
        self.setCursor(Qt.ArrowCursor)
        self._state = "empty"
        self.setProperty("state", self._state)

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
    layout = parent.layout()
    if layout is None:
        layout = QGridLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(1)
    layout.setVerticalSpacing(1)

    # corner
    layout.addWidget(QLabel("", parent), col_header_row, 0)
    # column headers
    for ci, col in enumerate(PLATE_COLS):
        lbl = QLabel(str(int(col)), parent)
        lbl.setObjectName("Muted")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl, col_header_row, ci + 1)

    # row headers + wells
    for ri, row_ltr in enumerate(PLATE_ROWS):
        rl = QLabel(row_ltr, parent)
        rl.setObjectName("Muted")
        rl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(rl, ri + row_start, 0)
        for ci, col in enumerate(PLATE_COLS):
            tok = f"{row_ltr}{col}"
            btn = WellButton(tok, parent)
            btn.setEnabled(False)
            if on_click is not None:
                btn.clicked.connect(lambda _=False, t=tok: on_click(t))
            layout.addWidget(btn, ri + row_start, ci + 1)
            btn_store[tok] = btn

    layout.setColumnStretch(0, 0)
    for ci in range(1, len(PLATE_COLS) + 1):
        layout.setColumnStretch(ci, 1)
    return layout
