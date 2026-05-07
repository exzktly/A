"""Cell-override persistence (``<data_dir>/cell_overrides.json``).

Stores Segmentation tab include/exclude patches for individual cells. Writes
are debounced via ``schedule_save`` to coalesce bursts of toggles into a
single disk write.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer

_logger = logging.getLogger("well_viewer")


def path_for(app) -> Optional[Path]:
    if app._data_dir:
        return app._data_dir / "cell_overrides.json"
    return None


def save_to_data_dir(app) -> None:
    path = path_for(app)
    if path is None:
        return
    overrides = []
    for (well, fov, tp, nid), val in app._review_included_overrides.items():
        overrides.append({
            "well": str(well),
            "fov": str(fov),
            "tp": str(tp),
            "nucleus_id": str(nid),
            "included": str(val),
        })
    payload = {"version": 1, "overrides": overrides}
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(path)
    except OSError as exc:
        _logger.warning("Failed to save cell overrides to %s: %s", path, exc)


def load_from_data_dir(app) -> None:
    path = path_for(app)
    if path is None or not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Failed to load cell overrides from %s: %s", path, exc)
        return
    overrides = data.get("overrides") if isinstance(data, dict) else None
    if not isinstance(overrides, list):
        return
    app._review_included_overrides.clear()
    for entry in overrides:
        if not isinstance(entry, dict):
            continue
        well = str(entry.get("well", "")).strip()
        fov = str(entry.get("fov", "")).strip()
        tp = str(entry.get("tp", "")).strip()
        nid = str(entry.get("nucleus_id", "")).strip()
        inc = str(entry.get("included", "1")).strip() or "1"
        if not (well and fov and tp and nid):
            continue
        # Re-normalize so keys match the form ``_set_review_cell_included``
        # produces on subsequent toggles.
        fov_n, tp_n, nid_n = app._review_row_keys(
            {"fov": fov, "tp": tp, "nucleus_id": nid}
        )
        if not (fov_n and tp_n and nid_n):
            continue
        app._review_included_overrides[(well, fov_n, tp_n, nid_n)] = inc
    app._review_image_override_version += 1


def schedule_save(app) -> None:
    """Debounced autosave (coalesces toggle bursts into a single write)."""
    if app._cell_overrides_save_pending:
        return
    if path_for(app) is None:
        return
    app._cell_overrides_save_pending = True
    QTimer.singleShot(500, lambda: _flush(app))


def _flush(app) -> None:
    app._cell_overrides_save_pending = False
    save_to_data_dir(app)
