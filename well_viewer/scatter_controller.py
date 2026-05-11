"""Scatter plot data collection and rendering for multi-well fluorescence analysis."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd

from . import debug_flags
from .data_loading import df_included_mask, resolve_value_series

NO_SELECTION_MSG = "No wells or well groups selected.\nSelect wells on the left panel or define groups to plot."


def get_all_timepoints(app) -> List[float]:
    """Extract all unique included timepoints across loaded wells."""
    timepoints: set = set()
    for label in app._well_paths:
        df = app._get_rows(label)
        if df is None or df.empty or "timepoint_hours" not in df.columns:
            continue
        mask = df_included_mask(df)
        tp = pd.to_numeric(df["timepoint_hours"], errors="coerce").where(mask)
        timepoints.update(float(t) for t in tp.dropna().unique())
    return sorted(timepoints)


def collect_scatter_data(
    app,
    col_x: str,
    col_y: str,
    timepoint_h: float,
    *,
    well_colors: List[str],
    cell_area_threshold: float = 0.0,
    fluor_gate_x: float = 0.0,
    fluor_gate_y: float = 0.0,
    ratios: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Collect scatter plot data for the given column names and timepoint.

    Groups data by well group (if defined) or by individual well. Each group/well
    gets a distinct color and contains x/y values plus metadata for click tracking.

    Args:
        app: WellViewerApp instance with data and state
        col_x: X-axis column name (e.g., "gfp_mean_intensity" or "gfp_smfish_count")
        col_y: Y-axis column name (e.g., "mcherry_mean_intensity" or "mcherry_smfish_count")
        timepoint_h: Target timepoint in hours
        well_colors: List of color strings for coloring groups/wells
        cell_area_threshold: Minimum cell area in pixels; cells below are excluded
        fluor_gate_x: FluorGating threshold for X channel; cells below are excluded
        fluor_gate_y: FluorGating threshold for Y channel; cells below are excluded

    Returns:
        Dict mapping group/well name → {
            'x': [values],
            'y': [values],
            'color': color_str,
            'metadata': [(well_label, fov, row_idx), ...]
        }
    """

    scatter_data: Dict[str, Dict[str, Any]] = {}

    if ratios is None:
        ratios = getattr(app, "_ratio_index", None) or {}

    def _collect_well(well_label: str) -> Optional[Tuple[np.ndarray, np.ndarray, list]]:
        df = app._get_rows(well_label)
        if df is None or df.empty:
            return None
        if "timepoint_hours" not in df.columns or "area_px" not in df.columns:
            return None
        mask = df_included_mask(df).to_numpy(copy=True)
        tp = pd.to_numeric(df["timepoint_hours"], errors="coerce").to_numpy()
        with np.errstate(invalid="ignore"):
            mask &= np.isfinite(tp) & (np.abs(tp - timepoint_h) <= 1e-6)
        area = pd.to_numeric(df["area_px"], errors="coerce").to_numpy()
        with np.errstate(invalid="ignore"):
            mask &= np.isfinite(area) & (area > cell_area_threshold)
        x = resolve_value_series(df, col_x, ratios).to_numpy()
        y = resolve_value_series(df, col_y, ratios).to_numpy()
        mask &= np.isfinite(x) & np.isfinite(y) & (x > fluor_gate_x) & (y > fluor_gate_y)
        if not mask.any():
            return None
        sel = df.loc[mask]
        if sel.empty:
            return None
        filenames = (sel["filename"].astype(str).to_numpy()
                     if "filename" in sel.columns else np.array([""] * len(sel)))
        nuclear_ids = (sel["nucleus_id"].astype(str).to_numpy()
                       if "nucleus_id" in sel.columns else np.array([""] * len(sel)))
        row_idx = sel.index.to_numpy()
        if debug_flags.review_scatter_debug_enabled() and len(sel) > 0:
            print(f"DEBUG scatter_controller: Row keys: {list(sel.columns)}")
            print(f"DEBUG scatter_controller: filename={filenames[0]!r}, nuclear_id={nuclear_ids[0]!r}")
        metadata = [(well_label, fn, nid, int(ri))
                    for fn, nid, ri in zip(filenames, nuclear_ids, row_idx)]
        return x[mask], y[mask], metadata

    # Use active replicate sets if defined, otherwise fall back to selected wells
    active_rsets = app._rep_sets_active()

    if active_rsets:
        from well_viewer.lineplot_controller import _apply_order as _apply_rs_order
        active_rsets = _apply_rs_order(
            active_rsets,
            list(getattr(app, "_line_order_rsets", []) or []),
            key=lambda r: getattr(r, "name", ""),
        )
        for group_idx, rset in enumerate(active_rsets):
            group_name = rset.name
            color = well_colors[group_idx % len(well_colors)]
            xs: List[np.ndarray] = []
            ys: List[np.ndarray] = []
            metadata: List[Tuple[str, str, str, int]] = []
            for well_label in rset.wells:
                if well_label not in app._well_paths:
                    continue
                got = _collect_well(well_label)
                if got is None:
                    continue
                wx, wy, wmeta = got
                xs.append(wx); ys.append(wy); metadata.extend(wmeta)
            if xs:
                scatter_data[group_name] = {
                    'x': np.concatenate(xs).tolist(),
                    'y': np.concatenate(ys).tolist(),
                    'color': color,
                    'metadata': metadata,
                }
    else:
        from well_viewer.lineplot_controller import _apply_order as _apply_well_order
        selected_wells = sorted(
            (lbl for lbl in app._selected_wells if lbl in app._well_paths),
            key=lambda lbl: app._parse_rc(lbl),
        )
        selected_wells = _apply_well_order(
            selected_wells,
            list(getattr(app, "_line_order_wells", []) or []),
            key=lambda x: x,
        )
        for well_idx, well_label in enumerate(selected_wells):
            color = well_colors[well_idx % len(well_colors)]
            got = _collect_well(well_label)
            if got is None:
                continue
            wx, wy, wmeta = got
            scatter_data[well_label] = {
                'x': wx.tolist(),
                'y': wy.tolist(),
                'color': color,
                'metadata': wmeta,
            }

    return scatter_data


