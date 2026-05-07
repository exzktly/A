"""Heatmap layout persistence (``<data_dir>/heatmap_layouts.json``)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("well_viewer")


def path_for(app) -> Optional[Path]:
    if app._data_dir:
        return app._data_dir / "heatmap_layouts.json"
    return None


def save_to_data_dir(app) -> None:
    path = path_for(app)
    if path is None:
        return
    layouts = list(getattr(app, "_heatmap_layouts", []) or [])
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([lay.to_dict() for lay in layouts], fh, indent=2)
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
    app._heatmap_layouts = layouts_from_dict(data)
    if hasattr(app, "_heatmap_sidebar_table"):
        try:
            from well_viewer.views.heatmap_layout_sidebar_view import (
                refresh_heatmap_layout_sidebar,
            )
            refresh_heatmap_layout_sidebar(app)
        except Exception:
            pass
