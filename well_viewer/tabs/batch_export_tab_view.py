"""Inline Batch Export tab content builders (Qt port)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from well_viewer.ui_helpers import btn_primary
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
    host_layout = host.layout()
    panels = state["panels"]
    if mode not in panels:
        if mode == "line":
            panel = BatchExportPanel(app, host, use_sidebar_groups=False)
        elif mode == "bar":
            panel = BarBatchExportPanel(app, host, use_sidebar_groups=False)
        elif mode == "scatter_cells":
            panel = ScatterBatchExportPanel(
                app, host, scatter_mode="cells", use_sidebar_groups=False,
            )
        else:
            panel = ScatterBatchExportPanel(
                app, host, scatter_mode="aggregate", use_sidebar_groups=False,
            )
        host_layout.addWidget(panel)
        panels[mode] = panel
    for key, panel in panels.items():
        panel.setVisible(key == mode)

    state["mode"] = mode


def build_batch_export_tab(app, parent: QWidget) -> None:
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(12, 12, 12, 12)

    title = QLabel("Batch Export", parent)
    title.setProperty("role", "section")
    layout.addWidget(title)

    subtitle = QLabel(
        "Configure and run inline line/bar batch export workflows from this tab.",
        parent,
    )
    subtitle.setObjectName("Muted")
    subtitle.setWordWrap(True)
    layout.addWidget(subtitle)

    switch_row = QWidget(parent)
    sr = QHBoxLayout(switch_row)
    sr.setContentsMargins(0, 0, 0, 8)
    sr.addWidget(btn_primary(switch_row, "Line Batch Builder",
                             lambda: app._open_batch_export()))
    sr.addWidget(btn_primary(switch_row, "Bar Batch Builder",
                             lambda: app._open_bar_batch_export()))
    sr.addWidget(btn_primary(switch_row, "Scatter Cells Batch",
                             lambda: app._open_scatter_cells_batch_export()))
    sr.addWidget(btn_primary(switch_row, "Scatter Aggregate Batch",
                             lambda: app._open_scatter_agg_batch_export()))
    sr.addStretch(1)
    layout.addWidget(switch_row)

    host = QWidget(parent)
    QVBoxLayout(host)
    layout.addWidget(host, 1)

    app._batch_export_inline_state = {"host": host, "panels": {}, "mode": "line"}
    app._batch_export_set_mode = lambda mode="line": _show_batch_mode(app, mode)
    app._batch_export_set_mode("line")
