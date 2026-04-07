"""Centre notebook/tab builder extracted from runtime_app.

``build_centre`` is the single entry point.  It creates each tab frame,
registers it with the ttk.Notebook, and delegates content-building to the
relevant module:

  Plot tabs (have figures):
    well_viewer/tabs/line_graphs_tab_view.py
    well_viewer/tabs/bar_plots_tab_view.py
    well_viewer/tabs/scatter_cells_tab_view.py
    well_viewer/tabs/scatter_agg_tab_view.py

  Workflow tab (buttons only):
    well_viewer/tabs/batch_export_tab_view.py

  Tabs that stay inline (class instantiation or single method call):
    Preview            → app._build_right_panel / app._build_preview_picker
    Review CSV         → app._build_review_csv_tab
    smFISH             → SmfishTab class
    Statistics         → app._build_stats_tab / app._build_stats_group_editor
    Cell Gating        → CellGatingTab class
    Sample Definitions → app._build_groups_centre / app._build_replicate_panel
                         / app._build_bar_group_panel
"""

import tkinter as tk
from tkinter import ttk

from well_viewer.runtime_app import BG_APP, BG_SIDE


def build_centre(app, parent: tk.Frame) -> None:
    from smfish_tab import SmfishTab
    from well_viewer.runtime_app import CellGatingTab
    from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
    from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
    from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
    from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab
    from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab

    app._notebook = ttk.Notebook(parent)
    app._notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
    app._notebook.bind("<<NotebookTabChanged>>", app._on_tab_change)

    # ── Tab 1: Line Graphs ────────────────────────────────────────────────
    tab_line = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_line, text="Line Graphs")
    build_line_graphs_tab(app, tab_line)

    # ── Tab 2: Sample Definitions (frame created now, added last) ─────────
    # Frame must exist early so _build_bar_group_panel and sidebar frames
    # that reference it can be built; the notebook.add call is deferred so
    # the tab appears at the end of the tab bar.
    tab_groups = tk.Frame(app._notebook, bg=BG_APP)
    app._build_groups_centre(tab_groups)
    app._build_replicate_panel(app._sidebar_sample_frame)
    app._build_bar_group_panel(app._sidebar_groups_frame)

    # ── Tab 3: Bar Plots ──────────────────────────────────────────────────
    tab_bar = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_bar, text="Bar Plots")
    build_bar_plots_tab(app, tab_bar)

    # ── Tab 4: Preview ────────────────────────────────────────────────────
    tab_preview = tk.Frame(app._notebook, bg=BG_SIDE)
    app._notebook.add(tab_preview, text="Preview")
    app._build_right_panel(tab_preview)
    app._build_preview_picker(app._sidebar_preview_frame)

    # ── Tab 5: Review CSV ─────────────────────────────────────────────────
    tab_review_csv = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_review_csv, text="Review CSV")
    app._build_review_csv_tab(tab_review_csv)

    # ── Tab 6: smFISH ─────────────────────────────────────────────────────
    tab_smfish = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_smfish, text="smFISH")
    app._smfish_tab = SmfishTab(tab_smfish, app=app)
    app._smfish_tab.pack(fill=tk.BOTH, expand=True)

    # ── Tab 7: Batch Export ───────────────────────────────────────────────
    tab_batch = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_batch, text="Batch Export")
    build_batch_export_tab(app, tab_batch)

    # ── Tab 8: Statistics ─────────────────────────────────────────────────
    tab_stats = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_stats, text="Statistics")
    app._build_stats_tab(tab_stats)
    app._build_stats_group_editor(app._sidebar_stats_frame)

    # ── Tab 9: Scatter Plot: Cells ────────────────────────────────────────
    tab_scatter = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter, text="Scatter Plot: Cells")
    build_scatter_cells_tab(app, tab_scatter)

    # ── Tab 10: Scatter Plot: Aggregate ───────────────────────────────────
    tab_scatter_agg = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter_agg, text="Scatter Plot: Aggregate")
    build_scatter_agg_tab(app, tab_scatter_agg)

    # ── Tab 11: Cell Gating ───────────────────────────────────────────────
    tab_cell_gating = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_cell_gating, text="Cell Gating")
    app._cell_gating_tab = CellGatingTab(tab_cell_gating, app)
    app._cell_gating_tab.pack(fill=tk.BOTH, expand=True)

    # ── Tab 12: Sample Definitions (deferred add) ─────────────────────────
    app._notebook.add(tab_groups, text="Sample Definitions")
