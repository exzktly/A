from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent.parent
ZIPPER_SCRIPT = HERE / "WellPlateZipper.py"
TIF_GLOB = ("*.tif", "*.tiff", "*.TIF", "*.TIFF")
_WELL_NAME_RE = re.compile(r"^([A-Ha-h])(\d{1,2})$")


def find_zipper_script() -> Path | None:
    return ZIPPER_SCRIPT if ZIPPER_SCRIPT.exists() else None


def tif_files_in(folder: Path) -> list[Path]:
    files: list[Path] = []
    for pat in TIF_GLOB:
        files.extend(folder.glob(pat))
    return files


def _has_well_content(folder: Path) -> bool:
    """Return True if *folder* contains zip files OR well-named subdirectories."""
    if any(folder.glob("*.zip")):
        return True
    try:
        return any(_WELL_NAME_RE.match(p.name) for p in folder.iterdir() if p.is_dir())
    except OSError:
        return False


def run_zipper(
    tif_folder: Path,
    out_folder: Path,
    *,
    log_fn: Callable[[str], None] | None = None,
    progress_fn: Callable[[str], None] | None = None,
    filename_schema: str,
    filename_sep: str,
) -> None:
    zipper = find_zipper_script()
    if zipper is None:
        raise RuntimeError(f"WellPlateZipper.py not found. Expected: {ZIPPER_SCRIPT}")

    out_folder.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(zipper),
        "--search-dir",
        str(tif_folder),
        "--output-dir",
        str(out_folder),
        "--filename_schema",
        filename_schema,
        "--filename_sep",
        filename_sep,
    ]
    if log_fn:
        log_fn(f"[zipper] $ {' '.join(cmd)}\n")

    well_pat = re.compile(r"^([A-H]\d{2}):\s+\d+\s+files", re.IGNORECASE)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if log_fn:
            log_fn(f"[zipper] {line}\n")
        m = well_pat.match(line.strip())
        if m and progress_fn:
            progress_fn(m.group(1).upper())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"WellPlateZipper exited with code {proc.returncode}.")


def resolve_input_output(
    raw: Path,
    *,
    log_fn: Callable[[str], None] | None = None,
    progress_fn: Callable[[str], None] | None = None,
    filename_schema: str,
    filename_sep: str,
) -> tuple[Path, Path]:
    if not raw.is_dir():
        raise ValueError(f"Not a directory:\n{raw}")

    if raw.name.lower() == "in":
        return raw, raw.parent / "out"

    in_sub = raw / "in"
    if in_sub.is_dir() and _has_well_content(in_sub):
        return in_sub, raw / "out"

    tifs = tif_files_in(raw)
    if len(tifs) > 3:
        if log_fn:
            log_fn(
                f"[zipper] Found {len(tifs)} TIF files — running WellPlateZipper to create per-well folders in in/\n"
            )
        run_zipper(
            raw,
            in_sub,
            log_fn=log_fn,
            progress_fn=progress_fn,
            filename_schema=filename_schema,
            filename_sep=filename_sep,
        )
        if not in_sub.is_dir() or not _has_well_content(in_sub):
            raise ValueError(
                "WellPlateZipper ran but produced no well folders or zip files.\n\n"
                "Common causes:\n"
                "  • The 'well' position in the Filename Schema does not match the actual well token in your filenames.\n"
                "  • The separator character does not match your filenames.\n"
                "  • The well token is not a valid 96-well plate position (A01–H12).\n\n"
                f"Schema used: {filename_schema}  |  Separator: '{filename_sep}'"
            )
        return in_sub, raw / "out"

    raise ValueError(
        "Cannot determine input layout.\n\n"
        "Expected one of:\n"
        "  • Selected folder is named \"in\"\n"
        "  • Selected folder contains a sub-folder named \"in\"\n"
        "  • Selected folder contains more than 3 TIF files\n"
        "    (will be grouped by well using WellPlateZipper)\n\n"
        f"Folder selected: {raw}\n"
        f"TIF files found: {len(tifs)}"
    )
