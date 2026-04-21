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

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from ui.theme import THEMES, ThemeManager, build_stylesheet, set_theme

REVIEW_TAB_DEBUG = False
ANALYZE_TAB_DEBUG = False
REVIEW_BAR_DEBUG = False
REVIEW_SCATTER_DEBUG = False

_PALETTE_ORDER = ["Warm", "Fluoro", "Ivory"]
_PALETTE_SWATCHES = {
    "Warm":   ("#F7F2EA", "#0E6B52", "#E25C3A"),
    "Fluoro": ("#0E0F0C", "#C6F24E", "#F05BB5"),
    "Ivory":  ("#F4F1EB", "#115E59", "#F4A87A"),
}
_PALETTE_LABELS = {
    "Warm":   "Warm lab",
    "Fluoro": "Fluoro",
    "Ivory":  "Ivory mint",
}


class _BrandMarkWidget(QWidget):
    """26×26 painted brand mark: rounded square, 2×2 well dots, sparkline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _event) -> None:  # noqa: N802
        from ui.theme.styles import get_color
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        ink    = QColor(get_color("TXT_PRI"))
        mut    = QColor(get_color("MUT"))
        accent = QColor(get_color("ACCENT"))
        panel  = QColor(get_color("BG_PANEL"))

        # Rounded square background
        path = QPainterPath()
        path.addRoundedRect(0, 0, 26, 26, 7, 7)
        p.fillPath(path, ink)

        # 2×2 well grid: 3 muted dots + 1 accent dot (bottom-right)
        r = 3.0
        p.setPen(Qt.NoPen)
        for cx, cy in [(8, 8), (18, 8), (8, 18)]:
            p.setBrush(mut)
            p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        p.setBrush(accent)
        p.drawEllipse(int(18 - r), int(18 - r), int(r * 2), int(r * 2))

        # Sparkline overlay
        pen = QPen(panel)
        pen.setWidthF(1.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        pts = [(4, 20), (7, 17), (11, 19), (15, 13), (19, 16), (22, 11)]
        for i in range(len(pts) - 1):
            p.drawLine(*pts[i], *pts[i + 1])

        p.end()


class _TweaksPanel(QFrame):
    """Floating palette-switcher panel (popup style)."""

    palette_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("TweaksPanel")
        self.setFixedWidth(230)
        self._pal_btns: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Header row
        hdr = QHBoxLayout()
        title = QLabel("Tweaks")
        title.setStyleSheet("font-size:11px; font-weight:600; letter-spacing:1px; text-transform:uppercase;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("border:0; background:transparent; font-size:16px; border-radius:11px;")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        # Palette label
        pal_lbl = QLabel("Palette")
        pal_lbl.setStyleSheet("font-size:11.5px; font-weight:500; color: inherit;")
        lay.addWidget(pal_lbl)

        # 3 palette buttons arranged horizontally
        pal_row = QHBoxLayout()
        pal_row.setSpacing(6)
        for pal_id in _PALETTE_ORDER:
            btn = QPushButton()
            btn.setObjectName("PalBtn")
            btn.setFixedHeight(62)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=pal_id: self.palette_selected.emit(p))
            self._pal_btns[pal_id] = btn
            pal_row.addWidget(btn)
        lay.addLayout(pal_row)

        note = QLabel("Palettes apply instantly.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size:11px; color: inherit; opacity: 0.6;")
        lay.addWidget(note)

    def set_active_palette(self, name: str) -> None:
        for pal_id, btn in self._pal_btns.items():
            btn.setProperty("active", "true" if pal_id == name else "false")
            btn.setText(_PALETTE_LABELS.get(pal_id, pal_id))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _repaint_swatches(self) -> None:
        for pal_id, btn in self._pal_btns.items():
            btn.setText(_PALETTE_LABELS.get(pal_id, pal_id))


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
        self._current_palette = "Warm"
        self._theme_manager = ThemeManager("Warm")
        self._cell_threshold = 0.0
        self._tweaks_panel: _TweaksPanel | None = None

        self._build_ui()
        self._install_app_icon()
        self._apply_stylesheet("Warm")

        if data_path is not None and self._review is not None:
            QTimer.singleShot(150, lambda: self._review._load_path(data_path))

    # ── UI construction ──────────────────────────────────────────────────
    def _apply_stylesheet(self, palette_name: str) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(palette_name))

    def _build_ui(self) -> None:
        from analyze_tab import AnalyzeTab
        from well_viewer import WellViewerApp

        root = QWidget(objectName="AppRoot")
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # ── Header bar ───────────────────────────────────────────────────
        header = QWidget(objectName="HeaderBar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(10)

        # Brand mark + wordmark
        self._brand_mark = _BrandMarkWidget(header)
        hl.addWidget(self._brand_mark)

        brand_name = QLabel("All·Well", objectName="BrandName")
        hl.addWidget(brand_name)

        # Spacer between brand and pill tabs
        hl.addSpacing(22)

        # Pill tab container
        pill_frame = QFrame(objectName="PillTabBar")
        pill_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pill_lay = QHBoxLayout(pill_frame)
        pill_lay.setContentsMargins(3, 3, 3, 3)
        pill_lay.setSpacing(2)

        self._review_tab_btn = QPushButton("Review", objectName="PillTab")
        self._review_tab_btn.setProperty("active", "true")
        self._review_tab_btn.setCursor(Qt.PointingHandCursor)
        self._review_tab_btn.clicked.connect(lambda: self._switch_tab(0))

        self._analyze_tab_btn = QPushButton("Analyze", objectName="PillTab")
        self._analyze_tab_btn.setProperty("active", "false")
        self._analyze_tab_btn.setCursor(Qt.PointingHandCursor)
        self._analyze_tab_btn.clicked.connect(lambda: self._switch_tab(1))

        pill_lay.addWidget(self._review_tab_btn)
        pill_lay.addWidget(self._analyze_tab_btn)
        hl.addWidget(pill_frame)

        # Right side
        hl.addStretch(1)

        # Crumb (dataset breadcrumb — updated when data loads)
        self._crumb_label = QLabel("", objectName="Crumb")
        self._crumb_label.setVisible(False)
        hl.addWidget(self._crumb_label)

        # Avatar
        avatar = QLabel("AW", objectName="Avatar")
        hl.addWidget(avatar)

        # Tweaks button
        self._tweaks_btn = QPushButton("✶", objectName="TweaksBtn")
        self._tweaks_btn.setToolTip("Palette tweaks")
        self._tweaks_btn.setCursor(Qt.PointingHandCursor)
        self._tweaks_btn.clicked.connect(self._toggle_tweaks)
        hl.addWidget(self._tweaks_btn)

        rl.addWidget(header)

        # 1px header separator
        sep = QFrame(objectName="Separator")
        sep.setFixedHeight(1)
        rl.addWidget(sep)

        # ── Notebook ─────────────────────────────────────────────────────
        self._nb = QTabWidget()
        self._nb.tabBar().hide()          # pill tabs replace the native tab bar
        self._nb.currentChanged.connect(self._on_nb_tab_change)
        rl.addWidget(self._nb, 1)

        self._review = WellViewerApp(parent=None)
        self._nb.addTab(self._review, "Review")

        self._analyze = AnalyzeTab(
            parent=None,
            on_pipeline_complete=self._on_analyze_pipeline_complete,
        )
        self._nb.addTab(self._analyze, "Analyze")
        self._nb.setCurrentIndex(0)

        # ── Tweaks panel (created lazily on first open) ───────────────────
        self._tweaks_panel = _TweaksPanel(self)
        self._tweaks_panel.hide()
        self._tweaks_panel.palette_selected.connect(self._on_palette_change)

    # ── Tab switching ────────────────────────────────────────────────────
    def _switch_tab(self, idx: int) -> None:
        self._nb.setCurrentIndex(idx)

    def _on_nb_tab_change(self, idx: int) -> None:
        self._review_tab_btn.setProperty("active", "true" if idx == 0 else "false")
        self._analyze_tab_btn.setProperty("active", "true" if idx == 1 else "false")
        for btn in (self._review_tab_btn, self._analyze_tab_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if idx == 0 and self._review is not None:
            QTimer.singleShot(50, self._nudge_review)

    # ── Tweaks panel ─────────────────────────────────────────────────────
    def _toggle_tweaks(self) -> None:
        if self._tweaks_panel is None:
            return
        if self._tweaks_panel.isVisible():
            self._tweaks_panel.hide()
            return
        self._tweaks_panel.set_active_palette(self._current_palette)
        # Position above the tweaks button (bottom-right corner area)
        btn_pos = self._tweaks_btn.mapToGlobal(self._tweaks_btn.rect().topRight())
        panel_w = self._tweaks_panel.sizeHint().width()
        panel_h = self._tweaks_panel.sizeHint().height()
        self._tweaks_panel.move(btn_pos.x() - panel_w, btn_pos.y() - panel_h - 8)
        self._tweaks_panel.show()
        self._tweaks_panel.raise_()

    def _on_palette_change(self, palette_name: str) -> None:
        if palette_name == self._current_palette:
            return
        self._current_palette = palette_name
        self._theme_manager.set_theme(palette_name)
        set_theme(palette_name)
        self._apply_stylesheet(palette_name)
        self._brand_mark.update()       # repaint brand mark with new colors

        # Re-polish all children so QSS property rules reapply
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)

        if self._review is not None and hasattr(self._review, "_on_theme_change"):
            try:
                self._review._on_theme_change(palette_name)
            except Exception:
                pass
        if self._tweaks_panel is not None:
            self._tweaks_panel.set_active_palette(palette_name)
        self._install_app_icon()

    # ── App icon ─────────────────────────────────────────────────────────
    def _install_app_icon(self) -> None:
        """Draw a 96-well plate icon whose lit wells spell A W."""
        size = 128
        img = QImage(size, size, QImage.Format_RGB32)
        img.fill(QColor("#0b1220"))

        C_PLATE = QColor("#eef2f8")
        C_EMPTY = QColor("#2a3858")
        C_BLUE = QColor("#5aa0ff"); C_CYAN = QColor("#3dd6d6")
        C_GREEN = QColor("#6fd672"); C_YELLOW = QColor("#f0d042")
        C_RED = QColor("#ff7a7a"); C_WHITE = QColor("#ffffff")

        for y in range(26, size - 26):
            for x in range(10, size - 10):
                img.setPixelColor(x, y, C_PLATE)

        xs = [14 + i * 9 for i in range(12)]
        ys = [32 + i * 9 for i in range(8)]
        pattern = {
            (1, 3): C_BLUE, (1, 7): C_BLUE, (1, 12): C_BLUE,
            (2, 2): C_BLUE, (2, 4): C_BLUE, (2, 7): C_BLUE, (2, 12): C_BLUE,
            (3, 2): C_CYAN, (3, 4): C_CYAN, (3, 7): C_CYAN, (3, 12): C_CYAN,
            (4, 1): C_GREEN, (4, 5): C_GREEN, (4, 7): C_GREEN, (4, 12): C_GREEN,
            (5, 1): C_GREEN, (5, 2): C_GREEN, (5, 3): C_WHITE,
            (5, 4): C_GREEN, (5, 5): C_GREEN, (5, 7): C_GREEN, (5, 12): C_GREEN,
            (6, 1): C_YELLOW, (6, 5): C_YELLOW, (6, 7): C_YELLOW,
            (6, 9): C_YELLOW, (6, 10): C_YELLOW, (6, 12): C_YELLOW,
            (7, 1): C_RED, (7, 5): C_RED, (7, 7): C_RED,
            (7, 8): C_RED, (7, 11): C_RED, (7, 12): C_RED,
            (8, 1): C_RED, (8, 5): C_RED, (8, 8): C_RED, (8, 11): C_RED,
        }

        def _disk(cx: int, cy: int, r: int, col: QColor) -> None:
            r2 = r * r
            for yy in range(cy - r, cy + r + 1):
                for xx in range(cx - r, cx + r + 1):
                    if 0 <= xx < size and 0 <= yy < size and (xx - cx) ** 2 + (yy - cy) ** 2 <= r2:
                        img.setPixelColor(xx, yy, col)

        for row in range(1, 9):
            for col in range(1, 13):
                _disk(xs[col - 1], ys[row - 1], 4, pattern.get((row, col), C_EMPTY))

        self.setWindowIcon(QIcon(QPixmap.fromImage(img)))

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

    def _on_analyze_pipeline_complete(self, output_dir: Path) -> None:
        if self._review is None:
            return
        dataset_path = output_dir
        if output_dir.name.lower() == "out" and (output_dir.parent / "in").is_dir():
            dataset_path = output_dir.parent
        self._nb.setCurrentIndex(0)
        QTimer.singleShot(50, lambda: self._review._load_path(dataset_path))

    def closeEvent(self, event) -> None:  # noqa: N802
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
    _debug_flags.BAR_DEBUG = REVIEW_BAR_DEBUG

    ap = argparse.ArgumentParser(
        description="All-Well: pipeline runner + well viewer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--data_dir", type=Path, default=None,
                    help="Pre-load a results directory into the Review tab on startup.")
    args = ap.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    win = AllWellApp(data_path=args.data_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
