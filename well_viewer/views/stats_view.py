"""Statistics-tab UI builders extracted from well_viewer3."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from well_viewer.ui_helpers import btn_primary, btn_secondary
from ui.theme import get_color


def build_stats_tab(app, parent: tk.Frame, *, bg_app: str, bg_side: str) -> None:
    """Build statistics results area (group editor lives in sidebar)."""
    app._stats_groups = []
    app._stats_active_grp = -1
    app._build_stats_results_panel(parent)


def build_stats_group_editor(
    app,
    parent: tk.Frame,
    *,
    fm_bold,
    fm_tiny,
    txt_mut: str,
    txt_sec: str,
    txt_pri: str,
    bg_side: str,
    bg_panel: str,
    bg_cell: str,
    bg_hover: str,
    accent: str,
    border: str,
    clr_white: str,
    clr_avail_well: str,
    clr_avail_hover: str,
    well_colors: list[str],
    bind_drag_fn,
    build_plate_grid_fn,
    make_scrollable_canvas_fn,
    extract_well_token_fn,
) -> None:
    """Build the left-hand statistics group editor."""
    hdr1 = tk.Frame(parent, bg=bg_side, pady=4, padx=8)
    hdr1.pack(fill=tk.X)
    tk.Label(hdr1, text="COMPARISON GROUPS", font=fm_bold, fg=txt_mut, bg=bg_side).pack(side=tk.LEFT)
    btn_primary(hdr1, "+ Add", app._stats_grp_add).pack(side=tk.RIGHT)
    btn_secondary(hdr1, "Clear All", app._stats_grp_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

    tk.Frame(parent, bg=border, height=1).pack(fill=tk.X)
    tk.Label(parent, text="Drag wells to assign them to a group.  Select a group card first.", font=fm_tiny, fg=txt_mut, bg=bg_side, pady=3, anchor="w", wraplength=360).pack(fill=tk.X, padx=6)

    map_frame = tk.Frame(parent, bg=bg_side)
    map_frame.pack(fill=tk.X, padx=4)
    app._stats_map_btns = {}
    build_plate_grid_fn(map_frame, app._stats_map_btns)

    app._stats_drag_adding = True
    app._stats_drag_visited = set()

    def _tok_at(event) -> Optional[str]:
        sx = event.widget.winfo_rootx() + event.x
        sy = event.widget.winfo_rooty() + event.y
        w = event.widget.winfo_containing(sx, sy)
        for tok, btn in app._stats_map_btns.items():
            if btn is w:
                return tok
        return None

    def _press(event):
        tok = _tok_at(event)
        if tok is None or tok not in app._tok_to_label:
            return
        grp = app._stats_active_group()
        if grp is None:
            return
        label = app._tok_to_label[tok]
        app._stats_drag_adding = label not in grp.wells
        app._stats_drag_visited = set()
        app._stats_apply_drag(tok)

    def _drag(event):
        tok = _tok_at(event)
        if tok and tok not in app._stats_drag_visited:
            app._stats_apply_drag(tok)

    def _release(_event):
        if app._stats_drag_visited:
            app._stats_refresh_map()
            app._stats_refresh_group_list()
        app._stats_drag_visited = set()

    bind_drag_fn(map_frame, app._stats_map_btns, _press, _drag, _release)

    tk.Frame(parent, bg=border, height=1).pack(fill=tk.X, pady=(4, 0))
    sf = tk.Frame(parent, bg=bg_side)
    sf.pack(fill=tk.BOTH, expand=True)
    app._stats_grp_canvas, app._stats_grp_inner = make_scrollable_canvas_fn(sf, bg=bg_side)

    app._stats_refresh_map()
    app._stats_refresh_group_list()


def build_stats_results_panel(
    app,
    parent: tk.Frame,
    *,
    fm_bold,
    fm_tiny,
    txt_mut: str,
    txt_sec: str,
    txt_pri: str,
    bg_app: str,
    bg_side: str,
    bg_panel: str,
    border: str,
    accent: str,
    clr_white: str,
) -> None:
    """Build the right-hand stats controls/results panel."""
    app._stats_hdr = tk.Frame(parent, bg=bg_side, pady=4, padx=12)
    app._stats_hdr.pack(fill=tk.X)
    app._stats_hdr_label = tk.Label(app._stats_hdr, text="STATISTICAL TEST", font=fm_bold, fg=txt_mut, bg=bg_side)
    app._stats_hdr_label.pack(side=tk.LEFT)

    app._stats_ctrl = tk.Frame(parent, bg=bg_app, pady=6, padx=12)
    app._stats_ctrl.pack(fill=tk.X)

    app._stats_test_label = tk.Label(app._stats_ctrl, text="Test:", font=fm_tiny, fg=txt_sec, bg=bg_app)
    app._stats_test_label.grid(row=0, column=0, sticky="w", padx=(0, 6))
    app._stats_test_var = tk.StringVar(value="t-test")
    _TEST_OPTIONS = ["t-test (Fisher)", "Wilcoxon rank-sum", "Mann-Whitney U", "KS test (2 wells only)"]
    test_cb = ttk.Combobox(app._stats_ctrl, textvariable=app._stats_test_var, values=_TEST_OPTIONS, state="readonly", width=26, font=fm_tiny)
    test_cb.grid(row=0, column=1, sticky="w")
    test_cb.bind("<<ComboboxSelected>>", lambda _e: app._stats_on_test_change())

    app._stats_tp_label = tk.Label(app._stats_ctrl, text="Timepoint:", font=fm_tiny, fg=txt_sec, bg=bg_app)
    app._stats_tp_label.grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
    app._stats_tp_var = tk.StringVar(value="—")
    app._stats_tp_cb = ttk.Combobox(app._stats_ctrl, textvariable=app._stats_tp_var, values=["—"], state="readonly", width=12, font=fm_tiny)
    app._stats_tp_cb.grid(row=1, column=1, sticky="w", pady=(6, 0))

    btn_primary(app._stats_ctrl, "Run test", app._stats_run, padx=10, pady=3).grid(row=0, column=2, rowspan=2, padx=(16, 0), sticky="ns")
    app._stats_sep = tk.Frame(parent, bg=border, height=1)
    app._stats_sep.pack(fill=tk.X, padx=12, pady=(4, 0))

    app._stats_fig_frame = tk.Frame(parent, bg=bg_app)
    from matplotlib.figure import Figure as _StatsFigure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as _StatsFCA

    app._stats_fig = _StatsFigure(figsize=(5, 2.8), dpi=96, facecolor=bg_app)
    app._stats_ax = app._stats_fig.add_subplot(111)
    app._stats_canvas_widget = _StatsFCA(app._stats_fig, master=app._stats_fig_frame)
    app._stats_canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    app._stats_res_frame = tk.Frame(parent, bg=bg_app)
    app._stats_res_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
    app._stats_result_text = tk.Text(
        app._stats_res_frame,
        font=fm_tiny,
        bg=bg_panel,
        fg=txt_pri,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=border,
        wrap=tk.WORD,
        state=tk.DISABLED,
        padx=8,
        pady=6,
    )
    app._stats_scrollbar = tk.Scrollbar(app._stats_res_frame, orient=tk.VERTICAL, command=app._stats_result_text.yview)
    app._stats_result_text.configure(yscrollcommand=app._stats_scrollbar.set)
    app._stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app._stats_result_text.pack(fill=tk.BOTH, expand=True)

    app._stats_update_tp_menu()
