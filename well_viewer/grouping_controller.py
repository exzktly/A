"""Grouping/replicate interaction controller helpers for WellViewerApp."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from well_viewer.batch_models import BarGroup, ReplicateSet
from well_viewer.viewer_state import extract_well_token as _extract_well_token
from well_viewer.ui_helpers import tok_at_event as _tok_at_event


def rep_map_tok_at(app, event):
    return _tok_at_event(event, app._rep_map_btns)


def _grp_active(app) -> bool:
    return 0 <= getattr(app, "_bar_active_grp", -1) < len(app._bar_groups)


def _rep_active(app) -> bool:
    return 0 <= app._active_rep_idx < len(app._rep_sets)


def rep_map_press(app, event) -> None:
    if not (_rep_active(app) or _grp_active(app)):
        return
    tok = rep_map_tok_at(app, event)
    if tok is None or tok not in app._well_paths:
        return
    if _grp_active(app):
        grp = app._bar_groups[app._bar_active_grp]
        app._rep_drag_adding = tok not in grp.solo_wells
    else:
        rset = app._rep_sets[app._active_rep_idx]
        app._rep_drag_adding = tok not in rset.wells
    app._rep_drag_visited = set()
    app._rep_map_apply(tok)


def rep_map_drag(app, event) -> None:
    if not (_rep_active(app) or _grp_active(app)):
        return
    tok = rep_map_tok_at(app, event)
    if tok and tok not in app._rep_drag_visited:
        app._rep_map_apply(tok)


def rep_map_release(app, _event=None) -> None:
    if getattr(app, "_rep_drag_visited", None):
        app._rebuild_all()
    app._rep_drag_visited = set()


def rep_map_apply(app, tok: str) -> None:
    if tok in app._rep_drag_visited:
        return
    app._rep_drag_visited.add(tok)
    if tok not in app._well_paths:
        return
    if _grp_active(app):
        grp = app._bar_groups[app._bar_active_grp]
        if app._rep_drag_adding:
            # A well belongs to at most one group — pull it out of every other.
            for r in app._rep_sets:
                if tok in r.wells:
                    r.wells.remove(tok)
            for g in app._bar_groups:
                if g is not grp and tok in g.solo_wells:
                    g.solo_wells.remove(tok)
            if tok not in grp.solo_wells:
                grp.solo_wells.append(tok)
        else:
            if tok in grp.solo_wells:
                grp.solo_wells.remove(tok)
        app._rep_refresh_map_single(tok)
        return
    if not _rep_active(app):
        return
    rset = app._rep_sets[app._active_rep_idx]
    if app._rep_drag_adding:
        for other in app._rep_sets:
            if other is not rset and tok in other.wells:
                other.wells.remove(tok)
        for g in app._bar_groups:
            if tok in g.solo_wells:
                g.solo_wells.remove(tok)
        if tok not in rset.wells:
            rset.wells.append(tok)
    else:
        if tok in rset.wells:
            rset.wells.remove(tok)
    app._rep_refresh_map_single(tok)


def grp_select(app, idx: int) -> None:
    app._bar_active_grp = idx
    # Group and replicate selection are mutually exclusive: selecting a group
    # clears any active replicate set so the sidebar plate grid edits the
    # group's solo wells instead of a replicate's wells.
    app._active_rep_idx = -1
    app._groups_centre_refresh()


def grp_add(app) -> None:
    name = f"Group {len(app._bar_groups) + 1}"
    app._bar_groups.append(BarGroup(name))
    app._bar_active_grp = len(app._bar_groups) - 1
    app._active_rep_idx = -1
    app._rebuild_all()


def grp_rename(app, idx: int) -> None:
    if not (0 <= idx < len(app._bar_groups)):
        return
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
    reply = QMessageBox.question(
        app, "Clear all groups?", f"Remove all {len(app._bar_groups)} group(s)?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply == QMessageBox.Yes:
        app._bar_groups.clear()
        app._bar_active_grp = -1
        app._rebuild_all()


def bg_on_well_change(app) -> None:
    app._refresh_sidebar_map()
    app._redraw_bars()


# ── Quick-group helpers (extracted from runtime_app) ──────────────────────────
#
# Bulk replicate-set / bar-group constructors driven by the "Quick Replicates"
# and "Quick Groups" dropdowns on the Sample Definitions panel.

from PySide6.QtCore import QTimer
from well_viewer.plate_layout import PLATE_COLS, PLATE_ROWS


def make_replicate_pairs(toks, prefix: str):
    """Pair adjacent tokens into ReplicateSets; singletons become solo sets."""
    sets = []
    i = 0
    while i < len(toks):
        if i + 1 < len(toks):
            t1, t2 = toks[i], toks[i + 1]
            sets.append(ReplicateSet(f"{t1}/{t2}", [t1, t2]))
            i += 2
        else:
            t = toks[i]
            sets.append(ReplicateSet(t, [t]))
            i += 1
    return sets


def rep_quick_pairs(app) -> None:
    """Generate quick replicate pairs using current dropdown selections."""
    pair_dir = app._rep_quick_pair_dir
    iter_order = app._rep_quick_iter_order
    new_sets = []

    if pair_dir == "row":
        if iter_order == "row":
            for row_ltr in PLATE_ROWS:
                loaded = [f"{row_ltr}{col}" for col in PLATE_COLS
                          if f"{row_ltr}{col}" in app._well_paths]
                new_sets.extend(make_replicate_pairs(loaded, row_ltr))
        else:
            by_col = {}
            for row_ltr in PLATE_ROWS:
                loaded = [f"{row_ltr}{col}" for col in PLATE_COLS
                          if f"{row_ltr}{col}" in app._well_paths]
                row_sets = make_replicate_pairs(loaded, row_ltr)
                for s in row_sets:
                    if s.wells:
                        col = _extract_well_token(s.wells[0])
                        if col and len(col) > 1:
                            col = col[1:]
                            by_col.setdefault(col, []).append(s)
            for col in PLATE_COLS:
                if col in by_col:
                    new_sets.extend(by_col[col])
    else:
        if iter_order == "col":
            for col in PLATE_COLS:
                loaded = [f"{row_ltr}{col}" for row_ltr in PLATE_ROWS
                          if f"{row_ltr}{col}" in app._well_paths]
                new_sets.extend(make_replicate_pairs(loaded, col))
        else:
            by_row = {}
            for col in PLATE_COLS:
                loaded = [f"{row_ltr}{col}" for row_ltr in PLATE_ROWS
                          if f"{row_ltr}{col}" in app._well_paths]
                col_sets = make_replicate_pairs(loaded, col)
                for s in col_sets:
                    if s.wells:
                        tok = _extract_well_token(s.wells[0])
                        if tok and len(tok) > 0:
                            row = tok[0]
                            by_row.setdefault(row, []).append(s)
            for row in PLATE_ROWS:
                if row in by_row:
                    new_sets.extend(by_row[row])

    if not new_sets:
        return
    if app._rep_sets:
        resp = QMessageBox.question(
            app, "Replace replicate sets?",
            f"This will replace the current {len(app._rep_sets)} "
            "replicate set(s). Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        for grp in app._bar_groups:
            grp.members.clear()
    app._rep_sets = new_sets
    app._active_rep_idx = 0 if app._rep_sets else -1
    app._rep_hidden.clear()
    app._invalidate_stats_cache()
    rep_quick_refresh_ui(app)


def rep_quick_refresh_ui(app) -> None:
    """Lightweight post-assignment refresh for Quick Replicates."""
    app._rep_refresh_map()
    app._refresh_sidebar_map()
    app._bar_refresh_map()

    try:
        active_tab = app._notebook.tabText(app._notebook.currentIndex())
    except Exception:
        active_tab = ""
    if active_tab == "Sample Definitions":
        app._rep_panel_refresh()

    if active_tab == "Bar Plots":
        QTimer.singleShot(0, app._redraw_bars)
    elif active_tab == "Line Graphs":
        QTimer.singleShot(0, app._redraw)


def bar_quick_groups(app) -> None:
    """Generate quick bar groups using current dropdown selections."""
    pair_dir = app._bar_quick_pair_dir
    iter_order = app._bar_quick_iter_order
    app._bar_groups.clear()
    app._bar_active_grp = -1

    if pair_dir == "row":
        if iter_order == "row":
            for row_ltr in PLATE_ROWS:
                loaded = [f"{row_ltr}{col}" for col in PLATE_COLS
                          if f"{row_ltr}{col}" in app._well_paths]
                if not loaded:
                    continue
                sets = make_replicate_pairs(loaded, row_ltr)
                app._bar_groups.append(BarGroup(f"Row {row_ltr}", members=sets))
        else:
            for col in PLATE_COLS:
                pairs_in_col = []
                for row_ltr in PLATE_ROWS:
                    loaded = [f"{row_ltr}{col}"]
                    next_col_idx = PLATE_COLS.index(col) + 1
                    if next_col_idx < len(PLATE_COLS):
                        loaded.append(f"{row_ltr}{PLATE_COLS[next_col_idx]}")
                    loaded = [t for t in loaded if t in app._well_paths]
                    if loaded:
                        pairs_in_col.extend(make_replicate_pairs(loaded, col))
                if pairs_in_col:
                    app._bar_groups.append(BarGroup(f"Col {col}", members=pairs_in_col))
    else:
        if iter_order == "col":
            for col in PLATE_COLS:
                loaded = [f"{row_ltr}{col}" for row_ltr in PLATE_ROWS
                          if f"{row_ltr}{col}" in app._well_paths]
                if not loaded:
                    continue
                sets = make_replicate_pairs(loaded, col)
                app._bar_groups.append(BarGroup(f"Col {col}", members=sets))
        else:
            for row_ltr in PLATE_ROWS:
                pairs_in_row = []
                for col in PLATE_COLS:
                    loaded = [f"{row_ltr}{col}"]
                    next_row_idx = PLATE_ROWS.index(row_ltr) + 1
                    if next_row_idx < len(PLATE_ROWS):
                        loaded.append(f"{PLATE_ROWS[next_row_idx]}{col}")
                    loaded = [t for t in loaded if t in app._well_paths]
                    if loaded:
                        pairs_in_row.extend(make_replicate_pairs(loaded, col))
                if pairs_in_row:
                    app._bar_groups.append(BarGroup(f"Row {row_ltr}", members=pairs_in_row))

    if app._bar_groups:
        app._bar_active_grp = 0
    app._bar_rebuild_groups_ui_now()
    QTimer.singleShot(50, app._bar_rebuild_groups)
