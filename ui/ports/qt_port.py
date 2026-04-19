from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from .base import FileFilter


class QtUIPort:
    """PySide6-backed implementation of the UI adapter port."""

    def ask_directory(self, *, title: str, parent=None) -> Path | None:
        from PySide6.QtWidgets import QFileDialog

        chosen = QFileDialog.getExistingDirectory(parent, title)
        return Path(chosen) if chosen else None

    def ask_open_file(
        self,
        *,
        title: str,
        parent=None,
        initial_dir: str | None = None,
        filters: Sequence[FileFilter] = (),
    ) -> Path | None:
        from PySide6.QtWidgets import QFileDialog

        selected, _ = QFileDialog.getOpenFileName(
            parent,
            title,
            initial_dir or "",
            self._qt_filter_string(filters),
        )
        return Path(selected) if selected else None

    def ask_save_file(
        self,
        *,
        title: str,
        parent=None,
        default_extension: str = "",
        default_name: str | None = None,
        initial_dir: str | None = None,
        filters: Sequence[FileFilter] = (),
    ) -> Path | None:
        from PySide6.QtWidgets import QFileDialog

        starting = str(Path(initial_dir or ".") / default_name) if default_name else (initial_dir or "")
        selected, _ = QFileDialog.getSaveFileName(
            parent,
            title,
            starting,
            self._qt_filter_string(filters),
        )
        if not selected:
            return None
        chosen = Path(selected)
        if default_extension and chosen.suffix == "":
            chosen = chosen.with_suffix(default_extension)
        return chosen

    def info(self, title: str, message: str, *, parent=None) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(parent, title, message)

    def warn(self, title: str, message: str, *, parent=None) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(parent, title, message)

    def error(self, title: str, message: str, *, parent=None) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(parent, title, message)

    def confirm(self, title: str, message: str, *, parent=None) -> bool:
        from PySide6.QtWidgets import QMessageBox

        return (
            QMessageBox.question(parent, title, message, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )

    def invoke_later(self, delay_ms: int, callback: Callable[[], None], *, owner) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(delay_ms, callback)

    def set_clipboard_text(self, text: str, *, owner) -> None:
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(text)

    def get_clipboard_text(self, *, owner) -> str | None:
        from PySide6.QtGui import QGuiApplication

        return QGuiApplication.clipboard().text() or None

    @staticmethod
    def _qt_filter_string(filters: Sequence[FileFilter]) -> str:
        if not filters:
            return ""
        return ";;".join(f"{f.label} ({f.pattern})" for f in filters)
