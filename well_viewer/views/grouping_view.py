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
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setProperty("variant", "rep_card")
        card.setProperty("active", "true" if is_sel else "false")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(2)

        name_row = QWidget(card)
        nr_l = QHBoxLayout(name_row)
        nr_l.setContentsMargins(0, 0, 0, 0)
        nr_l.setSpacing(4)
        name_lbl = QLabel(rset.name, name_row)
        nr_l.addWidget(name_lbl)
        n = len(rset.wells)
        count_lbl = QLabel(f"{n} well{'s' if n != 1 else ''}", name_row)
        count_lbl.setObjectName("Muted")
        nr_l.addWidget(count_lbl)
        nr_l.addStretch(1)
        cl.addWidget(name_row)

        btn_row = QWidget(card)
        br_l = QHBoxLayout(btn_row)
        br_l.setContentsMargins(0, 0, 0, 0)
        br_l.setSpacing(2)
        br_l.addStretch(1)
        br_l.addWidget(btn_card(btn_row, "Rename", lambda i=si: app._rep_rename(i)))
        br_l.addWidget(btn_danger(btn_row, "✕", lambda i=si: app._rep_delete(i)))
        cl.addWidget(btn_row)

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


def _grp_bar_selections(app):
    """The bar-group entries of the unified ``app._selections`` model (in order;
    the j-th here corresponds to ``app._bar_groups[j]``)."""
    return [s for s in getattr(app, "_selections", []) if s.get("source") == "bar_group"]


def _grp_idx_for(app, sel_id) -> int:
    for j, s in enumerate(_grp_bar_selections(app)):
        if s["id"] == sel_id:
            return j
    return -1


def grp_panel_refresh(app) -> None:
    """Refresh the GROUPS list — a ``widgets.SavedSelectionsList`` (composable)
    over the bar-group entries of ``app._selections``."""
    lst = getattr(app, "_grp_list", None)
    if lst is None:
        return
    sels = _grp_bar_selections(app)
    try:
        lst.setEnabledWells(list(getattr(app, "_well_paths", {}).keys()))
    except Exception:
        pass
    lst.updateSelections(sels)
    ai = getattr(app, "_bar_active_grp", -1)
    if 0 <= ai < len(sels):
        lst.setCurrentId(sels[ai]["id"])
    # honour a pending inline-rename request (set by the "Rename" action)
    idx = getattr(app, "_grp_inline_edit_idx", -1)
    if 0 <= idx < len(sels):
        app._grp_inline_edit_idx = -1
        row = getattr(lst, "_rows", {}).get(sels[idx]["id"])
        if row is not None and hasattr(row, "trigger_rename"):
            QTimer.singleShot(0, row.trigger_rename)


# ── GROUPS-list ↔ legacy-bar_groups bridge (Phase 8.0 Stage C, sub-cluster 1) ──
def _rebuild_group_from(app, j: int, wells, reps) -> None:
    """Rewrite ``app._bar_groups[j]`` so it represents the unified-model
    ``(wells, replicates)`` the user just edited in the list: one fresh
    ``ReplicateSet`` per replicate sub-list (named ``"<group> #k"``), the rest
    of ``wells`` as ``solo_wells``. Prunes / extends ``app._rep_sets`` to match.
    """
    from well_viewer.batch_models import ReplicateSet
    if not (0 <= j < len(app._bar_groups)):
        return
    grp = app._bar_groups[j]
    wells = list(wells or [])
    reps = [list(s) for s in (reps or []) if s]
    old_members = list(grp.members)
    new_members = [ReplicateSet(f"{grp.name} #{k + 1}", list(sub)) for k, sub in enumerate(reps)]
    covered = {w for sub in reps for w in sub}
    grp.members = new_members
    grp.solo_wells = [w for w in wells if w not in covered]
    # _rep_sets keeps the legacy invariant "every group member is in _rep_sets":
    # drop old members no longer referenced by any group; add the new ones.
    app._rep_sets = [r for r in app._rep_sets
                     if r not in old_members or any(r in g.members for g in app._bar_groups)]
    for m in new_members:
        if m not in app._rep_sets:
            app._rep_sets.append(m)
    app._rebuild_all()


