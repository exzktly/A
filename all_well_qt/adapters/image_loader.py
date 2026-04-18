"""Adapter: wraps well_viewer/loaders/* for use by PreviewPanel."""

from __future__ import annotations
from typing import Optional
import numpy as np


class ImageLoader:
    """Thin wrapper around the existing loader modules.

    Usage::
        loader = ImageLoader(data_dir)
        arr = loader.load_fov(well="A01", channel="GFP", fov=0)
    """

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir

    def set_data_dir(self, path: str) -> None:
        self._data_dir = path

    def load_fov(
        self,
        well: str,
        channel: str = "GFP",
        fov: int = 0,
    ) -> Optional[np.ndarray]:
        """Return a 2-D float32 array or None if not available."""
        if not self._data_dir:
            return None
        try:
            from well_viewer.loaders import load_single_fov  # type: ignore[import]
            return load_single_fov(self._data_dir, well, channel, fov)
        except Exception:
            return None
