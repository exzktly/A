"""Batch-export dialog panels (PySide6 port)."""

from __future__ import annotations

import copy
import csv
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from well_viewer.runtime_app import (
    PLOT_BG,
    PLOT_SPN,
    TXT_MUT,
    TXT_PRI,
    WARN,
    WELL_COLORS,
    _PLATE_COLS,
    _PLATE_ROWS,
    _all_fluor_values,
    _extract_well_token,
    _groups_with_loaded_wells,
    _logger,
    _read_pipeline_info_shared,
    aggregate_with_threshold,
    apply_ax_style,
)
from well_viewer.batch_models import BarGroup
from well_viewer.barplot_controller import render_bar_items as _bar_render_items
from well_viewer.scatter_controller import (
    collect_scatter_data as _collect_scatter_data,
    collect_scatter_agg_data as _collect_scatter_agg_data,
)
from well_viewer.ui_helpers import ask_name_dialog, btn_card, btn_danger, btn_primary, btn_secondary


_CLR_DANGER = "#d2453d"
_CLR_SUCCESS_DARK = "#2e7d32"
_CLR_PLACEHOLDER = "#9aa0a6"
_CLR_DISABLED_WELL = "#404040"
_CLR_ERR_BAR = "#333333"
_CLR_WHITE = "#ffffff"


def _parse_rc(tok: str):
    m = re.match(r"^([A-H])(\d{1,2})$", tok, re.I)
    if not m:
        return ("?", "?")
    return (m.group(1).upper(), f"{int(m.group(2)):02d}")


