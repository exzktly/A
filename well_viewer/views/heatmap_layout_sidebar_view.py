"""Heat-map layout configurator — sidebar variant.

Renders directly under the standard well picker on the Heat Map tab. The
user picks an R×C grid size, drags wells from the palette into table cells,
moves wells between cells by dragging, and clears a cell by double-clicking
it. The palette and the table are two views of a single shared
``HeatmapLayout`` instance held by the app (see
``heatmap_controller.active_layout``).

State of truth: ``app._heatmap_layouts``. The sidebar maintains exactly
one layout named ``SIDEBAR_LAYOUT_NAME`` and synchronises both widgets to
its ``cells`` dict on every change. Each cell holds at most one well token
in this UI; the underlying model still permits multi-well cells, which
remain accessible to programmatic / future editor uses.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from well_viewer.heatmap_models import HeatmapLayout


SIDEBAR_LAYOUT_NAME = "Sidebar"
WELL_MIME = "application/x-well-token"


# ── Drag-aware widgets ───────────────────────────────────────────────────────

class _WellPaletteList(QListWidget):
    """List of unassigned wells. Drag source AND drop sink."""

    def __init__(self, on_drop, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._on_drop = on_drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(2)
        self.setMaximumHeight(96)

    def mimeTypes(self) -> List[str]:
        return [WELL_MIME]

    def startDrag(self, _supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        token = item.text().strip()
        if not token:
            return
        mime = QMimeData()
        mime.setData(WELL_MIME, token.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction | Qt.CopyAction)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(WELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(WELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        md = event.mimeData()
        if not md.hasFormat(WELL_MIME):
            event.ignore()
            return
        token = bytes(md.data(WELL_MIME)).decode("utf-8").strip()
        if not token:
            event.ignore()
            return
        # Returning a well to the palette → unassign from any cell.
        self._on_drop("palette", None, token)
        event.acceptProposedAction()


class _LayoutTable(QTableWidget):
    """The R×C grid. Drag source AND drop sink for well tokens."""

    def __init__(self, on_drop, on_clear_cell, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._on_drop = on_drop
        self._on_clear_cell = on_clear_cell
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setDefaultSectionSize(22)
        self.horizontalHeader().setDefaultSectionSize(28)

    def mimeTypes(self) -> List[str]:
        return [WELL_MIME]

    def startDrag(self, _supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        token = (item.text() or "").strip()
        if not token:
            return
        mime = QMimeData()
        mime.setData(WELL_MIME, token.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction | Qt.CopyAction)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(WELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(WELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        md = event.mimeData()
        if not md.hasFormat(WELL_MIME):
            event.ignore()
            return
        token = bytes(md.data(WELL_MIME)).decode("utf-8").strip()
        if not token:
            event.ignore()
            return
        idx = self.indexAt(event.position().toPoint())
        if not idx.isValid():
            event.ignore()
            return
        self._on_drop("cell", (idx.row(), idx.column()), token)
        event.acceptProposedAction()

    def mouseDoubleClickEvent(self, event) -> None:
        idx = self.indexAt(event.position().toPoint())
        if not idx.isValid():
            super().mouseDoubleClickEvent(event)
            return
        item = self.item(idx.row(), idx.column())
        token = (item.text() if item else "").strip()
        if token:
            self._on_clear_cell(idx.row(), idx.column())
            return
        super().mouseDoubleClickEvent(event)


# ── Builder ──────────────────────────────────────────────────────────────────

def build_heatmap_layout_sidebar(app, parent: QWidget) -> QWidget:
    """Build the inline configurator and attach it to *parent*'s layout.

    Returns the outer frame widget so the caller can toggle its visibility.
    """
    outer = QWidget(parent)
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(0, 4, 0, 4)
    outer_layout.setSpacing(2)

    sep = QFrame(outer)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    outer_layout.addWidget(sep)

    hdr = QLabel("HEATMAP LAYOUT", outer)
    hdr.setObjectName("SidebarHeader")
    hdr.setProperty("role", "header")
    outer_layout.addWidget(hdr)

    # Size controls
    size_row = QWidget(outer)
    size_layout = QHBoxLayout(size_row)
    size_layout.setContentsMargins(6, 0, 6, 0)
    size_layout.setSpacing(4)
    size_layout.addWidget(QLabel("Rows:", size_row))
    rows_spin = QSpinBox(size_row)
    rows_spin.setRange(1, 32)
    rows_spin.setValue(8)
    size_layout.addWidget(rows_spin)
    size_layout.addWidget(QLabel("Cols:", size_row))
    cols_spin = QSpinBox(size_row)
    cols_spin.setRange(1, 32)
    cols_spin.setValue(12)
    size_layout.addWidget(cols_spin)
    size_layout.addStretch(1)
    outer_layout.addWidget(size_row)

    # Hint label
    hint = QLabel(
        "Drag wells from below into cells. Drag between cells to move. "
        "Double-click a cell to remove its well.",
        outer,
    )
    hint.setObjectName("Muted")
    hint.setWordWrap(True)
    outer_layout.addWidget(hint)

    # Layout table
    table = _LayoutTable(
        on_drop=lambda kind, rc, tok: _on_drop_event(app, kind, rc, tok),
        on_clear_cell=lambda r, c: _clear_cell(app, r, c),
        parent=outer,
    )
    table.setMinimumHeight(160)
    outer_layout.addWidget(table, 1)

    # Palette of unassigned wells
    palette_lbl = QLabel("Wells (drag to grid):", outer)
    palette_lbl.setObjectName("Muted")
    outer_layout.addWidget(palette_lbl)
    palette = _WellPaletteList(
        on_drop=lambda kind, rc, tok: _on_drop_event(app, kind, rc, tok),
        parent=outer,
    )
    outer_layout.addWidget(palette)

    # Stash widget refs on the app so callbacks/refresh can find them.
    app._heatmap_sidebar_frame = outer
    app._heatmap_sidebar_table = table
    app._heatmap_sidebar_palette = palette
    app._heatmap_sidebar_rows_spin = rows_spin
    app._heatmap_sidebar_cols_spin = cols_spin

    rows_spin.valueChanged.connect(lambda _v: _on_size_changed(app))
    cols_spin.valueChanged.connect(lambda _v: _on_size_changed(app))

    parent_layout = parent.layout()
    if parent_layout is None:
        parent_layout = QVBoxLayout(parent)
    parent_layout.addWidget(outer)

    refresh_heatmap_layout_sidebar(app)
    return outer


# ── State helpers ────────────────────────────────────────────────────────────

def _ensure_sidebar_layout(app) -> HeatmapLayout:
    """Return (creating if needed) the single ``Sidebar`` layout."""
    layouts: List[HeatmapLayout] = list(getattr(app, "_heatmap_layouts", []) or [])
    for lay in layouts:
        if lay.name == SIDEBAR_LAYOUT_NAME:
            return lay
    lay = HeatmapLayout(name=SIDEBAR_LAYOUT_NAME, rows=8, cols=12)
    layouts.append(lay)
    app._heatmap_layouts = layouts
    app._active_heatmap_layout_name = SIDEBAR_LAYOUT_NAME
    return lay


def _all_well_tokens(app) -> List[str]:
    return sorted((getattr(app, "_well_paths", {}) or {}).keys())


def _layout_assigned_tokens(layout: HeatmapLayout) -> List[str]:
    return list(layout.assigned_wells())


def _palette_tokens(app, layout: HeatmapLayout) -> List[str]:
    assigned = set(_layout_assigned_tokens(layout))
    return [w for w in _all_well_tokens(app) if w not in assigned]


def _find_cell_for_token(layout: HeatmapLayout, token: str) -> Optional[Tuple[int, int]]:
    for (r, c), wells in layout.cells.items():
        if token in wells:
            return (r, c)
    return None


# ── Refresh + drop handlers ──────────────────────────────────────────────────

def refresh_heatmap_layout_sidebar(app) -> None:
    """Re-render the table and palette from ``app._heatmap_layouts``."""
    table: _LayoutTable = getattr(app, "_heatmap_sidebar_table", None)
    palette: _WellPaletteList = getattr(app, "_heatmap_sidebar_palette", None)
    rows_spin: QSpinBox = getattr(app, "_heatmap_sidebar_rows_spin", None)
    cols_spin: QSpinBox = getattr(app, "_heatmap_sidebar_cols_spin", None)
    if table is None or palette is None:
        return

    layout = _ensure_sidebar_layout(app)

    if rows_spin is not None and rows_spin.value() != layout.rows:
        rows_spin.blockSignals(True)
        try:
            rows_spin.setValue(layout.rows)
        finally:
            rows_spin.blockSignals(False)
    if cols_spin is not None and cols_spin.value() != layout.cols:
        cols_spin.blockSignals(True)
        try:
            cols_spin.setValue(layout.cols)
        finally:
            cols_spin.blockSignals(False)

    table.blockSignals(True)
    try:
        table.clear()
        table.setRowCount(layout.rows)
        table.setColumnCount(layout.cols)
        row_labels = layout.row_labels or [str(i + 1) for i in range(layout.rows)]
        col_labels = layout.col_labels or [str(i + 1) for i in range(layout.cols)]
        table.setHorizontalHeaderLabels(col_labels[: layout.cols])
        table.setVerticalHeaderLabels(row_labels[: layout.rows])
        for r in range(layout.rows):
            for c in range(layout.cols):
                wells = layout.cells.get((r, c), [])
                token = wells[0] if wells else ""
                item = QTableWidgetItem(token)
                item.setTextAlignment(Qt.AlignCenter)
                # Selectable + draggable when populated; only selectable when empty.
                flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
                if token:
                    flags |= Qt.ItemIsDragEnabled
                item.setFlags(flags)
                table.setItem(r, c, item)
    finally:
        table.blockSignals(False)

    palette.blockSignals(True)
    try:
        palette.clear()
        for tok in _palette_tokens(app, layout):
            it = QListWidgetItem(tok)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            palette.addItem(it)
    finally:
        palette.blockSignals(False)


def _on_size_changed(app) -> None:
    rows_spin: QSpinBox = getattr(app, "_heatmap_sidebar_rows_spin", None)
    cols_spin: QSpinBox = getattr(app, "_heatmap_sidebar_cols_spin", None)
    if rows_spin is None or cols_spin is None:
        return
    layout = _ensure_sidebar_layout(app)
    new_rows = int(rows_spin.value())
    new_cols = int(cols_spin.value())
    if new_rows == layout.rows and new_cols == layout.cols:
        return
    # Drop labels when shrinking past their length so resize stays clean.
    if layout.row_labels and new_rows < len(layout.row_labels):
        layout.row_labels = layout.row_labels[:new_rows]
    if layout.col_labels and new_cols < len(layout.col_labels):
        layout.col_labels = layout.col_labels[:new_cols]
    layout.resize(new_rows, new_cols)
    _persist_and_redraw(app)
    refresh_heatmap_layout_sidebar(app)


def _on_drop_event(app, kind: str, rc: Optional[Tuple[int, int]], token: str) -> None:
    """Handle a successful drop. Updates state and re-renders both widgets."""
    layout = _ensure_sidebar_layout(app)
    src = _find_cell_for_token(layout, token)
    if kind == "palette":
        if src is not None:
            layout.assign(src[0], src[1], [])
    elif kind == "cell" and rc is not None:
        target_r, target_c = rc
        # If the target already holds a well, swap with the source (when
        # source was a cell) or push the existing tenant to the palette.
        existing = list(layout.cells.get((target_r, target_c), []))
        if src is not None and src != (target_r, target_c):
            layout.assign(src[0], src[1], existing)  # tenant goes back to source
        layout.assign(target_r, target_c, [token])
    _persist_and_redraw(app)
    refresh_heatmap_layout_sidebar(app)


def _clear_cell(app, r: int, c: int) -> None:
    layout = _ensure_sidebar_layout(app)
    if (r, c) in layout.cells:
        layout.assign(r, c, [])
        _persist_and_redraw(app)
        refresh_heatmap_layout_sidebar(app)


def _persist_and_redraw(app) -> None:
    if hasattr(app, "_heatmap_layouts_save_to_data_dir"):
        try:
            app._heatmap_layouts_save_to_data_dir()
        except Exception:
            pass
    if hasattr(app, "_heatmap_canvas"):
        try:
            from well_viewer.heatmap_controller import redraw_heatmap
            redraw_heatmap(app)
        except Exception:
            pass
