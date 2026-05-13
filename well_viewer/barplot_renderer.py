"""Bar/violin/beeswarm matplotlib drawing.

Extracted from ``WellViewerApp`` so the GUI class no longer owns plot
rendering. Each function takes ``app`` (WellViewerApp) for state access plus
the matplotlib axes to draw into.
"""

from __future__ import annotations

import math
from typing import List, Optional

from ui.theme import (
    BORDER,
    CLR_ERR_BAR,
    CLR_MUTED_DISABLED,
    CLR_PLACEHOLDER,
    WARN,
)

from well_viewer.barplot_controller import (
    apply_bar_ylims as _apply_bar_ylims,
    collect_bar_items as _collect_bar_items,
    ordered_bar_keys as _ordered_bar_keys,
    render_bar_items as _render_bar_items,
)
import numpy as np
import pandas as pd

from well_viewer.data_loading import (
    _beeswarm_jitter,
    df_included_mask,
    extract_well_token as _extract_well_token,
    parse_timepoint_hours,
    resolve_value_series,
)
from well_viewer.plate_layout import WELL_COLORS
from well_viewer.plot_style import apply_ax_style, tokens_for


NO_SELECTION_MSG = (
    "No wells or well groups selected.\n"
    "Select wells on the left panel or define groups to plot."
)


def draw_violin(
    app,
    ax_mean,
    ax_frac,
    wells: List[str],
    colors: List[str],
    xlabels: List[str],
    target_t: float,
    tp_str: str,
    threshold: float,
) -> None:
    """KDE-smoothed distribution per well/group."""
    try:
        from scipy.stats import gaussian_kde
    except ImportError:
        ax_mean.text(0.5, 0.5, "scipy required for violin plot",
                     transform=ax_mean.transAxes, ha="center", va="center",
                     color=tokens_for(ax_mean)[2], fontsize=9)
        return

    n = len(wells)
    slider = getattr(app, "_violin_slider", None)
    bw_raw = float(slider.value()) / 100.0 if slider is not None else 1.0
    bw = max(0.05, bw_raw)
    bar_w = min(0.4, 3.0 / max(n, 1))

    xs_ticks = list(range(n))
    frac_vals: List[float] = []
    ratios = getattr(app, "_ratio_index", None)

    for i, (lbl, color) in enumerate(zip(wells, colors)):
        df = app._get_rows(lbl)
        vals = np.empty(0, dtype=float)
        n_total = n_above = 0
        if df is not None and not df.empty and "timepoint_hours" in df.columns:
            mask = df_included_mask(df).to_numpy(copy=True)
            tp = pd.to_numeric(df["timepoint_hours"], errors="coerce").to_numpy()
            with np.errstate(invalid="ignore"):
                mask &= np.isfinite(tp) & (np.abs(tp - target_t) <= 1e-6)
            v = resolve_value_series(df, app._active_val_col, ratios).to_numpy()
            mask &= np.isfinite(v)
            v_sel = v[mask]
            n_total = int(v_sel.size)
            vals = v_sel[v_sel > threshold]
            n_above = int(vals.size)

        frac_vals.append(n_above / n_total if n_total else float("nan"))

        if vals.size < 3:
            if vals.size:
                ax_mean.scatter([i], [vals[0]], c=color, s=20, zorder=4)
            continue

        arr = vals
        kde = gaussian_kde(arr, bw_method=bw)
        y_min, y_max = float(arr.min()), float(arr.max())
        y_pad = (y_max - y_min) * 0.05
        ys = np.linspace(y_min - y_pad, y_max + y_pad, 200)
        density = kde(ys)
        max_d = density.max()
        if max_d > 0:
            density = density / max_d * bar_w

        ax_mean.fill_betweenx(ys, i - density, i + density,
                              color=color, alpha=0.55, zorder=2)
        ax_mean.plot(i - density, ys, color=color, lw=0.6, alpha=0.7, zorder=3)
        ax_mean.plot(i + density, ys, color=color, lw=0.6, alpha=0.7, zorder=3)

        median = float(np.median(arr))
        ax_mean.hlines(median, i - bar_w * 0.6, i + bar_w * 0.6,
                       colors="white", lw=2.0, zorder=5)
        ax_mean.hlines(median, i - bar_w * 0.6, i + bar_w * 0.6,
                       colors=color, lw=1.2, zorder=6)

    for i, (fv, color) in enumerate(zip(frac_vals, colors)):
        if not math.isnan(fv):
            ax_frac.scatter([i], [fv], c=color, s=30, zorder=3, linewidths=0)
        else:
            ax_frac.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                            marker="x", zorder=3, linewidths=1)

    ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--", alpha=0.7, zorder=1)
    ax_frac.axhline(0.5, color=BORDER, lw=0.8, ls="--", alpha=0.5, zorder=1)
    for ax in (ax_mean, ax_frac):
        ax.set_xticks(xs_ticks)
        ax.set_xticklabels(xlabels,
                           rotation=45 if n > 8 else 0,
                           ha="right" if n > 8 else "center",
                           fontsize=7)
        ax.set_xlim(-0.6, n - 0.4)
    ax_frac.set_ylim(-0.05, 1.05)
    ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
    ax_mean.set_title(
        f"{app._active_channel.upper()} distribution (violin, bw={bw:.2f})  —  t = {tp_str} h",
        color=tokens_for(ax_mean)[1], fontsize=9, fontweight="bold", pad=6)
    ax_frac.set_title(
        f"Fraction above threshold  —  t = {tp_str} h",
        color=tokens_for(ax_frac)[1], fontsize=9, fontweight="bold", pad=6)


