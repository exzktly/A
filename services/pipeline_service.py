from __future__ import annotations

import json
import os
import subprocess
import sys
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
        "fluor_tokens": fluor_tokens,
        "smfish_tokens": smfish_tokens,
        "segmentation_method": segmentation_method,
        "cytoplasm_token": cytoplasm_token,
        "min_nucleus_area_px": int(min_nucleus_area_px),
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
        "compress_input_well_folders",
        "compress_output_well_folders",
        "force",
        "cpu_only",
    ):
        if opts.get(flag):
            args.append(f"--{flag}")
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
