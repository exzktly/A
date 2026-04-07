"""Export/save service helpers extracted from runtime_app."""

from __future__ import annotations

from pathlib import Path


def export_plot_data(app) -> None:
    from well_viewer import runtime_app as rt

    selected = app._selected_labels()
    if not selected:
        rt.messagebox.showwarning("Export", "No wells selected.")
        return
    ch = app._active_channel
    metric = app._active_metric  # "mean_intensity" or "smfish_count"
    threshold = app._get_thresh_frac_on(ch)
    rows_out = []
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    for label in selected:
        pts = rt.aggregate_with_threshold(app._get_rows(label), threshold, use_sem=False, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates)
        for t, mean, sd, frac, n_above, n_total in pts:
            rows_out.append(
                {
                    "well": label,
                    "time_h": f"{t:.4f}",
                    f"mean_{ch}_{metric}": f"{mean:.6f}" if not rt.math.isnan(mean) else "",
                    f"sd_{ch}_{metric}": f"{sd:.6f}",
                    "n_above_threshold": n_above,
                    "fraction_above": f"{frac:.6f}" if not rt.math.isnan(frac) else "",
                    "n_total": n_total,
                    "threshold": f"{threshold:.4f}",
                    "metric": metric,
                }
            )
    if not rows_out:
        rt.messagebox.showwarning("Export", "No data to export for the current selection.")
        return
    out_path = rt.filedialog.asksaveasfilename(
        title="Export plot data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=f"{ch}_{metric}_plot_export.csv",
    )
    if not out_path:
        return
    fieldnames = ["well", "time_h", f"mean_{ch}_{metric}", f"sd_{ch}_{metric}", "n_above_threshold", "fraction_above", "n_total", "threshold", "metric"]
    try:
        with open(out_path, "w", newline="") as fh:
            writer = rt.csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} row(s) to {Path(out_path).name}")
    except OSError as exc:
        rt.messagebox.showerror("Export failed", str(exc))


def export_bar_plot_data(app) -> None:
    from well_viewer import runtime_app as rt

    tp_str = app._bar_tp_var.get()
    if tp_str in ("—", ""):
        rt.messagebox.showwarning("Export", "Select a timepoint first.", parent=app)
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
        for name, gm, g_err_m, gf, g_err_f, has, _ in items:
            rows_out.append(
                {
                    "name": name,
                    "timepoint_h": tp_str,
                    f"mean_{ch}_{metric}": f"{gm:.6f}" if has else "",
                    f"err_mean_{band_lbl}_{ch}_{metric}": f"{g_err_m:.6f}" if has else "",
                    "fraction_above": f"{gf:.6f}" if not rt.math.isnan(gf) else "",
                    f"err_frac_{band_lbl}": f"{g_err_f:.6f}" if not rt.math.isnan(gf) else "",
                    "threshold": f"{threshold:.4f}",
                    "metric": metric,
                }
            )
    else:
        for label, mean, spread, frac, has in items:
            rows_out.append(
                {
                    "well": rt._extract_well_token(label) or label,
                    "timepoint_h": tp_str,
                    f"mean_{ch}_{metric}": f"{mean:.6f}" if has and not rt.math.isnan(mean) else "",
                    f"err_{band_lbl}_{ch}_{metric}": f"{spread:.6f}" if has else "",
                    "fraction_above": f"{frac:.6f}" if has and not rt.math.isnan(frac) else "",
                    "threshold": f"{threshold:.4f}",
                    "metric": metric,
                }
            )
    if not rows_out:
        rt.messagebox.showwarning("Export", "No data to export.", parent=app)
        return
    out_path = rt.filedialog.asksaveasfilename(
        parent=app,
        title="Export bar plot data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=f"bar_t{tp_str}.csv",
        initialdir=str(app._data_dir) if app._data_dir else None,
    )
    if not out_path:
        return
    try:
        with open(out_path, "w", newline="") as fh:
            writer = rt.csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} row(s) → {Path(out_path).name}")
    except OSError as exc:
        rt.messagebox.showerror("Export failed", str(exc), parent=app)


