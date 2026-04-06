"""Viewer package app entry/composition module."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from .state import ViewerAppState


class WellViewerApp:
    """Package-facing app class with lazy runtime import."""

    def __init__(self, parent=None, data_path: Path | None = None) -> None:
        self._app_state = ViewerAppState(data_path=Path(data_path) if data_path else None)
        from .runtime_app import WellViewerApp as _RuntimeWellViewerApp

        self._impl = _RuntimeWellViewerApp(parent=parent, data_path=data_path)

    def __getattr__(self, name: str):
        return getattr(self._impl, name)


def main(data_path: Path | None = None) -> None:
    app = WellViewerApp(data_path=data_path)
    app.pack(fill=tk.BOTH, expand=True)
    app._tk_root.mainloop()


__all__ = ["WellViewerApp", "main"]
