"""Bar-plot group state serialization helpers extracted from well_viewer3."""

from __future__ import annotations

import math
import re
from typing import Callable, List, Optional, Tuple

from .batch_models import BarGroup, ReplicateSet


def bar_groups_to_dict(
    rep_sets: List[ReplicateSet],
    bar_groups: List[BarGroup],
    *,
    extract_well_token: Callable[[str], Optional[str]],
) -> dict:
    rep_list = [{"name": r.name, "wells": [extract_well_token(w) or w for w in r.wells]} for r in rep_sets]
    grp_list = []
    for grp in bar_groups:
        grp_list.append(
            {
                "name": grp.name,
                "hidden": grp.hidden,
                "members": [r.name for r in grp.members],
                "solo_wells": [extract_well_token(w) or w for w in grp.solo_wells],
            }
        )
    return {"rep_sets": rep_list, "groups": grp_list}


def bar_groups_from_data(data, *, tok_to_label: dict[str, str]) -> Tuple[List[ReplicateSet], List[BarGroup]]:
    def _norm(tok: str) -> str:
        tok = tok.strip().upper()
        m = re.match(r"^([A-H])(\d{1,2})$", tok, re.I)
        return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else tok

    def _tok_label(tok: str) -> Optional[str]:
        return tok_to_label.get(_norm(tok))

    rep_sets: List[ReplicateSet] = []
    bar_groups: List[BarGroup] = []

    if isinstance(data, dict):
        for item in data.get("rep_sets", []):
            wells = [_tok_label(t) for t in item.get("wells", []) if _tok_label(t)]
            rep_sets.append(ReplicateSet(item.get("name", "R"), wells))
        rep_by_name = {r.name: r for r in rep_sets}
        for item in data.get("groups", []):
            grp = BarGroup(item.get("name", "Group"), hidden=bool(item.get("hidden", False)))
            for rname in item.get("members", []):
                if rname in rep_by_name:
                    grp.members.append(rep_by_name[rname])
            for tok in item.get("solo_wells", []):
                lbl = _tok_label(tok)
                if lbl:
                    grp.solo_wells.append(lbl)
            bar_groups.append(grp)
    else:
        for item in (data if isinstance(data, list) else []):
            name = str(item.get("name", "Group"))
            hidden = bool(item.get("hidden", False))
            grp = BarGroup(name, hidden=hidden)
            for rdata in item.get("replicates", []):
                rname = rdata.get("name", "R")
                rwells = [_tok_label(t) for t in rdata.get("wells", []) if _tok_label(t)]
                rset = ReplicateSet(rname, rwells)
                rep_sets.append(rset)
                grp.members.append(rset)
            bar_groups.append(grp)

    return rep_sets, bar_groups


