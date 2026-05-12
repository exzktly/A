"""WellPlateSelector — the 8×12 microplate selector from the v2 mockup.

Composes a custom-painted plate grid (clickable A–H row letters and 1–12 column
numbers act as whole-row / whole-column toggles) with an action row
(``All 96`` / ``Invert`` / ``Clear``). Selected wells render as "lit chips":
a per-trace radial gradient keyed to the well's position in the selection, with
a faint top highlight.

The plate IS the legend — well A01 always carries trace colour 0, A02 trace 1,
etc. (selection is colour-ordered by plate position), matching the mockup.

API
---
* ``selectedWells`` — Qt property: list of well IDs like ``"A01"`` (sorted).
  Also ``selectedWellIds()`` / ``setSelectedWellIds(iterable)``.
* ``selectAll()`` / ``clearSelection()`` / ``invertSelection()``.
* ``selectionChanged(list)`` — emitted with the new sorted well-ID list.

All metrics derive from the widget font / available size — no hardcoded device
pixels — so the plate is DPI / font-scaling aware. Styled from ``theme`` tokens.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Property, QRectF, QSize, Qt, Signal  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QBrush, QColor, QPainter, QPen, QRadialGradient,
)
from PySide6.QtWidgets import (  # noqa: E402
    QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402
from widgets._support import with_alpha  # noqa: E402

_ROW_LETTERS = "ABCDEFGH"
_N_ROWS = 8
_N_COLS = 12


def _well_id(row: int, col: int) -> str:
    return f"{_ROW_LETTERS[row]}{col + 1:02d}"


def _parse_well_id(well_id: str) -> tuple[int, int] | None:
    well_id = str(well_id).strip().upper()
    if len(well_id) < 2 or well_id[0] not in _ROW_LETTERS:
        return None
    try:
        col = int(well_id[1:]) - 1
    except ValueError:
        return None
    row = _ROW_LETTERS.index(well_id[0])
    if 0 <= row < _N_ROWS and 0 <= col < _N_COLS:
        return row, col
    return None


class _PlateGrid(QWidget):
    """The painted grid + headers. Selection state lives here."""

    selectionChanged = Signal()
    rowHeaderClicked = Signal(int)
    colHeaderClicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PlateGrid")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

        self._selected: dict[tuple[int, int], int] = {}  # (row, col) -> trace idx
        self._hover_cell: tuple[int, int] | None = None
        self._hover_row: int | None = None
        self._hover_col: int | None = None

    # ── geometry (all font / size relative) ──────────────────────────────
    def _label_extent(self) -> float:
        return self.fontMetrics().height() * 1.7

    def _metrics(self) -> tuple[float, float, float, float]:
        """Return (label_extent, cell_size, grid_origin_x, grid_origin_y)."""
        lab = self._label_extent()
        avail_w = max(1.0, self.width() - lab - 2.0)
        avail_h = max(1.0, self.height() - lab - 2.0)
        cell = max(1.0, min(avail_w / _N_COLS, avail_h / _N_ROWS))
        total_w = lab + cell * _N_COLS
        total_h = lab + cell * _N_ROWS
        ox = (self.width() - total_w) / 2.0 + lab
        oy = (self.height() - total_h) / 2.0 + lab
        return lab, cell, ox, oy

    def _cell_rect(self, row: int, col: int) -> QRectF:
        _lab, cell, ox, oy = self._metrics()
        return QRectF(ox + col * cell, oy + row * cell, cell, cell)

    def _well_rect(self, row: int, col: int) -> QRectF:
        cr = self._cell_rect(row, col)
        d = cr.width() * 0.80
        cx, cy = cr.center().x(), cr.center().y()
        return QRectF(cx - d / 2.0, cy - d / 2.0, d, d)

    def sizeHint(self) -> QSize:
        u = max(20, round(self.fontMetrics().height() * 1.7))
        lab = round(self._label_extent())
        return QSize(lab + u * _N_COLS, lab + u * _N_ROWS)

    def minimumSizeHint(self) -> QSize:
        u = max(12, round(self.fontMetrics().height() * 1.1))
        lab = round(self.fontMetrics().height() * 1.4)
        return QSize(lab + u * _N_COLS, lab + u * _N_ROWS)

    # ── selection helpers ────────────────────────────────────────────────
    def _recolor(self) -> None:
        palette_n = len(theme.Colors.trace)
        for i, key in enumerate(sorted(self._selected)):
            self._selected[key] = i % palette_n

    def _changed(self) -> None:
        self._recolor()
        self.updateGeometry()
        self.update()
        self.selectionChanged.emit()

    def selected_ids(self) -> list[str]:
        return [_well_id(r, c) for (r, c) in sorted(self._selected)]

    def set_ids(self, ids) -> None:
        new: dict[tuple[int, int], int] = {}
        for wid in ids or ():
            parsed = _parse_well_id(wid) if not isinstance(wid, tuple) else wid
            if parsed is not None and 0 <= parsed[0] < _N_ROWS and 0 <= parsed[1] < _N_COLS:
                new[parsed] = 0
        if new == self._selected:
            return
        self._selected = new
        self._changed()

    def toggle_well(self, row: int, col: int) -> None:
        key = (row, col)
        if key in self._selected:
            del self._selected[key]
        else:
            self._selected[key] = 0
        self._changed()

    def toggle_row(self, row: int) -> None:
        keys = [(row, c) for c in range(_N_COLS)]
        if all(k in self._selected for k in keys):
            for k in keys:
                self._selected.pop(k, None)
        else:
            for k in keys:
                self._selected[k] = 0
        self._changed()

    def toggle_col(self, col: int) -> None:
        keys = [(r, col) for r in range(_N_ROWS)]
        if all(k in self._selected for k in keys):
            for k in keys:
                self._selected.pop(k, None)
        else:
            for k in keys:
                self._selected[k] = 0
        self._changed()

    def set_all(self, on: bool) -> None:
        if on:
            new = {(r, c): 0 for r in range(_N_ROWS) for c in range(_N_COLS)}
        else:
            new = {}
        if new == self._selected:
            return
        self._selected = new
        self._changed()

    def invert(self) -> None:
        new = {
            (r, c): 0
            for r in range(_N_ROWS) for c in range(_N_COLS)
            if (r, c) not in self._selected
        }
        self._selected = new
        self._changed()

    # ── input ────────────────────────────────────────────────────────────
    def _hit(self, x: float, y: float):
        """Return ('well', r, c) | ('row', r) | ('col', c) | None."""
        _lab, cell, ox, oy = self._metrics()
        col = int((x - ox) // cell) if x >= ox else -1
        row = int((y - oy) // cell) if y >= oy else -1
        in_cols = 0 <= col < _N_COLS
        in_rows = 0 <= row < _N_ROWS
        if y < oy and in_cols:
            return ("col", col)
        if x < ox and in_rows:
            return ("row", row)
        if in_rows and in_cols:
            return ("well", row, col)
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        pos = event.position()
        hit = self._hit(pos.x(), pos.y())
        if hit is None:
            return
        if hit[0] == "well":
            self.toggle_well(hit[1], hit[2])
        elif hit[0] == "row":
            self.rowHeaderClicked.emit(hit[1])
        elif hit[0] == "col":
            self.colHeaderClicked.emit(hit[1])

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        hit = self._hit(pos.x(), pos.y())
        cell = row = col = None
        if hit is not None:
            if hit[0] == "well":
                cell = (hit[1], hit[2])
            elif hit[0] == "row":
                row = hit[1]
            elif hit[0] == "col":
                col = hit[1]
        if (cell, row, col) != (self._hover_cell, self._hover_row, self._hover_col):
            self._hover_cell, self._hover_row, self._hover_col = cell, row, col
            self.update()

    def leaveEvent(self, _event) -> None:  # noqa: N802
        if (self._hover_cell, self._hover_row, self._hover_col) != (None, None, None):
            self._hover_cell = self._hover_row = self._hover_col = None
            self.update()

    # ── painting ─────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        c = theme.Colors
        traces = theme.Colors.trace
        lab, cell, ox, oy = self._metrics()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setFont(self.font())

        # Column numbers (1–12) along the top.
        for ci in range(_N_COLS):
            rect = QRectF(ox + ci * cell, oy - lab, cell, lab)
            hot = (self._hover_col == ci)
            p.setPen(QColor(c.text_primary if hot else c.text_muted))
            p.drawText(rect, int(Qt.AlignCenter), str(ci + 1))

        # Row letters (A–H) down the left.
        for ri in range(_N_ROWS):
            rect = QRectF(ox - lab, oy + ri * cell, lab, cell)
            hot = (self._hover_row == ri)
            p.setPen(QColor(c.text_primary if hot else c.text_muted))
            p.drawText(rect, int(Qt.AlignCenter), _ROW_LETTERS[ri])

        # Wells.
        for ri in range(_N_ROWS):
            for ci in range(_N_COLS):
                key = (ri, ci)
                wr = self._well_rect(ri, ci)
                hovered = (
                    self._hover_cell == key
                    or self._hover_row == ri
                    or self._hover_col == ci
                )
                if key in self._selected:
                    base = QColor(traces[self._selected[key] % len(traces)])
                    grad = QRadialGradient(
                        wr.center().x() - wr.width() * 0.15,
                        wr.center().y() - wr.height() * 0.20,
                        wr.width() * 0.75,
                    )
                    grad.setColorAt(0.0, base.lighter(150))
                    grad.setColorAt(0.55, base)
                    grad.setColorAt(1.0, base.darker(135))
                    p.setBrush(QBrush(grad))
                    p.setPen(QPen(base.darker(170) if not hovered else QColor(c.text_primary),
                                  max(1.0, wr.width() * 0.04)))
                    p.drawEllipse(wr)
                    # Faint top inset highlight (the "lit chip" sheen).
                    hl = QRectF(wr).adjusted(
                        wr.width() * 0.16, wr.height() * 0.10,
                        -wr.width() * 0.16, -wr.height() * 0.46,
                    )
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(with_alpha("#FFFFFF", 0.30), max(1.0, wr.width() * 0.06)))
                    p.drawArc(hl, 20 * 16, 140 * 16)
                else:
                    p.setBrush(QColor(c.hover if hovered else c.panel_elevated))
                    p.setPen(QPen(QColor(c.border_strong if hovered else c.border),
                                  max(1.0, wr.width() * 0.04)))
                    p.drawEllipse(wr)
        p.end()


class WellPlateSelector(QWidget):
    """8×12 plate selector with header toggles and All / Invert / Clear actions."""

    selectionChanged = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("WellPlateSelector")
        self.setAttribute(Qt.WA_StyledBackground, True)

        m = theme.Spacing.sm
        root = QVBoxLayout(self)
        root.setContentsMargins(m, m, m, m)
        root.setSpacing(theme.Spacing.sm)

        self._grid = _PlateGrid(self)
        self._grid.selectionChanged.connect(self._on_grid_changed)
        self._grid.rowHeaderClicked.connect(self._grid.toggle_row)
        self._grid.colHeaderClicked.connect(self._grid.toggle_col)
        root.addWidget(self._grid, 1)

        actions = QHBoxLayout()
        actions.setSpacing(theme.Spacing.sm)
        self._btn_all = QPushButton("All 96")
        self._btn_all.setToolTip("Select all 96 wells")
        self._btn_invert = QPushButton("Invert")
        self._btn_invert.setToolTip("Invert the current selection")
        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setObjectName("Danger")
        self._btn_clear.setToolTip("Clear the selection")
        for b in (self._btn_all, self._btn_invert, self._btn_clear):
            b.setCursor(Qt.PointingHandCursor)
            actions.addWidget(b)
        actions.addStretch(1)
        root.addLayout(actions)

        self._btn_all.clicked.connect(self.selectAll)
        self._btn_invert.clicked.connect(self.invertSelection)
        self._btn_clear.clicked.connect(self.clearSelection)

        self.setStyleSheet(self._build_qss())

    # ── public API ───────────────────────────────────────────────────────
    def selectAll(self) -> None:
        self._grid.set_all(True)

    def clearSelection(self) -> None:
        self._grid.set_all(False)

    def invertSelection(self) -> None:
        self._grid.invert()

    def selectedWellIds(self) -> list[str]:
        return self._grid.selected_ids()

    def setSelectedWellIds(self, ids) -> None:
        self._grid.set_ids(ids)

    def _get_selected(self) -> list:
        return self._grid.selected_ids()

    def _set_selected(self, ids) -> None:
        self._grid.set_ids(ids)

    selectedWells = Property(list, _get_selected, _set_selected)

    # ── internals ────────────────────────────────────────────────────────
    def _on_grid_changed(self) -> None:
        self.selectionChanged.emit(self._grid.selected_ids())

    def _build_qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        return f"""
        #WellPlateSelector {{
            background-color: {c.panel};
            border: 1px solid {c.border_subtle};
            border-radius: {r.md}px;
        }}
        #PlateGrid {{ background: transparent; }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("WellPlateSelector — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)

    title = QLabel("WellPlateSelector")
    title.setObjectName("Title")
    lay.addWidget(title)

    plate = WellPlateSelector()
    plate.setSelectedWellIds(["A01", "A02", "B01", "C03", "C04", "D06", "H12"])
    lay.addWidget(plate, 1)

    echo = QLabel()
    echo.setObjectName("Secondary")
    echo.setWordWrap(True)

    def _show(ids):
        echo.setText(f"{len(ids)} selected: {', '.join(ids) if ids else '(none)'}")

    plate.selectionChanged.connect(_show)
    _show(plate.selectedWellIds())
    lay.addWidget(echo)

    root.resize(620, 460)
    root.show()
    _sys.exit(app.exec())
