"""Runtime exports for the migrated viewer package.

This module intentionally avoids importing legacy Tk runtime modules at
import-time so Qt shells can import well_viewer without Tk dependencies.
"""

from __future__ import annotations

from .runtime_app_qt import WellViewerRuntimeQt


class WellViewerApp(WellViewerRuntimeQt):
    """Qt-first application export retained under the historical name."""


def __getattr__(name: str):
    if name == "LegacyWellViewerApp":
        from .runtime_app import WellViewerApp as _LegacyWellViewerApp

        return _LegacyWellViewerApp
    raise AttributeError(name)


__all__ = ["WellViewerApp", "LegacyWellViewerApp", "WellViewerRuntimeQt"]
