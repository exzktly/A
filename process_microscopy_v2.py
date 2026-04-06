"""
process_microscopy.py
---------------------
Production-ready pipeline to segment nuclei with StarDist and quantify
GFP intensities per nucleus from paired fluorescence microscopy images.

Zip-file mode (default when --input_dir contains .zip files)
------------------------------------------------------------
Input zips must be named after 96-well plate positions, e.g.:
    A01.zip  A02.zip  ...  H12.zip

For each zip the script will:
  1. Validate the name against the 96-well plate pattern (A-H, 01-12).
  2. Extract contents to a temporary directory  <output_dir>/tmp_<well>/.
  3. Run the full segmentation + quantification pipeline on that directory,
     writing QC images to a per-zip staging area.
  4. Compress all output images (masks + overlays) into
         <output_dir>/<well>_out.zip
  5. Delete the temporary directories (extracted input + staged images).
  6. Per-well CSVs are written to <output_dir> as usual (not zipped).

If no .zip files are found in --input_dir the script falls back to the
original flat-directory behaviour.

Usage
-----
python process_microscopy.py \\
    --input_dir  /data/raw \\        # may contain A01.zip … H12.zip
    --output_dir /data/results \\
    --nuclear_token NIR \\
    --gfp_token GFP \\
    --tophat_radius_nir 100 \\
    --tophat_radius_gfp 100 \\
    --no_tophat_nir \\
    --no_tophat_gfp \\
    --no_save_masks \\
    --no_save_overlays \\
    --workers 4 \\
    --csv_prefix gfp_measurements

Filename convention (underscore-separated):
    <ExperimentName>_<Well>_<FOV>_<Timepoint>_NIR.tif
    e.g.  Exp01_B03_F001_T0001_NIR.tif
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

import tifffile                                      # noqa: F401  (side-effects)
from tifffile import imread, imwrite
import numpy as np
from scipy.ndimage import grey_opening
from skimage.segmentation import find_boundaries
import imageio.v3 as iio

# StarDist and csbdeep (which import TensorFlow) are intentionally NOT imported
# here at module level.  They are imported inside _worker_init, after the
# TF_NUM_INTRAOP/INTEROP_THREADS env vars have been set, so TF picks up the
# thread limits before it initialises its internal thread pools.

# ---------------------------------------------------------------------------
# Per-worker StarDist model (loaded once at worker startup, not per image)
# ---------------------------------------------------------------------------

_STARDIST_MODEL: "StarDist2D | None" = None


def _ensure_stardist_runtime_deps() -> None:
    """
    Fail fast with a clear message when StarDist runtime deps are missing.

    Without this preflight check, missing packages can cause worker startup
    failures that surface only as a generic BrokenProcessPool-style error.
    """
    missing: list[str] = []
    if importlib.util.find_spec("csbdeep") is None:
        missing.append("csbdeep")
    if importlib.util.find_spec("stardist") is None:
        missing.append("stardist")

    if missing:
        deps = ", ".join(missing)
        raise RuntimeError(
            "Missing required StarDist dependency package(s): "
            f"{deps}. Install them in this environment before running Analyze."
        )


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 96-well plate helpers
# ---------------------------------------------------------------------------

# Valid well names: A1/A01 – H12  (rows A-H, columns 1-12 or 01-12)
_WELL_RE = re.compile(r"^([A-Ha-h])(\d{1,2})$")


def is_valid_well_name(stem: str) -> bool:
    """Return True if *stem* (filename without extension) is a valid 96-well position."""
    m = _WELL_RE.match(stem)
    if not m:
        return False
    col = int(m.group(2))
    return 1 <= col <= 12


def find_well_zips(input_dir: Path) -> list[tuple[str, Path]]:
    """
    Scan *input_dir* (non-recursively) for .zip files whose stem matches a
    96-well plate position.

    Returns a list of (well_label, zip_path) sorted by well_label.
    Zips with non-plate names are logged as warnings and skipped.
    """
    found: list[tuple[str, Path]] = []
    skipped: list[Path] = []

    for p in sorted(input_dir.glob("*.zip")):
        if p.name.startswith("."):
            log.debug("Skipping hidden file: %s", p.name)
            continue
        if is_valid_well_name(p.stem):
            # Normalise to upper-case, zero-padded column: a1 → A01
            m = _WELL_RE.match(p.stem)
            well = f"{m.group(1).upper()}{int(m.group(2)):02d}"
            found.append((well, p))
        else:
            skipped.append(p)

    if skipped:
        log.warning(
            "%d zip file(s) skipped (name not a valid 96-well position):",
            len(skipped),
        )
        for p in skipped:
            log.warning("  %s", p.name)

    log.info("Found %d well zip file(s) in %s", len(found), input_dir)
    return found

# ---------------------------------------------------------------------------
# Zip extraction / compression helpers
# ---------------------------------------------------------------------------

def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Extract image members of *zip_path* flat into *dest_dir*.
    CSV files and other non-image files inside the zip are skipped so
    that outputs from a previous run packaged back into the input zip
    cannot interfere with the current run or end up re-zipped in output.
    """
    image_exts = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Strip any directory structure inside the zip; extract flat.
            member_name = Path(member.filename).name
            if not member_name:          # skip directory entries
                continue
            if member_name.startswith("."):
                skipped.append(member_name)
                continue
            if Path(member_name).suffix.lower() not in image_exts:
                skipped.append(member_name)
                continue
            target = dest_dir / member_name
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    if skipped:
        log.debug(
            "Skipped %d non-image file(s) in %s: %s",
            len(skipped), zip_path.name, ", ".join(skipped),
        )
    log.info("Extracted %s  ->  %s", zip_path.name, dest_dir)


def compress_images_to_zip(image_dir: Path, out_zip: Path) -> int:
    """
    Compress all image files (TIF/TIFF/PNG) found in *image_dir* into
    *out_zip*.  Returns the number of files added.
    CSV files and any other non-image files are explicitly excluded.
    """
    include_exts = {".tif", ".tiff", ".png"}
    exclude_exts = {".csv"}
    image_files = sorted(
        p for p in image_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in include_exts
        and p.suffix.lower() not in exclude_exts
    )

    if not image_files:
        log.warning("No image files found in %s to compress.", image_dir)
        return 0

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for img_path in image_files:
            zf.write(img_path, arcname=img_path.name)

    log.info(
        "Compressed %d image(s)  ->  %s", len(image_files), out_zip.name
    )
    return len(image_files)


