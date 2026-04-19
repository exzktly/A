"""Qt-first viewer app entry/composition module."""

from __future__ import annotations

from pathlib import Path

from .runtime_app_qt import WellViewerRuntimeQt


class WellViewerApp(WellViewerRuntimeQt):
    """Backward-compatible app class name bound to Qt runtime implementation."""

    def __init__(self, parent=None, data_path: Path | None = None) -> None:
        super().__init__()
        if data_path is not None:
            self._load_path(Path(data_path))


def main(data_path: Path | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    runtime = WellViewerApp(data_path=data_path)
    runtime.widget.show()
    return app.exec()


__all__ = ["WellViewerApp", "main"]
