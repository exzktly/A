"""Distribution Analysis tab builder.

Per-cell histogram / KDE / violin views of the active value column at a
chosen timepoint, grouped per replicate set or per well.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    attach_plot_toolbar, btn_primary, ComboVar, make_plot_with_right_dock,
)


_MODE_OPTIONS = ["Histogram", "Histogram + KDE", "KDE only", "Violin (per group)"]


def build_distribution_tab(app, parent: QWidget) -> None:
    # matplotlib (and the QtAgg backend) is one of the heaviest imports in
    # the app. Loading it inside the builder rather than at module import
    # time keeps utility imports from this module (eg.
    # ``refresh_distribution_timepoints``) cheap.
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._distribution_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    ctrl = QWidget(parent)
    ctrl.setObjectName("Sidebar")
    cl = QHBoxLayout(ctrl)
    cl.setContentsMargins(10, 6, 10, 6)

    # Channel
    cl.addWidget(QLabel("Channel:", ctrl))
    app._chan_cb_distribution = QComboBox(ctrl)
    app._chan_cb_distribution.addItems(["GFP"])
    app._chan_cb_distribution.currentIndexChanged.connect(
        lambda _i, _src=app._chan_cb_distribution: app._on_plot_channel_selected(_src)
    )
    cl.addWidget(app._chan_cb_distribution)

    # Timepoint
    cl.addWidget(QLabel("t (h):", ctrl))
    app._distribution_tp_cb = QComboBox(ctrl)
    app._distribution_tp_cb.setMinimumContentsLength(8)
    app._distribution_tp_cb.currentIndexChanged.connect(
        lambda _i: _on_changed(app)
    )
    cl.addWidget(app._distribution_tp_cb)
    app._distribution_tp_var = ComboVar(app._distribution_tp_cb)

    # Mode
    cl.addWidget(QLabel("Mode:", ctrl))
    app._distribution_mode_cb = QComboBox(ctrl)
    app._distribution_mode_cb.addItems(_MODE_OPTIONS)
    app._distribution_mode_cb.setCurrentText("Histogram + KDE")
    app._distribution_mode_cb.currentIndexChanged.connect(
        lambda _i: _on_changed(app)
    )
    cl.addWidget(app._distribution_mode_cb)
    app._distribution_mode_var = ComboVar(app._distribution_mode_cb)

    # Bins
    cl.addWidget(QLabel("Bins:", ctrl))
    app._distribution_bins_spin = QSpinBox(ctrl)
    app._distribution_bins_spin.setRange(5, 500)
    app._distribution_bins_spin.setValue(40)
    app._distribution_bins = 40

    def _on_bins_changed(val: int) -> None:
        app._distribution_bins = int(val)
        _on_changed(app)
    app._distribution_bins_spin.valueChanged.connect(_on_bins_changed)
    cl.addWidget(app._distribution_bins_spin)

    # Log x
    app._distribution_log_x_cb = QCheckBox("log x", ctrl)
    app._distribution_log_x = False

    def _on_log_changed(state: int) -> None:
        app._distribution_log_x = bool(state)
        _on_changed(app)
    app._distribution_log_x_cb.stateChanged.connect(_on_log_changed)
    cl.addWidget(app._distribution_log_x_cb)

    cl.addStretch(1)

    style_btn = QPushButton("▸", ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.setToolTip("Export style / figure settings")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("distribution"))
    cl.addWidget(style_btn)

    cl.addWidget(btn_primary(ctrl, "Export CSV", app._export_distribution_data))
    layout.addWidget(ctrl)

    # Figure / canvas
    app._distribution_fig = Figure(figsize=(7.2, 5.4), dpi=100)
    app._distribution_ax = app._distribution_fig.add_subplot(1, 1, 1)
    app._distribution_fig.subplots_adjust(top=0.93, bottom=0.12, left=0.10, right=0.97)

    app._distribution_canvas = FigureCanvas(app._distribution_fig)
    layout.addWidget(app._distribution_canvas, 1)

    attach_plot_toolbar(layout, app._distribution_canvas, parent, app, with_fov=False)

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # Initial timepoint menu (if data already loaded)
    refresh_distribution_timepoints(app)


def _on_changed(app) -> None:
    """Common callback for any control change in the Distribution tab."""
    from well_viewer.distribution_controller import redraw_distribution
    redraw_distribution(app)


def refresh_distribution_timepoints(app) -> None:
    """Populate the timepoint dropdown from the loaded data."""
    cb = getattr(app, "_distribution_tp_cb", None)
    if cb is None:
        return
    try:
        from well_viewer.scatter_controller import get_all_timepoints
        tps = get_all_timepoints(app)
    except Exception:
        tps = []
    items = [f"{tp:g}" for tp in tps] if tps else []
    blocked = cb.blockSignals(True)
    try:
        cb.clear()
        if items:
            cb.addItems(items)
        else:
            cb.addItem("—")
    finally:
        cb.blockSignals(blocked)
