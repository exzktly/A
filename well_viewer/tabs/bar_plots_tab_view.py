"""Bar Plots tab builder extracted from centre_view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

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


def build_bar_plots_tab(app, parent: tk.Frame) -> None:
    """Fill *parent* with the Bar Plots controls and matplotlib figure.

    Creates and wires:
    - Channel / Metric / Timepoint selectors (Metric shares ``app._metric_var``)
    - Export CSV / Save Figure buttons
    - Beeswarm, Violin, Log Y, Reset Order toggles and smoothing slider
    - Matplotlib figure with 2 subplots: mean, fraction
    - Y-axis limit controls
    - Drag-to-reorder bar binding
    """
    # Bar Plots tab: just the figure (grouping panel lives in the sidebar)
    bar_right = tk.Frame(parent, bg=BG_APP)
    bar_right.pack(fill=tk.BOTH, expand=True)

    # ── Controls bar ───────────────────────────────────────────────────────
    bar_ctrl = tk.Frame(bar_right, bg=BG_SIDE, pady=6, padx=10)
    bar_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Channel, Metric, Timepoint selectors
    # (Threshold + Error Band live in the persistent bottom bar)
    tk.Label(bar_ctrl, text="Channel:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._chan_cb_bar = ttk.Combobox(bar_ctrl, textvariable=app._chan_var,
                                    values=["GFP"], state="readonly",
                                    width=10, font=FM_BOLD)
    app._chan_cb_bar.pack(side=tk.LEFT, padx=(0, 15))
    app._chan_cb_bar.bind("<<ComboboxSelected>>",
                          lambda _e: app._set_active_channel(app._chan_var.get().lower()))

    # Metric selector for bar tab (shares _metric_var with line tab)
    app._metric_selector_frame_bar = tk.Frame(bar_ctrl, bg=BG_SIDE)
    tk.Label(app._metric_selector_frame_bar, text="Metric:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._metric_cb_bar = ttk.Combobox(app._metric_selector_frame_bar,
                                       textvariable=app._metric_var,
                                       values=["Mean Intensity", "smFISH Count"],
                                       state="readonly", width=14, font=FM_BOLD)
    app._metric_cb_bar.pack(side=tk.LEFT, padx=(0, 12))
    app._metric_cb_bar.bind("<<ComboboxSelected>>", lambda _e: app._on_metric_selected())

    tk.Label(bar_ctrl, text="Timepoint:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._bar_tp_cb = ttk.Combobox(bar_ctrl, textvariable=app._bar_tp_var,
                                    values=["—"], state="readonly",
                                    width=12, font=FM_TINY)
    app._bar_tp_cb.pack(side=tk.LEFT)
    app._bar_tp_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_bars())

    # Right side: Export actions
    _make_action_button(
        bar_ctrl, text="Export CSV", command=app._export_bar_plot_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        bar_ctrl, text="Save Figure…", command=app._save_bar_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        bar_ctrl, text="▸", command=lambda: app._open_export_style_panel("bar"),
    ).pack(side=tk.RIGHT, padx=(0, 2))

    # Toggle controls: Beeswarm, Violin, smoothing slider, Log Y, Reset Order
    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=(10, 10))
    app._swarm_btn = ttk.Button(bar_ctrl, text="Beeswarm", style="Toggle.TButton",
                                command=app._toggle_swarm)
    app._swarm_btn.pack(side=tk.LEFT)

    app._violin_btn = ttk.Button(bar_ctrl, text="Violin", style="Toggle.TButton",
                                 command=app._toggle_violin)
    app._violin_btn.pack(side=tk.LEFT, padx=(4, 0))

    # Smoothing slider — only interactive when violin mode is active
    tk.Label(bar_ctrl, text="Smooth:", font=FM_TINY,
             fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT, padx=(10, 2))
    app._violin_slider = tk.Scale(
        bar_ctrl, variable=app._violin_bw,
        from_=0.05, to=2.0, resolution=0.05,
        orient=tk.HORIZONTAL, length=80,
        font=FM_TINY, bg=BG_SIDE, fg=TXT_MUT,
        troughcolor=BG_PANEL, highlightthickness=0,
        showvalue=False, bd=0,
        command=lambda _v: app._redraw_bars() if app._bar_violin.get() else None)
    app._violin_slider.pack(side=tk.LEFT)
    app._violin_slider.config(state=tk.DISABLED)

    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=(10, 10))
    app._bar_log_btn = ttk.Button(bar_ctrl, text="Log Y", style="Toggle.TButton",
                                  command=app._toggle_log_scale)
    app._bar_log_btn.pack(side=tk.LEFT)

    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=(10, 10))
    app._bar_reset_order_btn = ttk.Button(bar_ctrl, text="Reset Order",
                                          style="ToggleMuted.TButton",
                                          command=app._bar_reset_order)
    app._bar_reset_order_btn.pack(side=tk.LEFT)

    # ── Matplotlib figure (scrollable host) ───────────────────────────────
    app._bar_fig = Figure(figsize=(6.2, 8.4), dpi=100, facecolor=PLOT_BG)
    app._ax_bar_mean = app._bar_fig.add_subplot(2, 1, 1)
    app._ax_bar_frac = app._bar_fig.add_subplot(2, 1, 2)
    app._bar_fig.subplots_adjust(hspace=0.65, top=0.95, bottom=0.14, left=0.15, right=0.97)

    bar_plot_frame = tk.Frame(bar_right, bg=BG_APP)
    bar_plot_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 0))

    app._bar_scroll_canvas = tk.Canvas(bar_plot_frame, bg=BG_APP, highlightthickness=0, bd=0)
    app._bar_scrollbar = tk.Scrollbar(bar_plot_frame, orient=tk.VERTICAL, command=app._bar_scroll_canvas.yview)
    app._bar_scroll_canvas.configure(yscrollcommand=app._bar_scrollbar.set)
    app._bar_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    app._bar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app._bar_plot_inner = tk.Frame(app._bar_scroll_canvas, bg=BG_APP)
    app._bar_scroll_window = app._bar_scroll_canvas.create_window((0, 0), window=app._bar_plot_inner, anchor="nw")
    app._bar_plot_inner.bind("<Configure>", lambda _e: app._bar_scroll_canvas.configure(scrollregion=app._bar_scroll_canvas.bbox("all")))
    app._bar_scroll_canvas.bind("<Configure>", lambda e: app._bar_scroll_canvas.itemconfigure(app._bar_scroll_window, width=e.width))

    app._bar_canvas = FigureCanvasTkAgg(app._bar_fig, master=app._bar_plot_inner)
    bar_nav = NavigationToolbar2Tk(app._bar_canvas, bar_right)
    bar_nav.config(bg=BG_APP)
    bar_nav.update()
    app._bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    _bar_widget = app._bar_canvas.get_tk_widget()
    _bar_widget.configure(height=int(app._bar_fig.get_figheight() * app._bar_fig.get_dpi()))
    _bar_widget.update_idletasks()
    app._bar_scroll_canvas.configure(scrollregion=app._bar_scroll_canvas.bbox("all"))

    # ── Y-axis limit controls ──────────────────────────────────────────────
    # In their own row below the plots so they are always visible.
    ylim_row = tk.Frame(bar_right, bg=BG_SIDE, pady=4, padx=8)
    ylim_row.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Frame(ylim_row, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 4))
    for lbl_txt, lo_var, hi_var, _lbl_attr in (
        (f"{app._active_channel.upper()} y:", app._bar_ylim_mean_lo, app._bar_ylim_mean_hi,
         "_bar_ylim_chan_lbl"),
        ("Frac y:", app._bar_ylim_frac_lo, app._bar_ylim_frac_hi, None),
    ):
        _lbl = tk.Label(ylim_row, text=lbl_txt, font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE)
        _lbl.pack(side=tk.LEFT)
        if _lbl_attr:
            setattr(app, _lbl_attr, _lbl)
        for var in (lo_var, hi_var):
            e = tk.Entry(ylim_row, textvariable=var, width=5,
                         font=FM_TINY, fg=ACCENT, bg=BG_PANEL,
                         relief=tk.FLAT, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(side=tk.LEFT, padx=(1, 0))
            e.bind("<Return>",   lambda _e: app._redraw_bars())
            e.bind("<FocusOut>", lambda _e: app._redraw_bars())
        tk.Label(ylim_row, text="   ", font=FM_TINY, bg=BG_SIDE).pack(side=tk.LEFT)

    # ── Drag-to-reorder bar binding ────────────────────────────────────────
    # Bound directly to the Tk widget rather than via mpl_connect so that
    # NavigationToolbar2Tk cannot intercept or swallow these events.
    app._bar_drag_state: dict = {
        "active":  False,
        "src_idx": -1,
        "cur_idx": -1,
    }
    _bw = app._bar_canvas.get_tk_widget()
    _bw.bind("<ButtonPress-1>",   app._on_bar_drag_press)
    _bw.bind("<B1-Motion>",       app._on_bar_drag_motion)
    _bw.bind("<ButtonRelease-1>", app._on_bar_drag_release)