class _WellGridButton(QPushButton):
    """Small flat plate-map button used inside batch-export group editor."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(28, 22)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self._base_color = ""
        self._active = False

    def set_colors(self, bg: str, fg: str, active: bool = False, enabled: bool = True) -> None:
        self.setEnabled(enabled)
        self._base_color = bg
        self._active = active
        border = "2px solid #1976d2" if active else "1px solid #444"
        self.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border: {border}; padding: 0px; }}"
        )


class BatchExportPanel(QWidget):
    """Batch export panel — defines export groups and runs the export."""

    def __init__(
        self,
        app,
        parent: Optional[QWidget] = None,
        *,
        use_sidebar_groups: bool = False,
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._use_sidebar_groups = bool(use_sidebar_groups)

        default_out = str(app._data_dir) if app._data_dir else ""
        export_prefs = getattr(app, "_export_style_prefs", {}) or {}
        default_fmt = str(export_prefs.get("format", "png")).lower()
        if default_fmt not in {"png", "svg", "eps", "pdf"}:
            default_fmt = "png"
        default_profile = str(export_prefs.get("export_profile", "Custom"))

        self._out_dir_value: str = default_out
        self._fmt_value: str = default_fmt
        self._export_profile_value: str = default_profile
        self._active_grp = -1

        self._groups: List[BarGroup] = self._groups_from_rep_sets()
        self._auto_named_group_ids: set[int] = set()
        self._map_btns: Dict[str, _WellGridButton] = {}
        self._drag_adding = True
        self._drag_visited: set = set()

        self._build_ui()
        if not self._use_sidebar_groups:
            self._refresh_group_list()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if self._use_sidebar_groups:
            right = QWidget()
            right_layout = QVBoxLayout(right)
            right_layout.setContentsMargins(0, 0, 0, 0)
            self._build_output_panel(right_layout)
            outer.addWidget(right, 1)
            return

        left = QWidget()
        left.setMinimumWidth(420)
        left.setMaximumWidth(560)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._build_group_editor(left_layout)
        outer.addWidget(left)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Plain)
        outer.addWidget(sep)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._build_output_panel(right_layout)
        outer.addWidget(right, 1)

    def _build_group_editor(self, layout: QVBoxLayout) -> None:
        hdr1 = QHBoxLayout()
        hdr1.setContentsMargins(8, 4, 8, 4)
        title = QLabel("EXPORT GROUPS")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        hdr1.addWidget(title)
        hdr1.addStretch(1)
        clear_btn = btn_secondary(None, "Clear All", self._grp_clear_all)
        add_btn = btn_primary(None, "+ Add", self._grp_add)
        hdr1.addWidget(clear_btn)
        hdr1.addWidget(add_btn)
        layout.addLayout(hdr1)

        hdr2 = QHBoxLayout()
        hdr2.setContentsMargins(8, 2, 8, 2)
        qs_btn = QToolButton()
        qs_btn.setText("Quick Setup \u25be")
        qs_btn.setPopupMode(QToolButton.InstantPopup)
        qs_menu = QMenu(qs_btn)
        qs_menu.addAction("One group per row  (Row A = all A wells, \u2026)", self._quick_by_row)
        qs_menu.addAction("One group per column  (Col 01 = all col-01 wells, \u2026)", self._quick_by_col)
        qs_btn.setMenu(qs_menu)
        hdr2.addWidget(qs_btn)
        hdr2.addWidget(btn_secondary(None, "Save\u2026", self._save_groups))
        hdr2.addWidget(btn_secondary(None, "Load\u2026", self._load_groups))
        hdr2.addSpacing(12)
        hdr2.addWidget(btn_secondary(None, "Sync from app", self._sync_from_app))
        hdr2.addStretch(1)
        layout.addLayout(hdr2)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        hint = QLabel("Left-drag wells onto the plate map to add them to the selected group.")
        hint.setWordWrap(True)
        hint.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(hint)

        map_widget = QWidget()
        map_grid = QGridLayout(map_widget)
        map_grid.setSpacing(2)
        map_grid.setContentsMargins(4, 2, 4, 2)
        for ci, col in enumerate(_PLATE_COLS):
            lbl = QLabel(col)
            lbl.setAlignment(Qt.AlignCenter)
            map_grid.addWidget(lbl, 0, ci + 1)
        for ri, row in enumerate(_PLATE_ROWS):
            rlbl = QLabel(row)
            rlbl.setAlignment(Qt.AlignCenter)
            map_grid.addWidget(rlbl, ri + 1, 0)
            for ci, col in enumerate(_PLATE_COLS):
                tok = f"{row}{col}"
                btn = _WellGridButton(tok)
                self._map_btns[tok] = btn
                map_grid.addWidget(btn, ri + 1, ci + 1)

        map_widget.mousePressEvent = self._plate_press
        map_widget.mouseMoveEvent = self._plate_move
        map_widget.mouseReleaseEvent = self._plate_release
        layout.addWidget(map_widget)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        self._grp_scroll = QScrollArea()
        self._grp_scroll.setWidgetResizable(True)
        self._grp_inner = QWidget()
        self._grp_inner_layout = QVBoxLayout(self._grp_inner)
        self._grp_inner_layout.setContentsMargins(4, 2, 4, 2)
        self._grp_inner_layout.addStretch(1)
        self._grp_scroll.setWidget(self._grp_inner)
        layout.addWidget(self._grp_scroll, 1)

    def _tok_at(self, global_pos) -> Optional[str]:
        for tok, btn in self._map_btns.items():
            if btn.isVisible() and btn.rect().contains(btn.mapFromGlobal(global_pos)):
                return tok
        return None

    def _plate_press(self, event) -> None:
        tok = self._tok_at(event.globalPosition().toPoint())
        if tok is None or tok not in self._app._well_paths:
            return
        grp = self._active_group()
        if grp is None:
            return
        self._drag_adding = tok not in grp.wells
        self._drag_visited = set()
        self._apply_drag(tok)

    def _plate_move(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton):
            return
        tok = self._tok_at(event.globalPosition().toPoint())
        if tok and tok not in self._drag_visited:
            self._apply_drag(tok)

    def _plate_release(self, _event) -> None:
        if self._drag_visited:
            self._refresh_map()
            self._refresh_group_list()
        self._drag_visited = set()

    def _build_output_panel(self, layout: QVBoxLayout) -> None:
        hdr = QHBoxLayout()
        hdr.setContentsMargins(12, 4, 12, 4)
        t = QLabel("OUTPUT SETTINGS")
        f = t.font(); f.setBold(True); t.setFont(f)
        hdr.addWidget(t); hdr.addStretch(1)
        layout.addLayout(hdr)

        out_row = QHBoxLayout()
        out_row.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("Folder:")
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        out_row.addWidget(lbl)
        self._out_dir_edit = QLineEdit(self._out_dir_value)
        self._out_dir_edit.setMinimumWidth(240)
        out_row.addWidget(self._out_dir_edit, 1)
        out_row.addWidget(btn_secondary(None, "Browse\u2026", self._browse_out_dir))
        layout.addLayout(out_row)

        fmt_row = QHBoxLayout()
        fmt_row.setContentsMargins(12, 2, 12, 2)
        flbl = QLabel("Format:")
        f = flbl.font(); f.setBold(True); flbl.setFont(f)
        fmt_row.addWidget(flbl)
        self._fmt_cb = QComboBox()
        self._fmt_cb.addItems(["png", "svg", "eps", "pdf"])
        self._fmt_cb.setCurrentText(self._fmt_value)
        self._fmt_cb.currentTextChanged.connect(self._on_fmt_change)
        fmt_row.addWidget(self._fmt_cb)
        self._fmt_hint = QLabel("300 DPI raster")
        fmt_row.addWidget(self._fmt_hint)
        fmt_row.addStretch(1)
        layout.addLayout(fmt_row)

        self._build_export_profile_row(layout)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        info = QLabel(
            "Each export group produces:\n"
            "  \u2022 One figure with one line per group member\n"
            "    (ReplicateSet = mean of its wells, Solo well = raw)\n"
            "  \u2022 One CSV with per-member time-series data\n\n"
            + ("Groups come from Sample Definitions in the left sidebar.\n" if self._use_sidebar_groups else "Groups are defined in the left panel.\n")
            + "No statistics are computed across group members.\n"
              "SD/SEM is only computed within a ReplicateSet."
        )
        info.setWordWrap(True)
        info.setContentsMargins(12, 4, 12, 4)
        layout.addWidget(info)

        run_row = QHBoxLayout()
        run_row.setContentsMargins(12, 8, 12, 8)
        self._run_btn = QPushButton("\u25b6  Run Batch Export")
        self._run_btn.setProperty("variant", "primary")
        self._run_btn.clicked.connect(self._run_batch)
        run_row.addWidget(self._run_btn)
        self._prog_lbl = QLabel("")
        run_row.addWidget(self._prog_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setFixedWidth(180)
        self._prog_bar.setVisible(False)
        run_row.addWidget(self._prog_bar)
        run_row.addStretch(1)
        layout.addLayout(run_row)
        layout.addStretch(1)

    def _build_export_profile_row(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(12, 2, 12, 2)
        lbl = QLabel("Style Preset:")
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        row.addWidget(lbl)
        self._profile_combo = QComboBox()
        self._profile_combo.addItems(self._export_profile_names())
        if self._export_profile_value not in self._export_profile_names():
            self._export_profile_value = "Custom"
        self._profile_combo.setCurrentText(self._export_profile_value)
        self._profile_combo.currentTextChanged.connect(self._on_export_profile_selected)
        row.addWidget(self._profile_combo)
        row.addStretch(1)
        layout.addLayout(row)
        self._apply_export_profile_to_prefs(self._export_profile_value)

    def _export_profile_names(self) -> List[str]:
        from well_viewer.figure_export_editor import _get_all_profile_names

        names = _get_all_profile_names(self._app)
        return names or ["Custom"]

    def _refresh_export_profile_choices(self) -> None:
        names = self._export_profile_names()
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        self._profile_combo.addItems(names)
        current = self._export_profile_value if self._export_profile_value in names else "Custom"
        self._profile_combo.setCurrentText(current)
        self._profile_combo.blockSignals(False)

    def _apply_export_profile_to_prefs(self, profile_name: str) -> None:
        from well_viewer.figure_export_editor import (
            EXPORT_PROFILES,
            _ensure_custom_export_profiles,
            _ensure_export_style_prefs,
        )

        name = str(profile_name or "Custom")
        prefs = _ensure_export_style_prefs(self._app)
        custom_profiles = _ensure_custom_export_profiles(self._app)
        overrides = EXPORT_PROFILES.get(name) or custom_profiles.get(name) or {}
        prefs["export_profile"] = name
        for key, value in overrides.items():
            prefs[key] = value
        fmt = str(prefs.get("format", self._fmt_cb.currentText() or "png")).lower()
        if fmt in {"png", "svg", "eps", "pdf"}:
            self._fmt_cb.setCurrentText(fmt)
            self._on_fmt_change(fmt)

    def _on_export_profile_selected(self, text: str) -> None:
        self._export_profile_value = text
        self._apply_export_profile_to_prefs(text)

    def _on_fmt_change(self, text: str = None) -> None:
        if text is None:
            text = self._fmt_cb.currentText()
        hints = {"png": "300 DPI raster", "svg": "vector \u2014 text editable",
                 "eps": "vector \u2014 text editable", "pdf": "vector"}
        self._fmt_hint.setText(hints.get(text, ""))

    def _browse_out_dir(self) -> None:
        current = self._out_dir_edit.text() or ""
        chosen = QFileDialog.getExistingDirectory(self, "Select output directory", current)
        if chosen:
            self._out_dir_edit.setText(chosen)

    def _active_group(self) -> Optional[BarGroup]:
        if 0 <= self._active_grp < len(self._groups):
            return self._groups[self._active_grp]
        return None

    def _default_group_name(self, grp: BarGroup) -> str:
        labels = [r.name for r in grp.members]
        labels.extend(grp.solo_wells)
        if not labels:
            return "New Group"
        return ", ".join(labels)

    def _refresh_auto_group_name(self, grp: Optional[BarGroup]) -> None:
        if grp is None:
            return
        if id(grp) in self._auto_named_group_ids:
            grp.name = self._default_group_name(grp)

    def _apply_drag(self, tok: str) -> None:
        if tok in self._drag_visited:
            return
        self._drag_visited.add(tok)
        grp = self._active_group()
        if grp is None or tok not in self._app._well_paths:
            return
        rset = next((r for r in self._app._rep_sets if tok in r.wells), None)
        if rset is not None:
            if self._drag_adding:
                if rset not in grp.members:
                    grp.members.append(rset)
            else:
                if rset in grp.members:
                    grp.members.remove(rset)
        else:
            if self._drag_adding:
                if tok not in grp.solo_wells:
                    grp.solo_wells.append(tok)
            else:
                if tok in grp.solo_wells:
                    grp.solo_wells.remove(tok)
        self._refresh_auto_group_name(grp)
        self._refresh_single_btn(tok)

    def _refresh_single_btn(self, tok: str) -> None:
        btn = self._map_btns.get(tok)
        if btn is None or tok not in self._app._well_paths:
            return
        for gi, g in enumerate(self._groups):
            if tok in g.wells:
                c = WELL_COLORS[gi % len(WELL_COLORS)]
                btn.set_colors(c, _CLR_WHITE)
                return
        btn.set_colors("#2a2a2a", TXT_PRI)

    def _refresh_map(self) -> None:
        avail = set(self._app._well_paths.keys())
        tok_color: Dict[str, str] = {}
        for gi, grp in enumerate(self._groups):
            c = WELL_COLORS[gi % len(WELL_COLORS)]
            for w in grp.wells:
                tok_color.setdefault(w, c)
        active_wells: set = set()
        grp = self._active_group()
        if grp:
            for w in grp.wells:
                active_wells.add(w)
        for tok, btn in self._map_btns.items():
            if tok not in avail:
                btn.set_colors("#222", TXT_MUT, enabled=False)
            elif tok in tok_color:
                btn.set_colors(tok_color[tok], _CLR_WHITE, active=(tok in active_wells))
            else:
                btn.set_colors("#2a2a2a", TXT_PRI)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                inner = item.layout()
                if inner is not None:
                    self._clear_layout(inner)

    def _refresh_group_list(self) -> None:
        # Remove everything except the trailing stretch
        while self._grp_inner_layout.count() > 1:
            item = self._grp_inner_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                inner = item.layout()
                if inner is not None:
                    self._clear_layout(inner)

        if not self._groups:
            empty = QLabel("No export groups.  Click + Add or use Quick Setup.")
            empty.setContentsMargins(8, 8, 8, 8)
            self._grp_inner_layout.insertWidget(0, empty)
            self._refresh_map()
            return

        for gi, grp in enumerate(self._groups):
            card = self._build_group_card(gi, grp)
            self._grp_inner_layout.insertWidget(gi, card)

        self._refresh_map()

    def _build_group_card(self, gi: int, grp: BarGroup) -> QWidget:
        is_sel = (gi == self._active_grp)
        color = WELL_COLORS[gi % len(WELL_COLORS)]
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        if is_sel:
            card.setStyleSheet(f"QFrame {{ border: 2px solid {color}; background: #2a2a2a; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 4, 6, 4)

        hdr = QHBoxLayout()
        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {color};")
        hdr.addWidget(dot)
        name_lbl = QLabel(grp.name)
        f = name_lbl.font(); f.setBold(True); name_lbl.setFont(f)
        hdr.addWidget(name_lbl)
        n_mem, n_sol = len(grp.members), len(grp.solo_wells)
        parts = []
        if n_mem:
            parts.append(f"{n_mem} set{'s' if n_mem != 1 else ''}")
        if n_sol:
            parts.append(f"{n_sol} solo well{'s' if n_sol != 1 else ''}")
        if not parts:
            parts = ["empty"]
        summary = QLabel(f"  ({', '.join(parts)})")
        hdr.addWidget(summary)
        hdr.addStretch(1)
        hdr.addWidget(btn_card(None, "Rename", lambda i=gi: self._grp_rename(i)))
        hdr.addWidget(btn_card(None, "Clear", lambda i=gi: self._grp_clear(i)))
        hdr.addWidget(btn_danger(None, "\u2715", lambda i=gi: self._grp_delete(i)))
        card_layout.addLayout(hdr)

        if grp.members or grp.solo_wells:
            for rset in grp.members:
                mrow = QHBoxLayout()
                name_tag = QLabel(f"[{rset.name}]")
                name_tag.setStyleSheet(f"color: {color};")
                mrow.addWidget(name_tag)
                for w in rset.wells:
                    chip = QLabel(w)
                    chip.setStyleSheet(f"background: {color}; color: {_CLR_WHITE}; padding: 1px 3px;")
                    mrow.addWidget(chip)
                if is_sel:
                    mrow.addWidget(btn_danger(None, "\u2212", lambda g=gi, r=rset: self._grp_remove_member(g, r)))
                mrow.addStretch(1)
                card_layout.addLayout(mrow)
            for w in grp.solo_wells:
                srow = QHBoxLayout()
                s_lbl = QLabel(f"[solo] {w}")
                s_lbl.setStyleSheet(f"color: {color};")
                srow.addWidget(s_lbl)
                if is_sel:
                    srow.addWidget(btn_danger(None, "\u2212", lambda g=gi, wl=w: self._grp_remove_solo(g, wl)))
                srow.addStretch(1)
                card_layout.addLayout(srow)

        def _on_click(_event, _idx=gi):
            self._grp_select(_idx)
        card.mousePressEvent = _on_click
        return card

    def _grp_select(self, idx: int) -> None:
        self._active_grp = idx
        self._refresh_group_list()

    def _grp_add(self) -> None:
        grp = BarGroup("New Group")
        self._groups.append(grp)
        self._auto_named_group_ids.add(id(grp))
        self._refresh_auto_group_name(grp)
        self._active_grp = len(self._groups) - 1
        self._refresh_group_list()

    def _grp_rename(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            name = ask_name_dialog(
                self, title="Rename group", prompt="Group name:",
                default=self._groups[idx].name,
            )
            if name:
                grp = self._groups[idx]
                grp.name = name
                self._auto_named_group_ids.discard(id(grp))
                self._refresh_group_list()

    def _grp_clear(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            grp = self._groups[idx]
            grp.members.clear()
            grp.solo_wells.clear()
            self._refresh_auto_group_name(grp)
            self._refresh_group_list()

    def _grp_delete(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            grp = self._groups.pop(idx)
            self._auto_named_group_ids.discard(id(grp))
            self._active_grp = min(self._active_grp, len(self._groups) - 1)
            self._refresh_group_list()

    def _grp_clear_all(self) -> None:
        if not self._groups:
            return
        ret = QMessageBox.question(
            self, "Clear all groups?",
            f"Remove all {len(self._groups)} group(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self._groups.clear()
            self._auto_named_group_ids.clear()
            self._active_grp = -1
            self._refresh_group_list()

    def _grp_remove_member(self, grp_idx: int, rset) -> None:
        if 0 <= grp_idx < len(self._groups):
            grp = self._groups[grp_idx]
            if rset in grp.members:
                grp.members.remove(rset)
            self._refresh_auto_group_name(grp)
            self._refresh_group_list()

    def _grp_remove_solo(self, grp_idx: int, well: str) -> None:
        if 0 <= grp_idx < len(self._groups):
            grp = self._groups[grp_idx]
            if well in grp.solo_wells:
                grp.solo_wells.remove(well)
            self._refresh_auto_group_name(grp)
            self._refresh_group_list()

    def _quick_by_row(self) -> None:
        self._groups.clear()
        self._auto_named_group_ids.clear()
        self._active_grp = -1
        for row_ltr in _PLATE_ROWS:
            row_rsets = [r for r in self._app._rep_sets
                         if any(w[0].upper() == row_ltr for w in r.wells)]
            assigned_wells = {w for r in row_rsets for w in r.wells}
            row_solos = [tok for tok in self._app._well_paths
                         if tok[0].upper() == row_ltr and tok not in assigned_wells]
            if not row_rsets and not row_solos:
                continue
            grp = BarGroup(f"Row {row_ltr}", members=row_rsets, solo_wells=row_solos)
            self._groups.append(grp)
        if self._groups:
            self._active_grp = 0
        self._refresh_group_list()

    def _quick_by_col(self) -> None:
        self._groups.clear()
        self._auto_named_group_ids.clear()
        self._active_grp = -1
        for col in _PLATE_COLS:
            col_rsets = [r for r in self._app._rep_sets
                         if any(w[1:] == col for w in r.wells)]
            assigned_wells = {w for r in col_rsets for w in r.wells}
            col_solos = [tok for tok in self._app._well_paths
                         if tok[1:] == col and tok not in assigned_wells]
            if not col_rsets and not col_solos:
                continue
            grp = BarGroup(f"Col {col}", members=col_rsets, solo_wells=col_solos)
            self._groups.append(grp)
        if self._groups:
            self._active_grp = 0
        self._refresh_group_list()

    def _sync_from_app(self) -> None:
        self._groups = self._groups_from_rep_sets()
        self._auto_named_group_ids.clear()
        self._active_grp = 0 if self._groups else -1
        self._refresh_group_list()

    def _groups_from_rep_sets(self) -> List[BarGroup]:
        loaded = self._app._rep_sets_loaded()
        if loaded:
            groups = []
            for rset in loaded:
                grp = BarGroup(rset.name)
                grp.members.append(rset)
                groups.append(grp)
            return groups
        return copy.deepcopy(self._app._bar_groups)

    def _save_groups(self) -> None:
        if not self._groups:
            QMessageBox.warning(self, "Nothing to save", "No groups defined yet.")
            return
        rep_set_names: List[str] = []
        seen_sets: set = set()
        grp_list = []
        for grp in self._groups:
            members_names = []
            for rset in grp.members:
                members_names.append(rset.name)
                if rset.name not in seen_sets:
                    seen_sets.add(rset.name)
                    rep_set_names.append(rset.name)
            grp_list.append({
                "name": grp.name,
                "hidden": grp.hidden,
                "members": members_names,
                "solo_wells": list(grp.solo_wells),
            })
        rep_list = []
        for rset in self._app._rep_sets:
            rep_list.append({"name": rset.name, "wells": list(rset.wells)})
        data = {"rep_sets": rep_list, "groups": grp_list}

        path_str, _ = QFileDialog.getSaveFileName(
            self, "Save export groups",
            "export_groups.json",
            "JSON (*.json);;All files (*.*)",
        )
        if not path_str:
            return
        try:
            with open(path_str, "w") as fh:
                json.dump(data, fh, indent=2)
            self._prog_lbl.setText(f"Saved \u2192 {Path(path_str).name}")
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _load_groups(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Load export groups", "",
            "JSON (*.json);;All files (*.*)",
        )
        if not path_str:
            return
        try:
            with open(path_str) as fh:
                data = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", str(exc))
            return

        def _norm(tok: str) -> str:
            tok = tok.strip().upper()
            m = re.match(r"^([A-H])(\d{1,2})$", tok, re.I)
            return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else tok

        def _valid_tok(raw: str) -> Optional[str]:
            n = _norm(raw)
            return n if n in self._app._well_paths else None

        rep_by_name = {r.name: r for r in self._app._rep_sets}

        new_groups: List[BarGroup] = []
        if isinstance(data, dict):
            for item in data.get("groups", []):
                grp = BarGroup(item.get("name", "Group"),
                               hidden=bool(item.get("hidden", False)))
                for rname in item.get("members", []):
                    if rname in rep_by_name:
                        grp.members.append(rep_by_name[rname])
                for raw_tok in item.get("solo_wells", []):
                    n = _valid_tok(raw_tok)
                    if n:
                        grp.solo_wells.append(n)
                new_groups.append(grp)
        elif isinstance(data, list):
            for item in data:
                name = str(item.get("name", "Group"))
                grp = BarGroup(name, hidden=bool(item.get("hidden", False)))
                for rdata in item.get("replicates", []):
                    rname = rdata.get("name", "R")
                    if rname in rep_by_name:
                        grp.members.append(rep_by_name[rname])
                new_groups.append(grp)

        if not new_groups:
            QMessageBox.warning(
                self, "No groups loaded",
                "The file contained no groups that could be matched to the "
                "currently loaded wells and replicate sets.",
            )
            return

        self._groups = new_groups
        self._auto_named_group_ids.clear()
        self._active_grp = 0
        self._refresh_group_list()
        self._prog_lbl.setText(f"Loaded {len(self._groups)} group(s) from {Path(path_str).name}")

    def _resolve_out_dir(self) -> Optional[Path]:
        val = self._out_dir_edit.text().strip()
        if val:
            p = Path(val)
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except OSError as exc:
                QMessageBox.critical(self, "Output directory error",
                                     f"Cannot create:\n{p}\n{exc}")
                return None
        d = self._app._data_dir
        if d and d.is_dir():
            return d
        QMessageBox.critical(self, "No output directory",
                             "Load data or choose an output folder.")
        return None

    def _run_batch_jobs(
        self, *, jobs: list, progress_text_fn, run_job_fn,
        success_text: str, status_text: str,
    ) -> None:
        from PySide6.QtWidgets import QApplication

        self._prog_bar.setVisible(True)
        self._prog_bar.setMaximum(max(len(jobs), 1))
        self._prog_bar.setValue(0)
        self._run_btn.setEnabled(False)
        errors: List[str] = []
        try:
            for step, job in enumerate(jobs, 1):
                self._prog_lbl.setText(progress_text_fn(job, step, len(jobs)))
                self._prog_bar.setValue(step - 1)
                QApplication.processEvents()
                err = run_job_fn(job)
                if err:
                    errors.append(err)
            self._prog_bar.setValue(len(jobs))
        finally:
            self._run_btn.setEnabled(True)
            self._prog_bar.setVisible(False)

        if errors:
            self._prog_lbl.setText(f"Done with {len(errors)} error(s). See log.")
            self._prog_lbl.setStyleSheet(f"color: {_CLR_DANGER};")
            for err in errors:
                _logger.error("Batch export error: %s", err)
            return
        self._prog_lbl.setText(success_text)
        self._prog_lbl.setStyleSheet(f"color: {_CLR_SUCCESS_DARK};")
        self._app._set_status(status_text)

    def _save_figure(self, fig, fig_path: Path, fmt: str) -> None:
        import matplotlib as _mpl
        import matplotlib.pyplot as _plt
        from well_viewer.figure_export_editor import (
            _ensure_export_style_prefs,
            apply_export_style_prefs,
        )

        apply_export_style_prefs(fig, _ensure_export_style_prefs(self._app))

        orig_svg = _mpl.rcParams.get("svg.fonttype", "path")
        orig_ps = _mpl.rcParams.get("ps.fonttype", 3)
        try:
            if fmt == "svg":
                _mpl.rcParams["svg.fonttype"] = "none"
            elif fmt == "eps":
                _mpl.rcParams["ps.fonttype"] = 42
            kw = dict(bbox_inches="tight", facecolor=PLOT_BG, format=fmt)
            if fmt == "png":
                kw["dpi"] = 300
            fig.savefig(str(fig_path), **kw)
        finally:
            _mpl.rcParams["svg.fonttype"] = orig_svg
            _mpl.rcParams["ps.fonttype"] = orig_ps
            _plt.close(fig)

    def _groups_for_export(self) -> List[BarGroup]:
        if self._use_sidebar_groups:
            sidebar_groups = copy.deepcopy(getattr(self._app, "_bar_groups", []))
            if sidebar_groups and any(g.wells for g in sidebar_groups):
                return sidebar_groups
            return self._groups_from_rep_sets()
        return list(self._groups)

    def _run_batch(self) -> None:
        groups_with_data = [g for g in self._groups_for_export()
                            if any(w in self._app._well_paths for w in g.wells)]
        if not groups_with_data:
            msg = (
                "Define at least one non-empty group in Sample Definitions."
                if self._use_sidebar_groups
                else "Define at least one non-empty group."
            )
            QMessageBox.warning(self, "No groups", msg)
            return
        self._log_sample_definitions_snapshot(groups_with_data)
        out_dir = self._resolve_out_dir()
        if out_dir is None:
            return

        threshold = self._app._get_thresh_frac_on(self._app._active_channel)
        use_sem = self._app._use_sem.get()
        band_lbl = "SEM" if use_sem else "SD"
        fmt = self._fmt_cb.currentText()

        def _progress(grp: BarGroup, step: int, total: int) -> str:
            return f"Exporting '{grp.name}' ({step}/{total})\u2026"

        def _run_group(grp: BarGroup) -> Optional[str]:
            safe = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
            csv_path = out_dir / f"batch_{safe}.csv"
            fig_path = out_dir / f"batch_{safe}.{fmt}"

            try:
                rows_out: List[dict] = []
                for rset in grp.members:
                    valid_wells = [w for w in rset.wells if w in self._app._well_paths]
                    if not valid_wells:
                        continue
                    all_rows: List[dict] = []
                    for w in valid_wells:
                        all_rows.extend(self._app._get_rows(w))
                    _val_col = self._app._active_val_col
                    _ch = self._app._active_channel
                    _cell_area_threshold = self._app._get_cell_area_threshold()
                    _fluor_gates = self._app._get_all_fluor_gates()
                    pts = aggregate_with_threshold(
                        all_rows, threshold, use_sem=use_sem,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    )
                    for t, mean, sd, frac, n_above, n_total in pts:
                        rows_out.append({
                            "group": grp.name, "member": rset.name,
                            "member_type": "replicate_set",
                            "wells": ";".join(valid_wells), "n_wells": len(valid_wells),
                            "time_h": f"{t:.4f}",
                            f"mean_{_ch}": f"{mean:.6f}" if not math.isnan(mean) else "",
                            f"{'sem' if use_sem else 'sd'}_{_ch}": f"{sd:.6f}",
                            "fraction_above": f"{frac:.6f}" if not math.isnan(frac) else "",
                            "threshold": f"{threshold:.4f}",
                        })
                for w in grp.solo_wells:
                    if w not in self._app._well_paths:
                        continue
                    _val_col = self._app._active_val_col
                    _ch = self._app._active_channel
                    _cell_area_threshold = self._app._get_cell_area_threshold()
                    _fluor_gates = self._app._get_all_fluor_gates()
                    pts = aggregate_with_threshold(
                        self._app._get_rows(w), threshold, use_sem=use_sem,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    )
                    for t, mean, sd, frac, n_above, n_total in pts:
                        rows_out.append({
                            "group": grp.name, "member": w, "member_type": "solo_well",
                            "wells": w, "n_wells": 1, "time_h": f"{t:.4f}",
                            f"mean_{_ch}": f"{mean:.6f}" if not math.isnan(mean) else "",
                            f"{'sem' if use_sem else 'sd'}_{_ch}": f"{sd:.6f}",
                            "fraction_above": f"{frac:.6f}" if not math.isnan(frac) else "",
                            "threshold": f"{threshold:.4f}",
                        })
                if rows_out:
                    _ch = self._app._active_channel
                    fieldnames = ["group", "member", "member_type", "wells", "n_wells",
                                  "time_h", f"mean_{_ch}",
                                  f"{'sem' if use_sem else 'sd'}_{_ch}",
                                  "fraction_above", "threshold"]
                    with open(csv_path, "w", newline="") as fh:
                        writer = csv.DictWriter(fh, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows_out)
            except OSError as exc:
                return f"{grp.name} CSV: {exc}"

            try:
                fig = self._render_group_figure(grp, threshold, use_sem, band_lbl)
                self._save_figure(fig, fig_path, fmt)
            except Exception as exc:
                return f"{grp.name} figure: {exc}"

            _logger.info("Batch: wrote %s and %s", csv_path.name, fig_path.name)
            return None

        self._run_batch_jobs(
            jobs=groups_with_data,
            progress_text_fn=_progress,
            run_job_fn=_run_group,
            success_text=f"\u2713 {len(groups_with_data)} group(s) \u2192 {out_dir.name}/",
            status_text=f"Batch export: {len(groups_with_data)} group(s) \u2192 {out_dir}",
        )

    def _log_sample_definitions_snapshot(self, groups_for_export: List[BarGroup]) -> None:
        rep_sets = getattr(self._app, "_rep_sets", [])
        bar_groups = getattr(self._app, "_bar_groups", [])
        rep_summary = [f"{r.name}={len(r.wells)}w" for r in rep_sets]
        grp_summary = [f"{g.name}={len(g.wells)}w" for g in bar_groups]
        export_summary = [f"{g.name}={len(g.wells)}w" for g in groups_for_export]
        _logger.info(
            "Run Batch Export clicked | rep_sets=%s | bar_groups=%s | groups_for_export=%s",
            rep_summary, grp_summary, export_summary,
        )

    def _render_group_figure(
        self, grp: BarGroup, threshold: float, use_sem: bool, band_lbl: str,
    ):
        from matplotlib.figure import Figure as _Figure

        fig = _Figure(figsize=(10, 11), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(3, 1, 1)
        ax_frac = fig.add_subplot(3, 1, 2, sharex=ax_mean)
        ax_cdf = fig.add_subplot(3, 1, 3)
        fig.subplots_adjust(hspace=0.55, top=0.92, bottom=0.07, left=0.13, right=0.97)
        fig.suptitle(grp.name, fontsize=11, fontweight="bold", color=TXT_PRI, y=0.97)

        legend_kw = dict(fontsize=7, framealpha=0.9, facecolor=PLOT_BG,
                         edgecolor=PLOT_SPN, labelcolor=TXT_PRI)
        _ch = self._app._active_channel.upper()
        apply_ax_style(ax_mean, f"Mean {_ch} (above threshold) \u00b1 {band_lbl}", f"Mean {_ch}")
        apply_ax_style(ax_frac, "Fraction of Cells Above Threshold", "Fraction")
        apply_ax_style(ax_cdf, f"{_ch} Value CDF", "Cumulative fraction")
        ax_frac.set_xlabel("Time (hours)", fontsize=8, labelpad=5)
        ax_frac.set_ylim(-0.05, 1.05)
        ax_cdf.set_xlabel(f"{_ch} mean intensity", fontsize=8, labelpad=5)
        ax_cdf.set_ylim(-0.02, 1.05)

        any_ts = any_cdf = False
        all_fluor_vals: List[float] = []

        members: List[tuple] = []
        for rset in grp.members:
            valid = [w for w in rset.wells if w in self._app._well_paths]
            if not valid:
                continue
            members.append(("replicate", rset, valid, self._app._replicate_display_label(rset)))
        for w in grp.solo_wells:
            if w not in self._app._well_paths:
                continue
            members.append(("well", w, [w], w))

        _val_col = self._app._active_val_col
        _cell_area_threshold = self._app._get_cell_area_threshold()
        _fluor_gates = self._app._get_all_fluor_gates()
        for mi, (member_type, member_key, valid_wells, display_name) in enumerate(members):
            color = WELL_COLORS[mi % len(WELL_COLORS)]
            if member_type == "replicate":
                rset = member_key
                all_tps: set = set()
                fluor_vals_raw: List[float] = []
                for lbl in valid_wells:
                    rows = self._app._get_rows(lbl)
                    for t, *_ in aggregate_with_threshold(
                        rows, threshold, use_sem=False,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    ):
                        all_tps.add(t)
                    fluor_vals_raw.extend(_all_fluor_values(rows, val_col=_val_col))
                agg_times, agg_means, agg_errs, agg_fracs = [], [], [], []
                for t in sorted(all_tps):
                    gm, gerr, gf, _ = self._app._compute_rep_stats(rset, t, threshold, use_sem)
                    if not math.isnan(gm):
                        agg_times.append(t); agg_means.append(gm)
                        agg_errs.append(gerr); agg_fracs.append(gf)

                if agg_times:
                    ax_mean.plot(agg_times, agg_means, color=color, lw=2, marker="o",
                                 markersize=4, label=display_name, zorder=3)
                    ax_mean.fill_between(
                        agg_times,
                        [m - e for m, e in zip(agg_means, agg_errs)],
                        [m + e for m, e in zip(agg_means, agg_errs)],
                        color=color, alpha=0.15, zorder=2,
                    )
                    vf = [(t, f) for t, f in zip(agg_times, agg_fracs) if not math.isnan(f)]
                    if vf:
                        vt2, vf2 = zip(*vf)
                        ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s",
                                     markersize=3, label=display_name, zorder=3)
                        ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                    any_ts = True

                fluor_vals = sorted(fluor_vals_raw)
            else:
                rows = self._app._get_rows(member_key)
                pts = aggregate_with_threshold(
                    rows, threshold, use_sem=use_sem,
                    val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                    fluor_gates=_fluor_gates,
                )
                if pts:
                    times, means, spreads, fracs, *_ = zip(*pts)
                    vm = [(t, m, s) for t, m, s in zip(times, means, spreads) if not math.isnan(m)]
                    if vm:
                        vt, vmm, vs = zip(*vm)
                        ax_mean.plot(vt, vmm, color=color, lw=2, marker="o",
                                     markersize=4, label=display_name, zorder=3)
                        ax_mean.fill_between(
                            vt,
                            [m - s for m, s in zip(vmm, vs)],
                            [m + s for m, s in zip(vmm, vs)],
                            color=color, alpha=0.15, zorder=2,
                        )
                    vf = [(t, f) for t, f in zip(times, fracs) if not math.isnan(f)]
                    if vf:
                        vt2, vf2 = zip(*vf)
                        ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s",
                                     markersize=3, label=display_name, zorder=3)
                        ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                    any_ts = True

                fluor_vals = sorted(_all_fluor_values(rows, val_col=_val_col))

            all_fluor_vals.extend(fluor_vals)
            if fluor_vals:
                n = len(fluor_vals)
                ax_cdf.plot(fluor_vals, [(k + 1) / n for k in range(n)],
                            color=color, lw=1.8,
                            label=f"{display_name} (n={n:,})", zorder=3)
                any_cdf = True

        if any_ts:
            ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--", alpha=0.8)
            ax_mean.legend(**legend_kw)
            ax_frac.legend(**legend_kw)
        if any_cdf:
            ax_cdf.axvline(threshold, color=WARN, lw=1.2, ls="--",
                           label=f"threshold={threshold:.2f}", zorder=5)
            if all_fluor_vals:
                lo, hi = min(all_fluor_vals), max(all_fluor_vals)
                ax_cdf.axvspan(threshold, hi, alpha=0.05, color=WARN, zorder=1)
                ax_cdf.set_xlim(lo, hi)
            ax_cdf.legend(**legend_kw)

        return fig


class BarBatchExportPanel(BatchExportPanel):
    """Bar-plot batch export — same group editor + timepoint multi-select."""

    def __init__(
        self,
        app,
        parent: Optional[QWidget] = None,
        *,
        use_sidebar_groups: bool = False,
    ) -> None:
        super().__init__(app, parent, use_sidebar_groups=use_sidebar_groups)

    def _build_output_panel(self, layout: QVBoxLayout) -> None:
        hdr = QHBoxLayout()
        hdr.setContentsMargins(12, 4, 12, 4)
        t = QLabel("OUTPUT SETTINGS")
        f = t.font(); f.setBold(True); t.setFont(f)
        hdr.addWidget(t); hdr.addStretch(1)
        layout.addLayout(hdr)

        out_row = QHBoxLayout()
        out_row.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("Folder:")
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        out_row.addWidget(lbl)
        self._out_dir_edit = QLineEdit(self._out_dir_value)
        self._out_dir_edit.setMinimumWidth(240)
        out_row.addWidget(self._out_dir_edit, 1)
        out_row.addWidget(btn_secondary(None, "Browse\u2026", self._browse_out_dir))
        layout.addLayout(out_row)

        fmt_row = QHBoxLayout()
        fmt_row.setContentsMargins(12, 2, 12, 2)
        flbl = QLabel("Format:")
        f = flbl.font(); f.setBold(True); flbl.setFont(f)
        fmt_row.addWidget(flbl)
        self._fmt_cb = QComboBox()
        self._fmt_cb.addItems(["png", "svg", "eps", "pdf"])
        self._fmt_cb.setCurrentText(self._fmt_value)
        self._fmt_cb.currentTextChanged.connect(self._on_fmt_change)
        fmt_row.addWidget(self._fmt_cb)
        self._fmt_hint = QLabel("300 DPI raster")
        fmt_row.addWidget(self._fmt_hint)
        fmt_row.addStretch(1)
        layout.addLayout(fmt_row)
        self._build_export_profile_row(layout)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        tp_hdr = QHBoxLayout()
        tp_hdr.setContentsMargins(12, 0, 12, 2)
        tlbl = QLabel("TIMEPOINTS")
        f = tlbl.font(); f.setBold(True); tlbl.setFont(f)
        tp_hdr.addWidget(tlbl)
        tp_hdr.addStretch(1)
        tp_hdr.addWidget(btn_secondary(None, "All", self._tp_select_all))
        tp_hdr.addWidget(btn_secondary(None, "None", self._tp_clear_all))
        layout.addLayout(tp_hdr)

        self._tp_lb = QListWidget()
        self._tp_lb.setSelectionMode(QAbstractItemView.MultiSelection)
        self._tp_lb.setMinimumHeight(120)
        layout.addWidget(self._tp_lb, 1)

        self._app._update_bar_tp_menu()
        tp_vals = [self._app._bar_tp_cb.itemText(i)
                   for i in range(self._app._bar_tp_cb.count())]
        for tp in tp_vals:
            if tp and tp != "\u2014":
                item = QListWidgetItem(tp)
                self._tp_lb.addItem(item)
        self._tp_select_all()

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        info = QLabel(
            "Each group \u00d7 timepoint produces:\n"
            "  \u2022 One bar figure (one bar per replicate set or well)\n"
            "  \u2022 One CSV row per member at that timepoint\n\n"
            + ("Groups come from Sample Definitions in the left sidebar.\n"
               if self._use_sidebar_groups
               else "Groups are defined in the left panel.\n")
            + "SD/SEM is computed within each ReplicateSet only."
        )
        info.setWordWrap(True)
        info.setContentsMargins(12, 4, 12, 4)
        layout.addWidget(info)

        run_row = QHBoxLayout()
        run_row.setContentsMargins(12, 8, 12, 8)
        self._run_btn = QPushButton("\u25b6  Run Batch Export")
        self._run_btn.setProperty("variant", "primary")
        self._run_btn.clicked.connect(self._run_batch)
        run_row.addWidget(self._run_btn)
        self._prog_lbl = QLabel("")
        run_row.addWidget(self._prog_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setFixedWidth(180)
        self._prog_bar.setVisible(False)
        run_row.addWidget(self._prog_bar)
        run_row.addStretch(1)
        layout.addLayout(run_row)

    def _tp_select_all(self) -> None:
        for i in range(self._tp_lb.count()):
            self._tp_lb.item(i).setSelected(True)

    def _tp_clear_all(self) -> None:
        self._tp_lb.clearSelection()

    def _selected_tps(self) -> List[str]:
        return [it.text() for it in self._tp_lb.selectedItems()]

    def _run_batch(self) -> None:
        groups_with_data = _groups_with_loaded_wells(
            self._groups_for_export(), self._app._well_paths,
        )
        if not groups_with_data:
            msg = (
                "Define at least one non-empty group in Sample Definitions."
                if self._use_sidebar_groups
                else "Define at least one non-empty group."
            )
            QMessageBox.warning(self, "No groups", msg)
            return
        self._log_sample_definitions_snapshot(groups_with_data)

        selected_tps = self._selected_tps()
        if not selected_tps:
            QMessageBox.warning(self, "No timepoints", "Select at least one timepoint.")
            return

        out_dir = self._resolve_out_dir()
        if out_dir is None:
            return

        threshold = self._app._get_thresh_frac_on(self._app._active_channel)
        use_sem = self._app._use_sem.get()
        band_lbl = "SEM" if use_sem else "SD"
        fmt = self._fmt_cb.currentText()
        jobs = [(grp, tp_str) for grp in groups_with_data for tp_str in selected_tps]

        def _progress(job, step: int, total: int) -> str:
            grp, tp_str = job
            return f"'{grp.name}' @ t={tp_str}h  ({step}/{total})"

        def _run_job(job) -> Optional[str]:
            grp, tp_str = job
            safe_grp = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
            try:
                target_t = float(tp_str)
            except ValueError:
                return f"{grp.name} t={tp_str}: invalid timepoint"

            safe_tp = tp_str.replace(".", "_").replace("-", "m")
            base = out_dir / f"bar_{safe_grp}_t{safe_tp}"

            try:
                _val_col = self._app._active_val_col
                _ch = self._app._active_channel
                rows_csv: List[dict] = []
                _cell_area_threshold = self._app._get_cell_area_threshold()
                _fluor_gates = self._app._get_all_fluor_gates()
                for rset in grp.members:
                    valid = [w for w in rset.wells if w in self._app._well_paths]
                    if not valid:
                        continue
                    combined: List[dict] = []
                    for w in valid:
                        combined.extend(self._app._get_rows(w))
                    pts = aggregate_with_threshold(
                        combined, threshold, use_sem=use_sem,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    )
                    matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
                    if matched:
                        _, m, s, f, *_ = matched[0]
                        rows_csv.append({
                            "group": grp.name,
                            "member": rset.name,
                            "member_type": "replicate_set",
                            "n_wells": len(valid),
                            "timepoint_h": tp_str,
                            f"mean_{_ch}": f"{m:.6f}" if not math.isnan(m) else "",
                            f"{band_lbl.lower()}_{_ch}": f"{s:.6f}",
                            "fraction_above": f"{f:.6f}" if not math.isnan(f) else "",
                            "threshold": f"{threshold:.4f}",
                        })
                for w in grp.solo_wells:
                    if w not in self._app._well_paths:
                        continue
                    pts = aggregate_with_threshold(
                        self._app._get_rows(w), threshold, use_sem=use_sem,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    )
                    matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
                    if matched:
                        _, m, s, f, *_ = matched[0]
                        rows_csv.append({
                            "group": grp.name,
                            "member": w,
                            "member_type": "solo_well",
                            "n_wells": 1,
                            "timepoint_h": tp_str,
                            f"mean_{_ch}": f"{m:.6f}" if not math.isnan(m) else "",
                            f"{band_lbl.lower()}_{_ch}": f"{s:.6f}",
                            "fraction_above": f"{f:.6f}" if not math.isnan(f) else "",
                            "threshold": f"{threshold:.4f}",
                        })
                if rows_csv:
                    fnames = list(rows_csv[0].keys())
                    with open(str(base) + ".csv", "w", newline="") as fh:
                        wrt = csv.DictWriter(fh, fieldnames=fnames)
                        wrt.writeheader()
                        wrt.writerows(rows_csv)
            except Exception as exc:
                return f"{grp.name} t={tp_str} CSV: {exc}"

            try:
                fig = self._render_bar_group_figure(
                    grp, target_t, tp_str, threshold, use_sem, band_lbl,
                )
                self._save_figure(fig, Path(str(base) + f".{fmt}"), fmt)
            except Exception as exc:
                return f"{grp.name} t={tp_str} figure: {exc}"
            return None

        self._run_batch_jobs(
            jobs=jobs,
            progress_text_fn=_progress,
            run_job_fn=_run_job,
            success_text=f"\u2713 {len(groups_with_data)}g \u00d7 {len(selected_tps)}t \u2192 {out_dir.name}/",
            status_text=f"Bar batch export complete \u2192 {out_dir}",
        )

    def _render_bar_group_figure(
        self, grp: BarGroup, target_t: float, tp_str: str,
        threshold: float, use_sem: bool, band_lbl: str,
    ):
        from matplotlib.figure import Figure as _Figure

        fig = _Figure(figsize=(8, 7), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(2, 1, 1)
        ax_frac = fig.add_subplot(2, 1, 2)
        fig.subplots_adjust(hspace=0.55, top=0.92, bottom=0.12,
                            left=0.13, right=0.97)
        fig.suptitle(f"{grp.name}  \u2014  t = {tp_str} h",
                     fontsize=10, fontweight="bold", color=TXT_PRI, y=0.97)
        _ch = self._app._active_channel.upper()
        apply_ax_style(ax_mean,
                       f"Mean {_ch} (above threshold) \u00b1 {band_lbl}",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac, "Fraction of Cells Above Threshold", "Fraction")
        ax_frac.set_ylim(-0.05, 1.05)

        members: List[tuple] = []
        for rset in grp.members:
            valid = [w for w in rset.wells if w in self._app._well_paths]
            if not valid:
                continue
            combined: List[dict] = []
            for w in valid:
                combined.extend(self._app._get_rows(w))
            members.append((self._app._replicate_display_label(rset), combined))
        for w in grp.solo_wells:
            if w not in self._app._well_paths:
                continue
            members.append((w, self._app._get_rows(w)))

        if not members:
            return fig

        _cell_area_threshold = self._app._get_cell_area_threshold()
        _fluor_gates = self._app._get_all_fluor_gates()
        draw_items: List[tuple] = []
        xlabels: List[str] = []
        for i, (name, rows) in enumerate(members):
            color = WELL_COLORS[i % len(WELL_COLORS)]
            pts = aggregate_with_threshold(
                rows, threshold, use_sem=use_sem,
                cell_area_threshold=_cell_area_threshold, fluor_gates=_fluor_gates,
            )
            matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
            xlabels.append(name)
            if matched:
                _t, m, s, f, *extra = matched[0]
                frac_spread = float(extra[0]) if extra else 0.0
                has_data = not math.isnan(m)
                draw_items.append((name, name, m, s, f, frac_spread, has_data, color))
            else:
                draw_items.append((name, name, float("nan"), 0.0, float("nan"), 0.0, False, color))

        _bar_render_items(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            use_groups=True,
            items=draw_items,
            xlabels=xlabels,
            threshold=threshold,
            well_colors=WELL_COLORS,
            warn_color=WARN,
            border_color="#333",
            placeholder_color=_CLR_PLACEHOLDER,
            disabled_well_color=_CLR_DISABLED_WELL,
            err_bar_color=_CLR_ERR_BAR,
        )
        return fig


class ScatterBatchExportPanel(BatchExportPanel):
    """Batch exporter for Scatter Plot (cells/aggregate)."""

    def __init__(
        self,
        app,
        parent: Optional[QWidget] = None,
        *,
        scatter_mode: str = "cells",
        use_sidebar_groups: bool = False,
    ) -> None:
        self._scatter_mode = "aggregate" if scatter_mode == "aggregate" else "cells"
        super().__init__(app, parent, use_sidebar_groups=use_sidebar_groups)

    def _build_output_panel(self, layout: QVBoxLayout) -> None:
        hdr = QHBoxLayout()
        hdr.setContentsMargins(12, 4, 12, 4)
        title = "OUTPUT SETTINGS \u2014 SCATTER CELLS" if self._scatter_mode == "cells" else "OUTPUT SETTINGS \u2014 SCATTER AGGREGATE"
        t = QLabel(title)
        f = t.font(); f.setBold(True); t.setFont(f)
        hdr.addWidget(t); hdr.addStretch(1)
        layout.addLayout(hdr)

        out_row = QHBoxLayout()
        out_row.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("Folder:")
        f = lbl.font(); f.setBold(True); lbl.setFont(f)
        out_row.addWidget(lbl)
        self._out_dir_edit = QLineEdit(self._out_dir_value)
        self._out_dir_edit.setMinimumWidth(240)
        out_row.addWidget(self._out_dir_edit, 1)
        out_row.addWidget(btn_secondary(None, "Browse\u2026", self._browse_out_dir))
        layout.addLayout(out_row)

        fmt_row = QHBoxLayout()
        fmt_row.setContentsMargins(12, 2, 12, 2)
        flbl = QLabel("Format:")
        f = flbl.font(); f.setBold(True); flbl.setFont(f)
        fmt_row.addWidget(flbl)
        self._fmt_cb = QComboBox()
        self._fmt_cb.addItems(["png", "svg", "eps", "pdf"])
        self._fmt_cb.setCurrentText(self._fmt_value)
        self._fmt_cb.currentTextChanged.connect(self._on_fmt_change)
        fmt_row.addWidget(self._fmt_cb)
        self._fmt_hint = QLabel("300 DPI raster")
        fmt_row.addWidget(self._fmt_hint)
        fmt_row.addStretch(1)
        layout.addLayout(fmt_row)
        self._build_export_profile_row(layout)

        opt_row = QHBoxLayout()
        opt_row.setContentsMargins(12, 2, 12, 2)
        if self._scatter_mode == "cells":
            xlbl = QLabel("X:")
            f = xlbl.font(); f.setBold(True); xlbl.setFont(f)
            opt_row.addWidget(xlbl)
            self._sc_cells_x_cb = QComboBox()
            self._sc_cells_x_cb.setMinimumWidth(140)
            opt_row.addWidget(self._sc_cells_x_cb)
            ylbl = QLabel("Y:")
            f = ylbl.font(); f.setBold(True); ylbl.setFont(f)
            opt_row.addWidget(ylbl)
            self._sc_cells_y_cb = QComboBox()
            self._sc_cells_y_cb.setMinimumWidth(140)
            opt_row.addWidget(self._sc_cells_y_cb)
            self._init_scatter_cells_axes()
        else:
            xlbl = QLabel("Stat X:")
            f = xlbl.font(); f.setBold(True); xlbl.setFont(f)
            opt_row.addWidget(xlbl)
            self._sc_agg_x_cb = QComboBox()
            self._sc_agg_x_cb.setMinimumWidth(180)
            opt_row.addWidget(self._sc_agg_x_cb)
            ylbl = QLabel("Stat Y:")
            f = ylbl.font(); f.setBold(True); ylbl.setFont(f)
            opt_row.addWidget(ylbl)
            self._sc_agg_y_cb = QComboBox()
            self._sc_agg_y_cb.setMinimumWidth(180)
            opt_row.addWidget(self._sc_agg_y_cb)
            self._init_scatter_agg_stats()
        opt_row.addStretch(1)
        layout.addLayout(opt_row)

        tp_hdr = QHBoxLayout()
        tp_hdr.setContentsMargins(12, 4, 12, 2)
        tlbl = QLabel("TIMEPOINTS")
        f = tlbl.font(); f.setBold(True); tlbl.setFont(f)
        tp_hdr.addWidget(tlbl)
        tp_hdr.addStretch(1)
        tp_hdr.addWidget(btn_secondary(None, "All", self._tp_select_all))
        tp_hdr.addWidget(btn_secondary(None, "None", self._tp_clear_all))
        layout.addLayout(tp_hdr)

        self._tp_lb = QListWidget()
        self._tp_lb.setSelectionMode(QAbstractItemView.MultiSelection)
        self._tp_lb.setMinimumHeight(120)
        layout.addWidget(self._tp_lb, 1)
        self._init_timepoint_dropdown()

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(12, 0, 12, 4)
        self._scatter_split_tp_cb = QCheckBox(
            "Separate file per selected timepoint (otherwise combine all selected timepoints per group)"
        )
        self._scatter_split_tp_cb.setChecked(True)
        mode_row.addWidget(self._scatter_split_tp_cb)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        info = QLabel(
            "Each group \u00d7 timepoint produces one scatter figure and one CSV.\n"
            "Groups are selected with the same Batch Export group picker."
        )
        info.setWordWrap(True)
        info.setContentsMargins(12, 4, 12, 4)
        layout.addWidget(info)

        run_row = QHBoxLayout()
        run_row.setContentsMargins(12, 8, 12, 8)
        self._run_btn = QPushButton("\u25b6  Run Scatter Batch Export")
        self._run_btn.setProperty("variant", "primary")
        self._run_btn.clicked.connect(self._run_batch)
        run_row.addWidget(self._run_btn)
        self._prog_lbl = QLabel("")
        run_row.addWidget(self._prog_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setFixedWidth(180)
        self._prog_bar.setVisible(False)
        run_row.addWidget(self._prog_bar)
        run_row.addStretch(1)
        layout.addLayout(run_row)

    def _tp_select_all(self) -> None:
        for i in range(self._tp_lb.count()):
            self._tp_lb.item(i).setSelected(True)

    def _tp_clear_all(self) -> None:
        self._tp_lb.clearSelection()

    def _selected_tps(self) -> List[str]:
        return [it.text() for it in self._tp_lb.selectedItems()]

    def _init_timepoint_dropdown(self) -> None:
        timepoints = sorted(set(getattr(self._app, "_all_timepoints_cache", []) or []))
        if not timepoints:
            for lbl in self._app._well_paths:
                for row in self._app._get_rows(lbl):
                    try:
                        tp = float(row.get("timepoint_hours", float("nan")))
                    except (TypeError, ValueError):
                        continue
                    if not math.isnan(tp):
                        timepoints.append(tp)
            timepoints = sorted(set(timepoints))
        tp_vals = [f"{tp:.1f}" for tp in timepoints] if timepoints else ["0.0"]
        self._tp_lb.clear()
        for tp in tp_vals:
            self._tp_lb.addItem(QListWidgetItem(tp))
        self._tp_select_all()

    def _init_scatter_cells_axes(self) -> None:
        channels = list(self._app._fluor_channels) if self._app._fluor_channels else ["gfp"]
        options: List[str] = []
        smfish_channels = set(getattr(self._app, "_smfish_channels", []))
        for ch in channels:
            options.append(ch)
            if ch in smfish_channels:
                options.append(f"{ch} (spots)")
        if not options:
            options = ["gfp"]
        self._sc_cells_x_cb.clear()
        self._sc_cells_x_cb.addItems(options)
        self._sc_cells_y_cb.clear()
        self._sc_cells_y_cb.addItems(options)
        self._sc_cells_x_cb.setCurrentText(options[0])
        self._sc_cells_y_cb.setCurrentText(options[1] if len(options) > 1 else options[0])

    def _init_scatter_agg_stats(self) -> None:
        channels = list(self._app._fluor_channels) if self._app._fluor_channels else ["gfp"]
        stats: List[str] = []
        smfish_channels = set(getattr(self._app, "_smfish_channels", []))
        for ch in channels:
            up = ch.upper()
            stats.append(f"Mean Fluorescence {up}")
            stats.append(f"Fraction On {up}")
            if ch in smfish_channels:
                stats.append(f"smFISH Count {up}")
        self._sc_agg_x_cb.clear()
        self._sc_agg_x_cb.addItems(stats)
        self._sc_agg_y_cb.clear()
        self._sc_agg_y_cb.addItems(stats)
        self._sc_agg_x_cb.setCurrentText(stats[0])
        self._sc_agg_y_cb.setCurrentText(stats[1] if len(stats) > 1 else stats[0])

    def _run_batch(self) -> None:
        groups_with_data = _groups_with_loaded_wells(
            self._groups_for_export(), self._app._well_paths,
        )
        if not groups_with_data:
            QMessageBox.warning(self, "No groups", "Define at least one non-empty group.")
            return
        out_dir = self._resolve_out_dir()
        if out_dir is None:
            return
        selected_tps = self._selected_tps()
        if not selected_tps:
            QMessageBox.warning(self, "No timepoint", "Select a valid timepoint.")
            return
        timepoints: List[float] = []
        for tp_str in selected_tps:
            try:
                timepoints.append(float(tp_str))
            except ValueError:
                continue
        if not timepoints:
            QMessageBox.warning(self, "No timepoint", "Select at least one valid timepoint.")
            return
        fmt = self._fmt_cb.currentText()
        split_by_tp = self._scatter_split_tp_cb.isChecked()
        if split_by_tp:
            jobs = [(grp, tp) for grp in groups_with_data for tp in timepoints]

            def _progress(job, step: int, total: int) -> str:
                grp, tp_h = job
                return f"'{grp.name}' @ t={tp_h:.1f}h ({step}/{total})"

            def _run_job(job) -> Optional[str]:
                grp, tp_h = job
                safe_grp = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
                safe_tp = f"{tp_h:.1f}".replace(".", "_")
                stem = f"scatter_{self._scatter_mode}_{safe_grp}_t{safe_tp}"
                csv_path = out_dir / f"{stem}.csv"
                fig_path = out_dir / f"{stem}.{fmt}"
                if self._scatter_mode == "cells":
                    return self._run_scatter_cells_job(grp, tp_h, csv_path, fig_path, fmt)
                return self._run_scatter_agg_job(grp, tp_h, csv_path, fig_path, fmt)
        else:
            jobs = list(groups_with_data)

            def _progress(job, step: int, total: int) -> str:
                grp = job
                return f"'{grp.name}' all selected tps ({step}/{total})"

            def _run_job(job) -> Optional[str]:
                grp = job
                safe_grp = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
                stem = f"scatter_{self._scatter_mode}_{safe_grp}_all_tps"
                csv_path = out_dir / f"{stem}.csv"
                fig_path = out_dir / f"{stem}.{fmt}"
                if self._scatter_mode == "cells":
                    return self._run_scatter_cells_multi_tp_job(grp, timepoints, csv_path, fig_path, fmt)
                return self._run_scatter_agg_multi_tp_job(grp, timepoints, csv_path, fig_path, fmt)

        self._run_batch_jobs(
            jobs=jobs,
            progress_text_fn=_progress,
            run_job_fn=_run_job,
            success_text=f"\u2713 {len(jobs)} group(s) \u2192 {out_dir.name}/",
            status_text=f"Scatter batch export ({self._scatter_mode}): {len(jobs)} group(s) \u2192 {out_dir}",
        )

    def _run_scatter_cells_job(
        self, grp: BarGroup, tp_h: float, csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        col_x = self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText())
        col_y = self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText())
        old_rep_sets = self._app._rep_sets
        old_selected = self._app._selected_wells
        try:
            self._app._rep_sets = list(grp.members)
            self._app._selected_wells = set(grp.solo_wells)
            ch_x_base = self._sc_cells_x_cb.currentText().split(" ")[0]
            ch_y_base = self._sc_cells_y_cb.currentText().split(" ")[0]
            scatter_data = _collect_scatter_data(
                self._app, col_x, col_y, tp_h,
                well_colors=WELL_COLORS,
                cell_area_threshold=self._app._get_cell_area_threshold(),
                fluor_gate_x=self._app._get_fluor_gate(ch_x_base),
                fluor_gate_y=self._app._get_fluor_gate(ch_y_base),
            )
        finally:
            self._app._rep_sets = old_rep_sets
            self._app._selected_wells = old_selected
        if not scatter_data:
            return f"{grp.name}: no scatter-cells data at t={tp_h:.1f}h"
        try:
            rows: List[dict] = []
            for label, data in scatter_data.items():
                for x, y, meta in zip(data["x"], data["y"], data["metadata"]):
                    well, filename, nuclear_id, _row_idx = meta
                    rows.append({
                        "group": grp.name, "member": label, "well": well,
                        "timepoint_h": f"{tp_h:.4f}",
                        "x": f"{x:.8g}", "y": f"{y:.8g}",
                        "filename": filename, "nucleus_id": nuclear_id,
                    })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "member", "well", "timepoint_h", "x", "y", "filename", "nucleus_id"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-cells CSV: {exc}"
        try:
            from matplotlib.figure import Figure as _Figure
            fig = _Figure(figsize=(8, 6), dpi=300, facecolor=PLOT_BG)
            ax = fig.add_subplot(1, 1, 1)
            for label, data in scatter_data.items():
                ax.scatter(data["x"], data["y"], label=label, color=data["color"],
                           alpha=0.6, s=26, edgecolors="none")
            ax.set_xlabel(col_x)
            ax.set_ylabel(col_y)
            ax.set_title(f"{grp.name} \u2014 Scatter Cells (t={tp_h:.1f}h)")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best", fontsize=8)
            self._save_figure(fig, fig_path, fmt)
        except Exception as exc:
            return f"{grp.name} scatter-cells figure: {exc}"
        return None

    def _run_scatter_agg_job(
        self, grp: BarGroup, tp_h: float, csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        stat_x = self._sc_agg_x_cb.currentText()
        stat_y = self._sc_agg_y_cb.currentText()
        old_rep_sets = self._app._rep_sets
        old_selected = self._app._selected_wells
        try:
            self._app._rep_sets = list(grp.members)
            self._app._selected_wells = set(grp.solo_wells)
            scatter_data = _collect_scatter_agg_data(
                self._app, stat_x, stat_y, [tp_h],
                well_colors=WELL_COLORS,
                aggregate_with_threshold=aggregate_with_threshold,
            )
        finally:
            self._app._rep_sets = old_rep_sets
            self._app._selected_wells = old_selected
        if not scatter_data:
            return f"{grp.name}: no scatter-aggregate data at t={tp_h:.1f}h"
        try:
            rows: List[dict] = []
            for data in scatter_data.values():
                rows.append({
                    "group": grp.name,
                    "label": data.get("label", ""),
                    "timepoint_h": f"{float(data.get('timepoint', tp_h)):.4f}",
                    "x": f"{float(data['x'][0]):.8g}",
                    "y": f"{float(data['y'][0]):.8g}",
                    "x_err": f"{float(data['x_err'][0]):.8g}",
                    "y_err": f"{float(data['y_err'][0]):.8g}",
                })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "label", "timepoint_h", "x", "y", "x_err", "y_err"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-aggregate CSV: {exc}"
        try:
            from matplotlib.figure import Figure as _Figure
            fig = _Figure(figsize=(8, 6), dpi=300, facecolor=PLOT_BG)
            ax = fig.add_subplot(1, 1, 1)
            for data in scatter_data.values():
                ax.errorbar(
                    data["x"], data["y"],
                    xerr=data["x_err"], yerr=data["y_err"],
                    label=data.get("label", ""),
                    color=data["color"], marker=data.get("marker", "o"),
                    linestyle="none", capsize=5, alpha=0.75,
                )
            ax.set_xlabel(stat_x)
            ax.set_ylabel(stat_y)
            ax.set_title(f"{grp.name} \u2014 Scatter Aggregate (t={tp_h:.1f}h)")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best", fontsize=8)
            self._save_figure(fig, fig_path, fmt)
        except Exception as exc:
            return f"{grp.name} scatter-aggregate figure: {exc}"
        return None

    def _run_scatter_cells_multi_tp_job(
        self, grp: BarGroup, timepoints: List[float],
        csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        combined_rows: List[dict] = []
        combined_series: List[tuple] = []
        for tp_h in sorted(timepoints):
            col_x = self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText())
            col_y = self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText())
            old_rep_sets = self._app._rep_sets
            old_selected = self._app._selected_wells
            try:
                self._app._rep_sets = list(grp.members)
                self._app._selected_wells = set(grp.solo_wells)
                ch_x_base = self._sc_cells_x_cb.currentText().split(" ")[0]
                ch_y_base = self._sc_cells_y_cb.currentText().split(" ")[0]
                scatter_data = _collect_scatter_data(
                    self._app, col_x, col_y, tp_h,
                    well_colors=WELL_COLORS,
                    cell_area_threshold=self._app._get_cell_area_threshold(),
                    fluor_gate_x=self._app._get_fluor_gate(ch_x_base),
                    fluor_gate_y=self._app._get_fluor_gate(ch_y_base),
                )
            finally:
                self._app._rep_sets = old_rep_sets
                self._app._selected_wells = old_selected
            for label, data in scatter_data.items():
                combined_series.append((tp_h, label, data))
                for x, y, meta in zip(data["x"], data["y"], data["metadata"]):
                    well, filename, nuclear_id, _row_idx = meta
                    combined_rows.append({
                        "group": grp.name,
                        "timepoint_h": f"{tp_h:.4f}",
                        "member": label, "well": well,
                        "x": f"{x:.8g}", "y": f"{y:.8g}",
                        "filename": filename, "nucleus_id": nuclear_id,
                    })
        if not combined_rows:
            return f"{grp.name}: no scatter-cells data for selected timepoints"
        try:
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "timepoint_h", "member", "well", "x", "y", "filename", "nucleus_id"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(combined_rows)
        except OSError as exc:
            return f"{grp.name} scatter-cells CSV: {exc}"
        try:
            from matplotlib.figure import Figure as _Figure
            fig = _Figure(figsize=(8, 6), dpi=300, facecolor=PLOT_BG)
            ax = fig.add_subplot(1, 1, 1)
            for tp_h, label, data in combined_series:
                ax.scatter(data["x"], data["y"],
                           label=f"{label} @ t={tp_h:.1f}h",
                           alpha=0.55, s=24)
            ax.set_xlabel(self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText()))
            ax.set_ylabel(self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText()))
            ax.set_title(f"{grp.name} \u2014 Scatter Cells (all selected tps)")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best", fontsize=7)
            self._save_figure(fig, fig_path, fmt)
        except Exception as exc:
            return f"{grp.name} scatter-cells figure: {exc}"
        return None

    def _run_scatter_agg_multi_tp_job(
        self, grp: BarGroup, timepoints: List[float],
        csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        stat_x = self._sc_agg_x_cb.currentText()
        stat_y = self._sc_agg_y_cb.currentText()
        old_rep_sets = self._app._rep_sets
        old_selected = self._app._selected_wells
        try:
            self._app._rep_sets = list(grp.members)
            self._app._selected_wells = set(grp.solo_wells)
            scatter_data = _collect_scatter_agg_data(
                self._app, stat_x, stat_y, sorted(timepoints),
                well_colors=WELL_COLORS,
                aggregate_with_threshold=aggregate_with_threshold,
            )
        finally:
            self._app._rep_sets = old_rep_sets
            self._app._selected_wells = old_selected
        if not scatter_data:
            return f"{grp.name}: no scatter-aggregate data for selected timepoints"
        try:
            rows: List[dict] = []
            for data in scatter_data.values():
                rows.append({
                    "group": grp.name,
                    "label": data.get("label", ""),
                    "timepoint_h": f"{float(data.get('timepoint', float('nan'))):.4f}",
                    "x": f"{float(data['x'][0]):.8g}",
                    "y": f"{float(data['y'][0]):.8g}",
                    "x_err": f"{float(data['x_err'][0]):.8g}",
                    "y_err": f"{float(data['y_err'][0]):.8g}",
                })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "label", "timepoint_h", "x", "y", "x_err", "y_err"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-aggregate CSV: {exc}"
        try:
            from matplotlib.figure import Figure as _Figure
            fig = _Figure(figsize=(8, 6), dpi=300, facecolor=PLOT_BG)
            ax = fig.add_subplot(1, 1, 1)
            for data in scatter_data.values():
                ax.errorbar(
                    data["x"], data["y"],
                    xerr=data["x_err"], yerr=data["y_err"],
                    label=data.get("label", ""),
                    marker=data.get("marker", "o"),
                    linestyle="none", capsize=5, alpha=0.75,
                )
            ax.set_xlabel(stat_x)
            ax.set_ylabel(stat_y)
            ax.set_title(f"{grp.name} \u2014 Scatter Aggregate (all selected tps)")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="best", fontsize=7)
            self._save_figure(fig, fig_path, fmt)
        except Exception as exc:
            return f"{grp.name} scatter-aggregate figure: {exc}"
        return None


BatchExportDialog = BatchExportPanel
BarBatchExportDialog = BarBatchExportPanel


def _read_pipeline_info(out_dir: Path):
    """Read pipeline_info.json sidecar; returns (extractor, fluor_tokens)."""
    return _read_pipeline_info_shared(out_dir, logger=_logger, check_parent=True)
