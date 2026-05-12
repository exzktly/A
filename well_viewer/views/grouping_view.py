"""Replicate/group card-list UI builders (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_card, btn_danger, btn_primary, btn_secondary,
    build_hline_separator, build_section_header,
    clear_layout as _clear_layout, )


# ─────────────────────────────────────────────────────────────────────────────
# Groups list (the "GROUPS" panel on the Sample Definitions tab) — a
# widgets.SavedSelectionsList over the unified app._selections model, bridged
# to the legacy _rep_sets / _bar_groups mutators (Phase 8.0 Stage C).
#
# app._selections order is [bar_groups-as-selections..., free rep_sets-as-
# selections...]; selection i ↔ app._bar_groups[i] for i < len(_bar_groups),
# else ↔ the (i - len(_bar_groups))-th *free* rep-set (its index in _rep_sets).
# ─────────────────────────────────────────────────────────────────────────────

def _sel_legacy_target(app, sel_id):
    """→ ("grp", bar_group_idx) | ("rep", rep_set_idx) | (None, -1)."""
    sels = getattr(app, "_selections", []) or []
    pos = next((i for i, s in enumerate(sels) if s.get("id") == sel_id), -1)
    if pos < 0:
        return (None, -1)
    bg = getattr(app, "_bar_groups", []) or []
    if pos < len(bg):
        return ("grp", pos)
    j = pos - len(bg)
    rs = getattr(app, "_rep_sets", []) or []
    in_group = {id(m) for g in bg for m in getattr(g, "members", [])}
    free = [i for i, r in enumerate(rs) if id(r) not in in_group]
    if 0 <= j < len(free):
        return ("rep", free[j])
    return (None, -1)


def _rep_rebuild_from(app, sel_id, wells, reps) -> None:
    """Apply an edited (wells, replicates) back to the legacy state.

    For a *rep-set* selection: a ReplicateSet only holds {name, wells}; we set
    its wells (the next round-trip flattens any replicate sub-list back to one).
    For a *bar-group* selection: one fresh ReplicateSet "<group> #k" per sub-list,
    the rest of wells as solo_wells; prune/extend _rep_sets.
    """
    from well_viewer.batch_models import ReplicateSet
    kind, idx = _sel_legacy_target(app, sel_id)
    wells = list(wells or [])
    wset = set(wells)
    reps = [list(s) for s in (reps or []) if s]
    keep_rs = app._rep_sets[idx] if kind == "rep" and 0 <= idx < len(app._rep_sets) else None
    keep_grp = app._bar_groups[idx] if kind == "grp" and 0 <= idx < len(app._bar_groups) else None
    # A well belongs to at most one group — the group being edited wins; strip
    # its new wells out of every other group first.
    for r in app._rep_sets:
        if r is keep_rs:
            continue
        nw = [w for w in r.wells if w not in wset]
        if nw != r.wells:
            r.wells = nw
    for g in app._bar_groups:
        if g is not keep_grp:
            nw = [w for w in g.solo_wells if w not in wset]
            if nw != g.solo_wells:
                g.solo_wells = nw
        for m in g.members:
            if m is keep_rs:
                continue
            nm = [w for w in m.wells if w not in wset]
            if nm != m.wells:
                m.wells = nm
    if kind == "rep":
        if keep_rs is not None:
            keep_rs.wells = list(wells)
            app._rebuild_all()
        return
    if kind == "grp":
        if keep_grp is None:
            return
        grp = keep_grp
        old_members = list(grp.members)
        new_members = [ReplicateSet(f"{grp.name} #{k + 1}", list(sub)) for k, sub in enumerate(reps)]
        covered = {w for sub in reps for w in sub}
        grp.members = new_members
        grp.solo_wells = [w for w in wells if w not in covered]
        app._rep_sets = [r for r in app._rep_sets
                         if r not in old_members or any(r in g.members for g in app._bar_groups)]
        for m in new_members:
            if m not in app._rep_sets:
                app._rep_sets.append(m)
        app._rebuild_all()


def _grp_on_activated(app, sel_id) -> None:
    kind, idx = _sel_legacy_target(app, sel_id)
    if kind == "rep":
        app._rep_select(idx)
    elif kind == "grp":
        app._bar_select_group(idx)


def _grp_on_renamed(app, sel_id, name) -> None:
    kind, idx = _sel_legacy_target(app, sel_id)
    name = (name or "").strip()
    if not name:
        return
    if kind == "rep" and 0 <= idx < len(app._rep_sets):
        if name != app._rep_sets[idx].name:
            app._rep_sets[idx].name = name
            app._rebuild_all()
    elif kind == "grp" and 0 <= idx < len(app._bar_groups):
        if name != app._bar_groups[idx].name:
            app._bar_groups[idx].name = name
            app._rebuild_all()


def _grp_on_visibility(app, sel_id, hidden) -> None:
    kind, idx = _sel_legacy_target(app, sel_id)
    hidden = bool(hidden)
    if kind == "grp" and 0 <= idx < len(app._bar_groups):
        app._bar_groups[idx].hidden = hidden
        app._rebuild_all()
    elif kind == "rep" and 0 <= idx < len(app._rep_sets):
        # rep-set visibility lives in app._rep_hidden, indexed by _rep_sets_loaded() order
        rset = app._rep_sets[idx]
        loaded = app._rep_sets_loaded() if hasattr(app, "_rep_sets_loaded") else []
        if rset in loaded:
            li = loaded.index(rset)
            if hidden:
                app._rep_hidden.add(li)
            else:
                app._rep_hidden.discard(li)
            if hasattr(app, "_sb_on_rep_change"):
                app._sb_on_rep_change()
            else:
                app._rebuild_all()


def _grp_on_deleted(app, sel_id) -> None:
    kind, idx = _sel_legacy_target(app, sel_id)
    if kind == "rep":
        app._rep_delete(idx)
    elif kind == "grp":
        app._bar_remove_group(idx)


def _grp_on_duplicated(app, new_id, src_id) -> None:
    import copy as _copy
    kind, idx = _sel_legacy_target(app, src_id)
    # A well belongs to at most one group, so a duplicate starts empty (it
    # copies the group's name/structure; assign wells to it afterward).
    if kind == "rep" and 0 <= idx < len(app._rep_sets):
        r2 = _copy.deepcopy(app._rep_sets[idx])
        r2.name = f"{r2.name} copy"
        r2.wells = []
        app._rep_sets.insert(idx + 1, r2)
        app._rebuild_all()
    elif kind == "grp" and 0 <= idx < len(app._bar_groups):
        g2 = _copy.deepcopy(app._bar_groups[idx])
        g2.name = f"{g2.name} copy"
        g2.members = []
        g2.solo_wells = []
        app._bar_groups.insert(idx + 1, g2)
        for m in g2.members:
            if m not in app._rep_sets:
                app._rep_sets.append(m)
        app._rebuild_all()


def _grp_on_order(app, ids) -> None:
    # ids = the new app._selections order. Handle the common case (no bar
    # groups → selection i ↔ _rep_sets[i]); the mixed groups+rep-sets case is
    # left for Stage D (the widget keeps its working order until the next
    # refresh re-syncs).
    bg = getattr(app, "_bar_groups", []) or []
    if bg:
        return
    rs = list(getattr(app, "_rep_sets", []) or [])
    pre = list(getattr(app, "_selections", []) or [])
    id_to_rs = {pre[i]["id"]: rs[i] for i in range(min(len(pre), len(rs)))}
    new_rs = [id_to_rs[i] for i in ids if i in id_to_rs]
    for r in rs:
        if r not in new_rs:
            new_rs.append(r)
    if new_rs != rs:
        app._rep_sets = new_rs
        app._rebuild_all()


def _grp_on_composition(app, sel_id) -> None:
    lst = getattr(app, "_rep_list", None)
    if lst is None:
        return
    for s in lst.selections():
        if s.get("id") == sel_id:
            _rep_rebuild_from(app, sel_id, s.get("wells") or [], s.get("replicates"))
            return


def wire_selections_list(app, lst) -> None:
    """Connect a SavedSelectionsList's signals to the legacy group/rep mutators."""
    lst.entryActivated.connect(lambda sid: _grp_on_activated(app, sid))
    lst.entryRenamed.connect(lambda sid, name: _grp_on_renamed(app, sid, name))
    lst.entryVisibilityToggled.connect(lambda sid, hidden: _grp_on_visibility(app, sid, hidden))
    lst.entryDeleted.connect(lambda sid: _grp_on_deleted(app, sid))
    lst.entryDuplicated.connect(lambda new_id, src_id: _grp_on_duplicated(app, new_id, src_id))
    lst.orderChanged.connect(lambda ids: _grp_on_order(app, ids))
    lst.wellsChanged.connect(lambda sid, _w: _grp_on_composition(app, sid))
    lst.addFromSelectionRequested.connect(app._rep_add)
    load_cb = getattr(app, "_bar_load_groups", None)
    if callable(load_cb):
        lst.importRequested.connect(load_cb)


