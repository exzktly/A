"""ThemeManager singleton — owns the live palette and QSS reload."""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from .tokens import PALETTES, DEFAULT_PALETTE
from .qss import build_qss


class ThemeManager(QObject):
    palette_changed = Signal(str)  # palette key e.g. "warm"

    _instance: Optional["ThemeManager"] = None

    def __init__(self, app: QApplication, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._palette_key = DEFAULT_PALETTE
        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            raise RuntimeError("ThemeManager not yet created")
        return cls._instance

    @property
    def palette_key(self) -> str:
        return self._palette_key

    @property
    def tokens(self) -> dict:
        return PALETTES[self._palette_key]

    def set_palette(self, key: str) -> None:
        if key not in PALETTES:
            raise ValueError(f"Unknown palette: {key!r}")
        if key == self._palette_key:
            return
        self._palette_key = key
        self._apply()
        self.palette_changed.emit(key)

    def _apply(self) -> None:
        self._app.setStyleSheet(build_qss(self.tokens))
