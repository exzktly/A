"""Centre notebook/tab builder extracted from runtime_app."""

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from well_viewer.runtime_app import (
    ACCENT,
    BG_APP,
    BG_CELL,
    BG_HOVER,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    FM_BOLD,
    FM_TINY,
    PLOT_BG,
    TXT_MUT,
    TXT_SEC,
)


def _make_action_button(parent: tk.Widget, *, text: str, command, style: str):
    """Create a primary action button with the shared tab-toolbar style."""
    return ttk.Button(parent, text=text, command=command, style=style, cursor="hand2")


def _make_secondary_button(parent: tk.Widget, *, text: str, command):
    """Create a neutral toolbar button with the shared tab-toolbar style."""
    return ttk.Button(parent, text=text, command=command, style="ActionSecondary.TButton", cursor="hand2")


def _open_timepoint_selector(app):
    """Open a dropdown window with checkboxes for timepoint selection."""
    # Close any existing dropdown
    if hasattr(app, '_scatter_agg_tp_dropdown') and app._scatter_agg_tp_dropdown and app._scatter_agg_tp_dropdown.winfo_exists():
        app._scatter_agg_tp_dropdown.destroy()

    # Create a Toplevel window positioned below the button
    selector = tk.Toplevel(app._scatter_agg_tp_button)
    selector.wm_overrideredirect(True)
    selector.configure(bg=BG_PANEL, bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground=BORDER)

    # Store reference to the dropdown so we can close it later
    app._scatter_agg_tp_dropdown = selector

    # Position below the button
    app._scatter_agg_tp_button.update_idletasks()
    x = app._scatter_agg_tp_button.winfo_rootx()
    y = app._scatter_agg_tp_button.winfo_rooty() + app._scatter_agg_tp_button.winfo_height()
    selector.geometry(f"+{x}+{y}")

    # Inner frame with scrollbar for many timepoints
    inner_frame = tk.Frame(selector, bg=BG_PANEL)
    inner_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # Create scrollable container
    canvas = tk.Canvas(inner_frame, bg=BG_PANEL, highlightthickness=0, height=150)
    scrollbar = ttk.Scrollbar(inner_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=BG_PANEL)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Add checkboxes for each timepoint
    for tp_str in sorted(app._scatter_agg_tp_selections.keys(), key=lambda x: float(x)):
        var = app._scatter_agg_tp_selections[tp_str]
        frame = tk.Frame(scrollable_frame, bg=BG_PANEL)
        frame.pack(anchor="w", padx=4, pady=2)

        def on_check_change(v=var):
            _update_tp_selection_display(app)
            app._redraw_scatter_agg()

        cb = tk.Checkbutton(
            frame, text=tp_str, variable=var,
            bg=BG_PANEL, fg=TXT_SEC, font=FM_TINY,
            command=on_check_change, selectcolor=BG_PANEL,
            activebackground=BG_HOVER, activeforeground=TXT_SEC
        )
        cb.pack(anchor="w")

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    if len(app._scatter_agg_tp_selections) > 6:
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Add Select All / Deselect All buttons
    button_frame = tk.Frame(selector, bg=BG_PANEL)
    button_frame.pack(fill=tk.X, padx=4, pady=4)

    def select_all():
        for var in app._scatter_agg_tp_selections.values():
            var.set(True)
        _update_tp_selection_display(app)
        app._redraw_scatter_agg()

    def deselect_all():
        for var in app._scatter_agg_tp_selections.values():
            var.set(False)
        _update_tp_selection_display(app)
        app._redraw_scatter_agg()

    ttk.Button(button_frame, text="All", command=select_all, style="ActionSecondary.TButton").pack(side=tk.LEFT, padx=2)
    ttk.Button(button_frame, text="None", command=deselect_all, style="ActionSecondary.TButton").pack(side=tk.LEFT, padx=2)

    # Close dropdown when mouse leaves the window or focus is lost
    def close_dropdown():
        if selector.winfo_exists():
            selector.destroy()

    # Close on focus loss (works when clicking outside)
    selector.bind("<FocusOut>", lambda e: close_dropdown())
    # Also close when mouse leaves the dropdown (with a small delay to avoid premature closing)
    selector.bind("<Leave>", lambda e: selector.after(200, close_dropdown))

    selector.focus()


