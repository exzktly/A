"""Replicate panel builder (Qt port).

Sample Definitions tab is split between three places:

  - **Left sidebar** (this module, ``build_replicate_panel``): the plate
    map only. Clicking a well edits the *current* selection's well
    membership.
  - **Centre — Groups sub-tab** (``build_replicate_groups_centre``): the
    GROUPS header, Quick Replicates row, and the editable
    SavedSelectionsList over ``app._selections``. Hoisted out of the
    sidebar so the user has full vertical room for the list and the
    plate keeps its proper aspect ratio.
  - **Centre — Well Labels sub-tab**: see ``label_grid_view``.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import btn_primary, btn_secondary


def build_replicate_panel(app, parent: QWidget) -> None:
    """Sample-Definitions LEFT sidebar: the plate map only.

    The GROUPS panel (header + Quick Replicates + SavedSelectionsList +
    hint line) lives in the centre area now; see
    ``build_replicate_groups_centre``.
    """

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    from widgets.well_plate_selector import WellPlateSelector
    from PySide6.QtWidgets import QSizePolicy as _SizePolicy
    plate = WellPlateSelector(parent)
    plate.setActionsVisible(False)
    plate.setSelectionMode("select")
    plate.setDragSelectEnabled(True)
    plate.setRowColumnSelectable(True)
    plate.setEnabledWells([])
    # The plate is the only widget in this sidebar now — give it room to
    # expand vertically with the column. heightForWidth keeps the aspect.
    plate.setMinimumHeight(280)
    sp = _SizePolicy(_SizePolicy.Preferred, _SizePolicy.MinimumExpanding)
    sp.setHeightForWidth(True)
    plate.setSizePolicy(sp)
    layout.addWidget(plate, 1)
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

    hint = QLabel(
        "Click a well to add/remove it from the current group. Use the "
        "row letter or column number to select a whole row/column.",
        parent,
    )
    hint.setObjectName("Muted")
    hint.setWordWrap(True)
    hint.setContentsMargins(8, 6, 8, 6)
    layout.addWidget(hint)


def build_replicate_groups_centre(app, parent: QWidget) -> None:
    """Sample-Definitions CENTRE — Groups sub-tab.

    Hoists the legacy "below the plate" GROUPS chrome out of the sidebar.
    Contents (top → bottom):
      - GROUPS header with Clear-all / + Add buttons
      - Quick Replicates row (Pair + Order dropdowns + Apply button)
      - SavedSelectionsList (composable) over ``app._selections``
      - 1-line usage hint
    """
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    hdr = QWidget(parent)
    hdr_l = QHBoxLayout(hdr)
    hdr_l.setContentsMargins(10, 8, 10, 4)
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
    hdr2r_l.setContentsMargins(10, 4, 10, 4)
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
    hdr2r_l.addWidget(btn_primary(hdr2r, "Apply Quick Replicates",
                                  app._rep_quick_pairs_from_dropdowns))

    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # The groups card-list — a widgets.SavedSelectionsList (composable)
    # over app._selections.
    from widgets.saved_selections_list import SavedSelectionsList
    from well_viewer.views.grouping_view import wire_selections_list as _wire
    app._rep_list = SavedSelectionsList(parent)
    app._rep_list.setComposable(True)
    layout.addWidget(app._rep_list, 1)
    _wire(app, app._rep_list)

    hint = QLabel(
        "Select a group, then click wells on the plate map (left sidebar) "
        "to add/remove them. Expand a group to edit its replicate structure.",
        parent,
    )
    hint.setObjectName("Muted")
    hint.setWordWrap(True)
    hint.setContentsMargins(10, 6, 10, 8)
    layout.addWidget(hint)
