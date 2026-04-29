"""Heatmap layout editor dialog.

Lets the user define / duplicate / delete arbitrary R×C heatmap layouts and
assign wells to cells. Layouts are persisted as JSON next to the data files
(``heatmap_layouts.json``) and surfaced in the Heat Map tab's Layout
dropdown.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from well_viewer.heatmap_models import (
    HeatmapLayout,
    PLATE_DEFAULT_NAME,
    make_plate_layout,
)


def open_heatmap_layout_panel(app, parent: Optional[QWidget] = None) -> None:
    dlg = HeatmapLayoutPanelDialog(app, parent or app)
    dlg.exec()


class HeatmapLayoutPanelDialog(QDialog):
    def __init__(self, app, parent: QWidget) -> None:
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Heatmap Layouts")
        self.setModal(True)
        self.resize(940, 560)

        # Working copy of the layouts list.
        self._layouts: List[HeatmapLayout] = [
            HeatmapLayout.from_dict(lay.to_dict())
            for lay in (getattr(app, "_heatmap_layouts", []) or [])
        ]
        self._active_idx: int = 0 if self._layouts else -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        # Top row: layout picker + name + size
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        top_row.addWidget(QLabel("Layout:", self))
        self._layout_combo = QComboBox(self)
        self._layout_combo.currentIndexChanged.connect(self._on_layout_picked)
        top_row.addWidget(self._layout_combo, 1)

        new_btn = QPushButton("+ New", self)
        new_btn.clicked.connect(self._on_new)
        top_row.addWidget(new_btn)

        dup_btn = QPushButton("Duplicate", self)
        dup_btn.clicked.connect(self._on_duplicate)
        top_row.addWidget(dup_btn)

        plate_btn = QPushButton("Default from plate", self)
        plate_btn.clicked.connect(self._on_default_from_plate)
        top_row.addWidget(plate_btn)

        del_btn = QPushButton("Delete", self)
        del_btn.clicked.connect(self._on_delete)
        top_row.addWidget(del_btn)

        outer.addLayout(top_row)

        # Name + size + labels
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        meta_row.addWidget(QLabel("Name:", self))
        self._name_edit = QLineEdit(self)
        self._name_edit.editingFinished.connect(self._on_name_edited)
        meta_row.addWidget(self._name_edit, 1)

        meta_row.addWidget(QLabel("Rows:", self))
        self._rows_spin = QSpinBox(self)
        self._rows_spin.setRange(1, 32)
        self._rows_spin.valueChanged.connect(self._on_size_changed)
        meta_row.addWidget(self._rows_spin)

        meta_row.addWidget(QLabel("Cols:", self))
        self._cols_spin = QSpinBox(self)
        self._cols_spin.setRange(1, 32)
        self._cols_spin.valueChanged.connect(self._on_size_changed)
        meta_row.addWidget(self._cols_spin)

        outer.addLayout(meta_row)

        # Optional row/col labels
        labels_row = QHBoxLayout()
        labels_row.setSpacing(6)
        labels_row.addWidget(QLabel("Row labels (CSV):", self))
        self._row_labels_edit = QLineEdit(self)
        self._row_labels_edit.editingFinished.connect(self._on_labels_edited)
        labels_row.addWidget(self._row_labels_edit, 1)

        labels_row.addWidget(QLabel("Col labels (CSV):", self))
        self._col_labels_edit = QLineEdit(self)
        self._col_labels_edit.editingFinished.connect(self._on_labels_edited)
        labels_row.addWidget(self._col_labels_edit, 1)

        outer.addLayout(labels_row)

        # Center: grid table | unassigned wells panel
        splitter = QSplitter(Qt.Horizontal, self)
        outer.addWidget(splitter, 1)

        self._grid_table = QTableWidget(0, 0, splitter)
        self._grid_table.setSelectionBehavior(QTableWidget.SelectItems)
        self._grid_table.setSelectionMode(QTableWidget.SingleSelection)
        self._grid_table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._grid_table.itemChanged.connect(self._on_grid_item_changed)
        splitter.addWidget(self._grid_table)

        right_panel = QWidget(splitter)
        rp = QVBoxLayout(right_panel)
        rp.setContentsMargins(6, 0, 0, 0)
        rp.addWidget(QLabel("Unassigned wells", right_panel))
        self._unassigned_list = QListWidget(right_panel)
        self._unassigned_list.setSelectionMode(QListWidget.ExtendedSelection)
        rp.addWidget(self._unassigned_list, 1)

        assign_row = QHBoxLayout()
        assign_row.setSpacing(6)
        assign_btn = QPushButton("→ Assign to selected cell", right_panel)
        assign_btn.clicked.connect(self._on_assign_to_cell)
        assign_row.addWidget(assign_btn)
        clear_btn = QPushButton("Clear cell", right_panel)
        clear_btn.clicked.connect(self._on_clear_cell)
        assign_row.addWidget(clear_btn)
        rp.addLayout(assign_row)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        # Bottom: apply/cancel
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        apply_btn = QPushButton("Apply", self)
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)
        outer.addLayout(btn_row)

        self._refresh_layout_combo()
        if self._active_idx >= 0:
            self._render_active_layout()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _all_well_tokens(self) -> List[str]:
        return sorted((getattr(self._app, "_well_paths", {}) or {}).keys())

    def _refresh_layout_combo(self) -> None:
        cb = self._layout_combo
        blocked = cb.blockSignals(True)
        try:
            cb.clear()
            for lay in self._layouts:
                cb.addItem(lay.name)
            if self._active_idx >= 0 and self._active_idx < cb.count():
                cb.setCurrentIndex(self._active_idx)
        finally:
            cb.blockSignals(blocked)

    def _active_layout(self) -> Optional[HeatmapLayout]:
        if self._active_idx < 0 or self._active_idx >= len(self._layouts):
            return None
        return self._layouts[self._active_idx]

    def _render_active_layout(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        # name + size + label fields
        self._name_edit.setText(lay.name)
        self._rows_spin.blockSignals(True)
        self._cols_spin.blockSignals(True)
        try:
            self._rows_spin.setValue(lay.rows)
            self._cols_spin.setValue(lay.cols)
        finally:
            self._rows_spin.blockSignals(False)
            self._cols_spin.blockSignals(False)
        self._row_labels_edit.setText(",".join(lay.row_labels) if lay.row_labels else "")
        self._col_labels_edit.setText(",".join(lay.col_labels) if lay.col_labels else "")
        self._render_grid()
        self._render_unassigned()

    def _render_grid(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        t = self._grid_table
        blocked = t.blockSignals(True)
        try:
            t.clear()
            t.setRowCount(lay.rows)
            t.setColumnCount(lay.cols)
            row_labels = lay.row_labels or [f"{i+1}" for i in range(lay.rows)]
            col_labels = lay.col_labels or [f"{i+1}" for i in range(lay.cols)]
            t.setHorizontalHeaderLabels(col_labels[: lay.cols])
            t.setVerticalHeaderLabels(row_labels[: lay.rows])
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for r in range(lay.rows):
                for c in range(lay.cols):
                    wells = lay.cells.get((r, c), [])
                    item = QTableWidgetItem(",".join(wells))
                    item.setTextAlignment(Qt.AlignCenter)
                    t.setItem(r, c, item)
        finally:
            t.blockSignals(blocked)

    def _render_unassigned(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        assigned = set(lay.assigned_wells())
        all_wells = self._all_well_tokens()
        self._unassigned_list.clear()
        for w in all_wells:
            if w not in assigned:
                self._unassigned_list.addItem(QListWidgetItem(w))

    # ── event handlers ───────────────────────────────────────────────────────

    def _on_layout_picked(self, idx: int) -> None:
        if 0 <= idx < len(self._layouts):
            self._active_idx = idx
            self._render_active_layout()

    def _on_new(self) -> None:
        name, ok = QInputDialog.getText(self, "New layout", "Name:")
        if not ok or not name.strip():
            return
        new_lay = HeatmapLayout(name=name.strip(), rows=8, cols=12)
        self._layouts.append(new_lay)
        self._active_idx = len(self._layouts) - 1
        self._refresh_layout_combo()
        self._render_active_layout()

    def _on_duplicate(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        clone = HeatmapLayout.from_dict(lay.to_dict())
        clone.name = f"{lay.name} copy"
        self._layouts.append(clone)
        self._active_idx = len(self._layouts) - 1
        self._refresh_layout_combo()
        self._render_active_layout()

    def _on_delete(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        resp = QMessageBox.question(
            self, "Delete layout?",
            f"Delete layout {lay.name!r}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        del self._layouts[self._active_idx]
        self._active_idx = max(0, self._active_idx - 1) if self._layouts else -1
        self._refresh_layout_combo()
        if self._active_idx >= 0:
            self._render_active_layout()
        else:
            self._grid_table.clear()
            self._unassigned_list.clear()

    def _on_default_from_plate(self) -> None:
        plate = make_plate_layout(self._all_well_tokens())
        # Reuse the active layout's name if present so the user keeps editing
        # the same row in the dropdown rather than spawning a duplicate.
        active = self._active_layout()
        if active is None:
            plate.name = PLATE_DEFAULT_NAME
            self._layouts.append(plate)
            self._active_idx = len(self._layouts) - 1
        else:
            plate.name = active.name
            self._layouts[self._active_idx] = plate
        self._refresh_layout_combo()
        self._render_active_layout()

    def _on_name_edited(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        new = self._name_edit.text().strip()
        if new and new != lay.name:
            lay.name = new
            self._refresh_layout_combo()

    def _on_size_changed(self, _value: int) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        new_rows = int(self._rows_spin.value())
        new_cols = int(self._cols_spin.value())
        if new_rows == lay.rows and new_cols == lay.cols:
            return
        lay.resize(new_rows, new_cols)
        self._render_grid()
        self._render_unassigned()

    def _on_labels_edited(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        rows_csv = self._row_labels_edit.text().strip()
        cols_csv = self._col_labels_edit.text().strip()
        lay.row_labels = [s.strip() for s in rows_csv.split(",") if s.strip()] or None
        lay.col_labels = [s.strip() for s in cols_csv.split(",") if s.strip()] or None
        self._render_grid()

    def _on_grid_item_changed(self, item: QTableWidgetItem) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        r = item.row()
        c = item.column()
        text = item.text().strip()
        wells = [w.strip() for w in text.split(",") if w.strip()]
        # Normalize to upper case + 2-digit column when possible.
        normalized: List[str] = []
        for w in wells:
            up = w.upper()
            if len(up) >= 2 and up[0].isalpha() and up[1:].isdigit():
                normalized.append(f"{up[0]}{int(up[1:]):02d}")
            else:
                normalized.append(up)
        lay.assign(r, c, normalized)
        # Update unassigned list (cheap — recompute).
        self._render_unassigned()

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        # The default behavior (edit the cell text) is already triggered by
        # double-click; this hook is reserved for future drag-drop polish.
        pass

    def _on_assign_to_cell(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        cur = self._grid_table.currentItem()
        if cur is None:
            QMessageBox.information(self, "No cell selected", "Select a grid cell first.")
            return
        wells = [it.text() for it in self._unassigned_list.selectedItems()]
        if not wells:
            return
        existing = lay.cells.get((cur.row(), cur.column()), [])
        merged = existing + [w for w in wells if w not in existing]
        lay.assign(cur.row(), cur.column(), merged)
        self._render_grid()
        self._render_unassigned()

    def _on_clear_cell(self) -> None:
        lay = self._active_layout()
        if lay is None:
            return
        cur = self._grid_table.currentItem()
        if cur is None:
            return
        lay.assign(cur.row(), cur.column(), [])
        self._render_grid()
        self._render_unassigned()

    def _on_apply(self) -> None:
        # Commit the working copy to the app and persist.
        self._app._heatmap_layouts = self._layouts
        if hasattr(self._app, "_refresh_heatmap_layout_combo"):
            self._app._refresh_heatmap_layout_combo()
        if hasattr(self._app, "_heatmap_layouts_save_to_data_dir"):
            self._app._heatmap_layouts_save_to_data_dir()
        # Trigger a redraw of the heatmap tab if visible.
        if hasattr(self._app, "_heatmap_canvas"):
            try:
                from well_viewer.heatmap_controller import redraw_heatmap
                redraw_heatmap(self._app)
            except Exception:
                pass
        self.accept()
