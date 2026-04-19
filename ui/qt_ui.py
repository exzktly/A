"""Consolidated Qt UI helpers (sections + dialogs) for migrated runtime surfaces."""

from __future__ import annotations

from pathlib import Path


def make_labeled_field(label: str, widget):
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel(label))
    layout.addWidget(widget, stretch=1)
    return row


def make_section(title: str):
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout

    box = QGroupBox(title)
    box.setLayout(QVBoxLayout())
    return box


def pick_directory(parent, *, title: str) -> Path | None:
    from PySide6.QtWidgets import QFileDialog

    chosen = QFileDialog.getExistingDirectory(parent, title)
    return Path(chosen) if chosen else None


def warn(parent, title: str, message: str) -> None:
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.warning(parent, title, message)


def error(parent, title: str, message: str) -> None:
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.critical(parent, title, message)


def modal_note(parent, title: str, message: str) -> None:
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(message))
    btns = QDialogButtonBox(QDialogButtonBox.Ok)
    btns.accepted.connect(dlg.accept)
    lay.addWidget(btns)
    dlg.exec()
