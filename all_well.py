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
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QTabWidget, QVBoxLayout, QWidget,
)

from ui.theme import THEMES, ThemeManager, build_stylesheet, set_theme

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
        self._theme_manager = ThemeManager("Dark")
        self._cell_threshold = 0.0

        self._build_ui()
        self._install_app_icon()
        self._apply_stylesheet("Dark")

        if data_path is not None and self._review is not None:
            QTimer.singleShot(150, lambda: self._review._load_path(data_path))

    # ── UI construction ──────────────────────────────────────────────────
    def _apply_stylesheet(self, theme_name: str) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(theme_name))

    def _build_ui(self) -> None:
        from analyze_tab import AnalyzeTab
        from well_viewer import WellViewerApp

        root = QWidget(objectName="AppRoot")
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # Header bar
        header = QWidget(objectName="Sidebar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 7, 14, 7)
        title = QLabel("All-Well")
        title.setObjectName("Title")
        hl.addWidget(title)
        hl.addStretch(1)
        theme_label = QLabel("Theme:")
        theme_label.setObjectName("Muted")
        hl.addWidget(theme_label)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(self._theme_manager.get_available_themes())
        self._theme_combo.setFixedWidth(90)
        self._theme_combo.currentTextChanged.connect(self._on_theme_change)
        hl.addWidget(self._theme_combo)
        rl.addWidget(header)

        sep = QFrame()
        sep.setObjectName("Separator")
        sep.setFixedHeight(1)
        rl.addWidget(sep)

        # Notebook
        self._nb = QTabWidget()
        self._nb.currentChanged.connect(self._on_tab_change)
        nb_bar = self._nb.tabBar()
        nb_bar.setExpanding(False)
        nb_bar.setElideMode(Qt.ElideNone)
        rl.addWidget(self._nb, 1)

        self._review = WellViewerApp(parent=None)
        self._nb.addTab(self._review, "Review")

        self._analyze = AnalyzeTab(
            parent=None,
            on_pipeline_complete=self._on_analyze_pipeline_complete,
        )
        self._nb.addTab(self._analyze, "Analyze")
        self._nb.setCurrentIndex(0)

    def _on_theme_change(self, theme_name: str) -> None:
        old = self._theme_manager.current_theme
        if theme_name == old:
            return
        self._theme_manager.set_theme(theme_name)
        set_theme(theme_name)
        self._apply_stylesheet(theme_name)

        # Re-polish so dynamic property-based QSS rules reapply.
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)

        if self._review is not None and hasattr(self._review, "_on_theme_change"):
            try:
                self._review._on_theme_change(theme_name)
            except Exception:
                pass
        try:
            from well_viewer.ui_helpers import refresh_plot_toolbar_icons
            refresh_plot_toolbar_icons(self)
        except Exception:
            pass
        self._install_app_icon()

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

    def _on_tab_change(self, idx: int) -> None:
        if self._review is None:
            return
        if self._nb.tabText(idx).strip() == "Review":
            QTimer.singleShot(50, self._nudge_review)

    def _on_analyze_pipeline_complete(self, output_dir: Path) -> None:
        if self._review is None:
            return
        dataset_path = output_dir
        if output_dir.name.lower() == "out" and (output_dir.parent / "in").is_dir():
            dataset_path = output_dir.parent
        self._nb.setCurrentIndex(0)
        QTimer.singleShot(50, lambda: self._review._load_path(dataset_path))

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
