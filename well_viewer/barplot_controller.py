"""Bar-plot group state serialization helpers extracted from well_viewer3."""

from __future__ import annotations

import math
import re
from typing import Callable, List, Optional, Tuple

from .batch_models import BarGroup, ReplicateSet
from . import debug_flags
from . import fold_change as _fc


def _bar_debug(msg: str) -> None:
    """Emit opt-in bar-plot diagnostics for draw-time label debugging."""
    if debug_flags.review_bar_debug_enabled():
        print(f"DEBUG barplot_controller: {msg}")


def bar_groups_to_dict(
    rep_sets: List[ReplicateSet],
    bar_groups: List[BarGroup],
    *,
    extract_well_token: Callable[[str], Optional[str]],
) -> dict:
    rep_list = [{"name": r.name, "wells": list(r.wells)} for r in rep_sets]
    grp_list = []
    for grp in bar_groups:
        grp_list.append(
            {
                "name": grp.name,
                "hidden": grp.hidden,
                "members": [r.name for r in grp.members],
                "solo_wells": list(grp.solo_wells),
            }
        )
    return {"rep_sets": rep_list, "groups": grp_list}


def bar_groups_from_data(data, *, tok_to_label: dict[str, str]) -> Tuple[List[ReplicateSet], List[BarGroup]]:
    def _norm(tok: str) -> str:
        tok = tok.strip().upper()
        m = re.match(r"^([A-H])(\d{1,2})$", tok, re.I)
        return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else tok

    def _valid_tok(raw: str) -> Optional[str]:
        n = _norm(raw)
        return n if n in tok_to_label else None

    rep_sets: List[ReplicateSet] = []
    bar_groups: List[BarGroup] = []

    if not isinstance(data, dict):
        return rep_sets, bar_groups
    for item in data.get("rep_sets", []):
        wells = [t for t in (_valid_tok(x) for x in item.get("wells", [])) if t is not None]
        rep_sets.append(ReplicateSet(item.get("name", "R"), wells))
    rep_by_name = {r.name: r for r in rep_sets}
    for item in data.get("groups", []):
        grp = BarGroup(item.get("name", "Group"), hidden=bool(item.get("hidden", False)))
        for rname in item.get("members", []):
            if rname in rep_by_name:
                grp.members.append(rep_by_name[rname])
        for raw_tok in item.get("solo_wells", []):
            n = _valid_tok(raw_tok)
            if n:
                grp.solo_wells.append(n)
        bar_groups.append(grp)

    return rep_sets, bar_groups


