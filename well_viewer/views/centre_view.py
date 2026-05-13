"""Centre notebook/tab builder (Qt port).

``build_centre`` is the entry point. Replaces the tk-based ``CustomNotebook``
hand-drawn tab chrome with a standard ``QTabWidget`` styled via QSS.

Tabs are organised into three logical groups separated by a small visual
gap drawn by ``_GroupedTabBar``:

* **Analysis** — Plotting (sub-tabs: Line Graphs, Bar Plots, Scatter Plot,
  Distribution, Heat Map), smFISH, Statistics.
* **Images** — Image Table, Segmentation.
* **Data** — Review CSV, Sample Definitions, Batch Export.

Tabs are also built lazily: only the initially active "Plotting" tab
and the sidebar panels that other code touches at startup are constructed
eagerly. The remaining tab bodies build on a per-event-loop-tick timer so
the window paints quickly and stays responsive while heavy widget trees
(matplotlib canvases, image grids, etc.) populate in the background. If
the user clicks a tab whose body hasn't been built yet, the builder for
that tab is run inline on the tab-switch event.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Set

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QStyle, QStyleOptionTab, QStylePainter,
    QTabBar, QTabWidget, QVBoxLayout, QWidget,
)


_logger = logging.getLogger("well_viewer.centre_view")


class _GroupedTabBar(QTabBar):
    """Tab bar that reserves a header strip above the tabs for group labels.

    Tabs marked as group starts (via ``set_group_starts({index: label})``)
    are preceded by a small horizontal gap (``GAP_PX``) holding a vertical
    separator, and the group's uppercase label is painted in the
    ``HEADER_PX`` strip above the tabs, horizontally aligned with the first
    tab in that group.
    """

    GAP_PX = 4
    HEADER_PX = 0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._group_starts: Dict[int, str] = {}
        # Also track the first tab (index 0) so its group label paints above
        # it even though it is not preceded by a separator-gap.
        self._first_group_label: str = ""

    def set_group_starts(self, indices) -> None:
        if isinstance(indices, dict):
            new = {int(i): str(label or "") for i, label in indices.items() if int(i) > 0}
        else:
            new = {int(i): "" for i in indices if int(i) > 0}
        if new != self._group_starts:
            self._group_starts = new
            self.updateGeometry()
            self.update()

    def set_first_group_label(self, label: str) -> None:
        label = str(label or "")
        if label != self._first_group_label:
            self._first_group_label = label
            self.update()

    def tabSizeHint(self, index: int):  # noqa: N802 - Qt override
        size = super().tabSizeHint(index)
        if index in self._group_starts:
            size.setWidth(size.width() + self.GAP_PX)
        size.setHeight(size.height() + self.HEADER_PX)
        return size

    def minimumTabSizeHint(self, index: int):  # noqa: N802 - Qt override
        size = super().minimumTabSizeHint(index)
        if index in self._group_starts:
            size.setWidth(size.width() + self.GAP_PX)
        size.setHeight(size.height() + self.HEADER_PX)
        return size

    def paintEvent(self, event):  # noqa: N802 - Qt override
        half = self.GAP_PX // 2
        style_painter = QStylePainter(self)
        try:
            for i in range(self.count()):
                opt = QStyleOptionTab()
                self.initStyleOption(opt, i)
                opt.rect = opt.rect.adjusted(0, self.HEADER_PX, 0, 0)
                if i in self._group_starts:
                    # Centre the tab within its allocated area (which is GAP_PX
                    # wider than a normal tab) so its text appears centred.
                    opt.rect = opt.rect.adjusted(half, 0, -half, 0)
                style_painter.drawControl(QStyle.CE_TabBarTab, opt)
        finally:
            style_painter.end()

    # ── Wheel-to-scroll the tab bar ────────────────────────────────────────
    #
    # When the user lands the cursor on the tab bar and swipes horizontally
    # (touchpad) or wheels, scroll the tab strip rather than changing the
    # active tab. QTabBar exposes the overflow-scroll arrows as internal
    # QToolButton children when ``setUsesScrollButtons(True)`` is set; we
    # animate horizontal wheel deltas into clicks on those buttons. Vertical
    # scrolls fall through to the default Qt handling.

    _SCROLL_PIXELS_PER_CLICK = 30  # px of horizontal delta per arrow click

    def _scroll_buttons(self):  # noqa: D401 - helper
        from PySide6.QtWidgets import QToolButton
        buttons = self.findChildren(QToolButton)
        if len(buttons) < 2:
            return None, None
        buttons.sort(key=lambda b: b.x())
        return buttons[0], buttons[-1]

    def wheelEvent(self, event):  # noqa: N802 - Qt override
        from PySide6.QtCore import Qt as _Qt
        pixel = event.pixelDelta()
        angle = event.angleDelta()
        if pixel.x() != 0 or pixel.y() != 0:
            dx, dy = float(pixel.x()), float(pixel.y())
        else:
            dx = float(angle.x()) / 8.0
            dy = float(angle.y()) / 8.0
        # Horizontal-dominant gestures scroll the bar. Vertical-dominant
        # falls through to QTabBar's default (which steps the selection —
        # the long-standing Qt behaviour we don't want to change).
        if abs(dx) <= max(2.0, abs(dy)):
            super().wheelEvent(event)
            return
        left_btn, right_btn = self._scroll_buttons()
        if left_btn is None or right_btn is None or not left_btn.isVisible():
            # No overflow — nothing to scroll. Swallow the event so the
            # default ``selection-step`` handler doesn't fire instead.
            event.accept()
            return
        accum = getattr(self, "_wheel_scroll_accum", 0.0) + dx
        clicks = 0
        per = self._SCROLL_PIXELS_PER_CLICK
        while accum >= per:
            clicks -= 1  # swipe RIGHT -> reveal earlier tabs (click left)
            accum -= per
        while accum <= -per:
            clicks += 1  # swipe LEFT  -> reveal later tabs (click right)
            accum += per
        self._wheel_scroll_accum = accum
        if clicks != 0:
            target = left_btn if clicks < 0 else right_btn
            for _ in range(abs(clicks)):
                target.click()
        event.accept()


def build_centre(app, parent: QWidget) -> None:
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)

    app._notebook = QTabWidget(parent)
    app._notebook.setObjectName("CentreTabs")
    app._notebook.setMovable(False)
    app._notebook.setUsesScrollButtons(False)
    app._notebook.setElideMode(Qt.ElideNone)
    custom_tabbar = _GroupedTabBar(app._notebook)
    custom_tabbar.setUsesScrollButtons(False)
    custom_tabbar.setExpanding(False)
    custom_tabbar.setElideMode(Qt.ElideNone)
    app._notebook.setTabBar(custom_tabbar)
    # Phase 10 (A1): the section tabs migrate into the left rail's RailNav.
    # We keep the QTabWidget as the page host (so every call site that uses
    # tabText / setCurrentIndex / currentChanged still works) but hide its
    # tab bar; the rail drives currentIndex externally.
    custom_tabbar.setVisible(False)
    app._notebook.setDocumentMode(True)
    layout.addWidget(app._notebook, 1)

    def _select_by_text(title: str, _nb=app._notebook) -> None:
        for i in range(_nb.count()):
            if _nb.tabText(i) == title:
                _nb.setCurrentIndex(i)
                return
    app._notebook.select_by_text = _select_by_text

    # Map tab title -> deferred builder. Populated below; drained after the
    # window paints. The tab-change handler also calls into this map so a
    # user who clicks an un-built tab forces its builder to run inline.
    pending: Dict[str, Callable[[], None]] = {}
    app._centre_pending_builders = pending

    # Defined early so builder functions (including _build_plotting, which is
    # called eagerly as the first tab) can call it before the groups loop ends.
    def _build_pending(title: str) -> None:
        builder = pending.pop(title, None)
        if builder is None:
            return
        try:
            builder()
        except Exception:
            _logger.exception("Deferred build for %r failed", title)

    app._centre_build_pending = _build_pending

    # Tabs whose construction we never want to run from the background
    # drain — they only build on first user access (tab click). The tabs
    # listed here pull in the heaviest dependencies (matplotlib QtAgg,
    # skimage, tifffile) that aren't worth amortising at startup.
    lazy_only: Set[str] = {"smFISH"}
    app._centre_lazy_only_titles = frozenset(lazy_only)

    # Pre-create stable widget handles so deferred builder closures can
    # capture them. Sample Definitions in particular needs the QWidget to
    # be allocated up-front so the deferred ``_build_groups_centre_body``
    # closure can see it; otherwise the variable would be shadowed by the
    # ``addTab`` call further down.
    tab_groups = QWidget(app._notebook)
    QVBoxLayout(tab_groups).setContentsMargins(0, 0, 0, 0)

    # "Plotting" is a top-level tab whose body is a nested QTabWidget
    # containing the five plot sub-tabs.  We pre-allocate both the outer
    # container and the five sub-tab frames so builder closures (and the
    # drain) can reference them before the nested QTabWidget exists.
    plotting_container = QWidget(app._notebook)
    QVBoxLayout(plotting_container).setContentsMargins(0, 0, 0, 0)

    _PLOT_SUBTABS = [
        "Line Graphs", "Bar Plots", "Scatter Plot", "Distribution", "Heat Map",
    ]

    # Sidebars referenced by data-load + tab-switch logic must exist
    # immediately even though the centre tab bodies that depend on them
    # are deferred.
    app._build_replicate_panel(app._sidebar_sample_frame)
    app._build_preview_picker(app._sidebar_preview_frame)

    # Stable name -> tab QWidget map for builder closures to reach into.
    # Populated in two phases: plot sub-tab frames are inserted here before
    # the groups loop so the builder closures can close over them, even
    # though those frames end up inside the nested "Plotting" QTabWidget
    # rather than directly in app._notebook.
    tab_frames: Dict[str, QWidget] = {}
    for _t in _PLOT_SUBTABS:
        _f = QWidget()
        QVBoxLayout(_f).setContentsMargins(0, 0, 0, 0)
        tab_frames[_t] = _f

    # Group definitions: ordered list of (title, builder, eager_flag).
    # ``eager_flag`` means build the tab body immediately; otherwise the
    # builder is registered in ``pending`` and drained later. The first
    # tab in the first group is the initial active tab and is built eagerly.
    def _line_graphs_eager() -> None:
        from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
        build_line_graphs_tab(app, tab_frames["Line Graphs"])

    def _build_bar() -> None:
        from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
        build_bar_plots_tab(app, tab_frames["Bar Plots"])

    def _build_scatter() -> None:
        from well_viewer.tabs.scatter_tab_view import build_scatter_tab
        build_scatter_tab(app, tab_frames["Scatter Plot"])

    def _build_distribution() -> None:
        from well_viewer.tabs.distribution_tab_view import build_distribution_tab
        build_distribution_tab(app, tab_frames["Distribution"])

    def _build_heatmap() -> None:
        from well_viewer.tabs.heatmap_tab_view import build_heatmap_tab
        build_heatmap_tab(app, tab_frames["Heat Map"])

    # Register plot sub-tab builders in pending now so the background drain
    # can populate their frames while the app is starting up.  _build_plotting
    # (below) calls _build_pending("Line Graphs") eagerly and the drain
    # handles the rest.
    pending["Line Graphs"] = _line_graphs_eager
    pending["Bar Plots"] = _build_bar
    pending["Scatter Plot"] = _build_scatter
    pending["Distribution"] = _build_distribution
    pending["Heat Map"] = _build_heatmap

    def _build_plotting() -> None:
        """Create the nested QTabWidget and wire the five plot sub-tabs."""
        plotting_nb = QTabWidget(plotting_container)
        plotting_nb.setObjectName("PlottingSubTabs")
        plotting_nb.setElideMode(Qt.ElideNone)
        plotting_nb.setUsesScrollButtons(True)
        plotting_nb.tabBar().setExpanding(False)
        plotting_nb.tabBar().setElideMode(Qt.ElideNone)
        plotting_container.layout().addWidget(plotting_nb, 1)
        app._plotting_notebook = plotting_nb

        for title in _PLOT_SUBTABS:
            plotting_nb.addTab(tab_frames[title], title)

        # Build the first sub-tab immediately so the user sees content.
        _build_pending("Line Graphs")

        def _on_plotting_subtab(_i: int = 0) -> None:
            sub_title = plotting_nb.tabText(plotting_nb.currentIndex())
            if sub_title in pending:
                _build_pending(sub_title)
            app._on_tab_change(None)

        plotting_nb.currentChanged.connect(_on_plotting_subtab)

    def _build_image_table() -> None:
        from well_viewer.tabs.image_table_tab_view import build_image_table_tab
        from well_viewer.views.image_table_picker_view import build_image_table_picker
        build_image_table_tab(app, tab_frames["Image Table"])
        build_image_table_picker(app, app._sidebar_image_table_frame)

    def _build_review_image() -> None:
        app._build_review_image_panel(tab_frames["Segmentation"])

    def _build_smfish() -> None:
        from well_viewer.smfish_tab import SmfishTab
        frame = tab_frames["smFISH"]
        app._smfish_tab = SmfishTab(frame, app=app)
        frame.layout().addWidget(app._smfish_tab)

    def _build_stats() -> None:
        app._build_stats_tab(tab_frames["Statistics"])
        app._build_stats_group_editor(app._sidebar_stats_frame)

    def _build_review_csv() -> None:
        app._build_review_csv_tab(tab_frames["Review CSV"])

    def _build_sample_definitions() -> None:
        app._build_groups_centre(tab_groups)

    def _build_batch_export() -> None:
        from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
        build_batch_export_tab(app, tab_frames["Batch Export"])

    groups: List[Tuple[str, List[Tuple[str, Callable[[], None]]]]] = [
        ("Analysis", [
            # "Plotting" is a single top-level tab that contains Line Graphs,
            # Bar Plots, Scatter Plot, Distribution, and Heat Map as sub-tabs.
            ("Plotting", _build_plotting),
            # Cell Gating moved into the Sample Definitions tab (Cell Gating
            # sub-tab) — that's the new home for global per-cell config.
            ("smFISH", _build_smfish),
            ("Statistics", _build_stats),
        ]),
        ("Images", [
            # Movie Montage was folded into Image Table — pick a well, set
            # the channel to NUC+SEG (or any other), and click "Distribute
            # Timepoints" to get the same per-timepoint grid.
            ("Image Table", _build_image_table),
            ("Segmentation", _build_review_image),
        ]),
        ("Data", [
            ("Review CSV", _build_review_csv),
            ("Sample Definitions", _build_sample_definitions),
            ("Batch Export", _build_batch_export),
        ]),
    ]

    def _new_tab(title: str) -> QWidget:
        if title == "Sample Definitions":
            # Sample Definitions uses the pre-allocated tab_groups widget so
            # the deferred body builder closure (_build_sample_definitions)
            # can reference it before the tab is added to the QTabWidget.
            frame = tab_groups
        elif title == "Plotting":
            # "Plotting" uses the pre-allocated container so the nested
            # QTabWidget can be inserted into it by _build_plotting.
            frame = plotting_container
        else:
            frame = QWidget(app._notebook)
            QVBoxLayout(frame).setContentsMargins(0, 0, 0, 0)
        app._notebook.addTab(frame, title)
        tab_frames[title] = frame
        return frame

    # Add tabs in group order. Track which indices start a new group, and
    # the group's label, so the custom tab bar can paint a separator and a
    # tiny header before them.
    group_starts: Dict[int, str] = {}
    for group_idx, (group_label, tabs) in enumerate(groups):
        if group_idx > 0:
            group_starts[app._notebook.count()] = group_label
        for tab_idx_in_group, (title, builder) in enumerate(tabs):
            _new_tab(title)
            if group_idx == 0 and tab_idx_in_group == 0:
                # Initial active tab — build eagerly so the user sees content.
                builder()
            else:
                pending[title] = builder

    # Special pre-build hooks for tabs that wire app-level state at build
    # time even though their bodies are deferred (matches the original
    # eager attribute set so external references keep resolving).
    app._batch_export_tab_frame = tab_frames["Batch Export"]

    custom_tabbar.set_group_starts(group_starts)
    if groups:
        custom_tabbar.set_first_group_label(groups[0][0])

    app._notebook.setCurrentIndex(0)

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
    # in the background. Tabs marked lazy_only stay in ``pending`` so the
    # tab-switch handler can still build them on demand, but the drain
    # never touches them — they only construct when the user clicks them.
    def _next_drain_title():
        for title in pending:
            if title not in lazy_only:
                return title
        return None

    def _drain() -> None:
        title = _next_drain_title()
        if title is None:
            return
        _build_pending(title)
        if _next_drain_title() is not None:
            QTimer.singleShot(0, _drain)

    QTimer.singleShot(0, _drain)
