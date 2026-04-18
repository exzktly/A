from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PIPELINE_SCRIPT = HERE / "process_microscopy_v2.py"


def find_pipeline_script() -> Path | None:
    return PIPELINE_SCRIPT if PIPELINE_SCRIPT.exists() else None


def _to_jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return value


def _effective_fluor_tokens_for_sidecar(
    fluor_tokens: list[str],
    *,
    nuclear_token: str = "",
    segmentation_method: str = "stardist_nuclei",
    cytoplasm_token: str = "",
) -> list[str]:
    """Return effective quantified channel tokens for pipeline_info.json."""
    ordered = [str(nuclear_token or "").strip(), *[str(tok or "").strip() for tok in fluor_tokens]]
    if segmentation_method == "stardist_seeded_watershed_cell":
        ordered.append(str(cytoplasm_token or "").strip())
    out: list[str] = []
    seen: set[str] = set()
    for tok in ordered:
        if not tok:
            continue
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok)
    return out


def _parse_timepoint_hours(value: str) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        pass
    m = re.match(
        r"^\s*(?:(\d+(?:\.\d+)?)d)?\s*(?:(\d+(?:\.\d+)?)h)?\s*(?:(\d+(?:\.\d+)?)m)?\s*$",
        raw,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    d, h, mnt = m.groups()
    if not any((d, h, mnt)):
        return None
    return (float(d or 0.0) * 24.0) + float(h or 0.0) + (float(mnt or 0.0) / 60.0)


def collect_available_timepoints(
    input_dir: Path,
    *,
    filename_schema: str,
    filename_sep: str,
) -> list[str]:
    return _collect_available_schema_values(
        input_dir,
        filename_schema=filename_schema,
        filename_sep=filename_sep,
        field_name="timepoint",
        sort_key=lambda tp: (
            _parse_timepoint_hours(tp) is None,
            _parse_timepoint_hours(tp) or 0.0,
            tp,
        ),
    )


def collect_available_fovs(
    input_dir: Path,
    *,
    filename_schema: str,
    filename_sep: str,
) -> list[str]:
    return _collect_available_schema_values(
        input_dir,
        filename_schema=filename_schema,
        filename_sep=filename_sep,
        field_name="fov",
        sort_key=lambda fov: (_parse_numeric_token(fov) is None, _parse_numeric_token(fov) or 0.0, fov),
    )


def _parse_numeric_token(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _collect_image_stems(input_dir: Path) -> set[str]:
    stems: set[str] = set()
    for pat in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
        for p in input_dir.glob(pat):
            stems.add(p.stem)
    try:
        well_dirs = [p for p in input_dir.iterdir() if p.is_dir()]
    except OSError:
        well_dirs = []
    for well_dir in well_dirs:
        for pat in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
            for p in well_dir.glob(pat):
                stems.add(p.stem)
    for z in input_dir.glob("*.zip"):
        try:
            with zipfile.ZipFile(z, "r") as zf:
                for member in zf.namelist():
                    name = Path(member).name
                    lower = name.lower()
                    if not lower.endswith((".tif", ".tiff")):
                        continue
                    stems.add(Path(name).stem)
        except Exception:
            continue
    return stems


def _collect_available_schema_values(
    input_dir: Path,
    *,
    filename_schema: str,
    filename_sep: str,
    field_name: str,
    sort_key,
) -> list[str]:
    fields = [f.strip().lower() for f in filename_schema.split(":")]
    try:
        field_idx = fields.index(field_name)
    except ValueError:
        return []

    def _add_from_stem(stem: str, out: set[str]) -> None:
        parts = stem.split(filename_sep)
        if 0 <= field_idx < len(parts):
            tok = str(parts[field_idx]).strip()
            if tok:
                out.add(tok)

    values: set[str] = set()
    for stem in _collect_image_stems(input_dir):
        _add_from_stem(stem, values)
    return sorted(values, key=sort_key)


def write_pipeline_info(
    output_dir: Path,
    *,
    filename_schema: str,
    filename_sep: str,
    nuclear_token: str = "",
    fluor_tokens: list[str],
    smfish_tokens: list[str] = [],
    segmentation_method: str = "stardist_nuclei",
    cytoplasm_token: str = "",
    min_nucleus_area_px: int = 50,
    available_timepoints: list[str] | None = None,
    available_fovs: list[str] | None = None,
    execution_options: dict | None = None,
) -> Path:
    if segmentation_method != "stardist_seeded_watershed_cell":
        cytoplasm_token = ""
    fields = [f.strip() for f in filename_schema.split(":")]
    info = {
        "schema": filename_schema,
        "separator": filename_sep,
        "schema_fields": fields,
        "nuclear_token": str(nuclear_token or ""),
        "well_index": fields.index("well") if "well" in fields else -1,
        "channel_index": fields.index("channel") if "channel" in fields else -1,
        "fov_index": fields.index("fov") if "fov" in fields else -1,
        "tp_index": fields.index("timepoint") if "timepoint" in fields else -1,
        "fluor_tokens": _effective_fluor_tokens_for_sidecar(
            fluor_tokens,
            nuclear_token=nuclear_token,
            segmentation_method=segmentation_method,
            cytoplasm_token=cytoplasm_token,
        ),
        "smfish_tokens": smfish_tokens,
        "segmentation_method": segmentation_method,
        "cytoplasm_token": cytoplasm_token,
        "min_nucleus_area_px": int(min_nucleus_area_px),
        "available_timepoints": [str(tp).strip() for tp in (available_timepoints or []) if str(tp).strip()],
        "available_fovs": [str(fov).strip() for fov in (available_fovs or []) if str(fov).strip()],
        "execution_options": _to_jsonable(dict(execution_options or {})),
    }
    p = output_dir / "pipeline_info.json"
    p.write_text(json.dumps(info, indent=2))
    return p


def build_pipeline_args(
    pipeline: Path,
    input_dir: Path,
    output_dir: Path,
    opts: dict,
) -> list[str]:
    segmentation_method = opts.get("segmentation_method", "stardist_nuclei")
    args = [
        sys.executable,
        str(pipeline),
        "--input_dir",
        str(input_dir),
        "--output_dir",
        str(output_dir),
        "--nuclear_token",
        opts["nuclear_token"],
        "--fluor_tokens",
        *opts["fluor_tokens"],
        "--csv_prefix",
        opts["csv_prefix"],
        "--filename_schema",
        opts["filename_schema"],
        "--filename_sep",
        opts["filename_sep"],
        "--segmentation_method",
        segmentation_method,
    ]
    try:
        min_area = int(opts.get("min_nucleus_area_px", 50))
    except (TypeError, ValueError):
        min_area = 50
    args += ["--min_nucleus_area_px", str(max(1, min_area))]
    cytoplasm_token = (opts.get("cytoplasm_token") or "").strip()
    if segmentation_method == "stardist_seeded_watershed_cell" and cytoplasm_token:
        args += ["--cytoplasm_token", cytoplasm_token]
    try:
        args += ["--tophat_radius_nir", str(int(opts["tophat_radius_nir"]))]
    except ValueError:
        pass
    try:
        args += ["--tophat_radius_fluor", str(int(opts["tophat_radius_fluor"]))]
    except ValueError:
        pass

    for flag in (
        "no_tophat_nir",
        "no_tophat_fluor",
        "force",
        "cpu_only",
    ):
        if opts.get(flag):
            args.append(f"--{flag}")
    for flag in (
        "compress_input_well_folders",
        "compress_output_well_folders",
    ):
        args.append(f"--{flag}" if opts.get(flag) else f"--no-{flag}")
    smfish = opts.get("smfish_tokens", [])
    if smfish:
        args += ["--smfish_tokens"] + list(smfish)

    try:
        tf = int(opts["tf_threads"])
        if tf != 0:
            args += ["--tf_threads", str(tf)]
    except ValueError:
        pass
    try:
        workers = int(opts.get("workers", 0))
        if workers > 0:
            args += ["--workers", str(workers)]
    except (TypeError, ValueError):
        pass

    return args


def spawn_pipeline(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
