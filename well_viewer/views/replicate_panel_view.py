"""Replicate panel builder (Qt port)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import btn_primary, btn_secondary


def build_replicate_panel(app, parent: QWidget) -> None:
    """Left panel of the Sample Definitions tab: the GROUPS list (a composable
    ``widgets.SavedSelectionsList`` over ``app._selections``) plus the plate-map
    that edits the *current* selection's well membership."""

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    # Plate map first — nothing should appear above it.
    from widgets.well_plate_selector import WellPlateSelector
    from PySide6.QtWidgets import QSizePolicy as _SizePolicy
    plate = WellPlateSelector(parent)
    plate.setActionsVisible(False)
    plate.setSelectionMode("select")
    plate.setDragSelectEnabled(True)
    plate.setRowColumnSelectable(True)
    plate.setEnabledWells([])
    # The plate sits above the GROUPS list in this panel; without a floor
    # the V layout shrinks it to its minimumSizeHint when the centre column
    # is short, crushing the wells. Anchor a generous minimum height and
    # let WellPlateSelector.heightForWidth keep the aspect.
    plate.setMinimumHeight(280)
    sp = _SizePolicy(_SizePolicy.Preferred, _SizePolicy.MinimumExpanding)
    sp.setHeightForWidth(True)
    plate.setSizePolicy(sp)
    layout.addWidget(plate)
    app._rep_map_plate = plate

    def _commit_plate_to_current(*_a) -> None:
        sid = getattr(app, "_current_selection_id", None)
        sel = app._sel_by_id(sid) if sid else None
        if sel is None:
            app._rep_refresh_map()      # no current selection — revert the click
            return
        new = sorted((w for w in plate.selectedWellIds() if w in app._well_paths),
                     key=app._parse_rc)
        old = sorted((w for w in (sel.get("wells") or []) if w in app._well_paths),
                     key=app._parse_rc)
        if new == old:
            return
        # _sel_set_composition enforces well-exclusivity (the current group wins)
        # and runs _rebuild_all(), which re-pushes the plate via _rep_refresh_map.
        app._sel_set_composition(sid, new)
    # selectionDragFinished fires once per click *and* once at the end of a drag.
    plate.selectionDragFinished.connect(_commit_plate_to_current)

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