def remove_directory(path: Path) -> None:
    """Remove *path* and all its contents, logging any errors."""
    try:
        shutil.rmtree(path)
        log.debug("Removed temporary directory: %s", path)
    except Exception as exc:          # noqa: BLE001
        log.warning("Could not remove %s: %s", path, exc)

# ---------------------------------------------------------------------------
# Filename schema helpers
# ---------------------------------------------------------------------------

#: Ordered list of recognised field names (the vocabulary for schema slots).
SCHEMA_FIELDS = ("experiment", "channel", "well", "fov", "timepoint", "ignore")

#: Default schema — matches the original hardcoded convention.
DEFAULT_SCHEMA = "experiment:channel:well:fov:timepoint"
DEFAULT_SEP    = "_"


def parse_schema(schema_str: str) -> list[str]:
    """
    Parse a colon-delimited schema string into a list of field names.

    Each token must be one of SCHEMA_FIELDS.  Unknown tokens are silently
    replaced with "ignore" so that old schema strings remain forward-compatible
    when new field names are added later.

    Example:
        "experiment:channel:well:fov:timepoint"
        -> ["experiment", "channel", "well", "fov", "timepoint"]
    """
    known = set(SCHEMA_FIELDS)
    return [
        tok if tok in known else "ignore"
        for tok in schema_str.strip().split(":")
        if tok  # skip empty tokens from trailing colons etc.
    ]


def validate_schema(schema: list[str]) -> list[str]:
    """
    Return a list of human-readable error messages for *schema*.
    An empty list means the schema is valid.

    Rules:
      • "channel" must appear exactly once.
      • "well"    must appear exactly once.
    """
    errors: list[str] = []
    if schema.count("channel") != 1:
        errors.append(
            f'"channel" must appear exactly once in the schema '
            f'(found {schema.count("channel")}).'
        )
    if schema.count("well") != 1:
        errors.append(
            f'"well" must appear exactly once in the schema '
            f'(found {schema.count("well")}).'
        )
    return errors


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def _parse_timepoint_hours(tp: str) -> float:
    """
    Convert a timepoint string to fractional hours.
    Returns float("nan") when the string cannot be parsed at all.

    Formats tried in order:
      1. DDdHHhMMm  e.g. "02d04h30m" -> 52.5  (full or partial components)
      2. Standalone unit suffix  e.g. "48h" -> 48.0, "2d" -> 48.0, "30m" -> 0.5
      3. Pure number  e.g. "48" or "1.5" -> treated as hours
      4. Prefixed ordinal  e.g. "T01", "t3", "day2", "D02" -> ordinal value
         (strip leading non-digit chars, use the numeric part as a plain
          index so relative ordering is preserved)
    """
    s = tp.strip()
    if not s:
        return float("nan")

    # 1. Full DDdHHhMMm (all components optional, but at least one required)
    m = re.fullmatch(
        r"(?:(\d{1,4})d)?(?:(\d{1,2})h)?(?:(\d{1,2})m)?",
        s, re.IGNORECASE,
    )
    if m and any(m.groups()):
        days  = int(m.group(1) or 0)
        hours = int(m.group(2) or 0)
        mins  = int(m.group(3) or 0)
        return days * 24.0 + hours + mins / 60.0

    # 2. Standalone unit: "48h", "2d", "30m", "90min"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(h(?:ours?)?|d(?:ays?)?|m(?:in(?:utes?)?)?)",
                     s, re.IGNORECASE)
    if m:
        val  = float(m.group(1))
        unit = m.group(2)[0].lower()
        if unit == "h":
            return val
        if unit == "d":
            return val * 24.0
        if unit == "m":
            return val / 60.0

    # 3. Pure number (treat as hours)
    try:
        return float(s)
    except ValueError:
        pass

    # 4. Prefixed ordinal: strip leading non-digit characters, keep the number.
    #    e.g. "T01" -> 1.0, "day02" -> 2.0, "tp_3" -> 3.0
    m = re.search(r"(\d+(?:\.\d+)?)$", s)
    if m:
        return float(m.group(1))

    return float("nan")


