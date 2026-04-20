"""Scatter Plot: Aggregate tab builder (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout,
    QWidget, QWidgetAction,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from well_viewer.ui_helpers import btn_primary, ComboVar, make_plot_with_right_dock


class BoolHolder:
    """Tiny tk-compatible shim with ``get()``/``set()`` around a bool flag.

    Cross-module callers (runtime_app, export_service, plot_orchestrator) treat
    ``_scatter_agg_tp_selections`` values as tk.BooleanVars; this keeps them
    happy during the Qt port without changing those call sites yet.
    """

    __slots__ = ("_v", "_cb")

    def __init__(self, value: bool = False) -> None:
        self._v = bool(value)
        self._cb = None

    def get(self) -> bool:
        return self._v

    def set(self, value: bool) -> None:
        self._v = bool(value)
        if self._cb is not None:
            try:
                self._cb.blockSignals(True)
                self._cb.setChecked(self._v)
            finally:
                self._cb.blockSignals(False)

    def bind_checkbox(self, cb: QCheckBox) -> None:
        self._cb = cb
        cb.setChecked(self._v)
        cb.toggled.connect(lambda checked: setattr(self, "_v", bool(checked)))


def build_scatter_agg_tab(app, parent: QWidget) -> None:
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._scatter_agg_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    ctrl = QWidget(parent)
    ctrl.setObjectName("Sidebar")
    cl = QHBoxLayout(ctrl)
    cl.setContentsMargins(10, 6, 10, 6)

    cl.addWidget(QLabel("X-axis:", ctrl))
    app._scatter_agg_stat_x_cb = QComboBox(ctrl)
    app._scatter_agg_stat_x_cb.addItems(["Mean Fluorescence"])
    app._scatter_agg_stat_x_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_scatter_agg()
    )
    cl.addWidget(app._scatter_agg_stat_x_cb)
    app._scatter_agg_stat_x_var = ComboVar(app._scatter_agg_stat_x_cb)

    cl.addWidget(QLabel("Y-axis:", ctrl))
    app._scatter_agg_stat_y_cb = QComboBox(ctrl)
    app._scatter_agg_stat_y_cb.addItems(["Fraction On"])
    app._scatter_agg_stat_y_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_scatter_agg()
    )
    cl.addWidget(app._scatter_agg_stat_y_cb)
    app._scatter_agg_stat_y_var = ComboVar(app._scatter_agg_stat_y_cb)

    cl.addWidget(QLabel("Timepoints:", ctrl))

    app._scatter_agg_tp_button = QPushButton("Select Timepoints", ctrl)
    app._scatter_agg_tp_button.setProperty("variant", "secondary")
    app._scatter_agg_tp_button.clicked.connect(
        lambda _=False: _open_timepoint_selector(app)
    )
    cl.addWidget(app._scatter_agg_tp_button)

    app._scatter_agg_tp_label = QLabel("(0 selected)", ctrl)
    app._scatter_agg_tp_label.setObjectName("Muted")
    cl.addWidget(app._scatter_agg_tp_label)

    app._scatter_agg_tp_selections = {}

    cl.addStretch(1)

    style_btn = QPushButton("▸", ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("scatter_agg"))
    cl.addWidget(style_btn)
    cl.addWidget(btn_primary(ctrl, "Export CSV", app._export_scatter_agg_data))
    layout.addWidget(ctrl)

    app._scatter_agg_fig = Figure(figsize=(8, 6), dpi=100)
    app._ax_scatter_agg = app._scatter_agg_fig.add_subplot(1, 1, 1)
    app._scatter_agg_fig.subplots_adjust(
        hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97,
    )

    app._scatter_agg_canvas = FigureCanvas(app._scatter_agg_fig)
    nav = NavigationToolbar(app._scatter_agg_canvas, parent)
    layout.addWidget(nav)
    layout.addWidget(app._scatter_agg_canvas, 1)


def _open_timepoint_selector(app) -> None:
    """Pop up a QMenu of checkboxes below the Timepoints button."""
    menu = QMenu(app._scatter_agg_tp_button)

    for tp_str in sorted(app._scatter_agg_tp_selections.keys(), key=float):
        holder = app._scatter_agg_tp_selections[tp_str]
        cb = QCheckBox(tp_str, menu)
        holder.bind_checkbox(cb)

        def on_toggled(_checked: bool) -> None:
            app._update_tp_selection_display()
            app._redraw_scatter_agg()

        cb.toggled.connect(on_toggled)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(cb)
        menu.addAction(wa)

    menu.addSeparator()

    def _set_all(value: bool) -> None:
        for h in app._scatter_agg_tp_selections.values():
            h.set(value)
        app._update_tp_selection_display()
        app._redraw_scatter_agg()

    all_action = QAction("All", menu)
    all_action.triggered.connect(lambda _=False: _set_all(True))
    menu.addAction(all_action)

    none_action = QAction("None", menu)
    none_action.triggered.connect(lambda _=False: _set_all(False))
    menu.addAction(none_action)

    btn = app._scatter_agg_tp_button
    menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
