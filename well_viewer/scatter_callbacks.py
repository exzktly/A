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
        try:
            nuclear_id = int(float(self.nuclear_id))
        except (ValueError, TypeError):
            self._img_label.config(text="Invalid nuclear_id")
            return

        print(f"DEBUG: Loading well={self.well_label}, filename={self.filename}, nuclear_id={nuclear_id}")

        # Get timepoint from row
        rows = self.app._get_rows(self.well_label)
        if self.row_idx >= len(rows):
            self._img_label.config(text="Invalid row index")
            return

        row = rows[self.row_idx]
        try:
            timepoint_h = float(row.get("timepoint_hours", 0.0))
        except (ValueError, TypeError):
            timepoint_h = 0.0

        # Use the FOV column from the CSV row directly — it was populated by
        # parse_filename() from the input filename and matches the (fov, tp)
        # keys used in the output image dictionaries.
        self._target_fov = str(row.get("fov") or row.get("FOV") or "").strip() or None
        print(f"DEBUG: target_fov={self._target_fov!r} from CSV row")

        # Get cell bounds from mask using filename and nuclear_id
        self._cell_bounds = self._get_cell_bounds(nuclear_id, timepoint_h)
        if not self._cell_bounds:
            self._img_label.config(text=f"Cell {nuclear_id} not found in mask or mask error")
            return

        print(f"DEBUG: Cell bounds: {self._cell_bounds}")

        # Load and crop fluorescence images for all channels
        for ch in sorted(self.app._fluor_channels):
            arr = self._load_and_crop_channel(ch, timepoint_h)
            if arr is not None:
                self._cell_images[ch] = arr
                print(f"DEBUG: Loaded and cropped {ch}, shape: {arr.shape}")

        # Load and crop nuclear fluorescence image (overlay)
        arr = self._load_and_crop_channel("overlay", timepoint_h)
        if arr is not None:
            self._cell_images["nuclear_fluor"] = arr
            print(f"DEBUG: Loaded and cropped nuclear_fluor (overlay), shape: {arr.shape}")

        # Load and crop nuclear mask image
        arr = self._load_and_crop_channel("mask", timepoint_h)
        if arr is not None:
            self._cell_images["nuclear"] = arr
            print(f"DEBUG: Loaded and cropped nuclear (mask), shape: {arr.shape}")

        # Populate dropdown with fluorescence channels first, then nuclear fluor and mask
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

    def _get_cell_bounds(self, nuclear_id: int, timepoint_h: float) -> Optional[Tuple[int, int, int, int]]:
        """Get cell pixel boundaries from mask file specified by filename.

        Returns (y_min, x_min, y_max, x_max) or None if not found.
        """
        try:
            from well_viewer.runtime_app import open_imgref_as_array
            from pathlib import Path
            import numpy as np

            # Try to find mask file matching the filename
            # The filename typically indicates which files to use
            mask_arr = self._load_image_by_filename(timepoint_h, "mask")
            if mask_arr is None:
                print(f"DEBUG: Could not load mask for {self.filename}")
                return None

            # Find pixels belonging to this cell
            mask_arr = np.asarray(mask_arr)
            print(f"DEBUG: Mask shape: {mask_arr.shape}, dtype: {mask_arr.dtype}")
            print(f"DEBUG: Unique values in mask: {np.unique(mask_arr)}")

            cell_pixels = np.where(mask_arr == nuclear_id)

            if len(cell_pixels[0]) == 0:
                print(f"DEBUG: Cell {nuclear_id} not found in mask")
                return None

            # Get bounding box
            y_min, y_max = int(cell_pixels[0].min()), int(cell_pixels[0].max()) + 1
            x_min, x_max = int(cell_pixels[1].min()), int(cell_pixels[1].max()) + 1

            return (y_min, x_min, y_max, x_max)

        except Exception as e:
            print(f"DEBUG: Exception in _get_cell_bounds: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_and_crop_channel(self, channel: str, timepoint_h: float) -> Optional:
        """Load and crop fluorescence image for a channel using filename."""
        try:
            arr = self._load_image_by_filename(timepoint_h, channel)
            if arr is None or not self._cell_bounds:
                return None

            # Crop to cell
            y_min, x_min, y_max, x_max = self._cell_bounds
            return arr[y_min:y_max, x_min:x_max]

        except Exception as e:
            print(f"DEBUG: Exception loading {channel}: {e}")
            return None

    def _load_image_by_filename(self, timepoint_h: float, image_type: str) -> Optional:
        """Load image from the well's image dictionary using filename as template.

        image_type: 'mask', 'overlay', 'fluor', channel name like 'gfp', 'mcherry', etc.
        """
        try:
            from well_viewer.runtime_app import find_well_images_and_masks, open_imgref_as_array

            # Get appropriate image dictionary
            if image_type == "mask":
                _, _, img_dict, _ = find_well_images_and_masks(
                    self.app._data_dir,
                    self.well_label,
                    fluor_token=self.app._active_channel,
                    in_dir=self.app._in_dir,
                    _fov_tp_extractor=self.app._fov_tp_extractor,
                )
            elif image_type == "overlay":
                _, img_dict, _, _ = find_well_images_and_masks(
                    self.app._data_dir,
                    self.well_label,
                    fluor_token=self.app._active_channel,
                    in_dir=self.app._in_dir,
                    _fov_tp_extractor=self.app._fov_tp_extractor,
                )
            else:
                fluor_dict, _, _, _ = find_well_images_and_masks(
                    self.app._data_dir,
                    self.well_label,
                    fluor_token=image_type,
                    in_dir=self.app._in_dir,
                    _fov_tp_extractor=self.app._fov_tp_extractor,
                )
                img_dict = fluor_dict

            if not img_dict:
                print(f"DEBUG: No {image_type} images found")
                return None

            # Use the FOV from the CSV row (set by _load_cell_data).  The CSV
            # fov column comes from parse_filename() on the input file and
            # already matches the (fov, tp) keys in the output image dicts.
            target_fov: str | None = getattr(self, "_target_fov", None)

            tp_int = int(round(timepoint_h))
            img_ref = None

            # Try numeric format first, matching FOV when available
            for (fov, tp_str), ref in img_dict.items():
                if target_fov is not None and fov != target_fov:
                    continue
                try:
                    tp_float = float(tp_str)
                    if abs(tp_float - timepoint_h) < 0.1:
                        img_ref = ref
                        print(f"DEBUG: Matched {image_type} numeric format: fov={fov}, tp={tp_str}")
                        break
                except (ValueError, TypeError):
                    pass

            # Try T## format
            if not img_ref and tp_int > 0:
                for (fov, tp_str), ref in img_dict.items():
                    if target_fov is not None and fov != target_fov:
                        continue
                    if tp_str.upper().startswith('T'):
                        try:
                            tp_num = int(tp_str[1:])
                            if tp_num == tp_int:
                                img_ref = ref
                                print(f"DEBUG: Matched {image_type} T## format: fov={fov}, tp={tp_str}")
                                break
                        except (ValueError, IndexError):
                            pass

            # Fall back to any FOV if no match found with target FOV
            if not img_ref and target_fov is not None:
                print(f"DEBUG: No match for FOV={target_fov!r}, falling back to any FOV")
                for (fov, tp_str), ref in img_dict.items():
                    try:
                        tp_float = float(tp_str)
                        if abs(tp_float - timepoint_h) < 0.1:
                            img_ref = ref
                            print(f"DEBUG: Fallback matched {image_type} numeric: fov={fov}, tp={tp_str}")
                            break
                    except (ValueError, TypeError):
                        pass
                if not img_ref and tp_int > 0:
                    for (fov, tp_str), ref in img_dict.items():
                        if tp_str.upper().startswith('T'):
                            try:
                                tp_num = int(tp_str[1:])
                                if tp_num == tp_int:
                                    img_ref = ref
                                    print(f"DEBUG: Fallback matched {image_type} T## format: fov={fov}, tp={tp_str}")
                                    break
                            except (ValueError, IndexError):
                                pass

            if not img_ref:
                print(f"DEBUG: No matching {image_type} image for timepoint={timepoint_h}")
                return None

            # Load and return array
            arr = open_imgref_as_array(ref=img_ref, greyscale=True)
            if arr is not None:
                print(f"DEBUG: Loaded {image_type}, shape={arr.shape}")
            return arr

        except Exception as e:
            print(f"DEBUG: Exception in _load_image_by_filename({image_type}): {e}")
            import traceback
            traceback.print_exc()
            return None

    def _on_channel_changed(self) -> None:
        """Handle channel selection change."""
        self._current_channel = self._channel_var.get()
        if not self._current_channel:
            return

        # Update image display
        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.config(text="Image not found")
            return

        # Auto-compute LUT
        try:
            lo, hi = float(arr.min()), float(arr.max())
        except (ValueError, TypeError, AttributeError):
            lo, hi = 0.0, 100.0

        if hi <= lo:
            hi = lo + 1.0

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
        self._lut_min_var.set(f"{lo:.1f}")
        self._lut_max_var.set(f"{hi:.1f}")
        self._display_current_image()

    def _on_window_resize(self, event) -> None:
        """Handle window resize event to redraw image at new size."""
        # Only redraw if we have a current image and the size actually changed
        if self._current_channel and self._cell_images.get(self._current_channel) is not None:
            self._display_current_image()

    def _display_current_image(self) -> None:
        """Display the current channel image with current LUT."""
        arr = self._cell_images.get(self._current_channel)
        if arr is None:
            self._img_label.config(text="No image")
            return

        # Force layout update to get accurate dimensions
        self.update_idletasks()

        # Calculate thumbnail size based on label's current size
        # Get the label's allocated size
        label_width = self._img_label.winfo_width()
        label_height = self._img_label.winfo_height()

        # If size is not yet available, use window size as estimate
        if label_width <= 1:
            label_width = self.winfo_width() - 40
        if label_height <= 1:
            label_height = self.winfo_height() - 200  # Account for title, controls, LUT frame

        # Ensure minimum reasonable size
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

            # Normalize to 0-255
            disp = ((np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255).astype(np.uint8)
            img = _PILImage.fromarray(disp, mode="L").convert("RGB")

            # Scale to fit - allow magnification (no 1.0 cap like make_fluor_thumb)
            iw, ih = img.size
            scale = min(sz_w / iw, sz_h / ih)  # No upper limit, allows magnification
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)

            return _PILImageTk.PhotoImage(img)
        except Exception as e:
            print(f"DEBUG: Error in _make_magnified_thumb: {e}")
            return None

    def update_cell(self, well_label: str, filename: str, nuclear_id: str, row_idx: int) -> None:
        """Update viewer to show a different cell."""
        self.well_label = well_label
        self.filename = filename
        self.nuclear_id = nuclear_id
        self.row_idx = row_idx
        self.title(f"Cell Viewer - Scatter Plot: {well_label}")
        self._load_cell_data()