def collect_bar_items(app, target_t: float, *, well_colors) -> tuple:
    """Compute bar items for the active bar-plot mode (rep-set or per-well)."""
    use_sem = app._use_sem
    band_lbl = "SEM" if use_sem else "SD"
    threshold = app._get_thresh_frac_on(app._active_channel)
    active_rsets = app._rep_sets_active()

    # Fold-change normalization (vs control well/group, vs t0, or both).
    # Resolved once here so we don't re-aggregate the control per bar.
    fc_vs_ctrl, fc_ctrl_lbl, fc_vs_t0 = _fc.fold_change_state(app)
    fc_control_mean_at_t = None
    if fc_vs_ctrl and fc_ctrl_lbl:
        fc_control_mean_at_t = _fc.control_mean_at(
            app, fc_ctrl_lbl, target_t,
            threshold=threshold, val_col=app._active_val_col,
            cell_area_threshold=app._get_cell_area_threshold(),
            fluor_gates=app._get_all_fluor_gates(),
        )

    if active_rsets:
        from well_viewer.lineplot_controller import _apply_order as _apply_rs_order
        active_rsets = _apply_rs_order(
            active_rsets,
            list(getattr(app, "_line_order_rsets", []) or []),
            key=lambda r: getattr(r, "name", ""),
        )
        items: list = []
        per_fov_spread = app._use_fov_spread_active()
        for idx, rset in enumerate(active_rsets):
            color = app._rank_color_rset(rset)  # decision #1: colour by well-position rank
            label = app._replicate_display_label(rset)
            if per_fov_spread:
                # Pool every FOV across all wells in the rep set; SD/SEM is
                # across that pooled set of per-FOV means/fractions/counts.
                gm, g_err_m, gf, g_err_f, n_above_pf_mean, n_above_pf_spread = (
                    app._compute_rep_per_fov_stats(rset, target_t, threshold, use_sem)
                )
                n_above_val = float(n_above_pf_mean)
                n_above_err = float(n_above_pf_spread)
            else:
                gm, g_err_m, gf, g_err_f = app._compute_rep_stats(rset, target_t, threshold, use_sem)
                n_above_val = float(app._compute_rep_n_above(rset, target_t))
                n_above_err = 0.0
            t0_mean = None
            if fc_vs_t0:
                t0_mean = _fc.first_tp_value(app._aggregate_group(
                    list(rset.wells), threshold=threshold, use_sem=False,
                    val_col=app._active_val_col,
                    cell_area_threshold=app._get_cell_area_threshold(),
                    fluor_gates=app._get_all_fluor_gates(),
                ))
            if fc_vs_ctrl or fc_vs_t0:
                gm, g_err_m = _fc.scale_bar_value(
                    gm, g_err_m,
                    control_mean=fc_control_mean_at_t if fc_vs_ctrl else None,
                    t0_mean=t0_mean if fc_vs_t0 else None,
                )
            n_above_pair = (
                (n_above_val, n_above_err) if per_fov_spread
                else (int(n_above_val), 0.0)
            )
            items.append((label, gm, g_err_m, gf, g_err_f, not math.isnan(gm), color,
                          n_above_pair[0], n_above_pair[1]))
        return True, items, band_lbl

    from well_viewer.lineplot_controller import _apply_order as _apply_well_order
    bar_selected = sorted(
        (lbl for lbl in app._selected_wells if lbl in app._well_paths),
        key=lambda lbl: app._parse_rc(lbl),
    )
    bar_selected = _apply_well_order(
        bar_selected,
        list(getattr(app, "_line_order_wells", []) or []),
        key=lambda x: x,
    )
    items = []
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    per_fov_spread = app._use_fov_spread_active()
    for label in bar_selected:
        pts = app._aggregate_well(label, threshold=threshold, use_sem=use_sem, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates, per_fov_spread=per_fov_spread)
        # AggPoint: (t, mean, mean_spread, frac, n_above, n_total, frac_spread,
        #            n_above_per_fov_mean, n_above_per_fov_spread).
        # When the Aggregate FOVs toggle is on, the events panel reports
        # mean ± SD/SEM across the per-FOV above-threshold counts so the
        # column stays consistent with the per-FOV stats already shown in
        # rows 1 and 2; otherwise it reports the well's total count with no
        # error bar.
        matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
        if matched:
            pt = matched[0]
            m, s, f = pt[1], pt[2], pt[3]
            n_above_total = int(pt[4])
            fs = float(pt[6]) if len(pt) >= 7 else 0.0
            n_above_pf_mean = float(pt[7]) if len(pt) >= 8 else 0.0
            n_above_pf_spread = float(pt[8]) if len(pt) >= 9 else 0.0
            if fc_vs_ctrl or fc_vs_t0:
                t0_mean = _fc.first_tp_value(pts) if fc_vs_t0 else None
                m, s = _fc.scale_bar_value(
                    m, s,
                    control_mean=fc_control_mean_at_t if fc_vs_ctrl else None,
                    t0_mean=t0_mean if fc_vs_t0 else None,
                )
            has_data = not math.isnan(m)
            if per_fov_spread:
                items.append((label, m, s, f, fs, has_data, n_above_pf_mean, n_above_pf_spread))
            else:
                items.append((label, m, s, f, fs, has_data, float(n_above_total), 0.0))
        else:
            items.append((label, float("nan"), 0.0, float("nan"), 0.0, False, 0.0, 0.0))
    return False, items, band_lbl


