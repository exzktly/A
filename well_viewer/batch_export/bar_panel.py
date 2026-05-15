"""Bar-mode batch export panel."""

from __future__ import annotations

import copy
import csv
import json
import math
import re
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
        self._build_output_header_and_io(layout)
        self._build_channel_row(layout, attr="_bar_channel_cb")

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        self._build_timepoints_section(layout)

        self._app._update_bar_tp_menu()
        tp_vals = [self._app._bar_tp_cb.itemText(i)
                   for i in range(self._app._bar_tp_cb.count())]
        for tp in tp_vals:
            if tp and tp != "\u2014":
                self._tp_lb.addItem(QListWidgetItem(tp))
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

        self._build_run_row(layout)

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

        _ch_selected = self._selected_export_channel() or self._app._active_channel
        threshold = self._app._get_thresh_frac_on(_ch_selected)
        use_sem = self._app._use_sem
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
                from well_viewer.export_service import (
                    _well_labels_map, aggpoint_at, aggpoint_bar_fields,
                    bar_metric_fieldnames, bar_metric_row,
                    well_name_for, well_names_joined,
                )
                _val_col = self._app._active_val_col
                _ch = _ch_selected
                _metric = self._app._active_metric
                _well_labels = _well_labels_map(self._app)
                _cell_area_threshold = self._app._get_cell_area_threshold()
                _fluor_gates = self._app._get_all_fluor_gates()
                _per_fov_spread = self._app._use_fov_spread_active()
                rows_csv: List[dict] = []
                for rset in grp.members:
                    valid = [w for w in rset.wells if w in self._app._well_paths]
                    if not valid:
                        continue
                    pts = self._app._aggregate_group(
                        valid, threshold=threshold, use_sem=use_sem,
                        val_col=_val_col,
                        cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                        per_fov_spread=_per_fov_spread,
                    )
                    pt = aggpoint_at(pts, target_t)
                    if pt is None:
                        continue
                    fields = aggpoint_bar_fields(pt, use_fov_spread=_per_fov_spread)
                    wells_str = ";".join(valid)
                    row = {
                        "group": grp.name,
                        "member": rset.name,
                        "member_type": "replicate_set",
                        "wells": wells_str,
                        "well_names": well_names_joined(wells_str, _well_labels),
                        "n_wells": len(valid),
                    }
                    row.update(bar_metric_row(
                        ch=_ch, metric=_metric, tp_str=tp_str,
                        threshold=threshold, band_lbl=band_lbl, **fields,
                    ))
                    rows_csv.append(row)
                for w in grp.solo_wells:
                    if w not in self._app._well_paths:
                        continue
                    pts = self._app._aggregate_well(
                        w, threshold=threshold, use_sem=use_sem,
                        val_col=_val_col,
                        cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                        per_fov_spread=_per_fov_spread,
                    )
                    pt = aggpoint_at(pts, target_t)
                    if pt is None:
                        continue
                    fields = aggpoint_bar_fields(pt, use_fov_spread=_per_fov_spread)
                    row = {
                        "group": grp.name,
                        "member": w,
                        "member_type": "solo_well",
                        "wells": w,
                        "well_names": well_name_for(w, _well_labels),
                        "n_wells": 1,
                    }
                    row.update(bar_metric_row(
                        ch=_ch, metric=_metric, tp_str=tp_str,
                        threshold=threshold, band_lbl=band_lbl, **fields,
                    ))
                    rows_csv.append(row)
                if rows_csv:
                    fnames = (
                        ["group", "member", "member_type",
                         "wells", "well_names", "n_wells"]
                        + bar_metric_fieldnames(_ch, _metric, band_lbl)
                    )
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

        fig = _Figure(figsize=(8, 10), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(3, 1, 1)
        ax_frac = fig.add_subplot(3, 1, 2)
        ax_n = fig.add_subplot(3, 1, 3)
        fig.subplots_adjust(hspace=0.55, top=0.94, bottom=0.10,
                            left=0.13, right=0.97)
        fig.suptitle(f"{grp.name}  \u2014  t = {tp_str} h",
                     fontsize=10, fontweight="bold", color=get_color("PLOT_TXT"), y=0.97)
        _ch = (self._selected_export_channel() or self._app._active_channel).upper()
        apply_ax_style(ax_mean,
                       f"Mean {_ch} (above threshold) \u00b1 {band_lbl}",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac, "Fraction of Cells Above Threshold", "Fraction")
        if self._app._use_fov_spread_active():
            apply_ax_style(ax_n, f"Mean events above threshold per FOV ± {band_lbl}", "N(above)/FOV")
        else:
            apply_ax_style(ax_n, "Events above threshold (N)", "N(above)")
        ax_frac.set_ylim(-0.05, 1.05)

        members: List[tuple] = []
        for rset in grp.members:
            valid = [w for w in rset.wells if w in self._app._well_paths]
            if not valid:
                continue
            members.append((self._app._replicate_display_label(rset), valid))
        for w in grp.solo_wells:
            if w not in self._app._well_paths:
                continue
            members.append((w, [w]))

        if not members:
            return fig

        _cell_area_threshold = self._app._get_cell_area_threshold()
        _fluor_gates = self._app._get_all_fluor_gates()
        draw_items: List[tuple] = []
        xlabels: List[str] = []
        for i, (name, wells) in enumerate(members):
            color = WELL_COLORS[i % len(WELL_COLORS)]
            pts = self._app._aggregate_group(
                wells, threshold=threshold, use_sem=use_sem,
                val_col=self._app._active_val_col,
                cell_area_threshold=_cell_area_threshold,
                fluor_gates=_fluor_gates,
                per_fov_spread=self._app._use_fov_spread_active(),
            )
            matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
            xlabels.append(name)
            if matched:
                pt = matched[0]
                _t, m, s, f = pt[0], pt[1], pt[2], pt[3]
                # AggPoint shape is (t, mean, spread, frac, n_above, n_total,
                # frac_spread, n_above_per_fov_mean, n_above_per_fov_spread).
                # The events panel mirrors the on-screen bar plot: total
                # n_above by default, mean ± SD/SEM per FOV when batch export
                # is run with the Aggregate-FOVs toggle on.
                n_above_total = int(pt[4]) if len(pt) >= 5 else 0
                frac_spread = float(pt[6]) if len(pt) >= 7 else 0.0
                n_above_pf_mean = float(pt[7]) if len(pt) >= 8 else 0.0
                n_above_pf_spread = float(pt[8]) if len(pt) >= 9 else 0.0
                if self._app._use_fov_spread_active():
                    n_above = n_above_pf_mean
                    n_above_spread = n_above_pf_spread
                else:
                    n_above = float(n_above_total)
                    n_above_spread = 0.0
                has_data = not math.isnan(m)
                draw_items.append((name, name, m, s, f, frac_spread, has_data, color, n_above, n_above_spread))
            else:
                draw_items.append((name, name, float("nan"), 0.0, float("nan"), 0.0, False, color, 0.0, 0.0))

        _bar_render_items(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            ax_n=ax_n,
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

