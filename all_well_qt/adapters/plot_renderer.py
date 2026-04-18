"""Adapter: wraps well_viewer analysis modules for PlotWorkspace."""

from __future__ import annotations
from typing import Optional
import numpy as np


class PlotRenderer:
    """Bridges existing matplotlib figure generation to FigureCanvasQTAgg."""

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir

    def set_data_dir(self, path: str) -> None:
        self._data_dir = path

    def render_kinetics(
        self,
        groups: dict,  # {group_id: {"wells": [...], "color": "#…", "name": "…"}}
        metric: str = "Mean",
        normalize: bool = False,
    ) -> Optional[object]:
        """Return a matplotlib Figure or None."""
        if not self._data_dir:
            return None
        try:
            from well_viewer.analysis import build_kinetics_figure  # type: ignore[import]
            return build_kinetics_figure(
                self._data_dir, groups, metric=metric, normalize=normalize
            )
        except Exception:
            return None
