"""Main well-picker sidebar builder (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


def build_sidebar(app, parent: QWidget) -> None:
    """Build the 8x12 plate-map well selector in the sidebar.

    Creates:
      - "WELLS" header
      - Row/Col quick-select buttons (A-H, 01-12)
      - 8x12 WellButton plate-map grid with drag-to-select bindings
      - All / None buttons
      - Selected-well count label
      - Group-mode hint label
    """
    from well_viewer.runtime_app import _PLATE_ROWS, _PLATE_COLS
    from well_viewer.views.well_button import build_plate_grid

    # Ensure parent has a vertical layout
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    hdr = QLabel("WELLS", parent)
    hdr.setObjectName("SidebarHeader")
    hdr.setProperty("role", "header")
    layout.addWidget(hdr)

    # Row / Col quick-select
    rc_frame = QWidget(parent)
    rc_layout = QVBoxLayout(rc_frame)
    rc_layout.setContentsMargins(4, 0, 4, 2)
    rc_layout.setSpacing(1)
    layout.addWidget(rc_frame)
    app._sidebar_rc_frame = rc_frame

    row_frame = QWidget(rc_frame)
    row_grid = QGridLayout(row_frame)
    row_grid.setContentsMargins(0, 0, 0, 0)
    row_grid.setSpacing(1)
    row_lbl = QLabel("Row:", row_frame)
    row_lbl.setObjectName("Muted")
    row_grid.addWidget(row_lbl, 0, 0)
    for ci, r in enumerate(_PLATE_ROWS):
        b = QPushButton(r, row_frame)
        b.setProperty("variant", "quickselect")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, row=r: app._select_row(row))
        row_grid.addWidget(b, 0, ci + 1)
    for ci in range(1, len(_PLATE_ROWS) + 1):
        row_grid.setColumnStretch(ci, 1)
    rc_layout.addWidget(row_frame)

    col_frame = QWidget(rc_frame)
    col_grid = QGridLayout(col_frame)
    col_grid.setContentsMargins(0, 0, 0, 0)
    col_grid.setSpacing(1)
    col_lbl = QLabel("Col:", col_frame)
    col_lbl.setObjectName("Muted")
    col_grid.addWidget(col_lbl, 0, 0)
    for ci, c in enumerate(_PLATE_COLS):
        b = QPushButton(c.lstrip("0") or "0", col_frame)
        b.setProperty("variant", "quickselect")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, col=c: app._select_col(col))
        col_grid.addWidget(b, 0, ci + 1)
    for ci in range(1, len(_PLATE_COLS) + 1):
        col_grid.setColumnStretch(ci, 1)
    rc_layout.addWidget(col_frame)

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # Plate map grid
    map_outer = QWidget(parent)
    layout.addWidget(map_outer)

    app._sidebar_btns = {}
    app._sidebar_drag_adding = True
    app._sidebar_drag_visited = set()
    app._sb_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    app._bg_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    def _on_sidebar_well_click(tok: str) -> None:
        # Single-click path for Qt: apply one-cell toggle through the shared
        # drag-engine so rep-mode/per-well mode behavior stays identical.
        app._plate_drag_press(tok, app._selected_wells, app._sb_ds)
        app._plate_drag_apply(tok, app._sidebar_btns, app._selected_wells, app._sb_ds)
        app._plate_drag_release(
            app._sb_ds,
            on_rep_change=app._sb_on_rep_change,
            on_well_change=app._on_plate_sel_change,
        )
        app._sb_ds["visited"] = set()

    build_plate_grid(map_outer, app._sidebar_btns, on_click=_on_sidebar_well_click)
    # NOTE: drag bindings — runtime_app must bind to the plate map via mouse
    # event overrides; the legacy _bind_drag helper is not used in Qt.

    # All / None buttons
    br = QWidget(parent)
    br_l = QHBoxLayout(br)
    br_l.setContentsMargins(4, 2, 4, 4)
    br_l.setSpacing(3)
    layout.addWidget(br)
    app._sidebar_allnone_frame = br
    for txt, cmd in (("All", app._select_all), ("None", app._select_none)):
        b = QPushButton(txt, br)
        b.setProperty("variant", "primary-dark")
        b.clicked.connect(lambda _=False, c=cmd: c())
        br_l.addWidget(b, 1)

    # Selected well count label
    app._sel_count_lbl = QLabel("", parent)
    app._sel_count_lbl.setObjectName("Muted")
    layout.addWidget(app._sel_count_lbl)

    # Group-mode hint
    app._line_group_hint = QLabel("", parent)
    app._line_group_hint.setObjectName("Accent")
    app._line_group_hint.setWordWrap(True)
    layout.addWidget(app._line_group_hint)
