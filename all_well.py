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
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
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
        self._theme_combo.addItems(["Dark", "Light"])
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
