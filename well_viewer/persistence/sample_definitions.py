"""Sample-definitions persistence (in ``pipeline_info.json``).

Bundles per-block savers/loaders into the single Save / Load / Clear All
buttons exposed on the Sample Definitions tab.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

from well_viewer.data_loading import extract_well_token
from well_viewer.persistence import (
    cell_gating as _cell_gating,
    ratios as _ratios,
)

_logger = logging.getLogger("well_viewer")


def sync_selections_from_legacy(app) -> None:
    """No-op (Phase 8.0 Stage C). ``app._selections`` is now the in-memory
    source of truth, so there's nothing to re-derive before a save."""
    return


def save_to_pipeline_info(app) -> None:
    """Merge well labels + the unified ``selections`` model into pipeline_info.json."""
    from well_viewer.sample_definitions import (
        build_sample_definitions_v2,
        save_to_pipeline_info as _write_block,
    )
    if not app._data_dir:
        QMessageBox.warning(
            app, "No data loaded",
            "Open a data folder before saving sample definitions.",
        )
        return
    if getattr(app, "_selections_v2_writes_disabled", False):
        QMessageBox.warning(
            app, "Save unavailable",
            "Saved sample definitions couldn't be upgraded earlier this session, "
            "so writing them is disabled to avoid corrupting the file. See the log.",
        )
        return
    sync_selections_from_legacy(app)
    notes_edit = getattr(app, "_notes_edit", None)
    notes_text = (
        notes_edit.toPlainText() if notes_edit is not None
        else getattr(app, "_notes_text", "") or ""
    )
    app._notes_text = notes_text
    selections = list(getattr(app, "_selections", []) or [])
    current_id = getattr(app, "_current_selection_id", None)
    block = build_sample_definitions_v2(
        app._well_labels, selections, current_id, notes=notes_text,
    )
    try:
        info_path = _write_block(app._data_dir, block)
    except FileNotFoundError as exc:
        QMessageBox.warning(app, "pipeline_info.json missing", str(exc))
        return
    except OSError as exc:
        QMessageBox.critical(app, "Save failed", str(exc))
        return
    n_hidden = sum(1 for s in selections if s.get("hidden"))
    app._set_status(
        f"Sample definitions saved to {info_path.name}: "
        f"{len(block['well_labels'])} label(s), "
        f"{len(selections)} selection(s)"
        + (f" ({n_hidden} hidden)" if n_hidden else "")
        + " (schema v2)."
    )


def _apply_unified_state(app, block, *, set_notes: bool = True) -> tuple[bool, dict]:
    """Parse a sample_definitions/bar_groups block → set ``app._selections`` (the
    in-memory source of truth) and derive the legacy ``_rep_sets`` /
    ``_bar_groups`` / … shadow from it via ``selections_to_legacy``. v1 blocks
    are migrated by ``from_block``.

    Returns ``(applied, well_labels_dict)``. On a malformed block / migration
    failure: logs, leaves the existing state alone, disables v2 writes for the
    session, and returns ``(False, {})``.
    """
    from well_viewer import selections_model as _sel
    tok_to_label = getattr(app, "_tok_to_label", {})
    try:
        # Don't honour line order here — line_order.json loads *after* this; its
        # loader re-applies the reorder.
        selections, current_id, well_labels, notes = _sel.from_block(
            block, tok_to_label=tok_to_label)
    except Exception:  # pragma: no cover - defensive: never crash on bad data
        _logger.exception("Couldn't upgrade saved sample definitions — using "
                          "compatibility mode; the file was left untouched.")
        app._selections_v2_writes_disabled = True
        try:
            app._set_status("Couldn't upgrade saved sample definitions — using "
                            "them in compatibility mode (see log).")
        except Exception:
            pass
        return False, {}

    app._selections = selections
    app._current_selection_id = current_id
    if hasattr(app, "_sync_legacy_from_selections"):
        app._sync_legacy_from_selections()
    if set_notes:
        app._notes_text = notes
        notes_edit = getattr(app, "_notes_edit", None)
        if notes_edit is not None and notes_edit.toPlainText() != notes:
            blocked = notes_edit.blockSignals(True)
            try:
                notes_edit.setPlainText(notes)
            finally:
                notes_edit.blockSignals(blocked)
    return True, well_labels


