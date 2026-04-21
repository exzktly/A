"""Main well-picker sidebar builder (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class _QEvent:
    """Minimal shim mirroring the legacy tk drag event shape."""
    __slots__ = ("tok", "pos", "x", "y")

    def __init__(self, tok, pos):
        self.tok = tok
        self.pos = pos
        self.x = pos.x()
        self.y = pos.y()


def build_sidebar(app, parent: QWidget) -> None:
    """Build the 8x12 plate-map well selector in the sidebar.

    Creates:
      - Italic "Plate" heading with well-count meta
      - Row/Col quick-select buttons (A-H, 01-12)
      - 8x12 WellButton plate-map grid with drag-to-select bindings
      - All / None buttons
      - Selected-well count label
      - Group-mode hint label
    """
    from well_viewer.runtime_app import _PLATE_ROWS, _PLATE_COLS
    from well_viewer.views.well_button import build_plate_grid

    # Mark the parent container as Sidebar so QSS can target it
    parent.setObjectName("Sidebar")

    # Ensure parent has a vertical layout
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    # ── Plate heading ─────────────────────────────────────────────────────
    head_row = QHBoxLayout()
    head_row.setContentsMargins(16, 14, 16, 0)
    hdr = QLabel("Plate", parent)
    hdr.setObjectName("SideHead")
    head_row.addWidget(hdr)
    head_row.addStretch()
    meta = QLabel("96 wells · 8×12", parent)
    meta.setObjectName("Meta")
    head_row.addWidget(meta)
    layout.addLayout(head_row)

    sub = QLabel("Drag to select · shift-click for replicates.", parent)
    sub.setObjectName("SideMut")
    sub.setContentsMargins(16, 4, 16, 10)
    layout.addWidget(sub)

    # ── Row / Col quick-select ────────────────────────────────────────────
    rc_frame = QWidget(parent)
    rc_layout = QVBoxLayout(rc_frame)
    rc_layout.setContentsMargins(14, 0, 14, 4)
    rc_layout.setSpacing(2)
    layout.addWidget(rc_frame)
    app._sidebar_rc_frame = rc_frame

    row_frame = QWidget(rc_frame)
    row_grid = QGridLayout(row_frame)
    row_grid.setContentsMargins(0, 0, 0, 0)
    row_grid.setSpacing(2)
    row_lbl = QLabel("Row", row_frame)
    row_lbl.setObjectName("Meta")
    row_grid.addWidget(row_lbl, 0, 0)
    for ci, r in enumerate(_PLATE_ROWS):
        b = QPushButton(r, row_frame)
        b.setObjectName("RcBtn")
        b.setFixedHeight(22)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, row=r: app._select_row(row))
        row_grid.addWidget(b, 0, ci + 1)
    for ci in range(1, len(_PLATE_ROWS) + 1):
        row_grid.setColumnStretch(ci, 1)
    rc_layout.addWidget(row_frame)

    col_frame = QWidget(rc_frame)
    col_grid = QGridLayout(col_frame)
    col_grid.setContentsMargins(0, 0, 0, 0)
    col_grid.setSpacing(2)
    col_lbl = QLabel("Col", col_frame)
    col_lbl.setObjectName("Meta")
    col_grid.addWidget(col_lbl, 0, 0)
    for ci, c in enumerate(_PLATE_COLS):
        b = QPushButton(c.lstrip("0") or "0", col_frame)
        b.setObjectName("RcBtn")
        b.setFixedHeight(22)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, col=c: app._select_col(col))
        col_grid.addWidget(b, 0, ci + 1)
    for ci in range(1, len(_PLATE_COLS) + 1):
        col_grid.setColumnStretch(ci, 1)
    rc_layout.addWidget(col_frame)

    # ── Plate card (rounded card wrapping the grid) ───────────────────────
    plate_card = QFrame(parent)
    plate_card.setObjectName("PlateCard")
    plate_card_lay = QVBoxLayout(plate_card)
    plate_card_lay.setContentsMargins(10, 10, 10, 10)

    # Plate map grid lives inside the card
    map_outer = QWidget(plate_card)
    plate_card_lay.addWidget(map_outer)

    wrap = QWidget(parent)
    wrap_lay = QVBoxLayout(wrap)
    wrap_lay.setContentsMargins(14, 4, 14, 0)
    wrap_lay.addWidget(plate_card)
    layout.addWidget(wrap)

    app._sidebar_btns = {}
    app._sidebar_drag_adding = True
    app._sidebar_drag_visited = set()
    app._sb_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    app._bg_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    build_plate_grid(map_outer, app._sidebar_btns)
    app._sidebar_map_outer = map_outer

    def _tok_under_cursor(global_pos):
        """Find which sidebar well-button contains ``global_pos``."""
        for tok, btn in app._sidebar_btns.items():
            try:
                local = btn.mapFromGlobal(global_pos)
                if btn.rect().contains(local):
                    return tok
            except Exception:
                continue
        return None

    def _make_btn_handlers(tok, btn):
        def _press(event):
            if event.button() != Qt.LeftButton:
                return
            pos = event.position().toPoint()
            app._sb_press(_QEvent(tok, pos))

        def _move(event):
            if not (event.buttons() & Qt.LeftButton):
                return
            global_pos = event.globalPosition().toPoint()
            other_tok = _tok_under_cursor(global_pos)
            if other_tok is None:
                return
            app._sb_drag(_QEvent(other_tok, event.position().toPoint()))

        def _release(event):
            app._sb_release(None)

        btn.setMouseTracking(True)
        btn.mousePressEvent = _press
        btn.mouseMoveEvent = _move
        btn.mouseReleaseEvent = _release

    for _tok, _btn in app._sidebar_btns.items():
        _make_btn_handlers(_tok, _btn)

    # Count + clear row (below plate card)
    foot = QWidget(parent)
    foot_l = QHBoxLayout(foot)
    foot_l.setContentsMargins(16, 6, 16, 10)
    foot_l.setSpacing(8)

    app._sel_count_lbl = QLabel("", foot)
    app._sel_count_lbl.setObjectName("Meta")
    foot_l.addWidget(app._sel_count_lbl)
    foot_l.addStretch()

    # All / None buttons
    br = QWidget(foot)
    br_l = QHBoxLayout(br)
    br_l.setContentsMargins(0, 0, 0, 0)
    br_l.setSpacing(4)
    for txt, cmd in (("All", app._select_all), ("None", app._select_none)):
        b = QPushButton(txt, br)
        b.setProperty("variant", "secondary")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, c=cmd: c())
        br_l.addWidget(b)
    foot_l.addWidget(br)
    app._sidebar_allnone_frame = br

    layout.addWidget(foot)

    # Group-mode hint
    app._line_group_hint = QLabel("", parent)
    app._line_group_hint.setObjectName("Accent")
    app._line_group_hint.setWordWrap(True)
    layout.addWidget(app._line_group_hint)

    # Absorb leftover vertical space so the well picker stays pinned to the
    # top of the sidebar even when the sidebar is taller than its contents.
    layout.addStretch(1)
