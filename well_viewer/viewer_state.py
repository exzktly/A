"""State/pure helpers for incremental viewer modularization."""

from __future__ import annotations

import json
import logging
import re
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple


def make_schema_extractor(sep: str, fov_idx: int, tp_idx: int):
    def _extract(stem: str) -> Tuple[str, str]:
        parts = stem.split(sep)
        fov = parts[fov_idx] if 0 <= fov_idx < len(parts) else "unknown"
        tp = parts[tp_idx] if 0 <= tp_idx < len(parts) else "unknown"
        return fov, tp

    return _extract


def extract_well_token(label: str) -> Optional[str]:
    """Extract normalized well token from trailing label text.

    Example:
        "gfp_measurements_B10" -> "B10"
    """
    m = re.search(r"([A-Ha-h])(\d{1,2})$", label)
    return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else None


def read_pipeline_info(
    out_dir: Path,
    *,
    logger=None,
    check_parent: bool = True,
) -> tuple[Callable[[str], Tuple[str, str]] | None, list[str], set[str], dict]:
    if logger is None:
        logger = logging.getLogger("well_viewer")

    info_path = out_dir / "pipeline_info.json"
    if not info_path.exists() and check_parent:
        parent_path = out_dir.parent / "pipeline_info.json"
        if parent_path.exists():
            info_path = parent_path

    if not info_path.exists():
        return None, [], set(), {}

    try:
        data = json.loads(info_path.read_text())
        sep = str(data.get("separator", "_"))
        fov_idx = int(data["fov_index"])
        tp_idx = int(data["tp_index"])
        fluor_tokens = [str(t).lower() for t in data.get("fluor_tokens", [])]
        smfish_tokens = set(str(t).lower() for t in data.get("smfish_tokens", []))
        pipeline_info = {
            "schema": str(data.get("schema", "")),
            "schema_fields": [str(f).strip() for f in data.get("schema_fields", [])],
            "separator": sep,
            "well_index": int(data.get("well_index", -1)),
            "channel_index": int(data.get("channel_index", -1)),
            "fov_index": fov_idx,
            "tp_index": tp_idx,
            "nuclear_token": str(data.get("nuclear_token", "")).strip().lower(),
            "fluor_tokens": list(fluor_tokens),
        }
        if tp_idx < 0:
            logger.warning("pipeline_info.json has invalid tp_index (%s); using legacy regex", info_path)
            return None, fluor_tokens, smfish_tokens, pipeline_info
        if fov_idx < 0:
            logger.info("Loaded pipeline_info from %s  sep=%r fov=<single> tp=%d", info_path, sep, tp_idx)

            def _extract_single_fov(stem: str) -> Tuple[str, str]:
                parts = stem.split(sep)
                tp = parts[tp_idx] if 0 <= tp_idx < len(parts) else "unknown"
                return "1", tp

            return _extract_single_fov, fluor_tokens, smfish_tokens, pipeline_info
        logger.info(
            "Loaded pipeline_info from %s  sep=%r fov=%d tp=%d fluor=%s smfish=%s",
            info_path,
            sep,
            fov_idx,
            tp_idx,
            fluor_tokens,
            smfish_tokens,
        )
        return make_schema_extractor(sep, fov_idx, tp_idx), fluor_tokens, smfish_tokens, pipeline_info
    except Exception as exc:
        logger.warning("Could not parse pipeline_info.json (%s): %s — using legacy regex", info_path, exc)
        return None, [], set(), {}


# ── Batch export utilities (merged from batch_export.py) ─────────────────────

def ensure_unique_name(base: str, existing: set) -> str:
    if base not in existing:
        return base
    i = 2
    while f"{base} ({i})" in existing:
        i += 1
    return f"{base} ({i})"


def groups_with_loaded_wells(groups, well_paths: dict) -> list:
    """Return groups that contain at least one loaded well label."""
    return [g for g in groups if any(w in well_paths for w in g.wells)]


def selected_listbox_values(listbox: tk.Listbox) -> List[str]:
    """Return selected string values from a Tk listbox."""
    return [listbox.get(i) for i in listbox.curselection()]


# ── App-level state container (merged from app_state.py) ─────────────────────

@dataclass
class ViewerAppState:
    """Minimal package-level runtime state for app composition."""

    data_path: Path | None = None
