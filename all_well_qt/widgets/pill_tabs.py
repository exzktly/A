"""PillTabBar — segmented radio-group pill tab bar."""

from __future__ import annotations
from typing import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class PillTabBar(QWidget):
    """Horizontal pill-style tab bar backed by a QButtonGroup.

    Emits ``tab_changed(index)`` when selection changes.
    """

    tab_changed = Signal(int)

    def __init__(
        self,
        labels: Sequence[str],
        parent: QWidget | None = None,
        object_name: str = "pillRail",
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setObjectName("pillTab")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            self._group.addButton(btn, i)
            layout.addWidget(btn)

        self._group.idClicked.connect(self.tab_changed)

    def current_index(self) -> int:
        return self._group.checkedId()

    def set_current_index(self, index: int) -> None:
        btn = self._group.button(index)
        if btn:
            btn.setChecked(True)
