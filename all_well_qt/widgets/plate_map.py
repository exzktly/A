"""PlateMapWidget — QGraphicsView + QGraphicsScene with custom WellItem.

Each well is a QGraphicsObject with embossed/depressed rendering, hover
scale, group color fills, and click/drag selection.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QObject
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsObject,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QWidget,
)

ROWS = list("ABCDEFGH")
COLS = [f"{i:02d}" for i in range(1, 13)]
WELL_SIZE = 22.0
WELL_GAP = 4.0
CELL = WELL_SIZE + WELL_GAP
ROW_LABEL_W = 20.0
COL_LABEL_H = 18.0
PAD = 10.0


@dataclass
class GroupSpec:
    color: str
    name: str
    id: str


class WellItem(QGraphicsObject):
    """Single well cell — 22×22 with emboss/depress paint."""

    clicked = Signal(str)
    entered = Signal(str)

    def __init__(self, well_id: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.well_id = well_id
        self._selected = False
        self._group_color: Optional[str] = None
        self._sunk_color = "#EEE5D4"
        self._ink_color = "#1A1915"
        self._dark_highlight = False

        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsObject.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, WELL_SIZE, WELL_SIZE)

    def paint(
        self,
        painter: QPainter,
        option,  # noqa: ANN001
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, WELL_SIZE - 1, WELL_SIZE - 1)

        # Base fill
        if self._group_color:
            base = QColor(self._group_color)
        else:
            base = QColor(self._sunk_color)
        painter.setBrush(QBrush(base))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(r)

        if self._selected:
            # Depressed: inner top shadow + outer ring
            inner_shadow = QColor(0, 0, 0, 60)
            inner_pen = QPen(inner_shadow, 2.5)
            inner_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(inner_pen)
            painter.drawArc(r.adjusted(2, 2, -2, -2), 30 * 16, 120 * 16)

            ring_pen = QPen(QColor(self._ink_color), 1.5)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(r)
        else:
            # Embossed: top highlight + bottom shadow
            if self._dark_highlight:
                hi_alpha = 20
                shadow_alpha = 127
            else:
                hi_alpha = 140
                shadow_alpha = 38

            hi_pen = QPen(QColor(255, 255, 255, hi_alpha), 1.0)
            hi_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(hi_pen)
            painter.drawArc(r.adjusted(1, 1, -1, -1), 45 * 16, 270 * 16)

            shadow_pen = QPen(QColor(0, 0, 0, shadow_alpha), 1.5)
            shadow_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(shadow_pen)
            painter.drawArc(r.adjusted(1, 1, -1, -1), 225 * 16, 270 * 16)

    def hoverEnterEvent(self, event) -> None:  # noqa: ANN001
        self.setScale(1.1)
        self.entered.emit(self.well_id)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: ANN001
        self.setScale(1.0)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.well_id)
        super().mousePressEvent(event)

    # ── state setters ────────────────────────────────────────────────
    def set_selected(self, v: bool) -> None:
        if self._selected != v:
            self._selected = v
            self.update()

    def set_group_color(self, color: Optional[str]) -> None:
        if self._group_color != color:
            self._group_color = color
            self.update()

    def set_palette_colors(
        self, sunk: str, ink: str, dark_highlight: bool
    ) -> None:
        self._sunk_color = sunk
        self._ink_color = ink
        self._dark_highlight = dark_highlight
        self.update()


class PlateMapWidget(QGraphicsView):
    """8×12 plate map.

    Signals
    -------
    selection_changed(set[str])
    hovered_well_changed(str | None)
    """

    selection_changed = Signal(object)
    hovered_well_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setObjectName("plateView")

        self._wells: dict[str, WellItem] = {}
        self._selection: set[str] = set()
        self._groups: dict[str, GroupSpec] = {}
        self._drag_painting = False
        self._drag_state: Optional[bool] = None
        self._last_clicked: Optional[str] = None

        self._build_grid()
        self._fit()

    # ── Build ────────────────────────────────────────────────────────
    def _build_grid(self) -> None:
        self._scene.clear()
        self._wells.clear()

        width = ROW_LABEL_W + 12 * CELL + PAD
        height = COL_LABEL_H + 8 * CELL + PAD

        # Dotted background illustration (top-right corner)
        for dr in range(3):
            for dc in range(3):
                x = width - PAD - (dc + 1) * 7
                y = PAD + dr * 7
                dot = self._scene.addEllipse(x, y, 3, 3)
                dot.setPen(Qt.NoPen)
                dot.setBrush(QColor(0, 0, 0, 20))

        # Column labels
        for ci, col in enumerate(COLS):
            lbl = QGraphicsTextItem(col)
            lbl.setDefaultTextColor(QColor("#7C786D"))
            font = lbl.font()
            font.setPointSizeF(7.5)
            lbl.setFont(font)
            x = ROW_LABEL_W + ci * CELL + (WELL_SIZE - lbl.boundingRect().width()) / 2
            lbl.setPos(x, 2)
            self._scene.addItem(lbl)

        # Row labels + wells
        for ri, row in enumerate(ROWS):
            rlbl = QGraphicsTextItem(row)
            rlbl.setDefaultTextColor(QColor("#7C786D"))
            font = rlbl.font()
            font.setPointSizeF(7.5)
            rlbl.setFont(font)
            y = COL_LABEL_H + ri * CELL + (WELL_SIZE - rlbl.boundingRect().height()) / 2
            rlbl.setPos(2, y)
            self._scene.addItem(rlbl)

            for ci, col in enumerate(COLS):
                wid = f"{row}{col}"
                item = WellItem(wid)
                item.setPos(
                    QPointF(
                        ROW_LABEL_W + ci * CELL,
                        COL_LABEL_H + ri * CELL,
                    )
                )
                item.clicked.connect(self._on_well_clicked)
                item.entered.connect(self._on_well_entered)
                self._scene.addItem(item)
                self._wells[wid] = item

        self._scene.setSceneRect(0, 0, width, height)

    def _fit(self) -> None:
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._fit()

    def sizeHint(self):  # noqa: ANN001
        from PySide6.QtCore import QSize
        return QSize(320, 180)

    # ── Selection ────────────────────────────────────────────────────
    def _on_well_clicked(self, well_id: str) -> None:
        modifiers = __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication.keyboardModifiers()
        from PySide6.QtCore import Qt as _Qt
        if modifiers & _Qt.ShiftModifier and self._last_clicked:
            self._extend_selection(self._last_clicked, well_id)
        else:
            if well_id in self._selection:
                self._selection.discard(well_id)
                self._wells[well_id].set_selected(False)
            else:
                self._selection.add(well_id)
                self._wells[well_id].set_selected(True)
        self._last_clicked = well_id
        self.selection_changed.emit(set(self._selection))

    def _extend_selection(self, from_id: str, to_id: str) -> None:
        r1, c1 = ROWS.index(from_id[0]), COLS.index(from_id[1:])
        r2, c2 = ROWS.index(to_id[0]), COLS.index(to_id[1:])
        for ri in range(min(r1, r2), max(r1, r2) + 1):
            for ci in range(min(c1, c2), max(c1, c2) + 1):
                wid = f"{ROWS[ri]}{COLS[ci]}"
                self._selection.add(wid)
                self._wells[wid].set_selected(True)

    def _on_well_entered(self, well_id: str) -> None:
        if self._drag_painting and self._drag_state is not None:
            self._wells[well_id].set_selected(self._drag_state)
            if self._drag_state:
                self._selection.add(well_id)
            else:
                self._selection.discard(well_id)
            self.selection_changed.emit(set(self._selection))
        self.hovered_well_changed.emit(well_id)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.LeftButton:
            self._drag_painting = True
            item = self.itemAt(event.pos())
            if isinstance(item, WellItem):
                self._drag_state = item.well_id not in self._selection
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.LeftButton:
            self._drag_painting = False
            self._drag_state = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        self.hovered_well_changed.emit(None)
        super().leaveEvent(event)

    # ── Public API ───────────────────────────────────────────────────
    @property
    def selection(self) -> set[str]:
        return set(self._selection)

    @selection.setter
    def selection(self, wells: set[str]) -> None:
        for wid, item in self._wells.items():
            val = wid in wells
            item.set_selected(val)
        self._selection = set(wells)

    def clear_selection(self) -> None:
        self.selection = set()
        self.selection_changed.emit(set())

    def set_groups(self, mapping: dict[str, GroupSpec]) -> None:
        self._groups = mapping
        group_to_color: dict[str, str] = {}
        for g in mapping.values():
            group_to_color[g.id] = g.color
        well_to_group: dict[str, GroupSpec] = {}
        for wid, spec in mapping.items():
            well_to_group[wid] = spec
        for wid, item in self._wells.items():
            spec = well_to_group.get(wid)
            item.set_group_color(spec.color if spec else None)

    def apply_palette(self, sunk: str, ink: str, dark_highlight: bool) -> None:
        for item in self._wells.values():
            item.set_palette_colors(sunk, ink, dark_highlight)

    def select_row(self, row: str) -> None:
        for col in COLS:
            wid = f"{row}{col}"
            self._selection.add(wid)
            self._wells[wid].set_selected(True)
        self.selection_changed.emit(set(self._selection))

    def select_col(self, col: str) -> None:
        for row in ROWS:
            wid = f"{row}{col}"
            self._selection.add(wid)
            self._wells[wid].set_selected(True)
        self.selection_changed.emit(set(self._selection))
