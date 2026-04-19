"""Review CSV tab builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_review_csv_tab(app, parent: tk.Frame) -> None:
    """Build the Review CSV tab content."""
    from well_viewer.runtime_app import (
        BG_APP, BG_SIDE, FM_BOLD, FM_TINY, TXT_PRI, TXT_MUT,
    )

    wrap = tk.Frame(parent, bg=BG_APP, padx=10, pady=10)
    wrap.pack(fill=tk.BOTH, expand=True)

    ctrl = tk.Frame(wrap, bg=BG_SIDE, padx=8, pady=6)
    ctrl.pack(fill=tk.X)
    tk.Label(ctrl, text="Well:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT)
    app._review_well_var = tk.StringVar(value="(select one well)")
    tk.Label(ctrl, textvariable=app._review_well_var, font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT, padx=(6, 14))

    tk.Label(ctrl, text="FOV:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT)
    app._review_fov_var = tk.StringVar(value="")
    app._review_fov_cb = ttk.Combobox(ctrl, textvariable=app._review_fov_var, state="readonly", width=12)
    app._review_fov_cb.pack(side=tk.LEFT, padx=(6, 12))
    app._review_fov_cb.bind("<<ComboboxSelected>>", lambda _e: app._refresh_review_csv_rows())

    tk.Label(ctrl, text="Timepoint:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT)
    app._review_tp_var = tk.StringVar(value="")
    app._review_tp_cb = ttk.Combobox(ctrl, textvariable=app._review_tp_var, state="readonly", width=14)
    app._review_tp_cb.pack(side=tk.LEFT, padx=(6, 12))
    app._review_tp_cb.bind("<<ComboboxSelected>>", lambda _e: app._refresh_review_csv_rows())
    ttk.Button(ctrl, text="Refresh", command=app._refresh_review_csv).pack(side=tk.LEFT)

    table_wrap = tk.Frame(wrap, bg=BG_APP)
    table_wrap.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    app._review_csv_table = ttk.Treeview(table_wrap, show="headings")
    ys = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=app._review_csv_table.yview)
    xs = ttk.Scrollbar(table_wrap, orient=tk.HORIZONTAL, command=app._review_csv_table.xview)
    app._review_csv_table.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    app._review_csv_table.bind("<Double-1>", app._on_review_csv_row_double_click)
    app._review_csv_table.grid(row=0, column=0, sticky="nsew")
    ys.grid(row=0, column=1, sticky="ns")
    xs.grid(row=1, column=0, sticky="ew")
    table_wrap.rowconfigure(0, weight=1)
    table_wrap.columnconfigure(0, weight=1)
    app._review_csv_msg = tk.StringVar(value="Select a single well to inspect CSV rows.")
    tk.Label(wrap, textvariable=app._review_csv_msg, font=FM_TINY, fg=TXT_MUT, bg=BG_APP, anchor="w").pack(fill=tk.X, pady=(6, 0))
