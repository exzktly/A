"""Scatter Plot: Aggregate tab builder extracted from centre_view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from well_viewer.runtime_app import (
    BG_APP,
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
from well_viewer.tabs import _make_action_button, _make_secondary_button


def build_scatter_agg_tab(app, parent: tk.Frame) -> None:
    """Fill *parent* with the Scatter Plot: Aggregate controls and figure.

    Creates and wires:
    - X-axis statistic selector (``app._scatter_agg_stat_x_var``)
    - Y-axis statistic selector (``app._scatter_agg_stat_y_var``)
    - Timepoint multi-select dropdown (``app._scatter_agg_tp_selections`` dict)
      NOTE: This tab intentionally uses a multi-select checkbox dropdown rather
      than a single Combobox because it aggregates *across* timepoints, whereas
      the Cells scatter and Bar Plots tabs show one timepoint at a time.
    - Export CSV / Save Figure buttons
    - Matplotlib figure with one scatter subplot
    """
    # ── Controls bar ───────────────────────────────────────────────────────
    scatter_agg_ctrl = tk.Frame(parent, bg=BG_SIDE, pady=6, padx=10)
    scatter_agg_ctrl.pack(fill=tk.X, side=tk.TOP)

    # Left side: X-axis and Y-axis statistic selectors
    tk.Label(scatter_agg_ctrl, text="X-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_agg_stat_x_var = tk.StringVar(value="Mean Fluorescence")
    app._scatter_agg_stat_x_cb = ttk.Combobox(scatter_agg_ctrl,
                                               textvariable=app._scatter_agg_stat_x_var,
                                               values=["Mean Fluorescence"], state="readonly",
                                               width=20, font=FM_TINY)
    app._scatter_agg_stat_x_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_agg_stat_x_cb.bind("<<ComboboxSelected>>",
                                    lambda _e: app._redraw_scatter_agg())

    tk.Label(scatter_agg_ctrl, text="Y-axis:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
    app._scatter_agg_stat_y_var = tk.StringVar(value="Fraction On")
    app._scatter_agg_stat_y_cb = ttk.Combobox(scatter_agg_ctrl,
                                               textvariable=app._scatter_agg_stat_y_var,
                                               values=["Fraction On"], state="readonly",
                                               width=20, font=FM_TINY)
    app._scatter_agg_stat_y_cb.pack(side=tk.LEFT, padx=(0, 15))
    app._scatter_agg_stat_y_cb.bind("<<ComboboxSelected>>",
                                    lambda _e: app._redraw_scatter_agg())

    tk.Label(scatter_agg_ctrl, text="Timepoints:", font=FM_BOLD,
             fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))

    # Custom multi-select dropdown with checkboxes.
    # Populated lazily via app._update_scatter_menus() when data is loaded.
    tp_frame = tk.Frame(scatter_agg_ctrl, bg=BG_SIDE)
    tp_frame.pack(side=tk.LEFT, padx=(0, 15), fill=tk.X, expand=True)

    app._scatter_agg_tp_button = ttk.Button(
        tp_frame, text="Select Timepoints",
        command=lambda: _open_timepoint_selector(app),
        style="ActionSecondary.TButton"
    )
    app._scatter_agg_tp_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

    app._scatter_agg_tp_label = tk.Label(
        tp_frame, text="(0 selected)", font=FM_TINY,
        fg=TXT_MUT, bg=BG_SIDE
    )
    app._scatter_agg_tp_label.pack(side=tk.LEFT, padx=(4, 0))

    # dict[str, BooleanVar] — populated later by _update_scatter_menus()
    app._scatter_agg_tp_selections = {}

    # Right side: Export actions
    _make_action_button(
        scatter_agg_ctrl, text="Export CSV", command=app._export_scatter_agg_data,
        style="ActionSuccess.TButton",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        scatter_agg_ctrl, text="Save Figure…", command=app._save_scatter_agg_figure,
    ).pack(side=tk.RIGHT, padx=(4, 0))
    _make_secondary_button(
        scatter_agg_ctrl, text="▸", command=lambda: app._open_export_style_panel("scatter_agg"),
    ).pack(side=tk.RIGHT, padx=(0, 2))

    # ── Matplotlib figure ──────────────────────────────────────────────────
    app._scatter_agg_fig = Figure(figsize=(8, 6), dpi=100, facecolor=PLOT_BG)
    app._ax_scatter_agg = app._scatter_agg_fig.add_subplot(1, 1, 1)
    app._scatter_agg_fig.subplots_adjust(hspace=0.3, top=0.95, bottom=0.12, left=0.12, right=0.97)

    app._scatter_agg_canvas = FigureCanvasTkAgg(app._scatter_agg_fig, master=parent)

    # Toolbar must be created before the canvas is packed
    scatter_agg_nav = NavigationToolbar2Tk(app._scatter_agg_canvas, parent)
    scatter_agg_nav.config(bg=BG_APP)
    scatter_agg_nav.update()

    app._scatter_agg_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))


# ── Timepoint multi-select dropdown helpers ────────────────────────────────

def _open_timepoint_selector(app) -> None:
    """Open a dropdown window with checkboxes for timepoint multi-selection."""
    # Close any existing dropdown
    if (hasattr(app, '_scatter_agg_tp_dropdown')
            and app._scatter_agg_tp_dropdown
            and app._scatter_agg_tp_dropdown.winfo_exists()):
        app._scatter_agg_tp_dropdown.destroy()

    selector = tk.Toplevel(app._scatter_agg_tp_button)
    selector.wm_overrideredirect(True)
    selector.configure(bg=BG_PANEL, bd=1, relief=tk.SOLID,
                       highlightthickness=1, highlightbackground=BORDER)
    app._scatter_agg_tp_dropdown = selector

    # Position below the button
    app._scatter_agg_tp_button.update_idletasks()
    x = app._scatter_agg_tp_button.winfo_rootx()
    y = (app._scatter_agg_tp_button.winfo_rooty()
         + app._scatter_agg_tp_button.winfo_height())
    selector.geometry(f"+{x}+{y}")

    # Scrollable inner frame
    inner_frame = tk.Frame(selector, bg=BG_PANEL)
    inner_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    canvas = tk.Canvas(inner_frame, bg=BG_PANEL, highlightthickness=0, height=150)
    scrollbar = ttk.Scrollbar(inner_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=BG_PANEL)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    for tp_str in sorted(app._scatter_agg_tp_selections.keys(), key=float):
        var = app._scatter_agg_tp_selections[tp_str]
        frame = tk.Frame(scrollable_frame, bg=BG_PANEL)
        frame.pack(anchor="w", padx=4, pady=2)

        def on_check_change(v=var):
            app._update_tp_selection_display()
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

    # Select All / Deselect All buttons
    button_frame = tk.Frame(selector, bg=BG_PANEL)
    button_frame.pack(fill=tk.X, padx=4, pady=4)

    def select_all():
        for var in app._scatter_agg_tp_selections.values():
            var.set(True)
        app._update_tp_selection_display()
        app._redraw_scatter_agg()

    def deselect_all():
        for var in app._scatter_agg_tp_selections.values():
            var.set(False)
        app._update_tp_selection_display()
        app._redraw_scatter_agg()

    ttk.Button(button_frame, text="All", command=select_all,
               style="ActionSecondary.TButton").pack(side=tk.LEFT, padx=2)
    ttk.Button(button_frame, text="None", command=deselect_all,
               style="ActionSecondary.TButton").pack(side=tk.LEFT, padx=2)

    # Close on focus loss or mouse leave
    selector.bind("<FocusOut>", lambda e: selector.destroy()
                  if selector.winfo_exists() else None)
    selector.bind("<Leave>", lambda e: selector.after(
        200, lambda: selector.destroy() if selector.winfo_exists() else None))
    selector.focus()
