"""Legacy Tk module removed during PySide6 migration: `well_viewer/views/sidebar_view.py`."""

from __future__ import annotations


def __getattr__(name: str):
    raise RuntimeError(
        "Legacy Tk surface `well_viewer/views/sidebar_view.py` has been removed. "
        "Use the PySide6 runtime modules (`all_well.py`, `analyze_tab_qt.py`, "
        "`well_viewer/runtime_app_qt.py`, `well_viewer/qt_tools.py`)."
    )
