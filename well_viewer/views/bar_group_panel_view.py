"""Bar-plot group panel builders (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import btn_card, btn_danger, btn_primary, btn_secondary


def build_bar_group_panel(app, parent: QWidget) -> None:
    """Left panel of the Bar Plots tab."""
    from well_viewer.ui_helpers import make_scrollable_canvas
    from well_viewer.views.well_button import build_plate_grid

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    hdr1 = QWidget(parent)
    hdr1.setObjectName("Sidebar")
    h1 = QHBoxLayout(hdr1)
    h1.setContentsMargins(8, 3, 8, 3)
    title = QLabel("PLATE MAP", hdr1)
    title.setProperty("role", "section")
    h1.addWidget(title)
    hint = QLabel("(right-drag to toggle visibility)", hdr1)
    hint.setObjectName("Muted")
    h1.addWidget(hint)
    h1.addStretch(1)
    h1.addWidget(btn_secondary(hdr1, "Clear All", app._bar_clear_all_groups))
    h1.addWidget(btn_primary(hdr1, "+ Add Group", app._bar_add_group))
    layout.addWidget(hdr1)

    sep1 = QFrame(parent)
    sep1.setObjectName("Separator")
    sep1.setFrameShape(QFrame.HLine)
    sep1.setFixedHeight(1)
    layout.addWidget(sep1)

    help_lbl = QLabel(
        "Left-drag: add wells to active replicate set  ·  "
        "Right-click/drag: toggle group bar-plot visibility",
        parent,
    )
    help_lbl.setObjectName("Muted")
    help_lbl.setWordWrap(True)
    layout.addWidget(help_lbl)

    app._bar_map_frame = QWidget(parent)
    layout.addWidget(app._bar_map_frame)

    app._bar_map_btns: dict = {}
    app._bar_drag_adding = True
    app._bar_drag_visited: set = set()
    build_plate_grid(app._bar_map_frame, app._bar_map_btns)

    # Left/right drag state machine — we dispatch on button modifiers.
    # Enabled QPushButtons consume mouse events instead of bubbling them to
    # their parent frame, so handlers are installed per-button here.
    def _tok_under_cursor(global_pos):
        for tok, btn in app._bar_map_btns.items():
            try:
                local = btn.mapFromGlobal(global_pos)
                if btn.rect().contains(local):
                    return tok
            except Exception:
                continue
        return None

    def _press_for(tok):
        def _press(event):
            pos = event.position().toPoint()
            if event.button() == Qt.RightButton:
                app._bg_vis_press(_QEvent(tok, pos))
            else:
                app._bg_press(_QEvent(tok, pos))
        return _press

    def _move_for(tok):
        def _move(event):
            buttons = event.buttons()
            gp = event.globalPosition().toPoint()
            other = _tok_under_cursor(gp)
            if other is None:
                return
            pos = event.position().toPoint()
            if buttons & Qt.RightButton:
                app._bg_vis_drag(_QEvent(other, pos))
            elif buttons & Qt.LeftButton:
                app._bg_drag(_QEvent(other, pos))
        return _move

    def _release_for(tok):
        def _release(event):
            gp = event.globalPosition().toPoint()
            other = _tok_under_cursor(gp) or tok
            pos = event.position().toPoint()
            if event.button() == Qt.RightButton:
                app._bg_vis_release(_QEvent(other, pos))
            else:
                app._bg_release(_QEvent(other, pos))
        return _release

    for _tok, _btn in app._bar_map_btns.items():
        _btn.setMouseTracking(True)
        _btn.mousePressEvent = _press_for(_tok)
        _btn.mouseMoveEvent = _move_for(_tok)
        _btn.mouseReleaseEvent = _release_for(_tok)

    app._vis_rubber_win = None
    app._vis_rubber_rect = None

    sep2 = QFrame(parent)
    sep2.setObjectName("Separator")
    sep2.setFrameShape(QFrame.HLine)
    sep2.setFixedHeight(1)
    layout.addWidget(sep2)

    sa, inner = make_scrollable_canvas(parent)
    layout.addWidget(sa, 1)
    app._bar_grp_canvas = sa
    app._bar_grp_inner = inner

    app._bar_grp_count_lbl = QLabel("No groups defined", parent)
    app._bar_grp_count_lbl.setObjectName("Muted")
    layout.addWidget(app._bar_grp_count_lbl)


class _QEvent:
    """Minimal shim that looks like the legacy tk drag event used by bar_group handlers."""
    __slots__ = ("tok", "pos", "x", "y")

    def __init__(self, tok, pos):
        self.tok = tok
        self.pos = pos
        self.x = pos.x()
        self.y = pos.y()


def build_bar_perwell_strip(app, parent: QWidget) -> None:
    """Thin bar-specific sidebar strip shown when Bar Plots tab is active."""
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)

    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    lbl = QLabel("Per-well selection (fallback when no groups)", parent)
    lbl.setObjectName("Muted")
    layout.addWidget(lbl)

    row = QWidget(parent)
    rl = QHBoxLayout(row)
    rl.setContentsMargins(6, 0, 6, 4)
    all_btn = btn_primary(row, "All", app._bar_select_all)
    none_btn = btn_primary(row, "None", app._bar_select_none)
    rl.addWidget(all_btn, 1)
    rl.addWidget(none_btn, 1)
    layout.addWidget(row)


def rebuild_groups_ui_now(app) -> None:
    """Synchronous card-list rebuild + plate-map recolour."""
    app._grp_ui_pending = False
    inner = app._bar_grp_inner
    inner_layout = inner.layout()
    if inner_layout is None:
        inner_layout = QVBoxLayout(inner)
        inner.setLayout(inner_layout)
    while inner_layout.count():
        item = inner_layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()

    for idx, grp in enumerate(app._bar_groups):
        app._build_bar_group_row(idx, grp)
    update_bar_group_count_label(app)
    inner_layout.addStretch(1)
    app._bar_refresh_map()


def update_bar_group_count_label(app) -> None:
    if not hasattr(app, "_bar_grp_count_lbl"):
        return
    n_grps = len(app._bar_groups)
    n_vis = sum(1 for g in app._bar_groups if not g.hidden)
    n_hid = n_grps - n_vis
    if n_grps == 0:
        txt = "No groups defined"
    elif n_hid == 0:
        txt = f"{n_grps} group(s)  ·  all visible in bar plot"
    else:
        txt = f"{n_vis}/{n_grps} visible in bar plot  ·  {n_hid} hidden"
    app._bar_grp_count_lbl.setText(txt)


def build_bar_group_row(app, idx: int, grp) -> None:
    is_active = idx == app._bar_active_grp
    row = QWidget(app._bar_grp_inner)
    row.setProperty("variant", "group_row")
    row.setProperty("active", "true" if is_active else "false")
    row_l = QVBoxLayout(row)
    row_l.setContentsMargins(6, 4, 6, 4)

    build_bar_group_header(app, row_l, idx, grp, row)
    build_bar_group_chip_rows(app, row_l, idx, grp, is_active, row)
    if is_active:
        build_bar_group_action_row(app, row_l, idx, row)

    app._bar_grp_inner.layout().addWidget(row)

    # Select group on click on any child area
    def _click(_e, i=idx):
        app._bar_select_group(i)
    row.mousePressEvent = _click


def build_bar_group_header(app, parent_layout: QVBoxLayout, idx: int, grp, row: QWidget) -> None:
    from ui.theme.styles import _WELL_COLORS

    colors = list(_WELL_COLORS.values()) if isinstance(_WELL_COLORS, dict) else list(_WELL_COLORS)
    if not colors:
        colors = ["#5aa0ff"]

    hdr = QWidget(row)
    hl = QHBoxLayout(hdr)
    hl.setContentsMargins(0, 0, 0, 0)
    color = colors[idx % len(colors)]
    dot = QLabel("●", hdr)
    dot.setStyleSheet(f"color: {'#666' if grp.hidden else color};")
    hl.addWidget(dot)

    name_lbl = QLabel(grp.name, hdr)
    if grp.hidden:
        name_lbl.setObjectName("Muted")
    hl.addWidget(name_lbl)

    if grp.hidden:
        hid_lbl = QLabel("[hidden]", hdr)
        hid_lbl.setObjectName("Muted")
        hl.addWidget(hid_lbl)

    n_rep = len(grp.replicates) if grp.replicates else len(grp.wells)
    n_well = len(grp.wells)
    count_lbl = QLabel(
        f"({n_rep} replicate set{'s' if n_rep != 1 else ''}  ·  "
        f"{n_well} well{'s' if n_well != 1 else ''})",
        hdr,
    )
    count_lbl.setObjectName("Muted")
    hl.addWidget(count_lbl)
    hl.addStretch(1)

    def _cmd(action, i=idx):
        app._bar_active_grp = i
        action(i)

    vis_txt = "Show" if grp.hidden else "Hide"
    hl.addWidget(btn_card(hdr, vis_txt,
                          lambda: _cmd(app._bar_toggle_group_visibility, idx)))
    hl.addWidget(btn_card(hdr, "Rename",
                          lambda: _cmd(app._bar_rename_group, idx)))
    hl.addWidget(btn_card(hdr, "Clear",
                          lambda: _cmd(app._bar_clear_group, idx)))
    hl.addWidget(btn_danger(hdr, "✕",
                            lambda: _cmd(app._bar_remove_group, idx)))

    parent_layout.addWidget(hdr)


def build_bar_group_chip_rows(app, parent_layout: QVBoxLayout, idx: int, grp, is_active: bool, row: QWidget) -> None:
    if grp.replicates:
        rep_frame = QWidget(row)
        rf_l = QVBoxLayout(rep_frame)
        rf_l.setContentsMargins(0, 2, 0, 0)
        for si, rset in enumerate(grp.replicates):
            srow = QWidget(rep_frame)
            sl = QHBoxLayout(srow)
            sl.setContentsMargins(0, 2, 0, 0)
            sl.addWidget(QLabel(f"R{si+1}:", srow))
            for w in rset:
                chip = QLabel(w, srow)
                chip.setProperty("variant", "chip")
                sl.addWidget(chip)
            if is_active:
                rm = btn_danger(
                    srow, "✕",
                    lambda i=idx, s=si: app._bar_remove_replicate_set(i, s),
                )
                sl.addWidget(rm)
            sl.addStretch(1)
            rf_l.addWidget(srow)

        assigned = {w for rs in grp.replicates for w in rs}
        singles = [w for w in grp.wells if w not in assigned]
        if singles:
            singles_row = QWidget(rep_frame)
            sgl_l = QHBoxLayout(singles_row)
            sgl_l.setContentsMargins(0, 2, 0, 0)
            solo_lbl = QLabel("solo:", singles_row)
            solo_lbl.setObjectName("Muted")
            sgl_l.addWidget(solo_lbl)
            for w in singles:
                chip = QLabel(w, singles_row)
                chip.setProperty("variant", "chip_muted")
                sgl_l.addWidget(chip)
            sgl_l.addStretch(1)
            rf_l.addWidget(singles_row)
        parent_layout.addWidget(rep_frame)
    elif grp.wells:
        chips = QWidget(row)
        cl = QHBoxLayout(chips)
        cl.setContentsMargins(0, 2, 0, 0)
        for lbl in grp.wells:
            chip = QLabel(lbl, chips)
            chip.setProperty("variant", "chip")
            cl.addWidget(chip)
        cl.addStretch(1)
        parent_layout.addWidget(chips)
    else:
        empty_lbl = QLabel("No wells — assign replicates from the map", row)
        empty_lbl.setObjectName("Muted")
        parent_layout.addWidget(empty_lbl)


def build_bar_group_action_row(app, parent_layout: QVBoxLayout, idx: int, row: QWidget) -> None:
    act_frame = QWidget(row)
    al = QHBoxLayout(act_frame)
    al.setContentsMargins(0, 4, 0, 4)
    al.addWidget(btn_card(act_frame, "+ Add replicate set",
                          lambda: app._bar_add_replicate_set(idx)))
    al.addWidget(btn_card(act_frame, "Clear replicates",
                          lambda: app._bar_clear_replicates(idx)))
    al.addStretch(1)
    parent_layout.addWidget(act_frame)
