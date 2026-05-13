"""Plate/sidebar selection handlers for WellViewerApp."""

from __future__ import annotations


def _active_tab(app) -> str:
    # Plot tabs (Line Graphs / Bar Plots / Scatter Plot) live inside a nested
    # "Plotting" QTabWidget. Use the app's centre-tab resolver so callers see
    # the leaf tab name and dispatch correctly when the nested notebook is in
    # play; fall back to the top-level notebook for older code paths.
    resolver = getattr(app, "_current_centre_tab", None)
    if callable(resolver):
        try:
            tab = resolver()
            if tab:
                return tab
        except Exception:
            pass
    if not hasattr(app, "_notebook"):
        return ""
    try:
        return app._notebook.tabText(app._notebook.currentIndex())
    except Exception:
        return ""


def _refresh_after_selection_change(app) -> None:
    """Refresh only UI/views relevant to the active tab."""
    app._refresh_sidebar_map()
    tab = _active_tab(app)
    if tab == "Bar Plots":
        app._update_bar_tp_menu()
        app._redraw_bars()
    elif tab == "Scatter Plot":
        app._update_scatter_menus()
        from well_viewer.tabs.scatter_tab_view import scatter_redraw_active
        scatter_redraw_active(app)
    elif tab == "Review CSV":
        app._refresh_review_csv()
    elif tab == "smFISH":
        if hasattr(app, "_smfish_tab"):
            app._smfish_tab.sync_from_app()
    elif tab == "Sample Definitions":
        # Cell Gating is a sub-tab here; refresh its CDF if the user has
        # opened it at least once.
        gating = getattr(app, "_cell_gating_tab", None)
        if gating is not None:
            gating._load_cell_areas()
        # Don't fall through to _redraw — labels-and-groups edits don't
        # require a plot redraw.
    else:
        app._redraw()


def on_plate_sel_change(app) -> None:
    cur_labels = app._selected_wells.copy()
    added = cur_labels - app._prev_sel
    removed = app._prev_sel - cur_labels
    if added:
        app._last_sel = next(iter(added))
    elif removed:
        deselected = next(iter(removed))
        app._last_sel = deselected if cur_labels else None
    app._prev_sel = cur_labels
    if hasattr(app, "_notebook"):
        tab = app._notebook.tabText(app._notebook.currentIndex())
        if tab == "smFISH" and len(app._selected_wells) > 1:
            keep = app._last_sel if app._last_sel in app._selected_wells else next(iter(app._selected_wells))
            app._selected_wells = {keep}
            app._prev_sel = app._selected_wells.copy()
    _refresh_after_selection_change(app)


def _well_rc(app, w):
    try:
        return app._parse_rc(w)
    except Exception:
        return ("", "")


def _set_groups_hidden(app, sels, *, target=None) -> None:
    """Set ``hidden`` on each of *sels*. ``target`` None ⇒ toggle: hide them all
    if any is currently visible, else show them all."""
    sels = [s for s in sels if isinstance(s, dict)]
    if not sels:
        return
    if target is None:
        target = any(not bool(s.get("hidden")) for s in sels)  # any visible → hide all
    target = bool(target)
    changed = False
    for s in sels:
        if bool(s.get("hidden")) != target:
            s["hidden"] = target
            changed = True
    if changed:
        app._invalidate_stats_cache()
        app._rebuild_all()


def select_row(app, row: str) -> None:
    if app._rep_sets:  # rep-mode: toggle visibility of groups with a well in this row
        _set_groups_hidden(app, [
            s for s in app._selections
            if any(_well_rc(app, w)[0] == row and w in app._well_paths for w in (s.get("wells") or []))
        ])
    else:
        row_labels = [lbl for lbl in app._well_paths if _well_rc(app, lbl)[0] == row]
        if not row_labels:
            return
        if any(lbl not in app._selected_wells for lbl in row_labels):
            app._selected_wells.update(row_labels)
        else:
            app._selected_wells.difference_update(row_labels)
        app._on_plate_sel_change()


def select_col(app, col: str) -> None:
    if app._rep_sets:
        _set_groups_hidden(app, [
            s for s in app._selections
            if any(_well_rc(app, w)[1] == col and w in app._well_paths for w in (s.get("wells") or []))
        ])
    else:
        col_labels = [lbl for lbl in app._well_paths if _well_rc(app, lbl)[1] == col]
        if not col_labels:
            return
        if any(lbl not in app._selected_wells for lbl in col_labels):
            app._selected_wells.update(col_labels)
        else:
            app._selected_wells.difference_update(col_labels)
        app._on_plate_sel_change()


def select_all(app) -> None:
    if app._rep_sets:  # rep-mode: show every group
        _set_groups_hidden(app, app._selections, target=False)
    else:
        app._selected_wells = set(app._well_paths.keys())
        if app._selected_wells:
            app._last_sel = next(iter(app._selected_wells))
        app._prev_sel = app._selected_wells.copy()
        _refresh_after_selection_change(app)


def select_none(app) -> None:
    if app._rep_sets:  # rep-mode: hide every group
        _set_groups_hidden(app, app._selections, target=True)
    else:
        app._selected_wells.clear()
        app._last_sel = None
        app._prev_sel = set()
        _refresh_after_selection_change(app)
