"""Statistics-tab computation helpers extracted from well_viewer3."""

from __future__ import annotations

import tkinter as tk
from typing import List, Tuple


def collect_group_values(app, grp, target_t: float) -> List[float]:
    """Return per-cell fluor values above threshold for a group at target_t."""
    threshold = app._threshold
    vals: List[float] = []
    for lbl in grp.wells:
        if lbl not in app._well_paths:
            continue
        for row in app._get_rows(lbl):
            raw = row.get("timepoint_hours")
            try:
                t = float(raw)
            except (TypeError, ValueError):
                continue
            if abs(t - target_t) > 1e-6:
                continue
            try:
                v = float(row[app._active_val_col])
            except (KeyError, ValueError, TypeError):
                continue
            if v > threshold:
                vals.append(v)
    return vals


def draw_ks_cdf(app, group_vals: List[Tuple[str, List[float]]], tp_str: str, well_colors: list[str]) -> None:
    """Draw empirical CDFs for the two KS-test groups."""
    ax = app._stats_ax
    ax.cla()
    colors = [well_colors[0], well_colors[1]]
    for (name, vals), color in zip(group_vals, colors):
        sv = sorted(vals)
        n = len(sv)
        xs = [sv[0]] + sv + [sv[-1]]
        ys = [0.0] + [(i + 1) / n for i in range(n)] + [1.0]
        ax.step(xs, ys, where="post", label=name, color=color, linewidth=1.5)
    ax.set_xlabel(f"{app._active_channel.upper()} mean intensity", fontsize=8)
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
    tp_str = app._stats_tp_var.get()
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

    test = app._stats_test_var.get()
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

    group_vals: List[Tuple[str, List[float]]] = []
    for g in groups:
        vals = collect_group_values_fn(g, target_t)
        if not vals:
            app._stats_write_result(
                f"Group '{g.name}' has no data at t={tp_str} h "
                f"above threshold ({app._threshold:.1f})."
            )
            return
        group_vals.append((g.name, vals))

    try:
        import scipy.stats as _st
    except ImportError:
        app._stats_write_result("scipy is required for statistical tests.\nInstall with: pip install scipy")
        return

    lines: List[str] = [f"Test: {test}", f"Timepoint: {tp_str} h   Threshold: {app._threshold:.1f}\n"]
    for name_a, vals_a in group_vals:
        lines.append(
            f"{name_a}:  n={len(vals_a)}  "
            f"mean={sum(vals_a)/len(vals_a):.2f}  "
            f"median={sorted(vals_a)[len(vals_a)//2]:.2f}"
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
        app._stats_fig_frame.pack(fill=tk.X, padx=12, pady=(6, 0), before=app._stats_result_text.master)
    else:
        app._stats_fig_frame.pack_forget()
