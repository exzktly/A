"""Centre notebook/tab builder (Qt port).

``build_centre`` is the entry point. Replaces the tk-based ``CustomNotebook``
hand-drawn tab chrome with a standard ``QTabWidget`` styled via QSS.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget


def build_centre(app, parent: QWidget) -> None:
    from well_viewer.cell_gating_tab import CellGatingTab
    from well_viewer.smfish_tab import SmfishTab
    from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
    from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
    from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
    from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab
    from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    app._notebook = QTabWidget(parent)
    app._notebook.setObjectName("CentreTabs")
    app._notebook.setMovable(False)
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

    # Line Graphs
    tab_line = _new_tab("Line Graphs")
    build_line_graphs_tab(app, tab_line)

    # Sample Definitions centre built now, tab added last
    tab_groups = QWidget(app._notebook)
    QVBoxLayout(tab_groups).setContentsMargins(0, 0, 0, 0)
    app._build_groups_centre(tab_groups)
    app._build_replicate_panel(app._sidebar_sample_frame)
    app._build_bar_group_panel(app._sidebar_groups_frame)

    # Bar Plots
    tab_bar = _new_tab("Bar Plots")
    build_bar_plots_tab(app, tab_bar)

    # Scatter: Cells
    tab_scatter = _new_tab("Scatter Plot: Cells")
    build_scatter_cells_tab(app, tab_scatter)

    # Scatter: Aggregate
    tab_scatter_agg = _new_tab("Scatter Plot: Aggregate")
    build_scatter_agg_tab(app, tab_scatter_agg)

    # Movie Montage
    tab_preview = _new_tab("Movie Montage")
    app._build_right_panel(tab_preview)
    app._build_preview_picker(app._sidebar_preview_frame)

    # Review Image
    tab_review_image = _new_tab("Review Image")
    app._build_review_image_panel(tab_review_image)

    # Statistics
    tab_stats = _new_tab("Statistics")
    app._build_stats_tab(tab_stats)
    app._build_stats_group_editor(app._sidebar_stats_frame)

    # smFISH
    tab_smfish = _new_tab("smFISH")
    app._smfish_tab = SmfishTab(tab_smfish, app=app)
    tab_smfish.layout().addWidget(app._smfish_tab)

    # Review CSV
    tab_review_csv = _new_tab("Review CSV")
    app._build_review_csv_tab(tab_review_csv)

    # Cell Gating
    tab_cell_gating = _new_tab("Cell Gating")
    app._cell_gating_tab = CellGatingTab(tab_cell_gating, app)
    tab_cell_gating.layout().addWidget(app._cell_gating_tab)

    # Batch Export
    tab_batch = _new_tab("Batch Export")
    app._batch_export_tab_frame = tab_batch
    build_batch_export_tab(app, tab_batch)

    # Sample Definitions (added last so it appears at the end)
    app._notebook.addTab(tab_groups, "Sample Definitions")

    app._notebook.setCurrentIndex(0)

    # Wire the tab-change handler last so it never fires during construction
    # (the first addTab above would otherwise emit currentChanged(0) before
    # the Line-Graphs axes exist).
    app._notebook.currentChanged.connect(lambda _i: app._on_tab_change(None))
