"""Scatter Plot: Cells tab builder extracted from centre_view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from well_viewer.runtime_app import (
    BG_APP,
    BG_SIDE,
    FM_BOLD,
    FM_TINY,
    PLOT_BG,
    TXT_SEC,
)
from well_viewer.tabs import _make_action_button, _make_secondary_button


def build_scatter_cells_tab(app, parent: tk.Frame) -> None:
    """Fill *parent* with the Scatter Plot: Cells controls and figure.

    Creates and wires:
    - X-axis channel selector (``app._scatter_ch_x_var``)
    - Y-axis channel selector (``app._scatter_ch_y_var``)
    - Timepoint selector (single-select ``app._scatter_tp_var``)
    - Export CSV / Save Figure buttons
    - Matplotlib figure with one scatter subplot
    """
    # ── Controls bar ───────────────────────────────────────────────────────
    scatter_ctrl = tk.Frame(parent, bg=BG_SIDE, pady=6, padx=10)
    scatter_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: X-axis, Y-axis, and Timepoint selectors
    tk.Label(scatter_ctrl, text="X-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_ch_x_var = tk.StringVar(value="gfp")
    app._scatter_ch_x_cb = ttk.Combobox(scatter_ctrl, textvariable=app._scatter_ch_x_var,
                                        values=["gfp"], state="readonly",
                                        width=10, font=FM_TINY)
    app._scatter_ch_x_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_ch_x_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_scatter())

    tk.Label(scatter_ctrl, text="Y-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_ch_y_var = tk.StringVar(value="gfp")
    app._scatter_ch_y_cb = ttk.Combobox(scatter_ctrl, textvariable=app._scatter_ch_y_var,
                                        values=["gfp"], state="readonly",
                                        width=10, font=FM_TINY)
    app._scatter_ch_y_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_ch_y_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_scatter())

    tk.Label(scatter_ctrl, text="Timepoint:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_tp_var = tk.StringVar(value="0")
    app._scatter_tp_cb = ttk.Combobox(scatter_ctrl, textvariable=app._scatter_tp_var,
                                      values=["0"], state="readonly",
                                      width=12, font=FM_TINY)
    app._scatter_tp_cb.pack(side=tk.LEFT)
    app._scatter_tp_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_scatter())

    # Right side: Export actions
    _make_action_button(
        scatter_ctrl, text="Export CSV", command=app._export_scatter_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        scatter_ctrl, text="Save Figure…", command=app._save_scatter_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        scatter_ctrl, text="▸", command=lambda: app._open_export_style_panel("scatter_cells"),
    ).pack(side=tk.RIGHT, padx=(0, 2))

    # ── Matplotlib figure ──────────────────────────────────────────────────
    app._scatter_fig = Figure(figsize=(8, 6), dpi=100, facecolor=PLOT_BG)
    app._ax_scatter = app._scatter_fig.add_subplot(1, 1, 1)
    app._scatter_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)

    app._scatter_canvas = FigureCanvasTkAgg(app._scatter_fig, master=parent)

    # Toolbar must be created before the canvas is packed
    scatter_nav = NavigationToolbar2Tk(app._scatter_canvas, parent)
    scatter_nav.config(bg=BG_APP)
    scatter_nav.update()

    app._scatter_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
    app._scatter_canvas.mpl_connect("button_press_event",   app._on_scatter_click)
    app._scatter_canvas.mpl_connect("motion_notify_event",  app._on_scatter_motion)
