"""Line Graphs tab builder (Qt port) — the 3-stacked-subplot figure in a v2 PlotCard."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import (
    btn_primary, btn_secondary, install_canvas_wheel_scroll, make_band_controls,
    make_plot_with_right_dock, make_plot_view_switcher)

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

    # Channel combo: kept as an offscreen widget so the rest of the app can
    # still read/write the per-renderer channel through ``app._chan_cb_line``
    # and ``_plot_chan_var``; the global ctxbar combo is the only visible
    # channel control.
    app._chan_cb_line = QComboBox()
    app._chan_cb_line.addItems(["GFP"])
    app._chan_cb_line.currentIndexChanged.connect(
        lambda _i, _src=app._chan_cb_line: app._on_plot_channel_selected(_src)
    )
    app._chan_cb_line.hide()
    if not hasattr(app, "_plot_chan_var"):
        app._plot_chan_var = app._chan_cb_line
        app._chan_var = app._plot_chan_var

    # The visible metric selector now lives in the global plotting ctxbar
    # (``_plotting_metric_cb``). This hidden per-tab combo stays as a
    # back-compat shim for code that still reads ``_metric_var`` /
    # ``_metric_cb``; the global combo wins when present.
    from well_viewer.metric_labels import METRIC_ORDER as _METRIC_ORDER
    app._metric_selector_frame = QWidget(line_ctrl)
    mfl = QHBoxLayout(app._metric_selector_frame)
    mfl.setContentsMargins(0, 0, 0, 0)
    mfl.addWidget(QLabel("Property:", app._metric_selector_frame))
    app._metric_cb = QComboBox(app._metric_selector_frame)
    app._metric_cb.addItems(_METRIC_ORDER)
    app._metric_cb.currentIndexChanged.connect(lambda _i: app._on_metric_selected())
    mfl.addWidget(app._metric_cb)
    if getattr(app, "_plotting_metric_cb", None) is not None:
        app._metric_var = app._plotting_metric_cb
    else:
        app._metric_var = app._metric_cb
    cl.addWidget(app._metric_selector_frame)
    app._metric_selector_frame.hide()

    cl.addStretch(1)

    cl.addWidget(btn_primary(line_ctrl, "Export CSV", app._export_plot_data,
                             icon="download"))
    cl.addWidget(btn_secondary(line_ctrl, "Copy SVG",
                               lambda: app._copy_active_card_as_svg(),
                               icon="copy"))
    cl.addWidget(btn_secondary(line_ctrl, "Save figure",
                               lambda: app._save_active_card_figure(),
                               icon="save"))
    # Properties button last in the row so it sits flush with the right
    # edge of the plot area — adjacent to where the figure-properties
    # dock slides out, instead of the old "▸" floating mid-row.
    style_btn = btn_secondary(
        line_ctrl, "Properties",
        lambda: app._open_export_style_panel("line"),
        icon="sliders-horizontal",
    )
    style_btn.setToolTip("Show / hide the figure properties panel")
    cl.addWidget(style_btn)
    layout.addWidget(line_ctrl)

    # ── the figure, in a v2 PlotCard (card chrome + MplToolbar) ──────────────
    card = PlotCard(parent, figsize=(_FIG_W, _FIG_H), constrained=False)
    _sw = make_plot_view_switcher(app, 'Line Graphs')
    if _sw is not None:
        card.setLeftHeaderWidget(_sw)
    # Hide the per-card header — the ctxbar above already carries the same controls.
    card.setHeaderVisible(False)
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

    # The Publication↔Screen toggle is wired through plot_style.apply_ax_style
    # (it consults card.plotTheme() via ax.figure._plot_card). The stats chip is
    # left hidden — its statsChanged signal isn't wired to app state yet (the
    # error band lives on the controls row above; Mean/Median is unsupported).
    card.plotThemeChanged.connect(lambda _m: app._redraw())
    card.setStatsChipVisible(False)

    app._line_scroll_canvas = QScrollArea(parent)
    app._line_scroll_canvas.setWidgetResizable(True)
    app._line_scroll_canvas.setFrameShape(QFrame.NoFrame)
    app._line_scroll_canvas.setWidget(card)
    install_canvas_wheel_scroll(app._line_canvas, app._line_scroll_canvas)
    # Wrap the scroll area in an EmptyState stack — page 0 is the
    # placeholder shown until a dataset is loaded, page 1 is the figure.
    from well_viewer.ui_helpers import wrap_with_empty_state
    layout.addWidget(wrap_with_empty_state(app, app._line_scroll_canvas), 1)

    # Right-click an axes → toggle its legend. (The old left-click-drag-to-set
    # threshold on the CDF was removed — the threshold lives on the Cell Gating tab.)
    app._line_canvas.mpl_connect("button_press_event", app._on_fig_click)