def redraw_scatter(
    app,
    col_x: str,
    col_y: str,
    timepoint_h: float,
    *,
    well_colors: List[str],
    cell_area_threshold: float = 0.0,
    fluor_gate_x: float = 0.0,
    fluor_gate_y: float = 0.0,
) -> None:
    """Redraw scatter plot with new data.

    Args:
        app: WellViewerApp instance
        col_x: X-axis column name (e.g., "gfp_mean_intensity" or "gfp_smfish_count")
        col_y: Y-axis column name (e.g., "mcherry_mean_intensity" or "mcherry_smfish_count")
        timepoint_h: Timepoint in hours
        well_colors: List of colors for groups/wells
        cell_area_threshold: Minimum cell area in pixels; cells below are excluded
        fluor_gate_x: FluorGating threshold for X channel; cells below are excluded
        fluor_gate_y: FluorGating threshold for Y channel; cells below are excluded
    """
    active_rsets = app._rep_sets_active()
    selected_wells = [lbl for lbl in app._selected_wells if lbl in app._well_paths]

    # Clear existing plot
    app._ax_scatter.clear()

    if not selected_wells and not active_rsets:
        app._scatter_interaction_cache = {"points": []}
        app._ax_scatter.text(
            0.5,
            0.5,
            NO_SELECTION_MSG,
            ha='center',
            va='center',
            transform=app._ax_scatter.transAxes,
            fontsize=10,
            color='gray',
        )
        app._ax_scatter.set_axis_off()
        app._scatter_canvas.draw()
        return

    # Collect scatter data
    scatter_data = collect_scatter_data(
        app,
        col_x,
        col_y,
        timepoint_h,
        well_colors=well_colors,
        cell_area_threshold=cell_area_threshold,
        fluor_gate_x=fluor_gate_x,
        fluor_gate_y=fluor_gate_y,
    )

    # Plot each group/well as separate scatter series
    interaction_points: List[Tuple[float, float, Tuple[str, str, str, int]]] = []
    for label, data in scatter_data.items():
        app._ax_scatter.scatter(
            data['x'],
            data['y'],
            label=label,
            color=data['color'],
            alpha=0.6,
            s=30,
            edgecolors='none',
        )

        # Store metadata for click tracking
        if not hasattr(app, '_scatter_metadata'):
            app._scatter_metadata = {}
        app._scatter_metadata[label] = data['metadata']
        interaction_points.extend(
            (x, y, meta) for x, y, meta in zip(data['x'], data['y'], data['metadata'])
        )

    # Format axes — derive readable label from column name
    def _col_label(col: str) -> str:
        if col.endswith("_smfish_count"):
            ch = col[:-len("_smfish_count")]
            return f"{ch.upper()} smFISH Count"
        elif col.endswith("_mean_intensity"):
            ch = col[:-len("_mean_intensity")]
            return f"{ch.upper()} Mean Intensity"
        return col

    app._ax_scatter.set_xlabel(_col_label(col_x))
    app._ax_scatter.set_ylabel(_col_label(col_y))
    app._ax_scatter.set_title(f"Scatter: {_col_label(col_x)} vs {_col_label(col_y)} (t={timepoint_h}h)")
    app._ax_scatter.grid(True, alpha=0.3)
    if scatter_data:
        app._ax_scatter.legend(loc='best', fontsize=8)

    # Redraw canvas
    app._scatter_interaction_cache = {
        "points": interaction_points,
        "timepoint_h": timepoint_h,
        "col_x": col_x,
        "col_y": col_y,
    }
    app._scatter_canvas.draw()


