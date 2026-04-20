"""Qt/tk value compatibility helpers."""

from __future__ import annotations

from typing import Any


def combo_text(widget: Any, default: str = "") -> str:
    """Return combo-like current text across Qt/tk-style widgets."""
    if widget is None:
        return default
    if hasattr(widget, "currentText"):
        try:
            return str(widget.currentText() or default)
        except Exception:
            return default
    if hasattr(widget, "get"):
        try:
            return str(widget.get() or default)
        except Exception:
            return default
    return default
