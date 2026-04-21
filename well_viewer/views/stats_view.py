"""Statistics-tab UI builders (Qt port)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QTextEdit,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, btn_secondary, build_hline_separator, build_section_header,
)


def build_stats_tab(app, parent: QWidget, **_kw) -> None:
    app._stats_groups = []
    app._stats_active_grp = -1
    app._build_stats_results_panel(parent)


def build_stats_group_editor(app, parent: QWidget, **_kw) -> None:
    """Build the left-hand statistics group editor."""
    from well_viewer.ui_helpers import make_scrollable_canvas
    from well_viewer.views.well_button import build_plate_grid

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    hdr = build_section_header(
        parent,
        "COMPARISON GROUPS",
        buttons=(
            btn_secondary(parent, "Clear All", app._stats_grp_clear_all),
            btn_primary(parent, "+ Add", app._stats_grp_add),
        ),
    )
    layout.addWidget(hdr)
    layout.addWidget(build_hline_separator(parent))

    help_lbl = QLabel(
        "Drag wells to assign them to a group. Select a group card first.",
        parent,
    )
    help_lbl.setObjectName("Muted")
    help_lbl.setWordWrap(True)
    layout.addWidget(help_lbl)

    # Plate map — padding is set uniformly inside build_plate_grid.
    map_frame = QWidget(parent)
    layout.addWidget(map_frame)
    app._stats_map_btns = {}
    build_plate_grid(map_frame, app._stats_map_btns)

    app._stats_drag_adding = True
    app._stats_drag_visited = set()

    # Per-button drag handlers: enabled QPushButtons consume mouse events,
    # so parent-level handlers never fire. Install on each well button.
    def _tok_under_cursor(global_pos):
        for tok, btn in app._stats_map_btns.items():
            try:
                local = btn.mapFromGlobal(global_pos)
                if btn.rect().contains(local):
                    return tok
            except Exception:
                continue
        return None

    def _press_for(tok):
        def _press(event):
            if event.button() != Qt.LeftButton:
                return
            if tok not in app._well_paths:
                return
            grp = app._stats_active_group()
            if grp is None:
                return
            app._stats_drag_adding = tok not in grp.wells
            app._stats_drag_visited = set()
            app._stats_apply_drag(tok)
        return _press

    def _move_for(_tok):
        def _move(event):
            if not (event.buttons() & Qt.LeftButton):
                return
            other = _tok_under_cursor(event.globalPosition().toPoint())
            if other and other not in app._stats_drag_visited:
                app._stats_apply_drag(other)
        return _move

    def _release_for(_tok):
        def _release(_event):
            if app._stats_drag_visited:
                app._stats_refresh_map()
                app._stats_refresh_group_list()
            app._stats_drag_visited = set()
        return _release

    for _tok, _btn in app._stats_map_btns.items():
        _btn.setMouseTracking(True)
        _btn.mousePressEvent = _press_for(_tok)
        _btn.mouseMoveEvent = _move_for(_tok)
        _btn.mouseReleaseEvent = _release_for(_tok)

    sep2 = QFrame(parent)
    sep2.setObjectName("Separator")
    sep2.setFrameShape(QFrame.HLine)
    sep2.setFixedHeight(1)
    layout.addWidget(sep2)

    sa, inner = make_scrollable_canvas(parent)
    layout.addWidget(sa, 1)
    app._stats_grp_canvas = sa
    app._stats_grp_inner = inner

    app._stats_refresh_map()
    app._stats_refresh_group_list()


def build_stats_results_panel(app, parent: QWidget, **_kw) -> None:
    """Build the right-hand stats controls/results panel."""
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    app._stats_hdr = QWidget(parent)
    app._stats_hdr.setObjectName("Sidebar")
    hl = QHBoxLayout(app._stats_hdr)
    hl.setContentsMargins(12, 4, 12, 4)
    app._stats_hdr_label = QLabel("STATISTICAL TEST", app._stats_hdr)
    app._stats_hdr_label.setProperty("role", "section")
    hl.addWidget(app._stats_hdr_label)
    hl.addStretch(1)
    layout.addWidget(app._stats_hdr)

    app._stats_ctrl = QWidget(parent)
    cl = QGridLayout(app._stats_ctrl)
    cl.setContentsMargins(12, 6, 12, 6)

    app._stats_test_label = QLabel("Test:", app._stats_ctrl)
    cl.addWidget(app._stats_test_label, 0, 0, Qt.AlignLeft)

    app._stats_test_cb = QComboBox(app._stats_ctrl)
    app._stats_test_cb.addItems([
        "t-test (Fisher)",
        "Wilcoxon rank-sum",
        "Mann-Whitney U",
        "KS test (2 wells only)",
    ])
    app._stats_test_cb.setCurrentText("t-test (Fisher)")
    app._stats_test_cb.currentIndexChanged.connect(
        lambda _i: app._stats_on_test_change()
    )
    cl.addWidget(app._stats_test_cb, 0, 1, Qt.AlignLeft)

    app._stats_tp_label = QLabel("Timepoint:", app._stats_ctrl)
    cl.addWidget(app._stats_tp_label, 1, 0, Qt.AlignLeft)

    app._stats_tp_cb = QComboBox(app._stats_ctrl)
    app._stats_tp_cb.addItems(["—"])
    cl.addWidget(app._stats_tp_cb, 1, 1, Qt.AlignLeft)

    run_btn = btn_primary(app._stats_ctrl, "Run test", app._stats_run)
    cl.addWidget(run_btn, 0, 2, 2, 1)
    layout.addWidget(app._stats_ctrl)

    app._stats_sep = QFrame(parent)
    app._stats_sep.setObjectName("Separator")
    app._stats_sep.setFrameShape(QFrame.HLine)
    app._stats_sep.setFixedHeight(1)
    layout.addWidget(app._stats_sep)

    app._stats_fig_frame = QWidget(parent)
    ff_l = QVBoxLayout(app._stats_fig_frame)
    ff_l.setContentsMargins(0, 0, 0, 0)

    from matplotlib.figure import Figure as _StatsFigure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _StatsFCA

    app._stats_fig = _StatsFigure(figsize=(5, 2.8), dpi=96)
    app._stats_ax = app._stats_fig.add_subplot(111)
    app._stats_canvas_widget = _StatsFCA(app._stats_fig)
    ff_l.addWidget(app._stats_canvas_widget)
    layout.addWidget(app._stats_fig_frame)

    app._stats_res_frame = QWidget(parent)
    rl = QVBoxLayout(app._stats_res_frame)
    rl.setContentsMargins(12, 6, 12, 6)
    app._stats_result_text = QTextEdit(app._stats_res_frame)
    app._stats_result_text.setReadOnly(True)
    app._stats_result_text.setLineWrapMode(QTextEdit.WidgetWidth)
    rl.addWidget(app._stats_result_text)
    layout.addWidget(app._stats_res_frame, 1)

    if hasattr(app, "_stats_update_tp_menu"):
        app._stats_update_tp_menu()
