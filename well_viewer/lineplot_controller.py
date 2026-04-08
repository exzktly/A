"""Line-graph rendering helpers extracted from well_viewer3."""

from __future__ import annotations

import math


NO_SELECTION_MSG = "No wells or well groups selected.\nSelect wells on the left panel or define groups to plot."


def redraw_line_plots(
    app,
    *,
    apply_ax_style,
    aggregate_with_threshold,
    all_fluor_values,
    all_fluor_values_filtered,
    plot_bg: str,
    plot_spn: str,
    txt_pri: str,
    txt_mut: str,
    warn: str,
    well_colors: list[str],
    metric_label: str = "Intensity",
) -> None:
    """Redraw the line/fraction/CDF panel set for the active app state."""
    for ax in (app._line_ax_mean, app._line_ax_frac, app._line_ax_cdf):
        ax.cla()

    use_sem = app._use_sem.get()
    band_lbl = "SEM" if use_sem else "SD"
    threshold = app._get_thresh_frac_on(app._active_channel)
    selected = app._selected_labels()
    legend_kw = dict(fontsize=7, framealpha=0.9, facecolor=plot_bg, edgecolor=plot_spn, labelcolor=txt_pri)

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
    if not selected and not active_rsets:
        for ax in (app._line_ax_mean, app._line_ax_frac, app._line_ax_cdf):
            ax.text(0.5, 0.5, NO_SELECTION_MSG, transform=ax.transAxes, ha="center", va="center", color=txt_mut, fontsize=10)
            ax.set_axis_off()
        app._line_canvas.draw_idle()
        app._set_status("No wells selected.")
        return

    any_ts = any_cdf = False
    if active_rsets:
        for idx, rset in enumerate(active_rsets):
            color = well_colors[idx % len(well_colors)]
            valid_wells = [w for w in rset.wells if w in app._well_paths]
            all_tps: set = set()
            all_fluor_vals_rset = []
            cell_area_threshold = app._get_cell_area_threshold()
            fluor_gates = app._get_all_fluor_gates()
            for lbl in valid_wells:
                rows = app._get_rows(lbl)
                for t, *_ in aggregate_with_threshold(rows, threshold, use_sem=False, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates):
                    all_tps.add(t)
                all_fluor_vals_rset.extend(all_fluor_values_filtered(rows, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates))
            agg_times, agg_means, agg_errs, agg_fracs = [], [], [], []
            for t in sorted(all_tps):
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
    else:
        cell_area_threshold = app._get_cell_area_threshold()
        fluor_gates = app._get_all_fluor_gates()
        for i, label in enumerate(selected):
            color = well_colors[i % len(well_colors)]
            rows = app._get_rows(label)
            disp = app._well_display_label(label)
            pts = aggregate_with_threshold(rows, threshold, use_sem=use_sem, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates)
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
            vals = sorted(all_fluor_values_filtered(rows, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates))
            if vals:
                n = len(vals)
                app._line_ax_cdf.plot(vals, [(k + 1) / n for k in range(n)], color=color, lw=1.8, label=f"{disp} (n={n:,})", zorder=3)
                any_cdf = True

    if any_ts:
        app._line_ax_mean.axhline(threshold, color=warn, lw=1.0, ls="--", alpha=0.8, zorder=1)
        leg_mean = app._line_ax_mean.legend(**legend_kw)
        leg_frac = app._line_ax_frac.legend(**legend_kw)
        leg_mean.set_draggable(True)
        leg_frac.set_draggable(True)
        leg_mean.set_visible(app._legend_visible["mean"])
        leg_frac.set_visible(app._legend_visible["frac"])
    if any_cdf:
        app._line_ax_cdf.axvline(threshold, color=warn, lw=1.2, ls="--", label=f"threshold={threshold:.2f}", zorder=4, picker=8)
        try:
            cdf_lo = float(app._cdf_xmin_var.get())
        except (ValueError, AttributeError):
            cdf_lo = 0.0
        try:
            cdf_hi = float(app._cdf_xmax_var.get())
        except (ValueError, AttributeError):
            cdf_hi = 300.0
        if cdf_hi <= cdf_lo:
            cdf_hi = cdf_lo + 1.0
        app._line_ax_cdf.axvspan(threshold, cdf_hi, alpha=0.05, color=warn, zorder=1)
        leg_cdf = app._line_ax_cdf.legend(**legend_kw)
        leg_cdf.set_draggable(True)
        leg_cdf.set_visible(app._legend_visible["cdf"])
        app._line_ax_cdf.set_xlim(cdf_lo, cdf_hi)
    else:
        app._line_ax_cdf.text(0.5, 0.5, f"No {app._active_channel.upper()} data found.", transform=app._line_ax_cdf.transAxes, ha="center", va="center", color=txt_mut, fontsize=10)

    if active_rsets:
        n_wells = sum(sum(1 for w in r.wells if w in app._well_paths) for r in active_rsets)
        app._set_status(f"{len(active_rsets)} replicate set(s)  ·  {n_wells} well(s)  |  threshold={threshold:.2f}  |  band={band_lbl}")
    else:
        n_total = sum(len(app._get_rows(l)) for l in selected)
        app._set_status(f"{len(selected)} well(s)  |  {n_total:,} nuclei  |  threshold={threshold:.2f}  |  band={band_lbl}")

    app._line_canvas.draw_idle()
