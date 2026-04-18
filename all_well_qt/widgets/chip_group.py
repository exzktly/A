"""ChipGroup — compact segmented button group for metric toggles."""

from __future__ import annotations
from typing import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class ChipGroup(QWidget):
    """Tighter variant of PillTabBar for metric chips (Mean/Median/etc.)."""

    chip_changed = Signal(int)

    def __init__(
        self,
        labels: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chipRail")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setObjectName("chip")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            self._group.addButton(btn, i)
            layout.addWidget(btn)

        self._group.idClicked.connect(self.chip_changed)

    def current_index(self) -> int:
        return self._group.checkedId()

    def current_label(self) -> str:
        btn = self._group.checkedButton()
        return btn.text() if btn else ""
