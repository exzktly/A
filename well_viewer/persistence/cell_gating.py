"""Cell-gating threshold persistence (within ``pipeline_info.json``)."""

from __future__ import annotations

import logging

_logger = logging.getLogger("well_viewer")


def save_to_pipeline_info(app) -> None:
    """Persist non-default cell gating params to pipeline_info.json.

    Called from the Cell Gating tab whenever the user edits a value. Silently
    no-ops when no data directory is loaded or the sidecar is missing.
    """
    if not app._data_dir:
        return
    tab = getattr(app, "_cell_gating_tab", None)
    if tab is None:
        return
    from well_viewer.gating_state import (
        build_gating_block,
        save_gating_to_pipeline_info,
    )
    cell_area_threshold = app._get_cell_area_threshold()
    fluor_gates = app._get_all_fluor_gates()
    thresh_frac_on = {
        ch: tab.get_thresh_frac_on(ch) for ch in app._fluor_channels
    }
    block = build_gating_block(
        cell_area_threshold, fluor_gates, thresh_frac_on,
    )
    save_gating_to_pipeline_info(app._data_dir, block)


def load_from_pipeline_info(app) -> bool:
    """Apply any saved cell_gating block in pipeline_info.json.

    Returns True when a block was found and applied. The Cell Gating tab is
    built lazily, so when the sidecar has persisted thresholds we force-build
    the tab here so its QLineEdits exist before we try to set them.
    """
    if not app._data_dir:
        return False
    from well_viewer.gating_state import read_gating_params
    block = read_gating_params(app._data_dir)
    if not block:
        return False

    tab = getattr(app, "_cell_gating_tab", None)
    if tab is None:
        build = getattr(app, "_centre_build_pending", None)
        if callable(build):
            build("Sample Definitions")
        if hasattr(app, "_build_cell_gating_subtab"):
            app._build_cell_gating_subtab()
        tab = getattr(app, "_cell_gating_tab", None)
    if tab is None:
        return False

    applied = False
    cell_area = block.get("cell_area_threshold")
    if cell_area is not None:
        try:
            tab._cell_area_edit.setText(str(float(cell_area)))
            applied = True
        except (ValueError, TypeError, AttributeError):
            pass

    fluor_gates = block.get("fluor_gates") or {}
    if isinstance(fluor_gates, dict):
        for ch, val in fluor_gates.items():
            edit = tab._fluor_gate_edits.get(str(ch))
            if edit is None:
                continue
            try:
                edit.setText(str(float(val)))
                applied = True
            except (ValueError, TypeError):
                pass

    thresh_frac_on = block.get("thresh_frac_on") or {}
    if isinstance(thresh_frac_on, dict):
        if not hasattr(app, "_thresh_frac_on_saved"):
            app._thresh_frac_on_saved = {}
        for ch, val in thresh_frac_on.items():
            try:
                fval = float(val)
            except (ValueError, TypeError):
                continue
            app._thresh_frac_on_saved[str(ch)] = fval
            edit = tab._thresh_frac_edits.get(str(ch))
            if edit is not None:
                edit.setText(str(fval))
                applied = True

    return applied
