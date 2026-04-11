"""Main well-picker sidebar builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_sidebar(app, parent: tk.Frame) -> None:
    """Build the 8×12 plate-map well selector in the sidebar.

    Creates:
      - "WELLS" header
      - Row/Col quick-select buttons (A-H, 01-12)
      - 8×12 WellLabel plate-map grid with drag-to-select bindings
      - All / None buttons
      - Selected-well count label
      - Group-mode hint label
    """
    from well_viewer.runtime_app import (
        ACCENT, BG_SIDE, BORDER, FM_BOLD, FM_TINY, TXT_MUT,
        _PLATE_ROWS, _PLATE_COLS, _bind_drag, build_plate_grid,
    )

    tk.Label(parent, text="WELLS", font=FM_BOLD, fg=TXT_MUT,
             bg=BG_SIDE, pady=6).pack(fill=tk.X, padx=10)

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

    # ── All / None buttons ────────────────────────────────────────────────
    br = tk.Frame(parent, bg=BG_SIDE)
    br.pack(fill=tk.X, padx=6, pady=(4, 6))
    app._sidebar_allnone_frame = br
    for txt, cmd in (("All", app._select_all), ("None", app._select_none)):
        ttk.Button(br, text=txt, command=cmd,
                   style="PrimaryDark.TButton").pack(
                   side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

    # ── Selected well count label ─────────────────────────────────────────
    app._sel_count_lbl = tk.Label(parent, text="", font=FM_TINY,
                                   fg=TXT_MUT, bg=BG_SIDE, anchor="w")
    app._sel_count_lbl.pack(fill=tk.X, padx=10, pady=(0, 4))

    # ── Group-mode hint ───────────────────────────────────────────────────
    app._line_group_hint = tk.Label(
        parent,
        text="",
        font=FM_TINY, fg=ACCENT, bg=BG_SIDE,
        anchor="w", wraplength=280, justify=tk.LEFT)
    app._line_group_hint.pack(fill=tk.X, padx=10, pady=(0, 4))
