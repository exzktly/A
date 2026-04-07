"""Batch Export tab builder extracted from centre_view."""

from __future__ import annotations

import tkinter as tk

from well_viewer.runtime_app import (
    BG_APP,
    FM_BOLD,
    FM_TINY,
    TXT_MUT,
    TXT_SEC,
)
from well_viewer.tabs import _make_action_button


def build_batch_export_tab(app, parent: tk.Frame) -> None:
    """Fill *parent* with the Batch Export action buttons.

    All 5 buttons delegate to existing ``app._*`` methods; no figure
    is created in this tab.
    """
    batch_wrap = tk.Frame(parent, bg=BG_APP, padx=16, pady=16)
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
