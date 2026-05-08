"""Scatter plot data collection and rendering for multi-well fluorescence analysis."""

from __future__ import annotations

import math
import statistics as _statistics
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

from . import debug_flags
from .data_loading import resolve_value

NO_SELECTION_MSG = "No wells or well groups selected.\nSelect wells on the left panel or define groups to plot."


def get_all_timepoints(app) -> List[float]:
    """Extract all unique timepoints from loaded CSV data across all wells.

    Returns:
        Sorted list of unique timepoints (in hours) from all wells.
    """
    timepoints = set()

    for label in app._well_paths:
        rows = app._get_rows(label)
        for row in rows:
            if not app._row_is_included(row):
                continue
            try:
                tp = float(row.get("timepoint_hours", float('nan')))
                if not (tp != tp):  # Skip NaN
                    timepoints.add(tp)
            except (ValueError, TypeError):
                pass

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

    # Use active replicate sets if defined, otherwise fall back to selected wells
    active_rsets = app._rep_sets_active()

    if active_rsets:
        # Group by replicate sets
        for group_idx, rset in enumerate(active_rsets):
            group_name = rset.name
            color = well_colors[group_idx % len(well_colors)]
            x_vals: List[float] = []
            y_vals: List[float] = []
            metadata: List[Tuple[str, Optional[str], int]] = []

            # Collect data from all wells in this replicate set
            for well_label in rset.wells:
                if well_label not in app._well_paths:
                    continue

                rows = app._get_rows(well_label)
                for row_idx, row in enumerate(rows):
                    if not app._row_is_included(row):
                        continue
                    # Filter by timepoint
                    try:
                        tp = float(row.get("timepoint_hours", float('nan')))
                    except (ValueError, TypeError):
                        continue

                    if abs(tp - timepoint_h) > 1e-6:
                        continue

                    # Filter by cell area threshold
                    try:
                        area = float(row.get("area_px", float('nan')))
                    except (ValueError, TypeError):
                        continue

                    if (area != area) or area <= cell_area_threshold:  # Skip NaN or below threshold
                        continue

                    # Filter by fluorescence gate threshold on both channels.
                    # ``resolve_value`` transparently handles ratio: keys.
                    x = resolve_value(row, col_x, ratios)
                    y = resolve_value(row, col_y, ratios)

                    if (x != x) or (y != y):  # Skip NaN
                        continue

                    if x <= fluor_gate_x or y <= fluor_gate_y:
                        continue

                    x_vals.append(x)
                    y_vals.append(y)

                    # Store filename and nucleus_id for image lookup
                    filename = row.get("filename", "")
                    nuclear_id = row.get("nucleus_id", "")
                    if row_idx == 0 and debug_flags.review_scatter_debug_enabled():  # Debug first row only
                        print(f"DEBUG scatter_controller: Row keys: {list(row.keys())}")
                        print(f"DEBUG scatter_controller: filename={filename!r}, nuclear_id={nuclear_id!r}")
                    metadata.append((well_label, filename, nuclear_id, row_idx))

            if x_vals:  # Only add group if it has data
                scatter_data[group_name] = {
                    'x': x_vals,
                    'y': y_vals,
                    'color': color,
                    'metadata': metadata,
                }
    else:
        # No groups: show each well separately
        selected_wells = sorted(
            (lbl for lbl in app._selected_wells if lbl in app._well_paths),
            key=lambda lbl: app._parse_rc(lbl),
        )

        for well_idx, well_label in enumerate(selected_wells):
            color = well_colors[well_idx % len(well_colors)]
            x_vals: List[float] = []
            y_vals: List[float] = []
            metadata: List[Tuple[str, str, str, int]] = []

            rows = app._get_rows(well_label)
            for row_idx, row in enumerate(rows):
                if not app._row_is_included(row):
                    continue
                # Filter by timepoint
                try:
                    tp = float(row.get("timepoint_hours", float('nan')))
                except (ValueError, TypeError):
                    continue

                if abs(tp - timepoint_h) > 1e-6:
                    continue

                # Filter by cell area threshold
                try:
                    area = float(row.get("area_px", float('nan')))
                except (ValueError, TypeError):
                    continue

                if (area != area) or area <= cell_area_threshold:  # Skip NaN or below threshold
                    continue

                # Filter by fluorescence gate threshold on both channels
                try:
                    x = float(row.get(col_x, float('nan')))
                    y = float(row.get(col_y, float('nan')))
                except (ValueError, TypeError):
                    continue

                if (x != x) or (y != y):  # Skip NaN
                    continue

                if x <= fluor_gate_x or y <= fluor_gate_y:
                    continue

                x_vals.append(x)
                y_vals.append(y)

                # Store filename and nucleus_id for image lookup
                filename = row.get("filename", "")
                nuclear_id = row.get("nucleus_id", "")
                metadata.append((well_label, filename, nuclear_id, row_idx))

            if x_vals:  # Only add well if it has data
                scatter_data[well_label] = {
                    'x': x_vals,
                    'y': y_vals,
                    'color': color,
                    'metadata': metadata,
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
    use_sem = app._use_sem.get()
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
        mean_v = _statistics.mean(vals)
        n = len(vals)
        sd = _statistics.pstdev(vals) if n > 1 else 0.0
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
