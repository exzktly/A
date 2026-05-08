"""Pure data helpers (CSV loading, timepoint parsing, aggregation, beeswarm).

These are GUI-free utilities that were previously defined at module scope
inside ``runtime_app.py``. They are imported from there for backwards
compatibility and can be used directly by any module.
"""

from __future__ import annotations

import csv
import math
import re
import statistics
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .ratio_models import RatioMetric, is_ratio_key

if TYPE_CHECKING:
    import pandas as pd


# ── Timepoint parser ─────────────────────────────────────────────────────────

def parse_timepoint_hours(tp: str) -> Optional[float]:
    """
    Convert a timepoint string to fractional hours.
    Returns None when the string cannot be parsed at all.

    Formats tried in order:
      1. DDdHHhMMm  e.g. "02d04h30m" -> 52.5
      2. Standalone unit suffix  e.g. "48h", "2d", "30m"
      3. Pure number  e.g. "48" or "1.5" -> treated as hours
      4. Prefixed ordinal  e.g. "T01", "day2" -> numeric suffix as index
    """
    s = tp.strip()
    if not s:
        return None

    # 1. DDdHHhMMm (all components optional, at least one required)
    m = re.fullmatch(r"(?:(\d{1,4})d)?(?:(\d{1,2})h)?(?:(\d{1,2})m)?", s, re.I)
    if m and any(m.groups()):
        return int(m.group(1) or 0)*24.0 + int(m.group(2) or 0) + int(m.group(3) or 0)/60.0

    # 2. Standalone unit: "48h", "2d", "30m", "90min"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(h(?:ours?)?|d(?:ays?)?|m(?:in(?:utes?)?)?)",
                     s, re.I)
    if m:
        val, unit = float(m.group(1)), m.group(2)[0].lower()
        if unit == "h": return val
        if unit == "d": return val * 24.0
        if unit == "m": return val / 60.0

    # 3. Pure number (treated as hours)
    try:
        return float(s)
    except ValueError:
        pass

    # 4. Prefixed ordinal: strip leading non-digit chars, keep trailing number
    #    e.g. "T01" -> 1.0, "day02" -> 2.0, "tp_3" -> 3.0
    m = re.search(r"(\d+(?:\.\d+)?)$", s)
    if m:
        return float(m.group(1))

    return None


# ── CSV loading and channel detection ────────────────────────────────────────

# Columns kept as strings (not coerced to float)
_STRING_COLS = {"filename", "experiment", "channel", "well", "fov", "timepoint"}


def row_is_included(row: dict) -> bool:
    """Return True when CSV row is marked as included (Included == 1)."""
    raw = row.get("Included", 1)
    try:
        return int(float(raw)) == 1
    except (TypeError, ValueError):
        return False


