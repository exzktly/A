"""Line Graphs tab builder (Qt port)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    attach_plot_toolbar, btn_primary, btn_secondary, ComboVar,
    install_canvas_wheel_scroll, make_plot_with_right_dock,
)


def build_line_graphs_tab(app, parent: QWidget) -> None:
    # Defer matplotlib + QtAgg backend imports until the tab is actually
    # built so unrelated importers of this module don't pay the cost.
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._line_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    line_ctrl = QWidget(parent)
    line_ctrl.setObjectName("Sidebar")
    cl = QHBoxLayout(line_ctrl)
    cl.setContentsMargins(10, 6, 10, 6)

    cl.addWidget(QLabel("Channel:", line_ctrl))
    app._chan_cb_line = QComboBox(line_ctrl)
    app._chan_cb_line.addItems(["GFP"])
    app._chan_cb_line.currentIndexChanged.connect(
        lambda _i, _src=app._chan_cb_line: app._on_plot_channel_selected(_src)
    )
    cl.addWidget(app._chan_cb_line)
    if not hasattr(app, "_plot_chan_var"):
        app._plot_chan_var = ComboVar(app._chan_cb_line)
        app._chan_var = app._plot_chan_var

    app._metric_selector_frame = QWidget(line_ctrl)
    mfl = QHBoxLayout(app._metric_selector_frame)
    mfl.setContentsMargins(0, 0, 0, 0)
    mfl.addWidget(QLabel("Metric:", app._metric_selector_frame))
    app._metric_cb = QComboBox(app._metric_selector_frame)
    app._metric_cb.addItems(["Mean Intensity", "smFISH Count"])
    app._metric_cb.currentIndexChanged.connect(
        lambda _i: app._on_metric_selected()
    )
    mfl.addWidget(app._metric_cb)
    app._metric_var = ComboVar(app._metric_cb)
    cl.addWidget(app._metric_selector_frame)
    app._metric_selector_frame.hide()

    cl.addStretch(1)

    style_btn = QPushButton("▸", line_ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("line"))
    cl.addWidget(style_btn)
    cl.addWidget(btn_primary(line_ctrl, "Export CSV", app._export_plot_data))
    layout.addWidget(line_ctrl)

    app._line_fig = Figure(figsize=(7.2, 10.5), dpi=100)
    app._line_ax_mean = app._line_fig.add_subplot(3, 1, 1)
    app._line_ax_frac = app._line_fig.add_subplot(3, 1, 2, sharex=app._line_ax_mean)
    app._line_ax_cdf = app._line_fig.add_subplot(3, 1, 3)
    app._line_fig.subplots_adjust(
        hspace=0.62, top=0.96, bottom=0.08, left=0.13, right=0.97,
    )

    app._line_canvas = FigureCanvas(app._line_fig)
    app._line_canvas.setMinimumHeight(
        int(app._line_fig.get_figheight() * app._line_fig.get_dpi())
    )

    app._line_scroll_canvas = QScrollArea(parent)
    app._line_scroll_canvas.setWidgetResizable(True)
    app._line_scroll_canvas.setFrameShape(QFrame.NoFrame)
    app._line_scroll_canvas.setWidget(app._line_canvas)
    install_canvas_wheel_scroll(app._line_canvas, app._line_scroll_canvas)
    layout.addWidget(app._line_scroll_canvas, 1)

    attach_plot_toolbar(layout, app._line_canvas, parent, app, with_fov=True)

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    cdf_ctrl = QWidget(parent)
    cdf_ctrl.setObjectName("Sidebar")
    cc = QHBoxLayout(cdf_ctrl)
    cc.setContentsMargins(8, 3, 8, 3)
    cc.addWidget(QLabel("CDF x:", cdf_ctrl))
    app._cdf_xmin_edit = QLineEdit(cdf_ctrl)
    app._cdf_xmin_edit.setFixedWidth(70)
    app._cdf_xmin_edit.editingFinished.connect(app._redraw)
    cc.addWidget(app._cdf_xmin_edit)
    app._cdf_xmax_edit = QLineEdit(cdf_ctrl)
    app._cdf_xmax_edit.setFixedWidth(70)
    app._cdf_xmax_edit.editingFinished.connect(app._redraw)
    cc.addWidget(app._cdf_xmax_edit)
    app._cdf_chan_lbl = QLabel(
        f"({app._active_channel.upper()} x range)", cdf_ctrl,
    )
    app._cdf_chan_lbl.setObjectName("Muted")
    cc.addWidget(app._cdf_chan_lbl)
    cc.addStretch(1)
    layout.addWidget(cdf_ctrl)

    app._line_canvas.mpl_connect("button_press_event", app._on_fig_click)
    app._line_canvas.mpl_connect("motion_notify_event", app._on_cdf_motion)
    app._line_canvas.mpl_connect("button_release_event", app._on_cdf_release)
