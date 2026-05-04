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
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import numpy as np

from .ratio_models import RatioMetric, is_ratio_key


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


def _ordinal_timepoints(rows: List[dict], tp_col: str = "timepoint_hours") -> Dict[str, float]:
    """
    Build a string->ordinal mapping for rows whose numeric timepoint is NaN/missing.
    """
    raw_strings: set = set()
    for row in rows:
        raw = row.get(tp_col)
        numeric_ok = isinstance(raw, float) and not math.isnan(raw)
        if not numeric_ok:
            tp_str = str(row.get("timepoint", ""))
            if tp_str and parse_timepoint_hours(tp_str) is None:
                raw_strings.add(tp_str)
    return {s: float(i) for i, s in enumerate(sorted(raw_strings))}


def aggregate_with_threshold(
    rows: List[dict],
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

    Applies consistent gating criteria across all channels upfront, then computes
    statistics on the filtered cell population. This ensures that "Fraction On"
    and other metrics are computed on the same set of cells regardless of which
    channel or metric is being plotted.

    When ``per_fov_spread`` is True, the spread on the mean (third tuple field)
    is the SD/SEM **across per-FOV mean intensities** at each timepoint instead
    of the SD/SEM across individual cells. The trailing ``frac_spread`` field
    is also populated as the SD/SEM across per-FOV ``n_above/n_total`` ratios
    so the bar plot can draw an error bar on the fraction. Mean, fraction, and
    counts themselves are unaffected. Use this in single-well mode to treat
    FOVs as technical replicates within the well.

    Returns:
        List of AggPoint tuples: (timepoint, mean, spread, fraction_above, n_above, n_total, frac_spread)
    """
    if fluor_gates is None:
        fluor_gates = {}

    all_v:   Dict[float, List[float]] = defaultdict(list)
    above_v: Dict[float, List[float]] = defaultdict(list)
    fov_above: Dict[float, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    fov_total: Dict[float, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    ordinals = _ordinal_timepoints(rows, tp_col)

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
                if fluor != fluor or fluor <= gate_threshold:  # NaN or below gate
                    gates_passed = False
                    break
            except (ValueError, TypeError):
                gates_passed = False
                break

        if not gates_passed:
            continue

        raw = row.get(tp_col)
        if isinstance(raw, float) and not math.isnan(raw):
            t: Optional[float] = raw
        else:
            tp_str = str(row.get("timepoint", ""))
            t = parse_timepoint_hours(tp_str)
            if t is None:
                t = ordinals.get(tp_str)
            if t is None and not tp_str:
                t = 0.0
        if t is None:
            continue

        val = resolve_value(row, val_col, ratios)
        if not math.isfinite(val):
            continue

        all_v[t].append(val)
        if per_fov_spread:
            fov = str(row.get("fov", "1") or "1").strip() or "1"
            fov_total[t][fov] += 1
        if val > threshold:
            above_v[t].append(val)
            if per_fov_spread:
                fov_above[t][fov].append(val)

    result: List[AggPoint] = []
    for t in sorted(all_v):
        above   = above_v.get(t, [])
        n_total = len(all_v[t])
        n_above = len(above)
        mean    = sum(above) / n_above if n_above else float("nan")
        spread  = 0.0
        frac_spread = 0.0
        n_above_per_fov_mean = 0.0
        n_above_per_fov_spread = 0.0
        if per_fov_spread:
            fov_above_t = fov_above.get(t, {})
            fov_total_t = fov_total.get(t, {})
            fov_means = [sum(vs) / len(vs) for vs in fov_above_t.values() if vs]
            n_fov_means = len(fov_means)
            if n_fov_means > 1:
                sd = statistics.pstdev(fov_means)
                spread = sd / math.sqrt(n_fov_means) if use_sem else sd
            # Fraction-above SD/SEM across FOVs that contributed any cell to
            # the gated population at this timepoint (an FOV with zero gated
            # cells has no defined fraction and is excluded).
            fov_fracs = [
                len(fov_above_t.get(fov, ())) / total
                for fov, total in fov_total_t.items() if total > 0
            ]
            n_fov_fracs = len(fov_fracs)
            if n_fov_fracs > 1:
                fsd = statistics.pstdev(fov_fracs)
                frac_spread = fsd / math.sqrt(n_fov_fracs) if use_sem else fsd
            # Per-FOV count of events above threshold. Include every FOV that
            # contributed any gated cell, so an FOV with zero above-threshold
            # cells correctly counts as a 0 (not as missing data) when
            # averaging — that's the difference between "no FOVs imaged" and
            # "FOVs imaged but no events".
            fov_n_above = [
                len(fov_above_t.get(fov, ()))
                for fov, total in fov_total_t.items() if total > 0
            ]
            n_fov_above = len(fov_n_above)
            if n_fov_above >= 1:
                n_above_per_fov_mean = sum(fov_n_above) / n_fov_above
            if n_fov_above > 1:
                nsd = statistics.pstdev(fov_n_above)
                n_above_per_fov_spread = nsd / math.sqrt(n_fov_above) if use_sem else nsd
        else:
            if n_above > 1:
                sd     = statistics.pstdev(above)
                spread = sd / math.sqrt(n_above) if use_sem else sd
        result.append((t, mean, spread,
                       n_above / n_total if n_total else float("nan"),
                       n_above, n_total, frac_spread,
                       n_above_per_fov_mean, n_above_per_fov_spread))
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


# ── Columnar (numpy) representation for fast aggregation ─────────────────────
#
# The CSV-derived ``List[dict]`` representation is O(N) Python-level work for
# every aggregation. ``WellColumns`` mirrors the same data into a dict-of-numpy
# arrays so the line/bar-plot hot paths (gating mask, threshold compare,
# group-by-timepoint reductions) become vectorized.
#
# The legacy ``aggregate_with_threshold`` / ``_all_fluor_values_filtered``
# functions remain so external callers passing raw rows keep working; this
# module also exposes columnar twins that operate directly on ``WellColumns``.


@dataclass
class WellColumns:
    """Columnar mirror of a well's CSV rows for vectorized analytics.

    Fields are aligned: index ``i`` refers to the same physical row across
    every array. ``included_mask`` mirrors the per-row ``Included`` flag and
    is mutated in place by the cell-gating worker; ``version`` is bumped
    whenever ``included_mask`` changes so dependent caches invalidate.
    """

    n_rows: int
    numeric: Dict[str, np.ndarray] = field(default_factory=dict)
    strings: Dict[str, np.ndarray] = field(default_factory=dict)
    area_px: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    tp_hours: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    tp_strings: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=object))
    fov_codes: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int32))
    fov_labels: List[str] = field(default_factory=list)
    included_mask: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))
    version: int = 0

    def get_numeric(self, col: str) -> Optional[np.ndarray]:
        return self.numeric.get(col)


def _to_float_array(values: Iterable[Any]) -> np.ndarray:
    """Coerce mixed values to float64 with NaN for unparseable entries."""
    out = np.empty(len(values) if hasattr(values, "__len__") else 0, dtype=np.float64)
    for i, v in enumerate(values):
        if isinstance(v, bool):
            out[i] = float(v)
        else:
            try:
                out[i] = float(v)
            except (TypeError, ValueError):
                out[i] = float("nan")
    return out


def build_well_columns_from_rows(rows: List[dict]) -> WellColumns:
    """Build a ``WellColumns`` from a list of CSV-loaded dict rows.

    Used by both ``load_well_columns`` (after parsing the CSV) and by legacy
    callers that already hold ``List[dict]``. Unparseable timepoint strings
    leave ``tp_hours`` as NaN and the original string in ``tp_strings``;
    aggregators apply an ordinal fallback only when needed.
    """
    n = len(rows)
    cols = WellColumns(n_rows=n)
    if n == 0:
        return cols

    keys = list(rows[0].keys())
    string_keys = {k for k in keys if str(k).strip().lower() in _STRING_COLS}
    numeric_keys = [k for k in keys if k not in string_keys]

    for k in numeric_keys:
        col = np.empty(n, dtype=np.float64)
        for i, row in enumerate(rows):
            v = row.get(k, float("nan"))
            if isinstance(v, bool):
                col[i] = float(v)
            else:
                try:
                    col[i] = float(v)
                except (TypeError, ValueError):
                    col[i] = float("nan")
        cols.numeric[k] = col

    for k in string_keys:
        arr = np.empty(n, dtype=object)
        for i, row in enumerate(rows):
            arr[i] = row.get(k, "")
        cols.strings[k] = arr

    if "area_px" in cols.numeric:
        cols.area_px = cols.numeric["area_px"]
    else:
        cols.area_px = np.zeros(n, dtype=np.float64)

    # tp_hours: prefer numeric column, fall back to parsing the timepoint
    # string. Truly unparseable strings stay NaN here and are resolved via
    # ordinal mapping inside the aggregator (matching legacy semantics).
    tp_hours = np.empty(n, dtype=np.float64)
    if "timepoint_hours" in cols.numeric:
        tp_hours[:] = cols.numeric["timepoint_hours"]
    else:
        tp_hours[:] = float("nan")

    tp_strings = np.empty(n, dtype=object)
    str_col = cols.strings.get("timepoint")
    needs_parse = ~np.isfinite(tp_hours)
    if str_col is not None:
        for i in range(n):
            tp_strings[i] = str(str_col[i] or "")
        if needs_parse.any():
            for i in np.flatnonzero(needs_parse):
                parsed = parse_timepoint_hours(tp_strings[i])
                if parsed is not None:
                    tp_hours[i] = parsed
    else:
        tp_strings[:] = ""
    cols.tp_hours = tp_hours
    cols.tp_strings = tp_strings

    # fov as int codes for fast bincount in per-FOV aggregations.
    fov_str = cols.strings.get("fov")
    if fov_str is not None:
        labels: list[str] = []
        idx_by_label: dict[str, int] = {}
        codes = np.empty(n, dtype=np.int32)
        for i in range(n):
            raw = str(fov_str[i] or "1").strip() or "1"
            code = idx_by_label.get(raw)
            if code is None:
                code = len(labels)
                idx_by_label[raw] = code
                labels.append(raw)
            codes[i] = code
        cols.fov_codes = codes
        cols.fov_labels = labels
    else:
        cols.fov_codes = np.zeros(n, dtype=np.int32)
        cols.fov_labels = ["1"]

    inc = np.ones(n, dtype=bool)
    inc_col = None
    for k in keys:
        if str(k).strip() == "Included":
            inc_col = k
            break
    if inc_col is not None:
        for i, row in enumerate(rows):
            try:
                inc[i] = int(float(row.get(inc_col, 1))) == 1
            except (TypeError, ValueError):
                inc[i] = False
    cols.included_mask = inc

    return cols


def load_well_columns(path: Path) -> WellColumns:
    """Read a well CSV directly into a ``WellColumns``.

    Currently a thin wrapper around ``load_well_csv`` + ``build_well_columns_from_rows``.
    Kept as a separate entry point so the row-list intermediate can be
    eliminated later without touching call sites.
    """
    rows = load_well_csv(path)
    return build_well_columns_from_rows(rows)


def _resolve_value_array(
    cols: WellColumns,
    key: str,
    ratios: Optional[Dict[str, RatioMetric]] = None,
) -> np.ndarray:
    """Vectorized counterpart of ``resolve_value`` returning a length-``n_rows`` array."""
    n = cols.n_rows
    if is_ratio_key(key):
        if not ratios:
            return np.full(n, np.nan, dtype=np.float64)
        ratio = ratios.get(key)
        if ratio is None:
            return np.full(n, np.nan, dtype=np.float64)
        num_col = cols.numeric.get(ratio.numerator_col())
        den_col = cols.numeric.get(ratio.denominator_col())
        if num_col is None or den_col is None:
            return np.full(n, np.nan, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            denom = den_col + ratio.epsilon
            out = np.where(denom != 0.0, num_col / denom, np.nan)
        out = np.where(np.isfinite(num_col) & np.isfinite(den_col), out, np.nan)
        return out.astype(np.float64, copy=False)

    arr = cols.numeric.get(key)
    if arr is None:
        return np.full(n, np.nan, dtype=np.float64)
    out = np.where(np.isfinite(arr), arr, np.nan)
    return out.astype(np.float64, copy=False)


def _compute_gating_mask(
    cols: WellColumns,
    cell_area_threshold: float,
    fluor_gates: Optional[Dict[str, float]],
) -> np.ndarray:
    """Return the per-row boolean mask after Included/area/fluor-gate filtering."""
    mask = cols.included_mask & (cols.area_px > cell_area_threshold)
    if not fluor_gates:
        return mask
    for channel, gate in fluor_gates.items():
        col = cols.numeric.get(f"{channel}_mean_intensity")
        if col is None:
            mask = np.zeros_like(mask)
            return mask
        mask &= np.isfinite(col) & (col > gate)
    return mask


def _resolve_tp_hours_with_ordinals(cols: WellColumns) -> np.ndarray:
    """Return ``tp_hours`` with ordinal fallback for unparseable strings.

    Mirrors the per-call ordinal mapping in the legacy
    ``aggregate_with_threshold`` so unparseable timepoints still group.
    """
    tp = cols.tp_hours
    missing = ~np.isfinite(tp)
    if not missing.any():
        return tp
    # Empty strings get assigned 0.0 (legacy behavior) — no ordinal needed.
    tps = cols.tp_strings
    out = tp.copy()
    distinct: set[str] = set()
    for i in np.flatnonzero(missing):
        s = str(tps[i] or "")
        if s:
            distinct.add(s)
        else:
            out[i] = 0.0
    if distinct:
        ordinals = {s: float(j) for j, s in enumerate(sorted(distinct))}
        for i in np.flatnonzero(missing):
            s = str(tps[i] or "")
            if s:
                out[i] = ordinals[s]
    return out


@dataclass
class WellAgg:
    """Threshold-independent intermediate for fast plot redraws.

    Built once per ``(well, version, val_col, area_threshold, fluor_gates,
    ratio)`` combination and reused across threshold-only changes.
    """

    timepoints: np.ndarray  # sorted unique tp_hours, float64
    inv: np.ndarray  # group index per surviving row, intp
    values: np.ndarray  # gated values, float64
    fov_codes: np.ndarray  # post-mask fov codes, intp (or empty)
    n_total_per_t: np.ndarray  # gated row count per timepoint, int64

    @property
    def n_groups(self) -> int:
        return int(self.timepoints.shape[0])


_EMPTY_WELL_AGG = WellAgg(
    timepoints=np.zeros(0, dtype=np.float64),
    inv=np.zeros(0, dtype=np.intp),
    values=np.zeros(0, dtype=np.float64),
    fov_codes=np.zeros(0, dtype=np.intp),
    n_total_per_t=np.zeros(0, dtype=np.int64),
)


def build_well_agg(
    cols: WellColumns,
    *,
    val_col: str,
    cell_area_threshold: float,
    fluor_gates: Optional[Dict[str, float]],
    ratios: Optional[Dict[str, RatioMetric]],
) -> WellAgg:
    """Apply gating/area/value filters and group by timepoint — no threshold."""
    if cols.n_rows == 0:
        return _EMPTY_WELL_AGG

    mask = _compute_gating_mask(cols, cell_area_threshold, fluor_gates)
    if not mask.any():
        return _EMPTY_WELL_AGG

    val = _resolve_value_array(cols, val_col, ratios)
    mask &= np.isfinite(val)
    if not mask.any():
        return _EMPTY_WELL_AGG

    tp_hours = _resolve_tp_hours_with_ordinals(cols)
    mask &= np.isfinite(tp_hours)
    if not mask.any():
        return _EMPTY_WELL_AGG

    t = tp_hours[mask]
    v = val[mask]
    fov = cols.fov_codes[mask].astype(np.intp, copy=False)

    uniq, inv = np.unique(t, return_inverse=True)
    n_total = np.bincount(inv, minlength=int(uniq.shape[0])).astype(np.int64)
    return WellAgg(
        timepoints=uniq.astype(np.float64, copy=False),
        inv=inv.astype(np.intp, copy=False),
        values=v.astype(np.float64, copy=False),
        fov_codes=fov,
        n_total_per_t=n_total,
    )


def stats_from_well_agg(
    agg: WellAgg,
    threshold: float,
    *,
    use_sem: bool = False,
    per_fov_spread: bool = False,
) -> List[AggPoint]:
    """Reduce a cached ``WellAgg`` to ``AggPoint`` tuples for *threshold*."""
    n_groups = agg.n_groups
    if n_groups == 0:
        return []

    inv = agg.inv
    v = agg.values
    n_total = agg.n_total_per_t

    above = v > threshold
    n_above = np.bincount(inv, weights=above.astype(np.float64), minlength=n_groups).astype(np.int64)
    sum_ab = np.bincount(inv, weights=np.where(above, v, 0.0), minlength=n_groups)
    sq_ab = np.bincount(inv, weights=np.where(above, v * v, 0.0), minlength=n_groups)

    safe_n = np.where(n_above > 0, n_above, 1)
    mean = np.where(n_above > 0, sum_ab / safe_n, np.nan)
    var = sq_ab / safe_n - np.where(n_above > 0, mean * mean, 0.0)
    sd = np.sqrt(np.maximum(var, 0.0))

    spread = np.zeros(n_groups, dtype=np.float64)
    frac_spread = np.zeros(n_groups, dtype=np.float64)
    n_above_per_fov_mean = np.zeros(n_groups, dtype=np.float64)
    n_above_per_fov_spread = np.zeros(n_groups, dtype=np.float64)

    if per_fov_spread and agg.fov_codes.size:
        fov = agg.fov_codes
        n_fov = int(fov.max()) + 1
        comp = inv.astype(np.int64) * np.int64(n_fov) + fov.astype(np.int64)
        comp_above = comp[above]
        v_above = v[above]
        fov_total = np.bincount(comp, minlength=n_groups * n_fov).astype(np.int64).reshape(n_groups, n_fov)
        fov_n_above = (
            np.bincount(comp_above, minlength=n_groups * n_fov)
            .astype(np.int64)
            .reshape(n_groups, n_fov)
        )
        fov_sum_above = (
            np.bincount(comp_above, weights=v_above, minlength=n_groups * n_fov)
            .reshape(n_groups, n_fov)
        )
        present = fov_total > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            fov_mean = np.where(
                fov_n_above > 0, fov_sum_above / np.maximum(fov_n_above, 1), np.nan
            )
            fov_frac = np.where(
                present, fov_n_above / np.maximum(fov_total, 1), np.nan
            )

        for gi in range(n_groups):
            fm_row = fov_mean[gi]
            fm_valid = fm_row[np.isfinite(fm_row)]
            if fm_valid.size > 1:
                s = float(np.std(fm_valid, ddof=0))
                spread[gi] = s / math.sqrt(fm_valid.size) if use_sem else s

            ff_row = fov_frac[gi]
            ff_valid = ff_row[np.isfinite(ff_row)]
            if ff_valid.size > 1:
                s = float(np.std(ff_valid, ddof=0))
                frac_spread[gi] = s / math.sqrt(ff_valid.size) if use_sem else s

            fn_row = fov_n_above[gi][present[gi]]
            if fn_row.size >= 1:
                n_above_per_fov_mean[gi] = float(fn_row.mean())
            if fn_row.size > 1:
                s = float(np.std(fn_row.astype(np.float64), ddof=0))
                n_above_per_fov_spread[gi] = s / math.sqrt(fn_row.size) if use_sem else s
    else:
        if use_sem:
            with np.errstate(invalid="ignore"):
                sem_div = np.where(n_above > 1, np.sqrt(np.maximum(n_above, 1)), 1.0)
                spread = np.where(n_above > 1, sd / sem_div, 0.0)
        else:
            spread = np.where(n_above > 1, sd, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        frac_above = np.where(n_total > 0, n_above / np.maximum(n_total, 1), np.nan)

    result: List[AggPoint] = []
    timepoints = agg.timepoints
    for gi in range(n_groups):
        m = mean[gi]
        result.append((
            float(timepoints[gi]),
            float("nan") if math.isnan(m) else float(m),
            float(spread[gi]),
            float(frac_above[gi]),
            int(n_above[gi]),
            int(n_total[gi]),
            float(frac_spread[gi]),
            float(n_above_per_fov_mean[gi]),
            float(n_above_per_fov_spread[gi]),
        ))
    return result


def aggregate_with_threshold_cols(
    cols: WellColumns,
    threshold: float,
    *,
    use_sem: bool = False,
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
    per_fov_spread: bool = False,
    ratios: Optional[Dict[str, RatioMetric]] = None,
) -> List[AggPoint]:
    """Vectorized counterpart of ``aggregate_with_threshold``.

    Equivalent to ``stats_from_well_agg(build_well_agg(...))``; kept as a
    single-shot entry point for callers that don't cache the intermediate.
    """
    agg = build_well_agg(
        cols,
        val_col=val_col,
        cell_area_threshold=cell_area_threshold,
        fluor_gates=fluor_gates,
        ratios=ratios,
    )
    return stats_from_well_agg(agg, threshold, use_sem=use_sem, per_fov_spread=per_fov_spread)


def all_fluor_values_filtered_cols(
    cols: WellColumns,
    *,
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
    ratios: Optional[Dict[str, RatioMetric]] = None,
    tp_filter: Optional[float] = None,
) -> np.ndarray:
    """Vectorized counterpart of ``_all_fluor_values_filtered``.

    Returns a 1-D float64 ndarray; callers that want a Python list can call
    ``.tolist()``.
    """
    if cols.n_rows == 0:
        return np.zeros(0, dtype=np.float64)

    mask = _compute_gating_mask(cols, cell_area_threshold, fluor_gates)
    if not mask.any():
        return np.zeros(0, dtype=np.float64)

    val = _resolve_value_array(cols, val_col, ratios)
    mask &= np.isfinite(val)

    if tp_filter is not None:
        tp = _resolve_tp_hours_with_ordinals(cols)
        mask &= np.isfinite(tp) & (np.abs(tp - tp_filter) <= 1e-6)

    return val[mask]


def fluor_gates_signature(
    fluor_gates: Optional[Dict[str, float]],
) -> Tuple[Tuple[str, float], ...]:
    """Hashable signature for a fluor-gate dict (sorted by channel name)."""
    if not fluor_gates:
        return ()
    return tuple(sorted((str(k), float(v)) for k, v in fluor_gates.items()))


def ratio_signature(
    val_col: str,
    ratios: Optional[Dict[str, RatioMetric]],
) -> Tuple[Any, ...]:
    """Hashable signature for the ratio metric used by *val_col* (or empty)."""
    if not is_ratio_key(val_col) or not ratios:
        return ()
    rm = ratios.get(val_col)
    if rm is None:
        return ()
    return (val_col, rm.numerator_col(), rm.denominator_col(), float(rm.epsilon))
