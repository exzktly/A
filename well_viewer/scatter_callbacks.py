"""Scatter plot click handlers and single-cell image viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from well_viewer.image_resolver import (
    normalize_row_filename,
    resolve_filename_candidates,
)

if TYPE_CHECKING:
    from .runtime_app import WellViewerApp


class ScatterCellViewer(QDialog):
    """Modal dialog for viewing a single cell's fluorescence images.

    Shows one channel at a time, cropped to the cell's boundaries from the mask.
    Uses filename and nuclear_id from CSV to locate images.
    """

    def __init__(
        self,
        parent,
        app: "WellViewerApp",
        well_label: str,
        filename: str,
        nuclear_id: str,
        row_idx: int,
    ):
        super().__init__(parent)
        self.setWindowTitle("Cell Viewer - Scatter Plot")
        self.resize(600, 650)
        self.setModal(True)

        self.app = app
        self.well_label = well_label
        self.filename = normalize_row_filename(filename)
        self.nuclear_id = nuclear_id
        self.row_idx = row_idx

        self._cell_bounds: Optional[Tuple[int, int, int, int]] = None
        self._cell_images: dict[str, Optional] = {}
        self._cell_outline_mask = None
        self._current_channel = None
        self._current_lut: Tuple[float, float] = (0.0, 100.0)
        self._channel_luts: dict[str, Tuple[float, float]] = {}
        self._debug_lines: list[str] = []
        self._pixmap_cache: Optional[QPixmap] = None

        self._build_ui()
        self._load_cell_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 10)

        self._title_label = QLabel(f"Cell Viewer: {self.well_label}")
        tfont = self._title_label.font()
        tfont.setBold(True)
        self._title_label.setFont(tfont)
        self._title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title_label)

        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Channel:"))
        self._channel_dropdown = QComboBox()
        self._channel_dropdown.setEditable(False)
        self._channel_dropdown.currentIndexChanged.connect(self._on_channel_changed)
        ctrl_row.addWidget(self._channel_dropdown)
        ctrl_row.addStretch(1)
        layout.addLayout(ctrl_row)

        self._img_label = QLabel("Loading...")
        self._img_label.setAlignment(Qt.AlignCenter)
        self._img_label.setMinimumSize(300, 300)
        layout.addWidget(self._img_label, 1)

        lut_row = QHBoxLayout()
        lut_row.addWidget(QLabel("LUT min:"))
        self._lut_min_edit = QLineEdit("0")
        self._lut_min_edit.setFixedWidth(70)
        self._lut_min_edit.editingFinished.connect(self._on_lut_change)
        lut_row.addWidget(self._lut_min_edit)
        lut_row.addSpacing(10)
        lut_row.addWidget(QLabel("max:"))
        self._lut_max_edit = QLineEdit("100")
        self._lut_max_edit.setFixedWidth(70)
        self._lut_max_edit.editingFinished.connect(self._on_lut_change)
        lut_row.addWidget(self._lut_max_edit)
        auto_btn = QPushButton("Auto")
        auto_btn.clicked.connect(self._auto_lut)
        lut_row.addWidget(auto_btn)
        lut_row.addStretch(1)
        layout.addLayout(lut_row)

        diag_group = QGroupBox("Diagnostics")
        diag_layout = QVBoxLayout(diag_group)
        self._debug_text = QTextEdit()
        self._debug_text.setReadOnly(True)
        self._debug_text.setMinimumHeight(140)
        diag_layout.addWidget(self._debug_text)
        layout.addWidget(diag_group)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_channel and self._cell_images.get(self._current_channel) is not None:
            self._display_current_image()

    def _debug(self, message: str) -> None:
        line = str(message)
        self._debug_lines.append(line)
        if getattr(self, "_debug_text", None) is not None:
            self._debug_text.append(line)

    @staticmethod
    def _row_dict_at(rows, idx: int) -> dict:
        """Return row ``idx`` as a plain ``{column: value}`` dict.

        ``app._get_rows`` returns a ``list[dict]`` in the scalar code path and
        a ``pandas.DataFrame`` once the DataFrame migration lands; positional
        access on a DataFrame (``df[idx]``) is a *column* lookup, which raised
        ``KeyError`` here and made the cell-image popup vanish. Accept either.
        """
        if hasattr(rows, "iloc"):  # pandas DataFrame
            return dict(rows.iloc[idx])
        return rows[idx]

    def _load_cell_data(self) -> None:
        """Load cell data: find images using filename, get cell bounds from mask.

        Any unexpected failure is shown in the diagnostics panel rather than
        propagating — the dialog must always appear so the user can see *why*
        a cell image could not be loaded.
        """
        try:
            self._load_cell_data_impl()
        except Exception as exc:  # noqa: BLE001
            import traceback
            self._debug(f"Unexpected error while loading cell data: {exc!r}")
            self._debug(traceback.format_exc())
            try:
                self._img_label.setText(f"Error loading cell: {exc}")
            except Exception:
                pass

    def _load_cell_data_impl(self) -> None:
        self._channel_luts = {}
        self._cell_outline_mask = None
        self._debug_lines = []
        if getattr(self, "_debug_text", None) is not None:
            self._debug_text.clear()
        self._debug(f"well_label={self.well_label!r}, row_idx={self.row_idx}, filename={self.filename!r}, nuclear_id={self.nuclear_id!r}")
        try:
            nuclear_id = int(float(self.nuclear_id))
        except (ValueError, TypeError):
            self._img_label.setText("Invalid nuclear_id")
            self._debug("Failed to parse nuclear_id as int.")
            return
        self._debug(f"parsed_nuclear_id={nuclear_id}")

        if self.well_label not in getattr(self.app, "_well_paths", {}):
            self._img_label.setText(f"Well {self.well_label} is no longer loaded")
            self._debug(f"well_label not in app._well_paths: {self.well_label!r}")
            return

        rows = self.app._get_rows(self.well_label)
        if not (0 <= self.row_idx < len(rows)):
            self._img_label.setText("Invalid row index")
            self._debug(f"row_idx out of bounds: row_idx={self.row_idx}, rows={len(rows)}")
            return

        row = self._row_dict_at(rows, self.row_idx)
        self._nuclear_token = str(row.get("channel") or "").strip()
        self._debug(f"csv.channel={self._nuclear_token!r}")
        self._debug(f"fluor channels to probe={sorted(self.app._fluor_channels)!r}")

        mask_arr, mask_path = self._load_output_image_by_filename("mask")
        self._cell_bounds = self._get_cell_bounds(mask_arr, nuclear_id, padding_px=25)
        if not self._cell_bounds:
            self._img_label.setText(f"Cell {nuclear_id} not found in mask")
            self._debug("No bounds found for requested nuclear_id.")
            return
        self._debug(f"cell_bounds={self._cell_bounds}")
        self._debug(f"mask_path_for_bounds={mask_path}")

        try:
            import numpy as np

            y_min, x_min, y_max, x_max = self._cell_bounds
            mask_crop = np.asarray(mask_arr)[y_min:y_max, x_min:x_max]
            cell_mask = mask_crop == nuclear_id
            self._cell_outline_mask = self._compute_outline_mask(cell_mask)
        except Exception as e:
            self._cell_outline_mask = None
            self._debug(f"failed to compute cell outline mask: {e!r}")

        for ch in sorted(self.app._fluor_channels):
            arr = self._load_and_crop_channel(ch)
            if arr is not None:
                self._cell_images[ch] = arr

        nuc_key = self._nuclear_token.lower() if self._nuclear_token else "nuclear_fluor"
        arr = self._load_and_crop_nuclear()
        if arr is not None:
            self._cell_images[nuc_key] = arr

        arr = self._load_and_crop_channel("mask")
        if arr is not None:
            self._cell_images["nuclear"] = arr

        available_channels = [ch for ch in sorted(self.app._fluor_channels) if self._cell_images.get(ch) is not None]
        if nuc_key in self._cell_images and nuc_key not in available_channels:
            available_channels.append(nuc_key)
        if "nuclear" in self._cell_images:
            available_channels.append("nuclear")

        self._channel_dropdown.blockSignals(True)
        self._channel_dropdown.clear()
        self._channel_dropdown.addItems(available_channels)
        self._channel_dropdown.blockSignals(False)

        if available_channels:
            self._channel_dropdown.setCurrentIndex(0)
            self._on_channel_changed()
        else:
            self._img_label.setText("No images could be loaded")
            self._debug("No channels were successfully loaded.")

    def _load_output_image_by_filename(self, image_type: str):
        """Load a mask or overlay from the output zip via canonical filename resolver."""
        try:
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.data_loading import extract_well_token
            from well_viewer.image_discovery import (
                ImgRef,
                find_out_well_zips_in_dir,
                find_plain_well_zips_in_dir,
                find_well_zips_in_dir,
                open_imgref_as_array,
            )

            pipeline_info = getattr(self.app, "_pipeline_info", None)
            candidates = resolve_filename_candidates(
                self.filename,
                pipeline_info=pipeline_info,
                output_kind=image_type,
                filename_variants_fn=self._filename_variants,
            )
            if not candidates:
                return None, f"unknown image_type {image_type!r}"
            self._debug(
                f"output lookup type={image_type}, source={self.filename!r}, candidates={candidates!r}"
            )

            well_token = extract_well_token(self.well_label)
            if well_token is None:
                return None, f"could not extract well_token from {self.well_label!r}"

            data_dir = self.app._data_dir
            in_dir = self.app._in_dir
            zips: list = []
            if data_dir and data_dir.is_dir():
                zips = find_out_well_zips_in_dir(data_dir, well_token)
                zips += find_plain_well_zips_in_dir(data_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = find_well_zips_in_dir(data_dir, well_token)
            self._debug(f"output zip search well_token={well_token!r}, zips={[str(z) for z in zips]!r}")

            candidate_lowers = [c.lower() for c in candidates]
            for zip_path in zips:
                self._debug(f"scan zip for {image_type}: {zip_path}")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() in candidate_lowers:
                            ref = ImgRef(zip_path=zip_path, zip_member=member)
                            arr = open_imgref_as_array(ref=ref, greyscale=(image_type == "mask"))
                            self._debug(f"loaded {image_type} from zip: {zip_path}::{member}")
                            return arr, f"{zip_path}::{member}"

            search_dirs = [d for d in (data_dir, in_dir) if d and d.is_dir()]
            self._debug(f"output disk search dirs={[str(d) for d in search_dirs]!r}")
            for d in search_dirs:
                for candidate in candidates:
                    for img_path in d.rglob(candidate):
                        ref = ImgRef(disk_path=img_path)
                        arr = open_imgref_as_array(ref=ref, greyscale=(image_type == "mask"))
                        self._debug(f"loaded {image_type} from disk: {img_path}")
                        return arr, str(img_path)

            self._debug(f"{image_type} not found. candidates={candidates!r}")
            return None, f"not found: {candidates[0]!r}"

        except Exception as e:
            self._debug(f"_load_output_image_by_filename exception for {image_type}: {e!r}")
            return None, f"exception: {e}"

    def _well_token_variants(self, name: str) -> list[str]:
        import re as _re

        m = _re.match(r"^([A-Ha-h])(\d{1,2})(.*)$", name)
        if not m:
            return []
        row = m.group(1).upper()
        col = int(m.group(2))
        rest = m.group(3)
        variants = [
            f"{row}{col}{rest}",
            f"{row}{col:02d}{rest}",
        ]
        out: list[str] = []
        seen: set[str] = set()
        for v in variants:
            if v != name and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def _filename_variants(self, filename: str) -> list[str]:
        from pathlib import Path as _Path

        p = _Path(filename)
        stem_variants = [p.stem, *self._well_token_variants(p.stem)]
        variants: list[str] = []
        seen: set[str] = set()
        for stem in stem_variants:
            candidate = f"{stem}{p.suffix}"
            if candidate not in seen:
                seen.add(candidate)
                variants.append(candidate)
        return variants

    def _get_cell_bounds(self, mask_arr, nuclear_id: int, padding_px: int = 0) -> Optional[Tuple[int, int, int, int]]:
        try:
            import numpy as np

            if mask_arr is None:
                self._debug("mask unavailable.")
                return None

            mask_arr = np.asarray(mask_arr)
            self._debug(
                f"mask loaded: shape={tuple(mask_arr.shape)}, dtype={mask_arr.dtype}, min={mask_arr.min()}, max={mask_arr.max()}"
            )
            cell_pixels = np.where(mask_arr == nuclear_id)

            if len(cell_pixels[0]) == 0:
                try:
                    uniq = np.unique(mask_arr)
                    sample = uniq[:25].tolist()
                    self._debug(
                        f"nuclear_id={nuclear_id} not in mask. unique_count={len(uniq)}, sample_unique={sample}"
                    )
                except Exception:
                    self._debug(f"nuclear_id={nuclear_id} not in mask. failed to compute unique labels.")
                return None

            y_min, y_max = int(cell_pixels[0].min()), int(cell_pixels[0].max()) + 1
            x_min, x_max = int(cell_pixels[1].min()), int(cell_pixels[1].max()) + 1

            if padding_px > 0:
                y_min = max(0, y_min - padding_px)
                x_min = max(0, x_min - padding_px)
                y_max = min(mask_arr.shape[0], y_max + padding_px)
                x_max = min(mask_arr.shape[1], x_max + padding_px)
            return (y_min, x_min, y_max, x_max)

        except Exception as e:
            self._debug(f"_get_cell_bounds exception: {e!r}")
            return None

    def _compute_outline_mask(self, cell_mask):
        import numpy as np

        if cell_mask is None:
            return None

        cell_mask = np.asarray(cell_mask, dtype=bool)
        if cell_mask.size == 0:
            return None

        up = np.roll(cell_mask, 1, axis=0)
        down = np.roll(cell_mask, -1, axis=0)
        left = np.roll(cell_mask, 1, axis=1)
        right = np.roll(cell_mask, -1, axis=1)

        up[0, :] = False
        down[-1, :] = False
        left[:, 0] = False
        right[:, -1] = False

        interior = cell_mask & up & down & left & right
        return cell_mask & ~interior

    def _load_and_crop_channel(self, channel: str) -> Optional:
        try:
            if channel in ("mask", "overlay"):
                arr, src = self._load_output_image_by_filename(channel)
                self._debug(f"channel={channel} loaded_from={src}")
            else:
                arr = self._load_input_channel_by_filename(channel)
            if arr is None or not self._cell_bounds:
                self._debug(f"channel={channel} unavailable or missing bounds.")
                return None

            y_min, x_min, y_max, x_max = self._cell_bounds
            return arr[y_min:y_max, x_min:x_max]

        except Exception as e:
            self._debug(f"_load_and_crop_channel exception for {channel}: {e!r}")
            return None

    def _load_and_crop_nuclear(self) -> Optional:
        try:
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.data_loading import extract_well_token
            from well_viewer.image_discovery import (
                ImgRef,
                find_plain_well_zips_in_dir,
                find_well_zips_in_dir,
                open_imgref_as_array,
            )

            if not self._cell_bounds:
                self._debug("skip nuclear image load: no cell bounds.")
                return None

            well_token = extract_well_token(self.well_label)
            if well_token is None:
                self._debug(f"could not parse well token from {self.well_label!r} for nuclear image load")
                return None

            in_dir = self.app._in_dir
            data_dir = self.app._data_dir

            zips: list = []
            if in_dir and in_dir.is_dir():
                zips = find_plain_well_zips_in_dir(in_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = find_well_zips_in_dir(data_dir, well_token)
            self._debug(f"nuclear image zip search target={self.filename!r}, zips={[str(z) for z in zips]!r}")

            pipeline_info = getattr(self.app, "_pipeline_info", None)
            target_names = resolve_filename_candidates(
                self.filename,
                pipeline_info=pipeline_info,
                filename_variants_fn=self._filename_variants,
            )
            self._debug(f"nuclear image filename candidates={target_names!r}")
            target_lowers = {name.lower() for name in target_names}
            for zip_path in zips:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() in target_lowers:
                            arr = open_imgref_as_array(
                                ref=ImgRef(zip_path=zip_path, zip_member=member),
                                greyscale=True,
                            )
                            if arr is not None:
                                self._debug(f"loaded nuclear image from zip: {zip_path}::{member}")
                                y_min, x_min, y_max, x_max = self._cell_bounds
                                return arr[y_min:y_max, x_min:x_max]

            search_dirs = [d for d in (in_dir, data_dir) if d and d.is_dir()]
            self._debug(f"nuclear image disk search dirs={[str(d) for d in search_dirs]!r}")
            for d in search_dirs:
                for target_name in target_names:
                    for img_path in d.rglob(target_name):
                        arr = open_imgref_as_array(ref=ImgRef(disk_path=img_path), greyscale=True)
                        if arr is not None:
                            self._debug(f"loaded nuclear image from disk: {img_path}")
                            y_min, x_min, y_max, x_max = self._cell_bounds
                            return arr[y_min:y_max, x_min:x_max]

            self._debug(f"nuclear image not found for filename={self.filename!r}")
            return None

        except Exception as e:
            self._debug(f"_load_and_crop_nuclear exception: {e!r}")
            return None

    def _load_input_channel_by_filename(self, channel_token: str) -> Optional:
        try:
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.data_loading import extract_well_token
            from well_viewer.image_discovery import (
                ImgRef,
                find_plain_well_zips_in_dir,
                find_well_zips_in_dir,
                open_imgref_as_array,
            )

            pipeline_info = getattr(self.app, "_pipeline_info", None)
            target_names = resolve_filename_candidates(
                self.filename,
                pipeline_info=pipeline_info,
                target_channel=channel_token,
                filename_variants_fn=self._filename_variants,
            )
            self._debug(f"channel={channel_token}: filename candidates={target_names!r} from source={self.filename!r}")
            if not target_names:
                return None

            well_token = extract_well_token(self.well_label)
            if well_token is None:
                self._debug(f"channel={channel_token}: could not parse well token from {self.well_label!r}")
                return None

            in_dir = self.app._in_dir
            data_dir = self.app._data_dir

            zips: list = []
            if in_dir and in_dir.is_dir():
                zips = find_plain_well_zips_in_dir(in_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = find_well_zips_in_dir(data_dir, well_token)
            self._debug(f"channel={channel_token}: zip search zips={[str(z) for z in zips]!r}")

            target_lowers = {name.lower() for name in target_names}
            for zip_path in zips:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() in target_lowers:
                            ref = ImgRef(zip_path=zip_path, zip_member=member)
                            self._debug(f"channel={channel_token}: loaded from zip {zip_path}::{member}")
                            return open_imgref_as_array(ref=ref, greyscale=True)

            search_dirs = [d for d in (in_dir, data_dir) if d and d.is_dir()]
            self._debug(f"channel={channel_token}: disk search dirs={[str(d) for d in search_dirs]!r}")
            for d in search_dirs:
                for candidate_name in target_names:
                    for img_path in d.rglob(candidate_name):
                        self._debug(f"channel={channel_token}: loaded from disk {img_path}")
                        return open_imgref_as_array(ref=ImgRef(disk_path=img_path), greyscale=True)

            self._debug(f"channel={channel_token}: not found candidates={target_names!r}")
            return None

        except Exception as e:
            self._debug(f"_load_input_channel_by_filename exception for {channel_token}: {e!r}")
            return None

    def _on_channel_changed(self, *_args) -> None:
        self._current_channel = self._channel_dropdown.currentText()
        if not self._current_channel:
            return

        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.setText("Image not found")
            return

        if self._current_channel in self._channel_luts:
            lo, hi = self._channel_luts[self._current_channel]
        else:
            try:
                lo, hi = float(arr.min()), float(arr.max())
            except (ValueError, TypeError, AttributeError):
                lo, hi = 0.0, 100.0

            if hi <= lo:
                hi = lo + 1.0

            self._channel_luts[self._current_channel] = (lo, hi)

        self._current_lut = (lo, hi)
        self._lut_min_edit.setText(f"{lo:.1f}")
        self._lut_max_edit.setText(f"{hi:.1f}")

        self._display_current_image()

    def _on_lut_change(self) -> None:
        try:
            lo = float(self._lut_min_edit.text())
            hi = float(self._lut_max_edit.text())
            self._current_lut = (lo, hi)
            if self._current_channel:
                self._channel_luts[self._current_channel] = (lo, hi)
            self._display_current_image()
        except ValueError:
            pass

    def _auto_lut(self) -> None:
        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            return

        try:
            lo, hi = float(arr.min()), float(arr.max())
        except (ValueError, TypeError, AttributeError):
            return

        if hi <= lo:
            hi = lo + 1.0

        self._current_lut = (lo, hi)
        if self._current_channel:
            self._channel_luts[self._current_channel] = (lo, hi)
        self._lut_min_edit.setText(f"{lo:.1f}")
        self._lut_max_edit.setText(f"{hi:.1f}")
        self._display_current_image()

    def _display_current_image(self) -> None:
        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.setText("No image")
            return

        label_width = max(self._img_label.width(), 300)
        label_height = max(self._img_label.height(), 300)

        lo, hi = self._current_lut
        pixmap = self._make_magnified_thumb(
            arr,
            label_width,
            label_height,
            lo,
            hi,
            outline_mask=self._cell_outline_mask,
        )

        if pixmap is not None:
            self._pixmap_cache = pixmap
            self._img_label.setPixmap(pixmap)
        else:
            self._img_label.setText("Failed to render image")

    def _make_magnified_thumb(self, arr, sz_w: int, sz_h: int, lo, hi, outline_mask=None) -> Optional[QPixmap]:
        try:
            import numpy as np

            arr = np.asarray(arr, dtype=np.float32)
            alo = lo if lo is not None else float(arr.min())
            ahi = hi if hi is not None else float(arr.max())
            if ahi <= alo:
                ahi = alo + 1.0

            disp = ((np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255).astype(np.uint8)
            rgb = np.stack([disp, disp, disp], axis=-1)

            if outline_mask is not None:
                outline = np.asarray(outline_mask, dtype=bool)
                if outline.shape == disp.shape:
                    rgb[outline] = np.array([255, 0, 0], dtype=np.uint8)

            h, w, _ = rgb.shape
            rgb_c = np.ascontiguousarray(rgb)
            qimg = QImage(rgb_c.data, w, h, 3 * w, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qimg)
            return pixmap.scaled(
                int(sz_w), int(sz_h),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        except Exception:
            return None

    def update_cell(self, well_label: str, filename: str, nuclear_id: str, row_idx: int) -> None:
        self.well_label = well_label
        self.filename = normalize_row_filename(filename)
        self.nuclear_id = nuclear_id
        self.row_idx = row_idx
        self.setWindowTitle(f"Cell Viewer - Scatter Plot: {well_label}")
        self._load_cell_data()
