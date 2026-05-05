"""Statistics-tab computation helpers for WellViewerApp."""

from __future__ import annotations

import statistics as _pystats
from typing import Dict, List, Optional, Tuple

from well_viewer.data_loading import is_ratio_key, resolve_value, row_is_included


_STAT_LABELS = {
    "mean": "Mean (above threshold)",
    "median": "Median (above threshold)",
    "fraction": "Fraction above threshold",
}


def _compute_statistic(
    vals: List[float], statistic: str, threshold: float
) -> Optional[float]:
    """Compute the per-bucket summary value for ``statistic``.

    For "mean" / "median" the value is computed over cells whose value is
    above ``threshold``; for "fraction" it's the proportion of all cells
    whose value is above ``threshold``. Returns None when there is no
    underlying data to summarise.
    """
    if not vals:
        return None
    if statistic == "fraction":
        return sum(1 for v in vals if v > threshold) / len(vals)
    above = [v for v in vals if v > threshold]
    if not above:
        return None
    if statistic == "median":
        return float(_pystats.median(above))
    return float(sum(above) / len(above))


def collect_group_values(
    app,
    grp,
    target_t: float,
    *,
    val_col: Optional[str] = None,
    threshold: Optional[float] = None,
    statistic: str = "mean",
) -> List[float]:
    """Return one summary value per well (or per-FOV when the group has 1 well).

    Each element of the returned list is the chosen ``statistic`` (mean /
    median / fraction-above-threshold) computed across the cells in that well
    or FOV. When the group contains exactly one well, samples are aggregated
    per FOV so single-well groups yield enough samples to compute a meaningful
    SD via the chosen test.
    """
    val_col = val_col or app._active_val_col
    if threshold is None:
        try:
            threshold = float(app._get_thresh_frac_on(app._active_channel))
        except Exception:
            threshold = float(getattr(app, "_threshold", 0.0))
    threshold = float(threshold)
    ratios = getattr(app, "_ratio_index", None)

    wells = [w for w in grp.wells if w in app._well_paths]
    if not wells:
        return []
    aggregate_per_fov = (len(wells) == 1)

    samples: List[float] = []
    for lbl in wells:
        rows = app._get_rows(lbl)
        buckets: Dict[str, List[float]] = {}
        for row in rows:
            if not row_is_included(row):
                continue
            raw_t = row.get("timepoint_hours")
            try:
                t = float(raw_t)
            except (TypeError, ValueError):
                continue
            if abs(t - target_t) > 1e-6:
                continue
            v = resolve_value(row, val_col, ratios)
            if v is None or v != v:  # filter NaN
                continue
            if aggregate_per_fov:
                key = str(row.get("fov", "") or "").strip() or "_"
            else:
                key = lbl
            buckets.setdefault(key, []).append(float(v))

        for vals in buckets.values():
            stat = _compute_statistic(vals, statistic, threshold)
            if stat is not None:
                samples.append(stat)
    return samples


def collect_group_per_cell_values(
    app, grp, target_t: float, *, val_col: Optional[str] = None,
    threshold: Optional[float] = None,
) -> List[float]:
    """Return per-cell values above threshold for KS-test (distribution comparison)."""
    val_col = val_col or app._active_val_col
    if threshold is None:
        try:
            threshold = float(app._get_thresh_frac_on(app._active_channel))
        except Exception:
            threshold = float(getattr(app, "_threshold", 0.0))
    threshold = float(threshold)
    ratios = getattr(app, "_ratio_index", None)
    vals: List[float] = []
    for lbl in grp.wells:
        if lbl not in app._well_paths:
            continue
        for row in app._get_rows(lbl):
            if not row_is_included(row):
                continue
            try:
                t = float(row.get("timepoint_hours"))
            except (TypeError, ValueError):
                continue
            if abs(t - target_t) > 1e-6:
                continue
            v = resolve_value(row, val_col, ratios)
            if v is None or v != v:
                continue
            if v > threshold:
                vals.append(float(v))
    return vals


def _channel_label_for_val_col(val_col: str) -> str:
    """Human-readable channel label for the chart title / status string."""
    if is_ratio_key(val_col):
        return val_col.split(":", 1)[-1]
    if val_col.endswith("_mean_intensity"):
        return val_col[: -len("_mean_intensity")].upper()
    if val_col.endswith("_smfish_count"):
        return val_col[: -len("_smfish_count")].upper() + " (spots)"
    return val_col


def draw_ks_cdf(app, group_vals: List[Tuple[str, List[float]]], tp_str: str, well_colors: list[str]) -> None:
    """Draw empirical CDFs for the two KS-test groups."""
    ax = app._stats_ax
    ax.cla()
    colors = [well_colors[0], well_colors[1]]
    val_col = ""
    try:
        val_col = app._stats_active_val_col()
    except Exception:
        val_col = getattr(app, "_active_val_col", "")
    for (name, vals), color in zip(group_vals, colors):
        if not vals:
            continue
        sv = sorted(vals)
        n = len(sv)
        xs = [sv[0]] + sv + [sv[-1]]
        ys = [0.0] + [(i + 1) / n for i in range(n)] + [1.0]
        ax.step(xs, ys, where="post", label=name, color=color, linewidth=1.5)
    ax.set_xlabel(_channel_label_for_val_col(val_col) or "value", fontsize=8)
    ax.set_ylabel("Cumulative fraction", fontsize=8)
    ax.set_title(f"Empirical CDF  —  t = {tp_str} h", fontsize=9)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_ylim(-0.02, 1.05)
    try:
        app._stats_fig.tight_layout(pad=0.8)
    except Exception:
        pass
    app._stats_canvas_widget.draw_idle()


