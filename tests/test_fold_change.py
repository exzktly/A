"""Unit tests for ``well_viewer.fold_change``.

Pure-logic tests — no Qt, no matplotlib. Run with::

    python -m pytest tests/test_fold_change.py -v
"""

from __future__ import annotations

import math

import pytest

from well_viewer import fold_change as fc
from well_viewer.fold_change import (
    _match_control_mean, _TP_REL_TOL,
    build_cell_scaling,
    control_mean_at_for_bar, fold_change_state, fold_change_suffix,
    member_first_tp_value, member_mean_series,
    normalize_pts, pts_to_mean_by_t, resolve_control_wells,
    scale_bar_value, first_tp_value,
)


# ── pts_to_mean_by_t / _match_control_mean ──────────────────────────────────

def test_pts_to_mean_by_t_skips_nan():
    pts = [(0.0, 1.0, 0, 0, 0, 0), (1.0, float("nan"), 0, 0, 0, 0),
           (2.0, 3.0, 0, 0, 0, 0)]
    assert pts_to_mean_by_t(pts) == {0.0: 1.0, 2.0: 3.0}


def test_match_control_mean_exact():
    assert _match_control_mean(1.0, {0.0: 10.0, 1.0: 20.0}) == 20.0


def test_match_control_mean_relative_tolerance_regression():
    # The bar tp combo formats with :.4g so 2/3 parses back as 0.6667.
    # Old absolute 1e-6 tolerance missed this; relative tolerance catches it.
    t_combo = float("0.6667")
    t_data = 2.0 / 3.0
    assert _match_control_mean(t_combo, {t_data: 42.0}) == 42.0


def test_match_control_mean_empty():
    assert _match_control_mean(0.0, {}) is None


def test_match_control_mean_far_miss():
    # Truly mismatched values are still rejected.
    assert _match_control_mean(0.0, {1.0: 5.0}) is None


def test_tp_rel_tol_value():
    # Document the constant — if this changes, downstream behaviour shifts.
    assert _TP_REL_TOL == 1e-3


# ── normalize_pts ───────────────────────────────────────────────────────────

def test_normalize_pts_control_only():
    pts = [(0.0, 100.0, 10.0, 0.5, 5, 10), (1.0, 200.0, 20.0, 0.5, 5, 10)]
    out = normalize_pts(pts, control_means={0.0: 100.0, 1.0: 100.0})
    assert math.isclose(out[0][1], 1.0)
    assert math.isclose(out[1][1], 2.0)
    # Spread divides by the same factor.
    assert math.isclose(out[0][2], 0.1)
    assert math.isclose(out[1][2], 0.2)


def test_normalize_pts_t0_only():
    pts = [(0.0, 50.0, 5.0, 0.5, 5, 10), (1.0, 200.0, 20.0, 0.5, 5, 10)]
    out = normalize_pts(pts, use_t0=True)
    # First finite mean becomes 1.0.
    assert math.isclose(out[0][1], 1.0)
    assert math.isclose(out[1][1], 4.0)


def test_normalize_pts_ddct_stacking():
    """Stacking is ΔΔCt-style: (X/C@t) / (X/C@0), not (X/X@0) / (C/C@0)."""
    pts = [(0.0, 100.0, 0, 0, 0, 0), (1.0, 300.0, 0, 0, 0, 0)]
    ctrl = {0.0: 50.0, 1.0: 100.0}
    out = normalize_pts(pts, control_means=ctrl, use_t0=True)
    # Stage 1: control: 100/50=2.0, 300/100=3.0.
    # Stage 2: t0 baseline = 2.0 → 2/2=1, 3/2=1.5.
    assert math.isclose(out[0][1], 1.0)
    assert math.isclose(out[1][1], 1.5)


def test_normalize_pts_missing_control_drops_to_nan_and_records_miss():
    pts = [(0.0, 100.0, 0, 0, 0, 0), (1.0, 200.0, 0, 0, 0, 0)]
    ctrl = {0.0: 50.0}  # no sample at t=1.0
    misses: set = set()
    out = normalize_pts(pts, control_means=ctrl, miss_sink=misses)
    assert math.isclose(out[0][1], 2.0)
    assert math.isnan(out[1][1])
    assert misses == {1.0}


