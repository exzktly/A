"""Inline icon set + recoloring renderer for the widgets package.

A small set of Lucide-style line glyphs (24×24 viewBox, 2-unit stroke, round
caps) stored as SVG path fragments. ``make_icon`` renders one at an arbitrary
size in an arbitrary token color, device-pixel-ratio aware, with a cache.

This intentionally avoids shipping a binary icon font / SVG asset folder; when
the real Lucide set is bundled later, only ``_GLYPHS`` and ``make_pixmap`` need
to change — ``IconButton`` and callers stay the same.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QByteArray, Qt  # noqa: E402
from PySide6.QtGui import QIcon, QPainter, QPixmap  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

import theme  # noqa: E402

# name -> inner SVG markup (everything between <svg> tags)
_GLYPHS: dict[str, str] = {
    "chevron-down":  '<polyline points="6 9 12 15 18 9"/>',
    "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
    "chevron-left":  '<polyline points="15 18 9 12 15 6"/>',
    "x":             '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "plus":          '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "search":        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "sliders":       ('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
                      '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
                      '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
                      '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
                      '<line x1="17" y1="16" x2="23" y2="16"/>'),
    "home":          ('<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
                      '<polyline points="9 22 9 12 15 12 15 22"/>'),
    "arrow-left":    '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    "arrow-right":   '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "move":          ('<polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/>'
                      '<polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/>'
                      '<line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/>'),
    "zoom-in":       ('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
                      '<line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>'),
    "save":          ('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
                      '<polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>'),
    "download":      ('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                      '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'),
    "more-horizontal": '<circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/><circle cx="5" cy="12" r="1.4"/>',
    "check":         '<polyline points="20 6 9 17 4 12"/>',
    "alert-triangle": ('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
                       '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
    "info":          ('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/>'
                      '<line x1="12" y1="8" x2="12.01" y2="8"/>'),
    "image":         ('<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
                      '<circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>'),
    "grid":          ('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>'
                      '<rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'),
}

AVAILABLE = tuple(sorted(_GLYPHS))

_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</svg>'
)

_PIXMAP_CACHE: dict[tuple, QPixmap] = {}


def _resolve_color(color) -> str:
    """Accept a hex string, a ``theme.Colors`` attribute name, or anything
    QColor understands; return a ``#rrggbb`` string for the SVG."""
    if isinstance(color, str) and not color.startswith("#") and hasattr(theme.Colors, color):
        color = getattr(theme.Colors, color)
    from PySide6.QtGui import QColor
    c = QColor(color)
    return c.name() if c.isValid() else "#E6E9EF"


def make_pixmap(name: str, color, size_px: int, dpr: float = 1.0) -> QPixmap:
    """Render glyph *name* at *size_px* logical px in *color*, dpr-aware."""
    hexc = _resolve_color(color)
    key = (name, hexc, int(size_px), round(float(dpr), 3))
    cached = _PIXMAP_CACHE.get(key)
    if cached is not None:
        return cached
    body = _GLYPHS.get(name, _GLYPHS["alert-triangle"])
    svg = _SVG_TEMPLATE.format(color=hexc, body=body)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    px = max(1, int(round(size_px * dpr)))
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(float(dpr))
    _PIXMAP_CACHE[key] = pm
    return pm


def make_icon(name: str, size_px: int = 16, *,
              normal="text_secondary", active="text_primary",
              checked="accent", disabled="text_faint", dpr: float = 1.0) -> QIcon:
    """A ``QIcon`` with state-dependent token colors:

    Normal/Off → *normal*, Active (hover) → *active*, On (checked) → *checked*,
    Disabled → *disabled*.
    """
    icon = QIcon()
    icon.addPixmap(make_pixmap(name, normal, size_px, dpr), QIcon.Normal, QIcon.Off)
    icon.addPixmap(make_pixmap(name, active, size_px, dpr), QIcon.Active, QIcon.Off)
    icon.addPixmap(make_pixmap(name, checked, size_px, dpr), QIcon.Normal, QIcon.On)
    icon.addPixmap(make_pixmap(name, checked, size_px, dpr), QIcon.Active, QIcon.On)
    icon.addPixmap(make_pixmap(name, checked, size_px, dpr), QIcon.Selected, QIcon.On)
    icon.addPixmap(make_pixmap(name, disabled, size_px, dpr), QIcon.Disabled, QIcon.Off)
    icon.addPixmap(make_pixmap(name, disabled, size_px, dpr), QIcon.Disabled, QIcon.On)
    return icon


if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    host = QWidget()
    host.setWindowTitle("icons — preview")
    outer = QVBoxLayout(host)
    pad = theme.Spacing.lg
    outer.setContentsMargins(pad, pad, pad, pad)
    title = QLabel("Inline icon set")
    title.setObjectName("Title")
    outer.addWidget(title)

    grid_host = QWidget()
    grid = QGridLayout(grid_host)
    grid.setSpacing(theme.Spacing.lg)
    dpr = host.devicePixelRatioF()
    for i, name in enumerate(AVAILABLE):
        cell = QVBoxLayout()
        glyph = QLabel()
        glyph.setPixmap(make_pixmap(name, "text_primary", 20, dpr))
        glyph.setAlignment(Qt.AlignCenter)
        cap = QLabel(name)
        cap.setObjectName("Caption")
        cap.setAlignment(Qt.AlignCenter)
        cell.addWidget(glyph)
        cell.addWidget(cap)
        w = QWidget()
        w.setLayout(cell)
        grid.addWidget(w, i // 5, i % 5)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(grid_host)
    outer.addWidget(scroll, 1)

    host.resize(520, 420)
    host.show()
    _sys.exit(app.exec())
