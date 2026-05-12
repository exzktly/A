"""SavedSelectionsList — a list of saved well selections with condition dots.

Each row: a colour dot (the associated condition), the selection name, and a
right-aligned count chip. A custom ``QStyledItemDelegate`` paints the row; row
height and paddings derive from the font (DPI-aware). Token-styled.

API
---
* ``addEntry(name, color=None, count=0, data=None) -> int``
* ``clear()`` / ``count()`` / ``entryName(i)`` / ``entryData(i)``
* ``setEntries(list_of_(name, color, count[, data]))``
* ``currentName()`` / ``setCurrentIndex(i)``
* ``entryActivated(str)`` — a row was clicked/activated (emits the name).
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QRectF, QSize, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QStandardItem, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView, QListView, QStyle, QStyledItemDelegate,
)

import theme  # noqa: E402

_ROLE_COLOR = Qt.UserRole + 1
_ROLE_COUNT = Qt.UserRole + 2
_ROLE_DATA = Qt.UserRole + 3


class _RowDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        fm = option.fontMetrics
        return QSize(option.rect.width(), max(24, round(fm.height() * 1.9)))

    def paint(self, painter: QPainter, option, index) -> None:
        c = theme.Colors
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(option.rect)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        if selected:
            painter.fillRect(rect, QColor(c.accent_dim))
        elif hovered:
            painter.fillRect(rect, QColor(c.hover))

        fm = option.fontMetrics
        pad = theme.Spacing.md
        dot_d = max(7, round(fm.height() * 0.45))

        # condition dot
        dot_color = index.data(_ROLE_COLOR) or c.text_muted
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(dot_color))
        dot_x = rect.left() + pad
        dot_y = rect.center().y() - dot_d / 2.0
        painter.drawEllipse(QRectF(dot_x, dot_y, dot_d, dot_d))

        # count chip (right side)
        count = index.data(_ROLE_COUNT)
        chip_w = 0.0
        if count is not None:
            txt = str(count)
            tw = fm.horizontalAdvance(txt)
            chip_h = fm.height() + 2
            chip_w = tw + theme.Spacing.md
            chip_rect = QRectF(rect.right() - pad - chip_w,
                               rect.center().y() - chip_h / 2.0, chip_w, chip_h)
            painter.setBrush(QColor(c.panel_elevated))
            painter.setPen(QColor(c.border_subtle))
            painter.drawRoundedRect(chip_rect, theme.Radii.xs, theme.Radii.xs)
            painter.setPen(QColor(c.text_secondary))
            painter.drawText(chip_rect, int(Qt.AlignCenter), txt)
            chip_w += pad

        # name (elided to fit)
        name_left = dot_x + dot_d + theme.Spacing.sm
        name_right = rect.right() - pad - chip_w
        name_rect = QRectF(name_left, rect.top(), max(0.0, name_right - name_left), rect.height())
        name = index.data(Qt.DisplayRole) or ""
        elided = fm.elidedText(str(name), Qt.ElideRight, int(name_rect.width()))
        painter.setPen(QColor(c.text_primary if (selected or hovered) else c.text_secondary))
        painter.drawText(name_rect, int(Qt.AlignVCenter | Qt.AlignLeft), elided)

        painter.restore()


class SavedSelectionsList(QListView):
    entryActivated = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SavedSelectionsList")
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setItemDelegate(_RowDelegate(self))
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(self._build_qss())
        self.clicked.connect(self._on_clicked)
        self.activated.connect(self._on_clicked)

    # ── API ──────────────────────────────────────────────────────────────
    def addEntry(self, name: str, color=None, count: int = 0, data=None) -> int:
        item = QStandardItem(str(name))
        item.setData(QColor(color) if color else QColor(theme.Colors.text_muted), _ROLE_COLOR)
        item.setData(int(count), _ROLE_COUNT)
        item.setData(data, _ROLE_DATA)
        self._model.appendRow(item)
        return self._model.rowCount() - 1

    def setEntries(self, entries) -> None:
        self.clear()
        for e in entries:
            if len(e) == 4:
                self.addEntry(e[0], e[1], e[2], e[3])
            elif len(e) == 3:
                self.addEntry(e[0], e[1], e[2])
            else:
                self.addEntry(e[0])

    def clear(self) -> None:
        self._model.clear()

    def count(self) -> int:
        return self._model.rowCount()

    def entryName(self, index: int) -> str:
        item = self._model.item(index)
        return item.text() if item else ""

    def entryData(self, index: int):
        item = self._model.item(index)
        return item.data(_ROLE_DATA) if item else None

    def currentName(self) -> str:
        idx = self.currentIndex()
        return idx.data(Qt.DisplayRole) or "" if idx.isValid() else ""

    def setCurrentIndex(self, index: int) -> None:  # type: ignore[override]
        if 0 <= index < self._model.rowCount():
            super().setCurrentIndex(self._model.index(index, 0))

    # ── internals ────────────────────────────────────────────────────────
    def _on_clicked(self, index) -> None:
        if index.isValid():
            self.entryActivated.emit(index.data(Qt.DisplayRole) or "")

    def _build_qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        return f"""
        QListView#SavedSelectionsList {{
            background-color: {c.panel};
            border: 1px solid {c.border_subtle};
            border-radius: {r.sm}px;
            outline: 0;
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("SavedSelectionsList — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)

    title = QLabel("SavedSelectionsList")
    title.setObjectName("Title")
    lay.addWidget(title)

    lst = SavedSelectionsList()
    tr = theme.Colors.trace
    lst.setEntries([
        ("Control", tr[0], 6),
        ("Drug A — 1µM", tr[1], 6),
        ("Drug A — 10µM", tr[2], 6),
        ("Drug B — long condition name that should elide nicely", tr[3], 12),
        ("Untreated", theme.Colors.text_muted, 3),
    ])
    lst.setCurrentIndex(1)
    lay.addWidget(lst, 1)

    echo = QLabel("(click a row)")
    echo.setObjectName("Secondary")
    lay.addWidget(echo)
    lst.entryActivated.connect(lambda n: echo.setText(f"activated → {n}"))

    root.resize(380, 340)
    root.show()
    _sys.exit(app.exec())
