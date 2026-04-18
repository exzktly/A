"""Field — labeled entry pill (channel, LUT min/max, radius…)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget


class Field(QFrame):
    """A labeled inline entry inside a rounded pill frame.

    Layout: [label] [input] [unit?]
    """

    value_changed = Signal(str)

    def __init__(
        self,
        label: str,
        value: str = "",
        unit: str = "",
        width: int = 60,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sunkFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        lbl = QLabel(label.upper())
        lbl.setObjectName("section")
        layout.addWidget(lbl)

        self._edit = QLineEdit(value)
        self._edit.setObjectName("fieldInput")
        self._edit.setFixedWidth(width)
        self._edit.textChanged.connect(self.value_changed)
        layout.addWidget(self._edit)

        if unit:
            unit_lbl = QLabel(unit)
            unit_lbl.setObjectName("muted")
            layout.addWidget(unit_lbl)

    @property
    def value(self) -> str:
        return self._edit.text()

    @value.setter
    def value(self, v: str) -> None:
        self._edit.setText(v)
