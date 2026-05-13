"""Scatter Plot: Cells tab builder (Qt port) — single scatter in a v2 PlotCard."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, make_band_controls, make_plot_with_right_dock, make_plot_view_switcher)


def build_scatter_cells_tab(app, parent: QWidget) -> None:
    from widgets.plot_card import PlotCard

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._scatter_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    ctrl = QWidget(parent)
    ctrl.setObjectName("TabCtrl")
    cl = QHBoxLayout(ctrl)
    cl.setContentsMargins(10, 6, 10, 6)

    cl.addWidget(QLabel("X-axis:", ctrl))
    app._scatter_ch_x_cb = QComboBox(ctrl)
    app._scatter_ch_x_cb.addItems(["gfp"])
    app._scatter_ch_x_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_ch_x_cb)
    app._scatter_ch_x_var = app._scatter_ch_x_cb

    cl.addWidget(QLabel("Y-axis:", ctrl))
    app._scatter_ch_y_cb = QComboBox(ctrl)
    app._scatter_ch_y_cb.addItems(["gfp"])
    app._scatter_ch_y_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_ch_y_cb)
    app._scatter_ch_y_var = app._scatter_ch_y_cb

    cl.addWidget(QLabel("Timepoint:", ctrl))
    app._scatter_tp_cb = QComboBox(ctrl)
    app._scatter_tp_cb.addItems(["0"])
    app._scatter_tp_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_tp_cb)
    app._scatter_tp_var = app._scatter_tp_cb
    cl.addStretch(1)

    from widgets.icon_button import IconButton as _IconButton
    style_btn = _IconButton("sliders", ctrl)
    style_btn.setToolTip("Open export style panel for scatter (cells)")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("scatter_cells"))
    cl.addWidget(style_btn)
    cl.addWidget(btn_primary(ctrl, "Export CSV", app._export_scatter_data))
    layout.addWidget(ctrl)

    card = PlotCard(parent, figsize=(8, 6), constrained=False)
    _sw = make_plot_view_switcher(app, 'Scatter Plot')
    if _sw is not None:
        card.setLeftHeaderWidget(_sw)
    card.setFigureTitle("")
    app._scatter_card = card
    app._scatter_fig = card.figure
    app._ax_scatter = app._scatter_fig.add_subplot(1, 1, 1)
    app._scatter_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)
    app._scatter_canvas = card.canvas
    card.setControlsWidget(make_band_controls(app, card, with_fov=False))
    card.plotThemeChanged.connect(lambda _m: app._redraw_scatter())
    card.setStatsChipVisible(False)
    layout.addWidget(card, 1)

    app._scatter_canvas.mpl_connect("button_press_event", app._on_scatter_click)
    app._scatter_canvas.mpl_connect("motion_notify_event", app._on_scatter_motion)
