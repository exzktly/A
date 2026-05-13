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
# The "GROUPS" panel on the Sample Definitions tab — a widgets.SavedSelectionsList
# over the unified app._selections model (Phase 8.0 Stage C: _selections is the
# in-memory source of truth; the SavedSelectionsList's signals go straight to the
# app's `_sel_*` mutators, keyed by selection id).
# ─────────────────────────────────────────────────────────────────────────────

def _grp_on_composition(app, sel_id) -> None:
    lst = getattr(app, "_rep_list", None)
    if lst is None:
        return
    for s in lst.selections():
        if s.get("id") == sel_id:
            app._sel_set_composition(sel_id, s.get("wells") or [], s.get("replicates"))
            return


def wire_selections_list(app, lst) -> None:
    """Connect a SavedSelectionsList's signals to the app's `_sel_*` mutators."""
    lst.entryActivated.connect(lambda sid: app._sel_select(sid))
    lst.entryRenamed.connect(lambda sid, name: app._sel_rename(sid, name))
    lst.entryVisibilityToggled.connect(lambda sid, hidden: app._sel_set_hidden(sid, hidden))
    lst.entryDeleted.connect(lambda sid: app._sel_delete(sid))
    lst.entryDuplicated.connect(lambda new_id, src_id: app._sel_duplicate(src_id))
    lst.orderChanged.connect(lambda ids: app._sel_reorder(ids))
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
    try:
        lst.setEnabledWells(list(getattr(app, "_well_paths", {}).keys()))
    except Exception:
        pass
    sels = list(getattr(app, "_selections", []) or [])
    lst.updateSelections(sels)
    cur = getattr(app, "_current_selection_id", None)
    if cur:
        lst.setCurrentId(cur)
    # honour a pending inline-rename request (set by the "Rename" action — it
    # stores a position into _selections; see _sel_request_inline_rename)
    idx = getattr(app, "_grp_inline_edit_idx", -1)
    if 0 <= idx < len(sels):
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
