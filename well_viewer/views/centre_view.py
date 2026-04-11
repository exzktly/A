"""Centre notebook/tab builder extracted from runtime_app.

``build_centre`` is the single entry point.  It creates each tab frame,
registers it with the custom notebook, and delegates content-building to the
relevant module:

  Plot tabs (have figures):
    well_viewer/tabs/line_graphs_tab_view.py
    well_viewer/tabs/bar_plots_tab_view.py
    well_viewer/tabs/scatter_cells_tab_view.py
    well_viewer/tabs/scatter_agg_tab_view.py

  Workflow tab (buttons only):
    well_viewer/tabs/batch_export_tab_view.py

  Tabs that stay inline (class instantiation or single method call):
    Movie Montage      → app._build_right_panel / app._build_preview_picker
    Review CSV         → app._build_review_csv_tab
    smFISH             → well_viewer/smfish_tab.py  (SmfishTab)
    Statistics         → app._build_stats_tab / app._build_stats_group_editor
    Cell Gating        → well_viewer/cell_gating_tab.py  (CellGatingTab)
    Sample Definitions → app._build_groups_centre / app._build_replicate_panel
                         / app._build_bar_group_panel
"""

import tkinter as tk
from tkinter import ttk

from well_viewer.runtime_app import BG_APP, BG_SIDE, BORDER, FM_TINY, TXT_MUT, TXT_PRI


class CustomNotebook(tk.Frame):
    """Drop-in replacement for ttk.Notebook with custom tab bar.

    Features:
    - Custom header with tab buttons and visual separators
    - Full control over tab appearance and grouping
    - Maintains ttk.Notebook compatibility interface
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Header with tab buttons
        self.header = tk.Frame(self, bg=BG_SIDE, height=35)
        self.header.pack(fill=tk.X, padx=0, pady=0)
        self.header.pack_propagate(False)

        # Content area with single visible frame at a time
        self.content = tk.Frame(self, bg=BG_APP)
        self.content.pack(fill=tk.BOTH, expand=True)

        self._tabs = {}              # {text: frame}
        self._tab_buttons = {}       # {text: label widget}
        self._current_text = None
        self._callbacks = []

    def add(self, frame, text):
        """Add a tab with the given text and frame (mimics ttk.Notebook.add)"""
        self._tabs[text] = frame

        # Create tab button in header
        btn = tk.Label(
            self.header,
            text=text,
            font=(FM_TINY[0], FM_TINY[1]),
            fg=TXT_PRI,
            bg=BG_SIDE,
            padx=12,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
        )
        btn.pack(side=tk.LEFT, padx=0, pady=0)
        btn.bind("<Button-1>", lambda e: self.select_by_text(text))
        self._tab_buttons[text] = btn

        # Select first tab automatically
        if self._current_text is None:
            self.select_by_text(text)

    def add_separator(self):
        """Add a thin vertical separator in the tab bar"""
        sep = tk.Frame(self.header, bg=BORDER, width=1, height=25)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=5)

    def select_by_text(self, text):
        """Show the tab with the given text"""
        if text not in self._tabs:
            return

        # Hide current tab
        if self._current_text and self._current_text in self._tabs:
            self._tabs[self._current_text].pack_forget()
            # Unhighlight old button
            old_btn = self._tab_buttons[self._current_text]
            old_btn.configure(bg=BG_SIDE, relief=tk.FLAT)

        # Show new tab (pack it into the content area)
        self._tabs[text].pack(in_=self.content, fill=tk.BOTH, expand=True)
        self._current_text = text

        # Highlight new button
        new_btn = self._tab_buttons[text]
        new_btn.configure(bg=BG_APP, relief=tk.SUNKEN)

        # Trigger callbacks
        for cb in self._callbacks:
            cb(text)

    def select(self):
        """Return index of currently selected tab (mimics ttk.Notebook)"""
        if self._current_text is None:
            return 0
        tab_list = list(self._tabs.keys())
        try:
            return tab_list.index(self._current_text)
        except ValueError:
            return 0

    def tab(self, index, key):
        """Return tab info (mimics ttk.Notebook.tab)"""
        if key == "text":
            tab_list = list(self._tabs.keys())
            if 0 <= index < len(tab_list):
                return tab_list[index]
        return None

    def bind(self, event, callback):
        """Bind to tab change events (mimics ttk.Notebook)"""
        if event == "<<NotebookTabChanged>>":
            # Store callback to call when tab changes
            self._callbacks.append(lambda text: callback(None))
        else:
            super().bind(event, callback)


def build_centre(app, parent: tk.Frame) -> None:
    from well_viewer.smfish_tab import SmfishTab
    from well_viewer.cell_gating_tab import CellGatingTab
    from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
    from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
    from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
    from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab
    from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab

    # Create custom notebook (replaces ttk.Notebook)
    app._notebook = CustomNotebook(parent)
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

    # ── Tab 4: Scatter Plot: Cells ────────────────────────────────────────
    tab_scatter = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter, text="Scatter Plot: Cells")
    build_scatter_cells_tab(app, tab_scatter)

    # ── Tab 5: Scatter Plot: Aggregate ────────────────────────────────────
    tab_scatter_agg = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_scatter_agg, text="Scatter Plot: Aggregate")
    build_scatter_agg_tab(app, tab_scatter_agg)

    # Visual separator between left and middle tab groups
    app._notebook.add_separator()

    # ── Middle group: Movie Montage / Statistics / smFISH ──────────────────
    tab_preview = tk.Frame(app._notebook, bg=BG_SIDE)
    app._notebook.add(tab_preview, text="Movie Montage")
    app._build_right_panel(tab_preview)
    app._build_preview_picker(app._sidebar_preview_frame)

    tab_stats = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_stats, text="Statistics")
    app._build_stats_tab(tab_stats)
    app._build_stats_group_editor(app._sidebar_stats_frame)

    tab_smfish = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_smfish, text="smFISH")
    app._smfish_tab = SmfishTab(tab_smfish, app=app)
    app._smfish_tab.pack(fill=tk.BOTH, expand=True)

    # Visual separator between middle and right tab groups
    app._notebook.add_separator()

    # ── Right group: workflow/data tabs ────────────────────────────────────
    tab_review_csv = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_review_csv, text="Review CSV")
    app._build_review_csv_tab(tab_review_csv)

    tab_cell_gating = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_cell_gating, text="Cell Gating")
    app._cell_gating_tab = CellGatingTab(tab_cell_gating, app)
    app._cell_gating_tab.pack(fill=tk.BOTH, expand=True)

    tab_batch = tk.Frame(app._notebook, bg=BG_APP)
    app._notebook.add(tab_batch, text="Batch Export")
    build_batch_export_tab(app, tab_batch)

    app._notebook.add(tab_groups, text="Sample Definitions")
