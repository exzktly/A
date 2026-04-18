"""Main well-picker sidebar builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_sidebar(app, parent: tk.Frame) -> None:
    """Build the plate-map well selector sidebar.

    Creates:
      - "Plate" header with well-count meta + subtitle
      - Row/Col quick-select buttons (A-H, 01-12)
      - 8×12 WellLabel plate-map grid with drag-to-select bindings
      - Count + All + Clear footer
      - Sample groups panel (scrollable cards)
    """
    from well_viewer.runtime_app import (
        ACCENT, BG_SIDE, BG_PANEL, BORDER, FM_BOLD, FM_TINY, FM_TITLE,
        TXT_MUT, TXT_PRI,
        _PLATE_ROWS, _PLATE_COLS, _bind_drag, build_plate_grid,
        make_scrollable_canvas,
    )

    # ── Header: "Plate" + meta ────────────────────────────────────────────
    hdr = tk.Frame(parent, bg=BG_SIDE)
    hdr.pack(fill=tk.X, padx=10, pady=(8, 0))
    tk.Label(hdr, text="Plate", font=FM_TITLE, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT)
    tk.Label(hdr, text="8×12 · 96 wells", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.RIGHT, pady=2)

    tk.Label(
        parent,
        text="Drag to select · Colors encode sample group.",
        font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE,
        anchor="w", wraplength=280,
    ).pack(fill=tk.X, padx=10, pady=(2, 6))

    # ── Row / Col quick-select buttons ────────────────────────────────────
    rc_frame = tk.Frame(parent, bg=BG_SIDE)
    rc_frame.pack(fill=tk.X, padx=6, pady=(0, 4))
    app._sidebar_rc_frame = rc_frame

    row_frame = tk.Frame(rc_frame, bg=BG_SIDE)
    row_frame.pack(fill=tk.X)
    tk.Label(row_frame, text="Row:", font=FM_TINY, fg=TXT_MUT,
             bg=BG_SIDE, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 2))
    for ci, r in enumerate(_PLATE_ROWS):
        ttk.Button(
            row_frame,
            text=r,
            style="QuickSelect.TButton",
            command=lambda row=r: app._select_row(row),
            cursor="hand2",
        ).grid(row=0, column=ci + 1, sticky="ew", padx=1)
    row_frame.columnconfigure(0, weight=0)
    for ci in range(1, len(_PLATE_ROWS) + 1):
        row_frame.columnconfigure(ci, weight=1, uniform="rc_row")

    col_frame = tk.Frame(rc_frame, bg=BG_SIDE)
    col_frame.pack(fill=tk.X, pady=(2, 0))
    tk.Label(col_frame, text="Col:", font=FM_TINY, fg=TXT_MUT,
             bg=BG_SIDE, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 2))
    for ci, c in enumerate(_PLATE_COLS):
        ttk.Button(
            col_frame,
            text=c.lstrip("0") or "0",
            style="QuickSelect.TButton",
            command=lambda col=c: app._select_col(col),
            cursor="hand2",
        ).grid(row=0, column=ci + 1, sticky="ew", padx=1)
    col_frame.columnconfigure(0, weight=0)
    for ci in range(1, len(_PLATE_COLS) + 1):
        col_frame.columnconfigure(ci, weight=1, uniform="rc_col")

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=(4, 4))

    # ── Plate map grid ────────────────────────────────────────────────────
    map_outer = tk.Frame(parent, bg=BG_SIDE)
    map_outer.pack(fill=tk.X, padx=4)

    app._sidebar_btns = {}
    app._sidebar_drag_adding  = True
    app._sidebar_drag_visited = set()
    app._sb_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    app._bg_ds = {"adding": True, "visited": set(), "rep_toggled": set()}
    build_plate_grid(map_outer, app._sidebar_btns)
    _bind_drag(map_outer, app._sidebar_btns,
               app._sb_press, app._sb_drag, app._sb_release)

    # Hover → update status bar hover-well label
    for tok, btn in app._sidebar_btns.items():
        btn.bind("<Enter>", lambda _e, t=tok: (
            app._update_status_hover(t)
            if hasattr(app, "_update_status_hover") else None))
    map_outer.bind("<Leave>", lambda _e: (
        app._status_hover_lbl.config(text="")
        if hasattr(app, "_status_hover_lbl") else None))

    # ── Footer: count label + All + Clear ────────────────────────────────
    foot = tk.Frame(parent, bg=BG_SIDE)
    foot.pack(fill=tk.X, padx=6, pady=(4, 2))

    app._sel_count_lbl = tk.Label(foot, text="", font=FM_TINY,
                                   fg=TXT_MUT, bg=BG_SIDE, anchor="w")
    app._sel_count_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    ttk.Button(foot, text="All", command=app._select_all,
               style="PrimaryDark.TButton").pack(side=tk.LEFT, padx=(0, 3))
    ttk.Button(foot, text="Clear", command=app._select_none,
               style="Secondary.TButton").pack(side=tk.RIGHT)

    # Group-mode hint (kept for back-compat, hidden when empty)
    app._line_group_hint = tk.Label(
        parent,
        text="",
        font=FM_TINY, fg=ACCENT, bg=BG_SIDE,
        anchor="w", wraplength=280, justify=tk.LEFT)
    app._line_group_hint.pack(fill=tk.X, padx=10, pady=(0, 2))

    # ── Sample groups section ─────────────────────────────────────────────
    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=(2, 0))

    grp_head = tk.Frame(parent, bg=BG_SIDE)
    grp_head.pack(fill=tk.X, padx=10, pady=(6, 2))
    tk.Label(grp_head, text="SAMPLE GROUPS", font=FM_BOLD,
             fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
    ttk.Button(grp_head, text="+ New", style="Secondary.TButton",
               command=app._rep_add).pack(side=tk.RIGHT)

    # Scrollable group cards
    grp_canvas, grp_inner = make_scrollable_canvas(parent, bg=BG_SIDE)
    grp_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
    app._sidebar_groups_canvas = grp_canvas
    app._sidebar_groups_inner  = grp_inner
