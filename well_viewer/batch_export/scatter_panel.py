"""Scatter-mode (cells/aggregate) batch export panel."""

from __future__ import annotations

import copy
import csv
import json
import math
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, List, Optional

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

from well_viewer.batch_export._common import (
    PLOT_BG,
    PLOT_SPN,
    WARN,
    get_color,
    BarGroup,
    _bar_render_items,
    _extract_well_token,
    _PLATE_COLS,
    _PLATE_ROWS,
    WELL_COLORS,
    apply_ax_style,
    ask_name_dialog,
    btn_card,
    btn_danger,
    btn_primary,
    btn_secondary,
    _clear_layout_helper,
    _groups_with_loaded_wells,
    _logger,
    _CLR_DANGER,
    _CLR_SUCCESS_DARK,
    _CLR_PLACEHOLDER,
    _CLR_DISABLED_WELL,
    _CLR_ERR_BAR,
    _CLR_WHITE,
)
from well_viewer.batch_export.base_panel import BatchExportPanel
from well_viewer.batch_export.well_grid_button import _WellGridButton


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
        title = ("OUTPUT SETTINGS \u2014 SCATTER CELLS"
                 if self._scatter_mode == "cells"
                 else "OUTPUT SETTINGS \u2014 SCATTER AGGREGATE")
        self._build_output_header_and_io(layout, title=title)

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

        self._build_timepoints_section(layout)
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

        self._build_run_row(layout, button_text="\u25b6  Run Scatter Batch Export")

    def _init_timepoint_dropdown(self) -> None:
        timepoints = sorted(set(getattr(self._app, "_all_timepoints_cache", []) or []))
        if not timepoints:
            import pandas as _pd
            tps: set = set()
            for lbl in self._app._well_paths:
                df = self._app._get_rows(lbl)
                if df is None or "timepoint_hours" not in df.columns:
                    continue
                tp = _pd.to_numeric(df["timepoint_hours"], errors="coerce").dropna().unique()
                tps.update(float(t) for t in tp)
            timepoints = sorted(tps)
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

    @contextmanager
    def _app_group_scope(self, grp: "BarGroup"):
        """Temporarily make the app's selection state describe just *grp*: one
        selection per replicate-set member, plus the group's solo wells as the
        per-well selection. The scatter_controller collectors read
        ``app._rep_sets_active()`` / ``app._selected_wells`` (both derived from
        ``app._selections``), so we swap ``_selections`` for the duration."""
        from well_viewer.selections_model import make_selection
        app = self._app
        saved = (app._selections, app._current_selection_id, app._selected_wells)
        try:
            used_names: set = set()
            used_ids: set = set()
            app._selections = [
                make_selection(name=m.name, wells=list(m.wells), source="rep_set",
                               used_names=used_names, used_ids=used_ids,
                               fallback_color_idx=i)
                for i, m in enumerate(grp.members)
            ]
            app._current_selection_id = None
            app._selected_wells = set(grp.solo_wells)
            yield
        finally:
            (app._selections, app._current_selection_id, app._selected_wells) = saved

    def _run_scatter_cells_job(
        self, grp: BarGroup, tp_h: float, csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        from well_viewer.scatter_controller import collect_scatter_data as _collect_scatter_data
        col_x = self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText())
        col_y = self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText())
        with self._app_group_scope(grp):
            ch_x_base = self._sc_cells_x_cb.currentText().split(" ")[0]
            ch_y_base = self._sc_cells_y_cb.currentText().split(" ")[0]
            scatter_data = _collect_scatter_data(
                self._app, col_x, col_y, tp_h,
                well_colors=WELL_COLORS,
                cell_area_threshold=self._app._get_cell_area_threshold(),
                fluor_gate_x=self._app._get_fluor_gate(ch_x_base),
                fluor_gate_y=self._app._get_fluor_gate(ch_y_base),
            )
        if not scatter_data:
            return f"{grp.name}: no scatter-cells data at t={tp_h:.1f}h"
        try:
            from well_viewer.export_service import _well_labels_map, well_name_for
            _well_labels = _well_labels_map(self._app)
            rows: List[dict] = []
            for label, data in scatter_data.items():
                for x, y, meta in zip(data["x"], data["y"], data["metadata"]):
                    well, filename, nuclear_id, _row_idx = meta
                    rows.append({
                        "group": grp.name, "member": label,
                        "well": well,
                        "well_name": well_name_for(well, _well_labels),
                        "timepoint_h": f"{tp_h:.4f}",
                        "x": f"{x:.8g}", "y": f"{y:.8g}",
                        "filename": filename, "nucleus_id": nuclear_id,
                    })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "member", "well", "well_name", "timepoint_h", "x", "y", "filename", "nucleus_id"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-cells CSV: {exc}"
        try:
            def _draw(ax):
                for label, data in scatter_data.items():
                    ax.scatter(data["x"], data["y"], label=label, color=data["color"],
                               alpha=0.6, s=26, edgecolors="none")
            self._export_scatter_figure(
                _draw,
                xlabel=col_x, ylabel=col_y,
                title=f"{grp.name} \u2014 Scatter Cells (t={tp_h:.1f}h)",
                fig_path=fig_path, fmt=fmt,
            )
        except Exception as exc:
            return f"{grp.name} scatter-cells figure: {exc}"
        return None

    def _run_scatter_agg_job(
        self, grp: BarGroup, tp_h: float, csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        from well_viewer.scatter_controller import collect_scatter_agg_data as _collect_scatter_agg_data
        stat_x = self._sc_agg_x_cb.currentText()
        stat_y = self._sc_agg_y_cb.currentText()
        with self._app_group_scope(grp):
            scatter_data = _collect_scatter_agg_data(
                self._app, stat_x, stat_y, [tp_h],
                well_colors=WELL_COLORS,
            )
        if not scatter_data:
            return f"{grp.name}: no scatter-aggregate data at t={tp_h:.1f}h"
        try:
            from well_viewer.export_service import (
                _well_labels_map, _well_paths_keys, well_name_for,
            )
            _well_labels = _well_labels_map(self._app)
            _well_paths = _well_paths_keys(self._app)
            rows: List[dict] = []
            for data in scatter_data.values():
                lbl = data.get("label", "")
                rows.append({
                    "group": grp.name,
                    "label": lbl,
                    "well_name": well_name_for(
                        str(lbl).split("_tp")[0], _well_labels,
                        well_paths=_well_paths, strict=True,
                    ),
                    "timepoint_h": f"{float(data.get('timepoint', tp_h)):.4f}",
                    "x": f"{float(data['x'][0]):.8g}",
                    "y": f"{float(data['y'][0]):.8g}",
                    "x_err": f"{float(data['x_err'][0]):.8g}",
                    "y_err": f"{float(data['y_err'][0]):.8g}",
                })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "label", "well_name", "timepoint_h", "x", "y", "x_err", "y_err"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-aggregate CSV: {exc}"
        try:
            def _draw(ax):
                for data in scatter_data.values():
                    ax.errorbar(
                        data["x"], data["y"],
                        xerr=data["x_err"], yerr=data["y_err"],
                        label=data.get("label", ""),
                        color=data["color"], marker=data.get("marker", "o"),
                        linestyle="none", capsize=5, alpha=0.75,
                    )
            self._export_scatter_figure(
                _draw,
                xlabel=stat_x, ylabel=stat_y,
                title=f"{grp.name} \u2014 Scatter Aggregate (t={tp_h:.1f}h)",
                fig_path=fig_path, fmt=fmt,
            )
        except Exception as exc:
            return f"{grp.name} scatter-aggregate figure: {exc}"
        return None

    def _run_scatter_cells_multi_tp_job(
        self, grp: BarGroup, timepoints: List[float],
        csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        from well_viewer.scatter_controller import collect_scatter_data as _collect_scatter_data
        combined_rows: List[dict] = []
        combined_series: List[tuple] = []
        for tp_h in sorted(timepoints):
            col_x = self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText())
            col_y = self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText())
            with self._app_group_scope(grp):
                ch_x_base = self._sc_cells_x_cb.currentText().split(" ")[0]
                ch_y_base = self._sc_cells_y_cb.currentText().split(" ")[0]
                scatter_data = _collect_scatter_data(
                    self._app, col_x, col_y, tp_h,
                    well_colors=WELL_COLORS,
                    cell_area_threshold=self._app._get_cell_area_threshold(),
                    fluor_gate_x=self._app._get_fluor_gate(ch_x_base),
                    fluor_gate_y=self._app._get_fluor_gate(ch_y_base),
                )
            from well_viewer.export_service import _well_labels_map, well_name_for
            _well_labels = _well_labels_map(self._app)
            for label, data in scatter_data.items():
                combined_series.append((tp_h, label, data))
                for x, y, meta in zip(data["x"], data["y"], data["metadata"]):
                    well, filename, nuclear_id, _row_idx = meta
                    combined_rows.append({
                        "group": grp.name,
                        "timepoint_h": f"{tp_h:.4f}",
                        "member": label,
                        "well": well,
                        "well_name": well_name_for(well, _well_labels),
                        "x": f"{x:.8g}", "y": f"{y:.8g}",
                        "filename": filename, "nucleus_id": nuclear_id,
                    })
        if not combined_rows:
            return f"{grp.name}: no scatter-cells data for selected timepoints"
        try:
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "timepoint_h", "member", "well", "well_name", "x", "y", "filename", "nucleus_id"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(combined_rows)
        except OSError as exc:
            return f"{grp.name} scatter-cells CSV: {exc}"
        try:
            def _draw(ax):
                for tp_h, label, data in combined_series:
                    ax.scatter(data["x"], data["y"],
                               label=f"{label} @ t={tp_h:.1f}h",
                               alpha=0.55, s=24)
            self._export_scatter_figure(
                _draw,
                xlabel=self._app._col_for_scatter_entry(self._sc_cells_x_cb.currentText()),
                ylabel=self._app._col_for_scatter_entry(self._sc_cells_y_cb.currentText()),
                title=f"{grp.name} \u2014 Scatter Cells (all selected tps)",
                fig_path=fig_path, fmt=fmt, legend_fontsize=7,
            )
        except Exception as exc:
            return f"{grp.name} scatter-cells figure: {exc}"
        return None

    def _run_scatter_agg_multi_tp_job(
        self, grp: BarGroup, timepoints: List[float],
        csv_path: Path, fig_path: Path, fmt: str,
    ) -> Optional[str]:
        from well_viewer.scatter_controller import collect_scatter_agg_data as _collect_scatter_agg_data
        stat_x = self._sc_agg_x_cb.currentText()
        stat_y = self._sc_agg_y_cb.currentText()
        with self._app_group_scope(grp):
            scatter_data = _collect_scatter_agg_data(
                self._app, stat_x, stat_y, sorted(timepoints),
                well_colors=WELL_COLORS,
            )
        if not scatter_data:
            return f"{grp.name}: no scatter-aggregate data for selected timepoints"
        try:
            from well_viewer.export_service import (
                _well_labels_map, _well_paths_keys, well_name_for,
            )
            _well_labels = _well_labels_map(self._app)
            _well_paths = _well_paths_keys(self._app)
            rows: List[dict] = []
            for data in scatter_data.values():
                lbl = data.get("label", "")
                rows.append({
                    "group": grp.name,
                    "label": lbl,
                    "well_name": well_name_for(
                        str(lbl).split("_tp")[0], _well_labels,
                        well_paths=_well_paths, strict=True,
                    ),
                    "timepoint_h": f"{float(data.get('timepoint', float('nan'))):.4f}",
                    "x": f"{float(data['x'][0]):.8g}",
                    "y": f"{float(data['y'][0]):.8g}",
                    "x_err": f"{float(data['x_err'][0]):.8g}",
                    "y_err": f"{float(data['y_err'][0]):.8g}",
                })
            with open(csv_path, "w", newline="") as fh:
                fieldnames = ["group", "label", "well_name", "timepoint_h", "x", "y", "x_err", "y_err"]
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            return f"{grp.name} scatter-aggregate CSV: {exc}"
        try:
            def _draw(ax):
                for data in scatter_data.values():
                    ax.errorbar(
                        data["x"], data["y"],
                        xerr=data["x_err"], yerr=data["y_err"],
                        label=data.get("label", ""),
                        marker=data.get("marker", "o"),
                        linestyle="none", capsize=5, alpha=0.75,
                    )
            self._export_scatter_figure(
                _draw,
                xlabel=stat_x, ylabel=stat_y,
                title=f"{grp.name} \u2014 Scatter Aggregate (all selected tps)",
                fig_path=fig_path, fmt=fmt, legend_fontsize=7,
            )
        except Exception as exc:
            return f"{grp.name} scatter-aggregate figure: {exc}"
        return None