def test_normalize_pts_empty_input():
    assert normalize_pts([]) == []


# ── scale_bar_value ─────────────────────────────────────────────────────────

def test_scale_bar_value_no_normalization():
    m, s = scale_bar_value(10.0, 1.0)
    assert (m, s) == (10.0, 1.0)


def test_scale_bar_value_control_only():
    m, s = scale_bar_value(10.0, 1.0, control_mean=2.0)
    assert (m, s) == (5.0, 0.5)


def test_scale_bar_value_t0_only():
    m, s = scale_bar_value(10.0, 1.0, t0_mean=5.0)
    assert (m, s) == (2.0, 0.2)


def test_scale_bar_value_both_axes():
    m, s = scale_bar_value(10.0, 1.0, control_mean=2.0, t0_mean=5.0)
    # 10/2 = 5; 5/5 = 1.0
    assert math.isclose(m, 1.0)
    assert math.isclose(s, 0.1)


def test_scale_bar_value_zero_control_yields_nan():
    m, s = scale_bar_value(10.0, 1.0, control_mean=0.0)
    assert math.isnan(m)
    assert s == 0.0


def test_scale_bar_value_zero_t0_yields_nan():
    m, s = scale_bar_value(10.0, 1.0, t0_mean=0.0)
    assert math.isnan(m)


def test_scale_bar_value_nan_mean_propagates():
    m, s = scale_bar_value(float("nan"), 1.0, control_mean=2.0)
    assert math.isnan(m)


# ── first_tp_value ──────────────────────────────────────────────────────────

def test_first_tp_value_returns_earliest_finite():
    pts = [(1.0, 2.0, 0, 0, 0, 0), (0.0, 1.0, 0, 0, 0, 0),
           (2.0, 3.0, 0, 0, 0, 0)]
    assert first_tp_value(pts) == 1.0  # mean at t=0.0


def test_first_tp_value_skips_nan():
    pts = [(0.0, float("nan"), 0, 0, 0, 0), (1.0, 5.0, 0, 0, 0, 0)]
    assert first_tp_value(pts) == 5.0


def test_first_tp_value_empty():
    assert first_tp_value([]) is None


# ── fold_change_state / suffix ──────────────────────────────────────────────

def test_fold_change_state_reads_app(mock_app):
    mock_app.fc_vs_control_on = True
    mock_app.fc_control_label = "CTRL"
    assert fold_change_state(mock_app) == (True, "CTRL", False)


def test_fold_change_suffix_off():
    assert fold_change_suffix(False, False) == ""


def test_fold_change_suffix_control_only():
    assert "vs CTRL" in fold_change_suffix(True, False, "CTRL")


def test_fold_change_suffix_both():
    s = fold_change_suffix(True, True, "CTRL")
    assert "vs CTRL" in s
    assert "vs t0" in s


# ── resolve_control_wells ───────────────────────────────────────────────────

def test_resolve_control_wells_rep_set(mock_app):
    assert resolve_control_wells(mock_app, "CTRL") == ["A01", "A02"]


def test_resolve_control_wells_solo(mock_app):
    assert resolve_control_wells(mock_app, "C01") == ["C01"]


def test_resolve_control_wells_unknown(mock_app):
    assert resolve_control_wells(mock_app, "ZZ99") == []


def test_resolve_control_wells_empty(mock_app):
    assert resolve_control_wells(mock_app, "") == []
    assert resolve_control_wells(mock_app, None) == []


def test_resolve_control_wells_well_suffix_bypasses_repset(mock_app):
    # Pretend a rep-set is named "A01" — same as a well token.
    mock_app.selections.append({"name": "A01", "wells": ["B01"]})
    # Bare "A01" → rep-set (which points at B01)
    assert resolve_control_wells(mock_app, "A01") == ["B01"]
    # Suffixed "A01 (well)" → the actual A01 well
    assert resolve_control_wells(mock_app, "A01 (well)") == ["A01"]


