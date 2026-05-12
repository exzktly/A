"""Bar/replicate-group persistence (user-picked JSON file).

Reads/writes the same unified ``selections`` model as ``pipeline_info.json``
(schema v2: ``{"schema_version": 2, "selections": [...], "current_id": ...}``).
A legacy ``{"rep_sets": [...], "groups": [...]}`` file is migrated on load.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from well_viewer import selections_model as _sel

_logger = logging.getLogger("well_viewer")


def to_payload(app) -> dict:
    """Serialise the app's unified ``selections`` state for ``bar_groups.json``."""
    return _sel.to_bar_groups_payload(
        list(getattr(app, "_selections", []) or []),
        getattr(app, "_current_selection_id", None),
    )


def from_dict(app, data) -> None:
    """Restore selections state on *app* from a saved (v1 or v2) payload.

    A v1 ``{rep_sets, groups}`` file hydrates the legacy shadow via the original
    parser (byte-perfect); a v2 ``{selections, …}`` file derives it via the
    inverse map. ``app._selections`` is always set.
    """
    tok_to_label = getattr(app, "_tok_to_label", {})
    selections, current_id, _labels, _notes = _sel.from_block(data, tok_to_label=tok_to_label)
    if _sel.block_is_v2(data):
        rep_sets, bar_groups, ari, bag, rh = _sel.selections_to_legacy(
            selections, current_id, tok_to_label=tok_to_label)
    else:
        from well_viewer.barplot_controller import bar_groups_from_data
        rep_sets, bar_groups = bar_groups_from_data(data, tok_to_label=tok_to_label)
        ari = -1
        bag = 0 if bar_groups else -1
        rh = set()
    app._selections = selections
    app._current_selection_id = current_id
    app._rep_sets = rep_sets
    app._bar_groups = bar_groups
    app._bar_active_grp = bag
    app._active_rep_idx = ari
    app._rep_hidden = rh


def save_via_dialog(app) -> None:
    """Prompt the user for a JSON path and write the current selections."""
    if not getattr(app, "_selections", None):
        QMessageBox.warning(
            app, "Nothing to save",
            "Define at least one selection before saving.",
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
            json.dump(to_payload(app), fh, indent=2)
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
