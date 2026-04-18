"""MainWindow — QMainWindow with top bar, stacked views, status bar."""

from __future__ import annotations
import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from .theme.manager import ThemeManager
from .widgets.pill_tabs import PillTabBar
from .widgets.status_bar import StatusBar
from .widgets.tweaks_panel import TweaksPanel
from .views.review_view import ReviewView
from .views.analyze_view import AnalyzeView
from .views.pipelines_view import PipelinesView


class _BrandMark(QLabel):
    """All-Well brand mark: 2×2 well grid + sparkline overlay, painted."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(28, 28)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        try:
            from .theme.manager import ThemeManager
            t = ThemeManager.instance().tokens
            accent = t["accent"]
            sunk = t["sunk"]
        except Exception:
            accent = "#0E6B52"
            sunk = "#EEE5D4"

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 2×2 well grid
        for r in range(2):
            for c in range(2):
                x = 2 + c * 12
                y = 2 + r * 12
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(sunk))
                p.drawEllipse(x, y, 9, 9)

        # Sparkline
        pen_color = QColor(accent)
        pen_color.setAlpha(220)
        from PySide6.QtGui import QPen
        p.setPen(QPen(pen_color, 1.5))
        pts = [(2, 20), (8, 16), (14, 18), (20, 10), (26, 12)]
        for i in range(len(pts) - 1):
            p.drawLine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        p.end()


class TopBar(QWidget):
    """Top bar with brand, pill tabs, crumb, ✦ tweaks toggle, avatar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # Brand mark
        mark = _BrandMark()
        layout.addWidget(mark)

        # Brand name
        brand = QLabel()
        brand.setTextFormat(Qt.RichText)
        brand.setText('<span style="font-weight:700;font-size:13px;">All</span>'
                      '<span style="font-family:\'Instrument Serif\',Georgia,serif;'
                      'font-style:italic;font-size:13px;font-weight:400;">-Well</span>')
        layout.addWidget(brand)
        layout.addSpacing(22)

        # Pill tabs (Review / Analyze / Pipelines)
        self.pill_tabs = PillTabBar(["Review", "Analyze", "Pipelines"])
        layout.addWidget(self.pill_tabs)
        layout.addStretch()

        # Crumb
        crumb = QLabel('<span style="font-family:monospace;font-size:11px;">'
                       'plate_042 / <b>run-17</b></span>')
        crumb.setObjectName("muted")
        crumb.setTextFormat(Qt.RichText)
        layout.addWidget(crumb)

        # ⌘K command button
        cmd_btn = QPushButton("⌘K")
        cmd_btn.setObjectName("ghost")
        cmd_btn.setFixedHeight(28)
        cmd_btn.setToolTip("Command palette")
        cmd_btn.clicked.connect(self._open_command_palette)
        layout.addWidget(cmd_btn)

        # ✦ Tweaks
        self._tweak_btn = QPushButton("✦")
        self._tweak_btn.setObjectName("tweakToggle")
        self._tweak_btn.setCheckable(True)
        self._tweak_btn.setFixedHeight(28)
        self._tweak_btn.setToolTip("Palette")
        self._tweak_btn.clicked.connect(self._toggle_tweaks)
        layout.addWidget(self._tweak_btn)

        # Avatar
        avatar = QLabel("AW")
        avatar.setObjectName("badge")
        avatar.setFixedSize(26, 26)
        avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)

        self._tweaks_panel: TweaksPanel | None = None

    def _toggle_tweaks(self) -> None:
        if self._tweaks_panel is None:
            self._tweaks_panel = TweaksPanel(self.window())
        if self._tweaks_panel.isVisible():
            self._tweaks_panel.hide()
        else:
            pos = self._tweak_btn.mapToGlobal(
                self._tweak_btn.rect().bottomRight()
            )
            self._tweaks_panel.move(
                pos.x() - self._tweaks_panel.width(), pos.y() + 4
            )
            self._tweaks_panel.show()

    def _open_command_palette(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        QInputDialog.getText(self.window(), "Command palette", "Search commands…")


class MainWindow(QMainWindow):
    """App shell: top bar + stacked views + status bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("All-Well")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        # Top bar as menu widget
        self._top_bar = TopBar()
        self.setMenuWidget(self._top_bar)

        # Stacked widget
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._review = ReviewView()
        self._analyze = AnalyzeView()
        self._pipelines = PipelinesView()

        self._stack.addWidget(self._review)
        self._stack.addWidget(self._analyze)
        self._stack.addWidget(self._pipelines)

        self._top_bar.pill_tabs.tab_changed.connect(self._stack.setCurrentIndex)

        # Status bar
        tm = ThemeManager.instance()
        self._status_bar = StatusBar(tm.tokens["accent"])
        self.setStatusBar(self._status_bar)
        self._status_bar.set_status(
            "Pipeline idle · Loaded dataset plate_042 / run-17 · 96 wells · 48 t · 2 channels"
        )

        # Wire palette changes → repaint manual widgets
        tm.palette_changed.connect(self._on_palette_changed)
        tm._apply()  # apply initial QSS

        # Restore window geometry
        self._settings = QSettings("AllWell", "AllWell")
        self._restore_state()

    def _on_palette_changed(self, key: str) -> None:
        t = ThemeManager.instance().tokens
        self._status_bar.set_dot_color(t["accent"])
        self._review.sidebar.plate_map.apply_palette(
            t["sunk"], t["ink"], t["dark_highlight"]
        )
        self._top_bar._BrandMark if False else None
        self._top_bar.findChild(_BrandMark)
        # Force repaint of painted widgets
        self._top_bar.update()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self._save_state()
        super().closeEvent(event)

    def _save_state(self) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("palette", ThemeManager.instance().palette_key)
        self._review.save_state(self._settings)

    def _restore_state(self) -> None:
        geo = self._settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        palette = self._settings.value("palette", "warm")
        if palette in ("warm", "fluoro", "ivory"):
            ThemeManager.instance().set_palette(palette)
        self._review.restore_state(self._settings)
