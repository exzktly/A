"""Grouping/replicate interaction controller helpers for WellViewerApp."""

from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]

from well_viewer.batch_models import BarGroup, ReplicateSet
from well_viewer.viewer_state import extract_well_token as _extract_well_token
from well_viewer.ui_helpers import tok_at_event as _tok_at_event


def rep_map_tok_at(app, event: tk.Event):
    return _tok_at_event(event, app._rep_map_btns)


def rep_map_press(app, event: tk.Event) -> None:
    if not (0 <= app._active_rep_idx < len(app._rep_sets)):
        return
    tok = rep_map_tok_at(app, event)
    if tok is None or tok not in app._well_paths:
        return
    rset = app._rep_sets[app._active_rep_idx]
    app._rep_drag_adding = tok not in rset.wells
    app._rep_drag_visited = set()
    app._rep_map_apply(tok)


def rep_map_drag(app, event: tk.Event) -> None:
    if not (0 <= app._active_rep_idx < len(app._rep_sets)):
        return
    tok = rep_map_tok_at(app, event)
    if tok and tok not in app._rep_drag_visited:
        app._rep_map_apply(tok)


def rep_map_release(app, _event: tk.Event) -> None:
    if getattr(app, "_rep_drag_visited", None):
        app._rebuild_all()
    app._rep_drag_visited = set()


def rep_map_apply(app, tok: str) -> None:
    if tok in app._rep_drag_visited:
        return
    if not (0 <= app._active_rep_idx < len(app._rep_sets)):
        return
    app._rep_drag_visited.add(tok)
    if tok not in app._well_paths:
        return
    rset = app._rep_sets[app._active_rep_idx]
    if app._rep_drag_adding:
        for other in app._rep_sets:
            if other is not rset and tok in other.wells:
                other.wells.remove(tok)
        if tok not in rset.wells:
            rset.wells.append(tok)
    else:
        if tok in rset.wells:
            rset.wells.remove(tok)
    app._rep_refresh_map_single(tok)


def grp_select(app, idx: int) -> None:
    app._bar_active_grp = idx
    app._groups_centre_refresh()


def grp_add(app) -> None:
    name = f"Group {len(app._bar_groups) + 1}"
    app._bar_groups.append(BarGroup(name))
    app._bar_active_grp = len(app._bar_groups) - 1
    app._rebuild_all()


def grp_rename(app, idx: int) -> None:
    if not (0 <= idx < len(app._bar_groups)):
        return
    # Group names are now edited inline in the Sample Definitions panel.
    app._bar_active_grp = idx
    app._groups_centre_refresh()


def grp_delete(app, idx: int) -> None:
    if not (0 <= idx < len(app._bar_groups)):
        return
    app._bar_groups.pop(idx)
    app._bar_active_grp = min(app._bar_active_grp, len(app._bar_groups) - 1)
    app._rebuild_all()


def grp_toggle_visibility(app, idx: int) -> None:
    if 0 <= idx < len(app._bar_groups):
        app._bar_groups[idx].hidden = not app._bar_groups[idx].hidden
        app._rebuild_all()


def grp_add_member(app, grp_idx: int, rset) -> None:
    if 0 <= grp_idx < len(app._bar_groups):
        grp = app._bar_groups[grp_idx]
        if rset not in grp.members:
            grp.members.append(rset)
        app._rebuild_all()


def grp_remove_member(app, grp_idx: int, rset) -> None:
    if 0 <= grp_idx < len(app._bar_groups):
        grp = app._bar_groups[grp_idx]
        if rset in grp.members:
            grp.members.remove(rset)
        app._rebuild_all()


def grp_add_solo_well(app, grp_idx: int, well: str) -> None:
    if 0 <= grp_idx < len(app._bar_groups):
        grp = app._bar_groups[grp_idx]
        if well not in grp.solo_wells:
            grp.solo_wells.append(well)
        app._rebuild_all()


def grp_remove_solo(app, grp_idx: int, well: str) -> None:
    if 0 <= grp_idx < len(app._bar_groups):
        grp = app._bar_groups[grp_idx]
        if well in grp.solo_wells:
            grp.solo_wells.remove(well)
        app._rebuild_all()


def grp_clear_all(app) -> None:
    if not app._bar_groups:
        return
    if messagebox.askyesno("Clear all groups?", f"Remove all {len(app._bar_groups)} group(s)?", parent=app):
        app._bar_groups.clear()
        app._bar_active_grp = -1
        app._rebuild_all()


def bg_on_well_change(app) -> None:
    app._refresh_sidebar_map()
    app._redraw_bars()


def bg_apply_legacy(app, tok: str) -> None:
    if tok in app._bar_drag_visited:
        return
    app._bar_drag_visited.add(tok)
    if tok not in app._well_paths:
        return
    in_group_mode = 0 <= app._bar_active_grp < len(app._bar_groups)
    if in_group_mode:
        grp = app._bar_groups[app._bar_active_grp]
        for rset in grp.replicates:
            if tok in rset.wells:
                if not app._bar_drag_adding:
                    rset.wells.remove(tok)
                return
        if app._bar_drag_adding:
            if 0 <= app._bar_active_rep < len(grp.replicates):
                grp.replicates[app._bar_active_rep].wells.append(tok)
            else:
                grp.replicates.append(ReplicateSet(tok, [tok]))
    else:
        if app._bar_drag_adding:
            app._selected_wells.add(tok)
        else:
            app._selected_wells.discard(tok)
    app._bar_refresh_single_btn(tok)
