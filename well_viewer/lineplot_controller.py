"""Line-graph rendering helpers extracted from well_viewer3."""

from __future__ import annotations

import math


NO_SELECTION_MSG = "No wells or well groups selected.\nSelect wells on the left panel or define groups to plot."
NO_DATA_MSG = "Load a directory.\nUse the Open button at the top-right (⌘O) to pick a folder."


def _apply_order(items, saved_order, key):
    """Reorder ``items`` so entries matching ``saved_order`` come first.

    Items whose ``key(item)`` appears in ``saved_order`` are emitted in the
    saved order; the remainder follow in their natural (input) order. An empty
    or missing saved_order is a no-op (returns items unchanged).
    """
    if not saved_order:
        return list(items)
    items = list(items)
    by_key: dict[str, list] = {}
    natural_order: list = []
    for it in items:
        try:
            k = str(key(it))
        except Exception:
            k = ""
        by_key.setdefault(k, []).append(it)
        natural_order.append(it)
    seen_objs: set = set()
    out: list = []
    for k in saved_order:
        bucket = by_key.get(str(k))
        if not bucket:
            continue
        for it in bucket:
            out.append(it)
            seen_objs.add(id(it))
    for it in natural_order:
        if id(it) not in seen_objs:
            out.append(it)
    return out


