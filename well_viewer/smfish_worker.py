"""Background worker that applies a global smFISH threshold across all wells.

Runs in a daemon thread; never touches Qt directly. Status updates are
delivered through the ``status_cb`` and ``done_cb`` callables (the smFISH
tab builder hands in functions that emit Qt signals).
"""

from __future__ import annotations

import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from well_viewer.preview_controller import read_member_bytes
from well_viewer.smfish_controller import (
    SmfishImgRef,
    normalize_id,
    normalize_well_token,
    scan_well_zip,
)


logger = logging.getLogger("smfish_tab")


def _process_well(
    *,
    well: str,
    zip_path: Path,
    channel: str,
    threshold: float,
    classifier,
    fov_tp_extractor,
) -> dict[tuple[str, str, str, str], int]:
    """Compute per-cell smFISH spot counts for one well."""
    smfish, mask = scan_well_zip(
        zip_path=zip_path,
        channel=channel,
        classifier=classifier,
        fov_tp_extractor=fov_tp_extractor,
    )
    from tifffile import imread

    counts: dict[tuple[str, str, str, str], int] = {}
    for key in sorted(set(smfish).intersection(mask)):
        sm_ref = smfish[key]
        mk_ref = mask[key]
        sm_raw = read_member_bytes(zip_path=sm_ref.zip_path, member=sm_ref.zip_member, logger=logger)
        mk_raw = read_member_bytes(zip_path=mk_ref.zip_path, member=mk_ref.zip_member, logger=logger)
        if sm_raw is None or mk_raw is None:
            continue
        log_img = imread(io.BytesIO(sm_raw)).astype(np.float32)
        labels = imread(io.BytesIO(mk_raw))
        hits = labels[(labels > 0) & (log_img > threshold)].astype(np.int64, copy=False)
        if hits.size:
            hit_counts = np.bincount(hits)
            for nid in np.nonzero(hit_counts)[0]:
                counts[(well, key[0], key[1], str(int(nid)))] = int(hit_counts[nid])
    return counts


def _write_counts_to_csvs(
    out_dir: Path,
    well_to_zip: dict[str, Path],
    counts: dict[tuple[str, str, str, str], int],
    column: str,
) -> None:
    for well in sorted(well_to_zip):
        csv_matches = list(out_dir.glob(f"*_{well}.csv"))
        if not csv_matches:
            continue
        csv_path = csv_matches[0]
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

        well_series = (df["well"] if "well" in df.columns
                       else pd.Series([""] * len(df), index=df.index)).fillna("")
        r_well = well_series.where(well_series != "", well).map(normalize_well_token)
        fov_raw = (df.get("fov", df.get("FOV", pd.Series([""] * len(df), index=df.index)))
                   .fillna("").astype(str))
        fov = fov_raw.map(normalize_id)
        tp_raw_cols = [c for c in ("timepoint", "tp", "time") if c in df.columns]
        if tp_raw_cols:
            tp_raw = df[tp_raw_cols[0]]
            for c in tp_raw_cols[1:]:
                tp_raw = tp_raw.where(tp_raw.fillna("") != "", df[c])
        else:
            tp_raw = pd.Series([""] * len(df), index=df.index)
        tp = tp_raw.fillna("").astype(str).map(normalize_id)
        nid = ((df["nucleus_id"] if "nucleus_id" in df.columns
                else pd.Series([""] * len(df), index=df.index))
               .fillna("").astype(str).str.strip())

        keys = list(zip(r_well, fov, tp, nid))
        df[column] = [str(counts.get(k, 0)) for k in keys]

        df.to_csv(csv_path, index=False)


def apply_global_threshold_async(
    *,
    out_dir: Path,
    well_to_zip: dict[str, Path],
    channel: str,
    threshold: float,
    classifier,
    fov_tp_extractor,
    status_cb: Callable[[str], None],
    done_cb: Callable[[str], None],
    after_csv_cb: Callable[[], None] | None = None,
) -> threading.Thread:
    """Launch the apply-to-all worker on a daemon thread."""

    column = f"{channel}_smfish_count"

    def _run() -> None:
        if not channel:
            status_cb("Select channel and ensure one well is selected.")
            return
        counts: dict[tuple[str, str, str, str], int] = {}
        wells = sorted(well_to_zip.items())
        if wells:
            max_workers = min(8, len(wells))
            status_cb(
                f"Applying global threshold across {len(wells)} wells using {max_workers} workers..."
            )
            completed = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_well = {
                    executor.submit(
                        _process_well,
                        well=well,
                        zip_path=zip_path,
                        channel=channel,
                        threshold=threshold,
                        classifier=classifier,
                        fov_tp_extractor=fov_tp_extractor,
                    ): well
                    for well, zip_path in wells
                }
                for future in as_completed(future_to_well):
                    well = future_to_well[future]
                    completed += 1
                    try:
                        counts.update(future.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("smFISH global threshold failed for %s: %s", well, exc)
                    status_cb(f"Processed {well} ({completed}/{len(wells)})...")

        _write_counts_to_csvs(out_dir, well_to_zip, counts, column)
        if after_csv_cb is not None:
            after_csv_cb()
        done_cb("Apply to All complete. Line/Bar plots refreshed.")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
