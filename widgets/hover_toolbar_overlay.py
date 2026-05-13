"""HoverToolbarOverlay — show a toolbar only while a host widget is hovered.

Wraps any toolbar widget in a ``QGraphicsOpacityEffect`` and watches a "host"
widget for enter/leave: the toolbar fades to opacity 1 on enter and back to 0
on leave, while always keeping its space in the layout (so nothing jumps).

This is a behaviour wrapper, not a painted widget — no ``paintEvent`` of its
own. Use it for per-plot-card toolbars per the mockup's hover-reveal pattern.

API
---
* ``HoverToolbarOverlay(toolbar, host=None, parent=None, *, rest_opacity=0.0,
  fade_in=120, fade_out=200)``
* ``setHost(widget)`` — the widget whose hover drives the reveal (defaults to
  the toolbar's parent, or the toolbar itself).
* ``reveal()`` / ``conceal()`` — force the state.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import (  # noqa: E402
    QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget  # noqa: E402

import theme  # noqa: E402  (kept for parity; durations could be tokenized later)


class HoverToolbarOverlay(QObject):
    def __init__(self, toolbar: QWidget, host: QWidget | None = None,
                 parent: QObject | None = None, *, rest_opacity: float = 0.0,
                 fade_in: int = 120, fade_out: int = 200) -> None:
        super().__init__(parent or toolbar)
        self._toolbar = toolbar
        self._rest = max(0.0, min(1.0, rest_opacity))
        self._fade_in = int(fade_in)
        self._fade_out = int(fade_out)

        self._effect = QGraphicsOpacityEffect(toolbar)
        self._effect.setOpacity(self._rest)
        toolbar.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._host: QWidget | None = None
        self.setHost(host or toolbar.parentWidget() or toolbar)

    # ── API ──────────────────────────────────────────────────────────────
    def setHost(self, widget: QWidget) -> None:
        if self._host is not None:
            self._host.removeEventFilter(self)
        self._host = widget
        if self._host is not None:
            self._host.setAttribute(Qt.WA_Hover, True)
            self._host.installEventFilter(self)
            # Also follow the toolbar's own hover so it doesn't vanish while
            # the pointer is over it (it may sit outside the host's rect).
            self._toolbar.setAttribute(Qt.WA_Hover, True)
            self._toolbar.installEventFilter(self)

    def reveal(self) -> None:
        self._animate_to(1.0, self._fade_in)

    def conceal(self) -> None:
        self._animate_to(self._rest, self._fade_out)

    # ── internals ────────────────────────────────────────────────────────
    def _animate_to(self, target: float, duration: int) -> None:
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(target)
        self._anim.start()

    def _pointer_inside(self) -> bool:
        from PySide6.QtGui import QCursor
        gp = QCursor.pos()
        for w in (self._host, self._toolbar):
            if w is not None and w.isVisible():
                tl = w.mapToGlobal(w.rect().topLeft())
                br = w.mapToGlobal(w.rect().bottomRight())
                if tl.x() <= gp.x() <= br.x() and tl.y() <= gp.y() <= br.y():
                    return True
        return False

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        et = event.type()
        if et in (QEvent.Enter, QEvent.HoverEnter):
            self.reveal()
        elif et in (QEvent.Leave, QEvent.HoverLeave):
            # Defer slightly so moving host → toolbar doesn't flicker.
            if not self._pointer_inside():
                self.conceal()
        return super().eventFilter(obj, event)


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget as _QW,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("HoverToolbarOverlay — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)
    title = QLabel("HoverToolbarOverlay — hover the card below")
    title.setObjectName("Title")
    title.setWordWrap(True)
    lay.addWidget(title)

    # A mock "plot card": a panel with a toolbar row that only shows on hover.
    card = _QW()
    card.setObjectName("Panel")
    card.setAttribute(Qt.WA_StyledBackground, True)
    cv = QVBoxLayout(card)
    cv.setContentsMargins(theme.Spacing.md, theme.Spacing.md,
                          theme.Spacing.md, theme.Spacing.md)
    body = QLabel("(figure)")
    body.setObjectName("Secondary")
    body.setAlignment(Qt.AlignCenter)
    body.setMinimumHeight(180)
    cv.addWidget(body, 1)
    toolbar = _QW()
    tb = QHBoxLayout(toolbar)
    tb.setContentsMargins(0, 0, 0, 0)
    for name in ("Home", "Pan", "Zoom", "Save"):
        tb.addWidget(QPushButton(name))
    tb.addStretch(1)
    coords = QLabel("x = —  ·  y = —")
    coords.setObjectName("Mono")
    tb.addWidget(coords)
    cv.addWidget(toolbar)
    lay.addWidget(card, 1)

    HoverToolbarOverlay(toolbar, host=card)

    root.resize(520, 360)
    root.show()
    _sys.exit(app.exec())