def collect_bar_items(app, target_t: float, *, aggregate_with_threshold, well_colors) -> tuple:
    """Compute bar items for the active bar-plot mode (rep-set or per-well)."""
    use_sem = app._use_sem.get()
    band_lbl = "SEM" if use_sem else "SD"
    threshold = app._get_thresh_frac_on(app._active_channel)
    active_rsets = app._rep_sets_active()

    if active_rsets:
        items: list = []
        for idx, rset in enumerate(active_rsets):
            color = well_colors[idx % len(well_colors)]
            gm, g_err_m, gf, g_err_f = app._compute_rep_stats(rset, target_t, threshold, use_sem)
            n_w = sum(1 for w in rset.wells if w in app._well_paths)
            label = f"{rset.name} (n={n_w})" if n_w != 1 else rset.name
            items.append((label, gm, g_err_m, gf, g_err_f, not math.isnan(gm), color))
        return True, items, band_lbl

    bar_selected = sorted(
        (lbl for lbl in app._selected_wells if lbl in app._well_paths),
        key=lambda lbl: app._parse_rc(lbl),
    )
    items = []
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    for label in bar_selected:
        rows = app._get_rows(label)
        pts = aggregate_with_threshold(rows, threshold, use_sem=use_sem, val_col=app._active_val_col, cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates)
        matched = [(m, s, f) for t, m, s, f, *_ in pts if abs(t - target_t) < 1e-6]
        if matched:
            m, s, f = matched[0]
            items.append((label, m, s, f, True))
        else:
            items.append((label, float("nan"), 0.0, float("nan"), False))
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
) -> None:
    """Draw mean/fraction bar panels from precomputed items."""
    n = len(items)
    if use_groups:
        bar_w = min(0.65, 5.0 / max(n, 1))
        for i, (_key, _display, gm, g_err_m, gf, g_err_f, has, color) in enumerate(items):
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
            else:
                for ax in (ax_mean, ax_frac):
                    ax.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
    else:
        bar_w = min(0.6, 5.0 / max(n, 1))
        for i, (_label, mean, spread, frac, has_data) in enumerate(items):
            color = well_colors[i % len(well_colors)]
            if has_data and not math.isnan(mean):
                ax_mean.bar(i, mean, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
                if spread > 0:
                    ax_mean.errorbar(i, mean, yerr=spread, fmt="none", ecolor=err_bar_color, elinewidth=1.4, capsize=4, zorder=4)
            else:
                ax_mean.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)
            if has_data and not math.isnan(frac):
                ax_frac.bar(i, frac, width=bar_w, color=color, alpha=0.85, zorder=3, linewidth=0)
            else:
                ax_frac.bar(i, 0, width=bar_w, color=placeholder_color, linewidth=1, edgecolor=disabled_well_color, linestyle="--", zorder=3)

    ax_mean.axhline(threshold, color=warn_color, lw=1.0, ls="--", alpha=0.7, zorder=1, label=f"threshold={threshold:.2f}")
    ax_frac.axhline(0.5, color=border_color, lw=0.8, ls="--", alpha=0.5, zorder=1)
    # Add threshold context label to fraction axis
    ax_frac.text(0.02, 0.98, f"threshold={threshold:.2f}", transform=ax_frac.transAxes,
                 fontsize=8, va="top", ha="left", color=warn_color, alpha=0.7)

    xs = list(range(n))
    for ax in (ax_mean, ax_frac):
        ax.set_xticks(xs)
        ax.set_xticklabels(
            xlabels,
            rotation=45 if n > 8 else 0,
            ha="right" if n > 8 else "center",
            fontsize=7,
        )
        ax.set_xlim(-0.6, n - 0.4)


def apply_bar_ylims(app, ax_mean, ax_frac, *, log_scale: bool = False) -> None:
    """Apply user-entered y-limits and optional log scale to bar axes."""
    def _parse(var) -> Optional[float]:
        txt = var.get().strip()
        if not txt:
            return None
        try:
            return float(txt)
        except ValueError:
            return None

    ax_mean.set_yscale("log" if log_scale else "linear")
    mean_lo = _parse(app._bar_ylim_mean_lo)
    mean_hi = _parse(app._bar_ylim_mean_hi)
    if mean_lo is not None or mean_hi is not None:
        cur_lo, cur_hi = ax_mean.get_ylim()
        lo = mean_lo if mean_lo is not None else cur_lo
        hi = mean_hi if mean_hi is not None else cur_hi
        if log_scale:
            lo = max(lo, 1e-9)
            hi = max(hi, lo * 10)
        if hi > lo:
            ax_mean.set_ylim(lo, hi)

    frac_lo = _parse(app._bar_ylim_frac_lo)
    frac_hi = _parse(app._bar_ylim_frac_hi)
    if frac_lo is not None or frac_hi is not None:
        cur_lo, cur_hi = ax_frac.get_ylim()
        lo = frac_lo if frac_lo is not None else cur_lo
        hi = frac_hi if frac_hi is not None else cur_hi
        if hi > lo:
            ax_frac.set_ylim(lo, hi)