def ordered_bar_keys(app) -> list:
    """Return ordered bar keys for current mode, respecting custom drag order."""
    active_rsets = app._rep_sets_active()
    if active_rsets:
        keys = [r.name for r in active_rsets]
    else:
        keys = sorted(
            (lbl for lbl in app._selected_wells if lbl in app._well_paths),
            key=lambda lbl: app._parse_rc(lbl),
        )
    if app._bar_order is None:
        return keys
    ordered = [k for k in app._bar_order if k in keys]
    seen = set(ordered)
    ordered.extend(k for k in keys if k not in seen)
    return ordered


def render_bar_items(
    *,
    ax_mean,
    ax_frac,
    use_groups: bool,
    items: list,
    xlabels: list[str],
    threshold: float,
    well_colors: list[str],
    warn_color: str,
    border_color: str,
    placeholder_color: str,
    disabled_well_color: str,
    err_bar_color: str,
    ax_n=None,
) -> None:
    """Draw mean / fraction / events-above-threshold bar panels.

    When ``ax_n`` is provided, a third panel is populated with the number of
    events above threshold (``n_above``), pulled from the trailing field
    appended by ``collect_bar_items``. Items missing the field render as
    zero bars.
    """
    n = len(items)
    if len(xlabels) != n:
        if use_groups:
            xlabels = [str(display) for _key, display, *_ in items]
        else:
            xlabels = [str(label) for label, *_ in items]
    else:
        xlabels = [str(lbl) for lbl in xlabels]

    if use_groups:
        keys = [str(key) for key, *_ in items]
    else:
        keys = [str(label) for label, *_ in items]
    _bar_debug(
        f"render_bar_items use_groups={use_groups} n={n} keys={keys!r} xlabels={xlabels!r}"
    )

    if use_groups:
        bar_w = min(0.65, 5.0 / max(n, 1))
        for i, item in enumerate(items):
            # Use-groups items: (key, display, gm, g_err_m, gf, g_err_f, has,
            #                    color[, n_above[, n_above_spread]]).
            # The two trailing fields are optional so any caller still
            # emitting the older 8-tuple shape keeps working.
            _key, _display, gm, g_err_m, gf, g_err_f, has, color = item[:8]
            n_above = float(item[8]) if len(item) >= 9 else 0.0
            n_above_spread = float(item[9]) if len(item) >= 10 else 0.0
            if has:
                ax_mean.bar(i, gm, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                if g_err_m > 0:
                    ax_mean.errorbar(i, gm, yerr=g_err_m, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
                if not math.isnan(gf):
                    ax_frac.bar(i, gf, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                    if g_err_f > 0:
                        ax_frac.errorbar(i, gf, yerr=g_err_f, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
                else:
                    ax_frac.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
                if ax_n is not None:
                    if n_above > 0:
                        ax_n.bar(i, n_above, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                        if n_above_spread > 0:
                            ax_n.errorbar(i, n_above, yerr=n_above_spread, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
                    else:
                        ax_n.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
            else:
                for ax in (ax_mean, ax_frac):
                    ax.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
                if ax_n is not None:
                    ax_n.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
    else:
        bar_w = min(0.6, 5.0 / max(n, 1))
        for i, item in enumerate(items):
            # Per-well items are
            #   (label, mean, spread, frac, frac_spread, has_data[, n_above[, n_above_spread]]).
            # n_above is the events-above-threshold value for the third panel;
            # n_above_spread is non-zero only when the Aggregate FOVs toggle is
            # on and the value reflects the per-FOV mean. Both trailing fields
            # are optional so older 5- / 6- / 7-tuple shapes keep working.
            if len(item) >= 8:
                _label, mean, spread, frac, frac_spread, has_data, n_above, n_above_spread = item[:8]
                n_above = float(n_above)
                n_above_spread = float(n_above_spread)
            elif len(item) == 7:
                _label, mean, spread, frac, frac_spread, has_data, n_above = item[:7]
                n_above = float(n_above)
                n_above_spread = 0.0
            elif len(item) == 6:
                _label, mean, spread, frac, frac_spread, has_data = item
                n_above = 0.0
                n_above_spread = 0.0
            else:
                _label, mean, spread, frac, has_data = item
                frac_spread = 0.0
                n_above = 0.0
                n_above_spread = 0.0
            color = well_colors[i % len(well_colors)]
            if has_data and not math.isnan(mean):
                ax_mean.bar(i, mean, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                if spread > 0:
                    ax_mean.errorbar(i, mean, yerr=spread, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
            else:
                ax_mean.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
            if has_data and not math.isnan(frac):
                ax_frac.bar(i, frac, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                if frac_spread > 0:
                    ax_frac.errorbar(i, frac, yerr=frac_spread, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
            else:
                ax_frac.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
            if ax_n is not None:
                if has_data and n_above > 0:
                    ax_n.bar(i, n_above, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                    if n_above_spread > 0:
                        ax_n.errorbar(i, n_above, yerr=n_above_spread, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
                else:
                    ax_n.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)

    ax_frac.axhline(0.5, color=border_color, lw=0.8, ls="--", alpha=0.5, zorder=1)
    # Add threshold context label to fraction axis
    ax_frac.text(0.02, 0.98, f"threshold={threshold:.2f}", transform=ax_frac.transAxes,
                 fontsize=8, va="top", ha="left", color=warn_color, alpha=0.7)

    xs = list(range(n))
    axes_to_label = [ax_mean, ax_frac]
    if ax_n is not None:
        axes_to_label.append(ax_n)
    for ax in axes_to_label:
        ax.set_xticks(xs)
        ax.set_xticklabels(
            xlabels,
            rotation=45 if n > 8 else 0,
            ha="right" if n > 8 else "center",
            fontsize=7,
        )
        ax.set_xlim(-0.6, n - 0.4)
        # Mark categorical x-axis so downstream styling does not reset tick formatters.
        setattr(ax, "_categorical_xaxis", True)
    if ax_n is not None:
        cur_lo, cur_hi = ax_n.get_ylim()
        ax_n.set_ylim(0, max(cur_hi, 1))
        # Default to integer ticks because N is a count of events; in
        # Aggregate-FOVs mode the bar shows a per-FOV mean which can be
        # fractional, so let matplotlib pick auto ticks then.
        try:
            from matplotlib.ticker import MaxNLocator
            ax_n.yaxis.set_major_locator(MaxNLocator(integer=False))
        except ImportError:
            pass


def apply_bar_ylims(app, ax_mean, ax_frac, *, ax_n=None) -> None:
    """Apply user-entered y-limits to the bar panels (linear scale only)."""
    def _parse(edit) -> Optional[float]:
        txt = edit.text().strip() if hasattr(edit, "text") else str(edit).strip()
        if not txt:
            return None
        try:
            return float(txt)
        except ValueError:
            return None

    mean_lo = _parse(app._bar_ylim_mean_lo_edit)
    mean_hi = _parse(app._bar_ylim_mean_hi_edit)
    if mean_lo is not None or mean_hi is not None:
        cur_lo, cur_hi = ax_mean.get_ylim()
        lo = mean_lo if mean_lo is not None else cur_lo
        hi = mean_hi if mean_hi is not None else cur_hi
        if hi > lo:
            ax_mean.set_ylim(lo, hi)

    frac_lo = _parse(app._bar_ylim_frac_lo_edit)
    frac_hi = _parse(app._bar_ylim_frac_hi_edit)
    if frac_lo is not None or frac_hi is not None:
        cur_lo, cur_hi = ax_frac.get_ylim()
        lo = frac_lo if frac_lo is not None else cur_lo
        hi = frac_hi if frac_hi is not None else cur_hi
        if hi > lo:
            ax_frac.set_ylim(lo, hi)


# ── Drag-and-drop reordering ─────────────────────────────────────────────────
#
# Lightweight helpers that drive the bar drag interaction. The view (matplotlib
# canvas + axes) is owned by ``WellViewerApp``; these helpers only mutate
# ``app._bar_drag_state`` / ``app._bar_order`` and trigger a redraw.

def bar_event_xdata(app, event) -> Optional[float]:
    """Return data-x for a matplotlib MouseEvent over any bar axis."""
    ax = getattr(event, "inaxes", None)
    if ax is not app._ax_bar_mean and ax is not app._ax_bar_frac and ax is not getattr(app, "_ax_bar_n", None):
        return None
    xdata = getattr(event, "xdata", None)
    if xdata is None:
        return None
    return float(xdata)


def bar_idx_at_x(xdata: float, n: int) -> int:
    """Return the bar index nearest to *xdata*, clamped to [0, n-1]."""
    return max(0, min(n - 1, int(round(xdata))))


def bar_reset_order(app) -> None:
    app._bar_order = None
    app._bar_reset_order_btn.setProperty("variant", "toggle_muted")
    app._bar_reset_order_btn.style().unpolish(app._bar_reset_order_btn)
    app._bar_reset_order_btn.style().polish(app._bar_reset_order_btn)
    app._redraw_bars()


def on_bar_drag_press(app, event) -> None:
    """Begin drag — record which bar was pressed."""
    if getattr(event, "button", None) != 1:
        return
    xdata = bar_event_xdata(app, event)
    if xdata is None:
        return
    keys = app._bar_current_keys()
    n = len(keys)
    if n < 2:
        return
    idx = bar_idx_at_x(xdata, n)
    app._bar_drag_state.update(active=True, src_idx=idx, cur_idx=idx)


def on_bar_drag_motion(app, event, *, accent_color: str) -> None:
    """Update drop-target indicator while dragging."""
    ds = app._bar_drag_state
    if not ds["active"]:
        return
    xdata = bar_event_xdata(app, event)
    if xdata is None:
        return
    keys = app._bar_current_keys()
    n = len(keys)
    if n < 2:
        return
    tgt = bar_idx_at_x(xdata, n)
    if tgt == ds["cur_idx"]:
        return
    ds["cur_idx"] = tgt

    for ax in (app._ax_bar_mean, app._ax_bar_frac, getattr(app, "_ax_bar_n", None)):
        if ax is None:
            continue
        for ln in list(ax.lines):
            if getattr(ln, "_bar_drag_guide", False):
                ln.remove()
        if tgt > ds["src_idx"]:
            guide_x = min(tgt + 0.5, n - 0.5)
        else:
            guide_x = max(tgt - 0.5, -0.5)
        ln = ax.axvline(guide_x, color=accent_color, lw=1.5, ls="--",
                        alpha=0.8, zorder=10)
        ln._bar_drag_guide = True
    app._bar_canvas.draw_idle()


def on_bar_drag_release(app, event) -> None:
    """Finalise drop — reorder and redraw."""
    ds = app._bar_drag_state
    if not ds["active"]:
        return
    ds["active"] = False

    for ax in (app._ax_bar_mean, app._ax_bar_frac, getattr(app, "_ax_bar_n", None)):
        if ax is None:
            continue
        for ln in list(ax.lines):
            if getattr(ln, "_bar_drag_guide", False):
                ln.remove()

    src = ds["src_idx"]
    tgt = ds["cur_idx"]
    if src == tgt:
        app._bar_canvas.draw_idle()
        return

    keys = app._bar_current_keys()
    if not (0 <= src < len(keys) and 0 <= tgt < len(keys)):
        app._bar_canvas.draw_idle()
        return

    item = keys.pop(src)
    keys.insert(tgt, item)
    app._bar_order = keys
    app._bar_reset_order_btn.setProperty("variant", "toggle_accent")
    app._bar_reset_order_btn.style().unpolish(app._bar_reset_order_btn)
    app._bar_reset_order_btn.style().polish(app._bar_reset_order_btn)
    app._redraw_bars()
