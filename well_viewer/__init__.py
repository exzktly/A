"""Compatibility exports for viewer package-style imports."""

try:
    from .app import WellViewerApp
except (ImportError, ModuleNotFoundError):
    WellViewerApp = None  # type: ignore[assignment,misc]

__all__ = ["WellViewerApp"]
