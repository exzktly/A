"""
all_well.py
-----------
Composition root for the All-Well application (PySide6).

Tabs:
  * Review  - WellViewerApp (from well_viewer package runtime)
  * Analyze - AnalyzeTab (from analyze_tab.py)

Run:
    python all_well.py [--data_dir /path/to/results]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QTabWidget, QVBoxLayout, QWidget,
)

import theme as theme_v2
from widgets.brand_tile import BrandTile
from widgets.icon_button import IconButton
from widgets.status_dot import StatusDot

# Global tab-scoped debug toggles.
REVIEW_TAB_DEBUG = False
ANALYZE_TAB_DEBUG = False
REVIEW_BAR_DEBUG = False
REVIEW_SCATTER_DEBUG = False


class AllWellApp(QMainWindow):
    """Root window containing the Review and Analyze notebook tabs."""

    threshold_changed = Signal(float)

    def __init__(self, data_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("All-Well")
        self.resize(1640, 980)
        self.setMinimumSize(1100, 800)

        self._review: QWidget | None = None
        self._analyze: QWidget | None = None
        self._cell_threshold = 0.0

        self._build_ui()
        self._install_app_icon()
        self._apply_stylesheet()
        self._restore_window_state()

        if data_path is not None and self._review is not None:
            QTimer.singleShot(150, lambda: self._review._load_path(data_path))

    # ── UI construction ──────────────────────────────────────────────────
    def _apply_stylesheet(self) -> None:
        # Single source of truth for the app stylesheet (see theme.py /
        # design/PHASE_4_DIAGNOSIS.md). v2 ships one dark theme — there's no
        # per-theme QSS to swap.
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme_v2.qss())

    def _build_ui(self) -> None:
        from analyze_tab import AnalyzeTab
        from well_viewer import WellViewerApp

        root = QWidget(objectName="AppRoot")
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # Header bar — v2: BrandTile + wordmark + dataset chip + status dot +
        # action IconButtons (Open / Help). Per DECISIONS_NEEDED #4 we keep
        # the native frame, so this is the app-shell strip.
        header = QWidget(objectName="Sidebar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 7, 14, 7)
        hl.setSpacing(theme_v2.Spacing.sm)
        hl.addWidget(BrandTile(side=24))
        title = QLabel("All-Well")
        title.setObjectName("Title")
        hl.addWidget(title)

        # Phase 10 (B2): version pill next to wordmark.
        self._version_pill = QLabel("v2.4.1")
        self._version_pill.setObjectName("VersionPill")
        self._version_pill.setStyleSheet(
            f"color: {theme_v2.Colors.text_faint}; "
            f"font-family: {theme_v2.Typography.family_mono}; "
            f"font-size: {theme_v2.Typography.caption_size}px; "
            f"font-weight: 500; padding-left: 4px;"
        )
        hl.addWidget(self._version_pill)

        hl.addSpacing(theme_v2.Spacing.md)
        self._dataset_status = StatusDot("neutral")
        hl.addWidget(self._dataset_status)
        self._dataset_chip = QLabel("No dataset")
        self._dataset_chip.setObjectName("Chip")
        self._dataset_chip.setProperty("variant", "muted")
        hl.addWidget(self._dataset_chip)
        # Phase 10 (B1): faint trailing dataset stats (`· 96 wells · 8 tp`).
        self._dataset_stats = QLabel("")
        self._dataset_stats.setStyleSheet(
            f"color: {theme_v2.Colors.text_faint}; "
            f"font-size: {theme_v2.Typography.caption_size}px;"
        )
        self._dataset_stats.setVisible(False)
        hl.addWidget(self._dataset_stats)

        hl.addStretch(1)

        # Phase 10 (B3): refresh action.
        self._refresh_btn = IconButton("refresh-cw")
        self._refresh_btn.setToolTip("Reload the active dataset")
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        hl.addWidget(self._refresh_btn)

        # Global "presentation mode" toggle: flips every PlotCard in the app
        # between Screen (dark live-preview) and Publication (canonical
        # white-bg export). Per-card toggles still work; this is the master.
        self._present_mode = "publication"
        self._present_btn = IconButton("image")
        self._present_btn.setCheckable(True)
        self._present_btn.setToolTip("Presentation mode: toggle all plots screen ↔ publication")
        self._present_btn.toggled.connect(self._on_present_toggled)
        hl.addWidget(self._present_btn)

        self._open_btn = IconButton("home")
        self._open_btn.setToolTip("Open results directory…")
        self._open_btn.clicked.connect(self._open_dataset)
        hl.addWidget(self._open_btn)
        self._help_btn = IconButton("info")
        self._help_btn.setToolTip("Open the help drawer")
        self._help_btn.clicked.connect(self._toggle_help_drawer)
        hl.addWidget(self._help_btn)
        self._help_drawer = None  # built lazily on first open

        # Phase 10 (B23 / Q1): rail-collapse toggle for the Properties rail.
        # Glyph flips between panel-right-close (expanded) and panel-right-open
        # (collapsed) per the v2 mockup. Wired below to a CollapsibleRail
        # overlay mounted on the central widget.
        self._rail_toggle_btn = IconButton("panel-right-close")
        self._rail_toggle_btn.setToolTip("Hide the Properties rail")
        self._rail_toggle_btn.clicked.connect(self._on_rail_toggle_clicked)
        hl.addWidget(self._rail_toggle_btn)

        rl.addWidget(header)

        sep = QFrame()
        sep.setObjectName("Separator")
        sep.setFixedHeight(1)
        rl.addWidget(sep)

        # Phase 11: the outer Review/Analyze QStackedWidget is gone — Analyze
        # now lives inside WellViewerApp's central pane stack so that the
        # left rail (mode-seg + section nav + plate + saved) stays visible
        # in both modes. The mode-seg itself moved into WellViewerApp's
        # sidebar above the SECTION header.
        self._central_host = QWidget()
        self._central_host.setObjectName("CentralHost")
        ch_layout = QVBoxLayout(self._central_host)
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch_layout.setSpacing(0)
        rl.addWidget(self._central_host, 1)

        self._review = WellViewerApp(parent=None)
        ch_layout.addWidget(self._review, 1)
        # Back-compat for code paths that read self._nb (legacy after the
        # outer-stack retirement) — point it at WellViewerApp's central
        # pane stack so e.g. ``self._nb.setCurrentIndex(0)`` still means
        # "show Review".
        self._nb = self._review._central_pane_stack
        self._nb.currentChanged.connect(self._on_tab_change)
        self._review.modeChanged.connect(self._on_review_mode_changed)
        self._wrap_review_load_path()

        self._analyze = AnalyzeTab(
            parent=None,
            on_pipeline_complete=self._on_analyze_pipeline_complete,
        )
        self._review.mountAnalyzePane(self._analyze)

        # Phase 10 (A6 shell / B23 / Q11): Properties rail overlay + Log
        # tray drawer at the bottom.
        from widgets.collapsible_rail import CollapsibleRail as _CollapsibleRail
        self._properties_rail = _CollapsibleRail(
            self._central_host, width=332, collapsed=False,
        )
        # Placeholder content for Phase 10 — Phase 12 builds the real
        # scope segmented + ⌘K search + 8 sections.
        ph = QWidget()
        ph_layout = QVBoxLayout(ph)
        ph_layout.setContentsMargins(theme_v2.Spacing.lg, theme_v2.Spacing.lg,
                                     theme_v2.Spacing.lg, theme_v2.Spacing.lg)
        head_lbl = QLabel("Properties")
        head_lbl.setStyleSheet(
            f"color: {theme_v2.Colors.text_primary}; "
            f"font-size: {theme_v2.Typography.emph_size}px; font-weight: 600;"
        )
        ph_layout.addWidget(head_lbl)
        ph_layout.addSpacing(theme_v2.Spacing.sm)
        stub = QLabel(
            "Phase 12 populates this rail with the scope segmented "
            "(All / Plot 1 / Plot 2), ⌘K search, and eight collapsible "
            "sections (Profile & Format / Statistics / Axes / Legend / "
            "Lines & Markers / Grid / Limits & Scale / Layout)."
        )
        stub.setWordWrap(True)
        stub.setStyleSheet(f"color: {theme_v2.Colors.text_muted};")
        ph_layout.addWidget(stub)
        ph_layout.addStretch(1)
        self._properties_rail.setContentWidget(ph)
        self._properties_rail.collapsedChanged.connect(self._on_rail_collapsed_changed)

        # Status bar v2: status / kbd hints / Log tray IconButton.
        from widgets.kbd_hint import KbdHint as _KbdHint
        statusbar = QWidget(objectName="StatusBar")
        sb_layout = QHBoxLayout(statusbar)
        sb_layout.setContentsMargins(theme_v2.Spacing.md, 4,
                                     theme_v2.Spacing.md, 4)
        sb_layout.setSpacing(theme_v2.Spacing.sm)
        self._status_dot = StatusDot("success")
        sb_layout.addWidget(self._status_dot)
        self._status_lbl_app = QLabel("Ready.")
        self._status_lbl_app.setStyleSheet(
            f"color: {theme_v2.Colors.text_secondary}; "
            f"font-size: {theme_v2.Typography.caption_size}px;"
        )
        sb_layout.addWidget(self._status_lbl_app)
        sb_layout.addStretch(1)
        # Kbd hints (B16 wires the actual QShortcuts in Phase 13; the
        # statusbar already advertises them per the mockup).
        for label, hint in (("Open", "⌘O"), ("Search", "⌘K"), ("Export", "⌘E")):
            l = QLabel(label)
            l.setStyleSheet(
                f"color: {theme_v2.Colors.text_muted}; "
                f"font-size: {theme_v2.Typography.caption_size}px;"
            )
            sb_layout.addWidget(l)
            sb_layout.addWidget(_KbdHint(hint))
            sb_layout.addSpacing(theme_v2.Spacing.xs)
        self._log_tray_btn = IconButton("terminal-square")
        self._log_tray_btn.setText("  Log")
        self._log_tray_btn.setToolTip("Open the log drawer")
        self._log_tray_btn.clicked.connect(self._toggle_log_drawer)
        sb_layout.addWidget(self._log_tray_btn)
        statusbar.setStyleSheet(
            f"#StatusBar {{ background-color: {theme_v2.Colors.titlebar}; "
            f"border-top: 1px solid {theme_v2.Colors.border_subtle}; }}"
        )
        rl.addWidget(statusbar)
        self._log_drawer = None  # lazy
        self._log_ring: list[str] = []

    def _install_app_icon(self) -> None:
        """96-well plate icon whose lit wells spell A W across the fluorescence spectrum."""
        C_BG_TOP   = QColor("#1b2740")
        C_BG_BOT   = QColor("#0b1220")
        C_BG_STROKE = QColor("#2f3e63")
        C_PLATE    = QColor("#eef2f8")
        C_PLATE_EDGE = QColor("#c2ccda")
        C_NOTCH    = QColor("#dde3ed")
        C_EMPTY    = QColor("#2a3858")
        C_BLUE     = QColor("#5aa0ff")
        C_CYAN     = QColor("#3dd6d6")
        C_GREEN    = QColor("#6fd672")
        C_YELLOW   = QColor("#f0d042")
        C_RED      = QColor("#ff7a7a")
        C_WHITE    = QColor("#ffffff")

        # 1-indexed (row, col). Same design as _Docs/icons/icon_1_plate_grid.svg.
        pattern = {
            (1, 3): C_BLUE,   (1, 7): C_BLUE,    (1, 12): C_BLUE,
            (2, 2): C_BLUE,   (2, 4): C_BLUE,    (2, 7): C_BLUE,   (2, 12): C_BLUE,
            (3, 2): C_CYAN,   (3, 4): C_CYAN,    (3, 7): C_CYAN,   (3, 12): C_CYAN,
            (4, 1): C_GREEN,  (4, 5): C_GREEN,   (4, 7): C_GREEN,  (4, 12): C_GREEN,
            (5, 1): C_GREEN,  (5, 2): C_GREEN,   (5, 3): C_WHITE,
            (5, 4): C_GREEN,  (5, 5): C_GREEN,   (5, 7): C_GREEN,  (5, 12): C_GREEN,
            (6, 1): C_YELLOW, (6, 5): C_YELLOW,  (6, 7): C_YELLOW,
            (6, 9): C_YELLOW, (6, 10): C_YELLOW, (6, 12): C_YELLOW,
            (7, 1): C_RED,    (7, 5): C_RED,     (7, 7): C_RED,
            (7, 8): C_RED,    (7, 11): C_RED,    (7, 12): C_RED,
            (8, 1): C_RED,    (8, 5): C_RED,     (8, 8): C_RED,    (8, 11): C_RED,
        }

        def _render(size: int) -> QPixmap:
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing, True)

            s = size / 1024.0  # SVG is authored on a 1024×1024 grid

            # Rounded squircle background with vertical gradient.
            bg_rect = QRectF(72 * s, 72 * s, 880 * s, 880 * s)
            bg_grad = QRadialGradient(bg_rect.center(), bg_rect.height())
            bg_grad.setColorAt(0.0, C_BG_TOP)
            bg_grad.setColorAt(1.0, C_BG_BOT)
            p.setBrush(QBrush(bg_grad))
            p.setPen(QPen(C_BG_STROKE, max(1.0, 3 * s)))
            p.drawRoundedRect(bg_rect, 200 * s, 200 * s)

            # Plate body with notched corner.
            plate_rect = QRectF(140 * s, 220 * s, 744 * s, 584 * s)
            p.setBrush(QBrush(C_PLATE))
            p.setPen(QPen(C_PLATE_EDGE, max(1.0, 4 * s)))
            p.drawRoundedRect(plate_rect, 36 * s, 36 * s)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(C_NOTCH))
            p.drawRect(QRectF(140 * s, 220 * s, 100 * s, 36 * s))

            # 96 wells — 8 rows × 12 cols.
            xs = [200 + i * 56 for i in range(12)]
            ys = [276 + i * 64 for i in range(8)]
            r_well = 22 * s
            for row in range(1, 9):
                for col in range(1, 13):
                    cx = xs[col - 1] * s
                    cy = ys[row - 1] * s
                    colour = pattern.get((row, col), C_EMPTY)
                    # Centre-hot radial gradient gives wells a fluorescent glow.
                    grad = QRadialGradient(cx, cy - 0.2 * r_well, r_well * 1.2)
                    grad.setColorAt(0.0, colour.lighter(135))
                    grad.setColorAt(1.0, colour)
                    p.setBrush(QBrush(grad))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(QRectF(cx - r_well, cy - r_well,
                                         r_well * 2, r_well * 2))

            p.end()
            return pm

        icon = QIcon()
        for sz in (16, 24, 32, 48, 64, 128, 256, 512):
            icon.addPixmap(_render(sz))
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

    def _wrap_review_load_path(self) -> None:
        """Hook the review tab's _load_path so the header chip updates whenever
        a dataset is loaded (from either tab or CLI). We monkey-patch instead
        of adding a Qt signal to avoid touching runtime_app's __init__."""
        review = self._review
        if review is None or not hasattr(review, "_load_path"):
            return
        original = review._load_path

        def _patched(path, *a, **kw):
            result = original(path, *a, **kw)
            try:
                self._update_dataset_chip(path)
            except Exception:
                pass
            return result

        review._load_path = _patched  # type: ignore[assignment]

    def _update_dataset_chip(self, path) -> None:
        if path is None:
            self._dataset_chip.setText("No dataset")
            self._dataset_status.setStatus("neutral")
            if hasattr(self, "_dataset_stats"):
                self._dataset_stats.setVisible(False)
                self._dataset_stats.setText("")
            return
        try:
            p = Path(path)
            name = p.name or str(p)
        except Exception:
            name = str(path)
            p = None
        # Phase 10 (B1 / Q7): synthesise breadcrumb-ish path from the
        # dataset path — grandparent · parent · <name>.
        if p is not None:
            parents = list(p.parents)
            crumbs = []
            for i in range(min(2, len(parents))):
                if parents[i].name:
                    crumbs.append(parents[i].name)
            crumbs = list(reversed(crumbs))
            display = (" · ".join(crumbs + [name])) if crumbs else name
            self._dataset_chip.setText(display)
        else:
            self._dataset_chip.setText(name)
        self._dataset_chip.setToolTip(str(path))
        self._dataset_status.setStatus("success")
        # Best-effort dataset stats from the Review widget's loaded state.
        try:
            wells = len(getattr(self._review, "_well_paths", {}) or {})
            tps_attr = getattr(self._review, "_timepoints", None)
            tps = len(tps_attr) if tps_attr is not None else 0
            tail = []
            if wells:
                tail.append(f"{wells} wells")
            if tps:
                tail.append(f"{tps} timepoints")
            text = "· " + " · ".join(tail) if tail else ""
            if hasattr(self, "_dataset_stats"):
                self._dataset_stats.setText(text)
                self._dataset_stats.setVisible(bool(text))
        except Exception:
            pass

    def _on_present_toggled(self, on: bool) -> None:
        """Flip every known PlotCard's plotTheme together."""
        self._present_mode = "screen" if on else "publication"
        self._present_btn.setToolTip(
            f"Presentation mode: currently {self._present_mode} — click to toggle"
        )
        if self._review is None:
            return
        card_attrs = (
            "_line_card", "_bar_card", "_scatter_card",
            "_scatter_agg_card", "_distribution_card", "_heatmap_card",
        )
        for attr in card_attrs:
            card = getattr(self._review, attr, None)
            if card is None or not hasattr(card, "setPlotTheme"):
                continue
            try:
                card.setPlotTheme(self._present_mode)
            except Exception:
                pass

    def _toggle_help_drawer(self) -> None:
        """Show / hide a v2 Drawer with quick help. Lazy-built on first call."""
        if self._help_drawer is None:
            from widgets.drawer import Drawer
            drawer = Drawer(self, width_hint=420)
            content = QWidget(drawer)
            cl = QVBoxLayout(content)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(theme_v2.Spacing.md)
            heading = QLabel("All-Well — quick help", content)
            heading.setObjectName("Heading")
            cl.addWidget(heading)
            body = QLabel(content)
            body.setWordWrap(True)
            body.setText(
                "<b>Review tab</b> — explore an already-analyzed dataset: "
                "Line / Bar / Scatter / Distribution / Heat Map plots, "
                "per-cell Segmentation review, and the rendered Image Table.<br><br>"
                "<b>Analyze tab</b> — run the segmentation + measurement "
                "pipeline on a fresh dataset.<br><br>"
                "<b>Header buttons</b> — Open a results directory, toggle "
                "presentation mode (all plots Screen ↔ Publication), or this "
                "help drawer.<br><br>"
                "<b>Style panel</b> — the per-card sliders button on every "
                "plot opens the export-style sidebar; click again to hide.<br><br>"
                "For the full design notes see <tt>design/PORT_PLAN.md</tt>."
            )
            cl.addWidget(body)
            cl.addStretch(1)
            drawer.setContentWidget(content)
            self._help_drawer = drawer
        if self._help_drawer.isVisible():
            self._help_drawer.close()
        else:
            self._help_drawer.open()

    # ── Phase 10 / 11 handlers ───────────────────────────────────────────
    def _on_review_mode_changed(self, mode: str) -> None:
        """Mirror WellViewerApp's mode change into status / dataset chip."""
        # No external work needed today beyond status; keep for hookability.
        try:
            dot = getattr(self, "_status_dot", None)
            if dot is not None:
                dot.setStatus("success" if mode == "review" else "warn")
        except Exception:
            pass

    def _on_refresh_clicked(self) -> None:
        # Re-load the active dataset (Review's _load_path is the canonical
        # entry point).
        review = self._review
        if review is None or not hasattr(review, "_load_path"):
            return
        cur = getattr(review, "_loaded_path", None)
        if cur:
            try:
                review._load_path(Path(cur))
            except Exception:
                pass

    def _on_rail_toggle_clicked(self) -> None:
        rail = getattr(self, "_properties_rail", None)
        if rail is None:
            return
        rail.toggle()

    def _on_rail_collapsed_changed(self, collapsed: bool) -> None:
        if not hasattr(self, "_rail_toggle_btn"):
            return
        self._rail_toggle_btn.setIconName(
            "panel-right-open" if collapsed else "panel-right-close"
        )
        self._rail_toggle_btn.setToolTip(
            "Show the Properties rail" if collapsed else "Hide the Properties rail"
        )

    def _toggle_log_drawer(self) -> None:
        if self._log_drawer is None:
            from widgets.drawer import Drawer
            drawer = Drawer(self, width_hint=460)
            body = QWidget(drawer)
            bl = QVBoxLayout(body)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(theme_v2.Spacing.sm)
            head = QLabel("Application log")
            head.setObjectName("Heading")
            bl.addWidget(head)
            from PySide6.QtWidgets import QTextEdit as _QTextEdit
            self._log_view = _QTextEdit(body)
            self._log_view.setReadOnly(True)
            self._log_view.setStyleSheet(
                f"QTextEdit {{ background-color: {theme_v2.Colors.panel}; "
                f"color: {theme_v2.Colors.text_secondary}; "
                f"font-family: {theme_v2.Typography.family_mono}; "
                f"font-size: {theme_v2.Typography.caption_size}px; "
                f"border: 1px solid {theme_v2.Colors.border_subtle}; }}"
            )
            bl.addWidget(self._log_view, 1)
            drawer.setContentWidget(body)
            self._log_drawer = drawer
            self._attach_log_ring_buffer()
        # Re-fill from ring buffer each open in case the drawer was rebuilt.
        try:
            self._log_view.setPlainText("\n".join(self._log_ring[-500:]))
        except Exception:
            pass
        if self._log_drawer.isVisible():
            self._log_drawer.close()
        else:
            self._log_drawer.open()

    def _attach_log_ring_buffer(self) -> None:
        """Install a logging.Handler that keeps the last N records in
        ``self._log_ring`` so the Log drawer has something to show without
        having to subscribe live."""
        import logging as _logging

        ring = self._log_ring

        class _RingHandler(_logging.Handler):
            def emit(self, record):  # noqa: N802
                try:
                    ring.append(self.format(record))
                    if len(ring) > 1000:
                        del ring[:500]
                except Exception:
                    pass

        h = _RingHandler()
        h.setFormatter(_logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
                                          datefmt="%H:%M:%S"))
        _logging.getLogger().addHandler(h)

    def _open_dataset(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Open results directory")
        if not d:
            return
        self._nb.setCurrentIndex(0)
        if self._review is not None:
            QTimer.singleShot(50, lambda: self._review._load_path(Path(d)))

    def _on_tab_change(self, idx: int) -> None:
        if self._review is None:
            return
        # QStackedWidget has no tabText — index 0 is Review, 1 is Analyze
        # (matches the order they were added to self._nb and to the mode-seg).
        if idx == 0:
            QTimer.singleShot(50, self._nudge_review)
        # WellViewerApp's own mode-seg syncs via its _on_central_pane_changed;
        # nothing to do at this layer.

    def _on_analyze_pipeline_complete(self, output_dir: Path) -> None:
        if self._review is None:
            return
        dataset_path = output_dir
        if output_dir.name.lower() == "out" and (output_dir.parent / "in").is_dir():
            dataset_path = output_dir.parent
        self._nb.setCurrentIndex(0)
        QTimer.singleShot(50, lambda: self._review._load_path(dataset_path))
        self._update_dataset_chip(dataset_path)

    def _nudge_review(self) -> None:
        if self._review is None:
            return
        if hasattr(self._review, "_redraw"):
            try:
                self._review._redraw()
            except Exception:
                pass
        if hasattr(self._review, "_redraw_bars"):
            try:
                self._review._redraw_bars()
            except Exception:
                pass

    def _qsettings(self):
        from PySide6.QtCore import QSettings
        return QSettings("AllWell", "AllWellApp")

    def _restore_window_state(self) -> None:
        """Restore the main window geometry + splitter sizes saved from the
        previous session. Silent no-op the first time a user runs the app."""
        try:
            s = self._qsettings()
            geom = s.value("window/geometry")
            if geom is not None:
                self.restoreGeometry(geom)
            state = s.value("window/state")
            if state is not None:
                self.restoreState(state)
            # Splitter geometry lives inside the Review widget.
            if self._review is not None:
                h_pane = getattr(self._review, "_h_pane", None)
                if h_pane is not None:
                    sizes = s.value("review/h_pane_sizes")
                    if sizes is not None:
                        # QSettings serialises lists of int as list[str] on some
                        # backends; normalise.
                        try:
                            h_pane.setSizes([int(x) for x in sizes])
                        except Exception:
                            pass
        except Exception:
            pass

    def _save_window_state(self) -> None:
        try:
            s = self._qsettings()
            s.setValue("window/geometry", self.saveGeometry())
            s.setValue("window/state", self.saveState())
            if self._review is not None:
                h_pane = getattr(self._review, "_h_pane", None)
                if h_pane is not None:
                    s.setValue("review/h_pane_sizes", h_pane.sizes())
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_window_state()
        if self._review is not None and hasattr(self._review, "_cleanup_tmp"):
            try:
                self._review._cleanup_tmp()
            except Exception:
                pass
        super().closeEvent(event)

    # ── Cross-tab threshold ───────────────────────────────────────────────
    def get_cell_threshold(self) -> float:
        if self._analyze is not None and getattr(self._analyze, "_cell_properties_tab", None) is not None:
            try:
                return float(self._analyze._cell_properties_tab.get_threshold())
            except Exception:
                pass
        return self._cell_threshold

    def set_cell_threshold(self, value: float) -> None:
        self._cell_threshold = float(value)
        if self._analyze is not None and getattr(self._analyze, "_cell_properties_tab", None) is not None:
            try:
                self._analyze._cell_properties_tab.set_threshold(self._cell_threshold)
            except Exception:
                pass
        self.threshold_changed.emit(self._cell_threshold)


def main() -> None:
    from well_viewer import debug_flags as _debug_flags

    _debug_flags.REVIEW_TAB_DEBUG = REVIEW_TAB_DEBUG
    _debug_flags.ANALYZE_TAB_DEBUG = ANALYZE_TAB_DEBUG
    _debug_flags.REVIEW_BAR_DEBUG = REVIEW_BAR_DEBUG
    _debug_flags.REVIEW_SCATTER_DEBUG = REVIEW_SCATTER_DEBUG

    ap = argparse.ArgumentParser(
        description="All-Well: pipeline runner + well viewer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--data_dir", type=Path, default=None,
                    help="Pre-load a results directory into the Review tab on startup.")
    args = ap.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme_v2.qss())
    win = AllWellApp(data_path=args.data_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
