"""Export/save service helpers extracted from runtime_app."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox


_CSV_FILTER = "CSV files (*.csv);;All files (*.*)"


def _ask_save_csv(app, title: str, default_name: str) -> str:
    initial_dir = str(app._data_dir) if app._data_dir else ""
    initial_path = str(Path(initial_dir) / default_name) if initial_dir else default_name
    out, _ = QFileDialog.getSaveFileName(app, title, initial_path, _CSV_FILTER)
    return out or ""


def _warn(app, title: str, msg: str) -> None:
    QMessageBox.warning(app, title, msg)


def _error(app, title: str, msg: str) -> None:
    QMessageBox.critical(app, title, msg)


def export_plot_data(app) -> None:
    from well_viewer import runtime_app as rt

    selected = app._selected_labels()
    if not selected:
        _warn(app, "Export", "No wells selected.")
        return
    ch = app._active_channel
    metric = app._active_metric
    threshold = app._get_thresh_frac_on(ch)
    rows_out = []
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    for label in selected:
        pts = rt.aggregate_with_threshold(
            app._get_rows(label), threshold,
            use_sem=False, val_col=app._active_val_col,
            cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates,
        )
        for t, mean, sd, frac, n_above, n_total in pts:
            rows_out.append({
                "well": label,
                "time_h": f"{t:.4f}",
                f"mean_{ch}_{metric}": f"{mean:.6f}" if not math.isnan(mean) else "",
                f"sd_{ch}_{metric}": f"{sd:.6f}",
                "n_above_threshold": n_above,
                "fraction_above": f"{frac:.6f}" if not math.isnan(frac) else "",
                "n_total": n_total,
                "threshold": f"{threshold:.4f}",
                "metric": metric,
            })
    if not rows_out:
        _warn(app, "Export", "No data to export for the current selection.")
        return
    out_path = _ask_save_csv(app, "Export plot data", f"{ch}_{metric}_plot_export.csv")
    if not out_path:
        return
    fieldnames = ["well", "time_h", f"mean_{ch}_{metric}", f"sd_{ch}_{metric}", "n_above_threshold", "fraction_above", "n_total", "threshold", "metric"]
    try:
        with open(out_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} row(s) to {Path(out_path).name}")
    except OSError as exc:
        _error(app, "Export failed", str(exc))


def export_bar_plot_data(app) -> None:
    tp_str = app._bar_tp_cb.currentText()
    if tp_str in ("—", ""):
        _warn(app, "Export", "Select a timepoint first.")
        return
    try:
        target_t = float(tp_str)
    except ValueError:
        return
    use_groups, items, band_lbl = app._collect_bar_items(target_t)
    ch = app._active_channel
    metric = app._active_metric
    threshold = app._get_thresh_frac_on(ch)
    rows_out = []
    if use_groups:
        for item in items:
            # Rep-set items are (name, gm, g_err_m, gf, g_err_f, has, color[, n_above[, n_above_spread]]).
            name, gm, g_err_m, gf, g_err_f, has, _color = item[:7]
            n_above = float(item[7]) if len(item) >= 8 else 0.0
            n_above_spread = float(item[8]) if len(item) >= 9 else 0.0
            rows_out.append({
                "name": name,
                "timepoint_h": tp_str,
                f"mean_{ch}_{metric}": f"{gm:.6f}" if has else "",
                f"err_mean_{band_lbl}_{ch}_{metric}": f"{g_err_m:.6f}" if has else "",
                "fraction_above": f"{gf:.6f}" if not math.isnan(gf) else "",
                f"err_frac_{band_lbl}": f"{g_err_f:.6f}" if not math.isnan(gf) else "",
                "n_above_threshold": f"{n_above:.6f}" if n_above_spread > 0 else f"{int(n_above)}",
                f"err_n_above_{band_lbl}": f"{n_above_spread:.6f}" if n_above_spread > 0 else "",
                "threshold": f"{threshold:.4f}",
                "metric": metric,
            })
    else:
        for item in items:
            # Per-well items are (label, mean, spread, frac, frac_spread, has[, n_above[, n_above_spread]]);
            # tolerate older 5-/6-/7-tuple shapes that predated the trailing
            # event-count fields.
            if len(item) >= 8:
                label, mean, spread, frac, frac_spread, has, n_above, n_above_spread = item[:8]
                n_above = float(n_above)
                n_above_spread = float(n_above_spread)
            elif len(item) == 7:
                label, mean, spread, frac, frac_spread, has, n_above = item[:7]
                n_above = float(n_above)
                n_above_spread = 0.0
            elif len(item) == 6:
                label, mean, spread, frac, frac_spread, has = item
                n_above = 0.0
                n_above_spread = 0.0
            else:
                label, mean, spread, frac, has = item
                frac_spread = 0.0
                n_above = 0.0
                n_above_spread = 0.0
            rows_out.append({
                "well": label,
                "timepoint_h": tp_str,
                f"mean_{ch}_{metric}": f"{mean:.6f}" if has and not math.isnan(mean) else "",
                f"err_{band_lbl}_{ch}_{metric}": f"{spread:.6f}" if has else "",
                "fraction_above": f"{frac:.6f}" if has and not math.isnan(frac) else "",
                f"err_frac_{band_lbl}": f"{frac_spread:.6f}" if has and not math.isnan(frac) else "",
                "n_above_threshold": (
                    f"{n_above:.6f}" if n_above_spread > 0
                    else f"{int(n_above)}" if has else ""
                ),
                f"err_n_above_{band_lbl}": f"{n_above_spread:.6f}" if n_above_spread > 0 else "",
                "threshold": f"{threshold:.4f}",
                "metric": metric,
            })
    if not rows_out:
        _warn(app, "Export", "No data to export.")
        return
    out_path = _ask_save_csv(app, "Export bar plot data", f"bar_t{tp_str}.csv")
    if not out_path:
        return
    try:
        with open(out_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} row(s) → {Path(out_path).name}")
    except OSError as exc:
        _error(app, "Export failed", str(exc))


def export_raw_data_csv(app) -> None:
    if not app._well_paths:
        _warn(app, "Export", "Load data before exporting raw CSV.")
        return

    rows_out = []
    fieldnames = {"well"}
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gate_threshold = app._get_fluor_gate(app._active_channel)

    for label in sorted(app._well_paths):
        for row in app._get_rows(label):
            if not app._row_is_included(row):
                continue
            try:
                area = float(row.get("area_px", float('nan')))
            except (ValueError, TypeError):
                continue

            if (area != area) or area <= cell_area_threshold:
                continue

            fluor_col = f"{app._active_channel}_mean_intensity"
            try:
                fluor = float(row.get(fluor_col, float('nan')))
            except (ValueError, TypeError):
                continue

            if (fluor != fluor) or fluor <= fluor_gate_threshold:
                continue

            out_row = {"well": label}
            out_row.update(row)
            rows_out.append(out_row)
            fieldnames.update(out_row.keys())

    if not rows_out:
        _warn(app, "Export", "No raw rows available to export.")
        return

    ordered_fields = ["well"] + [k for k in sorted(fieldnames) if k != "well"]
    out_path = _ask_save_csv(app, "Export raw data", "raw_data_export.csv")
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=ordered_fields)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} raw row(s) → {Path(out_path).name}")
    except OSError as exc:
        _error(app, "Export failed", str(exc))


def save_montage_figure(app) -> None:
    from matplotlib.figure import Figure as _Figure
    from well_viewer import runtime_app as rt

    if not app._montage_fluor_arrays:
        _warn(app, "Nothing to save", "Load a well in the Preview tab first.")
        return
    fov = app._preview_fov_cb.currentText()
    well = rt._extract_well_token(app._preview_selected_well or "") or "well"
    n = len(app._montage_fluor_arrays)
    try:
        lo = float(app._mon_lmin_edit.text())
    except ValueError:
        lo = None
    try:
        hi = float(app._mon_lmax_edit.text())
    except ValueError:
        hi = None
    ov_lmin_edit = getattr(app, "_mon_ov_lmin_edit", None)
    ov_lmax_edit = getattr(app, "_mon_ov_lmax_edit", None)
    try:
        ov_lo = float(ov_lmin_edit.text()) if ov_lmin_edit is not None else None
    except (ValueError, AttributeError):
        ov_lo = None
    try:
        ov_hi = float(ov_lmax_edit.text()) if ov_lmax_edit is not None else None
    except (ValueError, AttributeError):
        ov_hi = None
    tophat_on = getattr(app, "_mon_tophat_cb", None) is not None and app._mon_tophat_cb.isChecked()
    use_display = tophat_on and hasattr(app, "_montage_fluor_display_arrays") and len(app._montage_fluor_display_arrays) == len(app._montage_fluor_arrays)
    fluor_source = app._montage_fluor_display_arrays if use_display else app._montage_fluor_arrays
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    crop = getattr(app, "_montage_crop", None)

    def _apply_crop(a):
        """Slice ``a`` to the active montage crop, preserving channel axes."""
        if crop is None or a is None:
            return a
        a = rt._np.asarray(a)
        ih, iw = a.shape[:2]
        y0, x0, y1, x1 = crop
        y0 = max(0, min(int(y0), ih))
        y1 = max(y0, min(int(y1), ih))
        x0 = max(0, min(int(x0), iw))
        x1 = max(x0, min(int(x1), iw))
        if y1 <= y0 or x1 <= x0:
            return a
        return a[y0:y1, x0:x1]

    fig = _Figure(figsize=(max(4, n * 2.5), 5), dpi=300, facecolor=rt.PLOT_BG)
    for ci, ((tp, _), display_arr, ov_arr) in enumerate(zip(tp_list, fluor_source, app._montage_overlay_arrays)):
        ax_g = fig.add_subplot(2, n, ci + 1)
        ax_o = fig.add_subplot(2, n, n + ci + 1)
        if display_arr is not None and rt._NP_AVAILABLE:
            arr = rt._np.asarray(_apply_crop(display_arr), dtype=rt._np.float32)
            alo = lo if lo is not None else float(arr.min())
            ahi = hi if hi is not None else float(arr.max())
            if ahi <= alo:
                ahi = alo + 1.0
            ax_g.imshow(arr, cmap="gray", vmin=alo, vmax=ahi, aspect="auto")
        else:
            ax_g.text(0.5, 0.5, "unavail", ha="center", va="center", transform=ax_g.transAxes, color=rt.TXT_MUT)
        ax_g.set_title(tp, fontsize=6, color=rt.TXT_PRI)
        ax_g.axis("off")
        if ci == 0:
            ax_g.set_ylabel(app._active_channel.upper(), fontsize=7, color=rt.TXT_PRI)
        if ov_arr is not None and rt._NP_AVAILABLE:
            arr = rt._np.asarray(_apply_crop(ov_arr))
            if arr.ndim == 2:
                arr_f = arr.astype(rt._np.float32)
                lo_o = ov_lo if ov_lo is not None else float(arr_f.min())
                hi_o = ov_hi if ov_hi is not None else float(arr_f.max())
                if hi_o <= lo_o:
                    hi_o = lo_o + 1.0
                ax_o.imshow(arr_f, cmap="gray", vmin=lo_o, vmax=hi_o, aspect="auto")
            elif arr.ndim == 3:
                a = arr[:, :, :3].astype(rt._np.float32)
                lo_o = ov_lo if ov_lo is not None else float(a.min())
                hi_o = ov_hi if ov_hi is not None else float(a.max())
                if hi_o <= lo_o:
                    hi_o = lo_o + 1.0
                a = rt._np.clip((a - lo_o) / (hi_o - lo_o) * 255.0, 0, 255).astype(rt._np.uint8)
                ax_o.imshow(a, aspect="auto")
        else:
            ax_o.text(0.5, 0.5, "unavail", ha="center", va="center", transform=ax_o.transAxes, color=rt.TXT_MUT)
        ax_o.axis("off")
        if ci == 0:
            ax_o.set_ylabel("overlay", fontsize=7, color=rt.TXT_PRI)
    fig.suptitle(f"{well}  FOV: {fov}", fontsize=9, fontweight="bold", color=rt.TXT_PRI, y=1.01)
    fig.tight_layout()
    app._save_matplotlib_fig(fig, f"montage_{well}_{fov}.png")


def export_scatter_data(app) -> None:
    """Export scatter plot data to CSV."""
    from well_viewer.scatter_controller import collect_scatter_data as _scatter_collect_data

    try:
        ch_x_entry = app._scatter_ch_x_cb.currentText()
        ch_y_entry = app._scatter_ch_y_cb.currentText()
        tp_str = app._scatter_tp_cb.currentText()
        timepoint_h = float(tp_str) if tp_str else 0.0
    except (ValueError, AttributeError):
        _warn(app, "Export", "Select channels and timepoint first.")
        return

    ch_x_base = ch_x_entry.split(" ")[0]
    ch_y_base = ch_y_entry.split(" ")[0]
    col_x = app._col_for_scatter_entry(ch_x_entry)
    col_y = app._col_for_scatter_entry(ch_y_entry)

    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gate_x = app._get_fluor_gate(ch_x_base)
    fluor_gate_y = app._get_fluor_gate(ch_y_base)

    scatter_data = _scatter_collect_data(
        app, col_x, col_y, timepoint_h,
        well_colors=[],
        cell_area_threshold=cell_area_threshold,
        fluor_gate_x=fluor_gate_x,
        fluor_gate_y=fluor_gate_y,
    )

    rows_out = []
    for label, data in scatter_data.items():
        x_vals = data['x']
        y_vals = data['y']
        for x, y in zip(x_vals, y_vals):
            rows_out.append({
                "group_well": label,
                f"{col_x}": f"{x:.6f}",
                f"{col_y}": f"{y:.6f}",
                "timepoint_h": f"{timepoint_h:.4f}",
            })

    if not rows_out:
        _warn(app, "Export", "No data to export for the current selection.")
        return

    out_path = _ask_save_csv(
        app, "Export scatter plot data",
        f"scatter_{ch_x_base}_vs_{ch_y_base}_t{timepoint_h}.csv",
    )
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["group_well", f"{col_x}", f"{col_y}", "timepoint_h"])
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} datapoint(s) → {Path(out_path).name}")
    except OSError as exc:
        _error(app, "Export failed", str(exc))


def export_scatter_agg_data(app) -> None:
    """Export aggregate scatter plot data to CSV."""
    from well_viewer import runtime_app as rt
    from well_viewer.scatter_controller import collect_scatter_agg_data as _scatter_collect_agg_data

    try:
        stat_x = app._scatter_agg_stat_x_cb.currentText()
        stat_y = app._scatter_agg_stat_y_cb.currentText()

        selected_timepoints: list[float] = []
        tp_checks = getattr(app, "_scatter_agg_tp_checks", None)
        if tp_checks:
            for tp_str, widget in tp_checks.items():
                try:
                    if widget.isChecked():
                        selected_timepoints.append(float(tp_str))
                except Exception:
                    pass
            selected_timepoints.sort()

        if not selected_timepoints:
            _warn(app, "Export", "Please select at least one timepoint.")
            return

    except (ValueError, AttributeError, IndexError):
        _warn(app, "Export", "Select statistics and timepoints first.")
        return

    scatter_data = _scatter_collect_agg_data(
        app, stat_x, stat_y, selected_timepoints,
        well_colors=[],
        aggregate_with_threshold=rt.aggregate_with_threshold,
    )

    rows_out = []
    for label, data in scatter_data.items():
        x_val = data['x'][0]
        y_val = data['y'][0]
        x_err = data['x_err'][0]
        y_err = data['y_err'][0]
        tp = data['timepoint']

        rows_out.append({
            "replicate_well": label.split("_tp")[0],
            "timepoint_h": f"{tp:.4f}",
            stat_x: f"{x_val:.6f}",
            f"{stat_x}_error": f"{x_err:.6f}",
            stat_y: f"{y_val:.6f}",
            f"{stat_y}_error": f"{y_err:.6f}",
        })

    if not rows_out:
        _warn(app, "Export", "No data to export for the current selection.")
        return

    tp_range = f"t{min(selected_timepoints):.1f}-{max(selected_timepoints):.1f}"
    stat_x_safe = stat_x.replace(" ", "_").lower()
    stat_y_safe = stat_y.replace(" ", "_").lower()

    out_path = _ask_save_csv(
        app, "Export aggregate scatter plot data",
        f"scatter_agg_{stat_x_safe}_vs_{stat_y_safe}_{tp_range}.csv",
    )
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            fieldnames = ["replicate_well", "timepoint_h", stat_x, f"{stat_x}_error", stat_y, f"{stat_y}_error"]
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} datapoint(s) → {Path(out_path).name}")
    except OSError as exc:
        _error(app, "Export failed", str(exc))
