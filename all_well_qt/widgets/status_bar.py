"""StatusBar with a pulsing dot and dataset / selection text."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStatusBar, QWidget


class _PulseDot(QLabel):
    """A small circle whose opacity pulses via a QPropertyAnimation."""

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(8, 8)
        self._opacity = 1.0
        self._update_style()
        self._anim = QPropertyAnimation(self, b"opacity_prop", self)
        self._anim.setDuration(2000)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.25)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def _update_style(self) -> None:
        alpha = int(self._opacity * 255)
        c = QColor(self._color)
        c.setAlpha(alpha)
        self.setStyleSheet(
            f"background-color: {c.name(QColor.HexArgb)};"
            f"border-radius: 4px;"
        )

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, v: float) -> None:
        self._opacity = v
        self._update_style()

    opacity_prop = property(get_opacity, set_opacity)  # type: ignore[assignment]

    # Expose as Qt property for QPropertyAnimation
    from PySide6.QtCore import Property as _Prop
    opacity_prop = _Prop(float, get_opacity, set_opacity)  # type: ignore[assignment]


class StatusBar(QStatusBar):
    def __init__(self, accent_color: str = "#0E6B52", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)

        container = QWidget()
        container.setObjectName("statusContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._dot = _PulseDot(accent_color)
        layout.addWidget(self._dot)

        self._label = QLabel("Ready")
        self._label.setObjectName("muted")
        layout.addWidget(self._label)
        layout.addStretch()

        self.addWidget(container, 1)

    def set_status(self, text: str) -> None:
        self._label.setText(text)

    def set_dot_color(self, color: str) -> None:
        self._dot._color = color
        self._dot._update_style()
