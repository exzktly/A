"""Tab builder modules for each centre-notebook tab.

Each module exposes a single ``build_*_tab(app, parent)`` function that
fills a pre-created QWidget with the controls and figure for that tab.
"""

from PySide6.QtWidgets import QPushButton, QWidget


def _make_action_button(parent: QWidget, *, text: str, command, style: str) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty("variant", "primary")
    btn.clicked.connect(lambda _=False: command())
    return btn


def _make_secondary_button(parent: QWidget, *, text: str, command) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty("variant", "secondary")
    btn.clicked.connect(lambda _=False: command())
    return btn
