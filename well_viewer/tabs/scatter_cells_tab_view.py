"""Scatter Plot: Cells tab builder (Qt port) — single scatter in a v2 PlotCard."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, btn_secondary, make_band_controls, make_plot_with_right_dock,
    make_plot_view_switcher)


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

    # Per-axis channel + property selectors. The scatter tab overrides
    # the global ctxbar channel/property combos (those are hidden when
    # Scatter Plot is the active plotting subtab) because each axis
    # needs to render an independent column.
    from well_viewer.metric_labels import METRIC_ORDER as _METRIC_ORDER
    cl.addWidget(QLabel("X-axis:", ctrl))
    cl.addWidget(QLabel("Channel:", ctrl))
    app._scatter_ch_x_cb = QComboBox(ctrl)
    app._scatter_ch_x_cb.addItems(["gfp"])
    app._scatter_ch_x_cb.currentIndexChanged.connect(lambda _i: app._on_scatter_axis_change("x"))
    cl.addWidget(app._scatter_ch_x_cb)
    app._scatter_ch_x_var = app._scatter_ch_x_cb

    cl.addWidget(QLabel("Property:", ctrl))
    app._scatter_metric_x_cb = QComboBox(ctrl)
    app._scatter_metric_x_cb.addItems(_METRIC_ORDER)
    app._scatter_metric_x_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_metric_x_cb)
    app._scatter_metric_x_var = app._scatter_metric_x_cb

    cl.addWidget(QLabel("Y-axis:", ctrl))
    cl.addWidget(QLabel("Channel:", ctrl))
    app._scatter_ch_y_cb = QComboBox(ctrl)
    app._scatter_ch_y_cb.addItems(["gfp"])
    app._scatter_ch_y_cb.currentIndexChanged.connect(lambda _i: app._on_scatter_axis_change("y"))
    cl.addWidget(app._scatter_ch_y_cb)
    app._scatter_ch_y_var = app._scatter_ch_y_cb

    cl.addWidget(QLabel("Property:", ctrl))
    app._scatter_metric_y_cb = QComboBox(ctrl)
    app._scatter_metric_y_cb.addItems(_METRIC_ORDER)
    app._scatter_metric_y_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_metric_y_cb)
    app._scatter_metric_y_var = app._scatter_metric_y_cb

    cl.addWidget(QLabel("Timepoint:", ctrl))
    app._scatter_tp_cb = QComboBox(ctrl)
    app._scatter_tp_cb.addItems(["0"])
    app._scatter_tp_cb.currentIndexChanged.connect(lambda _i: app._redraw_scatter())
    cl.addWidget(app._scatter_tp_cb)
    app._scatter_tp_var = app._scatter_tp_cb
    cl.addStretch(1)

    cl.addWidget(btn_primary(ctrl, "Export CSV", app._export_scatter_data,
                             icon="download"))
    _b = btn_secondary(ctrl, "", lambda: app._copy_active_card_as_svg(), icon="copy")
    _b.setToolTip("Copy SVG")
    cl.addWidget(_b)
    _b = btn_secondary(ctrl, "", lambda: app._save_active_card_figure(), icon="save")
    _b.setToolTip("Save figure")
    cl.addWidget(_b)
    # Properties button last in the row so it sits flush with the right
    # edge of the plot area — adjacent to where the dock slides out.
    style_btn = btn_secondary(
        ctrl, "Properties",
        lambda: app._open_export_style_panel("scatter_cells"),
        icon="sliders-horizontal",
    )
    style_btn.setToolTip("Show / hide the figure properties panel")
    cl.addWidget(style_btn)
    layout.addWidget(ctrl)

    card = PlotCard(parent, figsize=(8, 6), constrained=False)
    _sw = make_plot_view_switcher(app, 'Scatter Plot')
    if _sw is not None:
        card.setLeftHeaderWidget(_sw)
    # Hide the per-card header — the ctxbar above already carries the same controls.
    card.setHeaderVisible(False)
    card.setFigureTitle("")
    app._scatter_card = card
    app._scatter_fig = card.figure
    app._ax_scatter = app._scatter_fig.add_subplot(1, 1, 1)
    app._scatter_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)
    app._scatter_canvas = card.canvas
    card.setControlsWidget(make_band_controls(app, card, with_fov=False))
    card.plotThemeChanged.connect(lambda _m: app._redraw_scatter())
    card.setStatsChipVisible(False)
    from well_viewer.ui_helpers import wrap_with_empty_state
    layout.addWidget(wrap_with_empty_state(
        app, card, icon="scatter-chart",
    ), 1)

    app._scatter_canvas.mpl_connect("button_press_event", app._on_scatter_click)
    app._scatter_canvas.mpl_connect("motion_notify_event", app._on_scatter_motion)
