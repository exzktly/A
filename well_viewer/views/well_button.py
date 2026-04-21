"""WellButton + build_plate_grid for the Qt port.

WellButton is a QPushButton subclass with a dynamic ``state`` property used by
the QSS stylesheet to color plate-map wells. It replaces the legacy
``WellLabel(tk.Label)`` workaround (which existed only because macOS tk.Button
ignored bg).

Wells are rendered as small fixed-size circles (the shape of real multi-well
plate wells). The well token is stored as an instance attribute and surfaced
as a tooltip rather than as a visible text label.

Qt's QSS engine collapses ``border-style: outset`` / ``inset`` into plain
``solid`` once ``border-radius`` is set, so the 3D emboss/depress cue is
drawn manually in ``paintEvent`` on top of the base QSS render.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
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
        # Independent 3D cue, driven either by set_state() (preview picker) or
        # by _style_plate_button (inline-styled replicate wells). Values:
        # "none" | "raised" | "depressed".
        self._emboss = "none"

    @property
    def tok(self) -> str:
        return self._tok

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.setProperty("state", state)
            self.style().unpolish(self)
            self.style().polish(self)
        # Keep the 3D cue in sync with the symbolic state.
        if state == "empty":
            self.set_emboss("none")
        elif state == "selected":
            self.set_emboss("depressed")
        else:
            self.set_emboss("raised")

    def set_emboss(self, mode: str) -> None:
        if mode == self._emboss:
            return
        self._emboss = mode
        self.update()

    def state(self) -> str:  # type: ignore[override]
        return self._state

    def paintEvent(self, event) -> None:  # type: ignore[override]
        # Render the QSS-styled base first (fill + smooth black border).
        super().paintEvent(event)

        if self._emboss == "none" or not self.isEnabled():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Paint a highlight arc on one half and a shadow arc on the other to
        # simulate a raised (unselected) or sunken (selected) 3D edge just
        # inside the black border. Inset so the arcs sit inside the border.
        inset = 2.0
        rect = QRectF(inset, inset,
                      float(self.width()) - 2 * inset,
                      float(self.height()) - 2 * inset)

        if self._emboss == "depressed":
            # Shadow along the top-left quadrant,
            # highlight along the bottom-right quadrant.
            top_color = QColor(0, 0, 0, 190)
            bot_color = QColor(255, 255, 255, 110)
        else:
            # Raised: highlight along the top-left quadrant,
            # shadow along the bottom-right quadrant.
            top_color = QColor(255, 255, 255, 210)
            bot_color = QColor(0, 0, 0, 150)

        pen = QPen()
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.FlatCap)

        # Qt arc angles are in 1/16th of a degree, measured CCW from 3 o'clock.
        # Top-left quadrant spans 90°–180° (upper-left arc of the circle).
        pen.setColor(top_color)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, 90 * 16)

        # Bottom-right quadrant spans 270°–360° (lower-right arc).
        pen.setColor(bot_color)
        painter.setPen(pen)
        painter.drawArc(rect, 270 * 16, 90 * 16)

        painter.end()


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
