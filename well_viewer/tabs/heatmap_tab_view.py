"""Heat Map tab builder.

User-defined R×C grid colored by a chosen metric for one timepoint, with a
slider to scrub through time and click-to-select wells.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QSlider,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import attach_plot_toolbar, ComboVar, make_plot_with_right_dock


_CMAP_OPTIONS = ["viridis", "magma", "coolwarm", "RdYlBu_r", "Greys"]
_SCALE_OPTIONS = ["Auto", "Fixed"]


def build_heatmap_tab(app, parent: QWidget) -> None:
    # Defer matplotlib + heatmap_controller imports until the tab actually
    # builds. heatmap_controller pulls in matplotlib.patches and numpy at
    # module load, so importing it lazily keeps utility entry points like
    # ``refresh_heatmap_timepoints`` cheap.
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from well_viewer.heatmap_controller import METRIC_OPTIONS
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._heatmap_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    # ── Control row 1: channel / metric ─────────────────────────────────────
    # The layout itself is edited from the sidebar configurator on the left
    # (see ``views/heatmap_layout_sidebar_view.py``); this row is for the
    # plotting parameters only.
    ctrl1 = QWidget(parent)
    ctrl1.setObjectName("Sidebar")
    cl1 = QHBoxLayout(ctrl1)
    cl1.setContentsMargins(10, 6, 10, 6)

    cl1.addWidget(QLabel("Channel:", ctrl1))
    app._chan_cb_heatmap = QComboBox(ctrl1)
    app._chan_cb_heatmap.addItems(["GFP"])
    app._chan_cb_heatmap.currentIndexChanged.connect(
        lambda _i: app._on_plot_channel_selected(None)
    )
    cl1.addWidget(app._chan_cb_heatmap)

    cl1.addWidget(QLabel("Metric:", ctrl1))
    app._heatmap_metric_cb = QComboBox(ctrl1)
    app._heatmap_metric_cb.addItems(METRIC_OPTIONS)
    app._heatmap_metric_cb.currentIndexChanged.connect(lambda _i: _redraw(app))
    cl1.addWidget(app._heatmap_metric_cb)

    cl1.addStretch(1)
    layout.addWidget(ctrl1)

    # ── Control row 2: cmap / scale / log ───────────────────────────────────
    ctrl2 = QWidget(parent)
    ctrl2.setObjectName("Sidebar")
    cl2 = QHBoxLayout(ctrl2)
    cl2.setContentsMargins(10, 0, 10, 6)

    cl2.addWidget(QLabel("Color map:", ctrl2))
    app._heatmap_cmap_cb = QComboBox(ctrl2)
    app._heatmap_cmap_cb.addItems(_CMAP_OPTIONS)
    app._heatmap_cmap_cb.currentIndexChanged.connect(lambda _i: _redraw(app))
    cl2.addWidget(app._heatmap_cmap_cb)

    cl2.addWidget(QLabel("Scale:", ctrl2))
    app._heatmap_scale_cb = QComboBox(ctrl2)
    app._heatmap_scale_cb.addItems(_SCALE_OPTIONS)
    app._heatmap_scale_cb.currentIndexChanged.connect(lambda _i: _on_scale_changed(app))
    cl2.addWidget(app._heatmap_scale_cb)
    app._heatmap_scale_mode = "Auto"

    cl2.addWidget(QLabel("vmin:", ctrl2))
    app._heatmap_vmin_edit = QLineEdit(ctrl2)
    app._heatmap_vmin_edit.setFixedWidth(70)
    app._heatmap_vmin_edit.editingFinished.connect(lambda: _on_vminmax_changed(app))
    cl2.addWidget(app._heatmap_vmin_edit)

    cl2.addWidget(QLabel("vmax:", ctrl2))
    app._heatmap_vmax_edit = QLineEdit(ctrl2)
    app._heatmap_vmax_edit.setFixedWidth(70)
    app._heatmap_vmax_edit.editingFinished.connect(lambda: _on_vminmax_changed(app))
    cl2.addWidget(app._heatmap_vmax_edit)

    cl2.addStretch(1)

    app._heatmap_status_lbl = QLabel("", ctrl2)
    app._heatmap_status_lbl.setObjectName("Muted")
    cl2.addWidget(app._heatmap_status_lbl)

    layout.addWidget(ctrl2)

    # ── Figure ──────────────────────────────────────────────────────────────
    app._heatmap_fig = Figure(figsize=(8.0, 6.0), dpi=100)
    app._heatmap_ax = app._heatmap_fig.add_subplot(1, 1, 1)
    # Reserve a persistent colorbar axes via make_axes_locatable so each
    # redraw can refill it in place. Letting fig.colorbar(im, ax=ax)
    # allocate a fresh axes every redraw was the cause of the heatmap
    # plot shrinking and drifting left on every refresh — matplotlib does
    # not restore the original ax position when the colorbar is removed.
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(app._heatmap_ax)
    app._heatmap_cax = divider.append_axes("right", size="4%", pad=0.08)
    app._heatmap_canvas = FigureCanvas(app._heatmap_fig)
    layout.addWidget(app._heatmap_canvas, 1)

    attach_plot_toolbar(layout, app._heatmap_canvas, parent, app, with_fov=False)

    # ── Timepoint slider ────────────────────────────────────────────────────
    slider_row = QWidget(parent)
    slider_row.setObjectName("Sidebar")
    sl = QHBoxLayout(slider_row)
    sl.setContentsMargins(10, 4, 10, 6)
    sl.addWidget(QLabel("t (h):", slider_row))
    app._heatmap_tp_slider = QSlider(Qt.Horizontal, slider_row)
    app._heatmap_tp_slider.setMinimum(0)
    app._heatmap_tp_slider.setMaximum(0)
    app._heatmap_tp_slider.valueChanged.connect(lambda _v: _on_tp_changed(app))
    sl.addWidget(app._heatmap_tp_slider, 1)
    app._heatmap_tp_label = QLabel("—", slider_row)
    app._heatmap_tp_label.setMinimumWidth(80)
    sl.addWidget(app._heatmap_tp_label)
    layout.addWidget(slider_row)

    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # ── Mouse hooks ─────────────────────────────────────────────────────────
    app._heatmap_canvas.mpl_connect("button_press_event",
                                     lambda evt: _on_canvas_click(app, evt))
    app._heatmap_canvas.mpl_connect("motion_notify_event",
                                     lambda evt: _on_canvas_motion(app, evt))

    refresh_heatmap_timepoints(app)


# ── helpers attached or referenced from runtime_app ─────────────────────────

def refresh_heatmap_timepoints(app) -> None:
    slider = getattr(app, "_heatmap_tp_slider", None)
    label = getattr(app, "_heatmap_tp_label", None)
    if slider is None:
        return
    try:
        from well_viewer.scatter_controller import get_all_timepoints
        tps = list(get_all_timepoints(app))
    except Exception:
        tps = []
    app._heatmap_tp_values = tps
    blocked = slider.blockSignals(True)
    try:
        slider.setMinimum(0)
        slider.setMaximum(max(0, len(tps) - 1))
        slider.setValue(0)
    finally:
        slider.blockSignals(blocked)
    if label is not None:
        if tps:
            label.setText(f"t = {tps[0]:g} h")
        else:
            label.setText("—")
    _redraw(app)


def _on_tp_changed(app) -> None:
    tps: List[float] = list(getattr(app, "_heatmap_tp_values", []) or [])
    slider = getattr(app, "_heatmap_tp_slider", None)
    label = getattr(app, "_heatmap_tp_label", None)
    if not tps or slider is None:
        return
    idx = max(0, min(slider.value(), len(tps) - 1))
    if label is not None:
        label.setText(f"t = {tps[idx]:g} h")
    _redraw(app)


def _on_scale_changed(app) -> None:
    cb = getattr(app, "_heatmap_scale_cb", None)
    if cb is not None:
        app._heatmap_scale_mode = str(cb.currentText() or "Auto")
    _redraw(app)


def _on_vminmax_changed(app) -> None:
    try:
        app._heatmap_vmin = float(app._heatmap_vmin_edit.text() or "nan")
    except (TypeError, ValueError):
        app._heatmap_vmin = float("nan")
    try:
        app._heatmap_vmax = float(app._heatmap_vmax_edit.text() or "nan")
    except (TypeError, ValueError):
        app._heatmap_vmax = float("nan")
    _redraw(app)


def _on_canvas_click(app, evt) -> None:
    from well_viewer.heatmap_controller import on_heatmap_click
    on_heatmap_click(app, evt)


def _on_canvas_motion(app, evt) -> None:
    from well_viewer.heatmap_controller import on_heatmap_motion
    on_heatmap_motion(app, evt)


def _redraw(app) -> None:
    from well_viewer.heatmap_controller import redraw_heatmap
    redraw_heatmap(app)
