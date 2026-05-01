"""Unified Scatter Plot tab — merges the per-cell and per-well aggregate views.

A segmented button at the top of the tab toggles between two pages held in
a ``QStackedWidget``:

- ``Per-cell points`` — one matplotlib point per gated cell (intensity X
  vs intensity Y at a single timepoint).
- ``Per-well aggregate`` — one point per replicate or well (aggregated
  statistic on each axis, multi-timepoint).

Each page is built by the original ``build_scatter_cells_tab`` /
``build_scatter_agg_tab`` so the two rendering pipelines, controllers,
and per-mode controls stay separate. Only the active page is visible, so
controls that don't apply to the other mode aren't shown.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab
from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab


_MODE_CELLS = "cells"
_MODE_AGG = "aggregate"


_SEGMENTED_QSS = (
    "QPushButton#ScatterModeBtnLeft, QPushButton#ScatterModeBtnRight { "
    "background: #334155; "
    "border: 1px solid #64748B; "
    "color: #E2E8F0; "
    "padding: 4px 14px; font-size: 12px; font-weight: 500; "
    "} "
    "QPushButton#ScatterModeBtnLeft:checked, "
    "QPushButton#ScatterModeBtnRight:checked { "
    "background: #3B82F6; color: white; border-color: #2563EB; "
    "} "
    "QPushButton#ScatterModeBtnLeft:hover:!checked, "
    "QPushButton#ScatterModeBtnRight:hover:!checked { "
    "background: #475569; "
    "} "
    "QPushButton#ScatterModeBtnLeft { "
    "border-top-right-radius: 0; border-bottom-right-radius: 0; border-right: none; "
    "} "
    "QPushButton#ScatterModeBtnRight { "
    "border-top-left-radius: 0; border-bottom-left-radius: 0; "
    "}"
)


def build_scatter_tab(app, parent: QWidget) -> None:
    """Construct the unified Scatter Plot tab inside *parent*."""
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # ── Mode bar (segmented button toggle) ──────────────────────────────────
    mode_bar = QWidget(parent)
    mode_bar.setObjectName("TabCtrl")
    mode_bar.setStyleSheet(_SEGMENTED_QSS)
    mb = QHBoxLayout(mode_bar)
    mb.setContentsMargins(10, 6, 10, 6)
    mb.setSpacing(0)

    cells_btn = QPushButton("Per-cell points", mode_bar)
    cells_btn.setObjectName("ScatterModeBtnLeft")
    cells_btn.setCheckable(True)
    mb.addWidget(cells_btn)

    agg_btn = QPushButton("Per-well aggregate", mode_bar)
    agg_btn.setObjectName("ScatterModeBtnRight")
    agg_btn.setCheckable(True)
    mb.addWidget(agg_btn)

    mb.addStretch(1)
    layout.addWidget(mode_bar)

    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    # ── Stacked page area: each mode keeps its own builder unchanged ───────
    stack = QStackedWidget(parent)
    layout.addWidget(stack, 1)

    cells_page = QWidget(stack)
    QVBoxLayout(cells_page).setContentsMargins(0, 0, 0, 0)
    build_scatter_cells_tab(app, cells_page)
    stack.addWidget(cells_page)

    agg_page = QWidget(stack)
    QVBoxLayout(agg_page).setContentsMargins(0, 0, 0, 0)
    build_scatter_agg_tab(app, agg_page)
    stack.addWidget(agg_page)

    # ── Toggle wiring ──────────────────────────────────────────────────────
    group = QButtonGroup(parent)
    group.setExclusive(True)
    group.addButton(cells_btn, 0)
    group.addButton(agg_btn, 1)
    cells_btn.setChecked(True)
    stack.setCurrentIndex(0)
    app._scatter_mode = _MODE_CELLS
    app._scatter_mode_buttons = (cells_btn, agg_btn)
    app._scatter_mode_stack = stack

    def _set_mode(mode: str) -> None:
        if mode == _MODE_AGG:
            stack.setCurrentIndex(1)
            app._scatter_mode = _MODE_AGG
            if not agg_btn.isChecked():
                agg_btn.setChecked(True)
            try:
                app._update_scatter_menus()
            except Exception:
                pass
            try:
                app._redraw_scatter_agg()
            except Exception:
                pass
        else:
            stack.setCurrentIndex(0)
            app._scatter_mode = _MODE_CELLS
            if not cells_btn.isChecked():
                cells_btn.setChecked(True)
            try:
                app._update_scatter_menus()
            except Exception:
                pass
            try:
                app._redraw_scatter()
            except Exception:
                pass
    app._scatter_set_mode = _set_mode

    cells_btn.clicked.connect(lambda: _set_mode(_MODE_CELLS))
    agg_btn.clicked.connect(lambda: _set_mode(_MODE_AGG))


def scatter_active_mode(app) -> str:
    """Return ``"cells"`` or ``"aggregate"``; defaults to ``"cells"``."""
    return getattr(app, "_scatter_mode", _MODE_CELLS) or _MODE_CELLS


def scatter_redraw_active(app) -> None:
    """Redraw whichever scatter mode is currently visible."""
    if scatter_active_mode(app) == _MODE_AGG:
        if hasattr(app, "_redraw_scatter_agg"):
            app._redraw_scatter_agg()
    else:
        if hasattr(app, "_redraw_scatter"):
            app._redraw_scatter()