def _grp_on_activated(app, sel_id) -> None:
    j = _grp_idx_for(app, sel_id)
    if j >= 0:
        app._grp_select(j)


def _grp_on_renamed(app, sel_id, name) -> None:
    j = _grp_idx_for(app, sel_id)
    if not (0 <= j < len(app._bar_groups)):
        return
    name = (name or "").strip()
    if name and name != app._bar_groups[j].name:
        app._bar_groups[j].name = name
        app._rebuild_all()


def _grp_on_visibility(app, sel_id, hidden) -> None:
    j = _grp_idx_for(app, sel_id)
    if 0 <= j < len(app._bar_groups):
        app._bar_groups[j].hidden = bool(hidden)
        app._rebuild_all()


def _grp_on_deleted(app, sel_id) -> None:
    j = _grp_idx_for(app, sel_id)
    if j >= 0:
        app._grp_delete(j)


def _grp_on_duplicated(app, new_id, src_id) -> None:
    import copy as _copy
    from well_viewer.batch_models import ReplicateSet  # noqa: F401  (deepcopy clones members)
    j = _grp_idx_for(app, src_id)
    if not (0 <= j < len(app._bar_groups)):
        return
    g2 = _copy.deepcopy(app._bar_groups[j])
    g2.name = f"{g2.name} copy"
    app._bar_groups.insert(j + 1, g2)
    for m in g2.members:
        if m not in app._rep_sets:
            app._rep_sets.append(m)
    app._rebuild_all()


def _grp_on_order(app, ids) -> None:
    pre = _grp_bar_selections(app)
    id_to_j = {s["id"]: j for j, s in enumerate(pre)}
    new_groups = [app._bar_groups[id_to_j[i]] for i in ids if i in id_to_j]
    for g in app._bar_groups:
        if g not in new_groups:
            new_groups.append(g)
    if new_groups != app._bar_groups:
        app._bar_groups = new_groups
        app._rebuild_all()


def _grp_on_composition(app, sel_id) -> None:
    j = _grp_idx_for(app, sel_id)
    if j < 0:
        return
    lst = getattr(app, "_grp_list", None)
    if lst is None:
        return
    for s in lst.selections():
        if s.get("id") == sel_id:
            _rebuild_group_from(app, j, s.get("wells") or [], s.get("replicates"))
            return


def build_group_def_panel(app, parent: QWidget) -> None:
    """Right panel of Sample Definitions tab."""
    from widgets.saved_selections_list import SavedSelectionsList

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
        "Each group produces one bar/line on the plot. Expand a group to edit "
        "its wells / replicates, or use “+ wells…”.",
        parent,
    )
    help_lbl.setObjectName("Muted")
    help_lbl.setWordWrap(True)
    layout.addWidget(help_lbl)

    # v2 (Phase 8.0 Stage C): the group card-list is now a SavedSelectionsList
    # over the bar-group entries of app._selections, in composable mode.
    lst = SavedSelectionsList(parent)
    lst.setComposable(True)
    app._grp_list = lst
    layout.addWidget(lst, 1)
    lst.entryActivated.connect(lambda sid: _grp_on_activated(app, sid))
    lst.entryRenamed.connect(lambda sid, name: _grp_on_renamed(app, sid, name))
    lst.entryVisibilityToggled.connect(lambda sid, hidden: _grp_on_visibility(app, sid, hidden))
    lst.entryDeleted.connect(lambda sid: _grp_on_deleted(app, sid))
    lst.entryDuplicated.connect(lambda new_id, src_id: _grp_on_duplicated(app, new_id, src_id))
    lst.orderChanged.connect(lambda ids: _grp_on_order(app, ids))
    lst.wellsChanged.connect(lambda sid, _w: _grp_on_composition(app, sid))
    lst.addFromSelectionRequested.connect(app._grp_add)
    lst.importRequested.connect(app._bar_load_groups)
