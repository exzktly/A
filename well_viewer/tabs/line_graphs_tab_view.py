"""Line Graphs tab builder extracted from centre_view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from well_viewer.ui_helpers import bind_mousewheel_scroll
from well_viewer.runtime_app import (
    ACCENT,
    BG_APP,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    FM_BOLD,
    FM_TINY,
    PLOT_BG,
    TXT_MUT,
    TXT_SEC,
)
from well_viewer.tabs import _make_action_button, _make_secondary_button


def build_line_graphs_tab(app, parent: tk.Frame) -> None:
    """Fill *parent* with the Line Graphs controls and matplotlib figure.

    Creates and wires:
    - Channel selector (shares ``app._chan_var``)
    - Metric selector (hidden until a smFISH channel is active)
    - Export CSV + export-style panel buttons
    - Matplotlib figure with 3 subplots: mean, fraction, CDF
    - CDF x-axis limit controls
    """
    # ── Controls bar ───────────────────────────────────────────────────────
    line_ctrl = tk.Frame(parent, bg=BG_SIDE, pady=6, padx=10)
    line_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Channel selector
    tk.Label(line_ctrl, text="Channel:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._chan_cb_line = ttk.Combobox(line_ctrl, textvariable=app._chan_var,
                                     values=["GFP"], state="readonly",
                                     width=10, font=FM_BOLD)
    app._chan_cb_line.pack(side=tk.LEFT, padx=(0, 12))
    app._chan_cb_line.bind("<<ComboboxSelected>>",
                           lambda _e: app._set_active_channel(app._chan_var.get().lower()))

    # Metric selector (hidden by default, shown when current channel has smfish_count)
    app._metric_selector_frame = tk.Frame(line_ctrl, bg=BG_SIDE)
    tk.Label(app._metric_selector_frame, text="Metric:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._metric_var = tk.StringVar(value="Mean Intensity")
    app._metric_cb = ttk.Combobox(app._metric_selector_frame, textvariable=app._metric_var,
                                   values=["Mean Intensity", "smFISH Count"], state="readonly",
                                   width=14, font=FM_BOLD)
    app._metric_cb.pack(side=tk.LEFT, padx=(0, 12))
    app._metric_cb.bind("<<ComboboxSelected>>", lambda _e: app._on_metric_selected())

    # Right side: Export actions
    _make_action_button(
        line_ctrl, text="Export CSV", command=app._export_plot_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        line_ctrl, text="▸", command=lambda: app._open_export_style_panel("line"),
    ).pack(side=tk.RIGHT, padx=(0, 2))

    # ── Matplotlib figure (scrollable host) ───────────────────────────────
    app._line_fig = Figure(figsize=(7.2, 10.5), dpi=100, facecolor=PLOT_BG)
    app._line_ax_mean = app._line_fig.add_subplot(3, 1, 1)
    app._line_ax_frac = app._line_fig.add_subplot(3, 1, 2, sharex=app._line_ax_mean)
    app._line_ax_cdf  = app._line_fig.add_subplot(3, 1, 3)
    app._line_fig.subplots_adjust(hspace=0.62, top=0.96, bottom=0.08, left=0.13, right=0.97)

    line_plot_frame = tk.Frame(parent, bg=BG_APP)
    line_plot_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

    app._line_scroll_canvas = tk.Canvas(line_plot_frame, bg=BG_APP, highlightthickness=0, bd=0)
    app._line_scrollbar = tk.Scrollbar(line_plot_frame, orient=tk.VERTICAL, command=app._line_scroll_canvas.yview)
    app._line_scroll_canvas.configure(yscrollcommand=app._line_scrollbar.set)
    bind_mousewheel_scroll(app._line_scroll_canvas)
    app._line_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    app._line_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app._line_plot_inner = tk.Frame(app._line_scroll_canvas, bg=BG_APP)
    app._line_scroll_window = app._line_scroll_canvas.create_window((0, 0), window=app._line_plot_inner, anchor="nw")
    app._line_plot_inner.bind("<Configure>", lambda _e: app._line_scroll_canvas.configure(scrollregion=app._line_scroll_canvas.bbox("all")))
    app._line_scroll_canvas.bind("<Configure>", lambda e: app._line_scroll_canvas.itemconfigure(app._line_scroll_window, width=e.width))

    app._line_canvas = FigureCanvasTkAgg(app._line_fig, master=app._line_plot_inner)

    # Toolbar must be created before the canvas is packed
    nav = NavigationToolbar2Tk(app._line_canvas, parent)
    nav.config(bg=BG_APP)
    nav.update()

    # ── CDF x-axis limit controls (packed BOTTOM before canvas expands) ────
    cdf_ctrl = tk.Frame(parent, bg=BG_SIDE, pady=3, padx=8)
    cdf_ctrl.pack(side=tk.BOTTOM, fill=tk.X)
    tk.Label(cdf_ctrl, text="CDF x:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
    for _var in (app._cdf_xmin_var, app._cdf_xmax_var):
        _ce = tk.Entry(cdf_ctrl, textvariable=_var, font=FM_TINY,
                       fg=ACCENT, bg=BG_PANEL, insertbackground=ACCENT,
                       relief=tk.FLAT, width=7, justify="center",
                       highlightthickness=1, highlightcolor=ACCENT,
                       highlightbackground=BORDER)
        _ce.pack(side=tk.LEFT, padx=(0, 4))
        _ce.bind("<Return>",   lambda _e: app._redraw())
        _ce.bind("<FocusOut>", lambda _e: app._redraw())
    app._cdf_chan_lbl = tk.Label(cdf_ctrl,
                                  text=f"({app._active_channel.upper()} x range)",
                                  font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE)
    app._cdf_chan_lbl.pack(side=tk.LEFT)
    tk.Frame(parent, bg=BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

    app._line_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    _line_widget = app._line_canvas.get_tk_widget()
    _line_widget.configure(height=int(app._line_fig.get_figheight() * app._line_fig.get_dpi()))
    _line_widget.update_idletasks()
    app._line_scroll_canvas.configure(scrollregion=app._line_scroll_canvas.bbox("all"))
    app._line_canvas.mpl_connect("button_press_event",   app._on_fig_click)
    app._line_canvas.mpl_connect("motion_notify_event",  app._on_cdf_motion)
    app._line_canvas.mpl_connect("button_release_event", app._on_cdf_release)