def parse_filename(
    path: "Path | str",
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> dict:
    """
    Decompose a filename into metadata fields using a user-supplied schema.

    Parameters
    ----------
    path   : Path or str — file path or bare stem.
    schema : ordered list of field names from SCHEMA_FIELDS.
             Defaults to the legacy 5-slot convention
             ["experiment", "channel", "well", "fov", "timepoint"].
    sep    : separator character used to split the filename stem.
             Defaults to "_".

    The stem is split on *sep* and each token is assigned to the
    corresponding schema field.  Slots labelled "ignore" are consumed but
    not stored.  If the stem has fewer tokens than schema slots the missing
    fields default to "" (or NaN for timepoint_hours).

    Returns a dict with keys:
        filename, experiment, channel, well, fov,
        timepoint, timepoint_hours
    (always present; empty / NaN when absent from the schema or filename).
    """
    if schema is None:
        schema = parse_schema(DEFAULT_SCHEMA)

    p    = Path(path) if not isinstance(path, Path) else path
    stem = p.stem if p.suffix else str(path)
    parts = stem.split(sep)

    # Build result with all known non-ignore fields defaulted to "".
    result: dict = {
        "filename":        p.name if p.suffix else str(path),
        "experiment":      "",
        "channel":         "",
        "well":            "",
        "fov":             "",
        "timepoint":       "",
        "timepoint_hours": float("nan"),
    }

    for i, field in enumerate(schema):
        if field == "ignore":
            continue
        token = parts[i] if i < len(parts) else ""
        if field == "timepoint":
            result["timepoint"]       = token
            result["timepoint_hours"] = _parse_timepoint_hours(token)
        else:
            result[field] = token

    return result

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def load_2d_gray(path: Path) -> np.ndarray:
    """Load a TIFF (or other format) as a 2-D float32 array."""
    img = imread(str(path))
    while img.ndim > 2:
        img = img[0]
    return img.astype(np.float32)


def apply_tophat(image: np.ndarray, radius: int) -> np.ndarray:
    """Return white top-hat corrected image (background subtraction).

    Uses scipy.ndimage.grey_closing with a square (2*radius+1) structuring
    element.  A square footprint enables separable 1D decomposition inside
    scipy, giving O(radius) complexity per pixel instead of the O(radius²)
    of skimage's disk-based morphology.  For radius=50 on a 900×900 image
    this is ~100× faster than the skimage disk path with negligible
    difference in background-subtraction quality for typical fluorescence
    images where the background varies slowly.
    """
    img = image.astype(np.float32)
    size = 2 * radius + 1                      # side length of the square
    background = grey_opening(img, size=(size, size))   # opening = erosion→dilation
    return img - background                    # always ≥ 0 (opening is anti-extensive)


def save_overlay(nir_raw: np.ndarray, labels: np.ndarray, out_path: Path) -> None:
    """Save an 8-bit RGB PNG with nucleus boundaries drawn in red."""
    mn, mx = nir_raw.min(), nir_raw.max()
    grey = ((nir_raw - mn) / (mx - mn) * 255).astype(np.uint8) if mx > mn \
           else np.zeros_like(nir_raw, dtype=np.uint8)
    rgb = np.stack([grey, grey, grey], axis=-1)
    boundaries = find_boundaries(labels, mode="outer")
    rgb[boundaries, 0] = 255
    rgb[boundaries, 1] = 0
    rgb[boundaries, 2] = 0
    iio.imwrite(str(out_path), rgb)

# ---------------------------------------------------------------------------
# Per-image worker (runs in a subprocess)
# ---------------------------------------------------------------------------

def process_image_group(
    nuclear_path: Path,
    fluor_paths: "list[Path]",
    fluor_tokens: "list[str]",
    output_dir: Path,
    nuclear_token: str,
    tophat_nir: bool,
    tophat_radius_nir: int,
    tophat_fluor: "list[bool]",
    tophat_radius_fluor: "list[int]",
    save_masks: bool,
    save_overlays: bool,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> list[dict]:
    """
    Process one nuclear image together with an arbitrary number of fluorescent
    channel images.  Returns a list of per-nucleus measurement dicts.

    *fluor_paths*        : one Path per fluorescent channel (same order as
                           *fluor_tokens*).
    *fluor_tokens*       : channel token strings (e.g. ["GFP", "mCherry"]).
    *tophat_fluor*       : per-channel top-hat enable flags.
    *tophat_radius_fluor*: per-channel top-hat radii.

    Output CSV columns for each fluor channel are prefixed with the lower-cased
    token, e.g. "gfp_total_intensity", "mcherry_mean_intensity".
    """
    from csbdeep.utils import normalize
    log.info("Processing %s  (%d fluor channel(s): %s)",
             nuclear_path.name, len(fluor_paths), ", ".join(fluor_tokens))

    _t = time.perf_counter()
    nir_raw = load_2d_gray(nuclear_path)
    log.info("  load nuclear: %.1f s  (shape %s)", time.perf_counter() - _t, nir_raw.shape)

    # Load every fluorescent channel and verify shape consistency.
    fluor_raws: list[np.ndarray] = []
    for fp in fluor_paths:
        _t = time.perf_counter()
        img = load_2d_gray(fp)
        if img.shape != nir_raw.shape:
            raise ValueError(
                f"Shape mismatch: nuclear {nir_raw.shape} vs "
                f"{fp.name} {img.shape}"
            )
        fluor_raws.append(img)
        log.info("  load fluor:  %.1f s  %s", time.perf_counter() - _t, fp.name)

    # Top-hat on nuclear channel.
    _t = time.perf_counter()
    nir_corr = apply_tophat(nir_raw, tophat_radius_nir) if tophat_nir else nir_raw.copy()
    log.info("  tophat_nir:  %.1f s  (radius %d, enabled=%s)",
             time.perf_counter() - _t, tophat_radius_nir, tophat_nir)

    # Top-hat on each fluorescent channel.
    fluor_corr: list[np.ndarray] = []
    for i, (fraw, do_th, radius) in enumerate(
            zip(fluor_raws, tophat_fluor, tophat_radius_fluor)):
        _t = time.perf_counter()
        fc = apply_tophat(fraw, radius) if do_th else fraw.copy()
        fluor_corr.append(fc)
        log.info("  tophat_%s:  %.1f s  (radius %d, enabled=%s)",
                 fluor_tokens[i].lower(), time.perf_counter() - _t, radius, do_th)

    # StarDist segmentation on the nuclear channel.
    _t = time.perf_counter()
    nir_norm = normalize(nir_corr, 1, 99.8)
    log.info("  normalize:   %.1f s", time.perf_counter() - _t)

    if _STARDIST_MODEL is None:
        raise RuntimeError(
            "StarDist model is not initialised. "
            "Ensure _worker_init ran before process_image_group."
        )
    _t = time.perf_counter()
    labels, _ = _STARDIST_MODEL.predict_instances(nir_norm)
    labels = labels.astype(np.int32)
    log.info("  stardist:    %.1f s  (%d nuclei detected)",
             time.perf_counter() - _t, len(np.unique(labels)) - 1)

    # Save QC images.
    stem      = nuclear_path.stem
    base_name = stem.replace(nuclear_token, "")

    _t = time.perf_counter()
    th_nir_path = output_dir / f"{base_name}_tophat_nir.tif"
    imwrite(str(th_nir_path), np.clip(nir_corr, 0, None).astype(np.float32))
    for fc, tok in zip(fluor_corr, fluor_tokens):
        th_path = output_dir / f"{base_name}_tophat_{tok.lower()}.tif"
        imwrite(str(th_path), np.clip(fc, 0, None).astype(np.float32))
    log.info("  tophat tifs written")
    if save_masks:
        imwrite(str(output_dir / f"{base_name}_labels.tif"), labels)
    if save_overlays:
        save_overlay(nir_raw, labels, output_dir / f"{base_name}_overlay.png")
    log.info("  save:        %.1f s", time.perf_counter() - _t)

    # Quantify each nucleus across all fluorescent channels.
    meta    = parse_filename(nuclear_path, schema=schema, sep=sep)
    nuc_ids = np.unique(labels)
    nuc_ids = nuc_ids[nuc_ids != 0]

    _t = time.perf_counter()
    records: list[dict] = []
    for nid in nuc_ids:
        mask = labels == nid
        rec: dict = {
            **meta,
            "nucleus_id": int(nid),
            "area_px":    int(mask.sum()),
        }
        for fc, tok in zip(fluor_corr, fluor_tokens):
            px  = fc[mask]
            pfx = tok.lower()
            rec[f"{pfx}_total_intensity"] = float(px.sum())
            rec[f"{pfx}_mean_intensity"]  = float(px.mean())
            rec[f"{pfx}_max_intensity"]   = float(px.max())
            rec[f"{pfx}_min_intensity"]   = float(px.min())
            rec[f"{pfx}_std_intensity"]   = float(px.std())
        records.append(rec)
    log.info("  quantify:    %.1f s  (%d nuclei)", time.perf_counter() - _t, len(records))

    return records

# ---------------------------------------------------------------------------
# Directory scan
# ---------------------------------------------------------------------------

def find_image_groups(
    input_dir: Path,
    nuclear_token: str,
    fluor_tokens: "list[str]",
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> "list[tuple[Path, list[Path]]]":
    """
    Recursively scan *input_dir* for nuclear-channel files and locate all
    fluorescent-channel counterparts for each.

    Returns a list of (nuclear_path, [fluor_path, ...]) tuples where the
    nuclear file and every fluorescent file exist on disk.  Groups where any
    fluorescent channel is missing are skipped with a warning.

    Channel identification uses the schema's "channel" slot for position-aware
    matching.  Falls back to substring replacement when no "channel" slot exists.
    """
    if schema is None:
        schema = parse_schema(DEFAULT_SCHEMA)

    extensions = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    groups: "list[tuple[Path, list[Path]]]" = []
    incomplete: list[Path] = []

    channel_idx: "int | None" = (
        schema.index("channel") if "channel" in schema else None
    )

    def _derive_fluor_path(nuclear_path: Path, fluor_token: str) -> Path:
        """Return the expected path for one fluorescent channel file."""
        if channel_idx is not None:
            parts = nuclear_path.stem.split(sep)
            parts[channel_idx] = fluor_token
            return nuclear_path.parent / (sep.join(parts) + nuclear_path.suffix)
        # Legacy fallback: simple substring replacement.
        return nuclear_path.parent / nuclear_path.name.replace(
            nuclear_token, fluor_token
        )

    for path in sorted(input_dir.rglob("*")):
        if path.name.startswith("."):
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue

        # Filter to nuclear channel files only.
        if channel_idx is not None:
            stem_parts = path.stem.split(sep)
            if channel_idx >= len(stem_parts):
                continue
            if stem_parts[channel_idx] != nuclear_token:
                continue
        else:
            if nuclear_token not in path.name:
                continue

        # Build the expected path for each fluorescent channel.
        fluor_paths = [_derive_fluor_path(path, tok) for tok in fluor_tokens]
        missing = [fp for fp in fluor_paths if not fp.exists()]
        if missing:
            incomplete.append(path)
            for fp in missing:
                log.warning("  missing fluor file: %s", fp.name)
        else:
            groups.append((path, fluor_paths))

    if incomplete:
        log.warning(
            "%d nuclear file(s) skipped due to missing fluorescent channel(s):",
            len(incomplete),
        )
        for p in incomplete:
            log.warning("  %s", p.name)

    log.info(
        "Found %d image group(s) in %s  (%d fluor channel(s): %s)",
        len(groups), input_dir, len(fluor_tokens), ", ".join(fluor_tokens),
    )
    return groups


# Backward-compatible alias kept for any external callers.
def find_image_pairs(
    input_dir: Path,
    nuclear_token: str,
    gfp_token: str,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> "list[tuple[Path, Path]]":
    """Deprecated alias for find_image_groups with a single fluor channel."""
    groups = find_image_groups(
        input_dir, nuclear_token, [gfp_token], schema=schema, sep=sep
    )
    return [(nuc, fluors[0]) for nuc, fluors in groups]

# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def _safe_well(label: str) -> str:
    """Sanitise a well label for use as a filename component."""
    return label.replace("/", "_").replace("\\", "_")

def _write_single_csv(records: list[dict], out_path: Path) -> None:
    import csv
    fieldnames = list(records[0].keys())
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_csvs_per_well(
    all_records: list[dict],
    output_dir: Path,
    csv_prefix: str,
) -> None:
    """Write one CSV per well, partitioned by the 'well' metadata field."""
    if not all_records:
        log.warning("No records to write; no per-well CSVs produced.")
        return

    from collections import defaultdict
    by_well: dict[str, list[dict]] = defaultdict(list)
    for rec in all_records:
        well = rec.get("well") or "unknown_well"
        by_well[well].append(rec)

    for well, records in sorted(by_well.items()):
        safe_well = _safe_well(well)
        out_path  = output_dir / f"{csv_prefix}_{safe_well}.csv"
        _write_single_csv(records, out_path)
        log.info("Well %-12s -> %s  (%d rows)", well, out_path.name, len(records))

# ---------------------------------------------------------------------------
# Worker initialiser
# ---------------------------------------------------------------------------

def _worker_init(force_cpu: bool = False, threads_per_worker: int = 0) -> None:
    """
    Called once in each worker process before any image pairs are processed.

    *force_cpu*          When True, forces StarDist onto CPU regardless of
                         platform.  When False, the effective device is chosen
                         automatically:
                           macOS  -> Metal GPU via tensorflow-metal if installed,
                                     otherwise CPU.
                           Other  -> CPU only (CUDA available if a CUDA-enabled
                                     TF build is installed and force_cpu=False).
    *threads_per_worker* CPU threads per worker for TF/BLAS inference.

    Platform logic
    --------------
    On macOS, tensorflow-metal registers Metal as a GPU device automatically.
    Calling tf.config.set_visible_devices([], "GPU") disables Metal too (not
    just CUDA) so we must NOT call it on macOS unless --cpu_only is set.
    On all other platforms we default to CPU to avoid unexpected CUDA usage.
    """
    import sys as _sys
    global _STARDIST_MODEL

    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

    # Determine effective device policy before any TF import.
    _on_mac        = _sys.platform == "darwin"
    _effective_cpu = force_cpu or (not _on_mac)

    if threads_per_worker > 0:
        # Pin CPU thread pools before any library imports.
        t = str(threads_per_worker)
        os.environ["OMP_NUM_THREADS"]        = t
        os.environ["OPENBLAS_NUM_THREADS"]   = t
        os.environ["MKL_NUM_THREADS"]        = t
        os.environ["NUMEXPR_NUM_THREADS"]    = t
        os.environ["TF_NUM_INTRAOP_THREADS"] = t
        os.environ["TF_NUM_INTEROP_THREADS"] = t

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  [worker %(process)d]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Device note for logging ────────────────────────────────────────────────
    if force_cpu:
        device_note = "CPU-only (--cpu_only)"
    elif _on_mac:
        device_note = "Metal GPU (macOS) if tensorflow-metal installed, else CPU"
    else:
        device_note = "CPU-only (non-macOS default)"
    thr_note = (f"{threads_per_worker} TF thread(s)" if threads_per_worker > 0
                else "TF default threads")
    log.info("Worker %d loading StarDist (%s, %s).", os.getpid(), device_note, thr_note)

    # Import StarDist and its TF dependency HERE, after env vars are set.
    # This is the first point in the worker where TF is allowed to initialise.
    from csbdeep.utils import normalize as _normalize   # noqa: F401 — triggers TF init
    from stardist.models import StarDist2D as _StarDist2D

    # Disable GPU on non-Mac platforms (or when --cpu_only is set).
    # On macOS we leave GPU visible so tensorflow-metal can use Metal.
    if _effective_cpu:
        import tensorflow as tf
        tf.config.set_visible_devices([], "GPU")

    _t0 = time.perf_counter()
    # from_pretrained downloads the model weights via urllib if they are not
    # already cached locally (~/.keras/models/).  On machines where the SSL
    # certificate store cannot be verified (e.g. corporate proxies, some HPC
    # clusters) this raises an SSL error.  The override below disables
    # certificate verification for this one call only; the original context
    # factory is restored immediately in the finally block so no other network
    # code in the worker is affected.
    import ssl as _ssl
    _orig_ssl_ctx = _ssl._create_default_https_context
    _ssl._create_default_https_context = _ssl._create_unverified_context
    try:
        _STARDIST_MODEL = _StarDist2D.from_pretrained("2D_versatile_fluo")
    finally:
        _ssl._create_default_https_context = _orig_ssl_ctx
    log.info("Worker %d model loaded in %.1f s.", os.getpid(), time.perf_counter() - _t0)

# ---------------------------------------------------------------------------
# Well-level task functions (run inside worker processes)
# ---------------------------------------------------------------------------

def _process_groups_in_worker(
    groups: "list[tuple[Path, list[Path]]]",
    shared_kwargs: dict,
    well_label: str,
    fov_threads: int = 1,
) -> "tuple[list[dict], list[str]]":
    """
    Process all image groups for one well within a single worker process.

    Each group is (nuclear_path, [fluor_path, ...]).  StarDist is already
    loaded by _worker_init, so the model is reused across every group.

    *fov_threads* controls concurrent FOV processing via ThreadPoolExecutor.
    fov_threads=1 (default) is safe for any backend; >1 benefits multi-core CPU.

    Returns (records, failed_names).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

    fov_threads = shared_kwargs.pop("_fov_threads", fov_threads)
    kwargs = {k: v for k, v in shared_kwargs.items() if not k.startswith("_")}

    all_records: list[dict] = []
    failed:      list[str]  = []

    def _run_group(nuclear_path: Path, fluor_paths: "list[Path]") -> "list[dict]":
        _t0 = time.perf_counter()
        recs = process_image_group(nuclear_path, fluor_paths, **kwargs)
        log.info("FOV %s processed in %.1f s (%d nuclei)",
                 nuclear_path.name, time.perf_counter() - _t0, len(recs))
        for r in recs:
            r["well"] = well_label
        return recs

    if fov_threads == 1 or len(groups) == 1:
        for nuclear_path, fluor_paths in groups:
            try:
                all_records.extend(_run_group(nuclear_path, fluor_paths))
            except Exception as exc:           # noqa: BLE001
                log.error("FAILED %s: %s", nuclear_path.name, exc, exc_info=True)
                failed.append(nuclear_path.name)
    else:
        with ThreadPoolExecutor(max_workers=fov_threads) as tex:
            future_map = {
                tex.submit(_run_group, nuc, fluors): nuc
                for nuc, fluors in groups
            }
            for fut in _as_completed(future_map):
                nuclear_path = future_map[fut]
                try:
                    all_records.extend(fut.result())
                except Exception as exc:       # noqa: BLE001
                    log.error("FAILED %s: %s", nuclear_path.name, exc, exc_info=True)
                    failed.append(nuclear_path.name)

    return all_records, failed


def process_well_zip_task(
    well_label: str,
    zip_path: Path,
    output_dir: Path,
    shared_kwargs_template: dict,
    nuclear_token: str,
    fluor_tokens: "list[str]",
    csv_prefix: str,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> "tuple[list[dict], list[str]]":
    """
    Top-level picklable task: full lifecycle for one zipped well.

    Runs inside a worker process (StarDist already loaded by _worker_init).
    1. Extract zip to a temporary directory.
    2. Discover image groups (nuclear + all fluor channels) and process them.
    3. Write the per-well CSV.
    4. Compress output images to <output_dir>/<well>_out.zip.
    5. Remove temporary directories.

    Returns (records, failed_names).
    """
    if schema is None:
        schema = parse_schema(DEFAULT_SCHEMA)
    log.info("Well %s — starting (pid %d)", well_label, os.getpid())
    tmp_extract = output_dir / f"_tmp_extract_{well_label}"
    tmp_images  = output_dir / f"_tmp_images_{well_label}"

    # Remove any stale directories left by a previous crashed run before
    # creating fresh ones, so we never process stale files.
    for _stale in (tmp_extract, tmp_images):
        if _stale.exists():
            log.warning("Well %s: removing stale tmp dir %s", well_label, _stale.name)
            remove_directory(_stale)

    try:
        tmp_extract.mkdir(parents=True, exist_ok=True)
        tmp_images.mkdir(parents=True,  exist_ok=True)

        extract_zip(zip_path, tmp_extract)

        groups = find_image_groups(tmp_extract, nuclear_token, fluor_tokens,
                                   schema=schema, sep=sep)
        if not groups:
            log.warning("Well %s: no image groups found after extraction.", well_label)
            return [], []

        kwargs = {**shared_kwargs_template, "output_dir": tmp_images}
        records, failed = _process_groups_in_worker(groups, kwargs, well_label)

        if records:
            safe_well = _safe_well(well_label)
            csv_path  = output_dir / f"{csv_prefix}_{safe_well}.csv"
            _write_single_csv(records, csv_path)
            log.info("Well %-12s -> %s  (%d rows)", well_label, csv_path.name, len(records))
        else:
            log.warning("Well %s: no records produced; CSV not written.", well_label)

        out_zip = output_dir / f"{well_label}_out.zip"
        n_compressed = compress_images_to_zip(tmp_images, out_zip)
        log.info("Well %s: %d image(s) -> %s", well_label, n_compressed, out_zip.name)

        return records, failed

    finally:
        remove_directory(tmp_extract)
        remove_directory(tmp_images)
        log.info("Well %s — temporary directories removed.", well_label)


def process_well_flat_task(
    well_label: str,
    groups: "list[tuple[Path, list[Path]]]",
    shared_kwargs: dict,
) -> "tuple[list[dict], list[str]]":
    """
    Top-level picklable task: process all image groups for one flat-mode well.

    Runs inside a worker process (StarDist already loaded by _worker_init).
    Returns (records, failed_names).
    """
    log.info("Well %s — starting flat-mode (pid %d, %d group(s))",
             well_label, os.getpid(), len(groups))
    return _process_groups_in_worker(groups, shared_kwargs, well_label)

# ---------------------------------------------------------------------------
# Well-level pool dispatcher (replaces run_pipeline_on_directory)
# ---------------------------------------------------------------------------

def run_pipeline_on_wells(
    wells: "list[tuple[str, list[tuple[Path, Path]]]]",
    shared_kwargs: dict,
    workers: int,
    force_cpu: bool = False,
    threads_per_worker: int = 0,
    task_fn = None,
) -> "tuple[list[dict], list[str]]":
    """
    Submit one worker task per well and collect results.

    *wells*: list of (well_label, pairs) — pairs is a list of (nir, gfp) Paths.
    *threads_per_worker*: passed to _worker_init to pin TF/BLAS thread counts.
    *task_fn*: callable(well_label, pairs, shared_kwargs) -> (records, failed).
               Defaults to process_well_flat_task.
    """
    if task_fn is None:
        task_fn = process_well_flat_task

    _ensure_stardist_runtime_deps()

    all_records: list[dict] = []
    all_failed:  list[str]  = []

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_worker_init,
        initargs=(force_cpu, threads_per_worker),
    ) as executor:
        future_to_well = {
            executor.submit(task_fn, well_label, pairs, shared_kwargs): well_label
            for well_label, pairs in wells
        }
        for future in as_completed(future_to_well):
            well_label = future_to_well[future]
            try:
                records, failed = future.result()
                all_records.extend(records)
                all_failed.extend(failed)
            except Exception as exc:           # noqa: BLE001
                log.error("FAILED well %s: %s", well_label, exc, exc_info=True)
                all_failed.append(well_label)

    return all_records, all_failed

# ---------------------------------------------------------------------------
# Legacy shim kept for backward compatibility
# ---------------------------------------------------------------------------

def run_pipeline_on_directory(
    input_dir: Path,
    output_dir: Path,
    shared_kwargs: dict,
    nuclear_token: str,
    fluor_tokens: "list[str]",
    workers: int,
    skip_wells: "set[str] | None" = None,
    force_cpu: bool = False,
    threads_per_worker: int = 0,
    groups: "list[tuple[Path, list[Path]]] | None" = None,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> "tuple[list[dict], list[str]]":
    """
    Flat-directory entry point: group image groups by well, then run one worker per well.

    *groups* may be passed in if already discovered (avoids a second directory scan).
    """
    if schema is None:
        schema = parse_schema(DEFAULT_SCHEMA)
    if groups is None:
        groups = find_image_groups(input_dir, nuclear_token, fluor_tokens,
                                   schema=schema, sep=sep)
    if not groups:
        log.warning("No valid image groups found in %s.", input_dir)
        return [], []

    from collections import defaultdict
    by_well: dict[str, list] = defaultdict(list)
    for nuc, fluors in groups:
        tok = _well_token_from_path(nuc, nuclear_token, schema=schema, sep=sep) or "unknown"
        by_well[tok].append((nuc, fluors))

    # Filter already-complete wells
    if skip_wells:
        before = len(by_well)
        by_well = {w: p for w, p in by_well.items() if w not in skip_wells}
        n_removed = before - len(by_well)
        if n_removed:
            log.info("Skipped %d already-complete well(s).", n_removed)
        if not by_well:
            log.info("All wells already complete; nothing to do.")
            return [], []

    wells = sorted(by_well.items())
    log.info("Flat mode: %d well(s), %d worker(s).", len(wells), workers)

    return run_pipeline_on_wells(
        wells=wells,
        shared_kwargs={**shared_kwargs, "output_dir": output_dir},
        workers=workers,
        force_cpu=force_cpu,
        threads_per_worker=threads_per_worker,
    )

# ---------------------------------------------------------------------------
# Skip-detection helpers
# ---------------------------------------------------------------------------

def _well_token_from_path(
    nir_path: Path,
    nuclear_token: str,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> str:
    """Extract the well token from an image filename, or return empty string."""
    return parse_filename(nir_path, schema=schema, sep=sep)["well"]


def output_exists_for_well(output_dir: Path, well_label: str, csv_prefix: str) -> bool:
    """
    Return True if processable output already exists for *well_label*.

    Both outputs must be present and non-empty to count as complete:
      • <output_dir>/<well>_out.zip       – compressed QC images
      • <output_dir>/<csv_prefix>_<well>.csv – per-well measurements

    This prevents re-processing wells that completed successfully in a prior
    run while still allowing partially-completed wells to be retried.
    """
    safe_well = _safe_well(well_label)
    out_zip  = output_dir / f"{well_label}_out.zip"
    csv_path = output_dir / f"{csv_prefix}_{safe_well}.csv"
    zip_ok = out_zip.exists()  and out_zip.stat().st_size  > 0
    csv_ok = csv_path.exists() and csv_path.stat().st_size > 0
    return zip_ok and csv_ok


def output_exists_for_well_flat(output_dir: Path, well_label: str, csv_prefix: str) -> bool:
    """
    Return True if a per-well CSV already exists for *well_label* (flat mode).

    In flat mode there is no output zip; only the CSV is checked.
    """
    safe_well = _safe_well(well_label)
    csv_path  = output_dir / f"{csv_prefix}_{safe_well}.csv"
    return csv_path.exists() and csv_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Zip-aware orchestration
# ---------------------------------------------------------------------------

def process_well_zips(
    input_dir: Path,
    output_dir: Path,
    well_zips: "list[tuple[str, Path]]",
    shared_kwargs_template: dict,
    nuclear_token: str,
    fluor_tokens: "list[str]",
    workers: int,
    csv_prefix: str,
    force: bool = False,
    force_cpu: bool = False,
    threads_per_worker: int = 0,
    schema: "list[str] | None" = None,
    sep: str = DEFAULT_SEP,
) -> None:
    """
    Dispatch one worker process per well zip.

    Each worker: extracts its zip, processes all image pairs sequentially
    (StarDist loaded once), writes the CSV, compresses QC images, and cleans up.
    Up to *workers* wells are processed in parallel.
    """
    if schema is None:
        schema = parse_schema(DEFAULT_SCHEMA)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sweep any stale _tmp_extract_* / _tmp_images_* dirs left by a previous
    # crashed run before spawning new workers, so disk space is reclaimed early.
    for _stale in sorted(output_dir.glob("_tmp_extract_*")) + sorted(output_dir.glob("_tmp_images_*")):
        if _stale.is_dir():
            log.warning("Removing stale temporary directory from previous run: %s", _stale.name)
            remove_directory(_stale)

    # Skip already-complete wells unless --force
    n_skipped = 0
    to_process: list[tuple[str, Path]] = []
    for well_label, zip_path in well_zips:
        if not force and output_exists_for_well(output_dir, well_label, csv_prefix):
            log.info(
                "SKIP well %s — output already exists. Use --force to reprocess.",
                well_label,
            )
            n_skipped += 1
        else:
            to_process.append((well_label, zip_path))

    if not to_process:
        log.info("All wells already complete.")
        log.info("Zip mode complete. %d skipped.", n_skipped)
        return

    _ensure_stardist_runtime_deps()

    log.info("Zip mode: %d well(s) to process, %d worker(s).", len(to_process), workers)

    # Submit one worker per well zip directly.
    all_records: list[dict] = []
    all_failed:  list[str]  = []

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_worker_init,
        initargs=(force_cpu, threads_per_worker),
    ) as executor:
        future_to_well = {
            executor.submit(
                process_well_zip_task,
                well_label,
                zip_path,
                output_dir,
                shared_kwargs_template,
                nuclear_token,
                fluor_tokens,
                csv_prefix,
                schema,
                sep,
            ): well_label
            for well_label, zip_path in to_process
        }
        for future in as_completed(future_to_well):
            well_label = future_to_well[future]
            try:
                records, failed = future.result()
                all_records.extend(records)
                all_failed.extend(failed)
            except Exception as exc:           # noqa: BLE001
                log.error("FAILED well %s: %s", well_label, exc, exc_info=True)
                all_failed.append(well_label)

    log.info("=" * 60)
    log.info("Zip mode complete.")
    log.info(
        "Total wells : %d  |  processed : %d  |  skipped : %d  |  "
        "nuclei : %d  |  failed wells : %d",
        len(well_zips), len(to_process), n_skipped,
        len(all_records), len(all_failed),
    )
    if all_failed:
        log.warning("Failed wells/pairs:")
        for name in all_failed:
            log.warning("  %s", name)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Parallel StarDist nuclei segmentation + GFP quantification. "
            "Accepts a flat directory of images OR a directory of per-well "
            "zip files named after 96-well plate positions (A01.zip … H12.zip)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument("--input_dir",  type=Path, required=True,
                   help="Directory of images or per-well zip files")
    p.add_argument("--output_dir", type=Path, default=Path("results"),
                   help="Destination for CSVs, masks, overlays, and output zips")

    p.add_argument("--nuclear_token", default="NIR",
                   help="Channel token identifying nuclear-channel files "
                        "(used for segmentation only, not quantified)")
    p.add_argument("--fluor_tokens", nargs="+", default=["GFP"],
                   metavar="TOKEN",
                   help="One or more channel tokens identifying fluorescent "
                        "channels to quantify (e.g. GFP mCherry DAPI). "
                        "Each token produces its own intensity columns in the CSV.")

    p.add_argument("--filename_schema", default=DEFAULT_SCHEMA,
                   help=(
                       "Colon-separated ordered field names describing the "
                       "filename structure.  Each token must be one of: "
                       + ", ".join(SCHEMA_FIELDS) + ".  "
                       "'channel' and 'well' must each appear exactly once.  "
                       "Slots whose content is not needed should be labelled "
                       "'ignore'.  "
                       f"Default: '{DEFAULT_SCHEMA}' matches the convention "
                       "Exp01_NIR_B03_F001_02d04h30m.tif"
                   ))
    p.add_argument("--filename_sep", default=DEFAULT_SEP,
                   help=(
                       "Single character that separates fields in image "
                       f"filenames.  Default: '{DEFAULT_SEP}'"
                   ))

    p.add_argument("--tophat_radius_nir", type=int, default=100,
                   help="Top-hat structuring element radius for the nuclear "
                        "channel (pixels)")
    p.add_argument("--tophat_radius_fluor", type=int, default=100,
                   help="Top-hat structuring element radius applied to every "
                        "fluorescent channel (pixels)")
    p.add_argument("--no_tophat_nir", action="store_true",
                   help="Disable white top-hat on the nuclear channel")
    p.add_argument("--no_tophat_fluor", action="store_true",
                   help="Disable white top-hat on all fluorescent channels")

    p.add_argument("--no_save_masks",    action="store_true",
                   help="Do not save label-mask TIFFs")
    p.add_argument("--no_save_overlays", action="store_true",
                   help="Do not save red-outline overlay PNGs")

    p.add_argument("--tf_threads", type=int, default=0,
                   help=(
                       "CPU threads per worker for TensorFlow/BLAS inference. "
                       "0 (default) = auto-select based on cpu_count (always 4). "
                       "Common values: "
                       "4  = default, suits most x86 CPUs (≤32 cores); "
                       "8  = for CPUs with large L3 caches (e.g. EPYC, Xeon Scalable) "
                       "     where inference scales beyond 4 threads; "
                       "16 = for very wide-cache server CPUs where per-image "
                       "     throughput still improves at 16 threads "
                       "(workers = cpu_count // tf_threads in all cases). "
                       "Ignored when running on GPU (--cpu_only not set)."
                   ))
    p.add_argument(
        "--workers",
        type=int,
        default=0,
        help=(
            "Number of parallel worker processes. "
            "0 (default) = auto-select from CPU availability and tf_threads."
        ),
    )

    p.add_argument("--csv_prefix", default="gfp_measurements",
                   help="Filename prefix for per-well CSVs (<prefix>_<well>.csv)")

    p.add_argument("--force", action="store_true",
                   help=(
                       "Reprocess all wells even if output already exists. "
                       "By default, any well whose <well>_out.zip and "
                       "<csv_prefix>_<well>.csv are both present is skipped."
                   ))

    p.add_argument("--cpu_only", action="store_true",
                   help=(
                       "Force StarDist to run on CPU even if a GPU is available. "
                       "Sets CUDA_VISIBLE_DEVICES='' in every worker process "
                       "before TensorFlow is initialised, preventing GPU use. "
                       "Useful for debugging, reproducibility, or when sharing "
                       "a GPU with other jobs."
                   ))

    return p

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser    = build_parser()
    args      = parser.parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.is_dir():
        parser.error(f"--input_dir does not exist or is not a directory: {input_dir}")

    # ── Schema validation ─────────────────────────────────────────────────────
    schema = parse_schema(args.filename_schema)
    sep    = args.filename_sep
    schema_errors = validate_schema(schema)
    if schema_errors:
        parser.error("Invalid --filename_schema:\n" + "\n".join(f"  {e}" for e in schema_errors))
    log.info("Schema   : %s  (sep=%r)", args.filename_schema, sep)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Parallelism auto-configuration ────────────────────────────────────────
    # On GPU: TF manages its own scheduling — don't pin threads.
    # On CPU: StarDist inference sweet spot is ~4 threads per inference on
    #   modern x86 (L3 bandwidth saturates past that for typical microscopy
    #   image sizes).  Workers = floor(cpu_count / tf_threads) so every core
    #   is owned by exactly one worker with no contention.
    #   This scales automatically: 8 cores → 2 workers, 16 → 4, 30 → 7, 64 → 16.
    try:
        cpu_count = len(os.sched_getaffinity(0))
    except AttributeError:
        cpu_count = mp.cpu_count()
    # Reserve one core for the main process (orchestration, CSV writing, pool
    # management).  Without this, workers saturate all cores and the OS
    # time-slices the main process in, adding scheduling latency.
    available = max(1, cpu_count - 1)

    # Thread pinning applies whenever workers share CPU cores — regardless of
    # whether --cpu_only is set.  Without pinning, every TF worker tries to use
    # all available cores, causing contention even if no GPU is present.
    if args.tf_threads > 0:
        tf_threads = min(args.tf_threads, available)
    else:
        tf_threads = 4   # sweet spot for StarDist on modern x86
    workers            = max(1, available // tf_threads)
    threads_per_worker = tf_threads

    import sys as _sys
    _on_mac = _sys.platform == "darwin"

    if args.cpu_only:
        # Explicit override: CPU regardless of platform
        pass
    elif _on_mac:
        # macOS: tensorflow-metal handles GPU scheduling internally.
        # Use fewer workers (Metal serialises GPU calls anyway) and don't
        # pin as many CPU threads — Metal does its own thread management.
        workers            = max(1, args.tf_threads if args.tf_threads > 0 else 2)
        threads_per_worker = tf_threads
    else:
        # Non-Mac CPU-only default: full worker pool
        workers            = max(1, available // tf_threads)
        threads_per_worker = tf_threads

    workers_override = False
    if args.workers > 0:
        workers_override = True
        workers = max(1, min(args.workers, available))
        if workers != args.workers:
            log.warning(
                "Requested --workers=%d exceeds available CPU budget (%d); using %d.",
                args.workers,
                available,
                workers,
            )

    # Effective device for logging
    if args.cpu_only:
        _device_str = "CPU only (--cpu_only)"
    elif _on_mac:
        _device_str = "Metal GPU (macOS) if tensorflow-metal installed, else CPU"
    else:
        _device_str = "CPU only (non-macOS)"

    log.info("Input    : %s", input_dir)
    log.info("Output   : %s", output_dir)
    log.info("CPUs     : %d total, %d available (1 reserved for main process)",
             cpu_count, available)
    log.info("Device   : %s", _device_str)
    log.info("TF threads/worker : %d  (workers: %d x %d = %d cores)",
             tf_threads, workers, tf_threads, workers * tf_threads)
    if workers_override:
        log.info("Workers override : --workers=%d", args.workers)

    # Per-channel top-hat flags and radii: one entry per fluor token.
    n_fluor            = len(args.fluor_tokens)
    tophat_fluor       = [not args.no_tophat_fluor] * n_fluor
    tophat_radius_fluor = [args.tophat_radius_fluor] * n_fluor

    log.info("Fluor channels : %s", ", ".join(args.fluor_tokens))
    log.info("Tophat fluor   : radius=%d, enabled=%s",
             args.tophat_radius_fluor, not args.no_tophat_fluor)

    # kwargs forwarded to every process_image_group call.
    shared_kwargs = dict(
        output_dir=output_dir,
        nuclear_token=args.nuclear_token,
        fluor_tokens=args.fluor_tokens,
        tophat_nir=not args.no_tophat_nir,
        tophat_radius_nir=args.tophat_radius_nir,
        tophat_fluor=tophat_fluor,
        tophat_radius_fluor=tophat_radius_fluor,
        save_masks=not args.no_save_masks,
        save_overlays=not args.no_save_overlays,
        schema=schema,
        sep=sep,
    )

    # ── Decide mode: zip or flat ─────────────────────────────────────────────
    well_zips = find_well_zips(input_dir)

    if well_zips:
        log.info("Zip mode: %d well zip(s) detected.", len(well_zips))
        process_well_zips(
            input_dir=input_dir,
            output_dir=output_dir,
            well_zips=well_zips,
            shared_kwargs_template=shared_kwargs,
            nuclear_token=args.nuclear_token,
            fluor_tokens=args.fluor_tokens,
            workers=workers,
            csv_prefix=args.csv_prefix,
            force=args.force,
            force_cpu=args.cpu_only,
            threads_per_worker=threads_per_worker,
            schema=schema,
            sep=sep,
        )
    else:
        log.info("Flat mode: no well zips found, scanning directory directly.")

        # Discover groups once; reuse for both skip detection and processing.
        groups_all = find_image_groups(input_dir, args.nuclear_token, args.fluor_tokens,
                                       schema=schema, sep=sep)
        skip_wells: set[str] = set()
        if not args.force:
            for nuc, _ in groups_all:
                well = parse_filename(nuc, schema=schema, sep=sep)["well"]
                if well and output_exists_for_well_flat(output_dir, well, args.csv_prefix):
                    skip_wells.add(well)
            if skip_wells:
                log.info(
                    "Flat mode: skipping %d already-complete well(s): %s. "
                    "Use --force to reprocess.",
                    len(skip_wells), sorted(skip_wells),
                )

        all_records, failed = run_pipeline_on_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            shared_kwargs=shared_kwargs,
            nuclear_token=args.nuclear_token,
            fluor_tokens=args.fluor_tokens,
            workers=workers,
            skip_wells=skip_wells,
            force_cpu=args.cpu_only,
            threads_per_worker=threads_per_worker,
            groups=groups_all,
            schema=schema,
            sep=sep,
        )
        if not all_records and not failed:
            log.error("No valid image pairs found. Exiting.")
            return
        write_csvs_per_well(all_records, output_dir, args.csv_prefix)
        log.info("=" * 60)
        log.info("Total rows : %d", len(all_records))
        if failed:
            log.warning("%d pair(s) failed:", len(failed))
            for name in failed:
                log.warning("  %s", name)
        log.info("Per-well CSVs written to: %s", output_dir)
        log.info("=" * 60)


if __name__ == "__main__":
    main()
