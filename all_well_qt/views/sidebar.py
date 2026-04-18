"""ReviewView sidebar: plate picker, row/col selectors, sample groups."""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..widgets.plate_map import COLS, ROWS, GroupSpec, PlateMapWidget
from ..widgets.sample_group_list import SampleGroupList


class RowColSelector(QWidget):
    """Compact grid of toggle buttons for rows A–H or cols 1–12."""

    toggled = Signal(str)   # row or col label

    def __init__(
        self,
        labels: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        cols = 8 if len(labels) <= 8 else 12
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setObjectName("chip")
            btn.setCheckable(True)
            btn.setFixedSize(26, 22)
            btn.clicked.connect(lambda _, l=lbl: self.toggled.emit(l))
            layout.addWidget(btn, i // cols, i % cols)


class Sidebar(QWidget):
    """Left sidebar of ReviewView."""

    selection_changed = Signal(object)   # set[str]
    hovered_well_changed = Signal(object)  # Optional[str]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Head ──────────────────────────────────────────────────────
        head = QWidget()
        head.setObjectName("sidePanel")
        head_layout = QVBoxLayout(head)
        head_layout.setContentsMargins(14, 14, 14, 10)
        head_layout.setSpacing(4)

        title_row = QHBoxLayout()
        plate_title = QLabel("Plate")
        plate_title.setObjectName("panelTitle")
        title_row.addWidget(plate_title)
        title_row.addStretch()
        meta = QLabel("96 wells · 8×12")
        meta.setObjectName("muted")
        title_row.addWidget(meta)
        head_layout.addLayout(title_row)

        sub = QLabel("Drag to select · Shift-click for replicates. Colors encode sample group.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        head_layout.addWidget(sub)
        layout.addWidget(head)

        # ── Row selector ──────────────────────────────────────────────
        row_w = QWidget()
        row_w.setObjectName("sidePanel")
        row_layout = QVBoxLayout(row_w)
        row_layout.setContentsMargins(14, 6, 14, 2)
        row_layout.setSpacing(4)
        row_lbl = QLabel("ROWS")
        row_lbl.setObjectName("section")
        row_layout.addWidget(row_lbl)
        self._row_sel = RowColSelector(ROWS)
        self._row_sel.toggled.connect(self._on_row_toggled)
        row_layout.addWidget(self._row_sel)
        layout.addWidget(row_w)

        # ── Col selector ──────────────────────────────────────────────
        col_w = QWidget()
        col_w.setObjectName("sidePanel")
        col_layout = QVBoxLayout(col_w)
        col_layout.setContentsMargins(14, 2, 14, 6)
        col_layout.setSpacing(4)
        col_lbl = QLabel("COLS")
        col_lbl.setObjectName("section")
        col_layout.addWidget(col_lbl)
        self._col_sel = RowColSelector(COLS)
        self._col_sel.toggled.connect(self._on_col_toggled)
        col_layout.addWidget(self._col_sel)
        layout.addWidget(col_w)

        # ── Plate card ────────────────────────────────────────────────
        plate_frame = QFrame()
        plate_frame.setObjectName("plateCard")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        plate_frame.setGraphicsEffect(shadow)

        plate_frame_layout = QVBoxLayout(plate_frame)
        plate_frame_layout.setContentsMargins(10, 10, 10, 10)

        self.plate_map = PlateMapWidget()
        self.plate_map.selection_changed.connect(self._on_plate_selection)
        self.plate_map.hovered_well_changed.connect(self.hovered_well_changed)
        plate_frame_layout.addWidget(self.plate_map)

        plate_wrap = QWidget()
        plate_wrap.setObjectName("sidePanel")
        pw_layout = QVBoxLayout(plate_wrap)
        pw_layout.setContentsMargins(14, 6, 14, 6)
        pw_layout.addWidget(plate_frame)
        layout.addWidget(plate_wrap)

        # ── Plate foot ────────────────────────────────────────────────
        foot = QWidget()
        foot.setObjectName("sidePanel")
        foot_layout = QHBoxLayout(foot)
        foot_layout.setContentsMargins(14, 4, 14, 8)

        self._sel_count = QLabel("0 wells selected")
        self._sel_count.setObjectName("muted")
        foot_layout.addWidget(self._sel_count)
        foot_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("ghost")
        clear_btn.clicked.connect(self._on_clear)
        foot_layout.addWidget(clear_btn)
        layout.addWidget(foot)

        # ── Separator ─────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setObjectName("card")
        layout.addWidget(sep)

        # ── Sample groups ─────────────────────────────────────────────
        self.sample_groups = SampleGroupList()
        self.sample_groups.new_group_requested.connect(self._on_new_group)
        self.sample_groups.group_renamed.connect(self._on_group_renamed)
        self.sample_groups.group_deleted.connect(self._on_group_deleted)
        layout.addWidget(self.sample_groups, 1)

        # well_id → GroupSpec for the full plate mapping
        self._well_group_map: dict[str, GroupSpec] = {}

        # Seed demo groups
        self._seed_demo_groups()

    def _on_row_toggled(self, row: str) -> None:
        self.plate_map.select_row(row)

    def _on_col_toggled(self, col: str) -> None:
        self.plate_map.select_col(col)

    def _on_plate_selection(self, wells: set) -> None:
        self._sel_count.setText(f"{len(wells)} well{'s' if len(wells) != 1 else ''} selected")
        self.selection_changed.emit(wells)

    def _on_clear(self) -> None:
        self.plate_map.clear_selection()

    def _on_new_group(self) -> None:
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        from ..theme.manager import ThemeManager
        tokens = ThemeManager.instance().tokens
        wells = self.plate_map.selection
        if not wells:
            QMessageBox.information(self, "No selection", "Select wells before creating a group.")
            return
        name, ok = QInputDialog.getText(self, "New sample group", "Group name:")
        if not ok or not name.strip():
            return
        idx = len(self.sample_groups._rows)
        color = tokens["wells"][idx % len(tokens["wells"])]
        gid = f"group_{idx}"
        self.sample_groups.add_group(gid, name.strip(), color, len(wells))
        for w in wells:
            self._well_group_map[w] = GroupSpec(color=color, name=name.strip(), id=gid)
        self.plate_map.set_groups(self._well_group_map)

    def _on_group_renamed(self, group_id: str, new_name: str) -> None:
        for well_id, spec in self._well_group_map.items():
            if spec.id == group_id:
                self._well_group_map[well_id] = GroupSpec(
                    color=spec.color, name=new_name, id=spec.id
                )
        # Colors haven't changed so no plate repaint needed

    def _on_group_deleted(self, group_id: str) -> None:
        self._well_group_map = {
            w: spec for w, spec in self._well_group_map.items()
            if spec.id != group_id
        }
        self.plate_map.set_groups(self._well_group_map)

    def _seed_demo_groups(self) -> None:
        from ..theme.manager import ThemeManager
        try:
            tokens = ThemeManager.instance().tokens
        except RuntimeError:
            return
        groups = [
            ("ctrl",  "Control (DMSO)",     ["A01","A02","A03","B01","B02","B03"]),
            ("dose1", "PF-562271 · 100 nM", ["A05","A06","A07","B05","B06","B07"]),
            ("dose2", "PF-562271 · 1 µM",   ["A09","A10","A11","B09","B10","B11"]),
            ("ripk",  "RIPK1 kd",           ["D02","D03","D04","E02","E03","E04"]),
            ("ripa",  "RIPA co-treat",      ["D07","D08","D09","E07","E08","E09"]),
        ]
        for i, (gid, name, wells) in enumerate(groups):
            color = tokens["wells"][i % len(tokens["wells"])]
            self.sample_groups.add_group(gid, name, color, len(wells))
            for w in wells:
                self._well_group_map[w] = GroupSpec(color=color, name=name, id=gid)
        self.plate_map.set_groups(self._well_group_map)
