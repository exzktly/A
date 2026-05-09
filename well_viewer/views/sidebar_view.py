"""Main well-picker sidebar builder (Qt port)."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


def _drag_info(tok, pos):
    return SimpleNamespace(tok=tok, pos=pos, x=pos.x(), y=pos.y())


def _row_col_select_disabled(app) -> bool:
    """Tabs that don't support multi-well selection (smFISH) suppress the
    row/column header click handlers."""
    nb = getattr(app, "_notebook", None)
    if nb is None:
        return False
    try:
        return nb.tabText(nb.currentIndex()) == "smFISH"
    except Exception:
        return False


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
    from well_viewer.plate_layout import PLATE_ROWS as _PLATE_ROWS, PLATE_COLS as _PLATE_COLS
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

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # Plate map grid — padding is set uniformly inside build_plate_grid.
    # The row letters / column numbers in the grid headers double as the
    # row-or-column quick-select buttons via the ``on_row_click`` /
    # ``on_col_click`` callbacks below.
    map_outer = QWidget(parent)
    layout.addWidget(map_outer)

    app._sidebar_btns = {}
    app._sidebar_drag_adding = True
    app._sidebar_drag_visited = set()
    app._sb_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    app._bg_ds = {"adding": True, "visited": set(), "rep_toggled": set()}

    def _on_row_click(row: str) -> None:
        if _row_col_select_disabled(app):
            return
        app._select_row(row)

    def _on_col_click(col: str) -> None:
        if _row_col_select_disabled(app):
            return
        app._select_col(col)

    build_plate_grid(
        map_outer,
        app._sidebar_btns,
        on_row_click=_on_row_click,
        on_col_click=_on_col_click,
    )
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
        # Hold the WellButton's own mouse handlers so we can fall through
        # to its built-in drag-source logic when the heat-map drag mode is
        # active (set via ``btn.set_drag_mime(...)``). Without this fall-
        # through, the selection handlers below would swallow the press
        # before QDrag could start.
        base_press = type(btn).mousePressEvent
        base_move = type(btn).mouseMoveEvent
        base_release = type(btn).mouseReleaseEvent

        def _press(event):
            if getattr(btn, "_drag_mime", None):
                base_press(btn, event)
                return
            if event.button() != Qt.LeftButton:
                return
            pos = event.position().toPoint()
            app._sb_press(_drag_info(tok, pos))

        def _move(event):
            if getattr(btn, "_drag_mime", None):
                base_move(btn, event)
                return
            if not (event.buttons() & Qt.LeftButton):
                return
            global_pos = event.globalPosition().toPoint()
            other_tok = _tok_under_cursor(global_pos)
            if other_tok is None:
                return
            app._sb_drag(_drag_info(other_tok, event.position().toPoint()))

        def _release(event):
            if getattr(btn, "_drag_mime", None):
                base_release(btn, event)
                return
            app._sb_release(None)

        btn.setMouseTracking(True)
        btn.mousePressEvent = _press
        btn.mouseMoveEvent = _move
        btn.mouseReleaseEvent = _release

    for _tok, _btn in app._sidebar_btns.items():
        _make_btn_handlers(_tok, _btn)

    # All / None buttons
    br = QWidget(parent)
    br_l = QHBoxLayout(br)
    br_l.setContentsMargins(6, 4, 6, 6)
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

    # Heat-map layout configurator (sidebar variant). Hidden by default;
    # ``_on_tab_change`` reveals it when the Heat Map tab is active.
    from well_viewer.views.heatmap_layout_sidebar_view import (
        build_heatmap_layout_sidebar,
    )
    heatmap_frame = build_heatmap_layout_sidebar(app, parent)
    heatmap_frame.setVisible(False)

    # Absorb leftover vertical space so the well picker stays pinned to the
    # top of the sidebar even when the sidebar is taller than its contents.
    layout.addStretch(1)
