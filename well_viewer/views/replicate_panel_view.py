"""Replicate panel builder (Qt port)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, btn_secondary, ComboVar, make_scrollable_canvas,
)
from well_viewer.views.well_button import build_plate_grid


def build_replicate_panel(app, parent: QWidget) -> None:
    """Left panel: define named ReplicateSets from the global well pool."""

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    top_sep = QFrame(parent)
    top_sep.setFrameShape(QFrame.HLine)
    top_sep.setFixedHeight(1)
    layout.addWidget(top_sep)

    hdr = QWidget(parent)
    hdr_l = QHBoxLayout(hdr)
    hdr_l.setContentsMargins(8, 4, 8, 4)
    layout.addWidget(hdr)
    hdr_lbl = QLabel("REPLICATE SETS", hdr)
    hdr_lbl.setProperty("role", "section")
    hdr_l.addWidget(hdr_lbl)
    hdr_l.addStretch(1)
    hdr_l.addWidget(btn_secondary(hdr, "Clear All", app._rep_clear_all))
    hdr_l.addWidget(btn_primary(hdr, "+ Add", app._rep_add))

    # Second row: Quick Replicates dropdowns
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
    app._rep_quick_pair_dir_var = ComboVar(app._rep_quick_pair_dir_cb)

    order_lbl = QLabel("Order:", hdr2r)
    hdr2r_l.addWidget(order_lbl)
    app._rep_quick_iter_order_cb = QComboBox(hdr2r)
    app._rep_quick_iter_order_cb.addItems(["Across rows", "Down columns"])
    app._rep_quick_iter_order_cb.setCurrentText("Across rows")
    hdr2r_l.addWidget(app._rep_quick_iter_order_cb)
    app._rep_quick_iter_order_var = ComboVar(app._rep_quick_iter_order_cb)
    hdr2r_l.addStretch(1)

    btn_row = QWidget(parent)
    btn_row_l = QHBoxLayout(btn_row)
    btn_row_l.setContentsMargins(8, 2, 8, 2)
    layout.addWidget(btn_row)
    btn_row_l.addWidget(btn_primary(btn_row, "Apply Quick Replicates",
                                    app._rep_quick_pairs_from_dropdowns))
    btn_row_l.addStretch(1)

    hint = QLabel(
        "Select a set below, then drag wells on the map to add/remove.",
        parent,
    )
    hint.setObjectName("Muted")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    # Plate map
    rep_map_outer = QWidget(parent)
    layout.addWidget(rep_map_outer)
    app._rep_map_btns: dict = {}
    build_plate_grid(rep_map_outer, app._rep_map_btns)
    # NOTE: drag bindings handled in runtime_app via mouse events.

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    sf = QWidget(parent)
    sf_l = QVBoxLayout(sf)
    sf_l.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(sf, 1)
    app._rep_canvas, app._rep_inner = make_scrollable_canvas(sf)
    sf_l.addWidget(app._rep_canvas)
