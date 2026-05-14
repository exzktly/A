"""PillTabBar — a flat, top-of-canvas tab strip with an accent underline.

Matches the mockup's ``Channel 1 · Channel 2 · + Add`` strip: exclusive,
text-only tabs that get a 2-px accent bottom border when active, plus a
trailing ghost ``+`` button.

API
---
* ``addTab(text) -> int`` / ``removeTab(index)`` / ``count()`` / ``tabText(i)`` /
  ``setTabText(i, text)``
* ``setCurrentIndex(i)`` / ``currentIndex()``
* ``currentChanged(int)`` — active tab changed.
* ``addRequested()`` — the ``+`` button was clicked.

Token-styled; padding/underline are spacing relative (DPI-aware).
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QButtonGroup, QHBoxLayout, QSizePolicy, QToolButton, QWidget,
)

import theme  # noqa: E402


class PillTabBar(QWidget):
    currentChanged = Signal(int)
    addRequested = Signal()

    def __init__(self, parent: QWidget | None = None, *, show_add: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("PillTabBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(theme.Spacing.xs)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._tabs: list[QToolButton] = []
        self._current = -1

        self._add_btn = QToolButton(self)
        self._add_btn.setObjectName("PillTabAdd")
        self._add_btn.setText("+  Add")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setFocusPolicy(Qt.NoFocus)
        self._add_btn.setVisible(show_add)
        self._add_btn.clicked.connect(self.addRequested)

        self._layout.addWidget(self._add_btn)
        self._layout.addStretch(1)

        self._group.idClicked.connect(self._on_clicked)
        self.setStyleSheet(self._build_qss())

    # ── API ──────────────────────────────────────────────────────────────
    def addTab(self, text: str) -> int:
        idx = len(self._tabs)
        btn = QToolButton(self)
        btn.setObjectName("PillTab")
        btn.setText(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        # Insert before the add button + stretch.
        self._layout.insertWidget(self._layout.count() - 2, btn)
        self._group.addButton(btn, idx)
        self._tabs.append(btn)
        if self._current < 0:
            self.setCurrentIndex(0)
        return idx

    def removeTab(self, index: int) -> None:
        if not (0 <= index < len(self._tabs)):
            return
        btn = self._tabs.pop(index)
        self._group.removeButton(btn)
        self._layout.removeWidget(btn)
        btn.deleteLater()
        # Re-id the rest.
        for i, b in enumerate(self._tabs):
            self._group.setId(b, i)
        if not self._tabs:
            self._current = -1
        elif self._current >= len(self._tabs):
            self.setCurrentIndex(len(self._tabs) - 1)
        elif index <= self._current:
            self.setCurrentIndex(max(0, self._current - 1))

    def count(self) -> int:
        return len(self._tabs)

    def tabText(self, index: int) -> str:
        return self._tabs[index].text() if 0 <= index < len(self._tabs) else ""

    def setTabText(self, index: int, text: str) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs[index].setText(text)

    def currentIndex(self) -> int:
        return self._current

    def setCurrentIndex(self, index: int) -> None:
        if not (0 <= index < len(self._tabs)):
            return
        self._tabs[index].setChecked(True)
        if index != self._current:
            self._current = index
            self.currentChanged.emit(index)

    def setAddButtonVisible(self, visible: bool) -> None:
        self._add_btn.setVisible(bool(visible))

    # ── internals ────────────────────────────────────────────────────────
    def _on_clicked(self, idx: int) -> None:
        if idx != self._current:
            self._current = idx
            self.currentChanged.emit(idx)

    def _build_qss(self) -> str:
        c, t = theme.Colors, theme.Typography
        return f"""
        #PillTabBar {{ background: transparent; border-bottom: 1px solid {c.border_subtle}; }}
        #PillTabBar QToolButton#PillTab {{
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            color: {c.text_secondary};
            padding: 7px 12px;
            font-size: {t.small_size}px;
            font-weight: {t.medium};
        }}
        #PillTabBar QToolButton#PillTab:hover {{ color: {c.text_primary}; }}
        #PillTabBar QToolButton#PillTab:checked {{
            color: {c.text_primary};
            border-bottom: 2px solid {c.accent};
        }}
        #PillTabBar QToolButton#PillTabAdd {{
            background: transparent;
            border: none;
            color: {c.text_muted};
            padding: 7px 10px;
            font-size: {t.small_size}px;
            font-weight: {t.medium};
        }}
        #PillTabBar QToolButton#PillTabAdd:hover {{ color: {c.text_primary}; }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("PillTabBar — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)

    title = QLabel("PillTabBar")
    title.setObjectName("Title")
    lay.addWidget(title)

    bar = PillTabBar()
    for name in ("Channel 1", "Channel 2"):
        bar.addTab(name)
    lay.addWidget(bar)

    echo = QLabel("current → Channel 1")
    echo.setObjectName("Secondary")
    lay.addWidget(echo)

    def _add():
        i = bar.addTab(f"Channel {bar.count() + 1}")
        bar.setCurrentIndex(i)

    bar.addRequested.connect(_add)
    bar.currentChanged.connect(lambda i: echo.setText(f"current → {bar.tabText(i)}"))
    lay.addStretch(1)

    root.resize(420, 220)
    root.show()
    _sys.exit(app.exec())
