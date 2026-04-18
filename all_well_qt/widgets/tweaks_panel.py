"""TweaksPanel — floating popup for live palette switching."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme.manager import ThemeManager
from ..theme.tokens import PALETTES


class TweaksPanel(QFrame):
    """Frameless popup containing palette swatches.

    Shown/hidden by the ✦ toggle button in the top bar.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("tweaksPanel")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hdr = QLabel("PALETTE")
        hdr.setObjectName("section")
        layout.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        palettes = [
            ("warm",   "Warm lab",   ["#F7F2EA", "#0E6B52", "#E25C3A"]),
            ("fluoro", "Fluoro",     ["#0E0F0C", "#C6F24E", "#F05BB5"]),
            ("ivory",  "Ivory mint", ["#F4F1EB", "#115E59", "#F4A87A"]),
        ]
        for col, (key, name, colors) in enumerate(palettes):
            btn_widget = QWidget()
            btn_widget.setCursor(Qt.PointingHandCursor)
            bw_layout = QVBoxLayout(btn_widget)
            bw_layout.setContentsMargins(8, 8, 8, 8)
            bw_layout.setSpacing(6)

            swatches = QWidget()
            sw_layout = QHBoxLayout(swatches)
            sw_layout.setContentsMargins(0, 0, 0, 0)
            sw_layout.setSpacing(3)
            for c in colors:
                dot = QLabel()
                dot.setFixedSize(14, 14)
                dot.setStyleSheet(f"background:{c}; border-radius: 7px;")
                sw_layout.addWidget(dot)
            bw_layout.addWidget(swatches)

            name_lbl = QLabel(name)
            name_lbl.setObjectName("muted")
            name_lbl.setAlignment(Qt.AlignCenter)
            bw_layout.addWidget(name_lbl)

            # highlight current
            is_current = ThemeManager.instance().palette_key == key
            btn_widget.setStyleSheet(
                f"QWidget {{ background: {'var(--sunk)' if is_current else 'transparent'};"
                f"border-radius: 8px; border: {'2px solid #0E6B52' if is_current else '1px solid transparent'}; }}"
            )
            btn_widget.mousePressEvent = (
                lambda event, k=key: self._select(k)  # noqa: E731
            )
            grid.addWidget(btn_widget, 0, col)

        layout.addLayout(grid)
        self.setFixedWidth(260)

    def _select(self, key: str) -> None:
        ThemeManager.instance().set_palette(key)
        self.hide()
