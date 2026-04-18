"""PipelinesView — stub; placeholder for future pipeline management UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PipelinesView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel("Pipelines — coming soon")
        lbl.setObjectName("muted")
        layout.addWidget(lbl)
