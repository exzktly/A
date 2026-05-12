"""StyledSlider — a QSlider with token styling and an accent focus halo.

The groove / filled sub-page / handle are styled from ``theme`` tokens via a
per-widget stylesheet; ``paintEvent`` adds a soft accent ring around the handle
when the slider has keyboard focus (Qt QSS can't draw an outer glow).

Behaves exactly like ``QSlider`` (same API / signals). Defaults to horizontal.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPainter  # noqa: E402
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider  # noqa: E402

import theme  # noqa: E402
from widgets._support import with_alpha  # noqa: E402


class StyledSlider(QSlider):
    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setObjectName("StyledSlider")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self._build_qss())

    def _handle_rect(self):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        return self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self.hasFocus():
            return
        hr = self._handle_rect()
        if hr.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(Qt.NoBrush)
        grow = max(2, round(hr.width() * 0.18))
        p.setPen(with_alpha(theme.Colors.accent, 0.45))
        p.drawEllipse(hr.adjusted(-grow, -grow, grow, grow))

    def _build_qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        # Groove thickness scales modestly with the font for DPI friendliness.
        gh = max(4, round(self.fontMetrics().height() * 0.28))
        hd = max(12, round(self.fontMetrics().height() * 1.0))
        margin = round((hd - gh) / 2)
        return f"""
        #StyledSlider::groove:horizontal {{
            height: {gh}px; background: {c.border_subtle}; border-radius: {gh // 2}px;
        }}
        #StyledSlider::sub-page:horizontal {{
            background: {c.accent}; border-radius: {gh // 2}px;
        }}
        #StyledSlider::add-page:horizontal {{
            background: {c.border_subtle}; border-radius: {gh // 2}px;
        }}
        #StyledSlider::handle:horizontal {{
            width: {hd}px; height: {hd}px; margin: -{margin}px 0;
            background: {c.panel_elevated};
            border: 2px solid {c.rail};
            border-radius: {hd // 2}px;
        }}
        #StyledSlider::handle:horizontal:hover {{ background: {c.hover}; }}
        #StyledSlider::handle:horizontal:pressed {{ background: {c.active}; }}
        #StyledSlider::groove:vertical {{
            width: {gh}px; background: {c.border_subtle}; border-radius: {gh // 2}px;
        }}
        #StyledSlider::sub-page:vertical {{
            background: {c.accent}; border-radius: {gh // 2}px;
        }}
        #StyledSlider::handle:vertical {{
            width: {hd}px; height: {hd}px; margin: 0 -{margin}px;
            background: {c.panel_elevated}; border: 2px solid {c.rail};
            border-radius: {hd // 2}px;
        }}
        #StyledSlider:disabled {{ }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout,
        QWidget as _QW,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("StyledSlider — demo")
    pad = theme.Spacing.lg
    outer = QVBoxLayout(root)
    outer.setContentsMargins(pad, pad, pad, pad)
    outer.setSpacing(theme.Spacing.md)

    title = QLabel("StyledSlider")
    title.setObjectName("Title")
    outer.addWidget(title)

    form = QFormLayout()
    form.setSpacing(theme.Spacing.md)

    s1 = StyledSlider()
    s1.setRange(0, 100)
    s1.setValue(40)
    s2 = StyledSlider()
    s2.setRange(0, 100)
    s2.setValue(72)
    s3 = StyledSlider()
    s3.setRange(0, 100)
    s3.setValue(20)
    s3.setEnabled(False)

    val_lbl = QLabel("40")
    val_lbl.setObjectName("Mono")
    row = QHBoxLayout()
    row.addWidget(s1, 1)
    row.addWidget(val_lbl)
    form.addRow("Threshold:", row)
    form.addRow("Opacity:", s2)
    form.addRow("Disabled:", s3)
    outer.addLayout(form)

    s1.valueChanged.connect(lambda v: val_lbl.setText(str(v)))
    outer.addStretch(1)

    root.resize(380, 240)
    root.show()
    _sys.exit(app.exec())