def draw_beeswarm(
    app,
    ax_mean,
    ax_frac,
    wells: List[str],
    colors: List[str],
    xlabels: List[str],
    target_t: float,
    tp_str: str,
    threshold: float,
) -> None:
    """One column per well, each cell a jittered point."""
    n = len(wells)
    xs_ticks = list(range(n))
    bar_w = min(0.35, 3.0 / max(n, 1))
    ratios = getattr(app, "_ratio_index", None)

    for i, (lbl, color) in enumerate(zip(wells, colors)):
        df = app._get_rows(lbl)
        cell_vals = np.empty(0, dtype=float)
        frac_val: Optional[float] = None
        if df is not None and not df.empty:
            mask = df_included_mask(df).to_numpy(copy=True)
            if "timepoint_hours" in df.columns:
                tp = pd.to_numeric(df["timepoint_hours"], errors="coerce").to_numpy()
            else:
                tp = np.full(len(df), np.nan)
            need = ~np.isfinite(tp)
            if need.any() and "timepoint" in df.columns:
                fallback = (df.loc[need, "timepoint"].fillna("").astype(str)
                            .map(parse_timepoint_hours))
                tp[need] = fallback.fillna(np.nan).to_numpy(dtype=float)
            with np.errstate(invalid="ignore"):
                mask &= np.isfinite(tp) & (np.abs(tp - target_t) <= 1e-6)
            val = resolve_value_series(df, app._active_val_col, ratios).to_numpy()
            mask &= np.isfinite(val)
            v_sel = val[mask]
            n_total = int(v_sel.size)
            cell_vals = v_sel[v_sel > threshold]
            n_above = int(cell_vals.size)
            if n_total > 0:
                frac_val = n_above / n_total

        if cell_vals.size:
            jx, jy = _beeswarm_jitter(cell_vals.tolist(), x_center=float(i),
                                       max_spread=bar_w)
            ax_mean.scatter(jx, jy, c=color, s=6, alpha=0.55,
                            zorder=3, linewidths=0)
            m = float(cell_vals.mean())
            ax_mean.plot([i - bar_w * 0.6, i + bar_w * 0.6],
                         [m, m], color=color, lw=1.5, zorder=4)
        else:
            ax_mean.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                            marker="x", zorder=3, linewidths=1)

        if frac_val is not None:
            ax_frac.scatter([i], [frac_val], c=color, s=30,
                            zorder=3, linewidths=0)
        else:
            ax_frac.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                            marker="x", zorder=3, linewidths=1)

    ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--",
                    alpha=0.7, zorder=1)
    ax_frac.axhline(0.5, color=BORDER, lw=0.8, ls="--",
                    alpha=0.5, zorder=1)
    for ax in (ax_mean, ax_frac):
        ax.set_xticks(xs_ticks)
        ax.set_xticklabels(xlabels,
                           rotation=45 if n > 8 else 0,
                           ha="right" if n > 8 else "center",
                           fontsize=7)
        ax.set_xlim(-0.6, n - 0.4)
    ax_frac.set_ylim(-0.05, 1.05)
    ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
    ax_mean.set_title(
        f"{app._active_channel.upper()} per cell (above threshold)  —  t = {tp_str} h",
        color=tokens_for(ax_mean)[1], fontsize=9, fontweight="bold", pad=6)
    ax_frac.set_title(
        f"Fraction above threshold  —  t = {tp_str} h",
        color=tokens_for(ax_frac)[1], fontsize=9, fontweight="bold", pad=6)


