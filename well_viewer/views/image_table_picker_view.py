"""Image Table tab — sidebar plate-map picker (Qt port).

Multi-select well picker that explicitly ignores replicate sets and bar
groups. State is held in ``app._image_table_active_wells`` (a ``set`` of
well tokens). Wells render in three states:

- ``empty``      — token not present in ``app._well_paths``
- ``available``  — loaded but not currently selected
- ``selected``   — present in ``_image_table_active_wells``
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


def build_image_table_picker(app, parent: QWidget) -> None:
    """Compact plate-map picker for the Image Table tab sidebar."""
    from well_viewer.views.well_button import build_plate_grid

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    map_f = QWidget(parent)
    layout.addWidget(map_f)
    app._sidebar_image_table_btns = {}

    def _toggle_active(wells: list[str]) -> None:
        wells = [w for w in wells if w in app._well_paths]
        if not wells:
            return
        active = app._image_table_active_wells
        if any(w not in active for w in wells):
            active.update(wells)
        else:
            active.difference_update(wells)
        app._image_table_refresh_picker()

    def _on_row_click(row: str) -> None:
        _toggle_active([w for w in app._well_paths if app._parse_rc(w)[0] == row])

    def _on_col_click(col: str) -> None:
        _toggle_active([w for w in app._well_paths if app._parse_rc(w)[1] == col])

    build_plate_grid(
        map_f,
        app._sidebar_image_table_btns,
        on_click=lambda t: app._image_table_pick_well(t),
        on_row_click=_on_row_click,
        on_col_click=_on_col_click,
    )

    btn_row = QWidget(parent)
    bl = QHBoxLayout(btn_row)
    bl.setContentsMargins(6, 2, 6, 2)
    bl.setSpacing(4)

    select_all = QPushButton("Select All", btn_row)
    select_all.setProperty("variant", "secondary")
    select_all.clicked.connect(lambda _=False: app._image_table_select_all())
    bl.addWidget(select_all)

    clear_btn = QPushButton("Clear", btn_row)
    clear_btn.setProperty("variant", "secondary")
    clear_btn.clicked.connect(lambda _=False: app._image_table_clear_active())
    bl.addWidget(clear_btn)
    bl.addStretch(1)
    layout.addWidget(btn_row)

    app._image_table_count_lbl = QLabel("0 wells active", parent)
    app._image_table_count_lbl.setObjectName("Muted")
    app._image_table_count_lbl.setAlignment(Qt.AlignLeft)
    layout.addWidget(app._image_table_count_lbl)

    layout.addStretch(1)

    help_lbl = QLabel(
        "Click wells to mark active. Use 'Distribute Wells' to assign "
        "them row-wise to table cells.", parent,
    )
    help_lbl.setObjectName("Muted")
    help_lbl.setWordWrap(True)
    layout.addWidget(help_lbl)
