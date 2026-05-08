"""Heatmap tab rendering.

Renders an arbitrary R×C grid colored by a chosen metric (mean above
threshold, fraction above threshold, cell count, or ratio mean) at a
single timepoint. Supports click-to-select wells, modifier-aware
selection, and a hover-value status update.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from matplotlib import patches as mpatches
from matplotlib import colormaps as mpl_colormaps

from well_viewer.data_loading import (
    _all_fluor_values_filtered,
    parse_well_token,
    resolve_value,
)
from well_viewer.heatmap_models import (
    HeatmapLayout,
    PLATE_DEFAULT_NAME,
    make_plate_layout,
)
from well_viewer.ratio_models import is_ratio_key


METRIC_MEAN = "Mean above threshold"
METRIC_FRACTION = "Fraction above threshold"
METRIC_COUNT = "Cell count"
METRIC_RATIO = "Ratio value"  # legacy; not exposed in METRIC_OPTIONS — ratios are picked via the channel dropdown.

METRIC_OPTIONS = [METRIC_MEAN, METRIC_FRACTION, METRIC_COUNT]


def active_layout(app) -> HeatmapLayout:
    """Return the active layout, synthesizing the plate default when needed."""
    layouts = list(getattr(app, "_heatmap_layouts", []) or [])
    name = getattr(app, "_active_heatmap_layout_name", None)
    if name:
        for lay in layouts:
            if lay.name == name:
                return lay
    if layouts:
        return layouts[0]
    return make_plate_layout((getattr(app, "_well_paths", {}) or {}).keys())


def _selected_metric(app) -> str:
    cb = getattr(app, "_heatmap_metric_cb", None)
    if cb is None:
        return METRIC_MEAN
    return str(cb.currentText() or METRIC_MEAN)


def _selected_cmap(app) -> str:
    cb = getattr(app, "_heatmap_cmap_cb", None)
    if cb is None:
        return "viridis"
    return str(cb.currentText() or "viridis")


def _selected_tp(app) -> Optional[float]:
    slider = getattr(app, "_heatmap_tp_slider", None)
    tps: List[float] = list(getattr(app, "_heatmap_tp_values", []) or [])
    if slider is None or not tps:
        return None
    idx = max(0, min(slider.value(), len(tps) - 1))
    return tps[idx]


def _expand_repset_wells(app, wells: Iterable[str]) -> List[str]:
    """If the rep-set average toggle is on, expand each input well to every
    well in the rep-set it belongs to. Otherwise return wells as-is.
    """
    src = list(wells)
    if not bool(getattr(app, "_heatmap_repset_avg", False)):
        return src
    rep_sets = list(getattr(app, "_rep_sets", []) or [])
    if not rep_sets:
        return src
    out: List[str] = []
    seen: set = set()
    for w in src:
        chosen: Optional[List[str]] = None
        for rs in rep_sets:
            members = list(getattr(rs, "wells", []) or [])
            if w in members:
                chosen = members
                break
        if chosen is None:
            if w not in seen:
                seen.add(w)
                out.append(w)
        else:
            for m in chosen:
                if m not in seen:
                    seen.add(m)
                    out.append(m)
    return out


def _repset_name_for_wells(app, wells: Iterable[str]) -> Optional[str]:
    """Return the name of the first rep-set that contains any of *wells*, or None."""
    if not bool(getattr(app, "_heatmap_repset_avg", False)):
        return None
    rep_sets = list(getattr(app, "_rep_sets", []) or [])
    if not rep_sets:
        return None
    src = list(wells)
    for w in src:
        for rs in rep_sets:
            members = list(getattr(rs, "wells", []) or [])
            if w in members:
                return str(getattr(rs, "name", "") or "")
    return None


def _cell_value(
    app,
    wells: Iterable[str],
    target_t: float,
    metric: str,
    val_col: str,
    threshold: float,
    cell_area_threshold: float,
    fluor_gates: Dict[str, float],
    ratios: Optional[Dict] = None,
) -> float:
    """Compute the heatmap cell value by pooling rows across *wells*."""
    expanded = _expand_repset_wells(app, wells)
    valid_wells = [w for w in expanded if w in app._well_paths]
    if not valid_wells:
        return float("nan")

    if metric == METRIC_COUNT:
        # Use aggregate to apply gate logic consistently, then read n_total.
        pts = app._aggregate_group(
            valid_wells, threshold=threshold, use_sem=False,
            val_col=val_col,
            cell_area_threshold=cell_area_threshold,
            fluor_gates=fluor_gates,
        )
        matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
        return float(matched[0][5]) if matched else 0.0

    if metric == METRIC_FRACTION:
        pts = app._aggregate_group(
            valid_wells, threshold=threshold, use_sem=False,
            val_col=val_col,
            cell_area_threshold=cell_area_threshold,
            fluor_gates=fluor_gates,
        )
        matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
        if not matched:
            return float("nan")
        return float(matched[0][3])

    if metric == METRIC_RATIO:
        # Pool ratio values across cells at the target timepoint. The legacy
        # _all_fluor_values_filtered helper still expects a list of dicts;
        # rebuild it on demand only for this branch.
        if not is_ratio_key(val_col):
            return float("nan")
        pooled_rows: List[dict] = []
        for w in valid_wells:
            pooled_rows.extend(app._get_rows(w))
        vals = _all_fluor_values_filtered(
            pooled_rows, val_col=val_col,
            cell_area_threshold=cell_area_threshold,
            fluor_gates=fluor_gates,
            ratios=ratios,
            tp_filter=target_t,
        )
        if not vals:
            return float("nan")
        return float(sum(vals) / len(vals))

    # METRIC_MEAN (and fallback)
    pts = app._aggregate_group(
        valid_wells, threshold=threshold, use_sem=False,
        val_col=val_col,
        cell_area_threshold=cell_area_threshold,
        fluor_gates=fluor_gates,
    )
    matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
    if not matched:
        return float("nan")
    return float(matched[0][1])


def _resolve_color_scale(arr: np.ndarray, app) -> Tuple[Optional[float], Optional[float]]:
    """Pick (vmin, vmax) for the heatmap.

    Mode is read from ``app._heatmap_scale_mode`` (Auto/Fixed). For Fixed we
    read ``app._heatmap_vmin`` / ``app._heatmap_vmax``. For Auto we use the
    global range pre-computed across every timepoint (kept on
    ``app._heatmap_global_vmin`` / ``app._heatmap_global_vmax``) so the
    colormap stays stable while scrubbing the timepoint slider.
    """
    mode = str(getattr(app, "_heatmap_scale_mode", "Auto") or "Auto")
    if mode == "Fixed":
        vmin = float(getattr(app, "_heatmap_vmin", float("nan")) or float("nan"))
        vmax = float(getattr(app, "_heatmap_vmax", float("nan")) or float("nan"))
        if math.isfinite(vmin) and math.isfinite(vmax) and vmax > vmin:
            return vmin, vmax
    # Auto: prefer the global range across all timepoints.
    g_vmin = getattr(app, "_heatmap_global_vmin", None)
    g_vmax = getattr(app, "_heatmap_global_vmax", None)
    if (
        g_vmin is not None and g_vmax is not None
        and math.isfinite(g_vmin) and math.isfinite(g_vmax) and g_vmax > g_vmin
    ):
        return float(g_vmin), float(g_vmax)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None, None
    return float(finite.min()), float(finite.max())


def _compute_global_range(
    app,
    layout,
    metric: str,
    val_col: str,
    threshold: float,
    cell_area_threshold: float,
    fluor_gates: Dict[str, float],
    ratios,
) -> Tuple[Optional[float], Optional[float]]:
    """Pool ``_cell_value`` across every (timepoint, cell) and return (vmin, vmax).

    Result is cached on ``app`` keyed on the inputs that influence it so
    timepoint-slider scrubbing does not retrigger the full sweep.
    """
    tps = list(getattr(app, "_heatmap_tp_values", []) or [])
    if not tps:
        return None, None

    cache_key = (
        id(layout),
        getattr(layout, "name", ""),
        metric,
        val_col,
        float(threshold),
        float(cell_area_threshold),
        tuple(sorted((fluor_gates or {}).items())),
        id(ratios),
        tuple(tps),
        bool(getattr(app, "_heatmap_repset_avg", False)),
        bool(getattr(app, "_heatmap_log_scale", False)),
    )
    cached = getattr(app, "_heatmap_global_range_cache", None)
    if cached is not None and cached.get("key") == cache_key:
        return cached["vmin"], cached["vmax"]

    vmin: Optional[float] = None
    vmax: Optional[float] = None
    for tp in tps:
        for (r, c), wells in layout.cells.items():
            if not (0 <= r < layout.rows and 0 <= c < layout.cols):
                continue
            try:
                v = _cell_value(
                    app, wells, tp, metric, val_col,
                    threshold, cell_area_threshold, fluor_gates, ratios,
                )
            except Exception:
                v = float("nan")
            if math.isfinite(v):
                vmin = v if vmin is None else min(vmin, v)
                vmax = v if vmax is None else max(vmax, v)

    app._heatmap_global_range_cache = {"key": cache_key, "vmin": vmin, "vmax": vmax}
    return vmin, vmax


def redraw_heatmap(app) -> None:
    ax = getattr(app, "_heatmap_ax", None)
    canvas = getattr(app, "_heatmap_canvas", None)
    fig = getattr(app, "_heatmap_fig", None)
    if ax is None or canvas is None or fig is None:
        return

    layout = active_layout(app)
    tp = _selected_tp(app)
    if tp is None:
        # Try to derive from the data; if still none, leave the canvas blank.
        ax.clear()
        ax.text(
            0.5, 0.5, "No timepoints loaded.",
            ha="center", va="center", transform=ax.transAxes,
            fontsize=10, color="gray",
        )
        ax.set_axis_off()
        canvas.draw_idle()
        return

    metric = _selected_metric(app)
    val_col = app._active_val_col
    threshold = app._get_thresh_frac_on(app._active_channel)
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    ratios = getattr(app, "_ratio_index", None)
    cmap_name = _selected_cmap(app)

    arr = np.full((layout.rows, layout.cols), np.nan, dtype=float)
    cell_well_index: Dict[Tuple[int, int], List[str]] = {}

    for (r, c), wells in layout.cells.items():
        if not (0 <= r < layout.rows and 0 <= c < layout.cols):
            continue
        cell_well_index[(r, c)] = list(wells)
        try:
            arr[r, c] = _cell_value(
                app, wells, tp, metric, val_col,
                threshold, cell_area_threshold, fluor_gates, ratios,
            )
        except Exception:
            arr[r, c] = float("nan")

    # Cache for click/hover handlers.
    app._heatmap_cell_well_index = cell_well_index
    app._heatmap_array = arr
    app._heatmap_layout_active = layout

    # Pool min/max across every timepoint so the colormap stays consistent
    # while the user scrubs the timepoint slider. Cached on app so this
    # only recomputes when an input changes.
    g_vmin, g_vmax = _compute_global_range(
        app, layout, metric, val_col,
        threshold, cell_area_threshold, fluor_gates, ratios,
    )
    app._heatmap_global_vmin = g_vmin
    app._heatmap_global_vmax = g_vmax

    # Render.
    vmin, vmax = _resolve_color_scale(arr, app)
    cmap = mpl_colormaps.get_cmap(cmap_name).copy()
    cmap.set_bad(color="#ECEFF4")  # neutral light fill for empty cells

    masked = np.ma.masked_invalid(arr)

    # Log-scale toggle: route values through a LogNorm so the colorbar
    # spans orders of magnitude. Values ≤ 0 become invalid (masked).
    norm = None
    log_scale = bool(getattr(app, "_heatmap_log_scale", False))
    if log_scale:
        from matplotlib.colors import LogNorm
        positive = masked.filled(np.nan)
        positive = positive[np.isfinite(positive) & (positive > 0)]
        log_vmin = float(np.min(positive)) if positive.size else None
        log_vmax = float(np.max(positive)) if positive.size else None
        # User-fixed vmin/vmax win when they're positive.
        if (vmin is not None and vmin > 0) and (vmax is not None and vmax > vmin):
            log_vmin, log_vmax = float(vmin), float(vmax)
        if log_vmin is not None and log_vmax is not None and log_vmax > log_vmin > 0:
            norm = LogNorm(vmin=log_vmin, vmax=log_vmax)
            # Mask non-positive entries so LogNorm doesn't choke.
            masked = np.ma.masked_where(~np.isfinite(masked.filled(np.nan)) | (masked.filled(np.nan) <= 0), masked)

    ax.clear()
    if norm is not None:
        im = ax.imshow(masked, aspect="equal", cmap=cmap, norm=norm,
                       origin="upper", interpolation="nearest")
    else:
        im = ax.imshow(masked, aspect="equal", cmap=cmap, vmin=vmin, vmax=vmax,
                       origin="upper", interpolation="nearest")

    row_labels = layout.row_labels or [str(i + 1) for i in range(layout.rows)]
    col_labels = layout.col_labels or [str(i + 1) for i in range(layout.cols)]
    ax.set_xticks(range(layout.cols))
    ax.set_xticklabels(col_labels[: layout.cols], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks(range(layout.rows))
    ax.set_yticklabels(row_labels[: layout.rows], fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # Cell text annotations.
    for (r, c), wells in cell_well_index.items():
        v = arr[r, c]
        if not math.isfinite(v):
            continue
        rs_name = _repset_name_for_wells(app, wells)
        if rs_name:
            text = rs_name
        elif len(wells) == 1:
            text = wells[0]
        else:
            text = f"{wells[0]}+{len(wells) - 1}"
        ax.text(
            c, r + 0.32, text,
            ha="center", va="center",
            fontsize=6, color="black", alpha=0.8,
        )
        ax.text(
            c, r - 0.05, _format_cell_value(v, metric),
            ha="center", va="center",
            fontsize=8, color="black",
        )

    # Selection rectangles.
    selected = set(getattr(app, "_selected_wells", set()) or set())
    for (r, c), wells in cell_well_index.items():
        if any(w in selected for w in wells):
            rect = mpatches.Rectangle(
                (c - 0.5, r - 0.5), 1.0, 1.0,
                fill=False, edgecolor="#FF6B35", linewidth=2.0,
            )
            ax.add_patch(rect)

    # Color bar — refill the persistent ``cax`` reserved at build time so
    # the main axes geometry stays put across redraws. Calling
    # ``fig.colorbar(im, ax=ax, ...)`` would silently shrink ``ax`` on
    # each redraw, which is what made the plot creep left and shrink.
    cax = getattr(app, "_heatmap_cax", None)
    if cax is not None:
        try:
            cax.cla()
            app._heatmap_colorbar = fig.colorbar(im, cax=cax)
            app._heatmap_colorbar.set_label(_metric_axis_label(metric, app), fontsize=8)
        except Exception:
            app._heatmap_colorbar = None
    else:
        # Fallback for any caller that bypasses the build-time axes setup.
        if hasattr(app, "_heatmap_colorbar") and app._heatmap_colorbar is not None:
            try:
                app._heatmap_colorbar.remove()
            except Exception:
                pass
        try:
            app._heatmap_colorbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
            app._heatmap_colorbar.set_label(_metric_axis_label(metric, app), fontsize=8)
        except Exception:
            app._heatmap_colorbar = None

    title = (
        f"{app._active_channel_label() if hasattr(app, '_active_channel_label') else app._active_channel.upper()}"
        f" — {metric} — t = {tp:g} h"
    )
    ax.set_title(title, fontsize=9)

    canvas.draw_idle()


def _format_cell_value(v: float, metric: str) -> str:
    if not math.isfinite(v):
        return ""
    if metric == METRIC_COUNT:
        return f"{int(round(v))}"
    if metric == METRIC_FRACTION:
        return f"{v:.2f}"
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 1:
        return f"{v:.2f}"
    return f"{v:.3g}"


def _metric_axis_label(metric: str, app) -> str:
    label = app._active_channel_label() if hasattr(app, "_active_channel_label") else ""
    if metric == METRIC_COUNT:
        return "Cell count"
    if metric == METRIC_FRACTION:
        return f"{label} fraction above threshold"
    if metric == METRIC_RATIO:
        return f"{label} (mean ratio)"
    return f"{label} mean above threshold"


# ── Click + hover handlers ───────────────────────────────────────────────────

def _cell_at_event(app, event) -> Optional[Tuple[int, int]]:
    if event.inaxes is None or event.xdata is None or event.ydata is None:
        return None
    layout = getattr(app, "_heatmap_layout_active", None)
    if layout is None:
        return None
    c = int(round(event.xdata))
    r = int(round(event.ydata))
    if not (0 <= r < layout.rows and 0 <= c < layout.cols):
        return None
    return r, c


def on_heatmap_click(app, event) -> None:
    # If the press landed on a row/col tick label, the label-drag handler
    # owns this gesture (rename / reorder). Don't also treat it as a cell
    # click — that would steal the selection from under a drag.
    try:
        from well_viewer.tabs.heatmap_tab_view import _hit_test_tick_label
        if _hit_test_tick_label(app, event) is not None:
            return
    except Exception:
        pass
    rc = _cell_at_event(app, event)
    if rc is None:
        return
    cell_index = getattr(app, "_heatmap_cell_well_index", {}) or {}
    wells_here = list(cell_index.get(rc, []))
    if not wells_here:
        return

    selected = set(getattr(app, "_selected_wells", set()) or set())
    modifiers = 0
    try:
        # Matplotlib events expose the GUI event for modifier inspection.
        gui_event = getattr(event, "guiEvent", None)
        if gui_event is not None and hasattr(gui_event, "modifiers"):
            modifiers = int(gui_event.modifiers())
    except Exception:
        modifiers = 0

    from PySide6.QtCore import Qt as _Qt
    shift = bool(modifiers & int(_Qt.ShiftModifier))
    ctrl = bool(modifiers & int(_Qt.ControlModifier))

    if shift:
        selected.update(wells_here)
    elif ctrl:
        for w in wells_here:
            if w in selected:
                selected.discard(w)
            else:
                selected.add(w)
    else:
        selected = set(wells_here)

    if hasattr(app, "_set_selected_wells"):
        app._set_selected_wells(selected)
    else:
        app._selected_wells = selected
        if hasattr(app, "_redraw"):
            app._redraw()


def on_heatmap_motion(app, event) -> None:
    rc = _cell_at_event(app, event)
    status_lbl = getattr(app, "_heatmap_status_lbl", None)
    if rc is None:
        if status_lbl is not None:
            status_lbl.setText("")
        return
    cell_index = getattr(app, "_heatmap_cell_well_index", {}) or {}
    arr = getattr(app, "_heatmap_array", None)
    wells = cell_index.get(rc, [])
    if status_lbl is not None:
        if not wells:
            status_lbl.setText(f"({rc[0]},{rc[1]}): empty")
        else:
            v = arr[rc[0], rc[1]] if arr is not None else float("nan")
            sample = ",".join(wells[:3]) + ("…" if len(wells) > 3 else "")
            metric = _selected_metric(app)
            status_lbl.setText(f"{sample}: {_format_cell_value(v, metric)}")
