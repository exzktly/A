"""Heatmap layout persistence (``<data_dir>/heatmap_layouts.json``).

The JSON wraps the layouts in an object so visual settings (cmap, scale mode,
vmin/vmax, rep-set average toggle) can be persisted alongside.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("well_viewer")


def path_for(app) -> Optional[Path]:
    if app._data_dir:
        return app._data_dir / "heatmap_layouts.json"
    return None


def _collect_settings(app) -> dict:
    def _f(name):
        v = getattr(app, name, None)
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            return float(v)
        return None
    return {
        "cmap": str(getattr(app, "_heatmap_cmap_name", "") or ""),
        "scale_mode": str(getattr(app, "_heatmap_scale_mode", "Auto") or "Auto"),
        "vmin": _f("_heatmap_vmin"),
        "vmax": _f("_heatmap_vmax"),
        "repset_avg": bool(getattr(app, "_heatmap_repset_avg", False)),
        "log_scale": bool(getattr(app, "_heatmap_log_scale", False)),
    }


def save_to_data_dir(app) -> None:
    path = path_for(app)
    if path is None:
        return
    layouts = list(getattr(app, "_heatmap_layouts", []) or [])
    payload = {
        "layouts": [lay.to_dict() for lay in layouts],
        "settings": _collect_settings(app),
    }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except OSError as exc:
        _logger.warning("Failed to save heatmap layouts to %s: %s", path, exc)


def load_from_data_dir(app) -> None:
    path = path_for(app)
    if path is None or not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Failed to load heatmap layouts from %s: %s", path, exc)
        return
    from well_viewer.heatmap_models import layouts_from_dict
    if not isinstance(data, dict):
        _logger.warning("Heatmap layouts file %s is not a JSON object; ignoring.", path)
        return
    app._heatmap_layouts = layouts_from_dict(data.get("layouts", []) or [])
    settings = data.get("settings", {}) or {}
    if isinstance(settings, dict):
        app._heatmap_persisted_settings = settings
    if hasattr(app, "_heatmap_sidebar_table"):
        try:
            from well_viewer.views.heatmap_layout_sidebar_view import (
                refresh_heatmap_layout_sidebar,
            )
            refresh_heatmap_layout_sidebar(app)
        except Exception:
            pass
    apply_persisted_settings(app)


def apply_persisted_settings(app) -> None:
    """Push any settings loaded from disk into the heatmap UI widgets.

    Safe to call before the heatmap tab is built — does nothing in that case.
    """
    settings = getattr(app, "_heatmap_persisted_settings", None)
    if not isinstance(settings, dict) or not settings:
        return
    cmap_cb = getattr(app, "_heatmap_cmap_cb", None)
    scale_cb = getattr(app, "_heatmap_scale_cb", None)
    vmin_edit = getattr(app, "_heatmap_vmin_edit", None)
    vmax_edit = getattr(app, "_heatmap_vmax_edit", None)
    rs_cb = getattr(app, "_heatmap_repset_avg_cb", None)
    # Bail until the tab is built; init/build will call us again.
    if cmap_cb is None and scale_cb is None and rs_cb is None:
        return

    cmap = str(settings.get("cmap") or "")
    if cmap and cmap_cb is not None:
        idx = cmap_cb.findText(cmap)
        if idx >= 0:
            blocked = cmap_cb.blockSignals(True)
            try:
                cmap_cb.setCurrentIndex(idx)
            finally:
                cmap_cb.blockSignals(blocked)
        app._heatmap_cmap_name = cmap

    scale_mode = str(settings.get("scale_mode") or "Auto")
    if scale_cb is not None:
        idx = scale_cb.findText(scale_mode)
        if idx >= 0:
            blocked = scale_cb.blockSignals(True)
            try:
                scale_cb.setCurrentIndex(idx)
            finally:
                scale_cb.blockSignals(blocked)
    app._heatmap_scale_mode = scale_mode

    def _set_edit(edit, key):
        v = settings.get(key)
        if edit is not None and isinstance(v, (int, float)) and math.isfinite(float(v)):
            blocked = edit.blockSignals(True)
            try:
                edit.setText(f"{float(v):g}")
            finally:
                edit.blockSignals(blocked)
            setattr(app, f"_heatmap_{key}", float(v))

    _set_edit(vmin_edit, "vmin")
    _set_edit(vmax_edit, "vmax")

    repset_avg = bool(settings.get("repset_avg", False))
    app._heatmap_repset_avg = repset_avg
    if rs_cb is not None:
        blocked = rs_cb.blockSignals(True)
        try:
            rs_cb.setChecked(repset_avg)
        finally:
            rs_cb.blockSignals(blocked)

    log_scale = bool(settings.get("log_scale", False))
    app._heatmap_log_scale = log_scale
    log_cb = getattr(app, "_heatmap_log_scale_cb", None)
    if log_cb is not None:
        blocked = log_cb.blockSignals(True)
        try:
            log_cb.setChecked(log_scale)
        finally:
            log_cb.blockSignals(blocked)

    # Successfully applied — keep the dict around in case the tab rebuilds.
    # (No need to clear it; a subsequent save_to_data_dir overwrites the file
    # with current widget state anyway.)
