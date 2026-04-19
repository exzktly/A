from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence


@dataclass(frozen=True)
class FileFilter:
    label: str
    pattern: str


class UIPort(Protocol):
    def ask_directory(self, *, title: str, parent=None) -> Path | None: ...

    def ask_open_file(
        self,
        *,
        title: str,
        parent=None,
        initial_dir: str | None = None,
        filters: Sequence[FileFilter] = (),
    ) -> Path | None: ...

    def ask_save_file(
        self,
        *,
        title: str,
        parent=None,
        default_extension: str = "",
        default_name: str | None = None,
        initial_dir: str | None = None,
        filters: Sequence[FileFilter] = (),
    ) -> Path | None: ...

    def info(self, title: str, message: str, *, parent=None) -> None: ...
    def warn(self, title: str, message: str, *, parent=None) -> None: ...
    def error(self, title: str, message: str, *, parent=None) -> None: ...
    def confirm(self, title: str, message: str, *, parent=None) -> bool: ...

    def invoke_later(self, delay_ms: int, callback: Callable[[], None], *, owner) -> None: ...

    def set_clipboard_text(self, text: str, *, owner) -> None: ...
    def get_clipboard_text(self, *, owner) -> str | None: ...
