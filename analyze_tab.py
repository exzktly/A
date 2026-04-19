"""Qt compatibility entrypoint for Analyze tab."""

from __future__ import annotations

from analyze_tab_qt import AnalyzeTabQt

DEFAULT_SCHEMA = "experiment:channel:well:fov:timepoint"
DEFAULT_SEP = "_"
SCHEMA_FIELDS = ["experiment", "channel", "well", "fov", "timepoint"]


class AnalyzeTab(AnalyzeTabQt):
    """Backward-compatible Analyze tab name bound to Qt implementation."""


__all__ = [
    "AnalyzeTab",
    "AnalyzeTabQt",
    "DEFAULT_SCHEMA",
    "DEFAULT_SEP",
    "SCHEMA_FIELDS",
]
