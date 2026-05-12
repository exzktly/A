"""ToggleSwitch — an animated on/off switch that is a drop-in for QCheckBox.

Subclasses ``QAbstractButton`` (which IS-A ``QWidget``) so it inherits
``isChecked()`` / ``setChecked()`` / ``toggled(bool)`` / ``text()`` with
exactly QCheckBox semantics. The knob slides with a short animation; the track
color cross-fades between the elevated-control fill and the accent.

Styled entirely from ``theme`` tokens. The control's size derives from the
widget font metrics, so it scales with DPI / font scaling.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import (  # noqa: E402
    Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QPainter  # noqa: E402
from PySide6.QtWidgets import QAbstractButton, QWidget  # noqa: E402

import theme  # noqa: E402
from widgets._support import lerp_color, with_alpha  # noqa: E402


class ToggleSwitch(QAbstractButton):
    """A sliding boolean toggle. Emits ``toggled(bool)`` like ``QCheckBox``."""

    # Re-declared for editor discoverability; QAbstractButton already provides it.
    toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None, *, checked: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("ToggleSwitch")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)

        self._pos = 1.0 if checked else 0.0  # 0 = off, 1 = on
        if checked:
            self.setChecked(True)

        self._anim = QPropertyAnimation(self, b"knobPosition", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        # QAbstractButton.toggled fires on every state change (user or programmatic).
        super().toggled.connect(self._animate_to_state)

    # ── animated property ────────────────────────────────────────────────
    def _get_knob_position(self) -> float:
        return self._pos

    def _set_knob_position(self, value: float) -> None:
        self._pos = value
        self.update()

    knobPosition = Property(float, _get_knob_position, _set_knob_position)

    def _animate_to_state(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    # ── sizing (font-relative → DPI aware) ───────────────────────────────
    def _track_size(self) -> QSize:
        h = max(16, self.fontMetrics().height())
        return QSize(round(h * 1.85), h)

    def sizeHint(self) -> QSize:
        return self._track_size()

    def minimumSizeHint(self) -> QSize:
        return self._track_size()

    # ── painting ─────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:
        c = theme.Colors
        ts = self._track_size()
        w, h = ts.width(), ts.height()
        x0 = (self.width() - w) / 2.0
        y0 = (self.height() - h) / 2.0
        radius = h / 2.0

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        enabled = self.isEnabled()
        off_fill = QColor(c.panel if not enabled else c.panel_elevated)
        on_fill = QColor(c.accent_dim if not enabled else c.accent)
        track_fill = lerp_color(off_fill, on_fill, self._pos)
        track_border = lerp_color(QColor(c.border), QColor(c.accent), self._pos)

        track_rect = QRectF(x0, y0, w, h)
        p.setPen(track_border)
        p.setBrush(track_fill)
        p.drawRoundedRect(track_rect, radius, radius)

        margin = max(1.5, h * 0.13)
        knob_d = h - 2.0 * margin
        knob_x = x0 + margin + (w - 2.0 * margin - knob_d) * self._pos
        knob_y = y0 + margin
        knob_color = lerp_color(QColor(c.text_secondary), QColor(c.accent_fg), self._pos)
        if not enabled:
            knob_color = QColor(c.text_muted)
        p.setPen(Qt.NoPen)
        p.setBrush(knob_color)
        p.drawEllipse(QRectF(knob_x, knob_y, knob_d, knob_d))

        if self.hasFocus():
            grow = max(1.0, h * 0.12)
            p.setBrush(Qt.NoBrush)
            p.setPen(with_alpha(c.accent, 0.55))
            p.drawRoundedRect(
                track_rect.adjusted(-grow, -grow, grow, grow),
                radius + grow, radius + grow,
            )


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QFormLayout, QLabel, QVBoxLayout, QWidget as _QW,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("ToggleSwitch — demo")
    outer = QVBoxLayout(root)
    outer.setContentsMargins(theme.Spacing.lg, theme.Spacing.lg,
                             theme.Spacing.lg, theme.Spacing.lg)
    title = QLabel("ToggleSwitch")
    title.setObjectName("Title")
    outer.addWidget(title)

    form = QFormLayout()
    form.setSpacing(theme.Spacing.md)
    on = ToggleSwitch(checked=True)
    off = ToggleSwitch()
    disabled_on = ToggleSwitch(checked=True)
    disabled_on.setEnabled(False)
    disabled_off = ToggleSwitch()
    disabled_off.setEnabled(False)
    form.addRow("On by default:", on)
    form.addRow("Off by default:", off)
    form.addRow("Disabled (on):", disabled_on)
    form.addRow("Disabled (off):", disabled_off)
    outer.addLayout(form)

    echo = QLabel("toggled → (interact above)")
    echo.setObjectName("Secondary")
    outer.addWidget(echo)
    on.toggled.connect(lambda v: echo.setText(f"'On by default' toggled → {v}"))
    off.toggled.connect(lambda v: echo.setText(f"'Off by default' toggled → {v}"))
    outer.addStretch(1)

    root.resize(360, 280)
    root.show()
    _sys.exit(app.exec())
