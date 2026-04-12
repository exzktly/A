"""Inline Batch Export tab content builders."""

from __future__ import annotations

import tkinter as tk

from well_viewer.runtime_app import BG_APP, FM_BOLD, FM_TINY, TXT_MUT, TXT_SEC
from well_viewer.tabs import _make_action_button
from well_viewer.batch_export_dialog import (
    BatchExportPanel,
    BarBatchExportPanel,
    ScatterBatchExportPanel,
)


def _show_batch_mode(app, mode: str) -> None:
    state = getattr(app, "_batch_export_inline_state", None)
    if not state:
        return

    if mode not in ("line", "bar", "scatter_cells", "scatter_agg"):
        mode = "line"

    host = state["host"]
    panels = state["panels"]
    if mode not in panels:
        panel_cls = {
            "line": BatchExportPanel,
            "bar": BarBatchExportPanel,
            "scatter_cells": lambda app, host, use_sidebar_groups=False: ScatterBatchExportPanel(
                app,
                host,
                scatter_mode="cells",
                use_sidebar_groups=use_sidebar_groups,
            ),
            "scatter_agg": lambda app, host, use_sidebar_groups=False: ScatterBatchExportPanel(
                app,
                host,
                scatter_mode="aggregate",
                use_sidebar_groups=use_sidebar_groups,
            ),
        }[mode]
        panel = panel_cls(app, host, use_sidebar_groups=False)
        panel.pack(fill=tk.BOTH, expand=True)
        panels[mode] = panel
    for key, panel in panels.items():
        if key == mode:
            panel.pack(fill=tk.BOTH, expand=True)
        else:
            panel.pack_forget()

    state["mode"] = mode


def build_batch_export_tab(app, parent: tk.Frame) -> None:
    """Render inline line/bar batch export builders inside the tab body."""
    wrap = tk.Frame(parent, bg=BG_APP, padx=12, pady=12)
    wrap.pack(fill=tk.BOTH, expand=True)

    tk.Label(wrap, text="Batch Export", font=FM_BOLD, fg=TXT_SEC, bg=BG_APP).pack(anchor="w")
    tk.Label(
        wrap,
        text="Configure and run inline line/bar batch export workflows from this tab.",
        font=FM_TINY,
        fg=TXT_MUT,
        bg=BG_APP,
    ).pack(anchor="w", pady=(2, 10))

    switch_row = tk.Frame(wrap, bg=BG_APP)
    switch_row.pack(fill=tk.X, pady=(0, 8))
    _make_action_button(
        switch_row,
        text="Line Batch Builder",
        command=lambda: app._open_batch_export(),
        style="ActionIndigo.TButton",
    ).pack(side=tk.LEFT, padx=(0, 6))
    _make_action_button(
        switch_row,
        text="Bar Batch Builder",
        command=lambda: app._open_bar_batch_export(),
        style="ActionIndigo.TButton",
    ).pack(side=tk.LEFT)
    _make_action_button(
        switch_row,
        text="Scatter Cells Batch",
        command=lambda: app._open_scatter_cells_batch_export(),
        style="ActionIndigo.TButton",
    ).pack(side=tk.LEFT, padx=(6, 0))
    _make_action_button(
        switch_row,
        text="Scatter Aggregate Batch",
        command=lambda: app._open_scatter_agg_batch_export(),
        style="ActionIndigo.TButton",
    ).pack(side=tk.LEFT, padx=(6, 0))

    host = tk.Frame(wrap, bg=BG_APP)
    host.pack(fill=tk.BOTH, expand=True)

    app._batch_export_inline_state = {"host": host, "panels": {}, "mode": "line"}
    app._batch_export_set_mode = lambda mode="line": _show_batch_mode(app, mode)
    app._batch_export_set_mode("line")
