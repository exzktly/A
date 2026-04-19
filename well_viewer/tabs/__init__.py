"""Legacy Tk module removed during PySide6 migration: `well_viewer/tabs/__init__.py`."""

from __future__ import annotations


def __getattr__(name: str):
    raise RuntimeError(
        "Legacy Tk surface `well_viewer/tabs/__init__.py` has been removed. "
        "Use the PySide6 runtime modules (`all_well.py`, `analyze_tab_qt.py`, "
        "`well_viewer/runtime_app_qt.py`, `well_viewer/qt_tools.py`)."
    )