def export_raw_data_csv(app) -> None:
    from well_viewer import runtime_app as rt

    if not app._well_paths:
        rt.messagebox.showwarning("Export", "Load data before exporting raw CSV.", parent=app)
        return

    rows_out = []
    fieldnames = {"well"}
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gate_threshold = app._get_fluor_gate(app._active_channel)

    for label in sorted(app._well_paths):
        for row in app._get_rows(label):
            # Apply cell gating thresholds
            try:
                area = float(row.get("area_px", float('nan')))
            except (ValueError, TypeError):
                continue

            if (area != area) or area <= cell_area_threshold:  # Skip NaN or below threshold
                continue

            # Check fluorescence gate threshold
            fluor_col = f"{app._active_channel}_mean_intensity"
            try:
                fluor = float(row.get(fluor_col, float('nan')))
            except (ValueError, TypeError):
                continue

            if (fluor != fluor) or fluor <= fluor_gate_threshold:  # Skip NaN or below threshold
                continue

            out_row = {"well": label}
            out_row.update(row)
            rows_out.append(out_row)
            fieldnames.update(out_row.keys())

    if not rows_out:
        rt.messagebox.showwarning("Export", "No raw rows available to export.", parent=app)
        return

    ordered_fields = ["well"] + [k for k in sorted(fieldnames) if k != "well"]
    out_path = rt.filedialog.asksaveasfilename(
        parent=app,
        title="Export raw data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile="raw_data_export.csv",
        initialdir=str(app._data_dir) if app._data_dir else None,
    )
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            writer = rt.csv.DictWriter(fh, fieldnames=ordered_fields)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} raw row(s) → {Path(out_path).name}")
    except OSError as exc:
        rt.messagebox.showerror("Export failed", str(exc), parent=app)


def save_montage_figure(app) -> None:
    from matplotlib.figure import Figure as _Figure
    from well_viewer import runtime_app as rt

    if not app._montage_fluor_arrays:
        rt.messagebox.showwarning("Nothing to save", "Load a well in the Preview tab first.", parent=app)
        return
    fov = app._preview_fov_var.get()
    well = rt._extract_well_token(app._preview_selected_well or "") or "well"
    n = len(app._montage_fluor_arrays)
    try:
        lo = float(app._mon_lmin_var.get())
    except ValueError:
        lo = None
    try:
        hi = float(app._mon_lmax_var.get())
    except ValueError:
        hi = None
    use_display = getattr(app, "_mon_tophat_var", None) is not None and app._mon_tophat_var.get() and hasattr(app, "_montage_fluor_display_arrays") and len(app._montage_fluor_display_arrays) == len(app._montage_fluor_arrays)
    fluor_source = app._montage_fluor_display_arrays if use_display else app._montage_fluor_arrays
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    fig = _Figure(figsize=(max(4, n * 2.5), 5), dpi=300, facecolor=rt.PLOT_BG)
    for ci, ((tp, _), display_arr, ov_arr) in enumerate(zip(tp_list, fluor_source, app._montage_overlay_arrays)):
        ax_g = fig.add_subplot(2, n, ci + 1)
        ax_o = fig.add_subplot(2, n, n + ci + 1)
        if display_arr is not None and rt._NP_AVAILABLE:
            arr = rt._np.asarray(display_arr, dtype=rt._np.float32)
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
            arr = rt._np.asarray(ov_arr)
            if arr.ndim == 2:
                lo_o, hi_o = float(arr.min()), float(arr.max())
                if hi_o <= lo_o:
                    hi_o = lo_o + 1.0
                ax_o.imshow(arr, cmap="gray", vmin=lo_o, vmax=hi_o, aspect="auto")
            elif arr.ndim == 3:
                a = arr[:, :, :3]
                if a.dtype != rt._np.uint8:
                    rng = max(a.max() - a.min(), 1)
                    a = ((a.astype(rt._np.float32) - a.min()) / rng * 255).astype(rt._np.uint8)
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
    from well_viewer import runtime_app as rt
    from well_viewer.scatter_controller import collect_scatter_data as _scatter_collect_data

    try:
        ch_x_entry = app._scatter_ch_x_var.get()
        ch_y_entry = app._scatter_ch_y_var.get()
        tp_str = app._scatter_tp_var.get()
        timepoint_h = float(tp_str) if tp_str else 0.0
    except (ValueError, AttributeError):
        rt.messagebox.showwarning("Export", "Select channels and timepoint first.", parent=app)
        return

    # Extract base channel names for gate lookups
    ch_x_base = ch_x_entry.split(" ")[0]
    ch_y_base = ch_y_entry.split(" ")[0]
    # Resolve to actual column names
    col_x = app._col_for_scatter_entry(ch_x_entry)
    col_y = app._col_for_scatter_entry(ch_y_entry)

    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gate_x = app._get_fluor_gate(ch_x_base)
    fluor_gate_y = app._get_fluor_gate(ch_y_base)

    scatter_data = _scatter_collect_data(
        app,
        col_x,
        col_y,
        timepoint_h,
        well_colors=[],  # Not needed for export
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
        rt.messagebox.showwarning("Export", "No data to export for the current selection.", parent=app)
        return

    out_path = rt.filedialog.asksaveasfilename(
        parent=app,
        title="Export scatter plot data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=f"scatter_{ch_x}_vs_{ch_y}_t{timepoint_h}.csv",
        initialdir=str(app._data_dir) if app._data_dir else None,
    )
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            writer = rt.csv.DictWriter(fh, fieldnames=["group_well", f"{col_x}", f"{col_y}", "timepoint_h"])
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} datapoint(s) → {Path(out_path).name}")
    except OSError as exc:
        rt.messagebox.showerror("Export failed", str(exc), parent=app)


