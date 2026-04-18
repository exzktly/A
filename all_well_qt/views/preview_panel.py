"""PreviewPanel — right pane: channel/FOV controls + 2×2 montage grid."""

from __future__ import annotations
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..widgets.chip_group import ChipGroup
from ..widgets.field import Field


class MontageTile(QLabel):
    """Single microscopy thumbnail tile with rounded-corner clip."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setObjectName("sunkFrame")
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setText("—")
        self.setStyleSheet("border-radius: 8px; background: #EEE5D4; color: #7C786D;")

    def set_image_array(self, arr: np.ndarray, lut_min: float = 0, lut_max: float = 1) -> None:
        """Display a greyscale float32 array as a pixmap."""
        if arr is None:
            self._show_placeholder()
            return
        arr_norm = np.clip((arr - lut_min) / max(lut_max - lut_min, 1e-6), 0, 1)
        arr_u8 = (arr_norm * 255).astype(np.uint8)
        h, w = arr_u8.shape[:2]
        if arr_u8.ndim == 2:
            img = QImage(arr_u8.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            img = QImage(arr_u8.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img)
        self.setPixmap(
            pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class PreviewPanel(QWidget):
    """Right-side panel: channel/FOV selectors + 2×2 tile grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self._current_well: Optional[str] = None
        self._image_loader = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Head ──────────────────────────────────────────────────────
        head = QWidget()
        head.setObjectName("sidePanel")
        head_layout = QVBoxLayout(head)
        head_layout.setContentsMargins(14, 14, 14, 10)
        head_layout.setSpacing(6)

        title_row = QHBoxLayout()
        self._well_tag = QLabel("No well selected")
        self._well_tag.setObjectName("panelTitle")
        title_row.addWidget(self._well_tag)
        title_row.addStretch()
        self._well_badge = QLabel()
        self._well_badge.setObjectName("badge")
        self._well_badge.hide()
        title_row.addWidget(self._well_badge)
        head_layout.addLayout(title_row)
        layout.addWidget(head)

        # ── Channel chips ─────────────────────────────────────────────
        ch_row = QWidget()
        ch_row.setObjectName("sidePanel")
        ch_layout = QHBoxLayout(ch_row)
        ch_layout.setContentsMargins(14, 4, 14, 4)
        ch_layout.setSpacing(8)

        self._ch_chips = ChipGroup(["GFP", "DAPI", "Merge"])
        self._ch_chips.chip_changed.connect(self._on_channel_changed)
        ch_layout.addWidget(self._ch_chips)
        ch_layout.addStretch()
        layout.addWidget(ch_row)

        # ── LUT / FOV fields ──────────────────────────────────────────
        fields_row = QWidget()
        fields_row.setObjectName("sidePanel")
        fl_layout = QHBoxLayout(fields_row)
        fl_layout.setContentsMargins(14, 2, 14, 8)
        fl_layout.setSpacing(8)

        self._fov_field = Field("fov", "1", width=40)
        fl_layout.addWidget(self._fov_field)

        self._lut_min_field = Field("min", "0", unit="au", width=45)
        fl_layout.addWidget(self._lut_min_field)

        self._lut_max_field = Field("max", "65535", unit="au", width=55)
        fl_layout.addWidget(self._lut_max_field)
        fl_layout.addStretch()
        layout.addWidget(fields_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ── 2×2 Tile grid ─────────────────────────────────────────────
        tile_area = QWidget()
        tile_area.setObjectName("sidePanel")
        tile_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        tl = QGridLayout(tile_area)
        tl.setContentsMargins(10, 10, 10, 10)
        tl.setSpacing(6)

        self._tiles: list[MontageTile] = []
        for row in range(2):
            for col in range(2):
                tile = MontageTile()
                tl.addWidget(tile, row, col)
                self._tiles.append(tile)
        layout.addWidget(tile_area, 1)

    def update_well(self, well_id: Optional[str]) -> None:
        self._current_well = well_id
        if well_id:
            self._well_tag.setText(well_id)
            self._well_badge.setText(well_id)
            self._well_badge.show()
            self._refresh_tiles()
        else:
            self._current_well = None
            self._well_tag.setText("No well selected")
            self._well_badge.hide()
            for tile in self._tiles:
                tile._show_placeholder()

    def _on_channel_changed(self, _: int) -> None:
        self._refresh_tiles()

    def _refresh_tiles(self) -> None:
        """Load FOV thumbnails for the current well + channel, or show placeholders."""
        well = getattr(self, "_current_well", None)
        if not well:
            return

        channel_idx = self._ch_chips.current_index()
        channel = ["GFP", "DAPI", "Merge"][channel_idx]

        # Channel-tinted placeholder colors so the UI gives visual feedback
        # even before a real data directory is loaded.
        ch_colors = {
            "GFP":   ("#C9E4D6", "#0E6B52"),
            "DAPI":  ("#CDE4E0", "#115E59"),
            "Merge": ("#FBD9CE", "#E25C3A"),
        }
        bg, fg = ch_colors.get(channel, ("#EEE5D4", "#7C786D"))

        if hasattr(self, "_image_loader") and self._image_loader is not None:
            try:
                lut_min = float(self._lut_min_field.value or 0)
                lut_max = float(self._lut_max_field.value or 65535)
            except ValueError:
                lut_min, lut_max = 0.0, 65535.0

            try:
                fov_base = int(self._fov_field.value or 1) - 1
            except ValueError:
                fov_base = 0

            for i, tile in enumerate(self._tiles):
                arr = self._image_loader.load_fov(well, channel, fov_base + i)
                if arr is not None:
                    tile.set_image_array(arr, lut_min, lut_max)
                else:
                    tile.setStyleSheet(
                        f"border-radius: 8px; background: {bg}; color: {fg};"
                    )
                    tile.setText(f"{well} · {channel} · FOV {fov_base + i + 1}")
        else:
            # No loader — show channel-tinted placeholder with well/channel label
            for i, tile in enumerate(self._tiles):
                tile.setStyleSheet(
                    f"border-radius: 8px; background: {bg}; color: {fg};"
                )
                tile.setText(f"{well} · {channel} · FOV {i + 1}")

    def set_image_loader(self, loader) -> None:  # noqa: ANN001
        self._image_loader = loader
