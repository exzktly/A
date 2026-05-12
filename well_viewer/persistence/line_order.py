"""Line-plot draw-order persistence (``<data_dir>/line_order.json``)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer

_logger = logging.getLogger("well_viewer")


def path_for(app) -> Optional[Path]:
    if app._data_dir:
        return app._data_dir / "line_order.json"
    return None


def save_to_data_dir(app) -> None:
    path = path_for(app)
    if path is None:
        return
    payload = {
        "version": 1,
        "rsets": list(app._line_order_rsets),
        "wells": list(app._line_order_wells),
    }
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(path)
    except OSError as exc:
        _logger.warning("Failed to save line order to %s: %s", path, exc)


def load_from_data_dir(app) -> None:
    path = path_for(app)
    if path is None or not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Failed to load line order from %s: %s", path, exc)
        return
    if not isinstance(data, dict):
        return
    rsets = data.get("rsets") or []
    wells = data.get("wells") or []
    app._line_order_rsets = [str(x) for x in rsets if isinstance(x, str)]
    app._line_order_wells = [str(x) for x in wells if isinstance(x, str)]
    _reorder_selections_by_line_order(app)


def _reorder_selections_by_line_order(app) -> None:
    """Re-apply the saved line-graph order (§3.5) to the unified ``selections``
    model — it loads *after* sample_definitions, so the initial parse can't see
    it. Best-effort; a no-op when there's no model. The legacy ``_rep_sets`` /
    ``_bar_groups`` shadow is left alone here — the legacy renderers already
    re-order at draw time via ``_line_order_rsets`` / ``_line_order_wells``.
    """
    sels = getattr(app, "_selections", None)
    if not sels:
        return
    try:
        from well_viewer import selections_model as _sel
        new = _sel.reorder_by_line_order(
            sels,
            rset_order=getattr(app, "_line_order_rsets", None),
            well_order=getattr(app, "_line_order_wells", None),
        )
        if [s["id"] for s in new] != [s["id"] for s in sels]:
            app._selections = new
    except Exception:  # pragma: no cover - never break loading over a re-sort
        _logger.exception("Couldn't re-apply line order to selections")


def schedule_save(app) -> None:
    if app._line_order_save_pending:
        return
    if path_for(app) is None:
        return
    app._line_order_save_pending = True
    QTimer.singleShot(500, lambda: _flush(app))


def _flush(app) -> None:
    app._line_order_save_pending = False
    save_to_data_dir(app)
