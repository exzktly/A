"""Shared helpers for the ``widgets`` package.

Importing this module also makes the repo root importable so ``import theme``
resolves whether a widget module is imported normally or run directly as
``__main__``.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

import theme  # noqa: E402  (after the sys.path fix above)
from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402

__all__ = [
    "theme", "lerp_color", "with_alpha", "run_demo",
    "install_qss_refresh",
]


def lerp_color(a, b, t: float) -> QColor:
    """Linear-interpolate between two colors (any QColor-constructible input)."""
    a, b = QColor(a), QColor(b)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return QColor(
        round(a.red()   + (b.red()   - a.red())   * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue()  + (b.blue()  - a.blue())  * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def with_alpha(color, alpha: float) -> QColor:
    """Return *color* with its alpha set to *alpha* (0.0–1.0)."""
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def install_qss_refresh(widget, qss_factory) -> None:
    """Wire *widget* to refresh its per-instance stylesheet when the
    application theme changes.

    Widgets in ``widgets/`` set their own QSS in ``__init__`` via
    ``self.setStyleSheet(self._qss())`` — that's load-bearing for
    per-widget style scoping, but it freezes the colour tokens at
    construction time. When a runtime theme switcher rebuilds
    ``QApplication.setStyleSheet(...)``, Qt fires ``QEvent.StyleChange``
    on each widget; this helper installs an event filter that catches
    that event and calls ``widget.setStyleSheet(qss_factory())`` so the
    cached QSS picks up the new tokens.

    Idempotent: calling it twice on the same widget installs only one
    filter (the second is a no-op).
    """
    if getattr(widget, "_qss_refresh_filter_installed", False):
        return

    class _Filter:
        def eventFilter(self, obj, event):  # noqa: N802 — Qt naming
            if event.type() == QEvent.StyleChange:
                try:
                    obj.setStyleSheet(qss_factory())
                except Exception:
                    pass
            return False

    filt = _Filter()
    widget.installEventFilter(filt)
    # Keep the filter alive for as long as the widget is alive.
    widget._qss_refresh_filter = filt
    widget._qss_refresh_filter_installed = True


def run_demo(factory, title: str, *, size=(380, 320)) -> None:
    """Open a small standalone window hosting ``factory()`` with the v2 theme."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())
    w = factory()
    w.setWindowTitle(title)
    if size:
        w.resize(*size)
    w.show()
    app.exec()