def run_stats(app, *, collect_group_values_fn, draw_ks_cdf_fn) -> None:
    """Run the selected statistical test across all group pairs."""
    tp_str = app._stats_tp_cb.currentText()
    if tp_str in ("—", ""):
        app._stats_write_result("No timepoint selected.")
        return
    try:
        target_t = float(tp_str)
    except ValueError:
        app._stats_write_result("Invalid timepoint.")
        return

    groups = [g for g in app._stats_groups if g.wells]
    if len(groups) < 2:
        app._stats_write_result("Define at least 2 non-empty groups to run a test.")
        return

    test = app._stats_test_cb.currentText()
    is_ks = test.startswith("KS")

    if is_ks:
        if len(groups) != 2:
            app._stats_write_result("KS test requires exactly 2 groups.")
            return
        for g in groups:
            if len(g.wells) != 1:
                app._stats_write_result(
                    "KS test requires each group to contain exactly 1 well.\n"
                    f"Group '{g.name}' has {len(g.wells)} well(s)."
                )
                return

    try:
        threshold = float(app._stats_active_threshold())
    except Exception:
        threshold = float(getattr(app, "_threshold", 0.0))
    try:
        val_col = app._stats_active_val_col()
    except Exception:
        val_col = getattr(app, "_active_val_col", "")
    try:
        statistic = app._stats_active_statistic()
    except Exception:
        statistic = "mean"
    channel_lbl = _channel_label_for_val_col(val_col)
    stat_lbl = _STAT_LABELS.get(statistic, statistic)

    group_vals: List[Tuple[str, List[float]]] = []
    for g in groups:
        if is_ks:
            vals = collect_group_per_cell_values(
                app, g, target_t, val_col=val_col, threshold=threshold,
            )
            empty_msg = (
                f"Group '{g.name}' has no per-cell {channel_lbl} data "
                f"at t={tp_str} h above threshold ({threshold:.2f})."
            )
        else:
            vals = collect_group_values_fn(g, target_t)
            n_wells = len([w for w in g.wells if w in app._well_paths])
            if n_wells == 1:
                empty_msg = (
                    f"Group '{g.name}' (1 well, FOV-aggregated) has no "
                    f"{channel_lbl} samples at t={tp_str} h "
                    f"(threshold {threshold:.2f})."
                )
            else:
                empty_msg = (
                    f"Group '{g.name}' has no {channel_lbl} per-well "
                    f"samples at t={tp_str} h (threshold {threshold:.2f})."
                )
        if not vals:
            app._stats_write_result(empty_msg)
            return
        group_vals.append((g.name, vals))

    try:
        import scipy.stats as _st
    except ImportError:
        app._stats_write_result("scipy is required.\nInstall with: pip install scipy")
        return

    sample_units = (
        "per-cell values"
        if is_ks
        else ("per-FOV samples" if any(len([w for w in g.wells if w in app._well_paths]) == 1 for g in groups) else "per-well samples")
    )
    header_lines: List[str] = [
        f"Test:       {test}",
        f"Channel:    {channel_lbl}",
        f"Statistic:  {stat_lbl}" if not is_ks else "Statistic:  per-cell distribution",
        f"Threshold:  {threshold:.2f}",
        f"Timepoint:  {tp_str} h",
        f"Samples:    {sample_units}",
        "",
    ]
    lines: List[str] = list(header_lines)
    for name_a, vals_a in group_vals:
        if not vals_a:
            continue
        sv = sorted(vals_a)
        med = sv[len(sv) // 2]
        try:
            sd_val = _pystats.stdev(vals_a) if len(vals_a) > 1 else 0.0
        except _pystats.StatisticsError:
            sd_val = 0.0
        lines.append(
            f"{name_a}:  n={len(vals_a)}  "
            f"mean={sum(vals_a)/len(vals_a):.4g}  "
            f"median={med:.4g}  "
            f"sd={sd_val:.4g}"
        )
    lines.append("")

    pairs = [(group_vals[i], group_vals[j]) for i in range(len(group_vals)) for j in range(i + 1, len(group_vals))]
    for (name_a, vals_a), (name_b, vals_b) in pairs:
        lines.append(f"── {name_a}  vs  {name_b} ──")
        try:
            if test.startswith("t-test"):
                res = _st.ttest_ind(vals_a, vals_b, equal_var=False)
                stat_name = "t"
            elif test.startswith("Wilcoxon"):
                res = _st.ranksums(vals_a, vals_b)
                stat_name = "W"
            elif test.startswith("Mann"):
                res = _st.mannwhitneyu(vals_a, vals_b, alternative="two-sided")
                stat_name = "U"
            elif is_ks:
                res = _st.ks_2samp(vals_a, vals_b)
                stat_name = "D"
            else:
                lines.append("Unknown test.")
                continue
            p = res.pvalue
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            lines.append(f"  {stat_name} = {res.statistic:.4f}   p = {p:.4g}   {sig}")
        except Exception as exc:
            lines.append(f"  Error: {exc}")
        lines.append("")

    app._stats_write_result("\n".join(lines))

    if is_ks:
        draw_ks_cdf_fn(group_vals, tp_str)
        app._stats_fig_frame.setVisible(True)
    else:
        app._stats_fig_frame.setVisible(False)
