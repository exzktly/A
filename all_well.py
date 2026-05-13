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

        hl.addSpacing(theme_v2.Spacing.md)
        self._dataset_status = StatusDot("neutral")
        hl.addWidget(self._dataset_status)
        self._dataset_chip = QLabel("No dataset")
        self._dataset_chip.setObjectName("Chip")
        self._dataset_chip.setProperty("variant", "muted")
        hl.addWidget(self._dataset_chip)

        hl.addStretch(1)

        self._open_btn = IconButton("home")
        self._open_btn.setToolTip("Open results directory…")
        self._open_btn.clicked.connect(self._open_dataset)
        hl.addWidget(self._open_btn)
        self._help_btn = IconButton("info")
        self._help_btn.setToolTip("All-Well — see design/PORT_PLAN.md")
        hl.addWidget(self._help_btn)

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
        self._wrap_review_load_path()

        self._analyze = AnalyzeTab(
            parent=None,
            on_pipeline_complete=self._on_analyze_pipeline_complete,
        )
        self._nb.addTab(self._analyze, "Analyze")
        self._nb.setCurrentIndex(0)

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
            return
        try:
            p = Path(path)
            name = p.name or str(p)
        except Exception:
            name = str(path)
        self._dataset_chip.setText(name)
        self._dataset_chip.setToolTip(str(path))
        self._dataset_status.setStatus("success")

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
