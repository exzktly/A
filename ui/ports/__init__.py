"""Temporary UI adapter layer for framework-coupled operations.

Default runtime now prefers Qt-backed dialogs and notifications.
A Tk-backed compatibility port remains available lazily as TkUIPort.
"""

from __future__ import annotations

from .base import FileFilter, UIPort
from .qt_port import QtUIPort

_default_port = QtUIPort()


def get_ui_port() -> UIPort:
    """Return the process-wide default UI port implementation."""
    return _default_port


def __getattr__(name: str):
    if name == "TkUIPort":
        from .tk_port import TkUIPort

        return TkUIPort
    raise AttributeError(name)


__all__ = ["FileFilter", "UIPort", "QtUIPort", "TkUIPort", "get_ui_port"]
