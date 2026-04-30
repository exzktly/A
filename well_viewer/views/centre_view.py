"""Centre notebook/tab builder (Qt port).

``build_centre`` is the entry point. Replaces the tk-based ``CustomNotebook``
hand-drawn tab chrome with a standard ``QTabWidget`` styled via QSS.

Tabs are built lazily: only the initially active "Line Graphs" tab and the
sidebar panels that other code touches at startup are constructed
eagerly. The remaining tab bodies build on a per-event-loop-tick timer so
the window paints quickly and stays responsive while heavy widget trees
(matplotlib canvases, image grids, etc.) populate in the background. If
the user clicks a tab whose body hasn't been built yet, the builder for
that tab is run inline on the tab-switch event.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget


_logger = logging.getLogger("well_viewer.centre_view")


def build_centre(app, parent: QWidget) -> None:
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    app._notebook = QTabWidget(parent)
    app._notebook.setObjectName("CentreTabs")
    app._notebook.setMovable(False)
    app._notebook.setUsesScrollButtons(True)
    app._notebook.setElideMode(Qt.ElideNone)
    tabbar = app._notebook.tabBar()
    tabbar.setUsesScrollButtons(True)
    tabbar.setExpanding(False)
    tabbar.setElideMode(Qt.ElideNone)
    layout.addWidget(app._notebook, 1)

    def _select_by_text(title: str, _nb=app._notebook) -> None:
        for i in range(_nb.count()):
            if _nb.tabText(i) == title:
                _nb.setCurrentIndex(i)
                return
    app._notebook.select_by_text = _select_by_text

    def _new_tab(title: str) -> QWidget:
        frame = QWidget(app._notebook)
        QVBoxLayout(frame).setContentsMargins(0, 0, 0, 0)
        app._notebook.addTab(frame, title)
        return frame

    # Map tab title -> deferred builder. Populated below; drained after the
    # window paints. The tab-change handler also calls into this map so a
    # user who clicks an un-built tab forces its builder to run inline.
    pending: Dict[str, Callable[[], None]] = {}
    app._centre_pending_builders = pending

    # ── Line Graphs (initial active tab — build eagerly) ───────────────────
    from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
    tab_line = _new_tab("Line Graphs")
    build_line_graphs_tab(app, tab_line)

    # Sample Definitions tab is added LAST (at the right end), but its
    # sidebar panels are referenced by data-load and tab-switch logic, so
    # construct the sidebars eagerly. The tab body itself is deferred.
    tab_groups = QWidget(app._notebook)
    QVBoxLayout(tab_groups).setContentsMargins(0, 0, 0, 0)
    app._build_replicate_panel(app._sidebar_sample_frame)
    app._build_bar_group_panel(app._sidebar_groups_frame)

    def _build_groups_centre_body() -> None:
        app._build_groups_centre(tab_groups)
    pending["Sample Definitions"] = _build_groups_centre_body

    # ── Bar Plots ──────────────────────────────────────────────────────────
    tab_bar = _new_tab("Bar Plots")
    def _build_bar() -> None:
        from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
        build_bar_plots_tab(app, tab_bar)
    pending["Bar Plots"] = _build_bar

    # ── Scatter Plot: Cells ────────────────────────────────────────────────
    tab_scatter = _new_tab("Scatter Plot: Cells")
    def _build_scatter() -> None:
        from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab
        build_scatter_cells_tab(app, tab_scatter)
    pending["Scatter Plot: Cells"] = _build_scatter

    # ── Scatter Plot: Aggregate ────────────────────────────────────────────
    tab_scatter_agg = _new_tab("Scatter Plot: Aggregate")
    def _build_scatter_agg() -> None:
        from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab
        build_scatter_agg_tab(app, tab_scatter_agg)
    pending["Scatter Plot: Aggregate"] = _build_scatter_agg

    # ── Distribution ───────────────────────────────────────────────────────
    tab_distribution = _new_tab("Distribution")
    def _build_distribution() -> None:
        from well_viewer.tabs.distribution_tab_view import build_distribution_tab
        build_distribution_tab(app, tab_distribution)
    pending["Distribution"] = _build_distribution

    # ── Heat Map ───────────────────────────────────────────────────────────
    tab_heatmap = _new_tab("Heat Map")
    def _build_heatmap() -> None:
        from well_viewer.tabs.heatmap_tab_view import build_heatmap_tab
        build_heatmap_tab(app, tab_heatmap)
    pending["Heat Map"] = _build_heatmap

    # ── Movie Montage ──────────────────────────────────────────────────────
    tab_preview = _new_tab("Movie Montage")
    # The preview picker sidebar is referenced by tab-switch and data-load
    # logic, so build it eagerly. Tab body defers.
    app._build_preview_picker(app._sidebar_preview_frame)
    def _build_preview_body() -> None:
        app._build_right_panel(tab_preview)
    pending["Movie Montage"] = _build_preview_body

    # ── Image Table ────────────────────────────────────────────────────────
    tab_image_table = _new_tab("Image Table")
    def _build_image_table() -> None:
        from well_viewer.tabs.image_table_tab_view import build_image_table_tab
        from well_viewer.views.image_table_picker_view import build_image_table_picker
        build_image_table_tab(app, tab_image_table)
        build_image_table_picker(app, app._sidebar_image_table_frame)
    pending["Image Table"] = _build_image_table

    # ── Review Image ───────────────────────────────────────────────────────
    tab_review_image = _new_tab("Review Image")
    def _build_review_image() -> None:
        app._build_review_image_panel(tab_review_image)
    pending["Review Image"] = _build_review_image

    # ── Statistics ─────────────────────────────────────────────────────────
    tab_stats = _new_tab("Statistics")
    def _build_stats() -> None:
        app._build_stats_tab(tab_stats)
        app._build_stats_group_editor(app._sidebar_stats_frame)
    pending["Statistics"] = _build_stats

    # ── smFISH ─────────────────────────────────────────────────────────────
    tab_smfish = _new_tab("smFISH")
    def _build_smfish() -> None:
        from well_viewer.smfish_tab import SmfishTab
        app._smfish_tab = SmfishTab(tab_smfish, app=app)
        tab_smfish.layout().addWidget(app._smfish_tab)
    pending["smFISH"] = _build_smfish

    # ── Review CSV ─────────────────────────────────────────────────────────
    tab_review_csv = _new_tab("Review CSV")
    def _build_review_csv() -> None:
        app._build_review_csv_tab(tab_review_csv)
    pending["Review CSV"] = _build_review_csv

    # ── Cell Gating ────────────────────────────────────────────────────────
    tab_cell_gating = _new_tab("Cell Gating")
    def _build_cell_gating() -> None:
        from well_viewer.cell_gating_tab import CellGatingTab
        app._cell_gating_tab = CellGatingTab(tab_cell_gating, app)
        tab_cell_gating.layout().addWidget(app._cell_gating_tab)
        # If data is already loaded by the time Cell Gating finally builds
        # (deferred or user-clicked), sync so the tab reflects current state.
        if app._well_paths:
            try:
                app._cell_gating_tab._load_cell_areas()
                app._load_gating_from_pipeline_info()
                app._cell_gating_tab._load_threshold_frac_on()
            except Exception:
                _logger.exception("Cell Gating post-build sync failed")
    pending["Cell Gating"] = _build_cell_gating

    # ── Batch Export ───────────────────────────────────────────────────────
    tab_batch = _new_tab("Batch Export")
    app._batch_export_tab_frame = tab_batch
    def _build_batch_export() -> None:
        from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
        build_batch_export_tab(app, tab_batch)
    pending["Batch Export"] = _build_batch_export

    # Sample Definitions tab body added last so it appears at the right end
    # of the tab bar.
    app._notebook.addTab(tab_groups, "Sample Definitions")

    app._notebook.setCurrentIndex(0)

    def _build_pending(title: str) -> None:
        builder = pending.pop(title, None)
        if builder is None:
            return
        try:
            builder()
        except Exception:
            _logger.exception("Deferred build for %r failed", title)

    app._centre_build_pending = _build_pending

    def _on_tab_change(_i: int = 0) -> None:
        # Force-build the tab the user just switched to if it hasn't been
        # built yet, so click-before-build never shows a blank tab body.
        idx = app._notebook.currentIndex()
        title = app._notebook.tabText(idx) if idx >= 0 else ""
        if title in pending:
            _build_pending(title)
        app._on_tab_change(None)

    app._notebook.currentChanged.connect(_on_tab_change)

    # Drain pending builders one-per-event-loop-tick so the UI stays
    # responsive while heavy tabs (matplotlib canvases, image grids) build
    # in the background. By the time the user typically clicks anything
    # other than the initial tab, the corresponding builder will have run.
    def _drain() -> None:
        if not pending:
            return
        title = next(iter(pending))
        _build_pending(title)
        if pending:
            QTimer.singleShot(0, _drain)

    QTimer.singleShot(0, _drain)
