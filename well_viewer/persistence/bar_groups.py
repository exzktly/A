"""Bar/replicate-group persistence (user-picked JSON file)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from well_viewer.barplot_controller import (
    bar_groups_from_data,
    bar_groups_to_dict,
)
from well_viewer.data_loading import extract_well_token

_logger = logging.getLogger("well_viewer")


def to_dict(rep_sets, bar_groups) -> dict:
    """Serialise ``(rep_sets, bar_groups)`` to a JSON-friendly structure."""
    return bar_groups_to_dict(
        rep_sets, bar_groups, extract_well_token=extract_well_token,
    )


def from_dict(app, data) -> None:
    """Restore groups state on *app* from a saved dict."""
    app._rep_sets.clear()
    app._bar_groups.clear()
    app._bar_active_grp = -1
    app._active_rep_idx = -1
    app._rep_hidden.clear()
    app._rep_sets, app._bar_groups = bar_groups_from_data(
        data, tok_to_label=app._tok_to_label,
    )
    if app._bar_groups:
        app._bar_active_grp = 0


def save_via_dialog(app) -> None:
    """Prompt the user for a JSON path and write current bar groups."""
    if not app._bar_groups:
        QMessageBox.warning(
            app, "Nothing to save",
            "Define at least one group before saving.",
        )
        return
    out_dir = app._data_dir if app._data_dir else None
    init_dir = str(out_dir) if out_dir else ""
    init_path = str(Path(init_dir) / "bar_groups.json") if init_dir else "bar_groups.json"
    path_str, _ = QFileDialog.getSaveFileName(
        app, "Save bar group definitions",
        init_path,
        "Group definitions JSON (*.json);;All files (*.*)",
    )
    if not path_str:
        return
    try:
        with open(path_str, "w", encoding="utf-8") as fh:
            json.dump(to_dict(app._rep_sets, app._bar_groups), fh, indent=2)
        _logger.info("Bar groups saved to %s", path_str)
    except OSError as exc:
        QMessageBox.critical(app, "Save failed", str(exc))


def load_via_dialog(app) -> None:
    """Prompt the user for a JSON path and load bar groups from it."""
    out_dir = app._data_dir if app._data_dir else None
    init_dir = str(out_dir) if out_dir else ""
    path_str, _ = QFileDialog.getOpenFileName(
        app, "Load bar group definitions",
        init_dir,
        "Group definitions JSON (*.json);;All files (*.*)",
    )
    if not path_str:
        return
    try:
        with open(path_str, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object at the top level.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        QMessageBox.critical(
            app, "Load failed",
            f"Could not read group definitions:\n{exc}",
        )
        return
    if app._bar_groups:
        resp = QMessageBox.question(
            app, "Replace existing groups?",
            f"Loading will replace the current {len(app._bar_groups)} "
            f"group(s).  Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
    from_dict(app, data)
    app._bar_rebuild_groups()
    _logger.info("Bar groups loaded from %s (%d group(s))",
                 path_str, len(app._bar_groups))
