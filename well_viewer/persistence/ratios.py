"""Ratio metric persistence (``<data_dir>/ratios.json``)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from well_viewer.ratio_models import ratios_from_dict, ratios_to_dict

_logger = logging.getLogger("well_viewer")


def path_for(app) -> Optional[Path]:
    if app._data_dir:
        return app._data_dir / "ratios.json"
    return None


def save_to_data_dir(app) -> None:
    path = path_for(app)
    if path is None:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ratios_to_dict(app._ratio_metrics), fh, indent=2)
    except OSError as exc:
        _logger.warning("Failed to save ratios to %s: %s", path, exc)


def load_from_data_dir(app) -> None:
    path = path_for(app)
    if path is None or not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Failed to load ratios from %s: %s", path, exc)
        return
    app._set_ratio_metrics(ratios_from_dict(data))
