"""Scatter plot click handlers and single-cell image viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple
import tkinter as tk
from tkinter import ttk

if TYPE_CHECKING:
    from .runtime_app import WellViewerApp


class ScatterCellViewer(tk.Toplevel):
    """Modal window for viewing a single cell's fluorescence images.

    Shows one channel at a time, cropped to the cell's boundaries from the mask.
    Uses filename and nuclear_id from CSV to locate images.
    """

    def __init__(
        self,
        parent,
        app: WellViewerApp,
        well_label: str,
        filename: str,
        nuclear_id: str,
        row_idx: int,
    ):
        super().__init__(parent)
        self.title("Cell Viewer - Scatter Plot")
        self.geometry("600x650")
        self.resizable(True, True)
        self.grab_set()

        self.app = app
        self.well_label = well_label
        self.filename = filename
        self.nuclear_id = nuclear_id
        self.row_idx = row_idx

        self._cell_bounds: Optional[Tuple[int, int, int, int]] = None  # (y_min, x_min, y_max, x_max)
        self._cell_images: dict[str, Optional] = {}  # channel → cropped array
        self._current_channel = None
        self._current_lut: Tuple[float, float] = (0.0, 100.0)
        self._channel_luts: dict[str, Tuple[float, float]] = {}  # channel → (lo, hi)

        # Build UI
        self._build_ui()

        # Load data
        self._load_cell_data()

    def _build_ui(self) -> None:
        """Build the UI."""
        # Title
        title_label = tk.Label(
            self,
            text=f"Cell Viewer: {self.well_label}",
            font=("TkDefaultFont", 10, "bold"),
        )
        title_label.pack(pady=5)

        # Channel selector
        control_frame = tk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(control_frame, text="Channel:", font=("TkDefaultFont", 9)).pack(side=tk.LEFT)

        self._channel_var = tk.StringVar()
        self._channel_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self._channel_var,
            state="readonly",
            width=15,
        )
        self._channel_dropdown.pack(side=tk.LEFT, padx=5)
        self._channel_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_channel_changed())

        # Image display
        self._img_label = tk.Label(self, text="Loading...")
        self._img_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bind to window resize to redraw image at new size
        self.bind("<Configure>", self._on_window_resize)

        # LUT controls
        lut_frame = tk.Frame(self)
        lut_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(lut_frame, text="LUT min:", font=("TkDefaultFont", 8)).pack(side=tk.LEFT)
        self._lut_min_var = tk.StringVar(value="0")
        tk.Entry(lut_frame, textvariable=self._lut_min_var, width=8, font=("TkDefaultFont", 8)).pack(
            side=tk.LEFT, padx=2
        )
        self._lut_min_var.trace("w", lambda *args: self._on_lut_change())

        tk.Label(lut_frame, text="max:", font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=(10, 2))
        self._lut_max_var = tk.StringVar(value="100")
        tk.Entry(lut_frame, textvariable=self._lut_max_var, width=8, font=("TkDefaultFont", 8)).pack(
            side=tk.LEFT, padx=2
        )
        self._lut_max_var.trace("w", lambda *args: self._on_lut_change())

        tk.Button(lut_frame, text="Auto", font=("TkDefaultFont", 8), command=self._auto_lut).pack(
            side=tk.LEFT, padx=2
        )

    def _load_cell_data(self) -> None:
        """Load cell data: find images using filename, get cell bounds from mask."""
        self._channel_luts = {}
        try:
            nuclear_id = int(float(self.nuclear_id))
        except (ValueError, TypeError):
            self._img_label.config(text="Invalid nuclear_id")
            return

        rows = self.app._get_rows(self.well_label)
        if self.row_idx >= len(rows):
            self._img_label.config(text="Invalid row index")
            return

        row = rows[self.row_idx]

        # The 'channel' field in the CSV identifies the nuclear channel token
        # that appears in self.filename (e.g. "NIR", "DAPI").  Used to swap
        # in the correct fluor token when loading input images.
        self._nuclear_token = str(row.get("channel") or "").strip()

        self._cell_bounds = self._get_cell_bounds(nuclear_id)
        if not self._cell_bounds:
            self._img_label.config(text=f"Cell {nuclear_id} not found in mask")
            return

        # Load and crop fluorescence images for all channels
        for ch in sorted(self.app._fluor_channels):
            arr = self._load_and_crop_channel(ch)
            if arr is not None:
                self._cell_images[ch] = arr

        # Load and crop nuclear channel image (self.filename is the nuclear image)
        arr = self._load_and_crop_nuclear()
        if arr is not None:
            self._cell_images["nuclear_fluor"] = arr

        arr = self._load_and_crop_channel("mask")
        if arr is not None:
            self._cell_images["nuclear"] = arr

        # Populate dropdown with fluorescence channels first, then overlay and mask
        available_channels = [ch for ch in sorted(self.app._fluor_channels) if self._cell_images.get(ch) is not None]
        if "nuclear_fluor" in self._cell_images:
            available_channels.append("nuclear_fluor")
        if "nuclear" in self._cell_images:
            available_channels.append("nuclear")
        self._channel_dropdown.config(values=available_channels)

        if available_channels:
            self._channel_var.set(available_channels[0])
            self._on_channel_changed()
        else:
            self._img_label.config(text="No images could be loaded")

    def _load_output_image_by_filename(self, image_type: str):
        """Load a mask or overlay from the output zip by constructing the expected
        output filename from self.filename.

        process_microscopy_v2.py writes output files as:
            <stem with nuclear_token removed>_labels.tif   (mask)
            <stem with nuclear_token removed>_overlay.png  (overlay)

        Returns (array, path_str).
        """
        try:
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.runtime_app import (
                open_imgref_as_array, _ImgRef,
                _extract_well_token,
                _find_out_well_zips_in_dir,
                _find_plain_well_zips_in_dir,
                _find_well_zips_in_dir,
            )

            nuclear_token = getattr(self, "_nuclear_token", "")
            stem = _Path(self.filename).stem
            base = stem.replace(nuclear_token, "") if nuclear_token else stem

            if image_type == "mask":
                candidates = [base + "_labels.tif", base + "_labels.tiff", base + "_labels.png"]
            elif image_type == "overlay":
                candidates = [base + "_overlay.png", base + "_overlay.jpg", base + "_overlay.jpeg", base + "_overlay.tif"]
            else:
                return None, f"unknown image_type {image_type!r}"

            well_token = _extract_well_token(self.well_label)
            if well_token is None:
                return None, f"could not extract well_token from {self.well_label!r}"

            data_dir = self.app._data_dir
            in_dir = self.app._in_dir
            zips: list = []
            if in_dir and data_dir and data_dir.is_dir():
                zips = _find_out_well_zips_in_dir(data_dir, well_token)
                zips += _find_plain_well_zips_in_dir(data_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = _find_well_zips_in_dir(data_dir, well_token)

            candidate_lowers = [c.lower() for c in candidates]
            for zip_path in zips:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() in candidate_lowers:
                            ref = _ImgRef(zip_path=zip_path, zip_member=member)
                            arr = open_imgref_as_array(ref=ref, greyscale=(image_type == "mask"))
                            return arr, f"{zip_path}::{member}"

            # Fallback: raw files on disk
            search_dirs = [d for d in (data_dir, in_dir) if d and d.is_dir()]
            for d in search_dirs:
                for candidate in candidates:
                    for img_path in d.rglob(candidate):
                        ref = _ImgRef(disk_path=img_path)
                        arr = open_imgref_as_array(ref=ref, greyscale=(image_type == "mask"))
                        return arr, str(img_path)

            return None, f"not found: {candidates[0]!r}"

        except Exception as e:
            return None, f"exception: {e}"

    def _get_cell_bounds(self, nuclear_id: int) -> Optional[Tuple[int, int, int, int]]:
        """Get cell pixel boundaries from mask file.

        Returns (y_min, x_min, y_max, x_max) or None if not found.
        """
        try:
            import numpy as np

            mask_arr, _ = self._load_output_image_by_filename("mask")
            if mask_arr is None:
                return None

            mask_arr = np.asarray(mask_arr)
            cell_pixels = np.where(mask_arr == nuclear_id)

            if len(cell_pixels[0]) == 0:
                return None

            y_min, y_max = int(cell_pixels[0].min()), int(cell_pixels[0].max()) + 1
            x_min, x_max = int(cell_pixels[1].min()), int(cell_pixels[1].max()) + 1
            return (y_min, x_min, y_max, x_max)

        except Exception:
            return None

    def _load_and_crop_channel(self, channel: str) -> Optional:
        """Load and crop image for a channel."""
        try:
            if channel in ("mask", "overlay"):
                arr, _ = self._load_output_image_by_filename(channel)
            else:
                arr = self._load_input_channel_by_filename(channel)
            if arr is None or not self._cell_bounds:
                return None

            y_min, x_min, y_max, x_max = self._cell_bounds
            return arr[y_min:y_max, x_min:x_max]

        except Exception:
            return None

    def _load_and_crop_nuclear(self) -> Optional:
        """Load and crop the nuclear channel image (self.filename) from the input folder."""
        try:
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.runtime_app import (
                open_imgref_as_array, _ImgRef,
                _extract_well_token,
                _find_plain_well_zips_in_dir,
                _find_well_zips_in_dir,
            )

            if not self._cell_bounds:
                return None

            well_token = _extract_well_token(self.well_label)
            if well_token is None:
                return None

            in_dir = self.app._in_dir
            data_dir = self.app._data_dir

            zips: list = []
            if in_dir and in_dir.is_dir():
                zips = _find_plain_well_zips_in_dir(in_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = _find_well_zips_in_dir(data_dir, well_token)

            target_lower = self.filename.lower()
            for zip_path in zips:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() == target_lower:
                            arr = open_imgref_as_array(
                                ref=_ImgRef(zip_path=zip_path, zip_member=member),
                                greyscale=True,
                            )
                            if arr is not None:
                                y_min, x_min, y_max, x_max = self._cell_bounds
                                return arr[y_min:y_max, x_min:x_max]

            # Fallback: disk
            search_dirs = [d for d in (in_dir, data_dir) if d and d.is_dir()]
            for d in search_dirs:
                for img_path in d.rglob(self.filename):
                    arr = open_imgref_as_array(ref=_ImgRef(disk_path=img_path), greyscale=True)
                    if arr is not None:
                        y_min, x_min, y_max, x_max = self._cell_bounds
                        return arr[y_min:y_max, x_min:x_max]

            return None

        except Exception:
            return None

    def _load_input_channel_by_filename(self, channel_token: str) -> Optional:
        """Load a channel image from the input folder by swapping the nuclear
        channel token in self.filename with channel_token.

        Uses the CSV row's 'channel' field as the nuclear token to replace.
        """
        try:
            import re as _re
            import zipfile
            from pathlib import Path as _Path
            from well_viewer.runtime_app import (
                open_imgref_as_array, _ImgRef,
                _extract_well_token,
                _find_plain_well_zips_in_dir,
                _find_well_zips_in_dir,
            )

            nuclear_token = getattr(self, "_nuclear_token", "")
            if not nuclear_token:
                return None

            # Replace the nuclear token in the filename (case-insensitive, first occurrence)
            target_name = _re.sub(
                _re.escape(nuclear_token),
                channel_token,
                self.filename,
                count=1,
                flags=_re.IGNORECASE,
            )
            if target_name == self.filename:
                return None

            well_token = _extract_well_token(self.well_label)
            if well_token is None:
                return None

            in_dir = self.app._in_dir
            data_dir = self.app._data_dir

            zips: list = []
            if in_dir and in_dir.is_dir():
                zips = _find_plain_well_zips_in_dir(in_dir, well_token)
            if not zips and data_dir and data_dir.is_dir():
                zips = _find_well_zips_in_dir(data_dir, well_token)

            target_lower = target_name.lower()
            for zip_path in zips:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if _Path(member).name.lower() == target_lower:
                            ref = _ImgRef(zip_path=zip_path, zip_member=member)
                            return open_imgref_as_array(ref=ref, greyscale=True)

            # Fallback: raw files on disk
            search_dirs = [d for d in (in_dir, data_dir) if d and d.is_dir()]
            for d in search_dirs:
                for img_path in d.rglob(target_name):
                    return open_imgref_as_array(ref=_ImgRef(disk_path=img_path), greyscale=True)

            return None

        except Exception:
            return None

    def _on_channel_changed(self) -> None:
        """Handle channel selection change."""
        self._current_channel = self._channel_var.get()
        if not self._current_channel:
            return

        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.config(text="Image not found")
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
        self._lut_min_var.set(f"{lo:.1f}")
        self._lut_max_var.set(f"{hi:.1f}")

        self._display_current_image()

    def _on_lut_change(self) -> None:
        """Handle LUT value change."""
        try:
            lo = float(self._lut_min_var.get())
            hi = float(self._lut_max_var.get())
            self._current_lut = (lo, hi)
            if self._current_channel:
                self._channel_luts[self._current_channel] = (lo, hi)
            self._display_current_image()
        except ValueError:
            pass

    def _auto_lut(self) -> None:
        """Auto-scale LUT to image range."""
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
        self._lut_min_var.set(f"{lo:.1f}")
        self._lut_max_var.set(f"{hi:.1f}")
        self._display_current_image()

    def _on_window_resize(self, event) -> None:
        """Handle window resize event to redraw image at new size."""
        if self._current_channel and self._cell_images.get(self._current_channel) is not None:
            self._display_current_image()

    def _display_current_image(self) -> None:
        """Display the current channel image with current LUT."""
        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.config(text="No image")
            return

        self.update_idletasks()

        label_width = self._img_label.winfo_width()
        label_height = self._img_label.winfo_height()

        if label_width <= 1:
            label_width = self.winfo_width() - 40
        if label_height <= 1:
            label_height = self.winfo_height() - 200

        label_width = max(label_width, 300)
        label_height = max(label_height, 300)

        lo, hi = self._current_lut
        photo = self._make_magnified_thumb(arr, label_width, label_height, lo, hi)

        if photo is not None:
            self._img_label.config(image=photo, text="")
            self._img_label.image = photo
        else:
            self._img_label.config(text="Failed to render image")

    def _make_magnified_thumb(self, arr, sz_w: int, sz_h: int, lo, hi):
        """Render a greyscale array as a magnified thumbnail that scales UP to fit."""
        try:
            import numpy as np
            from PIL import Image as _PILImage
            from PIL import ImageTk as _PILImageTk

            arr = np.asarray(arr, dtype=np.float32)
            alo = lo if lo is not None else float(arr.min())
            ahi = hi if hi is not None else float(arr.max())
            if ahi <= alo:
                ahi = alo + 1.0

            disp = ((np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255).astype(np.uint8)
            img = _PILImage.fromarray(disp, mode="L").convert("RGB")

            iw, ih = img.size
            scale = min(sz_w / iw, sz_h / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)

            return _PILImageTk.PhotoImage(img)
        except Exception:
            return None

    def update_cell(self, well_label: str, filename: str, nuclear_id: str, row_idx: int) -> None:
        """Update viewer to show a different cell."""
        self.well_label = well_label
        self.filename = filename
        self.nuclear_id = nuclear_id
        self.row_idx = row_idx
        self.title(f"Cell Viewer - Scatter Plot: {well_label}")
        self._load_cell_data()
