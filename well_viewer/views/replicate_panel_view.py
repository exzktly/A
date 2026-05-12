"""Replicate panel builder (Qt port)."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, btn_secondary, make_scrollable_canvas,
)
from well_viewer.views.well_button import build_plate_grid


def _drag_info(tok, pos):
    return SimpleNamespace(tok=tok, pos=pos, x=pos.x(), y=pos.y())


def build_replicate_panel(app, parent: QWidget) -> None:
    """Left panel: define named ReplicateSets from the global well pool."""

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    # Plate map first — nothing should appear above it.
    rep_map_outer = QWidget(parent)
    layout.addWidget(rep_map_outer)
    app._rep_map_btns: dict = {}
    build_plate_grid(rep_map_outer, app._rep_map_btns)

    top_sep = QFrame(parent)
    top_sep.setFrameShape(QFrame.HLine)
    top_sep.setFixedHeight(1)
    layout.addWidget(top_sep)

    hdr = QWidget(parent)
    hdr_l = QHBoxLayout(hdr)
    hdr_l.setContentsMargins(8, 4, 8, 4)
    layout.addWidget(hdr)
    hdr_lbl = QLabel("GROUPS", hdr)
    hdr_lbl.setProperty("role", "section")
    hdr_l.addWidget(hdr_lbl)
    hdr_l.addStretch(1)
    hdr_l.addWidget(btn_secondary(hdr, "Clear All", app._rep_clear_all))
    hdr_l.addWidget(btn_primary(hdr, "+ Add", app._rep_add))

    # Quick Replicates dropdowns
    hdr2r = QWidget(parent)
    hdr2r_l = QHBoxLayout(hdr2r)
    hdr2r_l.setContentsMargins(8, 4, 8, 4)
    layout.addWidget(hdr2r)

    pair_lbl = QLabel("Pair:", hdr2r)
    hdr2r_l.addWidget(pair_lbl)
    app._rep_quick_pair_dir_cb = QComboBox(hdr2r)
    app._rep_quick_pair_dir_cb.addItems(["Rows (A01+A02)", "Columns (A01+B01)"])
    app._rep_quick_pair_dir_cb.setCurrentText("Rows (A01+A02)")
    hdr2r_l.addWidget(app._rep_quick_pair_dir_cb)
    app._rep_quick_pair_dir_var = app._rep_quick_pair_dir_cb

    order_lbl = QLabel("Order:", hdr2r)
    hdr2r_l.addWidget(order_lbl)
    app._rep_quick_iter_order_cb = QComboBox(hdr2r)
    app._rep_quick_iter_order_cb.addItems(["Across rows", "Down columns"])
    app._rep_quick_iter_order_cb.setCurrentText("Across rows")
    hdr2r_l.addWidget(app._rep_quick_iter_order_cb)
    app._rep_quick_iter_order_var = app._rep_quick_iter_order_cb
    hdr2r_l.addStretch(1)

    btn_row = QWidget(parent)
    btn_row_l = QHBoxLayout(btn_row)
    btn_row_l.setContentsMargins(8, 2, 8, 2)
    layout.addWidget(btn_row)
    btn_row_l.addWidget(btn_primary(btn_row, "Apply Quick Replicates",
                                    app._rep_quick_pairs_from_dropdowns))
    btn_row_l.addStretch(1)

    # Per-button mouse handlers: enabled buttons consume events instead of
    # bubbling to a parent-level handler, so we install press/move/release
    # on each well button directly.
    def _tok_under_cursor(global_pos):
        for t, b in app._rep_map_btns.items():
            try:
                local = b.mapFromGlobal(global_pos)
                if b.rect().contains(local):
                    return t
            except Exception:
                continue
        return None

    def _make_btn_handlers(tok, btn):
        def _press(event):
            if event.button() != Qt.LeftButton:
                return
            pos = event.position().toPoint()
            app._rep_map_press(_drag_info(tok, pos))

        def _move(event):
            if not (event.buttons() & Qt.LeftButton):
                return
            gp = event.globalPosition().toPoint()
            other = _tok_under_cursor(gp)
            if other is None:
                return
            app._rep_map_drag(_drag_info(other, event.position().toPoint()))

        def _release(event):
            app._rep_map_release(None)

        btn.setMouseTracking(True)
        btn.mousePressEvent = _press
        btn.mouseMoveEvent = _move
        btn.mouseReleaseEvent = _release

    for _tok, _btn in app._rep_map_btns.items():
        _make_btn_handlers(_tok, _btn)

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # v2 (Phase 8.0 Stage C): the groups card-list is a widgets.SavedSelectionsList
    # (composable) over app._selections. (The legacy _rep_canvas/_rep_inner +
    # grouping_view.rep_panel_refresh card rendering are retired.)
    from widgets.saved_selections_list import SavedSelectionsList
    from well_viewer.views.grouping_view import wire_selections_list as _wire
    app._rep_list = SavedSelectionsList(parent)
    app._rep_list.setComposable(True)
    layout.addWidget(app._rep_list, 1)
    _wire(app, app._rep_list)

    hint = QLabel(
        "Select a group, then drag wells on the map to add/remove them. "
        "Expand a group to edit its replicate structure.",
        parent,
    )
    hint.setObjectName("Muted")
    hint.setWordWrap(True)
    layout.addWidget(hint)
