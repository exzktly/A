"""Plate/sidebar selection and drag handlers extracted from runtime_app."""

from __future__ import annotations

from typing import Optional

from well_viewer.ui_support import tok_at_event as _tok_at_event


def sidebar_tok_at(app, event) -> Optional[str]:
    return _tok_at_event(event, app._sidebar_btns)


def plate_drag_press(app, label: str, well_set: set, ds: dict) -> None:
    ds["visited"] = set()
    ds["rep_toggled"] = set()
    if app._rep_sets:
        si = app._rep_idx_for_label(label)
        ds["adding"] = (si is None or si in app._rep_hidden)
    else:
        ds["adding"] = label not in well_set


def plate_drag_apply(app, tok: str, btn_dict, well_set: set, ds: dict) -> None:
    from well_viewer import runtime_app as rt

    if tok in ds["visited"]:
        return
    ds["visited"].add(tok)
    label = app._tok_to_label.get(tok)
    if label is None:
        return

    if app._rep_sets:
        si = app._rep_idx_for_label(label)
        if si is None or si in ds["rep_toggled"]:
            return
        ds["rep_toggled"].add(si)
        if ds["adding"]:
            app._rep_hidden.discard(si)
        else:
            app._rep_hidden.add(si)
        loaded = app._rep_sets_loaded()
        if si < len(loaded):
            rset = loaded[si]
            full_c = rt.WELL_COLORS[si % len(rt.WELL_COLORS)]
            muted = app._mute_color(full_c)
            hidden = si in app._rep_hidden
            for w in rset.wells:
                t = rt._extract_well_token(w) or w
                b = btn_dict.get(t)
                if b:
                    b.config(
                        bg=muted if hidden else full_c,
                        fg=rt.CLR_MUTED_TEXT_SOFT if hidden else rt.CLR_WHITE,
                        activebackground=full_c,
                        relief=rt.tk.FLAT if hidden else rt.tk.SUNKEN,
                    )
    else:
        if ds["adding"]:
            well_set.add(label)
        else:
            well_set.discard(label)
        btn = btn_dict.get(tok)
        if btn:
            if label in well_set:
                btn.config(bg=rt.ACCENT, fg=rt.CLR_WHITE, activebackground=rt.CLR_ACCENT_DARK)
            else:
                btn.config(bg=rt.BG_PANEL, fg=rt.TXT_PRI, activebackground=rt.BG_HOVER)


def plate_drag_release(app, ds: dict, on_rep_change, on_well_change) -> None:
    if not ds["visited"]:
        return
    if app._rep_sets and ds["rep_toggled"]:
        app._invalidate_stats_cache()
        on_rep_change()
    elif not app._rep_sets:
        on_well_change()


def sb_press(app, event) -> None:
    tok = sidebar_tok_at(app, event)
    if tok is None or tok not in app._tok_to_label:
        return
    plate_drag_press(app, app._tok_to_label[tok], app._selected_wells, app._sb_ds)
    plate_drag_apply(app, tok, app._sidebar_btns, app._selected_wells, app._sb_ds)


def sb_drag(app, event) -> None:
    tok = sidebar_tok_at(app, event)
    if tok is None or tok not in app._tok_to_label:
        return
    plate_drag_apply(app, tok, app._sidebar_btns, app._selected_wells, app._sb_ds)


def sb_release(app) -> None:
    plate_drag_release(
        app,
        app._sb_ds,
        on_rep_change=app._sb_on_rep_change,
        on_well_change=app._on_plate_sel_change,
    )
    app._sb_ds["visited"] = set()


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
        tab = app._notebook.tab(app._notebook.select(), "text")
        if tab == "smFISH" and len(app._selected_wells) > 1:
            keep = app._last_sel if app._last_sel in app._selected_wells else next(iter(app._selected_wells))
            app._selected_wells = {keep}
            app._prev_sel = app._selected_wells.copy()
    app._refresh_sidebar_map()
    app._redraw()
    app._redraw_bars()
    app._redraw_scatter()
    if hasattr(app, "_notebook") and app._notebook.tab(app._notebook.select(), "text") == "smFISH":
        app._smfish_tab.sync_from_app()


def select_row(app, row: str) -> None:
    if app._rep_sets:
        loaded = app._rep_sets_loaded()
        row_idxs = [si for si, r in enumerate(loaded) if any(app._parse_rc(w)[0] == row for w in r.wells if w in app._well_paths)]
        if not row_idxs:
            return
        if any(si in app._rep_hidden for si in row_idxs):
            for si in row_idxs:
                app._rep_hidden.discard(si)
        else:
            for si in row_idxs:
                app._rep_hidden.add(si)
        app._on_plate_sel_change()
    else:
        row_labels = [lbl for lbl in app._well_paths if app._parse_rc(lbl)[0] == row]
        if not row_labels:
            return
        if any(lbl not in app._selected_wells for lbl in row_labels):
            app._selected_wells.update(row_labels)
        else:
            app._selected_wells.difference_update(row_labels)
        app._on_plate_sel_change()


def select_col(app, col: str) -> None:
    if app._rep_sets:
        loaded = app._rep_sets_loaded()
        col_idxs = [si for si, r in enumerate(loaded) if any(app._parse_rc(w)[1] == col for w in r.wells if w in app._well_paths)]
        if not col_idxs:
            return
        if any(si in app._rep_hidden for si in col_idxs):
            for si in col_idxs:
                app._rep_hidden.discard(si)
        else:
            for si in col_idxs:
                app._rep_hidden.add(si)
        app._on_plate_sel_change()
    else:
        col_labels = [lbl for lbl in app._well_paths if app._parse_rc(lbl)[1] == col]
        if not col_labels:
            return
        if any(lbl not in app._selected_wells for lbl in col_labels):
            app._selected_wells.update(col_labels)
        else:
            app._selected_wells.difference_update(col_labels)
        app._on_plate_sel_change()


def select_all(app) -> None:
    if app._rep_sets:
        app._rep_hidden.clear()
    else:
        app._selected_wells = set(app._well_paths.keys())
        if app._selected_wells:
            app._last_sel = next(iter(app._selected_wells))
        app._prev_sel = app._selected_wells.copy()
    app._refresh_sidebar_map()
    app._redraw()
    app._redraw_bars()
    app._redraw_scatter()


def select_none(app) -> None:
    if app._rep_sets:
        loaded = app._rep_sets_loaded()
        app._rep_hidden = set(range(len(loaded)))
    else:
        app._selected_wells.clear()
        app._last_sel = None
        app._prev_sel = set()
    app._refresh_sidebar_map()
    app._redraw()
    app._redraw_bars()
    app._redraw_scatter()
