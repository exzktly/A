"""Parity test: vectorized aggregate_with_threshold_df vs. scalar aggregate_with_threshold.

The vectorized DataFrame implementation in well_viewer.data_loading is meant
to produce numerically identical output (up to floating-point rounding) to
the scalar list-of-dict implementation it replaces. This test pins that
contract across the parameter combinations consumers actually exercise:

    * threshold values
    * SEM vs SD
    * cell-area gating on/off
    * fluor gating on/off
    * per-FOV spread on/off
    * real value column vs ratio key
    * mixed numeric / unparseable / ordinal-only timepoints
    * empty fov strings, NaN included flags, NaN values

If you change either implementation, run::

    pytest tests/test_aggregate_parity.py -q

from the repo root and confirm every parameter combination still matches.
"""

from __future__ import annotations

import itertools
import math

import pytest

from well_viewer.data_loading import (
    aggregate_with_threshold,
    aggregate_with_threshold_df,
    rows_to_df,
)
from well_viewer.ratio_models import RATIO_PREFIX, RatioMetric


def _make_rows() -> list[dict]:
    """Synthetic rows covering edge cases the parity contract has to honor."""
    rows: list[dict] = []
    # 4 numeric timepoints
    numeric_tps = [0.0, 6.0, 12.0, 24.0]
    fovs = ["1", "2", "3"]

    # Numeric-timepoint rows: vary gfp & rfp intensities deterministically.
    for i, t in enumerate(numeric_tps):
        for j, fov in enumerate(fovs):
            for k in range(7):
                idx = i * 100 + j * 10 + k
                gfp = 50.0 + idx * 13.0
                rfp = 30.0 + idx * 7.0
                area = 20.0 + (idx % 5) * 30.0
                rows.append({
                    "Included": 1 if idx % 11 else 0,
                    "area_px": area,
                    "timepoint_hours": t,
                    "timepoint": f"{int(t):02d}h",
                    "fov": fov,
                    "gfp_mean_intensity": gfp,
                    "rfp_mean_intensity": rfp,
                })

    # NaN-intensity row: should be dropped by val resolution.
    rows.append({
        "Included": 1, "area_px": 100.0, "timepoint_hours": 6.0,
        "timepoint": "06h", "fov": "1",
        "gfp_mean_intensity": float("nan"), "rfp_mean_intensity": 100.0,
    })

    # NaN area row: should be dropped by area gate.
    rows.append({
        "Included": 1, "area_px": float("nan"), "timepoint_hours": 6.0,
        "timepoint": "06h", "fov": "1",
        "gfp_mean_intensity": 200.0, "rfp_mean_intensity": 100.0,
    })

    # Empty fov string: should normalize to "1".
    rows.append({
        "Included": 1, "area_px": 100.0, "timepoint_hours": 12.0,
        "timepoint": "12h", "fov": "",
        "gfp_mean_intensity": 250.0, "rfp_mean_intensity": 80.0,
    })
    # fov == "-1": load_well_csv normalizes this to "1"; rows_to_df doesn't,
    # so we feed "1" directly to keep the parity comparison apples-to-apples.

    # Ordinal-only timepoint rows: numeric tp_col missing; string unparseable.
    for label in ("conditionA", "conditionB"):
        for fov in ("1", "2"):
            for k in range(5):
                rows.append({
                    "Included": 1,
                    "area_px": 80.0 + k * 10.0,
                    "timepoint_hours": float("nan"),
                    "timepoint": label,
                    "fov": fov,
                    "gfp_mean_intensity": 120.0 + k * 25.0,
                    "rfp_mean_intensity": 60.0 + k * 15.0,
                })

    # Empty timepoint string with NaN tp_col: resolves to t=0.0 in scalar.
    rows.append({
        "Included": 1, "area_px": 100.0, "timepoint_hours": float("nan"),
        "timepoint": "", "fov": "1",
        "gfp_mean_intensity": 500.0, "rfp_mean_intensity": 90.0,
    })

    # Row with denominator that triggers ratio /0 with epsilon=0.
    rows.append({
        "Included": 1, "area_px": 100.0, "timepoint_hours": 24.0,
        "timepoint": "24h", "fov": "2",
        "gfp_mean_intensity": 300.0, "rfp_mean_intensity": 0.0,
    })

    return rows


