"""Replicate/group card-list UI builders (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_card, btn_danger, btn_primary, btn_secondary, ComboVar,
)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()


def rep_panel_refresh(app) -> None:
    if not hasattr(app, "_rep_inner"):
        return
    inner = app._rep_inner
    inner_layout = inner.layout()
    if inner_layout is None:
        inner_layout = QVBoxLayout(inner)
        inner.setLayout(inner_layout)
    _clear_layout(inner_layout)

    if not app._rep_sets:
        msg = QLabel(
            "No replicate sets defined yet.\nClick + Add to create one.",
            inner,
        )
        msg.setObjectName("Muted")
        inner_layout.addWidget(msg)
        inner_layout.addStretch(1)
        if hasattr(app, "_rep_refresh_map"):
            app._rep_refresh_map()
        return

    for si, rset in enumerate(app._rep_sets):
        is_sel = si == app._active_rep_idx
        card = QWidget(inner)
        card.setProperty("variant", "group_row")
        card.setProperty("active", "true" if is_sel else "false")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)

        hdr = QWidget(card)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0, 0, 0, 0)
        name_lbl = QLabel(rset.name, hdr)
        hl.addWidget(name_lbl)
        n = len(rset.wells)
        count_lbl = QLabel(f"  {n} well{'s' if n != 1 else ''}", hdr)
        count_lbl.setObjectName("Muted")
        hl.addWidget(count_lbl)
        hl.addStretch(1)
        hl.addWidget(btn_card(hdr, "Rename", lambda i=si: app._rep_rename(i)))
        hl.addWidget(btn_card(hdr, "Edit wells", lambda i=si: app._rep_edit_wells(i)))
        hl.addWidget(btn_danger(hdr, "✕", lambda i=si: app._rep_delete(i)))
        cl.addWidget(hdr)

        if rset.wells:
            chips = QWidget(card)
            ch_l = QHBoxLayout(chips)
            ch_l.setContentsMargins(0, 0, 0, 0)
            for w in rset.wells:
                chip = QLabel(w, chips)
                chip.setProperty("variant", "chip")
                ch_l.addWidget(chip)
            ch_l.addStretch(1)
            cl.addWidget(chips)

        def _select(_e, i=si):
            app._rep_select(i)
        card.mousePressEvent = _select
        inner_layout.addWidget(card)

    inner_layout.addStretch(1)
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

            assigned_wells = set(grp.wells)
            unassigned = [
                tok for tok in sorted(
                    app._well_paths.keys(),
                    key=lambda t: app._parse_rc(t),
                )
                if tok not in assigned_wells
            ]
            if unassigned:
                act_well = QWidget(card)
                awl = QHBoxLayout(act_well)
                awl.setContentsMargins(0, 0, 0, 0)
                lbl = QLabel("+ Well:", act_well)
                lbl.setObjectName("Muted")
                awl.addWidget(lbl)
                for tok in unassigned:
                    awl.addWidget(btn_card(
                        act_well, tok,
                        lambda wl=tok, g=gi: app._grp_add_solo_well(g, wl),
                    ))
                awl.addStretch(1)
                cl.addWidget(act_well)

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

    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    hdr = QWidget(parent)
    hdr.setObjectName("Sidebar")
    hl = QHBoxLayout(hdr)
    hl.setContentsMargins(8, 4, 8, 4)
    title = QLabel("GROUPS", hdr)
    title.setProperty("role", "section")
    hl.addWidget(title)
    hl.addStretch(1)
    hl.addWidget(btn_secondary(hdr, "Clear All", app._grp_clear_all))
    hl.addWidget(btn_primary(hdr, "+ Add", app._grp_add))
    layout.addWidget(hdr)

    hdr2 = QWidget(parent)
    hdr2.setObjectName("Sidebar")
    h2 = QHBoxLayout(hdr2)
    h2.setContentsMargins(8, 4, 8, 4)
    h2.addWidget(QLabel("Pair:", hdr2))
    app._bar_quick_pair_dir_cb = QComboBox(hdr2)
    app._bar_quick_pair_dir_cb.addItems(["Rows (A01+A02)", "Columns (A01+B01)"])
    h2.addWidget(app._bar_quick_pair_dir_cb)
    app._bar_quick_pair_dir_var = ComboVar(app._bar_quick_pair_dir_cb)
    h2.addWidget(QLabel("Order:", hdr2))
    app._bar_quick_iter_order_cb = QComboBox(hdr2)
    app._bar_quick_iter_order_cb.addItems(["Across rows", "Down columns"])
    h2.addWidget(app._bar_quick_iter_order_cb)
    app._bar_quick_iter_order_var = ComboVar(app._bar_quick_iter_order_cb)
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
