"""Replicate panel builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_replicate_panel(app, parent: tk.Frame) -> None:
    """Left panel: define named ReplicateSets from the global well pool."""
    from well_viewer.runtime_app import (
        BORDER, BG_SIDE, FM_BOLD, TXT_MUT, FM_TINY, TXT_PRI, BG_APP,
        _btn_primary, _btn_secondary, build_plate_grid, _bind_drag,
        make_scrollable_canvas,
    )

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

    hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="REPLICATE SETS", font=FM_BOLD,
             fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
    _btn_primary(hdr, "+ Add", app._rep_add).pack(side=tk.RIGHT)
    _btn_secondary(hdr, "Clear All", app._rep_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

    # Second row: Quick Replicates dropdowns
    hdr2r = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
    hdr2r.pack(fill=tk.X)

    # Pair direction dropdown
    tk.Label(hdr2r, text="Pair:", font=FM_TINY, fg=TXT_PRI,
             bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
    app._rep_quick_pair_dir_var = tk.StringVar(value="Rows (A01+A02)")
    pair_dir_cb = ttk.Combobox(
        hdr2r,
        textvariable=app._rep_quick_pair_dir_var,
        values=["Rows (A01+A02)", "Columns (A01+B01)"],
        state="readonly",
        width=18)
    pair_dir_cb.pack(side=tk.LEFT, padx=(0, 8))

    # Iteration order dropdown
    tk.Label(hdr2r, text="Order:", font=FM_TINY, fg=TXT_PRI,
             bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
    app._rep_quick_iter_order_var = tk.StringVar(value="Across rows")
    iter_order_cb = ttk.Combobox(
        hdr2r,
        textvariable=app._rep_quick_iter_order_var,
        values=["Across rows", "Down columns"],
        state="readonly",
        width=14)
    iter_order_cb.pack(side=tk.LEFT, padx=(0, 4))

    # Apply button on separate row below dropdowns
    btn_row = tk.Frame(parent, bg=BG_SIDE, pady=2, padx=8)
    btn_row.pack(fill=tk.X)
    _btn_primary(btn_row, "Apply Quick Replicates", app._rep_quick_pairs_from_dropdowns).pack(side=tk.LEFT)

    tk.Label(parent,
             text="Select a set below, then drag wells on the map to add/remove.",
             font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
             wraplength=580, justify=tk.LEFT).pack(
             fill=tk.X, padx=8, pady=(4, 2))

    # Plate map — shows all rep-set colours; drag edits the selected set
    rep_map_outer = tk.Frame(parent, bg=BG_SIDE)
    rep_map_outer.pack(fill=tk.X, padx=4)
    app._rep_map_btns: dict = {}
    build_plate_grid(rep_map_outer, app._rep_map_btns)
    _bind_drag(rep_map_outer, app._rep_map_btns,
               app._rep_map_press, app._rep_map_drag, app._rep_map_release)

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(4, 0))

    sf = tk.Frame(parent, bg=BG_APP)
    sf.pack(fill=tk.BOTH, expand=True)
    app._rep_canvas, app._rep_inner = make_scrollable_canvas(sf, bg=BG_APP)