def draw_grouped_bar_mode(
    app,
    *,
    ax_mean,
    ax_frac,
    ax_n,
    active_rsets,
    target_t: float,
    tp_str: str,
    threshold: float,
    band_lbl: str,
    use_sem: bool,
) -> None:
    """Render the canonical grouped-bar (or per-well) view."""
    use_groups, items, _ = app._collect_bar_items(target_t)
    if use_groups:
        by_key = {r.name: r for r in active_rsets}
        # decision #1: a rep-set's bar is coloured by its lowest well's rank.
        color_by_key = {r.name: app._rank_color_rset(r) for r in active_rsets}
        per_fov_spread = app._use_fov_spread_active()
        ordered = []
        for key in app._bar_current_keys():
            rset = by_key.get(key)
            if not rset:
                continue
            if per_fov_spread:
                gm, g_err_m, gf, g_err_f, n_above_mean, n_above_spread = (
                    app._compute_rep_per_fov_stats(rset, target_t, threshold, use_sem)
                )
                trailing = (float(n_above_mean), float(n_above_spread))
            else:
                gm, g_err_m, gf, g_err_f = app._compute_rep_stats(rset, target_t, threshold, use_sem)
                n_above = app._compute_rep_n_above(rset, target_t)
                trailing = (int(n_above), 0.0)
            base_lbl = app._replicate_display_label(rset)
            display = base_lbl
            ordered.append(
                (
                    rset.name,
                    display,
                    gm,
                    g_err_m,
                    gf,
                    g_err_f,
                    not math.isnan(gm),
                    color_by_key.get(rset.name, WELL_COLORS[0]),
                    trailing[0],
                    trailing[1],
                )
            )
        xlabels = [display for _, display, *_ in ordered]
        draw_items = ordered
    else:
        key_to_item = {item[0]: item for item in items}
        ordered_keys = [k for k in app._bar_current_keys() if k in key_to_item]
        draw_items = [key_to_item[k] for k in ordered_keys]
        xlabels = [app._bar_well_display_label(lbl) for lbl, *_ in draw_items]

    # decision #1: per-well bars are coloured by each well's position rank
    # (group bars carry their own colour in the item tuple already).
    per_well_colors = (WELL_COLORS if use_groups
                       else ([app._rank_color_well(lbl) for lbl, *_ in draw_items] or WELL_COLORS))
    _render_bar_items(
        ax_mean=ax_mean,
        ax_frac=ax_frac,
        ax_n=ax_n,
        use_groups=use_groups,
        items=draw_items,
        xlabels=xlabels,
        threshold=threshold,
        well_colors=per_well_colors,
        warn_color=WARN,
        border_color=BORDER,
        placeholder_color=CLR_PLACEHOLDER,
        disabled_well_color=CLR_MUTED_DISABLED,
        err_bar_color=CLR_ERR_BAR,
    )
    ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
    _ch = app._active_channel.upper()
    ax_mean.set_title(
        f"Mean {_ch} (above threshold) ± {band_lbl}  —  t = {tp_str} h",
        color=tokens_for(ax_mean)[1], fontsize=9, fontweight="bold", pad=6,
    )
    ax_frac.set_title(
        f"Fraction above threshold  —  t = {tp_str} h",
        color=tokens_for(ax_frac)[1], fontsize=9, fontweight="bold", pad=6,
    )
    if ax_n is not None:
        fov_active = app._use_fov_spread_active()
        if fov_active:
            n_title = f"Mean events above threshold per FOV ± {band_lbl}  —  t = {tp_str} h"
            n_ylabel = "N(above)/FOV"
        else:
            n_title = f"Events above threshold (N)  —  t = {tp_str} h"
            n_ylabel = "N(above)"
        ax_n.set_title(
            n_title, color=tokens_for(ax_n)[1], fontsize=9, fontweight="bold", pad=6,
        )
        ax_n.set_ylabel(n_ylabel, fontsize=8, labelpad=5)
    _apply_bar_ylims(app, ax_mean, ax_frac, ax_n=ax_n)
    app._bar_canvas.draw_idle()