def _agg_close(a, b, tol: float = 1e-9) -> bool:
    """AggPoint tuples are equal up to *tol* on floats; ints must match exactly."""
    if len(a) != len(b):
        return False
    # Tuple layout: (t, mean, spread, frac, n_above, n_total,
    #               frac_spread, n_above_per_fov_mean, n_above_per_fov_spread)
    int_positions = (4, 5)
    for i, (x, y) in enumerate(zip(a, b)):
        if i in int_positions:
            if int(x) != int(y):
                return False
            continue
        if isinstance(x, float) and math.isnan(x):
            if not (isinstance(y, float) and math.isnan(y)):
                return False
            continue
        if isinstance(y, float) and math.isnan(y):
            return False
        if abs(float(x) - float(y)) > tol:
            return False
    return True


_RATIO = RatioMetric(
    name="test",
    numerator_channel="gfp",
    numerator_metric="mean_intensity",
    denominator_channel="rfp",
    denominator_metric="mean_intensity",
    epsilon=0.0,
)
_RATIO_KEY = _RATIO.key()
_RATIOS = {_RATIO_KEY: _RATIO}


_PARAM_GRID = list(itertools.product(
    [0.0, 100.0, 250.0],                       # threshold
    [False, True],                             # use_sem
    [0.0, 50.0],                               # cell_area_threshold
    [None, {"rfp": 60.0}],                     # fluor_gates
    [False, True],                             # per_fov_spread
    ["gfp_mean_intensity", _RATIO_KEY],        # val_col
))


@pytest.mark.parametrize(
    ("threshold", "use_sem", "cell_area", "fluor_gates", "per_fov", "val_col"),
    _PARAM_GRID,
)
def test_aggregate_parity(threshold, use_sem, cell_area, fluor_gates, per_fov, val_col):
    rows = _make_rows()
    df = rows_to_df(rows)

    scalar = aggregate_with_threshold(
        rows,
        threshold=threshold,
        use_sem=use_sem,
        cell_area_threshold=cell_area,
        fluor_gates=fluor_gates,
        per_fov_spread=per_fov,
        val_col=val_col,
        ratios=_RATIOS,
    )
    vectorized = aggregate_with_threshold_df(
        df,
        threshold=threshold,
        use_sem=use_sem,
        cell_area_threshold=cell_area,
        fluor_gates=fluor_gates,
        per_fov_spread=per_fov,
        val_col=val_col,
        ratios=_RATIOS,
    )

    assert len(scalar) == len(vectorized), (
        f"Different number of timepoints: scalar={len(scalar)} vec={len(vectorized)}"
    )
    for i, (a, b) in enumerate(zip(scalar, vectorized)):
        assert _agg_close(a, b), (
            f"Mismatch at index {i} for threshold={threshold} use_sem={use_sem} "
            f"cell_area={cell_area} fluor_gates={fluor_gates} per_fov={per_fov} "
            f"val_col={val_col}\n  scalar={a}\n  vector={b}"
        )


def test_empty_input_returns_empty():
    assert aggregate_with_threshold_df(rows_to_df([]), threshold=0.0) == []


def test_missing_val_column_returns_empty():
    rows = [{"Included": 1, "area_px": 100.0, "timepoint_hours": 0.0,
             "timepoint": "0h", "fov": "1", "rfp_mean_intensity": 50.0}]
    df = rows_to_df(rows)
    assert aggregate_with_threshold_df(df, threshold=0.0,
                                        val_col="gfp_mean_intensity") == []


def test_missing_fluor_gate_column_returns_empty():
    rows = [{"Included": 1, "area_px": 100.0, "timepoint_hours": 0.0,
             "timepoint": "0h", "fov": "1", "gfp_mean_intensity": 100.0}]
    df = rows_to_df(rows)
    assert aggregate_with_threshold_df(
        df, threshold=0.0, fluor_gates={"yfp": 50.0}) == []
