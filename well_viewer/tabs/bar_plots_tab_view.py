"""Bar Plots tab builder (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSlider, QVBoxLayout, QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from well_viewer.ui_helpers import (
    attach_plot_toolbar, btn_primary, btn_secondary, BoolVar, ComboVar,
    install_canvas_wheel_scroll, make_plot_with_right_dock,
)


def build_bar_plots_tab(app, parent: QWidget) -> None:
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, outer_layout, app._bar_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    bar_right = QWidget(parent)
    right_l = QVBoxLayout(bar_right)
    right_l.setContentsMargins(0, 0, 0, 0)
    outer_layout.addWidget(bar_right, 1)

    # Controls bar
    bar_ctrl = QWidget(bar_right)
    bar_ctrl.setObjectName("Sidebar")
    cl = QHBoxLayout(bar_ctrl)
    cl.setContentsMargins(10, 6, 10, 6)

    cl.addWidget(QLabel("Channel:", bar_ctrl))
    app._chan_cb_bar = QComboBox(bar_ctrl)
    app._chan_cb_bar.addItems(["GFP"])
    app._chan_cb_bar.currentIndexChanged.connect(
        lambda _i: app._on_plot_channel_selected(None)
    )
    cl.addWidget(app._chan_cb_bar)

    app._metric_selector_frame_bar = QWidget(bar_ctrl)
    mf_l = QHBoxLayout(app._metric_selector_frame_bar)
    mf_l.setContentsMargins(0, 0, 0, 0)
    mf_l.addWidget(QLabel("Metric:", app._metric_selector_frame_bar))
    app._metric_cb_bar = QComboBox(app._metric_selector_frame_bar)
    app._metric_cb_bar.addItems(["Mean Intensity", "smFISH Count"])
    app._metric_cb_bar.currentIndexChanged.connect(
        lambda _i: app._on_metric_selected()
    )
    mf_l.addWidget(app._metric_cb_bar)
    cl.addWidget(app._metric_selector_frame_bar)

    cl.addWidget(QLabel("Timepoint:", bar_ctrl))
    app._bar_tp_cb = QComboBox(bar_ctrl)
    app._bar_tp_cb.addItems(["—"])
    app._bar_tp_cb.currentIndexChanged.connect(
        lambda _i: app._redraw_bars()
    )
    cl.addWidget(app._bar_tp_cb)
    app._bar_tp_var = ComboVar(app._bar_tp_cb)

    cl.addStretch(1)

    # Toggle buttons
    app._swarm_btn = QPushButton("Beeswarm", bar_ctrl)
    app._swarm_btn.setProperty("variant", "toggle")
    app._swarm_btn.setCheckable(True)
    app._swarm_btn.clicked.connect(lambda _=False: app._toggle_swarm())
    cl.addWidget(app._swarm_btn)
    app._bar_swarm = BoolVar(False)

    app._violin_btn = QPushButton("Violin", bar_ctrl)
    app._violin_btn.setProperty("variant", "toggle")
    app._violin_btn.setCheckable(True)
    app._violin_btn.clicked.connect(lambda _=False: app._toggle_violin())
    cl.addWidget(app._violin_btn)
    app._bar_violin = BoolVar(False)

    cl.addWidget(QLabel("Smooth:", bar_ctrl))
    app._violin_slider = QSlider(Qt.Horizontal, bar_ctrl)
    app._violin_slider.setRange(5, 200)
    app._violin_slider.setValue(100)
    app._violin_slider.setFixedWidth(80)
    app._violin_slider.valueChanged.connect(
        lambda _v: (app._redraw_bars() if app._bar_violin.get() else None)
    )
    app._violin_slider.setEnabled(False)
    cl.addWidget(app._violin_slider)

    app._bar_log_btn = QPushButton("Log Y", bar_ctrl)
    app._bar_log_btn.setProperty("variant", "toggle")
    app._bar_log_btn.setCheckable(True)
    app._bar_log_btn.clicked.connect(lambda _=False: app._toggle_log_scale())
    cl.addWidget(app._bar_log_btn)
    app._bar_log_scale = BoolVar(False)

    app._bar_reset_order_btn = QPushButton("Reset Order", bar_ctrl)
    app._bar_reset_order_btn.setProperty("variant", "toggle_muted")
    app._bar_reset_order_btn.clicked.connect(lambda _=False: app._bar_reset_order())
    cl.addWidget(app._bar_reset_order_btn)

    style_btn = QPushButton("▸", bar_ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("bar"))
    cl.addWidget(style_btn)

    cl.addWidget(btn_primary(bar_ctrl, "Export CSV", app._export_bar_plot_data))
    right_l.addWidget(bar_ctrl)

    # Matplotlib figure inside a scroll area
    app._bar_fig = Figure(figsize=(6.2, 8.4), dpi=100)
    app._ax_bar_mean = app._bar_fig.add_subplot(2, 1, 1)
    app._ax_bar_frac = app._bar_fig.add_subplot(2, 1, 2)
    app._bar_fig.subplots_adjust(
        hspace=0.65, top=0.95, bottom=0.14, left=0.15, right=0.97,
    )

    app._bar_canvas = FigureCanvas(app._bar_fig)
    app._bar_canvas.setMinimumHeight(
        int(app._bar_fig.get_figheight() * app._bar_fig.get_dpi())
    )

    app._bar_scroll_canvas = QScrollArea(bar_right)
    app._bar_scroll_canvas.setWidgetResizable(True)
    app._bar_scroll_canvas.setFrameShape(QFrame.NoFrame)
    app._bar_scroll_canvas.setWidget(app._bar_canvas)
    install_canvas_wheel_scroll(app._bar_canvas, app._bar_scroll_canvas)
    right_l.addWidget(app._bar_scroll_canvas, 1)

    attach_plot_toolbar(right_l, app._bar_canvas, bar_right, app)

    # Y-axis limit controls
    ylim_row = QWidget(bar_right)
    ylim_row.setObjectName("Sidebar")
    yl = QHBoxLayout(ylim_row)
    yl.setContentsMargins(8, 4, 8, 4)

    app._bar_ylim_chan_lbl = QLabel(f"{app._active_channel.upper()} y:", ylim_row)
    yl.addWidget(app._bar_ylim_chan_lbl)
    app._bar_ylim_mean_lo_edit = QLineEdit(ylim_row)
    app._bar_ylim_mean_lo_edit.setFixedWidth(60)
    app._bar_ylim_mean_lo_edit.editingFinished.connect(app._redraw_bars)
    yl.addWidget(app._bar_ylim_mean_lo_edit)
    app._bar_ylim_mean_hi_edit = QLineEdit(ylim_row)
    app._bar_ylim_mean_hi_edit.setFixedWidth(60)
    app._bar_ylim_mean_hi_edit.editingFinished.connect(app._redraw_bars)
    yl.addWidget(app._bar_ylim_mean_hi_edit)

    yl.addSpacing(20)
    yl.addWidget(QLabel("Frac y:", ylim_row))
    app._bar_ylim_frac_lo_edit = QLineEdit(ylim_row)
    app._bar_ylim_frac_lo_edit.setFixedWidth(60)
    app._bar_ylim_frac_lo_edit.editingFinished.connect(app._redraw_bars)
    yl.addWidget(app._bar_ylim_frac_lo_edit)
    app._bar_ylim_frac_hi_edit = QLineEdit(ylim_row)
    app._bar_ylim_frac_hi_edit.setFixedWidth(60)
    app._bar_ylim_frac_hi_edit.editingFinished.connect(app._redraw_bars)
    yl.addWidget(app._bar_ylim_frac_hi_edit)
    yl.addStretch(1)
    right_l.addWidget(ylim_row)

    # Drag-to-reorder bar state
    app._bar_drag_state = {"active": False, "src_idx": -1, "cur_idx": -1}
    app._bar_canvas.mousePressEvent = app._on_bar_drag_press
    app._bar_canvas.mouseMoveEvent = app._on_bar_drag_motion
    app._bar_canvas.mouseReleaseEvent = app._on_bar_drag_release