def rep_panel_refresh(app) -> None:
    """Refresh the GROUPS list (a widgets.SavedSelectionsList over app._selections)."""
    lst = getattr(app, "_rep_list", None)
    if lst is None:
        return
    sync = getattr(app, "_sync_selections_from_legacy", None)
    if callable(sync):
        sync()
    try:
        lst.setEnabledWells(list(getattr(app, "_well_paths", {}).keys()))
    except Exception:
        pass
    lst.updateSelections(list(getattr(app, "_selections", []) or []))
    cur = getattr(app, "_current_selection_id", None)
    if cur:
        lst.setCurrentId(cur)
    # honour a pending inline-rename request (set by the "Rename" action)
    idx = getattr(app, "_grp_inline_edit_idx", -1)
    bg = getattr(app, "_bar_groups", []) or []
    if 0 <= idx < len(bg):
        sels = list(getattr(app, "_selections", []) or [])
        if idx < len(sels):
            app._grp_inline_edit_idx = -1
            row = getattr(lst, "_rows", {}).get(sels[idx].get("id"))
            if row is not None and hasattr(row, "trigger_rename"):
                QTimer.singleShot(0, row.trigger_rename)
    if hasattr(app, "_rep_refresh_map"):
        app._rep_refresh_map()


def grp_panel_refresh(app) -> None:
    """Rebuild the group card list in the Sample Definitions tab."""
    if not hasattr(app, "_grp_inner"):
        return
    inner = app._grp_inner
    inner_layout = inner.layout()
    if inner_layout is None:
        inner_layout = QVBoxLayout(inner)
        inner.setLayout(inner_layout)
    _clear_layout(inner_layout)

    if not app._bar_groups:
        msg = QLabel(
            "No groups defined.\nClick + Add to create one.",
            inner,
        )
        msg.setObjectName("Muted")
        inner_layout.addWidget(msg)
        inner_layout.addStretch(1)
        return

    for gi, grp in enumerate(app._bar_groups):
        is_sel = gi == app._bar_active_grp
        card = QWidget(inner)
        card.setProperty("variant", "group_row")
        card.setProperty("active", "true" if is_sel else "false")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)

        hdr = QWidget(card)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0, 0, 0, 0)
        dot = QLabel("●", hdr)
        hl.addWidget(dot)

        name_edit = QLineEdit(grp.name, hdr)
        hl.addWidget(name_edit)

        def _commit_name(i=gi, ed=name_edit):
            new_name = (ed.text() or "").strip()
            if not new_name:
                ed.setText(app._bar_groups[i].name)
                return
            if new_name != app._bar_groups[i].name:
                app._bar_groups[i].name = new_name
                app._rebuild_all()

        name_edit.editingFinished.connect(_commit_name)

        if getattr(app, "_grp_inline_edit_idx", -1) == gi:
            app._grp_inline_edit_idx = -1
            QTimer.singleShot(0, lambda ed=name_edit: (ed.setFocus(), ed.selectAll()))

        if grp.hidden:
            hid = QLabel("[hidden]", hdr)
            hid.setObjectName("Muted")
            hl.addWidget(hid)

        n_sets = len(grp.members)
        n_wells = len(grp.wells)
        cnt = QLabel(
            f"  {n_sets} set{'s' if n_sets != 1 else ''}  ·  "
            f"{n_wells} well{'s' if n_wells != 1 else ''}",
            hdr,
        )
        cnt.setObjectName("Muted")
        hl.addWidget(cnt)
        hl.addStretch(1)

        hl.addWidget(btn_card(
            hdr, "Show" if grp.hidden else "Hide",
            lambda i=gi: app._grp_toggle_visibility(i),
        ))
        hl.addWidget(btn_danger(hdr, "✕", lambda i=gi: app._grp_delete(i)))
        cl.addWidget(hdr)

        if grp.members or grp.solo_wells:
            mem = QWidget(card)
            ml = QVBoxLayout(mem)
            ml.setContentsMargins(0, 0, 0, 0)
            for rset in grp.members:
                mrow = QWidget(mem)
                mrl = QHBoxLayout(mrow)
                mrl.setContentsMargins(0, 0, 0, 0)
                mrl.addWidget(QLabel(f"[{rset.name}]", mrow))
                for w in rset.wells:
                    chip = QLabel(w, mrow)
                    chip.setProperty("variant", "chip")
                    mrl.addWidget(chip)
                if is_sel:
                    mrl.addWidget(btn_danger(
                        mrow, "−",
                        lambda g=gi, r=rset: app._grp_remove_member(g, r),
                    ))
                mrl.addStretch(1)
                ml.addWidget(mrow)
            for w in grp.solo_wells:
                srow = QWidget(mem)
                srl = QHBoxLayout(srow)
                srl.setContentsMargins(0, 0, 0, 0)
                srl.addWidget(QLabel(f"[solo] {w}", srow))
                if is_sel:
                    srl.addWidget(btn_danger(
                        srow, "−",
                        lambda g=gi, wl=w: app._grp_remove_solo(g, wl),
                    ))
                srl.addStretch(1)
                ml.addWidget(srow)
            cl.addWidget(mem)
        else:
            empty = QLabel("Empty — add replicate sets or wells below", card)
            empty.setObjectName("Muted")
            cl.addWidget(empty)

        if is_sel:
            if app._rep_sets:
                act_rep = QWidget(card)
                arl = QHBoxLayout(act_rep)
                arl.setContentsMargins(0, 0, 0, 0)
                lbl = QLabel("+ Set:", act_rep)
                lbl.setObjectName("Muted")
                arl.addWidget(lbl)
                for rset in app._rep_sets:
                    if rset not in grp.members:
                        arl.addWidget(btn_card(
                            act_rep, rset.name,
                            lambda r=rset, g=gi: app._grp_add_member(g, r),
                        ))
                arl.addStretch(1)
                cl.addWidget(act_rep)
            else:
                lbl = QLabel(
                    "(No replicate sets — define them in the left panel)",
                    card,
                )
                lbl.setObjectName("Muted")
                cl.addWidget(lbl)

        def _sel(_e, i=gi):
            app._grp_select(i)
        card.mousePressEvent = _sel
        inner_layout.addWidget(card)

    inner_layout.addStretch(1)


