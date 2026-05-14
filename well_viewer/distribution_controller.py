"""Distribution tab rendering.

Histograms / KDE / violin plots of the active value column at a chosen
timepoint, grouped per replicate set or per well. The active column is
ratio-aware (handled transparently by ``data_loading.resolve_value_series``).
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np

from well_viewer.data_loading import _all_fluor_values_filtered, iter_plot_groups


NO_DATA_MSG = (
    "No values to plot.\n"
    "Pick a channel, metric, and timepoint, and select wells or groups."
)


def _gaussian_kde(values: Sequence[float], grid: np.ndarray) -> np.ndarray:
    """Silverman's-rule Gaussian KDE evaluated on *grid*.

    Hand-rolled fallback so the distribution tab works without scipy. Returns
    an array of the same shape as *grid*.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n < 2:
        return np.zeros_like(grid)
    sd = float(np.std(arr, ddof=1))
    if sd <= 0.0:
        return np.zeros_like(grid)
    iqr = float(np.subtract(*np.percentile(arr, [75, 25])))
    sigma = min(sd, iqr / 1.34) if iqr > 0 else sd
    h = 0.9 * sigma * (n ** (-1.0 / 5.0))
    if h <= 0.0:
        return np.zeros_like(grid)
    diff = (grid[:, None] - arr[None, :]) / h
    kernel = np.exp(-0.5 * diff * diff) / math.sqrt(2.0 * math.pi)
    return kernel.sum(axis=1) / (n * h)


def _grid_for(values_lists: Iterable[Sequence[float]], n_pts: int = 200, log_x: bool = False) -> np.ndarray:
    """Build an x-axis grid spanning all per-group min/max."""
    chunks = [np.asarray(vs, dtype=float) for vs in values_lists]
    if not chunks:
        return np.linspace(0.0, 1.0, n_pts)
    pooled = np.concatenate(chunks)
    pooled = pooled[np.isfinite(pooled)]
    if pooled.size == 0:
        return np.linspace(0.0, 1.0, n_pts)
    lo = float(pooled.min())
    hi = float(pooled.max())
    if hi <= lo:
        hi = lo + 1.0
    if log_x and lo > 0:
        return np.logspace(math.log10(lo), math.log10(hi), n_pts)
    return np.linspace(lo, hi, n_pts)


def _empty_msg(ax) -> None:
    # Preserve the facecolor that the caller already applied via
    # apply_axes_style; matplotlib's ax.clear() resets it otherwise.
    fc = ax.get_facecolor()
    ax.clear()
    ax.set_facecolor(fc)
    fig = ax.figure
    if fig is not None:
        fig.set_facecolor(fc)
    ax.text(
        0.5, 0.5, NO_DATA_MSG,
        ha="center", va="center", transform=ax.transAxes,
        fontsize=10, color="gray",
    )
    ax.set_axis_off()


def _apply_card_style(app, ax) -> None:
    """Re-apply the active card's plot theme to *ax* after ``ax.clear()``.

    The other plot tabs route through ``well_viewer.plot_style.apply_ax_style``
    which already does this; the distribution renderer didn't, so on initial
    load the dark Screen-mode tokens never reached the axes (the user saw
    matplotlib's default white background instead).
    """
    from widgets.plot_card import apply_axes_style
    card = getattr(app, "_distribution_card", None)
    mode = getattr(card, "_plot_theme", "screen") if card is not None else "screen"
    apply_axes_style(ax, mode)


def redraw_distribution(app) -> None:
    """Redraw the Distribution tab."""
    ax = getattr(app, "_distribution_ax", None)
    canvas = getattr(app, "_distribution_canvas", None)
    if ax is None or canvas is None:
        return

    val_col = app._active_val_col
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    ratios = getattr(app, "_ratio_index", None)

    tp_str = (getattr(app, "_distribution_tp_var", None).currentText()
              if getattr(app, "_distribution_tp_var", None) is not None else "")
    try:
        tp_h: float = float(tp_str) if tp_str not in ("", "—", None) else float("nan")
    except (ValueError, TypeError):
        tp_h = float("nan")

    mode = (getattr(app, "_distribution_mode_var", None).currentText()
            if getattr(app, "_distribution_mode_var", None) is not None
            else "Histogram + KDE")
    bins = int(getattr(app, "_distribution_bins", 40) or 40)
    log_x = bool(getattr(app, "_distribution_log_x", False))

    groups: List[Tuple[str, str, np.ndarray]] = []
    for name, color, df in iter_plot_groups(app, fallback_to_all=False):
        tp_filter = tp_h if math.isfinite(tp_h) else None
        vals = _all_fluor_values_filtered(
            df, val_col=val_col,
            cell_area_threshold=cell_area_threshold,
            fluor_gates=fluor_gates,
            ratios=ratios,
            tp_filter=tp_filter,
        )
        if vals.size:
            groups.append((name, color, vals))

    ax.clear()
    _apply_card_style(app, ax)
    if not groups:
        _empty_msg(ax)
        canvas.draw_idle()
        return

    ax.set_axis_on()

    if mode == "Violin (per group)":
        data = [vals for _, _, vals in groups]
        labels = [name for name, _, _ in groups]
        parts = ax.violinplot(data, showmeans=False, showmedians=True)
        for i, body in enumerate(parts.get("bodies", [])):
            body.set_facecolor(groups[i][1])
            body.set_edgecolor(groups[i][1])
            body.set_alpha(0.55)
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Value")
    else:
        grid = _grid_for((vs for _, _, vs in groups), log_x=log_x)
        for name, color, vals in groups:
            if mode in ("Histogram", "Histogram + KDE"):
                ax.hist(
                    vals, bins=bins, density=True, alpha=0.45,
                    color=color, label=f"{name} (n={int(vals.size)})",
                )
            if mode in ("KDE only", "Histogram + KDE"):
                kde = _gaussian_kde(vals, grid)
                if np.any(kde > 0):
                    ax.plot(grid, kde, color=color, lw=1.6,
                            label=None if mode == "Histogram + KDE" else f"{name} (n={len(vals)})")
        if log_x:
            try:
                ax.set_xscale("log")
            except Exception:
                pass
        ax.set_xlabel(_xlabel_for(app))
        ax.set_ylabel("Density")
        if any(name for name, _, _ in groups):
            try:
                ax.legend(fontsize=7, loc="best")
            except Exception:
                pass

    # Threshold marker for non-violin modes (vertical dashed line).
    if mode != "Violin (per group)":
        try:
            threshold = app._get_thresh_frac_on(app._active_channel)
            if math.isfinite(threshold):
                ax.axvline(threshold, color="orange", linestyle="--", linewidth=1.0, alpha=0.8)
        except Exception:
            pass

    title = _title_for(app, tp_h, int(sum(int(vs.size) for _, _, vs in groups)), len(groups))
    ax.set_title(title, fontsize=9)
    canvas.draw_idle()


def _xlabel_for(app) -> str:
    label = app._active_channel_label() if hasattr(app, "_active_channel_label") else app._active_channel.upper()
    metric = getattr(app, "_active_metric", "")
    if metric and not str(getattr(app, "_active_val_col", "")).startswith("ratio:"):
        return f"{label} {metric.replace('_', ' ')}"
    return label


def _title_for(app, tp_h: float, n_cells: int, n_groups: int) -> str:
    label = app._active_channel_label() if hasattr(app, "_active_channel_label") else app._active_channel.upper()
    if math.isfinite(tp_h):
        tp_str = f"t = {tp_h:g} h"
    else:
        tp_str = "all timepoints"
    return f"{label} distribution — {tp_str} ({n_cells} cells, {n_groups} groups)"