def load_well_csv(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if "Included" not in row:
                row["Included"] = 1
            coerced: dict = {}
            for k, v in row.items():
                key_norm = str(k).strip().lower()
                if key_norm in _STRING_COLS:
                    if key_norm == "fov" and str(v).strip() in {"", "-1"}:
                        coerced[k] = "1"
                    else:
                        coerced[k] = v
                else:
                    try:
                        coerced[k] = float(v)
                    except (ValueError, TypeError):
                        coerced[k] = v
            rows.append(coerced)
    return rows


def rows_to_df(rows: List[dict]) -> "pd.DataFrame":
    """Build a DataFrame matching ``load_well_csv`` semantics.

    String columns stay as object dtype; numeric ones are coerced via
    ``pd.to_numeric`` with ``errors="coerce"``. An empty input yields an empty
    DataFrame (no columns) — callers that need a specific schema must add
    columns themselves.
    """
    import pandas as pd

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "Included" not in df.columns:
        df["Included"] = 1
    for col in df.columns:
        if str(col).strip().lower() in _STRING_COLS:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_well_csv_df(path: Path) -> "pd.DataFrame":
    """DataFrame variant of :func:`load_well_csv`. Same normalization rules."""
    return rows_to_df(load_well_csv(path))


def detect_fluor_channels(rows: List[dict]) -> List[str]:
    """
    Inspect column names in *rows* and return a sorted list of fluorescent
    channel prefixes that have a *_mean_intensity column.
    """
    if not rows:
        return []
    channels = []
    for col in rows[0].keys():
        if col.endswith("_mean_intensity"):
            prefix = col[: -len("_mean_intensity")]
            if prefix:
                channels.append(prefix)
    return sorted(channels)


def detect_smfish_channels(rows: List[dict]) -> List[str]:
    """
    Inspect column names in *rows* and return a sorted list of smFISH
    channel prefixes that have a *_smfish_count column.
    """
    if not rows:
        return []
    channels = []
    for col in rows[0].keys():
        if col.endswith("_smfish_count"):
            prefix = col[: -len("_smfish_count")]
            if prefix:
                channels.append(prefix)
    return sorted(channels)


def detect_nuclear_channel_token(rows: List[dict]) -> str:
    """Return the nuclear/segmentation channel token from the CSV 'channel' column (lowercase)."""
    if not rows:
        return ""
    return str(rows[0].get("channel", "") or "").strip().lower()


def normalize_channel_tokens(tokens: List[str]) -> List[str]:
    """Stable lower-case de-dupe for channel tokens."""
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        cleaned = str(tok or "").strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def merge_fluor_channels(
    pipeline_fluor: List[str],
    detected_fluor: List[str],
    seg_channel_token: str = "",
) -> List[str]:
    """Merge pipeline + detected channel lists with stable order, always including seg token."""
    merged = normalize_channel_tokens(list(pipeline_fluor) + list(detected_fluor))
    seg_tok = str(seg_channel_token or "").strip().lower()
    if seg_tok and seg_tok not in merged:
        merged.append(seg_tok)
    return merged


def detect_review_image_channels(rows: List[dict], fluor_channels: List[str], seg_channel_token: str = "") -> List[str]:
    """Return channel prefixes suitable for Review Image.

    Harmonized policy:
      - use the measured fluorescence channels
      - include the explicit segmentation channel token from CSV `channel`
    """
    chans: list[str] = []
    seen: set[str] = set()
    for ch in fluor_channels:
        tok = str(ch or "").strip().lower()
        if tok and tok not in seen:
            seen.add(tok)
            chans.append(tok)
    seg_tok = str(seg_channel_token or "").strip().lower()
    if seg_tok and seg_tok not in seen:
        seen.add(seg_tok)
        chans.append(seg_tok)
    return chans


# ── Value resolution (real columns + virtual ratio columns) ──────────────────

def resolve_value(
    row: dict,
    key: str,
    ratios: Optional[Dict[str, RatioMetric]] = None,
) -> float:
    """Return the float value at *key* from *row*.

    *key* may be either a real CSV column name (e.g. ``"gfp_mean_intensity"``)
    or a ratio key in the form ``"ratio:<name>"``. Ratios are resolved by
    looking up the ``RatioMetric`` in *ratios* and computing
    ``numerator / (denominator + epsilon)``.

    Returns ``float('nan')`` for any missing column, non-numeric value, or
    division-by-zero with epsilon=0. Callers are expected to drop NaNs.
    """
    if is_ratio_key(key):
        if not ratios:
            return float("nan")
        ratio = ratios.get(key)
        if ratio is None:
            return float("nan")
        try:
            num = float(row[ratio.numerator_col()])
            den = float(row[ratio.denominator_col()])
        except (KeyError, TypeError, ValueError):
            return float("nan")
        if not (math.isfinite(num) and math.isfinite(den)):
            return float("nan")
        denom = den + ratio.epsilon
        if denom == 0.0:
            return float("nan")
        return num / denom

    try:
        val = float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")
    return val if math.isfinite(val) else float("nan")


# ── Aggregation ──────────────────────────────────────────────────────────────

# (time_h, mean_above_threshold, sd_above, fraction_above, n_above, n_total,
#  frac_spread, n_above_per_fov_mean, n_above_per_fov_spread)
# n_above                 : cells above threshold at this timepoint  → plot 1 denominator
# n_total                 : all cells at this timepoint              → plot 2 denominator
# frac_spread             : SD/SEM of the fraction across per-FOV fractions when
#                           per_fov_spread is enabled, else 0.0.
# n_above_per_fov_mean    : when per_fov_spread is enabled, mean of per-FOV
#                           above-threshold counts; else 0.0.
# n_above_per_fov_spread  : when per_fov_spread is enabled, SD/SEM of those
#                           per-FOV counts (the "Aggregate FOVs" toggle uses
#                           these to make the events panel show per-FOV mean ±
#                           error instead of a single total bar); else 0.0.
# Trailing positions so existing destructuring with `*_` (and `*extra`) keeps
# working.
AggPoint = Tuple[float, float, float, float, int, int, float, float, float]


def _ordinal_timepoints_df(df: "pd.DataFrame", tp_col: str = "timepoint_hours") -> Dict[str, float]:
    """Build a string→ordinal mapping for rows whose numeric timepoint is NaN/missing."""
    import numpy as np
    import pandas as pd

    if len(df) == 0 or "timepoint" not in df.columns:
        return {}
    if tp_col in df.columns:
        tp_num = pd.to_numeric(df[tp_col], errors="coerce").to_numpy()
    else:
        tp_num = np.full(len(df), np.nan)
    tp_str = df["timepoint"].fillna("").astype(str).to_numpy()
    not_finite = ~np.isfinite(tp_num)
    raw_strings: set[str] = set()
    for s in tp_str[not_finite]:
        s_str = str(s)
        if s_str and parse_timepoint_hours(s_str) is None:
            raw_strings.add(s_str)
    return {s: float(i) for i, s in enumerate(sorted(raw_strings))}


def aggregate_with_threshold_df(
    df: "pd.DataFrame",
    threshold: float,
    use_sem: bool = False,
    tp_col: str = "timepoint_hours",
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
    per_fov_spread: bool = False,
    ratios: Optional[Dict[str, RatioMetric]] = None,
) -> List[AggPoint]:
    """Group rows by timepoint; compute stats for cells above threshold.

    Applies consistent gating (Included flag, cell-area threshold, per-channel
    fluorescence gates) across all rows up front, then computes statistics on
    the filtered cell population. This ensures that "Fraction On" and other
    metrics are computed on the same set of cells regardless of which channel
    or metric is being plotted.

    When ``per_fov_spread`` is True, the spread on the mean (third tuple
    field) is the SD/SEM **across per-FOV mean intensities** at each timepoint
    instead of the SD/SEM across individual cells. The trailing ``frac_spread``
    field is also populated as the SD/SEM across per-FOV ``n_above/n_total``
    ratios so the bar plot can draw an error bar on the fraction. Mean,
    fraction, and counts themselves are unaffected. Use this in single-well
    mode to treat FOVs as technical replicates within the well.
    """
    import numpy as np
    import pandas as pd

    if df is None or len(df) == 0:
        return []
    if fluor_gates is None:
        fluor_gates = {}

    n = len(df)

    if "Included" in df.columns:
        incl = pd.to_numeric(df["Included"], errors="coerce").to_numpy()
        mask = incl == 1
    else:
        mask = np.ones(n, dtype=bool)

    if "area_px" in df.columns:
        area = pd.to_numeric(df["area_px"], errors="coerce").to_numpy()
        # Scalar uses ``if area <= threshold: continue`` which silently keeps
        # NaN areas (NaN comparisons are always False). Match that exactly via
        # ``~(area <= threshold)`` rather than ``area > threshold``, since
        # the latter drops NaN.
        with np.errstate(invalid="ignore"):
            mask &= ~(area <= cell_area_threshold)
    elif 0.0 <= cell_area_threshold:
        # Scalar: row.get("area_px", 0) → 0 → 0 <= threshold → skip.
        return []

    for channel, gate in fluor_gates.items():
        col = f"{channel}_mean_intensity"
        if col not in df.columns:
            # Scalar treats missing column as NaN → gate fails → skip all rows.
            return []
        v = pd.to_numeric(df[col], errors="coerce").to_numpy()
        mask &= np.isfinite(v) & (v > gate)

    if not mask.any():
        return []

    ord_map = _ordinal_timepoints_df(df, tp_col)

    if tp_col in df.columns:
        tp_num = pd.to_numeric(df[tp_col], errors="coerce").to_numpy().astype(float)
    else:
        tp_num = np.full(n, np.nan)

    if "timepoint" in df.columns:
        tp_str = df["timepoint"].fillna("").astype(str).str.strip().to_numpy()
    else:
        tp_str = np.array([""] * n, dtype=object)

    need = ~np.isfinite(tp_num)
    if need.any():
        cache: Dict[str, float] = {}
        for s in np.unique(tp_str[need]):
            s_str = str(s)
            if s_str == "":
                cache[s_str] = 0.0
            else:
                v = parse_timepoint_hours(s_str)
                if v is None:
                    v = ord_map.get(s_str)
                cache[s_str] = float(v) if v is not None else float("nan")
        for i in np.flatnonzero(need):
            tp_num[i] = cache[str(tp_str[i])]

    if is_ratio_key(val_col):
        if not ratios or val_col not in ratios:
            return []
        r = ratios[val_col]
        ncol, dcol = r.numerator_col(), r.denominator_col()
        if ncol not in df.columns or dcol not in df.columns:
            return []
        num = pd.to_numeric(df[ncol], errors="coerce").to_numpy()
        den = pd.to_numeric(df[dcol], errors="coerce").to_numpy()
        finite = np.isfinite(num) & np.isfinite(den)
        denom = den + r.epsilon
        nz = denom != 0.0
        with np.errstate(divide="ignore", invalid="ignore"):
            val = np.where(finite & nz, num / np.where(nz, denom, 1.0), np.nan)
    else:
        if val_col not in df.columns:
            return []
        v = pd.to_numeric(df[val_col], errors="coerce").to_numpy()
        val = np.where(np.isfinite(v), v, np.nan)

    final = mask & np.isfinite(tp_num) & np.isfinite(val)
    if not final.any():
        return []

    tp_arr = tp_num[final]
    val_arr = val[final]

    if per_fov_spread:
        if "fov" in df.columns:
            fov_series = (df["fov"].fillna("1").astype(str).str.strip()
                          .replace("", "1"))
        else:
            fov_series = pd.Series(["1"] * n, index=df.index)
        fov_arr = fov_series.to_numpy()[final]
    else:
        fov_arr = None

    return _aggregate_arrays(tp_arr, val_arr, fov_arr, threshold, use_sem,
                             per_fov_spread)


def _aggregate_arrays(
    tp_arr,
    val_arr,
    fov_arr,
    threshold: float,
    use_sem: bool,
    per_fov_spread: bool,
) -> List[AggPoint]:
    import numpy as np

    result: List[AggPoint] = []
    for t in np.unique(tp_arr):
        idx = tp_arr == t
        v = val_arr[idx]
        n_total = int(v.size)
        above_mask = v > threshold
        above = v[above_mask]
        n_above = int(above.size)
        mean = float(above.sum() / n_above) if n_above else float("nan")

        spread = 0.0
        frac_spread = 0.0
        n_above_per_fov_mean = 0.0
        n_above_per_fov_spread = 0.0

        if per_fov_spread:
            f = fov_arr[idx]
            fov_total: Dict[str, int] = {}
            fov_above: Dict[str, List[float]] = {}
            for vi, fi in zip(v.tolist(), f.tolist()):
                fov_total[fi] = fov_total.get(fi, 0) + 1
                if vi > threshold:
                    fov_above.setdefault(fi, []).append(vi)

            fov_means = [statistics.mean(vs) for vs in fov_above.values() if vs]
            if len(fov_means) > 1:
                sd = statistics.pstdev(fov_means)
                spread = sd / math.sqrt(len(fov_means)) if use_sem else sd

            fov_fracs = [len(fov_above.get(fov, ())) / total
                         for fov, total in fov_total.items() if total > 0]
            if len(fov_fracs) > 1:
                fsd = statistics.pstdev(fov_fracs)
                frac_spread = fsd / math.sqrt(len(fov_fracs)) if use_sem else fsd

            fov_n_above = [len(fov_above.get(fov, ()))
                           for fov, total in fov_total.items() if total > 0]
            if len(fov_n_above) >= 1:
                n_above_per_fov_mean = sum(fov_n_above) / len(fov_n_above)
            if len(fov_n_above) > 1:
                nsd = statistics.pstdev(fov_n_above)
                n_above_per_fov_spread = (nsd / math.sqrt(len(fov_n_above))
                                          if use_sem else nsd)
        else:
            if n_above > 1:
                m = above.sum() / n_above
                sd = float(np.sqrt(((above - m) ** 2).sum() / n_above))
                spread = sd / math.sqrt(n_above) if use_sem else sd

        result.append((float(t), mean, float(spread),
                       n_above / n_total if n_total else float("nan"),
                       int(n_above), int(n_total), float(frac_spread),
                       float(n_above_per_fov_mean),
                       float(n_above_per_fov_spread)))
    return result


def _all_fluor_values(rows: List[dict], val_col: str = "gfp_mean_intensity") -> List[float]:
    return [float(row[val_col]) for row in rows
            if row_is_included(row)
            if val_col in row and math.isfinite(float(row[val_col]))
            if isinstance(row[val_col], (int, float)) and not isinstance(row[val_col], bool)]


def _all_fluor_values_filtered(
    rows: List[dict],
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
    ratios: Optional[Dict[str, RatioMetric]] = None,
    tp_filter: Optional[float] = None,
    tp_col: str = "timepoint_hours",
) -> List[float]:
    """Extract fluorescence values from rows, filtering by cell area and all fluorescence gates.

    When ``tp_filter`` is supplied, only rows whose timepoint matches (within
    a 1e-6 tolerance) are included.
    """
    if fluor_gates is None:
        fluor_gates = {}

    result = []
    for row in rows:
        if not row_is_included(row):
            continue
        try:
            area = float(row.get("area_px", 0))
            if area <= cell_area_threshold:
                continue
        except (ValueError, TypeError):
            continue

        gates_passed = True
        for channel, gate_threshold in fluor_gates.items():
            col = f"{channel}_mean_intensity"
            try:
                fluor = float(row.get(col, float('nan')))
                if fluor != fluor or fluor <= gate_threshold:
                    gates_passed = False
                    break
            except (ValueError, TypeError):
                gates_passed = False
                break

        if not gates_passed:
            continue

        if tp_filter is not None:
            try:
                tp = float(row.get(tp_col, float("nan")))
            except (ValueError, TypeError):
                continue
            if not math.isfinite(tp) or abs(tp - tp_filter) > 1e-6:
                continue

        val = resolve_value(row, val_col, ratios)
        if not math.isfinite(val):
            continue
        result.append(val)

    return result


# ── Beeswarm jitter ──────────────────────────────────────────────────────────

def _beeswarm_jitter(
    values: List[float],
    x_center: float = 0.0,
    max_spread: float = 0.35,
    n_bins: int = 40,
) -> Tuple[List[float], List[float]]:
    """
    Compute x-jitter positions for a beeswarm column.

    Values are binned vertically (by value magnitude); within each bin points
    are spread left/right alternately from the centre.  Returns parallel lists
    (xs, ys) ready for ax.scatter().
    """
    if not values:
        return [], []

    sorted_v = sorted(values)
    lo, hi = sorted_v[0], sorted_v[-1]
    rng = hi - lo if hi > lo else 1.0
    bin_w = rng / n_bins

    bins: Dict[int, List[int]] = {}
    for i, v in enumerate(values):
        b = min(int((v - lo) / bin_w), n_bins - 1)
        bins.setdefault(b, []).append(i)

    step = max_spread / max(max(len(idxs) for idxs in bins.values()), 1)

    xs = [0.0] * len(values)
    ys = list(values)
    for idxs in bins.values():
        idxs_sorted = sorted(idxs, key=lambda k: values[k])
        for rank, idx in enumerate(idxs_sorted):
            offset = ((rank + 1) // 2) * (1 if rank % 2 == 1 else -1)
            xs[idx] = x_center + offset * step

    return xs, ys


# ── Well-token parsing ───────────────────────────────────────────────────────

def extract_well_token(label: str) -> Optional[str]:
    """'gfp_measurements_B10' → 'B10'."""
    m = re.search(r"([A-Ha-h])(\d{1,2})$", label)
    return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else None


def parse_well_token(token: str) -> Optional[Tuple[int, int]]:
    """Convert a well token like ``"A01"`` into ``(row, col)`` zero-based.

    Row is derived from the letter (A→0, …, H→7); col from the number minus 1.
    Returns None when the token cannot be parsed.
    """
    if not token:
        return None
    m = re.fullmatch(r"\s*([A-Za-z])(\d{1,2})\s*", str(token))
    if not m:
        return None
    row = ord(m.group(1).upper()) - ord("A")
    col = int(m.group(2)) - 1
    if row < 0 or col < 0:
        return None
    return row, col


# ── Plot-group iteration ─────────────────────────────────────────────────────

def iter_plot_groups(app) -> Iterator[Tuple[str, str, List[dict]]]:
    """Yield ``(name, color, rows)`` for each replicate set or selected well.

    Mirrors the loop used by the line and bar plot controllers:
      - if replicate sets are defined, iterate one per replicate set, pooling
        rows from all wells in the set;
      - otherwise iterate one per selected well.

    The colour follows the existing well-colour palette from the theme via
    ``app._color_for_label`` / ``app._color_for_well`` when available, falling
    back to a neutral palette otherwise.
    """
    rep_sets = list(getattr(app, "_rep_sets", []) or [])
    well_paths = getattr(app, "_well_paths", {}) or {}
    selected = set(getattr(app, "_selected_wells", set()) or set())
    color_for_label = getattr(app, "_color_for_label", None)
    color_for_well = getattr(app, "_color_for_well", None)
    fallback_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22",
    ]

    def _color(name: str, idx: int) -> str:
        if callable(color_for_label):
            try:
                c = color_for_label(name)
                if c:
                    return c
            except Exception:
                pass
        if callable(color_for_well):
            try:
                c = color_for_well(name)
                if c:
                    return c
            except Exception:
                pass
        return fallback_palette[idx % len(fallback_palette)]

    if rep_sets:
        for idx, rset in enumerate(rep_sets):
            wells = [w for w in rset.wells if w in well_paths]
            if not wells:
                continue
            pooled: List[dict] = []
            for w in wells:
                pooled.extend(app._get_rows(w))
            yield rset.name, _color(rset.name, idx), pooled
        return

    if not selected:
        selected = set(well_paths.keys())
    for idx, w in enumerate(sorted(selected)):
        if w not in well_paths:
            continue
        yield w, _color(w, idx), app._get_rows(w)
