"""PreviewStrip — inline mini-preview row for the Properties → Lines & Markers section.

Mockup: a small framed strip showing a representative polyline + markers, live-
synced to the section's current line-width / marker-size / colour controls.
Used as a glance preview without making the user open the figure.

Custom-painted (no SVG bundling needed); ~36 px tall, full container width.
Idempotent ``setStyle()`` — call with any subset of the keyword args.

API
---
* ``PreviewStrip(parent=None)``
* ``setStyle(*, color=None, line_width=None, marker_size=None, marker_edge=None, marker=True, dashed=False)``
* read-only properties: ``line_width``, ``marker_size``, ``color``
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, QSize  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPainterPath  # noqa: E402
from PySide6.QtWidgets import QFrame, QSizePolicy  # noqa: E402

import theme  # noqa: E402


class PreviewStrip(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PreviewStrip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Roughly 3 lines of body text — matches the architecture's
        # fontMetrics-derived sizing rule (§7) so the strip scales at
        # 1×/1.5×/2× displays.
        self.setFixedHeight(max(36, self.fontMetrics().height() * 3))

        self._color = QColor(theme.Colors.trace[0])
        self._line_width = 1.8
        self._marker_size = 5.0
        self._marker_edge = 0.8
        self._marker = True
        self._dashed = False

        self.setStyleSheet(self._build_qss())

    # ── API ──────────────────────────────────────────────────────────────
    def setStyle(self, *, color=None, line_width=None, marker_size=None,
                 marker_edge=None, marker=None, dashed=None) -> None:
        if color is not None:
            qc = QColor(color) if not isinstance(color, QColor) else color
            if qc.isValid():
                self._color = qc
        if line_width is not None:
            self._line_width = max(0.0, float(line_width))
        if marker_size is not None:
            self._marker_size = max(0.0, float(marker_size))
        if marker_edge is not None:
            self._marker_edge = max(0.0, float(marker_edge))
        if marker is not None:
            self._marker = bool(marker)
        if dashed is not None:
            self._dashed = bool(dashed)
        self.update()

    @property
    def line_width(self) -> float:
        return self._line_width

    @property
    def marker_size(self) -> float:
        return self._marker_size

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    # ── paint ────────────────────────────────────────────────────────────
    def sizeHint(self) -> QSize:  # noqa: N802
        fm = self.fontMetrics()
        return QSize(fm.averageCharWidth() * 28, max(36, fm.height() * 3))

    def paintEvent(self, ev):  # noqa: N802
        super().paintEvent(ev)
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            inner = self.contentsRect().adjusted(10, 10, -10, -10)
            if inner.width() <= 1 or inner.height() <= 1:
                return

            # zig-zag polyline approximating the mockup sample.
            pts = []
            base_y = inner.center().y()
            amp = inner.height() / 4.0
            steps = 8
            xs = [inner.left() + i * inner.width() / (steps - 1) for i in range(steps)]
            ys_pattern = [0.6, -0.2, -0.7, -0.4, -0.95, -0.3, -0.55, -0.85]
            for x, k in zip(xs, ys_pattern):
                pts.append((x, base_y + k * amp))

            pen = QPen(self._color)
            pen.setWidthF(max(0.5, self._line_width))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            if self._dashed:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            path = QPainterPath()
            path.moveTo(pts[0][0], pts[0][1])
            for x, y in pts[1:]:
                path.lineTo(x, y)
            p.drawPath(path)

            if self._marker and self._marker_size > 0:
                fill = QBrush(self._color)
                edge = QPen(QColor(theme.Colors.panel))
                edge.setWidthF(max(0.0, self._marker_edge))
                p.setBrush(fill)
                p.setPen(edge if self._marker_edge > 0 else Qt.NoPen)
                # Draw markers on every other point to match the mockup density.
                r = self._marker_size / 2.0
                for i, (x, y) in enumerate(pts):
                    if i % 2 == 1:
                        p.drawEllipse(int(x - r), int(y - r),
                                      int(self._marker_size),
                                      int(self._marker_size))
        finally:
            p.end()

    def _build_qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        return f"""
        QFrame#PreviewStrip {{
            background-color: {c.panel};
            border: 1px solid {c.border_subtle};
            border-radius: {r.sm}px;
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    host = QWidget()
    host.setWindowTitle("PreviewStrip — demo")
    host.resize(420, 240)
    lay = QVBoxLayout(host)
    lay.setContentsMargins(24, 24, 24, 24)
    lay.setSpacing(12)

    strip = PreviewStrip(host)
    lay.addWidget(strip)

    def _row(label_text, slider):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(100)
        row.addWidget(lbl)
        row.addWidget(slider, 1)
        return row

    lw = QSlider(Qt.Horizontal); lw.setRange(0, 60); lw.setValue(18)
    lw.valueChanged.connect(lambda v: strip.setStyle(line_width=v / 10.0))
    lay.addLayout(_row("Line width", lw))

    ms = QSlider(Qt.Horizontal); ms.setRange(0, 28); ms.setValue(10)
    ms.valueChanged.connect(lambda v: strip.setStyle(marker_size=v / 2.0))
    lay.addLayout(_row("Marker size", ms))

    me = QSlider(Qt.Horizontal); me.setRange(0, 30); me.setValue(8)
    me.valueChanged.connect(lambda v: strip.setStyle(marker_edge=v / 10.0))
    lay.addLayout(_row("Marker edge", me))

    btns = QHBoxLayout()
    for token, label in (("trace_1", "Blue"), ("trace_2", "Red"),
                         ("trace_3", "Green"), ("trace_4", "Amber")):
        b = QPushButton(label)
        b.clicked.connect(lambda _=False, t=token: strip.setStyle(color=getattr(theme.Colors, t)))
        btns.addWidget(b)
    dashed = QPushButton("Toggle dashed")
    dashed.setCheckable(True)
    dashed.toggled.connect(lambda on: strip.setStyle(dashed=on))
    btns.addWidget(dashed)
    lay.addLayout(btns)
    lay.addStretch(1)

    host.show()
    _sys.exit(app.exec())
