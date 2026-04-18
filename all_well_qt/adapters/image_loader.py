"""ImageLoader adapter — loads FOV thumbnails from the well_viewer image pipeline."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np


class ImageLoader:
    """Wraps well_viewer image-loading functions for use by PreviewPanel.

    Call ``set_data_dir(path)`` after construction (or pass *data_dir* to
    ``__init__``).  Optionally call ``set_in_dir(path)`` for the structured
    in/out directory layout.
    """

    def __init__(self, data_dir: str = "", in_dir: str = "") -> None:
        self._data_dir: Optional[Path] = Path(data_dir) if data_dir else None
        self._in_dir: Optional[Path] = Path(in_dir) if in_dir else None
        self._pipeline_info: dict = {}
        self._fov_tp_extractor = None
        self._fluor_tokens: list[str] = []
        self._smfish_tokens: set[str] = set()
        self._ready = False

    def set_data_dir(self, path: str) -> None:
        self._data_dir = Path(path)
        self._reload_pipeline_info()

    def set_in_dir(self, path: str) -> None:
        self._in_dir = Path(path) if path else None

    def _reload_pipeline_info(self) -> None:
        if not self._data_dir:
            return
        try:
            from well_viewer.viewer_state import read_pipeline_info
            extractor, fluor, smfish, info = read_pipeline_info(
                self._data_dir, logger=None
            )
            self._fov_tp_extractor = extractor
            self._fluor_tokens = list(fluor)
            self._smfish_tokens = smfish
            self._pipeline_info = info
        except Exception:
            pass
        self._ready = True

    def load_fov(
        self,
        well: str,
        channel: str = "GFP",
        fov_index: int = 0,
    ) -> Optional[np.ndarray]:
        """Return a 2-D float32 array (H×W), or None if not available.

        *channel* is matched case-insensitively against the filename token.
        *fov_index* is 0-based; FOVs are sorted lexicographically by their
        key so index 0 is the first discovered FOV.
        """
        if not self._data_dir:
            return None
        try:
            from well_viewer.runtime_app import (
                find_well_images_and_masks,
                open_imgref_as_array,
            )
        except ImportError:
            return None

        try:
            fluor_dict, overlay_dict, mask_dict, tophat_dict = find_well_images_and_masks(
                data_dir=self._data_dir,
                well_label=well,
                fluor_token=channel,
                in_dir=self._in_dir,
                _fov_tp_extractor=self._fov_tp_extractor,
                _pipeline_info=self._pipeline_info,
            )
        except Exception:
            return None

        # Prefer tophat > fluor_raw > overlay for the image shown in Preview
        source = tophat_dict if tophat_dict else fluor_dict
        if not source:
            source = overlay_dict

        if not source:
            return None

        # Sort FOV keys and pick by index
        sorted_keys = sorted(source.keys())
        if fov_index >= len(sorted_keys):
            fov_index = 0
        key = sorted_keys[fov_index]
        ref = source[key]

        try:
            arr = open_imgref_as_array(ref, greyscale=True)
            if arr is None:
                return None
            return arr.astype(np.float32)
        except Exception:
            return None
