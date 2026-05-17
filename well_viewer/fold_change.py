"""Fold-change normalization helpers for the Bar and Line plot tabs.

Two independent modes are supported and may be combined:

1. ``vs control`` — every bar / curve is divided by the control well's
   (or replicate-set's) mean at the same timepoint.
2. ``vs t0``     — every bar / curve is divided by its own value at the
   earliest available timepoint (each member's own baseline).

The helpers operate on aggregation-point ("AggPoint") tuples produced by
``aggregate_with_threshold_df`` / ``_aggregate_well`` / ``_aggregate_group``:

    (t, mean, spread, frac, n_above, n_total,
     frac_spread?, n_above_pf_mean?, n_above_pf_spread?)

Only ``mean`` and its ``spread`` field are rescaled; fractions, counts and
per-FOV spreads of counts are left untouched (they're not interpretable as
fold-change). The transform returns new tuples with the same arity.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


CONTROL_NONE = ""


def _safe_div(numer: float, denom: float) -> float:
    if denom == 0 or not math.isfinite(denom):
        return float("nan")
    return numer / denom


def _scale_pt(pt: tuple, factor: float) -> tuple:
    """Return a copy of *pt* with mean & spread scaled by ``1/factor``."""
    if factor == 0 or not math.isfinite(factor):
        scaled_mean = float("nan")
        scaled_spread = 0.0
    else:
        m = pt[1]
        s = pt[2]
        scaled_mean = m / factor if isinstance(m, (int, float)) and math.isfinite(m) else float("nan")
        scaled_spread = (s / factor) if isinstance(s, (int, float)) and math.isfinite(s) else 0.0
    new = list(pt)
    new[1] = scaled_mean
    new[2] = scaled_spread
    return tuple(new)


def pts_to_mean_by_t(pts) -> Dict[float, float]:
    """Build a ``{t: mean}`` dict from an AggPoint list, skipping NaN means."""
    out: Dict[float, float] = {}
    for pt in pts or ():
        t = float(pt[0])
        m = pt[1]
        if isinstance(m, (int, float)) and math.isfinite(m):
            out[t] = float(m)
    return out


def _match_control_mean(t: float, control_means: Dict[float, float],
                        tol: float = 1e-6) -> Optional[float]:
    """Resolve the control mean at timepoint *t* (tolerant match)."""
    if not control_means:
        return None
    if t in control_means:
        return control_means[t]
    for ct, cm in control_means.items():
        if abs(ct - t) < tol:
            return cm
    return None


def normalize_pts(
    pts,
    *,
    control_means: Optional[Dict[float, float]] = None,
    use_t0: bool = False,
) -> list:
    """Apply optional vs-control and/or vs-t0 normalization to AggPoint list.

    *control_means* — when supplied, divides each point's mean by the control's
    mean at the matching timepoint. Points with no matching control sample
    produce NaN means (and zeroed spreads).

    *use_t0* — when True, finds the member's earliest finite mean and divides
    every point by it after the control step. The earliest point itself
    becomes 1.0 by construction.
    """
    if not pts:
        return []

    # Step 1: control normalization.
    if control_means:
        stage1: list = []
        for pt in pts:
            t = float(pt[0])
            cm = _match_control_mean(t, control_means)
            if cm is None:
                # No control sample at this t — drop mean to NaN.
                new = list(pt)
                new[1] = float("nan")
                new[2] = 0.0
                stage1.append(tuple(new))
            else:
                stage1.append(_scale_pt(pt, cm))
    else:
        stage1 = list(pts)

    # Step 2: t0 normalization (uses post-control values).
    if use_t0:
        baseline = None
        for pt in sorted(stage1, key=lambda p: p[0]):
            m = pt[1]
            if isinstance(m, (int, float)) and math.isfinite(m) and m != 0:
                baseline = float(m)
                break
        if baseline is None:
            return stage1
        return [_scale_pt(pt, baseline) for pt in stage1]

    return stage1


# ── State accessors / app integration ───────────────────────────────────────

def fold_change_state(app) -> Tuple[bool, str, bool]:
    """Return the active ``(vs_control_on, control_label, vs_t0_on)`` triple.

    Used by both the on-screen plot tabs and the per-tab CSV exporter so the
    plot and the export stay in sync.
    """
    return (
        bool(getattr(app, "_fc_vs_control_on", False)),
        str(getattr(app, "_fc_control_label", "") or ""),
        bool(getattr(app, "_fc_vs_t0_on", False)),
    )


def is_active(app) -> bool:
    vs_ctrl, _, vs_t0 = fold_change_state(app)
    return vs_ctrl or vs_t0


def fold_change_suffix(vs_control_on: bool, vs_t0_on: bool,
                       control_label: str = "") -> str:
    """Compact " (fold-change …)" label fragment for axis titles."""
    parts: List[str] = []
    if vs_control_on:
        parts.append(f"vs {control_label}" if control_label else "vs control")
    if vs_t0_on:
        parts.append("vs t0")
    if not parts:
        return ""
    return "  (fold change " + ", ".join(parts) + ")"


# ── Control-series helpers ──────────────────────────────────────────────────

def resolve_control_wells(app, control_label: str) -> List[str]:
    """Translate a control selection string into a list of loaded well tokens.

    The control may identify either a ReplicateSet (by name, taking precedence
    when there's a name clash) or a single well token. Unknown / empty
    selections return an empty list so callers can short-circuit.
    """
    label = str(control_label or "").strip()
    if not label:
        return []
    for s in (getattr(app, "_selections", []) or []):
        if s.get("name") == label:
            wells = [w for w in (s.get("wells") or []) if w in app._well_paths]
            if wells:
                return wells
    if label in (getattr(app, "_well_paths", None) or {}):
        return [label]
    return []


def control_pts_for_line(app, control_label: str, *, threshold: float,
                         val_col: str, cell_area_threshold: float,
                         fluor_gates) -> list:
    """Aggregate the control selection as a single pooled series.

    Used by the line-plot path where we want a control mean at every
    timepoint the data exposes. Returns an AggPoint list (or [] if the
    control is unresolved).
    """
    wells = resolve_control_wells(app, control_label)
    if not wells:
        return []
    return app._aggregate_group(
        wells, threshold=threshold, use_sem=False,
        val_col=val_col,
        cell_area_threshold=cell_area_threshold,
        fluor_gates=fluor_gates,
    )


def control_mean_at(app, control_label: str, target_t: float, *,
                    threshold: float, val_col: str,
                    cell_area_threshold: float, fluor_gates) -> Optional[float]:
    """Return the control's pooled mean at *target_t* (or None)."""
    pts = control_pts_for_line(
        app, control_label, threshold=threshold, val_col=val_col,
        cell_area_threshold=cell_area_threshold, fluor_gates=fluor_gates,
    )
    means = pts_to_mean_by_t(pts)
    return _match_control_mean(target_t, means)


# ── Bar-plot scaling ────────────────────────────────────────────────────────

def scale_bar_value(
    mean: float,
    spread: float,
    *,
    control_mean: Optional[float] = None,
    t0_mean: Optional[float] = None,
) -> Tuple[float, float]:
    """Apply control and/or t0 normalization to a single (mean, spread) pair.

    Both denominators are optional; missing denominators are treated as 1.0.
    Returns ``(scaled_mean, scaled_spread)`` with NaN propagation when any
    factor is non-finite or zero.
    """
    m, s = mean, spread
    if control_mean is not None:
        if not math.isfinite(control_mean) or control_mean == 0:
            return float("nan"), 0.0
        m = m / control_mean if math.isfinite(m) else float("nan")
        s = s / control_mean if math.isfinite(s) else 0.0
    if t0_mean is not None:
        if not math.isfinite(t0_mean) or t0_mean == 0:
            return float("nan"), 0.0
        m = m / t0_mean if math.isfinite(m) else float("nan")
        s = s / t0_mean if math.isfinite(s) else 0.0
    return float(m) if math.isfinite(m) else float("nan"), float(s) if math.isfinite(s) else 0.0


def first_tp_value(pts) -> Optional[float]:
    """Return the mean of the earliest finite-mean AggPoint, or None."""
    if not pts:
        return None
    for pt in sorted(pts, key=lambda p: p[0]):
        m = pt[1]
        if isinstance(m, (int, float)) and math.isfinite(m):
            return float(m)
    return None