def redraw_line_plots(
    app,
    *,
    apply_ax_style,
    all_fluor_values,
    all_fluor_values_filtered,
    warn: str,
    metric_label: str = "Intensity",
) -> None:
    """Redraw the line/fraction/CDF panel set for the active app state."""
    for ax in (app._line_ax_mean, app._line_ax_frac, app._line_ax_cdf):
        ax.cla()

    use_sem = app._use_sem
    band_lbl = "SEM" if use_sem else "SD"
    threshold = app._get_thresh_frac_on(app._active_channel)
    selected = app._selected_labels()
    # Theme-aware chrome colors (track the active PlotCard's Publication/Screen
    # state) — the renderer's *trace* colours stay rank-based.
    from well_viewer.plot_style import tokens_for as _tokens_for_ax
    _bg, _title_fg, _muted_fg, _grid, _spine = _tokens_for_ax(app._line_ax_mean)
    legend_kw = dict(fontsize=7, framealpha=0.9, facecolor=_bg, edgecolor=_spine, labelcolor=_title_fg)

    _ch = app._active_channel.upper()
    apply_ax_style(app._line_ax_mean, f"Mean {_ch} {metric_label} (above threshold) ± {band_lbl}", f"Mean {metric_label}")
    apply_ax_style(app._line_ax_frac, "Fraction of Cells Above Threshold", "Fraction")
    cdf_lbl = (f"{_ch} {metric_label} CDF (all wells per replicate set)" if app._rep_sets_active() else f"{_ch} {metric_label} CDF (all selected wells)")
    apply_ax_style(app._line_ax_cdf, cdf_lbl, "Cumulative fraction")
    app._line_ax_frac.set_xlabel("Time (hours)", fontsize=8, labelpad=5)
    app._line_ax_frac.set_ylim(-0.05, 1.05)
    app._line_ax_cdf.set_xlabel(f"{_ch} {metric_label}", fontsize=8, labelpad=5)
    app._line_ax_cdf.set_ylim(-0.02, 1.05)

    active_rsets = app._rep_sets_active()
    has_data = bool(getattr(app, "_well_paths", None))
    # Empty-state warning needs to honour Screen mode so the text isn't
    # painted against a default white matplotlib figure when the rest of
    # the app is dark. Force the figure + axes facecolor to the theme bg
    # before drawing the message.
    if not has_data:
        try:
            app._line_fig.set_facecolor(_bg)
        except Exception:
            pass
        for ax in (app._line_ax_mean, app._line_ax_frac, app._line_ax_cdf):
            ax.set_title("")
            ax.cla()
            ax.set_facecolor(_bg)
            ax.text(0.5, 0.5, NO_DATA_MSG, transform=ax.transAxes,
                    ha="center", va="center", color=_muted_fg, fontsize=10)
            ax.set_axis_off()
        app._line_canvas.draw_idle()
        app._set_status("No data loaded.")
        return
    if not selected and not active_rsets:
        try:
            app._line_fig.set_facecolor(_bg)
        except Exception:
            pass
        for ax in (app._line_ax_mean, app._line_ax_frac, app._line_ax_cdf):
            ax.set_title("")
            ax.set_facecolor(_bg)
            ax.text(0.5, 0.5, NO_SELECTION_MSG, transform=ax.transAxes, ha="center", va="center", color=_muted_fg, fontsize=10)
            ax.set_axis_off()
        app._line_canvas.draw_idle()
        app._set_status("No wells selected.")
        return

    any_ts = any_cdf = False
    rep_per_fov = app._use_fov_spread_active() if active_rsets else False
    if active_rsets:
        ordered_rsets = _apply_order(
            active_rsets,
            list(getattr(app, "_line_order_rsets", []) or []),
            key=lambda r: getattr(r, "name", ""),
        )
        for idx, rset in enumerate(ordered_rsets):
            # decision #1: line-plot trace colour = the rep-set's well-position
            # rank colour, so it matches the sidebar plate and the bar plot.
            color = app._rank_color_rset(rset)
            valid_wells = [w for w in rset.wells if w in app._well_paths]
            all_tps: set = set()
            all_fluor_vals_rset = []
            cell_area_threshold = app._get_cell_area_threshold()
            fluor_gates = app._get_all_fluor_gates()
            for lbl in valid_wells:
                rows = app._get_rows(lbl)
                for t, *_ in app._aggregate_well(lbl, threshold=threshold, use_sem=False, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates):
                    all_tps.add(t)
                all_fluor_vals_rset.extend(all_fluor_values_filtered(rows, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates, ratios=getattr(app, "_ratio_index", None)))
            agg_times, agg_means, agg_errs, agg_fracs = [], [], [], []
            for t in sorted(all_tps):
                if rep_per_fov:
                    gm, gerr, gf, _, _, _ = app._compute_rep_per_fov_stats(rset, t, threshold, use_sem)
                else:
                    gm, gerr, gf, _ = app._compute_rep_stats(rset, t, threshold, use_sem)
                if not math.isnan(gm):
                    agg_times.append(t)
                    agg_means.append(gm)
                    agg_errs.append(gerr)
                    agg_fracs.append(gf)
            n_wells = len(valid_wells)
            lbl_str = f"{rset.name} (n={n_wells})" if n_wells != 1 else rset.name
            if agg_times:
                app._line_ax_mean.plot(agg_times, agg_means, color=color, lw=2, marker="o", markersize=4, label=lbl_str, zorder=3)
                app._line_ax_mean.fill_between(agg_times, [m - e for m, e in zip(agg_means, agg_errs)], [m + e for m, e in zip(agg_means, agg_errs)], color=color, alpha=0.15, zorder=2)
                vf = [(t, f) for t, f in zip(agg_times, agg_fracs) if not math.isnan(f)]
                if vf:
                    vt2, vf2 = zip(*vf)
                    app._line_ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s", markersize=3, label=lbl_str, zorder=3)
                    app._line_ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                any_ts = True
            if all_fluor_vals_rset:
                fluor_s = sorted(all_fluor_vals_rset)
                n = len(fluor_s)
                app._line_ax_cdf.plot(fluor_s, [(k + 1) / n for k in range(n)], color=color, lw=1.8, label=f"{lbl_str} (n={n:,})", zorder=3)
                any_cdf = True
        # The earlier "solo wells alongside groups" path (PR 152) was
        # reverted: stale ``_selected_wells`` from before group creation
        # was surfacing as a phantom A01 trace whenever the plate was in
        # passive rep_mode.
    else:
        cell_area_threshold = app._get_cell_area_threshold()
        fluor_gates = app._get_all_fluor_gates()
        per_fov_spread = app._use_fov_spread_active()
        ordered_selected = _apply_order(
            selected,
            list(getattr(app, "_line_order_wells", []) or []),
            key=lambda x: x,
        )
        for i, label in enumerate(ordered_selected):
            color = app._rank_color_well(label)  # decision #1: colour by well-position rank
            rows = app._get_rows(label)
            disp = app._well_display_label(label)
            pts = app._aggregate_well(label, threshold=threshold, use_sem=use_sem, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates, per_fov_spread=per_fov_spread)
            if pts:
                times, means, spreads, fracs, *_ = zip(*pts)
                vm = [(t, m, s) for t, m, s in zip(times, means, spreads) if not math.isnan(m)]
                if vm:
                    vt, vmm, vs = zip(*vm)
                    app._line_ax_mean.plot(vt, vmm, color=color, lw=2, marker="o", markersize=4, label=disp, zorder=3)
                    app._line_ax_mean.fill_between(vt, [m - s for m, s in zip(vmm, vs)], [m + s for m, s in zip(vmm, vs)], color=color, alpha=0.15, zorder=2)
                vf = [(t, f) for t, f in zip(times, fracs) if not math.isnan(f)]
                if vf:
                    vt2, vf2 = zip(*vf)
                    app._line_ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s", markersize=3, label=disp, zorder=3)
                    app._line_ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                any_ts = True
            vals = sorted(all_fluor_values_filtered(rows, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates, ratios=getattr(app, "_ratio_index", None)))
            if vals:
                n = len(vals)
                app._line_ax_cdf.plot(vals, [(k + 1) / n for k in range(n)], color=color, lw=1.8, label=f"{disp} (n={n:,})", zorder=3)
                any_cdf = True

    def _has_labeled(ax) -> bool:
        handles, labels = ax.get_legend_handles_labels()
        return any(lbl and not str(lbl).startswith("_") for lbl in labels)

    if any_ts:
        if _has_labeled(app._line_ax_mean):
            leg_mean = app._line_ax_mean.legend(**legend_kw)
            leg_mean.set_draggable(True)
            leg_mean.set_visible(app._legend_visible["mean"])
        if _has_labeled(app._line_ax_frac):
            leg_frac = app._line_ax_frac.legend(**legend_kw)
            leg_frac.set_draggable(True)
            leg_frac.set_visible(app._legend_visible["frac"])
    if any_cdf:
        app._line_ax_cdf.axvline(threshold, color=warn, lw=1.2, ls="--", label=f"threshold={threshold:.2f}", zorder=4, picker=8)
        try:
            cdf_lo = float(app._cdf_xmin_edit.text())
        except (ValueError, AttributeError):
            cdf_lo = 0.0
        try:
            cdf_hi = float(app._cdf_xmax_edit.text())
        except (ValueError, AttributeError):
            cdf_hi = 300.0
        if cdf_hi <= cdf_lo:
            cdf_hi = cdf_lo + 1.0
        app._line_ax_cdf.axvspan(threshold, cdf_hi, alpha=0.05, color=warn, zorder=1)
        if _has_labeled(app._line_ax_cdf):
            leg_cdf = app._line_ax_cdf.legend(**legend_kw)
            leg_cdf.set_draggable(True)
            leg_cdf.set_visible(app._legend_visible["cdf"])
        app._line_ax_cdf.set_xlim(cdf_lo, cdf_hi)
    else:
        app._line_ax_cdf.text(0.5, 0.5, f"No {app._active_channel.upper()} data found.", transform=app._line_ax_cdf.transAxes, ha="center", va="center", color=_muted_fg, fontsize=10)

    if active_rsets:
        n_wells = sum(sum(1 for w in r.wells if w in app._well_paths) for r in active_rsets)
        app._set_status(f"{len(active_rsets)} replicate set(s)  ·  {n_wells} well(s)  |  threshold={threshold:.2f}  |  band={band_lbl}")
    else:
        n_total = sum(len(app._get_rows(l)) for l in selected)
        app._set_status(f"{len(selected)} well(s)  |  {n_total:,} nuclei  |  threshold={threshold:.2f}  |  band={band_lbl}")

    app._line_canvas.draw_idle()
