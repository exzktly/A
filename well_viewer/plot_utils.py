"""Shared plotting/statistics helpers for viewer modules."""

from __future__ import annotations

import math
import statistics

from ui.theme.styles import get_color


TXT_PRI = get_color("TXT_PRI")
TXT_MUT = get_color("TXT_MUT")
PLOT_SPN = get_color("PLOT_SPN")


def all_fluor_values(rows: list[dict], *, val_col: str = "gfp_mean_intensity") -> list[float]:
    vals: list[float] = []
    for r in rows:
        try:
            v = float(r.get(val_col, "nan"))
        except Exception:
            continue
        if v == v:
            vals.append(v)
    return vals


def aggregate_with_threshold(
    rows: list[dict],
    threshold: float,
    *,
    use_sem: bool = False,
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: dict[str, tuple[float | None, float | None]] | None = None,
) -> list[tuple[float, float, float, float, int, int]]:
    by_t: dict[float, list[float]] = {}
    for r in rows:
        try:
            area = float(r.get("cell_area_px", r.get("area_px", "nan")))
            if (area != area) or area <= float(cell_area_threshold):
                continue
        except Exception:
            continue
        blocked = False
        if fluor_gates:
            for ch, (lo, hi) in fluor_gates.items():
                try:
                    gv = float(r.get(f"{ch}_mean_intensity", "nan"))
                except Exception:
                    blocked = True
                    break
                if gv != gv:
                    blocked = True
                    break
                if lo is not None and gv < float(lo):
                    blocked = True
                    break
                if hi is not None and gv > float(hi):
                    blocked = True
                    break
        if blocked:
            continue
        try:
            t = float(r.get("timepoint_hours", r.get("time_s", "nan")))
            v = float(r.get(val_col, "nan"))
        except Exception:
            continue
        if (t != t) or (v != v):
            continue
        by_t.setdefault(t, []).append(v)

    out: list[tuple[float, float, float, float, int, int]] = []
    for t in sorted(by_t):
        vals = by_t[t]
        n_total = len(vals)
        if n_total == 0:
            continue
        mean_v = sum(vals) / n_total
        if n_total > 1:
            sd = statistics.pstdev(vals)
            err = sd / math.sqrt(n_total) if use_sem else sd
        else:
            err = 0.0
        n_above = sum(1 for v in vals if v > threshold)
        frac = n_above / n_total
        out.append((t, mean_v, err, frac, n_above, n_total))
    return out


def apply_ax_style(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=10, color=TXT_PRI)
    ax.set_ylabel(ylabel, fontsize=9, color=TXT_PRI)
    ax.tick_params(colors=TXT_MUT, labelsize=8)
    for side in ("left", "right", "top", "bottom"):
        ax.spines[side].set_color(PLOT_SPN)
    ax.grid(True, alpha=0.2)
