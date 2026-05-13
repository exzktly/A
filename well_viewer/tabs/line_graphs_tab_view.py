"""Line Graphs tab builder (Qt port) — the 3-stacked-subplot figure in a v2 PlotCard."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, install_canvas_wheel_scroll, make_band_controls,
    make_plot_with_right_dock,
)

# The Line Graphs figure: three stacked subplots (mean / fraction / CDF).
_FIG_W, _FIG_H, _DPI = 7.2, 10.5, 100


def build_line_graphs_tab(app, parent: QWidget) -> None:
    from widgets.plot_card import PlotCard

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    plot_area, layout, app._line_export_dock = make_plot_with_right_dock(parent)
    parent = plot_area

    # ── controls row above the card (Channel / Metric / style / Export CSV) ──
    line_ctrl = QWidget(parent)
    line_ctrl.setObjectName("TabCtrl")
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
        app._plot_chan_var = app._chan_cb_line
        app._chan_var = app._plot_chan_var

    app._metric_selector_frame = QWidget(line_ctrl)
    mfl = QHBoxLayout(app._metric_selector_frame)
    mfl.setContentsMargins(0, 0, 0, 0)
    mfl.addWidget(QLabel("Metric:", app._metric_selector_frame))
    app._metric_cb = QComboBox(app._metric_selector_frame)
    app._metric_cb.addItems(["Mean Intensity", "smFISH Count"])
    app._metric_cb.currentIndexChanged.connect(lambda _i: app._on_metric_selected())
    mfl.addWidget(app._metric_cb)
    app._metric_var = app._metric_cb
    cl.addWidget(app._metric_selector_frame)
    app._metric_selector_frame.hide()

    cl.addStretch(1)

    style_btn = QPushButton("▸", line_ctrl)
    style_btn.setProperty("variant", "secondary")
    style_btn.clicked.connect(lambda _=False: app._open_export_style_panel("line"))
    cl.addWidget(style_btn)
    cl.addWidget(btn_primary(line_ctrl, "Export CSV", app._export_plot_data))
    layout.addWidget(line_ctrl)

    # ── the figure, in a v2 PlotCard (card chrome + MplToolbar) ──────────────
    card = PlotCard(parent, figsize=(_FIG_W, _FIG_H), constrained=False)
    card.setFigureTitle("")          # the tab name is the title; keep the header lean
    app._line_card = card
    app._line_fig = card.figure
    app._line_ax_mean = app._line_fig.add_subplot(3, 1, 1)
    app._line_ax_frac = app._line_fig.add_subplot(3, 1, 2, sharex=app._line_ax_mean)
    app._line_ax_cdf = app._line_fig.add_subplot(3, 1, 3)
    app._line_fig.subplots_adjust(
        hspace=0.62, top=0.96, bottom=0.08, left=0.13, right=0.97,
    )
    app._line_canvas = card.canvas
    app._line_canvas.setMinimumHeight(int(_FIG_H * _DPI))
    card.setMinimumHeight(int(_FIG_H * _DPI) + 110)   # + header / controls / toolbar rows

    # The "Error Band: SEM/SD" + "Spread: FOV" toggles (formerly on the legacy
    # plot toolbar) → the card's controls row beneath the header.
    card.setControlsWidget(make_band_controls(app, card, with_fov=True))

    # The card's Publication↔Screen toggle + the stats chip are hidden here for
    # now: the line plot's styling comes from plot_style.apply_ax_style (a redraw
    # would override the card theme) and its stats UI is the Error Band/Spread
    # toggles above — wiring those to the card chips is a follow-up.
    card.setThemeToggleVisible(False)
    card.setStatsChipVisible(False)

    app._line_scroll_canvas = QScrollArea(parent)
    app._line_scroll_canvas.setWidgetResizable(True)
    app._line_scroll_canvas.setFrameShape(QFrame.NoFrame)
    app._line_scroll_canvas.setWidget(card)
    install_canvas_wheel_scroll(app._line_canvas, app._line_scroll_canvas)
    layout.addWidget(app._line_scroll_canvas, 1)

    # Right-click an axes → toggle its legend. (The old left-click-drag-to-set
    # threshold on the CDF was removed — the threshold lives on the Cell Gating tab.)
    app._line_canvas.mpl_connect("button_press_event", app._on_fig_click)
