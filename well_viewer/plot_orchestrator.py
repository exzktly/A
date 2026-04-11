"""Plot/export orchestration helpers for WellViewerApp."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

from well_viewer.figure_export_editor import launch_export_editor


def redraw(
    app,
    *,
    lineplot_redraw,
    apply_ax_style,
    aggregate_with_threshold,
    all_fluor_values,
    all_fluor_values_filtered,
    plot_bg,
    plot_spn,
    txt_pri,
    txt_mut,
    warn,
    well_colors,
) -> None:
    # Determine metric label for axis titles
    metric_label = "smFISH Count" if app._active_metric == "smfish_count" else "Intensity"

    lineplot_redraw(
        app,
        apply_ax_style=apply_ax_style,
        aggregate_with_threshold=aggregate_with_threshold,
        all_fluor_values=all_fluor_values,
        all_fluor_values_filtered=all_fluor_values_filtered,
        plot_bg=plot_bg,
        plot_spn=plot_spn,
        txt_pri=txt_pri,
        txt_mut=txt_mut,
        warn=warn,
        well_colors=well_colors,
        metric_label=metric_label,
    )

    if hasattr(app, "_notebook"):
        tab = app._notebook.tab(app._notebook.select(), "text")
        if tab == "Movie Montage" and app._preview_selected_well:
            app._update_preview(app._preview_selected_well)

def save_matplotlib_fig(app, fig, default_name: str, *, plot_bg: str) -> None:
    import matplotlib as _mpl

    out = filedialog.asksaveasfilename(
        parent=app,
        title="Save figure",
        defaultextension=".png",
        filetypes=app._FIG_FILETYPES,
        initialfile=default_name,
        initialdir=str(app._data_dir) if app._data_dir else None,
    )
    if not out:
        return

    fmt = Path(out).suffix.lstrip(".").lower() or "png"
    orig_svg = _mpl.rcParams.get("svg.fonttype", "path")
    orig_ps = _mpl.rcParams.get("ps.fonttype", 3)
    try:
        if fmt == "svg":
            _mpl.rcParams["svg.fonttype"] = "none"
        elif fmt == "eps":
            _mpl.rcParams["ps.fonttype"] = 42
        kw: dict = dict(bbox_inches="tight", facecolor=plot_bg, format=fmt)
        if fmt == "png":
            kw["dpi"] = 300
        fig.savefig(out, **kw)
        app._set_status(f"Figure saved → {Path(out).name}")
    except Exception as exc:
        messagebox.showerror("Save failed", str(exc), parent=app)
    finally:
        _mpl.rcParams["svg.fonttype"] = orig_svg
        _mpl.rcParams["ps.fonttype"] = orig_ps


def _launch_editor_or_save(app, fig, default_name: str, *, plot_bg: str, canvas=None) -> None:
    session = launch_export_editor(app, fig, default_name, plot_bg=plot_bg, canvas=canvas)
    if session is not None:
        app._set_status("Export editor opened.")
        return
    save_matplotlib_fig(app, fig, default_name, plot_bg=plot_bg)


def save_line_figure(app, *, plot_bg: str) -> None:
    _launch_editor_or_save(app, app._line_fig, "line_graphs.png", plot_bg=plot_bg, canvas=getattr(app, "_line_canvas", None))


def save_bar_figure(app, *, plot_bg: str) -> None:
    tp = app._bar_tp_var.get().replace(".", "_")
    _launch_editor_or_save(app, app._bar_fig, f"bar_t{tp}.png", plot_bg=plot_bg, canvas=getattr(app, "_bar_canvas", None))


def save_scatter_figure(app, *, plot_bg: str) -> None:
    ch_x = app._scatter_ch_x_var.get()
    ch_y = app._scatter_ch_y_var.get()
    tp = app._scatter_tp_var.get().replace(".", "_")
    _launch_editor_or_save(
        app,
        app._scatter_fig,
        f"scatter_{ch_x}_vs_{ch_y}_t{tp}.png",
        plot_bg=plot_bg,
        canvas=getattr(app, "_scatter_canvas", None),
    )


def save_scatter_agg_figure(app, *, plot_bg: str) -> None:
    stat_x = app._scatter_agg_stat_x_var.get()
    stat_y = app._scatter_agg_stat_y_var.get()

    # Get selected timepoints from BooleanVar selections
    selected_timepoints = []
    if hasattr(app, "_scatter_agg_tp_selections") and app._scatter_agg_tp_selections:
        selected_timepoints = [float(tp_str) for tp_str, var in app._scatter_agg_tp_selections.items() if var.get()]
        selected_timepoints.sort()

    if selected_timepoints:
        tp_range = f"t{min(selected_timepoints):.1f}-{max(selected_timepoints):.1f}".replace(".", "_")
    else:
        tp_range = "no_tp"

    stat_x_safe = stat_x.replace(" ", "_").lower()
    stat_y_safe = stat_y.replace(" ", "_").lower()

    _launch_editor_or_save(
        app,
        app._scatter_agg_fig,
        f"scatter_agg_{stat_x_safe}_vs_{stat_y_safe}_{tp_range}.png",
        plot_bg=plot_bg,
        canvas=getattr(app, "_scatter_agg_canvas", None),
    )