def load_from_pipeline_info(app) -> bool:
    """Apply any saved sample_definitions block in pipeline_info.json.

    v1 blocks are migrated to the unified ``selections`` model on the fly (the
    migrated state is persisted, with a one-time backup, on the next Save).
    Returns True when a block was found and applied.
    """
    from well_viewer.sample_definitions import read_sample_definitions
    if not app._data_dir:
        return False
    block = read_sample_definitions(app._data_dir)
    if not block:
        return False
    applied, well_labels = _apply_unified_state(app, block)
    if not applied:
        return True  # a block existed; we just couldn't upgrade it
    valid = set(app._well_paths.keys())
    for tok, lab in (well_labels or {}).items():
        if tok in valid and str(lab).strip():
            app._well_labels[str(tok)] = str(lab).strip()
    app._invalidate_stats_cache()
    return True


def save_all(app) -> None:
    """Persist labels + reps + groups + ratios + gating in one click."""
    if not app._data_dir:
        QMessageBox.warning(
            app, "No data loaded",
            "Open a data folder before saving sample definitions.",
        )
        return
    panel = getattr(app, "_ratio_panel", None)
    if panel is not None:
        try:
            panel._on_apply()
        except Exception:
            _logger.exception("Ratio panel apply failed during Save")
    save_to_pipeline_info(app)
    _ratios.save_to_data_dir(app)
    try:
        _cell_gating.save_to_pipeline_info(app)
    except Exception:
        _logger.exception("Gating save during combined Save failed")


def load_all(app) -> None:
    """Reload labels + reps + groups + ratios + gating from the data folder."""
    if not app._data_dir:
        QMessageBox.warning(
            app, "No data loaded",
            "Open a data folder before loading sample definitions.",
        )
        return
    applied = load_from_pipeline_info(app)
    _ratios.load_from_data_dir(app)
    try:
        _cell_gating.load_from_pipeline_info(app)
    except Exception:
        _logger.exception("Gating load during combined Load failed")
    if hasattr(app, "_groups_centre_refresh"):
        try:
            app._groups_centre_refresh()
        except Exception:
            _logger.exception("Sample Definitions refresh after Load failed")
    panel = getattr(app, "_ratio_panel", None)
    if panel is not None:
        try:
            panel.refresh_from_app()
        except Exception:
            _logger.exception("Ratio panel refresh after Load failed")
    app._set_status(
        "Sample definitions reloaded." if applied
        else "No saved sample definitions found in this data folder."
    )


def clear_all(app) -> None:
    """Clear every definition driven from the Sample Definitions tab."""
    confirm = QMessageBox.question(
        app, "Clear sample definitions",
        "Discard all well labels, replicate sets, bar groups, ratio "
        "metrics, and cell-gating thresholds defined on this tab?\n\n"
        "Saved JSON files are not touched until you click Save.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if confirm != QMessageBox.Yes:
        return

    app._well_labels.clear()
    if hasattr(app, "_label_panel_refresh"):
        try:
            app._label_panel_refresh()
        except Exception:
            pass

    app._notes_text = ""
    notes_edit = getattr(app, "_notes_edit", None)
    if notes_edit is not None:
        blocked = notes_edit.blockSignals(True)
        try:
            notes_edit.clear()
        finally:
            notes_edit.blockSignals(blocked)

    app._selections = []
    app._current_selection_id = None

    app._rep_sets = []
    app._active_rep_idx = -1

    app._bar_groups = []
    app._bar_active_grp = -1

    app._set_ratio_metrics([])

    gating = getattr(app, "_cell_gating_tab", None)
    if gating is not None:
        try:
            gating._cell_area_edit.setText("0.0")
            for edit in gating._fluor_gate_edits.values():
                edit.setText("0.0")
            for edit in gating._thresh_frac_edits.values():
                edit.setText("50.0")
            if hasattr(gating, "_on_gating_change"):
                gating._on_gating_change()
            if hasattr(gating, "_on_threshold_frac_on_change"):
                gating._on_threshold_frac_on_change()
        except Exception:
            _logger.exception("Cell Gating reset during Clear failed")

    if hasattr(app, "_groups_centre_refresh"):
        try:
            app._groups_centre_refresh()
        except Exception:
            _logger.exception("Sample Definitions refresh after Clear failed")
    app._invalidate_stats_cache()
    if hasattr(app, "_redraw"):
        try:
            app._redraw()
        except Exception:
            pass
    app._set_status("Sample definitions cleared.")
