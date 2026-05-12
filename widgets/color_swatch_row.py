"""ColorSwatchRow — a curated row of tappable colour swatches.

The mockup never opens a free-form colour dialog; instead you pick from a small
constrained set. The selected swatch gets a 2-px accent ring drawn outside its
fill. Swatch size derives from the font (DPI-aware).

API
---
* ``ColorSwatchRow(colors=None, parent=None)`` — defaults to ``theme.Colors.trace``.
* ``setColors(iterable)`` / ``colors()``
* ``currentColor()`` / ``setCurrentColor(c)`` / ``currentIndex()`` / ``setCurrentIndex(i)``
* ``colorPicked(QColor)`` — emitted when the user picks a swatch.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QRectF, QSize, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QSizePolicy, QWidget  # noqa: E402

import theme  # noqa: E402


class ColorSwatchRow(QWidget):
    colorPicked = Signal(QColor)

    def __init__(self, colors=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ColorSwatchRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._colors = [QColor(c) for c in (colors or theme.Colors.trace)]
        self._current = 0 if self._colors else -1
        self._hover = -1
        self.setStyleSheet("#ColorSwatchRow { background: transparent; }")

    # ── API ──────────────────────────────────────────────────────────────
    def setColors(self, colors) -> None:
        self._colors = [QColor(c) for c in colors if QColor(c).isValid()]
        if self._current >= len(self._colors):
            self._current = len(self._colors) - 1
        self.updateGeometry()
        self.update()

    def colors(self) -> list[QColor]:
        return list(self._colors)

    def currentIndex(self) -> int:
        return self._current

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._colors) and index != self._current:
            self._current = index
            self.update()

    def currentColor(self) -> QColor:
        return QColor(self._colors[self._current]) if 0 <= self._current < len(self._colors) else QColor()

    def setCurrentColor(self, color) -> None:
        target = QColor(color)
        for i, c in enumerate(self._colors):
            if c.rgb() == target.rgb():
                self.setCurrentIndex(i)
                return

    # ── geometry ─────────────────────────────────────────────────────────
    def _swatch(self) -> int:
        return max(16, round(self.fontMetrics().height() * 1.25))

    def _gap(self) -> int:
        return theme.Spacing.sm

    def _ring(self) -> int:
        return max(2, round(self._swatch() * 0.12))

    def _swatch_rect(self, i: int) -> QRectF:
        s = self._swatch()
        g = self._gap()
        r = self._ring()
        x = r + i * (s + g)
        y = (self.height() - s) / 2.0
        return QRectF(x, y, s, s)

    def sizeHint(self) -> QSize:
        s = self._swatch()
        g = self._gap()
        r = self._ring()
        n = max(0, len(self._colors))
        w = 2 * r + n * s + max(0, n - 1) * g
        return QSize(w, s + 2 * r)

    minimumSizeHint = sizeHint

    # ── input ────────────────────────────────────────────────────────────
    def _index_at(self, x: float, y: float) -> int:
        for i in range(len(self._colors)):
            if self._swatch_rect(i).adjusted(-self._gap() / 2, 0, self._gap() / 2, 0).contains(x, y):
                return i
        return -1

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        i = self._index_at(event.position().x(), event.position().y())
        if i >= 0 and i != self._current:
            self._current = i
            self.update()
            self.colorPicked.emit(QColor(self._colors[i]))
        elif i >= 0:
            self.colorPicked.emit(QColor(self._colors[i]))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        i = self._index_at(event.position().x(), event.position().y())
        if i != self._hover:
            self._hover = i
            self.update()

    def leaveEvent(self, _event) -> None:  # noqa: N802
        if self._hover != -1:
            self._hover = -1
            self.update()

    # ── painting ─────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        c = theme.Colors
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        radius = theme.Radii.xs
        for i, col in enumerate(self._colors):
            rect = self._swatch_rect(i)
            p.setPen(QPen(QColor(c.border), 1.0))
            p.setBrush(QColor(col))
            p.drawRoundedRect(rect, radius, radius)
            if i == self._current:
                p.setBrush(Qt.NoBrush)
                ring = self._ring()
                p.setPen(QPen(QColor(c.accent), ring))
                p.drawRoundedRect(
                    rect.adjusted(-ring, -ring, ring, ring),
                    radius + ring, radius + ring,
                )
            elif i == self._hover:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(c.border_strong), max(1.0, self._ring() * 0.7)))
                p.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5),
                                  radius + 1.5, radius + 1.5)
        p.end()


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QFormLayout, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("ColorSwatchRow — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)

    title = QLabel("ColorSwatchRow")
    title.setObjectName("Title")
    lay.addWidget(title)

    form = QFormLayout()
    form.setSpacing(theme.Spacing.md)
    traces = ColorSwatchRow()
    luts = ColorSwatchRow(["#FFFFFF", "#5B9BF8", "#4ADE80", "#F26B6B", "#F5A524"])
    luts.setCurrentIndex(2)
    form.addRow("Trace colour:", traces)
    form.addRow("LUT colour:", luts)
    lay.addLayout(form)

    echo = QLabel("(pick a swatch)")
    echo.setObjectName("Secondary")
    lay.addWidget(echo)
    traces.colorPicked.connect(lambda c: echo.setText(f"trace → {c.name()}"))
    luts.colorPicked.connect(lambda c: echo.setText(f"LUT → {c.name()}"))
    lay.addStretch(1)

    root.resize(360, 200)
    root.show()
    _sys.exit(app.exec())