def _update_tp_selection_display(app):
    """Update the label showing how many timepoints are selected."""
    count = sum(1 for var in app._scatter_agg_tp_selections.values() if var.get())
    total = len(app._scatter_agg_tp_selections)
    if count == 0:
        label_text = f"({count}/{total} selected)"
    elif count == total:
        label_text = f"(All {count} selected)"
    else:
        label_text = f"({count}/{total} selected)"
    app._scatter_agg_tp_label.config(text=label_text)


def build_centre(app, parent: tk.Frame) -> None:
    from smfish_tab import SmfishTab

    app._notebook = ttk.Notebook(parent)
    app._notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
    app._notebook.bind("<<NotebookTabChanged>>", app._on_tab_change)

    # ── Tab 1: Line Graphs ───────────────────────────────────────────────
    tab_line = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_line, text="Line Graphs")

    # Controls bar — Line Graphs export actions and channel selector
    # (Threshold + Error Band live in the persistent bottom bar)
    line_ctrl = tk.Frame(tab_line, bg=BG_SIDE, pady=6, padx=10)
    line_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Channel selector
    tk.Label(line_ctrl, text="Channel:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._chan_cb_line = ttk.Combobox(line_ctrl, textvariable=app._chan_var,
                                     values=["GFP"], state="readonly",
                                     width=10, font=FM_BOLD)
    app._chan_cb_line.pack(side=tk.LEFT, padx=(0, 12))
    app._chan_cb_line.bind("<<ComboboxSelected>>", lambda _e: app._set_active_channel(app._chan_var.get().lower()))

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
        line_ctrl, text="Save Figure…", command=app._save_line_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))

    app._fig = Figure(figsize=(7, 9), dpi=100, facecolor=PLOT_BG)
    app._ax_mean = app._fig.add_subplot(3, 1, 1)
    app._ax_frac = app._fig.add_subplot(3, 1, 2, sharex=app._ax_mean)
    app._ax_cdf  = app._fig.add_subplot(3, 1, 3)
    app._fig.subplots_adjust(hspace=0.55, top=0.95, bottom=0.07, left=0.13, right=0.97)

    app._mpl_canvas = FigureCanvasTkAgg(app._fig, master=tab_line)

    # Toolbar must be created before the canvas is packed
    nav = NavigationToolbar2Tk(app._mpl_canvas, tab_line)
    nav.config(bg=BG_APP)
    nav.update()

    # CDF x-axis limit controls — sit directly under the CDF subplot.
    # Must be packed side=BOTTOM before the canvas so pack reserves the
    # space at the bottom of tab_line before the canvas expands to fill.
    cdf_ctrl = tk.Frame(tab_line, bg=BG_SIDE, pady=3, padx=8)
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
    tk.Frame(tab_line, bg=BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

    app._mpl_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
    app._mpl_canvas.mpl_connect("button_press_event",   app._on_fig_click)
    app._mpl_canvas.mpl_connect("motion_notify_event",  app._on_cdf_motion)
    app._mpl_canvas.mpl_connect("button_release_event", app._on_cdf_release)

    # ── Tab 2: Sample Definitions (added last — see below after Preview) ──
    # Frame must be created here so _build_bar_group_panel and
    # _build_bar_perwell_strip can reference _sidebar_groups_frame,
    # but the notebook.add call is deferred to after Preview so the tab
    # appears last in the tab bar.
    tab_groups = tk.Frame(app._notebook, bg=BG_APP)
    app._build_groups_centre(tab_groups)

    # Sample Definitions uses a dedicated sidebar replicate panel.
    app._build_replicate_panel(app._sidebar_sample_frame)

    # Build the shared groups panel into the dedicated sidebar frame.
    # Shown in sidebar only when Bar Plots tab is active.
    app._build_bar_group_panel(app._sidebar_groups_frame)

    # Bar-specific per-well strip removed — All/None in the unified
    # well picker (via _select_all / _select_none) serves both tabs.

    # ── Tab 3: Bar Plots ─────────────────────────────────────────────────
    tab_bar = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_bar, text="Bar Plots")

    # Bar Plots tab: just the figure (grouping panel in sidebar_groups_frame)
    bar_right = tk.Frame(tab_bar, bg=BG_APP)
    bar_right.pack(fill=tk.BOTH, expand=True)

    bar_ctrl = tk.Frame(bar_right, bg=BG_SIDE, pady=6, padx=10)
    bar_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Channel selector and Timepoint selector
    # (Threshold + Error Band live in the persistent bottom bar)
    tk.Label(bar_ctrl, text="Channel:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._chan_cb_bar = ttk.Combobox(bar_ctrl, textvariable=app._chan_var,
                                    values=["GFP"], state="readonly",
                                    width=10, font=FM_BOLD)
    app._chan_cb_bar.pack(side=tk.LEFT, padx=(0, 15))
    app._chan_cb_bar.bind("<<ComboboxSelected>>", lambda _e: app._set_active_channel(app._chan_var.get().lower()))

    # Metric selector for bar tab (shares _metric_var with line tab)
    app._metric_selector_frame_bar = tk.Frame(bar_ctrl, bg=BG_SIDE)
    tk.Label(app._metric_selector_frame_bar, text="Metric:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._metric_cb_bar = ttk.Combobox(app._metric_selector_frame_bar, textvariable=app._metric_var,
                                       values=["Mean Intensity", "smFISH Count"], state="readonly",
                                       width=14, font=FM_BOLD)
    app._metric_cb_bar.pack(side=tk.LEFT, padx=(0, 12))
    app._metric_cb_bar.bind("<<ComboboxSelected>>", lambda _e: app._on_metric_selected())

    tk.Label(bar_ctrl, text="Timepoint:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._bar_tp_cb = ttk.Combobox(bar_ctrl, textvariable=app._bar_tp_var,
                                    values=["—"], state="readonly",
                                    width=12, font=FM_TINY)
    app._bar_tp_cb.pack(side=tk.LEFT)
    app._bar_tp_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_bars())

    # Right side: export actions
    _make_action_button(
        bar_ctrl, text="Export CSV", command=app._export_bar_plot_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        bar_ctrl, text="Save Figure…", command=app._save_bar_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))

    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y,
                                                 padx=(10, 10))
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

    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y,
                                                  padx=(10, 10))
    app._bar_log_btn = ttk.Button(bar_ctrl, text="Log Y", style="Toggle.TButton",
                                  command=app._toggle_log_scale)
    app._bar_log_btn.pack(side=tk.LEFT)

    tk.Frame(bar_ctrl, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y,
                                                  padx=(10, 10))
    app._bar_reset_order_btn = ttk.Button(bar_ctrl, text="Reset Order",
                                          style="ToggleMuted.TButton",
                                          command=app._bar_reset_order)
    app._bar_reset_order_btn.pack(side=tk.LEFT)

    app._bar_fig = Figure(figsize=(5, 6), dpi=100, facecolor=PLOT_BG)
    app._ax_bar_mean = app._bar_fig.add_subplot(2, 1, 1)
    app._ax_bar_frac = app._bar_fig.add_subplot(2, 1, 2)
    app._bar_fig.subplots_adjust(hspace=0.6, top=0.93, bottom=0.14, left=0.15, right=0.97)

    app._bar_canvas = FigureCanvasTkAgg(app._bar_fig, master=bar_right)
    bar_nav = NavigationToolbar2Tk(app._bar_canvas, bar_right)
    bar_nav.config(bg=BG_APP)
    bar_nav.update()
    app._bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 0))

    # Y-axis limit controls — in their own row below the plots so they are
    # always visible regardless of window height.
    ylim_row = tk.Frame(bar_right, bg=BG_SIDE, pady=4, padx=8)
    ylim_row.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Frame(ylim_row, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 4))
    for lbl_txt, lo_var, hi_var, _lbl_attr in (
        (f"{app._active_channel.upper()} y:", app._bar_ylim_mean_lo, app._bar_ylim_mean_hi, "_bar_ylim_chan_lbl"),
        ("Frac y:", app._bar_ylim_frac_lo, app._bar_ylim_frac_hi, None),
    ):
        _lbl = tk.Label(ylim_row, text=lbl_txt, font=FM_TINY,
                        fg=TXT_MUT, bg=BG_SIDE)
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
        tk.Label(ylim_row, text="   ", font=FM_TINY,
                 bg=BG_SIDE).pack(side=tk.LEFT)

    # Drag-and-drop bar reordering.
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

    # ── Tab 4: Preview ────────────────────────────────────────────────────
    tab_preview = tk.Frame(app._notebook, bg=BG_SIDE)
    app._notebook.add(tab_preview, text="Preview")
    app._build_right_panel(tab_preview)
    app._build_preview_picker(app._sidebar_preview_frame)

    # ── Tab 5: Review CSV ─────────────────────────────────────────────────
    tab_review_csv = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_review_csv, text="Review CSV")
    app._build_review_csv_tab(tab_review_csv)

    # ── Tab 6: smFISH ─────────────────────────────────────────────────────
    tab_smfish = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_smfish, text="smFISH")
    app._smfish_tab = SmfishTab(tab_smfish, app=app)
    app._smfish_tab.pack(fill=tk.BOTH, expand=True)

    # ── Tab 7: Batch Export ───────────────────────────────────────────────
    tab_batch = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_batch, text="Batch Export")

    batch_wrap = tk.Frame(tab_batch, bg=BG_APP, padx=16, pady=16)
    batch_wrap.pack(fill=tk.BOTH, expand=True)
    tk.Label(batch_wrap, text="Batch Export", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_APP).pack(anchor="w", pady=(0, 8))
    tk.Label(batch_wrap,
             text="Run line/bar batch exports and save CSV outputs from one place.",
             font=FM_TINY, fg=TXT_MUT, bg=BG_APP).pack(anchor="w", pady=(0, 12))

    actions = tk.Frame(batch_wrap, bg=BG_APP)
    actions.pack(anchor="w")
    _make_action_button(
        actions, text="Line Graph Batch Export",
        command=app._open_batch_export, style="ActionIndigo.TButton",
    ).pack(anchor="w", pady=(0, 6))
    _make_action_button(
        actions, text="Bar Plot Batch Export",
        command=app._open_bar_batch_export, style="ActionIndigo.TButton",
    ).pack(anchor="w", pady=(0, 6))
    _make_action_button(
        actions, text="Export Line Graph CSV",
        command=app._export_plot_data, style="ActionSuccess.TButton",
    ).pack(anchor="w", pady=(0, 6))
    _make_action_button(
        actions, text="Export Bar Plot CSV",
        command=app._export_bar_plot_data, style="ActionSuccess.TButton",
    ).pack(anchor="w", pady=(0, 6))
    _make_action_button(
        actions, text="Export Raw Data CSV",
        command=app._export_raw_data_csv, style="ActionSuccess.TButton",
    ).pack(anchor="w", pady=(0, 6))

    # ── Tab 7: Statistics ──────────────────────────────────────────────────
    tab_stats = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_stats, text="Statistics")
    app._build_stats_tab(tab_stats)
    app._build_stats_group_editor(app._sidebar_stats_frame)

    # ── Tab 8: Scatter Plot: Cells ────────────────────────────────────────
    tab_scatter = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter, text="Scatter Plot: Cells")

    # Controls bar — Scatter plot controls
    scatter_ctrl = tk.Frame(tab_scatter, bg=BG_SIDE, pady=6, padx=10)
    scatter_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Channel and timepoint selectors
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

    # Create matplotlib figure for scatter plot
    app._scatter_fig = Figure(figsize=(8, 6), dpi=100, facecolor=PLOT_BG)
    app._ax_scatter = app._scatter_fig.add_subplot(1, 1, 1)
    app._scatter_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)

    app._scatter_canvas = FigureCanvasTkAgg(app._scatter_fig, master=tab_scatter)

    # Toolbar must be created before the canvas is packed
    scatter_nav = NavigationToolbar2Tk(app._scatter_canvas, tab_scatter)
    scatter_nav.config(bg=BG_APP)
    scatter_nav.update()

    app._scatter_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
    app._scatter_canvas.mpl_connect("button_press_event", app._on_scatter_click)
    app._scatter_canvas.mpl_connect("motion_notify_event", app._on_scatter_motion)

    # ── Tab 8: Scatter Plot: Aggregate ────────────────────────────────────
    tab_scatter_agg = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter_agg, text="Scatter Plot: Aggregate")

    # Controls bar — Scatter plot aggregate controls
    scatter_agg_ctrl = tk.Frame(tab_scatter_agg, bg=BG_SIDE, pady=6, padx=10)
    scatter_agg_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: Statistic selectors (Mean Fluorescence or Fraction On per channel)
    tk.Label(scatter_agg_ctrl, text="X-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_agg_stat_x_var = tk.StringVar(value="Mean Fluorescence")
    app._scatter_agg_stat_x_cb = ttk.Combobox(scatter_agg_ctrl, textvariable=app._scatter_agg_stat_x_var,
                                              values=["Mean Fluorescence"], state="readonly",
                                              width=20, font=FM_TINY)
    app._scatter_agg_stat_x_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_agg_stat_x_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_scatter_agg())

    tk.Label(scatter_agg_ctrl, text="Y-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_agg_stat_y_var = tk.StringVar(value="Fraction On")
    app._scatter_agg_stat_y_cb = ttk.Combobox(scatter_agg_ctrl, textvariable=app._scatter_agg_stat_y_var,
                                              values=["Fraction On"], state="readonly",
                                              width=20, font=FM_TINY)
    app._scatter_agg_stat_y_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_agg_stat_y_cb.bind("<<ComboboxSelected>>", lambda _e: app._redraw_scatter_agg())

    tk.Label(scatter_agg_ctrl, text="Timepoints:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))

    # Custom dropdown with checkboxes for timepoint selection
    tp_frame = tk.Frame(scatter_agg_ctrl, bg=BG_SIDE)
    tp_frame.pack(side=tk.LEFT, padx=(0, 15), fill=tk.X, expand=True)

    # Button to open timepoint selector
    app._scatter_agg_tp_button = ttk.Button(
        tp_frame, text="Select Timepoints",
        command=lambda: _open_timepoint_selector(app),
        style="ActionSecondary.TButton"
    )
    app._scatter_agg_tp_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Label to show selected count
    app._scatter_agg_tp_label = tk.Label(
        tp_frame, text="(0 selected)", font=FM_TINY,
        fg=TXT_MUT, bg=BG_SIDE
    )
    app._scatter_agg_tp_label.pack(side=tk.LEFT, padx=(4, 0))

    # Store for timepoint selections (will be populated later)
    app._scatter_agg_tp_selections = {}  # maps tp_str -> BooleanVar

    # Right side: Export actions
    _make_action_button(
        scatter_agg_ctrl, text="Export CSV", command=app._export_scatter_agg_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        scatter_agg_ctrl, text="Save Figure…", command=app._save_scatter_agg_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))

    # Create matplotlib figure for aggregate scatter plot
    app._scatter_agg_fig = Figure(figsize=(8, 6), dpi=100, facecolor=PLOT_BG)
    app._ax_scatter_agg = app._scatter_agg_fig.add_subplot(1, 1, 1)
    app._scatter_agg_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)

    app._scatter_agg_canvas = FigureCanvasTkAgg(app._scatter_agg_fig, master=tab_scatter_agg)

    # Toolbar must be created before the canvas is packed
    scatter_agg_nav = NavigationToolbar2Tk(app._scatter_agg_canvas, tab_scatter_agg)
    scatter_agg_nav.config(bg=BG_APP)
    scatter_agg_nav.update()

    app._scatter_agg_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

    # ── Tab 9: Cell Gating ───────────────────────────────────────────
    from well_viewer.runtime_app import CellGatingTab
    tab_cell_gating = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_cell_gating, text="Cell Gating")
    app._cell_gating_tab = CellGatingTab(tab_cell_gating, app)
    app._cell_gating_tab.pack(fill=tk.BOTH, expand=True)

    # ── Tab 10: Sample Definitions (last) ──────────────────────────────────
    app._notebook.add(tab_groups, text="Sample Definitions")