def build_group_def_panel(app, parent: QWidget) -> None:
    """Right panel of Sample Definitions tab."""
    from well_viewer.ui_helpers import make_scrollable_canvas

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    layout.addWidget(build_hline_separator(parent))

    hdr = build_section_header(
        parent,
        "GROUPS",
        buttons=(
            btn_secondary(parent, "Clear All", app._grp_clear_all),
            btn_primary(parent, "+ Add", app._grp_add),
        ),
    )
    layout.addWidget(hdr)

    hdr2 = QWidget(parent)
    hdr2.setObjectName("Sidebar")
    h2 = QHBoxLayout(hdr2)
    h2.setContentsMargins(8, 4, 8, 4)
    h2.addWidget(QLabel("Pair:", hdr2))
    app._bar_quick_pair_dir_cb = QComboBox(hdr2)
    app._bar_quick_pair_dir_cb.addItems(["Rows (A01+A02)", "Columns (A01+B01)"])
    h2.addWidget(app._bar_quick_pair_dir_cb)
    app._bar_quick_pair_dir_var = app._bar_quick_pair_dir_cb
    h2.addWidget(QLabel("Order:", hdr2))
    app._bar_quick_iter_order_cb = QComboBox(hdr2)
    app._bar_quick_iter_order_cb.addItems(["Across rows", "Down columns"])
    h2.addWidget(app._bar_quick_iter_order_cb)
    app._bar_quick_iter_order_var = app._bar_quick_iter_order_cb
    h2.addStretch(1)
    layout.addWidget(hdr2)

    btn_row = QWidget(parent)
    btn_row.setObjectName("Sidebar")
    br = QHBoxLayout(btn_row)
    br.setContentsMargins(8, 2, 8, 2)
    br.addWidget(btn_primary(btn_row, "Apply Quick Groups",
                             app._bar_quick_groups_from_dropdowns))
    br.addWidget(btn_secondary(btn_row, "Save…", app._bar_save_groups))
    br.addWidget(btn_secondary(btn_row, "Load…", app._bar_load_groups))
    br.addStretch(1)
    layout.addWidget(btn_row)

    help_lbl = QLabel(
        "Each group produces one bar/line on the plot. "
        "Add replicate sets or individual wells to a group.",
        parent,
    )
    help_lbl.setObjectName("Muted")
    help_lbl.setWordWrap(True)
    layout.addWidget(help_lbl)

    sa, inner = make_scrollable_canvas(parent)
    layout.addWidget(sa, 1)
    app._grp_canvas = sa
    app._grp_inner = inner
