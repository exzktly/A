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

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QStackedWidget, QStyle, QStyleOptionTab, QStylePainter,
    QTabBar, QTabWidget, QVBoxLayout, QWidget,
)


_logger = logging.getLogger("well_viewer.centre_view")


class NamedPageStack(QStackedWidget):
    """``QStackedWidget`` with name-keyed page lookup.

    Phase 15 replacement for the legacy ``_notebook`` / ``_plotting_notebook``
    ``QTabWidget``s. Exposes the v2 name-based API
    (``addPage`` / ``setCurrentByName`` / ``currentName`` / ``pageNames`` /
    ``nameOf``) plus a couple of ``QTabWidget`` back-compat shims
    (``tabText``, ``select_by_text``) so the migration can land across small
    commits without breaking any downstream caller.
    """

    currentNameChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._names: list[str] = []
        self._by_name: dict[str, QWidget] = {}
        super().currentChanged.connect(self._emit_name)

    # ── v2 API ────────────────────────────────────────────────────────────
    def addPage(self, name: str, widget: QWidget) -> int:  # noqa: N802
        idx = self.addWidget(widget)
        # Pad / overwrite the name list to keep indices aligned with the
        # underlying QStackedWidget order.
        while len(self._names) <= idx:
            self._names.append("")
        self._names[idx] = name
        self._by_name[name] = widget
        return idx

    def setCurrentByName(self, name: str) -> bool:  # noqa: N802
        w = self._by_name.get(name)
        if w is None:
            return False
        self.setCurrentWidget(w)
        return True

    def currentName(self) -> str:  # noqa: N802
        idx = self.currentIndex()
        if 0 <= idx < len(self._names):
            return self._names[idx]
        return ""

    def pageNames(self) -> list[str]:  # noqa: N802
        return list(self._names)

    def nameOf(self, w: QWidget) -> str | None:  # noqa: N802
        idx = self.indexOf(w)
        if 0 <= idx < len(self._names):
            return self._names[idx]
        return None

    # ── QTabWidget back-compat shims ──────────────────────────────────────
    def tabText(self, i: int) -> str:  # noqa: N802
        if 0 <= i < len(self._names):
            return self._names[i]
        return ""

    def select_by_text(self, name: str) -> bool:
        return self.setCurrentByName(name)

    def _emit_name(self, idx: int) -> None:
        if 0 <= idx < len(self._names):
            self.currentNameChanged.emit(self._names[idx])


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

    # Phase 15: the centre is a NamedPageStack (QStackedWidget subclass) —
    # the rail nav on the left drives currentIndex externally, and downstream
    # callers reach pages via currentName() / setCurrentByName() / pageNames().
    # The QTabWidget back-compat shims (tabText, select_by_text) remain
    # during the staged caller migration; commit 5 removes the now-unused ones.
    app._notebook = NamedPageStack(parent)
    app._notebook.setObjectName("CentreTabs")
    layout.addWidget(app._notebook, 1)

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
        """Build the Plotting section: mockup-style ctxbar above a tab-bar-hidden
        QTabWidget that hosts the five renderers (line / bar / scatter cells +
        agg / distribution / heatmap). Phase 11 retires the visible plot-type
        QTabBar in favour of the v2 ctxbar.subnav SegmentedControl (Q5: switch
        governs the whole canvas — implemented here by routing through the
        existing per-renderer pages); a global Channel chip lives in
        ctxbar.right (A4); Add panel / Configure subplots / Edit axes-curve
        buttons (B9, B11) sit alongside.

        The underlying per-renderer pages keep their existing rendering
        contracts so we don't regress functionality. Phase 11b will collapse
        them into a single shared PlotCanvas.
        """
        from widgets.segmented_control import SegmentedControl as _SegmentedControl
        from widgets.icon_button import IconButton as _IconButton

        # ── ctxbar ─ Row 1 (plot-type SegmentedControl, full width) ──────
        ctxbar = QWidget(plotting_container)
        ctxbar.setObjectName("PlottingCtxbar")
        ctxbar.setAttribute(Qt.WA_StyledBackground, True)
        from theme import Colors as _C, Spacing as _S, Typography as _T, Radii as _R
        ctxbar.setStyleSheet(
            f"#PlottingCtxbar {{ background-color: {_C.surface}; "
            f"border-bottom: 1px solid {_C.border_subtle}; }}"
        )
        cbl = QHBoxLayout(ctxbar)
        cbl.setContentsMargins(_S.md, 6, _S.md, 6)
        cbl.setSpacing(_S.sm)

        sub_seg = _SegmentedControl()
        for title in _PLOT_SUBTABS:
            sub_seg.addSegment(title, data=title)
        cbl.addWidget(sub_seg, 1)  # fill the full row

        plotting_container.layout().addWidget(ctxbar, 0)

        # ── ctxbar ─ Row 2 (channel + actions, sits above the canvas) ────
        action_row = QWidget(plotting_container)
        action_row.setObjectName("PlottingActionRow")
        action_row.setAttribute(Qt.WA_StyledBackground, True)
        action_row.setStyleSheet(
            f"#PlottingActionRow {{ background-color: {_C.surface}; "
            f"border-bottom: 1px solid {_C.border_subtle}; }}"
        )
        arl = QHBoxLayout(action_row)
        arl.setContentsMargins(_S.md, 4, _S.md, 4)
        arl.setSpacing(_S.sm)

        # Phase 11b (A4): the channel selector is now a single global combo
        # in the ctxbar. The per-renderer combos still exist for back-compat
        # but ``app._on_plot_channel_selected`` mirrors every change back to
        # all of them, so editing here re-renders every renderer's view
        # against the new channel.
        from PySide6.QtWidgets import QComboBox as _QComboBox
        chan_lbl = QLabel("Channel")
        chan_lbl.setStyleSheet(
            f"color: {_C.text_muted}; font-size: {_T.caption_size}px; "
            f"letter-spacing: 0.08em;"
        )
        arl.addWidget(chan_lbl)
        app._plotting_channel_cb = _QComboBox()
        app._plotting_channel_cb.setMinimumContentsLength(8)
        app._plotting_channel_cb.setStyleSheet(
            f"QComboBox {{ background-color: {_C.panel_elevated}; "
            f"color: {_C.text_secondary}; "
            f"border: 1px solid {_C.border_subtle}; "
            f"border-radius: {_R.pill}px; padding: 2px 22px 2px 10px; "
            f"font-size: {_T.caption_size}px; font-weight: 500; "
            f"min-width: 88px; }}"
            f"QComboBox:hover {{ color: {_C.text_primary}; }}"
        )

        def _on_global_channel(_idx: int) -> None:
            on_select = getattr(app, "_on_plot_channel_selected", None)
            if on_select is None:
                return
            try:
                on_select(app._plotting_channel_cb)
            except Exception:
                pass

        app._plotting_channel_cb.currentIndexChanged.connect(_on_global_channel)
        arl.addWidget(app._plotting_channel_cb)
        # Legacy display-only chip remains as an attribute for code that
        # still pokes at ``_plotting_channel_chip`` — point it at the new
        # combo so callers that read its text still work.
        app._plotting_channel_chip = app._plotting_channel_cb

        hint = QLabel("· click a trace to filter properties")
        hint.setStyleSheet(
            f"color: {_C.text_muted}; font-size: {_T.caption_size}px; "
            f"padding-left: 4px;"
        )
        arl.addWidget(hint)

        arl.addStretch(1)

        add_panel_btn = _IconButton("plus", text=" Add panel")
        add_panel_btn.setToolTip("Add a subplot to the canvas (1–4 max)")
        arl.addWidget(add_panel_btn)
        config_btn = _IconButton("sliders")
        config_btn.setToolTip("Configure subplots…")
        arl.addWidget(config_btn)
        edit_btn = _IconButton("settings-2")
        edit_btn.setToolTip("Edit axes / curve…")
        arl.addWidget(edit_btn)
        export_btn = _IconButton("download", text=" Export figure")
        export_btn.setToolTip("Export the current figure")
        arl.addWidget(export_btn)

        plotting_container.layout().addWidget(action_row, 0)

        # ── renderer pages (per-tab views in a NamedPageStack — Phase 15) ─
        plotting_nb = NamedPageStack(plotting_container)
        plotting_nb.setObjectName("PlottingSubTabs")
        plotting_container.layout().addWidget(plotting_nb, 1)
        app._plotting_notebook = plotting_nb

        # Register all pages BEFORE wiring currentChanged so the first emit
        # always sees a valid currentName().
        for title in _PLOT_SUBTABS:
            plotting_nb.addPage(title, tab_frames[title])

        # Build the first sub-tab immediately so the user sees content.
        _build_pending("Line Graphs")

        def _on_plotting_subtab(_i: int = 0) -> None:
            sub_title = plotting_nb.currentName()
            if sub_title in pending:
                _build_pending(sub_title)
            app._on_tab_change(None)
            _refresh_channel_chip(sub_title)
            if sub_seg.currentData() != sub_title:
                blocked = sub_seg.blockSignals(True)
                try:
                    sub_seg.setCurrentByData(sub_title)
                finally:
                    sub_seg.blockSignals(blocked)

        plotting_nb.currentChanged.connect(_on_plotting_subtab)

        def _on_sub_seg(idx: int) -> None:
            target = sub_seg.currentData()
            if target:
                plotting_nb.setCurrentByName(target)

        sub_seg.currentChanged.connect(_on_sub_seg)
        sub_seg.setCurrentByData("Line Graphs")

        def _refresh_channel_chip(title: str) -> None:
            """Re-populate the global ctxbar channel combo from whichever
            renderer just became active. The renderer's own combo is the
            canonical item list (it gets populated from the loaded dataset)
            — we mirror it into the global, blocking signals so the mirror
            itself doesn't trigger ``_on_plot_channel_selected``."""
            global_cb = getattr(app, "_plotting_channel_cb", None)
            if global_cb is None:
                return
            attr_map = {
                "Line Graphs":   "_chan_cb_line",
                "Bar Plots":     "_chan_cb_bar",
                "Scatter Plot":  "_chan_cb_scatter",
                "Distribution":  "_chan_cb_distribution",
                "Heat Map":      "_chan_cb_heatmap",
            }
            cb = getattr(app, attr_map.get(title, ""), None)
            blocked = global_cb.blockSignals(True)
            try:
                global_cb.clear()
                if cb is not None and hasattr(cb, "count"):
                    for i in range(cb.count()):
                        global_cb.addItem(cb.itemText(i))
                    idx = cb.currentIndex()
                    if 0 <= idx < global_cb.count():
                        global_cb.setCurrentIndex(idx)
            finally:
                global_cb.blockSignals(blocked)

        # Wire the buttons.
        def _add_panel() -> None:
            # Phase 11b: route into PlotCanvas.addPanel once the shared
            # canvas replaces the per-renderer pages.
            app._toast("Add panel: per-renderer multi-subplot landing in "
                       "Phase 11b.", kind="info") if hasattr(app, "_toast") else None
        add_panel_btn.clicked.connect(_add_panel)

        def _config_subplots() -> None:
            # Delegate to matplotlib's built-in dialog on whichever PlotCard
            # is currently active.
            for attr in ("_line_card", "_bar_card", "_scatter_card",
                         "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
                card = getattr(app, attr, None)
                if card is None or not card.isVisible():
                    continue
                nav = getattr(card, "_nav", None)
                if nav is not None and hasattr(nav, "configure_subplots"):
                    try:
                        nav.configure_subplots()
                    except Exception:
                        pass
                return
        config_btn.clicked.connect(_config_subplots)

        def _edit_axes() -> None:
            for attr in ("_line_card", "_bar_card", "_scatter_card",
                         "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
                card = getattr(app, attr, None)
                if card is None or not card.isVisible():
                    continue
                nav = getattr(card, "_nav", None)
                if nav is not None and hasattr(nav, "edit_parameters"):
                    try:
                        nav.edit_parameters()
                    except Exception:
                        pass
                return
        edit_btn.clicked.connect(_edit_axes)

        def _export_figure() -> None:
            for attr in ("_line_card", "_bar_card", "_scatter_card",
                         "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
                card = getattr(app, attr, None)
                if card is None or not card.isVisible():
                    continue
                nav = getattr(card, "_nav", None)
                if nav is not None and hasattr(nav, "save_figure"):
                    try:
                        nav.save_figure()
                    except Exception:
                        pass
                return
        export_btn.clicked.connect(_export_figure)

        _refresh_channel_chip("Line Graphs")

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
        app._notebook.addPage(title, frame)
        tab_frames[title] = frame
        return frame

    # Add tabs in group order. The tab bar / group separator chrome retired
    # in Phase 15 — RailNav (in the left sidebar) is now the only section
    # selector, so group_starts is unused at the view layer.
    for group_idx, (_group_label, tabs) in enumerate(groups):
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

    app._notebook.setCurrentIndex(0)

    def _on_tab_change(_i: int = 0) -> None:
        # Force-build the tab the user just switched to if it hasn't been
        # built yet, so click-before-build never shows a blank tab body.
        title = app._notebook.currentName()
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