def collect_scatter_agg_data(
    app,
    stat_x: str,  # e.g., "Mean Fluorescence GFP"
    stat_y: str,  # e.g., "Fraction On mCherry"
    timepoints_h: List[float],
    *,
    well_colors: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Collect aggregate scatter plot data by computing statistics for each replicate/well.

    Args:
        app: WellViewerApp instance with data and state
        stat_x: X-axis statistic (e.g., "Mean Fluorescence GFP" or "Fraction On GFP")
        stat_y: Y-axis statistic (e.g., "Mean Fluorescence mCherry" or "Fraction On mCherry")
        timepoints_h: List of target timepoints in hours
        well_colors: List of color strings for coloring replicates/wells

    Returns:
        Dict mapping "label_tp{timepoint}" → {
            'x': [mean_x],
            'y': [mean_y],
            'x_err': [error_x],
            'y_err': [error_y],
            'color': color_str,
            'timepoint': timepoint_h,
            'label': 'label (t=Xh)'
        }
    """
    scatter_data: Dict[str, Dict[str, Any]] = {}

    # Extract channel and metric type from statistic names
    def parse_statistic(stat_str: str) -> Tuple[str, str]:
        """Parse statistic strings.

        Returns ``(channel_or_label, metric)`` where ``metric`` is one of
        ``"mean"`` | ``"frac"`` | ``"smfish"`` | ``"ratio"``. For ratios
        the first element is the dropdown label (mixed case) so the caller
        can look it up in ``app._label_to_channel_key``; for the others
        it's the lowercased channel token.
        """
        if stat_str.startswith("Mean Ratio "):
            label = stat_str[len("Mean Ratio "):]
            return label, "ratio"
        if stat_str.startswith("Mean Fluorescence"):
            channel = stat_str.replace("Mean Fluorescence ", "").lower()
            return channel, "mean"
        elif stat_str.startswith("Fraction On"):
            channel = stat_str.replace("Fraction On ", "").lower()
            return channel, "frac"
        elif stat_str.startswith("smFISH Count"):
            channel = stat_str.replace("smFISH Count ", "").lower()
            return channel, "smfish"
        else:
            return "gfp", "mean"

    ch_x, metric_x = parse_statistic(stat_x)
    ch_y, metric_y = parse_statistic(stat_y)
    use_sem = app._use_sem
    # Per-channel cell-gating thresholds don't apply to ratios — use 0 so
    # every cell with a defined ratio contributes to the well-level mean.
    threshold_x = 0.0 if metric_x == "ratio" else app._get_thresh_frac_on(ch_x)
    threshold_y = 0.0 if metric_y == "ratio" else app._get_thresh_frac_on(ch_y)
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()  # Apply all channel gates
    ratios = getattr(app, "_ratio_index", None)
    label_to_key = getattr(app, "_label_to_channel_key", None) or {}

    # Get active replicates or selected wells
    active_rsets = app._rep_sets_active()

    if active_rsets:
        # Mode: replicate sets
        labels_to_process = [(r.name, r.wells) for r in active_rsets]
    else:
        # Mode: individual wells
        selected_wells = sorted(
            (lbl for lbl in app._selected_wells if lbl in app._well_paths),
            key=lambda lbl: app._parse_rc(lbl),
        )
        labels_to_process = [(lbl, [lbl]) for lbl in selected_wells]

    # Define markers for each well/group
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h', '+', 'x']  # circle, square, triangle, diamond, etc.

    # Create color gradient for timepoints using a colormap
    if timepoints_h:
        cmap = cm.get_cmap('viridis')
        normalized_tps = np.linspace(0, 1, len(timepoints_h))
        tp_to_color = {tp: cmap(norm_val) for tp, norm_val in zip(sorted(timepoints_h), normalized_tps)}
    else:
        tp_to_color = {}

    # Derive column names based on metric type
    if metric_x == "smfish":
        val_col_x = f"{ch_x}_smfish_count"
        threshold_x = 0  # No threshold for smfish counts (all spots)
    elif metric_x == "ratio":
        val_col_x = label_to_key.get(ch_x, "")
    else:
        val_col_x = f"{ch_x}_mean_intensity"

    if metric_y == "smfish":
        val_col_y = f"{ch_y}_smfish_count"
        threshold_y = 0  # No threshold for smfish counts (all spots)
    elif metric_y == "ratio":
        val_col_y = label_to_key.get(ch_y, "")
    else:
        val_col_y = f"{ch_y}_mean_intensity"

    def _agg_wells(wells, tp, val_col, threshold, metric):
        """Compute mean ± SD/SEM across well-level values (same method as bar plot _compute_rep_stats)."""
        if not val_col:
            return float("nan"), 0.0
        well_means: List[float] = []
        well_fracs: List[float] = []
        for well_label in wells:
            if well_label not in app._well_paths:
                continue
            pts = app._aggregate_well(
                well_label, threshold=threshold, use_sem=False,
                val_col=val_col,
                cell_area_threshold=cell_area_threshold,
                fluor_gates=fluor_gates,
            )
            matched = [(m, f) for t, m, _s, f, *_ in pts if abs(t - tp) < 1e-6]
            if matched:
                m, f = matched[0]
                if not math.isnan(m):
                    well_means.append(m)
                if not math.isnan(f):
                    well_fracs.append(f)

        vals = well_fracs if metric == "frac" else well_means
        if not vals:
            return float("nan"), 0.0
        arr = np.asarray(vals, dtype=float)
        mean_v = float(arr.mean())
        n = arr.size
        sd = float(arr.std(ddof=0)) if n > 1 else 0.0
        err = sd / math.sqrt(n) if (use_sem and n > 1) else sd
        return mean_v, err

    for label_idx, (label, wells) in enumerate(labels_to_process):
        marker = markers[label_idx % len(markers)]

        for tp in sorted(timepoints_h):
            mean_x, err_x = _agg_wells(wells, tp, val_col_x, threshold_x, metric_x)
            mean_y, err_y = _agg_wells(wells, tp, val_col_y, threshold_y, metric_y)

            if math.isnan(mean_x) or math.isnan(mean_y):
                continue

            data_key = f"{label}_tp{tp}"
            tp_color = tp_to_color.get(tp, (0, 0, 0, 1))
            scatter_data[data_key] = {
                'x': [mean_x],
                'y': [mean_y],
                'x_err': [err_x],
                'y_err': [err_y],
                'color': tp_color,
                'marker': marker,
                'timepoint': tp,
                'label': f"{label} (t={tp}h)",
            }

    return scatter_data


def redraw_scatter_agg(
    app,
    stat_x: str,
    stat_y: str,
    timepoints_h: List[float],
    *,
    well_colors: List[str],
) -> None:
    """Redraw aggregate scatter plot with statistics for multiple timepoints.

    Args:
        app: WellViewerApp instance
        stat_x: X-axis statistic (e.g., "Mean Fluorescence GFP")
        stat_y: Y-axis statistic (e.g., "Fraction On GFP")
        timepoints_h: List of timepoints in hours
        well_colors: List of colors for replicates/wells
    """
    active_rsets = app._rep_sets_active()
    selected_wells = [lbl for lbl in app._selected_wells if lbl in app._well_paths]

    # Clear existing plot
    app._ax_scatter_agg.clear()

    if not selected_wells and not active_rsets:
        app._ax_scatter_agg.text(
            0.5,
            0.5,
            NO_SELECTION_MSG,
            ha='center',
            va='center',
            transform=app._ax_scatter_agg.transAxes,
            fontsize=10,
            color='gray',
        )
        app._ax_scatter_agg.set_axis_off()
        app._scatter_agg_canvas.draw()
        return

    # Collect aggregate scatter data
    scatter_data = collect_scatter_agg_data(
        app,
        stat_x,
        stat_y,
        timepoints_h,
        well_colors=well_colors,
    )

    if not scatter_data:
        app._ax_scatter_agg.text(
            0.5, 0.5,
            "No data available.\nPlease select wells/groups and timepoints.",
            ha='center', va='center',
            transform=app._ax_scatter_agg.transAxes,
            fontsize=10,
            color='gray'
        )
    else:
        # Plot each replicate/well-timepoint as separate error bar series
        for label, data in scatter_data.items():
            app._ax_scatter_agg.errorbar(
                data['x'],
                data['y'],
                xerr=data['x_err'],
                yerr=data['y_err'],
                label=data['label'],
                color=data['color'],
                marker=data.get('marker', 'o'),
                markersize=8,
                linestyle='none',
                capsize=5,
                capthick=1.5,
                alpha=0.7,
            )

        # Format axes
        app._ax_scatter_agg.set_xlabel(stat_x)
        app._ax_scatter_agg.set_ylabel(stat_y)
        tp_range = f"t={min(timepoints_h)}h to {max(timepoints_h)}h" if timepoints_h else ""
        app._ax_scatter_agg.set_title(f"Aggregate Scatter: {stat_x} vs {stat_y} ({tp_range})")
        app._ax_scatter_agg.grid(True, alpha=0.3)
        app._ax_scatter_agg.legend(loc='best', fontsize=8)

    # Redraw canvas
    app._scatter_agg_canvas.draw()
