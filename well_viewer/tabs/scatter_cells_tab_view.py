"""Scatter Plot: Cells tab builder (Qt port)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    attach_plot_toolbar, btn_primary, make_plot_with_right_dock,
)


def build_scatter_cells_tab(app, parent: QWidget) -> None:
    # Defer matplotlib + QtAgg backend imports until the tab actually builds.
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
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
    app._scatter_ch_x_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_scatter()
    )
    cl.addWidget(app._scatter_ch_x_cb)
    app._scatter_ch_x_var = app._scatter_ch_x_cb

    cl.addWidget(QLabel("Y-axis:", ctrl))
    app._scatter_ch_y_cb = QComboBox(ctrl)
    app._scatter_ch_y_cb.addItems(["gfp"])
    app._scatter_ch_y_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_scatter()
    )
    cl.addWidget(app._scatter_ch_y_cb)
    app._scatter_ch_y_var = app._scatter_ch_y_cb

    cl.addWidget(QLabel("Timepoint:", ctrl))
    app._scatter_tp_cb = QComboBox(ctrl)
    app._scatter_tp_cb.addItems(["0"])
    app._scatter_tp_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_scatter()
    )
    cl.addWidget(app._scatter_tp_cb)
    app._scatter_tp_var = app._scatter_tp_cb
    cl.addStretch(1)

    style_btn = QPushButton("▸", ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("scatter_cells"))
    cl.addWidget(style_btn)
    cl.addWidget(btn_primary(ctrl, "Export CSV", app._export_scatter_data))
    svg_btn_sc = QPushButton("Copy SVG", ctrl)
    svg_btn_sc.setProperty("variant", "secondary")
    svg_btn_sc.setToolTip("Copy the current figure as SVG to the clipboard")
    svg_btn_sc.clicked.connect(
        lambda _=False: app._copy_figure_svg(app._scatter_fig)
        if getattr(app, "_scatter_fig", None) is not None else None
    )
    cl.addWidget(svg_btn_sc)
    layout.addWidget(ctrl)

    app._scatter_fig = Figure(figsize=(8, 6), dpi=100)
    app._ax_scatter = app._scatter_fig.add_subplot(1, 1, 1)
    app._scatter_fig.subplots_adjust(
        hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97,
    )

    app._scatter_canvas = FigureCanvas(app._scatter_fig)
    layout.addWidget(app._scatter_canvas, 1)
    attach_plot_toolbar(layout, app._scatter_canvas, parent, app)

    app._scatter_canvas.mpl_connect("button_press_event", app._on_scatter_click)
    app._scatter_canvas.mpl_connect("motion_notify_event", app._on_scatter_motion)
