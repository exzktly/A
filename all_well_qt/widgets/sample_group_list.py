"""Sample group list — scrollable rows of replicate-set cards."""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SampleGroupRow(QFrame):
    """One row: colored dot · name · count · ··· menu."""

    rename_requested = Signal(str)   # group_id
    delete_requested = Signal(str)   # group_id
    clicked = Signal(str)            # group_id

    def __init__(
        self,
        group_id: str,
        name: str,
        color: str,
        count: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.group_id = group_id
        self.setObjectName("groupRow")
        self.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PointingHandCursor)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            f"background: {color}; border-radius: 7px;"
            f"border: 2px solid {_soften(color)};"
        )
        layout.addWidget(dot)

        self._name_lbl = QLabel(name)
        layout.addWidget(self._name_lbl)
        layout.addStretch()

        self._count_lbl = QLabel(f"{count}w")
        self._count_lbl.setObjectName("muted")
        layout.addWidget(self._count_lbl)

        more = QPushButton("···")
        more.setObjectName("ghost")
        more.setFixedSize(28, 24)
        more.clicked.connect(self._show_menu)
        layout.addWidget(more)

        self._color = color
        self._more_btn = more

    def update_count(self, count: int) -> None:
        self._count_lbl.setText(f"{count}w")

    def _show_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("Rename…", lambda: self.rename_requested.emit(self.group_id))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self.delete_requested.emit(self.group_id))
        menu.exec(self._more_btn.mapToGlobal(self._more_btn.rect().bottomLeft()))

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        self.clicked.emit(self.group_id)
        super().mousePressEvent(event)


def _soften(hex_color: str) -> str:
    c = QColor(hex_color)
    c.setAlpha(64)
    return c.name(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor.HexArgb)


class SampleGroupList(QWidget):
    """Scrollable list of SampleGroupRow cards with a header and "+ New" button."""

    group_selected = Signal(str)
    new_group_requested = Signal()
    group_renamed = Signal(str, str)   # (group_id, new_name)
    group_deleted = Signal(str)        # group_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setObjectName("sidePanel")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(10, 8, 10, 6)

        title = QLabel("Sample groups")
        title.setObjectName("panelTitle")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        new_btn = QPushButton("+ New")
        new_btn.setObjectName("ghost")
        new_btn.clicked.connect(self.new_group_requested)
        hdr_layout.addWidget(new_btn)
        outer.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("card")
        sep.setFixedHeight(1)
        outer.addWidget(sep)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(8, 6, 8, 6)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()

        scroll.setWidget(self._container)
        outer.addWidget(scroll, 1)

        self._rows: dict[str, SampleGroupRow] = {}

    def add_group(
        self, group_id: str, name: str, color: str, count: int = 0
    ) -> SampleGroupRow:
        row = SampleGroupRow(group_id, name, color, count)
        row.rename_requested.connect(self._on_rename)
        row.delete_requested.connect(self._on_delete)
        row.clicked.connect(self.group_selected)
        # Insert before stretch
        idx = self._list_layout.count() - 1
        self._list_layout.insertWidget(idx, row)
        self._rows[group_id] = row
        return row

    def remove_group(self, group_id: str) -> None:
        row = self._rows.pop(group_id, None)
        if row:
            self._list_layout.removeWidget(row)
            row.deleteLater()

    def update_count(self, group_id: str, count: int) -> None:
        row = self._rows.get(group_id)
        if row:
            row.update_count(count)

    def clear(self) -> None:
        for row in list(self._rows.values()):
            self._list_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

    def _on_rename(self, group_id: str) -> None:
        from PySide6.QtWidgets import QInputDialog
        row = self._rows.get(group_id)
        if not row:
            return
        name, ok = QInputDialog.getText(
            self, "Rename group", "New name:", text=row._name_lbl.text()
        )
        if ok and name.strip():
            row._name_lbl.setText(name.strip())
            self.group_renamed.emit(group_id, name.strip())

    def _on_delete(self, group_id: str) -> None:
        self.remove_group(group_id)
        self.group_deleted.emit(group_id)
