"""Qt compatibility runtime module replacing legacy Tk runtime."""

from __future__ import annotations

from .runtime_app_qt import WellViewerRuntimeQt


class WellViewerApp(WellViewerRuntimeQt):
    """Backward-compatible runtime class name bound to Qt runtime."""


__all__ = ["WellViewerApp", "WellViewerRuntimeQt"]
