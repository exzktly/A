"""RangePair — two ``QLineEdit``s with a separator glyph.

Mockup usage: ``X limits``, ``Y limits`` (separator ``–``) in Limits & Scale,
``Aspect`` (separator ``×``) in Layout. The widget gives the host one signal
when either side commits (Enter or focus-out) so callers can route into a
single setter.

API
---
* ``RangePair(parent=None, *, separator="–", placeholder=("", ""), value=("", ""))``
* ``value() -> (str, str)`` / ``setValue(low, high)``
* ``setPlaceholder(low, high)``
* signal ``valueChanged(low: str, high: str)`` — fires when **either** side
  commits via Enter or focus-out, after the local state is updated.
* ``bindingAdapter()`` — for the ExportStyleSidebar binding pipeline.

Type-conversion is intentionally left to the caller (auto / int / float
/ blank-means-auto are all valid for the mockup's targets). Editors get
``setAlignment(Qt.AlignRight)`` so numeric values right-align like the
mockup's mono ``.input`` fields.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QWidget,
)

import theme  # noqa: E402


class RangePair(QFrame):
    valueChanged = Signal(str, str)

    def __init__(self, parent: QWidget | None = None, *,
                 separator: str = "–",
                 placeholder: tuple[str, str] = ("", ""),
                 value: tuple[str, str] = ("", "")) -> None:
        super().__init__(parent)
        self.setObjectName("RangePair")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.Spacing.xs)

        self._lo = QLineEdit(self)
        self._lo.setObjectName("RangePairInput")
        self._lo.setPlaceholderText(placeholder[0] or "")
        self._lo.setText(value[0] or "")
        self._lo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._sep = QLabel(separator, self)
        self._sep.setObjectName("RangePairSep")
        self._sep.setAlignment(Qt.AlignCenter)

        self._hi = QLineEdit(self)
        self._hi.setObjectName("RangePairInput")
        self._hi.setPlaceholderText(placeholder[1] or "")
        self._hi.setText(value[1] or "")
        self._hi.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(self._lo, 1)
        lay.addWidget(self._sep, 0)
        lay.addWidget(self._hi, 1)

        self._lo.editingFinished.connect(self._emit)
        self._hi.editingFinished.connect(self._emit)

        self.setStyleSheet(self._build_qss())

    # ── API ──────────────────────────────────────────────────────────────
    def value(self) -> tuple[str, str]:
        return self._lo.text(), self._hi.text()

    def setValue(self, low: str = "", high: str = "") -> None:
        if low != self._lo.text():
            self._lo.setText(low or "")
        if high != self._hi.text():
            self._hi.setText(high or "")

    def setPlaceholder(self, low: str, high: str) -> None:
        self._lo.setPlaceholderText(low or "")
        self._hi.setPlaceholderText(high or "")

    def setSeparator(self, glyph: str) -> None:
        self._sep.setText(glyph or "–")

    # ── ExportStyleSidebar binding adapter ───────────────────────────────
    def bindingAdapter(self):
        """Return (getter, setter, change_signal) for the binding pipeline.

        Marshals between the panel's pref dict (which stores tuples / lists)
        and the widget's two strings. Empty strings round-trip as empty.
        """
        return (
            lambda: list(self.value()),
            lambda v: self.setValue(*(v if isinstance(v, (list, tuple)) and len(v) == 2 else ("", ""))),
            self.valueChanged,
        )

    # ── internals ────────────────────────────────────────────────────────
    def _emit(self) -> None:
        lo, hi = self.value()
        self.valueChanged.emit(lo, hi)

    def _build_qss(self) -> str:
        c, t, r = theme.Colors, theme.Typography, theme.Radii
        return f"""
        QFrame#RangePair {{ background: transparent; border: 0; }}
        QLineEdit#RangePairInput {{
            background-color: {c.bg_elevated};
            color: {c.text_primary};
            border: 1px solid {c.border_subtle};
            border-radius: {r.xs}px;
            padding: 4px 8px;
            font-family: {t.family_mono};
            font-size: {t.small_size}px;
        }}
        QLineEdit#RangePairInput:focus {{
            border-color: {c.accent};
            outline: none;
        }}
        QLabel#RangePairSep {{
            color: {c.text_muted};
            font-size: {t.caption_size}px;
            background: transparent;
            border: 0;
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QVBoxLayout

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    host = QWidget()
    host.setWindowTitle("RangePair — demo")
    host.resize(360, 240)
    lay = QVBoxLayout(host)
    lay.setContentsMargins(24, 24, 24, 24)
    lay.setSpacing(12)

    out = QLabel("Edit a field and press Enter or Tab.")
    out.setWordWrap(True)

    lay.addWidget(QLabel("X limits (separator '–', placeholder 'auto'):"))
    rp1 = RangePair(separator="–", placeholder=("auto", "auto"))
    rp1.valueChanged.connect(lambda lo, hi: out.setText(f"X limits → ({lo!r}, {hi!r})"))
    lay.addWidget(rp1)

    lay.addWidget(QLabel("Y limits (separator '–', initial 0..1200):"))
    rp2 = RangePair(separator="–", value=("0", "1200"))
    rp2.valueChanged.connect(lambda lo, hi: out.setText(f"Y limits → ({lo!r}, {hi!r})"))
    lay.addWidget(rp2)

    lay.addWidget(QLabel("Aspect (separator '×', initial 1.618 × 1.000):"))
    rp3 = RangePair(separator="×", value=("1.618", "1.000"))
    rp3.valueChanged.connect(lambda lo, hi: out.setText(f"Aspect → ({lo!r}, {hi!r})"))
    lay.addWidget(rp3)

    lay.addStretch(1)
    lay.addWidget(out)
    host.show()
    _sys.exit(app.exec())