def redraw_bars(app) -> None:
    """Top-level bar plot redraw (drives the Bar Plots tab)."""
    if not hasattr(app, "_ax_bar_mean"):
        return
    ax_mean = app._ax_bar_mean
    ax_frac = app._ax_bar_frac
    ax_n = getattr(app, "_ax_bar_n", None)
    ax_mean.cla()
    ax_frac.cla()
    if ax_n is not None:
        ax_n.cla()

    use_sem = app._use_sem
    band_lbl = "SEM" if use_sem else "SD"
    threshold = app._get_thresh_frac_on(app._active_channel)

    active_rsets = app._rep_sets_active()
    bar_selected = app._selected_bar_wells(active_rsets)

    _ch = app._active_channel.upper()
    apply_ax_style(ax_mean,
                   f"Mean {_ch} (above threshold) ± {band_lbl}",
                   f"Mean {_ch}")
    apply_ax_style(ax_frac,
                   "Fraction of Cells Above Threshold",
                   "Fraction")
    if ax_n is not None:
        fov_active = app._use_fov_spread_active()
        if fov_active:
            apply_ax_style(
                ax_n,
                f"Mean events above threshold per FOV ± {band_lbl}",
                "N(above)/FOV",
            )
        else:
            apply_ax_style(ax_n, "Events above threshold (N)", "N(above)")
    ax_frac.set_ylim(-0.05, 1.05)

    if not bar_selected and not active_rsets:
        app._draw_bar_empty_state(ax_mean, ax_frac, NO_SELECTION_MSG, ax_n=ax_n)
        return

    tp_data = app._resolve_bar_timepoint()
    if tp_data is None:
        app._draw_bar_empty_state(ax_mean, ax_frac, "Select a timepoint above", ax_n=ax_n)
        return
    target_t, tp_str = tp_data

    if app._draw_per_cell_bar_mode(
        ax_mean=ax_mean,
        ax_frac=ax_frac,
        ax_n=ax_n,
        active_rsets=active_rsets,
        target_t=target_t,
        tp_str=tp_str,
        threshold=threshold,
    ):
        return
    draw_grouped_bar_mode(
        app,
        ax_mean=ax_mean,
        ax_frac=ax_frac,
        ax_n=ax_n,
        active_rsets=active_rsets,
        target_t=target_t,
        tp_str=tp_str,
        threshold=threshold,
        band_lbl=band_lbl,
        use_sem=use_sem,
    )
    from well_viewer.figure_export_editor import apply_export_style_to_current

    apply_export_style_to_current(app, app._bar_fig, getattr(app, "_bar_canvas", None))