# ── member_mean_series / control_mean_at_for_bar ────────────────────────────

def _kw(threshold=50.0, val_col="gfp", use_sem=True, per_fov_spread=False,
        cell_area_threshold=0.0, fluor_gates=None):
    return dict(threshold=threshold, val_col=val_col, use_sem=use_sem,
                per_fov_spread=per_fov_spread,
                cell_area_threshold=cell_area_threshold,
                fluor_gates=fluor_gates or {})


def test_member_mean_series_repset_uses_mean_of_means(mock_app):
    series = member_mean_series(mock_app, "TREAT", **_kw())
    # Both B01 and B02 have means 100, 200, 400 — mean-of-means is identical.
    assert math.isclose(series[0.0], 100.0)
    assert math.isclose(series[1.0], 200.0)
    assert math.isclose(series[2.0], 400.0)


def test_member_mean_series_solo_well(mock_app):
    series = member_mean_series(mock_app, "C01", **_kw())
    assert math.isclose(series[0.0], 50.0)
    assert math.isclose(series[2.0], 200.0)


def test_member_mean_series_unknown_label(mock_app):
    assert member_mean_series(mock_app, "ZZ99", **_kw()) == {}


def test_control_mean_at_for_bar_repset(mock_app):
    v = control_mean_at_for_bar(mock_app, "CTRL", 1.0, **_kw())
    assert math.isclose(v, 100.0)


def test_control_mean_at_for_bar_missing_tp(mock_app):
    # Target tp not in any well of the control rep-set.
    v = control_mean_at_for_bar(mock_app, "CTRL", 99.0, **_kw())
    assert v is None


def test_member_first_tp_value_repset(mock_app):
    v = member_first_tp_value(mock_app, "TREAT", **_kw())
    assert math.isclose(v, 100.0)  # mean of B01, B02 at t=0


def test_member_first_tp_value_well(mock_app):
    v = member_first_tp_value(mock_app, "C01", **_kw())
    assert math.isclose(v, 50.0)


def test_member_first_tp_value_unknown(mock_app):
    assert member_first_tp_value(mock_app, "ZZ99", **_kw()) is None


# ── build_cell_scaling ──────────────────────────────────────────────────────

def test_build_cell_scaling_off():
    fc_state = (False, "", False)
    scale = build_cell_scaling(
        None, ["A01"], fc_state=fc_state, target_t=0.0, **_kw(),
    )
    assert scale["A01"] == 1.0


def test_build_cell_scaling_control_only(mock_app):
    fc_state = (True, "CTRL", False)
    scale = build_cell_scaling(
        mock_app, ["B01", "B02"], fc_state=fc_state, target_t=1.0, **_kw(),
    )
    # CTRL mean at t=1.0 is 100.0
    assert math.isclose(scale["B01"], 100.0)
    assert math.isclose(scale["B02"], 100.0)


def test_build_cell_scaling_t0_only(mock_app):
    fc_state = (False, "", True)
    scale = build_cell_scaling(
        mock_app, ["B01", "C01"], fc_state=fc_state, target_t=2.0, **_kw(),
    )
    # B01's first tp value is 100.0 (B01 is a solo well in this mock view)
    # C01's first tp value is 50.0
    assert math.isclose(scale["B01"], 100.0)
    assert math.isclose(scale["C01"], 50.0)


def test_build_cell_scaling_both(mock_app):
    fc_state = (True, "CTRL", True)
    scale = build_cell_scaling(
        mock_app, ["B01"], fc_state=fc_state, target_t=1.0, **_kw(),
    )
    # control_mean (100) * t0_mean (100) = 10000
    assert math.isclose(scale["B01"], 10000.0)


def test_build_cell_scaling_control_missing_yields_nan(mock_app):
    fc_state = (True, "CTRL", False)
    # tp doesn't exist in CTRL data
    scale = build_cell_scaling(
        mock_app, ["B01"], fc_state=fc_state, target_t=99.0, **_kw(),
    )
    assert math.isnan(scale["B01"])