def export_scatter_agg_data(app) -> None:
    """Export aggregate scatter plot data to CSV."""
    from well_viewer import runtime_app as rt
    from well_viewer.scatter_controller import get_all_timepoints as _scatter_get_timepoints
    from well_viewer.scatter_controller import collect_scatter_agg_data as _scatter_collect_agg_data

    try:
        stat_x = app._scatter_agg_stat_x_var.get()
        stat_y = app._scatter_agg_stat_y_var.get()

        # Get selected timepoints from BooleanVar selections
        selected_timepoints = []
        if hasattr(app, "_scatter_agg_tp_selections") and app._scatter_agg_tp_selections:
            selected_timepoints = [float(tp_str) for tp_str, var in app._scatter_agg_tp_selections.items() if var.get()]
            selected_timepoints.sort()

        if not selected_timepoints:
            rt.messagebox.showwarning("Export", "Please select at least one timepoint.", parent=app)
            return

    except (ValueError, AttributeError, IndexError):
        rt.messagebox.showwarning("Export", "Select statistics and timepoints first.", parent=app)
        return

    scatter_data = _scatter_collect_agg_data(
        app,
        stat_x,
        stat_y,
        selected_timepoints,
        well_colors=[],  # Not needed for export
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
            "replicate_well": label.split("_tp")[0],  # Remove timepoint suffix
            "timepoint_h": f"{tp:.4f}",
            stat_x: f"{x_val:.6f}",
            f"{stat_x}_error": f"{x_err:.6f}",
            stat_y: f"{y_val:.6f}",
            f"{stat_y}_error": f"{y_err:.6f}",
        })

    if not rows_out:
        rt.messagebox.showwarning("Export", "No data to export for the current selection.", parent=app)
        return

    # Create timepoint range string for filename
    tp_range = f"t{min(selected_timepoints):.1f}-{max(selected_timepoints):.1f}"
    stat_x_safe = stat_x.replace(" ", "_").lower()
    stat_y_safe = stat_y.replace(" ", "_").lower()

    out_path = rt.filedialog.asksaveasfilename(
        parent=app,
        title="Export aggregate scatter plot data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=f"scatter_agg_{stat_x_safe}_vs_{stat_y_safe}_{tp_range}.csv",
        initialdir=str(app._data_dir) if app._data_dir else None,
    )
    if not out_path:
        return

    try:
        with open(out_path, "w", newline="") as fh:
            fieldnames = ["replicate_well", "timepoint_h", stat_x, f"{stat_x}_error", stat_y, f"{stat_y}_error"]
            writer = rt.csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_out)
        app._set_status(f"Exported {len(rows_out)} datapoint(s) → {Path(out_path).name}")
    except OSError as exc:
        rt.messagebox.showerror("Export failed", str(exc), parent=app)
