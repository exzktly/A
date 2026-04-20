"""Plot/export orchestration helpers for WellViewerApp."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from well_viewer.figure_export_editor import launch_export_editor
from well_viewer.qt_compat import combo_text, is_checked


def _qt_file_filter_from_filetypes(filetypes) -> str:
    """Convert list-of-(label, pattern) tuples to a Qt file dialog filter string."""
    parts: list[str] = []
    for label, pattern in filetypes:
        if isinstance(pattern, (list, tuple)):
            pat = " ".join(pattern)
        else:
            pat = str(pattern)
        parts.append(f"{label} ({pat})")
    return ";;".join(parts) if parts else "All files (*)"


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
        tab = app._notebook.tabText(app._notebook.currentIndex())
        if tab == "Movie Montage" and app._preview_selected_well:
            app._update_preview(app._preview_selected_well)


def save_matplotlib_fig(app, fig, default_name: str, *, plot_bg: str) -> None:
    import matplotlib as _mpl

    initial_dir = str(app._data_dir) if app._data_dir else ""
    initial_path = str(Path(initial_dir) / default_name) if initial_dir else default_name
    filter_str = _qt_file_filter_from_filetypes(app._FIG_FILETYPES)

    out, _selected = QFileDialog.getSaveFileName(
        app,
        "Save figure",
        initial_path,
        filter_str,
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
        QMessageBox.critical(app, "Save failed", str(exc))
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
    fig = getattr(app, "_line_fig", None)
    if fig is None:
        app._set_status("Line figure is not ready yet.")
        return
    _launch_editor_or_save(app, fig, "line_graphs.png", plot_bg=plot_bg, canvas=getattr(app, "_line_canvas", None))


def save_bar_figure(app, *, plot_bg: str) -> None:
    fig = getattr(app, "_bar_fig", None)
    if fig is None:
        app._set_status("Bar figure is not ready yet.")
        return
    tp = combo_text(getattr(app, "_bar_tp_cb", None), "0").replace(".", "_")
    _launch_editor_or_save(app, fig, f"bar_t{tp}.png", plot_bg=plot_bg, canvas=getattr(app, "_bar_canvas", None))


def save_scatter_figure(app, *, plot_bg: str) -> None:
    fig = getattr(app, "_scatter_fig", None)
    if fig is None:
        app._set_status("Scatter figure is not ready yet.")
        return
    ch_x = combo_text(getattr(app, "_scatter_ch_x_cb", None))
    ch_y = combo_text(getattr(app, "_scatter_ch_y_cb", None))
    tp = combo_text(getattr(app, "_scatter_tp_cb", None), "0").replace(".", "_")
    _launch_editor_or_save(
        app,
        fig,
        f"scatter_{ch_x}_vs_{ch_y}_t{tp}.png",
        plot_bg=plot_bg,
        canvas=getattr(app, "_scatter_canvas", None),
    )


def save_scatter_agg_figure(app, *, plot_bg: str) -> None:
    fig = getattr(app, "_scatter_agg_fig", None)
    if fig is None:
        app._set_status("Aggregate scatter figure is not ready yet.")
        return
    stat_x = combo_text(getattr(app, "_scatter_agg_stat_x_cb", None))
    stat_y = combo_text(getattr(app, "_scatter_agg_stat_y_cb", None))

    selected_timepoints: list[float] = []
    tp_checks = getattr(app, "_scatter_agg_tp_checks", None)
    if tp_checks:
        for tp_str, widget in tp_checks.items():
            try:
                if is_checked(widget):
                    selected_timepoints.append(float(tp_str))
            except Exception:
                pass
        selected_timepoints.sort()

    if selected_timepoints:
        tp_range = f"t{min(selected_timepoints):.1f}-{max(selected_timepoints):.1f}".replace(".", "_")
    else:
        tp_range = "no_tp"

    stat_x_safe = stat_x.replace(" ", "_").lower()
    stat_y_safe = stat_y.replace(" ", "_").lower()

    _launch_editor_or_save(
        app,
        fig,
        f"scatter_agg_{stat_x_safe}_vs_{stat_y_safe}_{tp_range}.png",
        plot_bg=plot_bg,
        canvas=getattr(app, "_scatter_agg_canvas", None),
    )
