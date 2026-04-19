"""Scatter callback helpers retained for non-UI filename resolution tests.

UI-bound Tk callback code was removed in the PySide6 migration.
"""

from __future__ import annotations

from pathlib import PurePath


def _lookup_filename_from_row_value(value: object) -> str:
    """Extract a basename-like filename token from CSV/table row values."""
    text = str(value or "").strip()
    if not text:
        return ""
    return PurePath(text).name


__all__ = ["_lookup_filename_from_row_value"]
