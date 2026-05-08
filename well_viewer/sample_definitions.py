"""Save / load Sample Definitions (well labels + replicate sets + groups)
inside ``pipeline_info.json``.

The pipeline writes pipeline_info.json as part of every analysis run. This
module lets the viewer overlay user-curated sample metadata onto that file
without disturbing the pipeline-owned keys: it reads the existing JSON,
sets / replaces the ``sample_definitions`` block, and writes the file back.
On load, ``read_sample_definitions`` returns the saved block (or None) so
the runtime app can re-apply it.

Schema written under the ``sample_definitions`` key:

    {
        "well_labels": {"A01": "Treated 0nM", "B05": "Control", ...},
        "rep_sets":    [{"name": "Rep 1", "wells": ["A01", "A02"]}, ...],
        "groups":      [{"name": "Control", "hidden": false,
                          "members": ["Rep 1"],
                          "solo_wells": ["B05"]}, ...],
    }

This mirrors the format already used by the standalone bar_groups.json
loader so the same parser (``barplot_controller.bar_groups_from_data``)
can hydrate the in-memory state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .barplot_controller import bar_groups_from_data, bar_groups_to_dict
from .batch_models import BarGroup, ReplicateSet


_logger = logging.getLogger("well_viewer.sample_definitions")

PIPELINE_INFO_FILENAME = "pipeline_info.json"
SAMPLE_DEFINITIONS_KEY = "sample_definitions"


def _resolve_pipeline_info_path(out_dir: Path) -> Path:
    """Return the pipeline_info.json path, falling back to parent dir.

    Mirrors ``viewer_state.read_pipeline_info`` so save and load look in
    the same place.
    """
    primary = out_dir / PIPELINE_INFO_FILENAME
    if primary.exists():
        return primary
    parent = out_dir.parent / PIPELINE_INFO_FILENAME
    if parent.exists():
        return parent
    return primary  # may not exist; caller decides


def build_sample_definitions(
    well_labels: Dict[str, str],
    rep_sets: Iterable[ReplicateSet],
    bar_groups: Iterable[BarGroup],
    *,
    extract_well_token,
    notes: str = "",
) -> Dict[str, Any]:
    """Snapshot the current sample-definition state as a JSON-friendly dict."""
    groups_dict = bar_groups_to_dict(
        list(rep_sets), list(bar_groups), extract_well_token=extract_well_token,
    )
    return {
        "well_labels": {
            str(k): str(v)
            for k, v in (well_labels or {}).items()
            if str(v).strip()
        },
        "rep_sets": list(groups_dict.get("rep_sets", [])),
        "groups": list(groups_dict.get("groups", [])),
        "notes": str(notes or ""),
    }


def save_to_pipeline_info(
    out_dir: Path,
    sample_definitions: Dict[str, Any],
) -> Path:
    """Merge ``sample_definitions`` into the pipeline_info.json sidecar.

    Existing keys (schema, fov_index, fluor_tokens, …) are preserved
    verbatim. The ``sample_definitions`` key is replaced.

    Raises FileNotFoundError when the pipeline file does not yet exist —
    the caller should run the pipeline first so the file gets created.
    """
    info_path = _resolve_pipeline_info_path(out_dir)
    if not info_path.exists():
        raise FileNotFoundError(
            f"{PIPELINE_INFO_FILENAME} was not found in {out_dir} "
            f"(or its parent). Run the pipeline first to create it."
        )
    try:
        existing = json.loads(info_path.read_text())
        if not isinstance(existing, dict):
            raise ValueError(f"{info_path} is not a JSON object.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise OSError(f"Could not read {info_path}: {exc}") from exc

    existing[SAMPLE_DEFINITIONS_KEY] = sample_definitions
    tmp = info_path.with_suffix(info_path.suffix + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2))
    tmp.replace(info_path)
    return info_path


def read_sample_definitions(out_dir: Path) -> Optional[Dict[str, Any]]:
    """Return the saved sample_definitions block, or None when absent."""
    info_path = _resolve_pipeline_info_path(out_dir)
    if not info_path.exists():
        return None
    try:
        data = json.loads(info_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Could not read %s: %s", info_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    block = data.get(SAMPLE_DEFINITIONS_KEY)
    if not isinstance(block, dict):
        return None
    return block


def parse_groups_block(
    block: Dict[str, Any],
    *,
    tok_to_label: Dict[str, str],
):
    """Hydrate (rep_sets, bar_groups) from a sample_definitions block."""
    payload: Dict[str, Any] = {
        "rep_sets": list(block.get("rep_sets", []) or []),
        "groups": list(block.get("groups", []) or []),
    }
    return bar_groups_from_data(payload, tok_to_label=tok_to_label)


def parse_notes(block: Dict[str, Any]) -> str:
    """Return the freeform notes string from a sample_definitions block."""
    raw = block.get("notes", "")
    if isinstance(raw, str):
        return raw
    return ""


def parse_well_labels(
    block: Dict[str, Any],
    *,
    valid_tokens: Iterable[str],
) -> Dict[str, str]:
    """Filter the well_labels map to tokens that are actually loaded."""
    raw = block.get("well_labels", {}) or {}
    valid = set(valid_tokens)
    out: Dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for tok, label in raw.items():
        if tok in valid and str(label).strip():
            out[str(tok)] = str(label).strip()
    return out
