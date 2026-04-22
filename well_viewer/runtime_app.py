"""
well_viewer.py
--------------
GUI for exploring per-well fluorescence measurement CSVs from process_microscopy.py.

Open a directory or archive (zip / tar.gz) with the single "Open…" button.
CSVs are loaded automatically; per-well image zips in the same folder are
discovered on demand for the preview panel.

Layout
------
  Left     – well list with row/column quick-selectors
  Centre   – plots: mean fluorescence above threshold ± SD/SEM, fraction, CDF
  Right    – fluorescence + mask image preview (hidden by default; "Show Preview" button)

Image preview notes
-------------------
  • Reads images directly from <well>_out.zip or <well>.zip without extraction.
  • Supports 16-bit TIFFs via tifffile (pip install tifffile).
  • LUT min/max editor on fluorescence panel; mouseover shows raw pixel value.
  • "Montage" button opens a popout window showing one FOV across all timepoints.

Dependencies:  pip install matplotlib pillow numpy tifffile
Usage:
    python well_viewer.py
    python well_viewer.py --data_dir /path/to/results
    python well_viewer.py --data_dir /path/to/results.zip
"""

from __future__ import annotations

# Legacy compatibility surface
# ----------------------------
# Canonical runtime module for the viewer.
# Implementation logic is incrementally delegated into well_viewer/* modules;
# keep exported names stable for package imports and entrypoints.

import argparse
import copy
import csv
import io
import logging
import json
import math
import re
import shutil
import statistics
import sys
import threading
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import matplotlib
from matplotlib.figure import Figure
from well_viewer.batch_models import BarGroup, ReplicateSet
from well_viewer.viewer_state import groups_with_loaded_wells as _groups_with_loaded_wells
from well_viewer.viewer_state import selected_listbox_values as _selected_listbox_values
from well_viewer.barplot_controller import bar_groups_from_data as _bar_groups_from_data
from well_viewer.barplot_controller import bar_groups_to_dict as _bar_groups_to_dict
from well_viewer.barplot_controller import apply_bar_ylims as _bar_apply_ylims
from well_viewer.barplot_controller import collect_bar_items as _bar_collect_items
from well_viewer.barplot_controller import ordered_bar_keys as _bar_ordered_keys
from well_viewer.barplot_controller import render_bar_items as _bar_render_items
from well_viewer import debug_flags as _debug_flags
from well_viewer.preview_controller import classify_member as _preview_classify_member
from well_viewer.preview_controller import open_imgref_as_array as _preview_open_imgref_as_array
from well_viewer.preview_controller import read_member_bytes as _preview_read_member_bytes
from well_viewer.preview_controller import scan_zip_members as _preview_scan_zip_members
from well_viewer.image_resolver import (
    find_well_subfolder_path as _find_well_subfolder_path,
    normalize_well_token as _normalize_well_token,
    output_suffixes_for_kind as _output_suffixes_for_kind,
    resolve_ref_by_fov_tp as _resolve_ref_by_fov_tp,
    well_token_matches_text as _well_token_matches_text,
)
from well_viewer.views.preview_view import build_preview_picker as _build_preview_picker_view
from well_viewer.views.preview_view import preview_pick_well as _preview_pick_well_view
from well_viewer.views.preview_view import refresh_preview_picker as _refresh_preview_picker_view
from well_viewer.lineplot_controller import redraw_line_plots as _lineplot_redraw
from well_viewer.scatter_controller import get_all_timepoints as _scatter_get_timepoints
from well_viewer.scatter_controller import redraw_scatter as _scatter_redraw
from well_viewer.grouping_controller import (
    bg_apply_legacy as _gc_bg_apply_legacy,
    bg_on_well_change as _gc_bg_on_well_change,
    grp_add as _gc_grp_add,
    grp_add_member as _gc_grp_add_member,
    grp_add_solo_well as _gc_grp_add_solo_well,
    grp_clear_all as _gc_grp_clear_all,
    grp_delete as _gc_grp_delete,
    grp_remove_member as _gc_grp_remove_member,
    grp_remove_solo as _gc_grp_remove_solo,
    grp_rename as _gc_grp_rename,
    grp_select as _gc_grp_select,
    grp_toggle_visibility as _gc_grp_toggle_visibility,
    rep_map_apply as _gc_rep_map_apply,
    rep_map_drag as _gc_rep_map_drag,
    rep_map_press as _gc_rep_map_press,
    rep_map_release as _gc_rep_map_release,
    rep_map_tok_at as _gc_rep_map_tok_at,
)
from well_viewer.load_controller import (
    build_tok_to_label as _load_build_tok_to_label,
    load_directory as _load_directory_controller,
    load_path as _load_path_controller,
)
from well_viewer.plot_orchestrator import (
    redraw as _plot_redraw_orchestrator,
    save_bar_figure as _plot_save_bar_figure_orchestrator,
    save_line_figure as _plot_save_line_figure_orchestrator,
    save_matplotlib_fig as _plot_save_matplotlib_fig_orchestrator,
)
from well_viewer.montage_controller import montage_auto_lut as _montage_auto_lut_controller
from well_viewer.montage_controller import montage_redraw_at_zoom as _montage_redraw_at_zoom_controller
from well_viewer.montage_controller import montage_resize_deferred as _montage_resize_deferred_controller
from well_viewer.montage_controller import montage_tophat_done as _montage_tophat_done_controller
from well_viewer.montage_controller import montage_zoom_fit as _montage_zoom_fit_controller
from well_viewer.montage_controller import montage_zoom_step as _montage_zoom_step_controller
from well_viewer.montage_controller import on_montage_canvas_resize as _on_montage_canvas_resize_controller
from well_viewer.montage_controller import on_montage_fluor_motion as _on_montage_fluor_motion_controller
from well_viewer.montage_controller import on_montage_shift_wheel as _on_montage_shift_wheel_controller
from well_viewer.montage_controller import on_montage_wheel as _on_montage_wheel_controller
from well_viewer.montage_controller import _show_image_pixel_tooltip as _show_image_pixel_tooltip_controller
from well_viewer.review_image_controller import on_review_csv_row_double_click as _on_review_csv_row_double_click_controller
from well_viewer.review_image_controller import on_review_image_click as _on_review_image_click_controller
from well_viewer.review_image_controller import select_review_csv_row_for_cell as _select_review_csv_row_for_cell_controller
from well_viewer.stats_controller import collect_group_values as _stats_collect_group_values
from well_viewer.stats_controller import draw_ks_cdf as _stats_draw_ks_cdf
from well_viewer.stats_controller import run_stats as _stats_run_controller
from well_viewer.views.stats_view import build_stats_group_editor as _build_stats_group_editor_view
from well_viewer.views.stats_view import build_stats_results_panel as _build_stats_results_panel_view
from well_viewer.views.stats_view import build_stats_tab as _build_stats_tab_view
from well_viewer.viewer_state import make_schema_extractor as _make_schema_extractor
from well_viewer.viewer_state import read_pipeline_info as _read_pipeline_info_shared
from well_viewer.ui_helpers import (
    ask_name_dialog as _ui_ask_name_dialog,
    BoolVar,
    btn_card as _btn_card,
    btn_danger as _btn_danger,
    btn_primary as _btn_primary,
    btn_secondary as _btn_secondary,
    clear_layout as _clear_layout,
    make_scrollable_canvas as _ui_make_scrollable_canvas,
)
from ui.theme import (
    ACCENT,
    ACCENT_DARK,
    BG_APP,
    BG_CELL,
    BG_HOVER,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    button_bg,
    button_text,
    button_text_disabled,
    CLR_AVAIL_HOVER,
    CLR_AVAIL_WELL,
    CLR_DANGER,
    CLR_DANGER_DARK,
    CLR_DANGER_BG,
    CLR_DANGER_HOVER,
    CLR_ERR_BAR,
    CLR_ERROR_BG_DARK,
    CLR_ERROR_TEXT_SOFT,
    CLR_MUTED_DISABLED,
    CLR_MUTED_TEXT_SOFT,
    CLR_OFF_WHITE,
    CLR_PLACEHOLDER,
    CLR_SLATE_BG,
    CLR_SLATE_TEXT,
    CLR_SUCCESS,
    CLR_SUCCESS_BG_DARK,
    CLR_SUCCESS_DARK,
    CLR_SUCCESS_TEXT_SOFT,
    CLR_WARN_BG,
    CLR_WARN_DARK,
    CLR_WARN_TEXT,
    CLR_WHITE,
    FM_BOLD,
    FM_MONO,
    FM_TINY,
    FM_TITLE,
    FM_UI,
    PLOT_BG,
    PLOT_GRD,
    PLOT_SPN,
    PLOT_TXT,
    TAB_BG,
    TAB_BG_ACTIVE,
    TAB_BORDER,
    TAB_FG,
    TAB_FG_ACTIVE,
    TOOLTIP_BG,
    TOOLTIP_FG,
    TXT_MUT,
    TXT_PRI,
    TXT_SEC,
    WARN,
    WELL_COLOR_1,
    WELL_COLOR_2,
    WELL_COLOR_3,
    WELL_COLOR_4,
    WELL_COLOR_5,
    WELL_COLOR_6,
    WELL_COLOR_7,
    WELL_COLOR_8,
    WELL_COLOR_9,
)


try:
    import tifffile as _tifffile
    _TIFFFILE_AVAILABLE = True
except ImportError:
    _tifffile = None          # type: ignore[assignment]
    _TIFFFILE_AVAILABLE = False

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import numpy as _np
    _NP_AVAILABLE = True
except ImportError:
    _np = None                # type: ignore[assignment]
    _NP_AVAILABLE = False

# ── Module logger (GUI handler wired in at build time) ───────────────────────
_logger = logging.getLogger("well_viewer")

# ── Semantic colour aliases (use these instead of magic hex strings) ──────────
CLR_ACCENT_DARK = ACCENT_DARK
CLR_DISABLED_WELL = CLR_MUTED_DISABLED   # disabled-well border on placeholder bars

WELL_COLORS = [
    WELL_COLOR_1, WELL_COLOR_2, WELL_COLOR_3, CLR_SUCCESS, WELL_COLOR_4,
    WELL_COLOR_5, WELL_COLOR_6, WELL_COLOR_7, WELL_COLOR_8, WELL_COLOR_9,
]
NO_SELECTION_MSG = "No wells or well groups selected.\nSelect wells on the left panel or define groups to plot."


def make_scrollable_canvas(parent, bg: str = BG_APP, scrollbar_width: int = 7):
    """Return (scroll_area, inner_widget) for a vertically scrollable panel."""
    return _ui_make_scrollable_canvas(parent, bg=bg)


# =============================================================================
# Shared UI helpers
# =============================================================================

def ask_name_dialog(parent, title: str = "Name", prompt: str = "Name:",
                    default: str = "", width: int = 24) -> Optional[str]:
    """Reusable modal text-input dialog."""
    return _ui_ask_name_dialog(parent, title=title, prompt=prompt, default=default)


def _set_combo_values(combo: object, values: List[str]) -> None:
    """Set combobox values for both Qt and legacy widget shims.

    Preserves the current selection when the new item list contains it, so a
    tk-style ``currentIndexChanged`` handler that calls back into a refresh
    function doesn't clobber the user's pick as a side-effect.
    """
    vals = [str(v) for v in values]
    if hasattr(combo, "clear") and hasattr(combo, "addItems"):
        block = getattr(combo, "blockSignals", None)
        prev_text = combo.currentText() if hasattr(combo, "currentText") else ""
        if callable(block):
            block(True)
        combo.clear()  # type: ignore[attr-defined]
        combo.addItems(vals)  # type: ignore[attr-defined]
        if prev_text and prev_text in vals and hasattr(combo, "setCurrentIndex"):
            combo.setCurrentIndex(vals.index(prev_text))  # type: ignore[attr-defined]
        if callable(block):
            block(False)
        return
    combo["values"] = vals  # type: ignore[index]


# Canonical definitions live in well_viewer/views/well_button.py
from well_viewer.views.well_button import WellButton as WellLabel, build_plate_grid


def make_fluor_thumb(arr, sz_w: int, sz_h: int,
                   lo: Optional[float], hi: Optional[float]):
    """Render a greyscale float32 array as a QPixmap with LUT [lo, hi]."""
    if arr is None or not _NP_AVAILABLE:
        return None
    arr = _np.asarray(arr, dtype=_np.float32)
    alo = lo if lo is not None else float(arr.min())
    ahi = hi if hi is not None else float(arr.max())
    if ahi <= alo:
        ahi = alo + 1.0
    disp = ((_np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255).astype(_np.uint8)
    rgb = _np.stack([disp, disp, disp], axis=-1).copy()
    h, w, _ = rgb.shape
    qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    pm = QPixmap.fromImage(qimg)
    return pm.scaled(int(sz_w), int(sz_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def make_overlay_thumb(arr, sz_w: int, sz_h: int):
    """Render a 2-D or 3-D array as a QPixmap scaled to (sz_w, sz_h)."""
    if arr is None or not _NP_AVAILABLE:
        return None
    arr = _np.asarray(arr)
    if arr.ndim == 2:
        arr_f = arr.astype(_np.float32)
        lo, hi = float(arr_f.min()), float(arr_f.max())
        if hi <= lo:
            hi = lo + 1.0
        disp = ((arr_f - lo) / (hi - lo) * 255).astype(_np.uint8)
        rgb = _np.stack([disp, disp, disp], axis=-1).copy()
    elif arr.ndim == 3 and arr.shape[2] >= 3:
        a = arr[:, :, :3]
        if a.dtype != _np.uint8:
            rng = max(a.max() - a.min(), 1)
            a = ((a.astype(_np.float32) - a.min()) / rng * 255).astype(_np.uint8)
        rgb = _np.ascontiguousarray(a)
    else:
        return None
    h, w, _ = rgb.shape
    qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    pm = QPixmap.fromImage(qimg)
    return pm.scaled(int(sz_w), int(sz_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _bind_drag(frame, btn_store, on_press, on_drag, on_release, *, button: int = 1) -> None:
    """Bind press/drag/release events — stub retained for API compat under Qt."""
    # Qt: wire mousePressEvent/mouseMoveEvent/mouseReleaseEvent overrides instead.
    frame.mousePressEvent = on_press
    frame.mouseMoveEvent = on_drag
    frame.mouseReleaseEvent = on_release


def _wells_multiselect_listbox(parent, available, preselect=None):
    """Return a QListWidget of *available* well labels with multi-selection."""
    lb = QListWidget(parent)
    lb.setSelectionMode(QAbstractItemView.MultiSelection)
    preset = set(preselect or ())
    for w in available:
        item = QListWidgetItem(w)
        lb.addItem(item)
        if w in preset:
            item.setSelected(True)
    return lb


def _selected_list_values(lb) -> list:
    """Return the current selected item text list from a QListWidget."""
    return [lb.item(i).text() for i in range(lb.count()) if lb.item(i).isSelected()]


def save_json_file(parent, data: object, *,
                   title: str = "Save", default_name: str = "data.json",
                   initial_dir: Optional[str] = None) -> bool:
    """Show a save-file dialog and write *data* as indented JSON."""
    initial = default_name if not initial_dir else str(Path(initial_dir) / default_name)
    path_str, _ = QFileDialog.getSaveFileName(
        parent, title, initial, "JSON files (*.json);;All files (*.*)",
    )
    if not path_str:
        return False
    try:
        with open(path_str, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
    except OSError as exc:
        QMessageBox.critical(parent, "Save failed", str(exc))
        return False


def load_json_file(parent, *, title: str = "Load",
                   initial_dir: Optional[str] = None) -> Optional[object]:
    """Show an open-file dialog and return the parsed JSON object, or None."""
    start_dir = initial_dir or ""
    path_str, _ = QFileDialog.getOpenFileName(
        parent, title, start_dir, "JSON files (*.json);;All files (*.*)",
    )
    if not path_str:
        return None
    try:
        with open(path_str, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        QMessageBox.critical(parent, "Load failed", str(exc))
        return None


def apply_ax_style(ax, title: str, ylabel: str) -> None:
    """
    Apply the standard dark-on-light plot style to *ax*.

    Extracted from WellViewerApp._style_ax and the local _style() closures
    inside _render_subset_figure so there is a single authoritative copy.
    """
    ax.set_facecolor(PLOT_BG)
    for sp in ax.spines.values():
        sp.set_color(PLOT_SPN)
        sp.set_linewidth(0.8)
    ax.tick_params(colors=PLOT_TXT, labelsize=8)
    ax.xaxis.label.set_color(PLOT_TXT)
    ax.yaxis.label.set_color(PLOT_TXT)
    ax.set_title(title, color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)
    ax.set_ylabel(ylabel, fontsize=8, labelpad=5, color=PLOT_TXT)
    ax.grid(True, color=PLOT_GRD, linewidth=0.7, linestyle="-")


# Pure-data helpers live in data_loading.py. Re-exported here for backwards
# compatibility with callers that import them from runtime_app.
from well_viewer.data_loading import (
    AggPoint,
    _STRING_COLS,
    _all_fluor_values,
    _all_fluor_values_filtered,
    _beeswarm_jitter,
    _ordinal_timepoints,
    aggregate_with_threshold,
    detect_fluor_channels,
    detect_nuclear_channel_token,
    detect_review_image_channels,
    detect_smfish_channels,
    load_well_csv,
    merge_fluor_channels,
    normalize_channel_tokens,
    parse_timepoint_hours,
    row_is_included,
)


# =============================================================================
# Image reference and finders
# =============================================================================

_IMAGE_EXTS   = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}


def _suffix_matcher(kind: str) -> re.Pattern[str]:
    suffixes = [re.escape(sfx) for sfx in _output_suffixes_for_kind(kind, target_channel="x")]
    if kind in {"fluor_processed", "smfish"}:
        suffixes = [sfx.replace("x", r"\w+") for sfx in suffixes]
    return re.compile(r"(?:%s)$" % "|".join(suffixes), re.I)


_MASK_RE      = _suffix_matcher("mask")
_OVERLAY_RE   = _suffix_matcher("overlay")
_TOPHAT_FLUOR_RE = _suffix_matcher("fluor_processed")
_OUT_ZIP_RE   = re.compile(r"^([A-Ha-h])(\d{1,2})_out\.zip$", re.I)
_PLAIN_ZIP_RE = re.compile(r"^([A-Ha-h])(\d{1,2})\.zip$",     re.I)
_FNAME_RE     = re.compile(
    r"^(?P<exp>[^_]+)_(?P<channel>[^_]*)_(?P<well>[^_]+)_(?P<fov>[^_]+)_(?P<tp>[^_.]+)",
    re.I,
)


def _norm_well(raw: str) -> Optional[str]:
    normalized = _normalize_well_token(raw)
    return normalized or None


from well_viewer.data_loading import extract_well_token as _extract_well_token


class _ImgRef:
    """Pointer to an image on disk or inside a zip (possibly nested)."""
    __slots__ = ("disk_path", "zip_path", "zip_member")

    def __init__(self, disk_path: Optional[Path] = None,
                 zip_path: Optional[Path] = None,
                 zip_member: Optional[str] = None) -> None:
        self.disk_path  = disk_path
        self.zip_path   = zip_path
        self.zip_member = zip_member

    @property
    def name(self) -> str:
        if self.disk_path:
            return self.disk_path.name
        if self.zip_member:
            return Path(self.zip_member.split("::")[-1]).name
        return "unknown"

    @property
    def full_path_str(self) -> str:
        if self.disk_path:
            return str(self.disk_path)
        if self.zip_path and self.zip_member:
            return f"{self.zip_path}  >>  {self.zip_member}"
        return "unknown"


def _read_member_bytes(zip_path: Path, member: str) -> Optional[bytes]:
    """Read bytes of a zip member; handles nested 'outer::inner' notation."""
    return _preview_read_member_bytes(zip_path=zip_path, member=member, logger=_logger)


def open_imgref_as_array(ref: _ImgRef,
                         greyscale: bool = False) -> "Optional[_np.ndarray]":
    """
    Load an image as a numpy array at full native bit depth.

    Returns float32 for single-channel images; uint8 (H×W×3) for RGB images
    such as overlays.  Pass greyscale=True to force conversion to float32
    greyscale (used for fluorescence and mask panels where colour is irrelevant).

    Prefers tifffile for TIFFs (better 16-bit support); falls back to PIL.
    """
    return _preview_open_imgref_as_array(
        ref=ref,
        greyscale=greyscale,
        np_available=_NP_AVAILABLE,
        tifffile_available=_TIFFFILE_AVAILABLE,
        pil_available=_PIL_AVAILABLE,
        tifffile_module=_tifffile,
        pil_image_module=_PILImage if _PIL_AVAILABLE else None,
        np_module=_np,
        io_module=io,
        read_member_bytes_fn=_read_member_bytes,
        logger=_logger,
    )


def _legacy_extractor(stem: str) -> Tuple[str, str]:
    """Fallback extractor that uses the classic 5-field regex."""
    m = _FNAME_RE.match(stem)
    if m:
        return m.group("fov"), m.group("tp")
    _logger.debug("_FNAME_RE no match: stem=%r", stem)
    return "unknown", "unknown"


def _extract_pipeline_fields(stem: str, pipeline_info: Optional[dict]) -> Dict[str, str]:
    """Parse *stem* into schema fields from pipeline_info.json when available."""
    if not pipeline_info:
        return {}
    sep = str(pipeline_info.get("separator", "_"))
    schema_fields = [
        str(f).strip() for f in (pipeline_info.get("schema_fields", []) or [])
        if str(f).strip()
    ]
    if not schema_fields:
        schema = str(pipeline_info.get("schema", "")).strip()
        schema_fields = [f.strip() for f in schema.split(":") if f.strip()]
    if not schema_fields:
        return {}
    parts = stem.split(sep)
    return {field: (parts[i] if i < len(parts) else "") for i, field in enumerate(schema_fields)}


def _classify_member(
    name: str,
    fluor_lower: str,
    _fov_tp_extractor=None,
    _pipeline_info: Optional[dict] = None,
) -> Tuple[str, str, str]:
    """Return (kind, fov, tp) where kind is 'fluor', 'tophat_fluor', 'mask', 'overlay', or ''.

    *fluor_lower* is the lowercase fluorescent channel token (e.g. 'gfp', 'mcherry').
    *_fov_tp_extractor* is an optional callable(stem) -> (fov, tp).  When
    None the legacy hardcoded _FNAME_RE is used as a fallback so that results
    directories produced before pipeline_info.json was introduced still work.
    """
    kind, fov, tp = _preview_classify_member(
        name=name,
        fluor_lower=fluor_lower,
        mask_re=_MASK_RE,
        overlay_re=_OVERLAY_RE,
        tophat_fluor_re=_TOPHAT_FLUOR_RE,
        fov_tp_extractor=_fov_tp_extractor,
        legacy_extractor=_legacy_extractor,
        pipeline_fields_extractor=lambda stem: _extract_pipeline_fields(stem, _pipeline_info),
    )
    if _debug_flags.review_image_channel_switch_debug_enabled():
        _logger.debug(
            "[RI-CHSW step 5] classify_member name=%r fluor=%r -> kind=%r fov=%r tp=%r",
            name,
            fluor_lower,
            kind,
            fov,
            tp,
        )
    return kind, fov, tp


def _scan_zip_members(
    zip_path: Path,
    fluor_lower: str,
    member_prefix: str = "",
    _fov_tp_extractor=None,
    _pipeline_info: Optional[dict] = None,
) -> Tuple[Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef],
           Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef],
           Dict[Tuple[str,str], _ImgRef]]:
    """Scan a zip file (or nested zip via member_prefix) for fluor/overlay/mask/tophat images."""
    return _preview_scan_zip_members(
        zip_path=zip_path,
        fluor_lower=fluor_lower,
        image_exts=_IMAGE_EXTS,
        classify_member_fn=_classify_member,
        imgref_factory=lambda p, m: _ImgRef(zip_path=p, zip_member=m),
        logger=_logger,
        member_prefix=member_prefix,
        fov_tp_extractor=_fov_tp_extractor,
        pipeline_info=_pipeline_info,
    )


def _find_well_zips_in_dir(data_dir: Path, well_token: str) -> List[Path]:
    """Return [_out.zip, <well>.zip] for this well token, _out first (legacy flat mode)."""
    out_zips, plain_zips = [], []
    for p in sorted(data_dir.glob("*.zip")):
        if p.name.startswith("."):
            continue
        m = _OUT_ZIP_RE.match(p.name)
        if m and _norm_well(m.group(1) + m.group(2)) == well_token:
            out_zips.append(p)
            continue
        m2 = _PLAIN_ZIP_RE.match(p.name)
        if m2 and _norm_well(m2.group(1) + m2.group(2)) == well_token:
            plain_zips.append(p)
    return out_zips + plain_zips


def _find_plain_well_zips_in_dir(in_dir: Path, well_token: str) -> List[Path]:
    """Return plain <well>.zip paths from the input directory."""
    result = []
    for p in sorted(in_dir.glob("*.zip")):
        if p.name.startswith("."):
            continue
        m = _PLAIN_ZIP_RE.match(p.name)
        if m and _norm_well(m.group(1) + m.group(2)) == well_token:
            result.append(p)
    return result


def _find_out_well_zips_in_dir(out_dir: Path, well_token: str) -> List[Path]:
    """Return <well>_out.zip paths from the output directory."""
    result = []
    for p in sorted(out_dir.glob("*.zip")):
        if p.name.startswith("."):
            continue
        m = _OUT_ZIP_RE.match(p.name)
        if m and _norm_well(m.group(1) + m.group(2)) == well_token:
            result.append(p)
    return result


def _find_well_subfolder(parent_dir: Path, well_token: str) -> "Optional[Path]":
    """Return well subfolder matching token, accepting both A1/A01 forms."""
    return _find_well_subfolder_path(parent_dir, well_token)


def _scan_folder_members(
    folder_path: Path,
    fluor_lower: str,
    _fov_tp_extractor=None,
    _pipeline_info: Optional[dict] = None,
) -> "Tuple[Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef]]":
    """Scan a plain disk folder for fluor/overlay/mask/tophat/smfish images."""
    fluor:        "Dict[Tuple[str,str], _ImgRef]" = {}
    overlay:      "Dict[Tuple[str,str], _ImgRef]" = {}
    mask:         "Dict[Tuple[str,str], _ImgRef]" = {}
    tophat_fluor: "Dict[Tuple[str,str], _ImgRef]" = {}
    smfish:       "Dict[Tuple[str,str], _ImgRef]" = {}
    try:
        _logger.info("Scanning folder %s", folder_path)
        for p in sorted(folder_path.iterdir()):
            if not p.is_file():
                continue
            if p.suffix.lower() not in _IMAGE_EXTS or p.name.startswith("."):
                continue
            kind, fov, tp = _classify_member(
                p.name,
                fluor_lower,
                _fov_tp_extractor,
                _pipeline_info=_pipeline_info,
            )
            if not kind:
                continue
            key = (fov, tp)
            ref = _ImgRef(disk_path=p)
            if kind == "fluor":
                fluor.setdefault(key, ref)
            elif kind == "tophat_fluor":
                tophat_fluor.setdefault(key, ref)
            elif kind == "overlay":
                overlay.setdefault(key, ref)
            elif kind == "mask":
                mask.setdefault(key, ref)
            elif kind == "smfish":
                smfish.setdefault(key, ref)
    except Exception as exc:
        _logger.warning("Failed scanning folder %s: %s", folder_path, exc)
    return fluor, overlay, mask, tophat_fluor, smfish


def find_well_images_and_masks(
    data_dir: Optional[Path],
    well_label: str,
    fluor_token: str = "GFP",
    in_dir: Optional[Path] = None,
    _fov_tp_extractor=None,
    _pipeline_info: Optional[dict] = None,
) -> Tuple[Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef],
           Dict[Tuple[str,str], _ImgRef], Dict[Tuple[str,str], _ImgRef]]:
    """
    Find fluorescent channel images, overlay images, label masks, and pre-filtered tophat images.

    Returns (fluor_dict, overlay_dict, mask_dict, tophat_dict), each keyed by (fov, timepoint).

    *_fov_tp_extractor* is a callable(stem) -> (fov, tp) built from the
    pipeline_info.json sidecar that analyze_tab.py writes alongside each run.
    When None the legacy hardcoded _FNAME_RE regex is used as a fallback so that
    output directories produced before pipeline_info.json was introduced still
    work correctly.

    Directory layout modes
    ----------------------
    Structured (in/out):
      *in_dir*   – contains plain <well>.zip with original fluorescent/NIR images.
      *data_dir* – the "out" folder; contains <well>_out.zip (masks + overlays)
                   and the per-well CSVs.
      Fluorescent images are sourced from *in_dir*; masks/overlays from *data_dir*.

    Flat (legacy):
      *in_dir* is None.  All zips are searched in *data_dir* with the old
      priority: <well>_out.zip first (masks/overlays), then <well>.zip (fluor).

    Archive mode:
      *source_zip* is set; nested per-well zips are searched inside it.
    """
    well_token  = _extract_well_token(well_label)
    fluor_lower   = fluor_token.lower()  # passed to _classify_member as fluor_lower
    fluor:        Dict[Tuple[str,str], _ImgRef] = {}
    overlay:      Dict[Tuple[str,str], _ImgRef] = {}
    mask:         Dict[Tuple[str,str], _ImgRef] = {}
    tophat_fluor: Dict[Tuple[str,str], _ImgRef] = {}

    _logger.info(
        "Searching images: well=%r token=%r  in_dir=%s  data_dir=%s",
        well_label, well_token,
        str(in_dir)   if in_dir   else "None",
        str(data_dir) if data_dir else "None",
    )
    image_load_debug = (
        _debug_flags.review_image_load_debug_enabled()
        or _debug_flags.movie_montage_load_debug_enabled()
    )
    channel_switch_debug = _debug_flags.review_image_channel_switch_debug_enabled()
    if channel_switch_debug:
        _logger.debug(
            "[RI-CHSW step 5] find_well_images_and_masks start well=%r token=%r fluor=%r",
            well_label,
            well_token,
            fluor_lower,
        )

    # ── 1. Structured in/out directory layout ────────────────────────────────
    # in_dir  → plain <well>.zip files → GFP source images
    # data_dir → <well>_out.zip files  → masks and overlays
    if in_dir and in_dir.is_dir() and well_token:
        in_zips = _find_plain_well_zips_in_dir(in_dir, well_token)
        for wzip in in_zips:
            g, ov, mk, th, _sm = _scan_zip_members(wzip, fluor_lower,
                                                   _fov_tp_extractor=_fov_tp_extractor,
                                                   _pipeline_info=_pipeline_info)
            for k, v in g.items():
                fluor.setdefault(k, v)
            # Fluor zips may also contain overlays/masks in some workflows
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)

    if in_dir and data_dir and data_dir.is_dir() and well_token:
        # out-zips contain masks and overlays
        out_zips = _find_out_well_zips_in_dir(data_dir, well_token)
        for wzip in out_zips:
            g, ov, mk, th, _sm = _scan_zip_members(wzip, fluor_lower,
                                                   _fov_tp_extractor=_fov_tp_extractor,
                                                   _pipeline_info=_pipeline_info)
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)

    # ── 1b. Well subfolder layout (folder mode, no zips) ─────────────────────
    # in_dir/<well>/   → fluor/NIR source images
    # data_dir/<well>/ → masks, overlays, tophat output images
    if in_dir and in_dir.is_dir() and well_token:
        in_folder = _find_well_subfolder(in_dir, well_token)
        if in_folder:
            if image_load_debug:
                _logger.info("[image-load-debug] in_folder resolved for %s -> %s", well_token, in_folder)
            g, ov, mk, th, _sm = _scan_folder_members(
                in_folder, fluor_lower, _fov_tp_extractor=_fov_tp_extractor, _pipeline_info=_pipeline_info
            )
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)
        elif image_load_debug:
            _logger.info("[image-load-debug] in_folder missing for token=%s in %s", well_token, in_dir)

    if in_dir and data_dir and data_dir.is_dir() and well_token:
        out_folder = _find_well_subfolder(data_dir, well_token)
        if out_folder:
            if image_load_debug:
                _logger.info("[image-load-debug] out_folder resolved for %s -> %s", well_token, out_folder)
            g, ov, mk, th, _sm = _scan_folder_members(
                out_folder, fluor_lower, _fov_tp_extractor=_fov_tp_extractor, _pipeline_info=_pipeline_info
            )
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)
        elif image_load_debug:
            _logger.info("[image-load-debug] out_folder missing for token=%s in %s", well_token, data_dir)

    # ── 2. Flat directory: all zips in data_dir ───────────────────────────────
    if in_dir is None and data_dir and data_dir.is_dir() and well_token:
        for wzip in _find_well_zips_in_dir(data_dir, well_token):
            g, ov, mk, th, _sm = _scan_zip_members(wzip, fluor_lower,
                                                   _fov_tp_extractor=_fov_tp_extractor,
                                                   _pipeline_info=_pipeline_info)
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)

    # ── 2b. Flat directory: <well>/ subfolders in data_dir ───────────────────
    if in_dir is None and data_dir and data_dir.is_dir() and well_token:
        flat_folder = _find_well_subfolder(data_dir, well_token)
        if flat_folder:
            g, ov, mk, th, _sm = _scan_folder_members(
                flat_folder, fluor_lower, _fov_tp_extractor=_fov_tp_extractor, _pipeline_info=_pipeline_info
            )
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)

    # ── 3. Raw files on disk fallback ─────────────────────────────────────────
    search_dirs = [d for d in (in_dir, data_dir) if d and d.is_dir()] if in_dir else (
        [data_dir] if data_dir and data_dir.is_dir() else []
    )
    if not fluor and search_dirs:
        for search_root in search_dirs:
            for p in sorted(search_root.rglob("*")):
                if p.suffix.lower() not in _IMAGE_EXTS or p.name.startswith("."):
                    continue
                kind, fov, tp = _classify_member(
                    p.name,
                    fluor_lower,
                    _fov_tp_extractor,
                    _pipeline_info=_pipeline_info,
                )
                if not kind:
                    continue
                if well_token:
                    # Filter by well: when a schema extractor is present we have
                    # no dedicated well-field extractor here, so we use a safe
                    # substring match.  With the legacy path we keep the old
                    # regex-based well comparison for backward compatibility.
                    parsed = _extract_pipeline_fields(p.stem, _pipeline_info)
                    parsed_well = _norm_well(str(parsed.get("well", ""))) if parsed else None
                    if parsed_well:
                        if parsed_well != well_token:
                            if image_load_debug:
                                _logger.info(
                                    "[image-load-debug] skip %s parsed_well=%s token=%s",
                                    p.name,
                                    parsed_well,
                                    well_token,
                                )
                            continue
                    elif _fov_tp_extractor is None:
                        m = _FNAME_RE.match(p.stem)
                        fw = _norm_well(m.group("well")) if m else None
                        if fw and fw != well_token:
                            if image_load_debug:
                                _logger.info(
                                    "[image-load-debug] skip %s legacy_well=%s token=%s",
                                    p.name,
                                    fw,
                                    well_token,
                                )
                            continue
                        if not fw and not _well_token_matches_text(p.name, well_token):
                            if image_load_debug:
                                _logger.info(
                                    "[image-load-debug] skip %s no well token match target=%s",
                                    p.name,
                                    well_token,
                                )
                            continue
                    elif not _well_token_matches_text(p.name, well_token):
                        if image_load_debug:
                            _logger.info(
                                "[image-load-debug] skip %s schema path no well token match target=%s",
                                p.name,
                                well_token,
                            )
                        continue
                ref = _ImgRef(disk_path=p)
                if kind == "fluor":
                    fluor.setdefault((fov, tp), ref)
                elif kind == "tophat_fluor":
                    tophat_fluor.setdefault((fov, tp), ref)
                elif kind == "overlay":
                    overlay.setdefault((fov, tp), ref)
                else:
                    mask.setdefault((fov, tp), ref)

    if not fluor:
        _logger.warning("No fluor images found for %r (token=%r)", well_label, well_token)
    if not overlay:
        _logger.info("No overlay images found for %r (token=%r)", well_label, well_token)
    if not mask:
        _logger.warning("No masks found for %r (token=%r)", well_label, well_token)
    if tophat_fluor:
        _logger.info("Pre-filtered tophat images found for %r (%d)", well_label, len(tophat_fluor))
    if channel_switch_debug:
        _logger.debug(
            "[RI-CHSW step 5] find_well_images_and_masks done fluor=%d tophat=%d overlay=%d mask=%d",
            len(fluor),
            len(tophat_fluor),
            len(overlay),
            len(mask),
        )

    return (dict(sorted(fluor.items())), dict(sorted(overlay.items())),
            dict(sorted(mask.items())), dict(sorted(tophat_fluor.items())))

# =============================================================================
# Categorical label colourmap  (canonical: well_viewer/views/image_panel_view.py)
# =============================================================================

from well_viewer.views.image_panel_view import _label_to_rgb

# =============================================================================
# Tooltip
# =============================================================================

from PySide6.QtWidgets import QToolTip


class _Tooltip:
    """Lightweight pixel-tooltip helper backed by ``QToolTip``."""

    def __init__(self, parent=None) -> None:
        self._parent = parent

    def show(self, x: int, y: int, text: str) -> None:
        from PySide6.QtCore import QPoint
        widget = self._parent
        if widget is None:
            QToolTip.showText(QPoint(int(x), int(y)), text)
            return
        global_pt = widget.mapToGlobal(QPoint(int(x), int(y)))
        QToolTip.showText(global_pt, text, widget)

    def hide(self) -> None:
        QToolTip.hideText()

# =============================================================================
# Reusable image panel  (canonical: well_viewer/views/image_panel_view.py)
# =============================================================================

from well_viewer.views.image_panel_view import _ImagePanel

# =============================================================================
# GUI log handler  (canonical: well_viewer/views/status_view.py)
# =============================================================================

from well_viewer.views.status_view import _GUILogHandler

# =============================================================================
# Montage popout window
# =============================================================================


# =============================================================================
# Batch export – data model
# =============================================================================

class BatchSubset:
    """
    A named subset of wells for a single batch export run.

    *wells*       – ordered list of well labels (e.g. 'gfp_measurements_B03').
    *replicates*  – future extension: maps a replicate-group name to a list of
                    well labels within this subset that are biological replicates.
                    Currently always empty; reserved for a future update that
                    will compute proper replicate-averaged statistics.

    Example (future use):
        subset.replicates = {
            "rep_A": ["gfp_measurements_B03", "gfp_measurements_B04"],
            "rep_B": ["gfp_measurements_C03", "gfp_measurements_C04"],
        }
    """
    def __init__(self, name: str, wells: List[str]) -> None:
        self.name:       str                    = name
        self.wells:      List[str]              = list(wells)
        self.replicates: Dict[str, List[str]]   = {}   # reserved for future use

    def __repr__(self) -> str:
        return f"BatchSubset({self.name!r}, wells={self.wells})"



# Plate layout constants
_PLATE_ROWS = list("ABCDEFGH")
_PLATE_COLS = [f"{c:02d}" for c in range(1, 13)]  # "01" … "12"


class _SubsetEntry:
    """
    Holds one named subset of wells for batch export.

    Fields intentionally include *replicate_group* (empty string by default)
    so that a future update can assign wells to replicate groups and compute
    combined statistics without changing the data model.

    replicate_group maps well_label -> group identifier string.
    e.g.  {"gfp_measurements_B03": "rep1", "gfp_measurements_B04": "rep1",
            "gfp_measurements_B05": "rep2"}
    When empty, each well is treated as an independent measurement.
    """

    def __init__(self, name: str) -> None:
        self.name:             str            = name
        self.wells:            List[str]      = []   # ordered list of well labels
        self.replicate_group:  Dict[str, str] = {}   # well_label -> replicate id (future use)


# CellGatingTab lives in well_viewer/cell_gating_tab.py
from well_viewer.cell_gating_tab import CellGatingTab  # noqa: E402  (re-export)

class WellViewerApp(QWidget):

    def __init__(self, parent=None, data_path: Optional[Path] = None) -> None:
        super().__init__(parent)
        self._NP_AVAILABLE = _NP_AVAILABLE
        self._np = _np
        self._theme_name = "Dark"

        # Data state
        self._data_dir:   Optional[Path]        = None
        self._in_dir:     Optional[Path]        = None
        self._tmp_dir:    Optional[Path]        = None
        self._well_paths: Dict[str, Path]       = {}
        self._cache:      Dict[str, List[dict]] = {}
        self._all_timepoints_cache: List[float] = []
        self._all_fovs_cache: List[str] = []
        self._last_sel:   Optional[str]         = None
        self._prev_sel:   set                   = set()
        self._sidebar_map_refresh_pending: bool = False

        # Active fluorescent channel (set when CSVs are loaded)
        self._fluor_channels: List[str] = []
        self._review_image_channels: List[str] = []
        self._smfish_channels: set[str] = set()
        self._active_channel: str       = "gfp"
        self._active_image_channel: str = "gfp"
        self._active_metric: str        = "mean_intensity"
        self._active_val_col: str       = "gfp_mean_intensity"

        # Plot controls — widgets are assigned in _build_ui; keep placeholders
        # until then so callers can inspect default state.
        self._threshold_min = 0.0
        self._threshold_max = 1.0
        self._threshold     = 50.0
        # Qt: concrete widgets are assigned in _build_ui() / view builders.
        # Provide plain-Python defaults so early callers before _build_ui get sane values.
        # SEM/SD toggle state — one BoolVar drives every per-toolbar SEM button.
        # attach_plot_toolbar() registers each button in _sem_btns, so we must
        # initialize both BEFORE any plot tab is built.
        self._use_sem = BoolVar(True)
        self._sem_btns: List = []
        self._sem_btn = None
        self._legend_visible: Dict[str, bool] = {
            "mean": True, "frac": True, "cdf": True,
        }
        # Channel / timepoint comboboxes are assigned to these attrs in the view builders.
        self._plot_chan_cb = None
        self._montage_chan_cb = None
        self._review_image_chan_cb = None
        self._bar_tp_cb = None
        self._bar_swarm_cb = None
        self._bar_violin_cb = None
        self._violin_bw_edit = None
        self._bar_log_scale_cb = None
        self._bar_ylim_mean_lo_edit = None
        self._bar_ylim_mean_hi_edit = None
        self._bar_ylim_frac_lo_edit = None
        self._bar_ylim_frac_hi_edit = None
        self._bar_order: Optional[List] = None
        self._rep_sets:          List[ReplicateSet] = []
        self._active_rep_idx:    int               = -1
        self._rep_hidden:        set               = set()
        self._well_labels:       Dict[str, str]    = {}
        self._bar_groups:        List[BarGroup]    = []
        self._bar_active_grp:    int               = -1
        self._rep_quick_pair_dir   = "row"
        self._rep_quick_iter_order = "row"
        self._bar_quick_pair_dir   = "row"
        self._bar_quick_iter_order = "row"
        self._entry_edit = None
        self._cdf_xmin_edit = None
        self._cdf_xmax_edit = None
        self._thr_dragging  = False

        # Plate-map well selection
        self._selected_wells: set  = set()
        self._tok_to_label:   Dict[str, str] = {}

        # Preview state
        self._fov_tp_extractor = None
        self._pipeline_info: Dict[str, object] = {}
        self._preview_selected_well: Optional[str] = None
        self._preview_fov_cb = None
        self._montage_photos: List[object] = []
        self._preview_fluor:   Dict[Tuple[str,str], _ImgRef] = {}
        self._preview_overlay: Dict[Tuple[str,str], _ImgRef] = {}
        self._preview_mask:    Dict[Tuple[str,str], _ImgRef] = {}
        self._review_image_tp_cb = None
        self._review_image_selected_nucleus: Optional[int] = None
        self._review_image_nucleus_to_iid: Dict[int, str] = {}
        self._review_image_include_edit_mode: bool = False
        self._review_included_overrides: Dict[Tuple[str, str, str, str], str] = {}
        self._review_csv_lookup_context: Dict[str, str] = {}
        self._review_image_zoom: float = 1.0
        self._review_image_pan_x: float = 0.0
        self._review_image_pan_y: float = 0.0
        self._review_image_dragging: bool = False
        self._review_image_drag_moved: bool = False
        self._review_image_drag_last_xy: Tuple[int, int] = (0, 0)
        self._review_image_base_pil = None
        self._review_image_is_tif: bool = False
        self._review_image_lut_by_channel: Dict[str, Tuple[float, float]] = {}
        self._review_image_last_fluor_arr = None
        self._review_image_preserve_view_on_refresh: bool = False

        self._build_ui()
        self._apply_theme()

        if data_path is not None:
            QTimer.singleShot(100, lambda: self._load_path(data_path))

    @staticmethod
    def _position_root_on_screen(root, *, preferred_w: int, preferred_h: int) -> None:
        """Qt: no-op; window placement handled by QMainWindow / QWidget defaults."""
        return
        w = min(preferred_w, max(1000, sw - margin))
        h = min(preferred_h, max(800, sh - margin))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        root.geometry(f"{w}x{h}+{x}+{y}")

    # ── Threshold helpers ─────────────────────────────────────────────────────

    def _get_cell_area_threshold(self) -> float:
        """Get cell area threshold from the Cell Gating tab."""
        if hasattr(self, '_cell_gating_tab') and self._cell_gating_tab is not None:
            try:
                return float(self._cell_gating_tab._cell_area_threshold.get())
            except ValueError:
                return 0.0
        return 0.0

    def _get_fluor_gate(self, channel: str) -> float:
        """Get FluorGating threshold for a channel."""
        if hasattr(self, '_cell_gating_tab') and self._cell_gating_tab is not None:
            return self._cell_gating_tab.get_fluor_gate(channel)
        return 0.0

    def _get_all_fluor_gates(self) -> Dict[str, float]:
        """Get FluorGating thresholds for all loaded channels.

        Returns a dict mapping channel name -> gate threshold, e.g., {"gfp": 10.0, "mcherry": 20.0}.
        Used by aggregate_with_threshold to apply consistent gating across all channels.
        """
        gates = {}
        for channel in self._fluor_channels:
            gates[channel] = self._get_fluor_gate(channel)
        return gates

    def _row_is_included(self, row: dict) -> bool:
        """Instance wrapper so controllers can consistently check Included."""
        return row_is_included(row)

    def _apply_cell_gating_to_included(self) -> None:
        """Write cell-gating result into each cached row's Included field (1/0)."""
        cell_area_threshold = self._get_cell_area_threshold()
        fluor_gates = self._get_all_fluor_gates()

        for label in self._well_paths:
            rows = self._get_rows(label)
            for row in rows:
                include = 1
                try:
                    area = float(row.get("area_px", 0))
                    if area <= cell_area_threshold:
                        include = 0
                except (ValueError, TypeError):
                    include = 0

                if include:
                    for channel, gate_threshold in fluor_gates.items():
                        col = f"{channel}_mean_intensity"
                        try:
                            fluor = float(row.get(col, float("nan")))
                            if fluor != fluor or fluor <= gate_threshold:
                                include = 0
                                break
                        except (ValueError, TypeError):
                            include = 0
                            break

                row["Included"] = include

        self._invalidate_stats_cache()
        # Keep Review CSV table in sync whenever Included is recomputed.
        if hasattr(self, "_refresh_review_csv_rows"):
            self._refresh_review_csv_rows()

    def _get_thresh_frac_on(self, channel: Optional[str] = None) -> float:
        """Get ThreshFracOn threshold. Uses active channel if not specified."""
        if channel is None:
            channel = self._active_channel
        if hasattr(self, '_cell_gating_tab') and self._cell_gating_tab is not None:
            return self._cell_gating_tab.get_thresh_frac_on(channel)
        # Fallback to current threshold for backwards compatibility
        return self._threshold

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Topbar
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(14, 8, 14, 8)
        self._top_bar = top
        self._dir_label = QLabel("No data loaded")
        self._dir_label.setObjectName("Muted")
        top_layout.addWidget(self._dir_label)
        top_layout.addStretch(1)
        open_btn = QPushButton("Open\u2026")
        open_btn.setProperty("variant", "primary")
        open_btn.clicked.connect(self._browse)
        top_layout.addWidget(open_btn)
        outer.addWidget(top)

        self._top_sep = QFrame()
        self._top_sep.setFrameShape(QFrame.HLine)
        outer.addWidget(self._top_sep)

        # ── Horizontal splitter: sidebar | plots ───────────────────────────
        self._h_pane = QSplitter(Qt.Horizontal)
        outer.addWidget(self._h_pane, 1)

        sidebar = QWidget()
        sidebar.setMinimumWidth(260)
        sidebar.setMaximumWidth(600)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self._sidebar_main_frame = QWidget()
        QVBoxLayout(self._sidebar_main_frame).setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self._sidebar_main_frame, 1)

        self._sidebar_line_frame = self._sidebar_main_frame
        # Companion frames stacked in the sidebar and toggled by
        # _on_tab_change.  All are hidden initially; the tab handler shows
        # the relevant one.
        self._sidebar_groups_frame = QWidget()
        self._sidebar_bar_frame = QWidget()
        self._sidebar_preview_frame = QWidget()
        self._sidebar_sample_frame = QWidget()
        self._sidebar_stats_frame = QWidget()
        for w in (self._sidebar_groups_frame, self._sidebar_bar_frame,
                  self._sidebar_preview_frame, self._sidebar_sample_frame,
                  self._sidebar_stats_frame):
            QVBoxLayout(w).setContentsMargins(0, 0, 0, 0)
            sidebar_layout.addWidget(w, 1)
            w.hide()

        self._h_pane.addWidget(sidebar)
        self._build_sidebar(self._sidebar_main_frame)

        # Centre plots
        centre = QWidget()
        QVBoxLayout(centre).setContentsMargins(0, 0, 0, 0)
        self._h_pane.addWidget(centre)
        self._h_pane.setStretchFactor(0, 0)
        self._h_pane.setStretchFactor(1, 3)
        self._h_pane.setChildrenCollapsible(False)
        self._h_pane.setSizes([340, 1200])
        self._build_centre(centre)

        # Status + log — packed last so it sits below the splitter.
        self._build_bottom()

    def _build_sidebar(self, parent) -> None:
        from well_viewer.views.sidebar_view import build_sidebar as _build_sidebar_view
        _build_sidebar_view(self, parent)

    def _build_centre(self, parent) -> None:
        from well_viewer.views.centre_view import build_centre as _build_centre_view
        _build_centre_view(self, parent)

    # ── Statistics tab ────────────────────────────────────────────────────────

    def _build_stats_tab(self, parent) -> None:
        _build_stats_tab_view(self, parent, bg_app=BG_APP, bg_side=BG_SIDE)

    # ── Stats left: group editor ──────────────────────────────────────────────

    def _build_stats_group_editor(self, parent) -> None:
        _build_stats_group_editor_view(
            self,
            parent,
            fm_bold=FM_BOLD,
            fm_tiny=FM_TINY,
            txt_mut=TXT_MUT,
            txt_sec=TXT_SEC,
            txt_pri=TXT_PRI,
            bg_side=BG_SIDE,
            bg_panel=BG_PANEL,
            bg_cell=BG_CELL,
            bg_hover=BG_HOVER,
            accent=ACCENT,
            border=BORDER,
            clr_white=CLR_WHITE,
            clr_avail_well=CLR_AVAIL_WELL,
            clr_avail_hover=CLR_AVAIL_HOVER,
            well_colors=WELL_COLORS,
            bind_drag_fn=_bind_drag,
            build_plate_grid_fn=build_plate_grid,
            make_scrollable_canvas_fn=make_scrollable_canvas,
            extract_well_token_fn=_extract_well_token,
        )

    def _stats_active_group(self) -> Optional[BarGroup]:
        if 0 <= self._stats_active_grp < len(self._stats_groups):
            return self._stats_groups[self._stats_active_grp]
        return None

    def _stats_apply_drag(self, tok: str) -> None:
        if tok in self._stats_drag_visited:
            return
        self._stats_drag_visited.add(tok)
        grp = self._stats_active_group()
        if grp is None or tok not in self._well_paths:
            return
        rset = next((r for r in self._rep_sets if tok in r.wells), None)
        if rset is not None:
            if self._stats_drag_adding:
                if rset not in grp.members:
                    grp.members.append(rset)
            else:
                if rset in grp.members:
                    grp.members.remove(rset)
        else:
            if self._stats_drag_adding:
                if tok not in grp.solo_wells:
                    grp.solo_wells.append(tok)
            else:
                if tok in grp.solo_wells:
                    grp.solo_wells.remove(tok)
        self._stats_refresh_single_btn(tok)

    def _stats_refresh_single_btn(self, tok: str) -> None:
        self._stats_refresh_map()

    def _stats_refresh_map(self) -> None:
        bg, fg, fg_disabled = self._plate_theme_colors()
        avail = set(self._well_paths.keys())
        tok_color: Dict[str, str] = {}
        for gi, grp in enumerate(self._stats_groups):
            c = WELL_COLORS[gi % len(WELL_COLORS)]
            for w in grp.wells:
                tok_color.setdefault(w, c)
        grp = self._stats_active_group()
        active_wells: set = set(grp.wells) if grp else set()
        for tok, btn in self._stats_map_btns.items():
            if tok not in avail:
                self._plate_apply_disabled(btn, bg, fg, fg_disabled)
            elif tok in tok_color:
                self._plate_apply_colored(
                    btn, tok_color[tok],
                    active=tok in active_wells, fg_disabled=fg_disabled,
                )
            else:
                self._plate_apply_neutral(btn, bg, fg, fg_disabled)

    def _stats_refresh_group_list(self) -> None:
        container = self._stats_grp_inner
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(2)
        _clear_layout(layout)
        if not self._stats_groups:
            lbl = QLabel("No groups.  Click + Add to create one.")
            lbl.setObjectName("Muted")
            layout.addWidget(lbl)
            self._stats_refresh_map()
            return
        for gi, grp in enumerate(self._stats_groups):
            is_sel = (gi == self._stats_active_grp)
            color  = WELL_COLORS[gi % len(WELL_COLORS)]
            card = QFrame()
            card.setObjectName("StatsGroupCard")
            if is_sel:
                card.setProperty("state", "selected")
            hl = QHBoxLayout(card)
            hl.setContentsMargins(6, 4, 6, 4)
            dot = QLabel("\u25cf")
            dot.setStyleSheet(f"color: {color};")
            hl.addWidget(dot)
            hl.addWidget(QLabel(grp.name))
            n_mem = len(grp.members)
            n_sol = len(grp.solo_wells)
            parts = []
            if n_mem: parts.append(f"{n_mem} set{'s' if n_mem!=1 else ''}")
            if n_sol: parts.append(f"{n_sol} solo well{'s' if n_sol!=1 else ''}")
            if not parts: parts = ["empty"]
            meta = QLabel(f"  ({', '.join(parts)})")
            meta.setObjectName("Muted")
            hl.addWidget(meta)
            hl.addStretch(1)
            idx = gi
            ren_btn = QPushButton("\u270e")
            ren_btn.setFlat(True)
            ren_btn.clicked.connect(lambda _=False, i=idx: self._stats_grp_rename(i))
            hl.addWidget(ren_btn)
            del_btn = QPushButton("\u2715")
            del_btn.setFlat(True)
            del_btn.clicked.connect(lambda _=False, i=idx: self._stats_grp_delete(i))
            hl.addWidget(del_btn)

            def _click_select(ev, i=idx):
                self._stats_select_grp(i)
            card.mousePressEvent = _click_select
            layout.addWidget(card)
        layout.addStretch(1)
        self._stats_refresh_map()

    def _stats_select_grp(self, idx: int) -> None:
        self._stats_active_grp = idx
        self._stats_refresh_group_list()

    def _stats_grp_add(self) -> None:
        n = len(self._stats_groups) + 1
        self._stats_groups.append(BarGroup(f"Group {n}"))
        self._stats_active_grp = len(self._stats_groups) - 1
        self._stats_refresh_group_list()

    def _stats_grp_delete(self, idx: int) -> None:
        if 0 <= idx < len(self._stats_groups):
            self._stats_groups.pop(idx)
            self._stats_active_grp = max(0, min(
                self._stats_active_grp, len(self._stats_groups) - 1))
            self._stats_refresh_group_list()

    def _stats_grp_rename(self, idx: int) -> None:
        if not (0 <= idx < len(self._stats_groups)):
            return
        old = self._stats_groups[idx].name
        name = ask_name_dialog(self, title="Rename group", default=old)
        if name:
            self._stats_groups[idx].name = name
            self._stats_refresh_group_list()

    def _stats_grp_clear_all(self) -> None:
        self._stats_groups.clear()
        self._stats_active_grp = -1
        self._stats_refresh_group_list()

    def _stats_sync_from_app(self) -> None:
        self._stats_groups = copy.deepcopy(self._groups_from_rep_sets())
        self._stats_active_grp = 0 if self._stats_groups else -1
        self._stats_refresh_group_list()

    # ── Stats right: test selector + results ─────────────────────────────────

    def _build_stats_results_panel(self, parent) -> None:
        _build_stats_results_panel_view(
            self,
            parent,
            fm_bold=FM_BOLD,
            fm_tiny=FM_TINY,
            txt_mut=TXT_MUT,
            txt_sec=TXT_SEC,
            txt_pri=TXT_PRI,
            bg_app=BG_APP,
            bg_side=BG_SIDE,
            bg_panel=BG_PANEL,
            border=BORDER,
            accent=ACCENT,
            clr_white=CLR_WHITE,
        )

    def _stats_on_test_change(self) -> None:
        """Clear results when test changes; update UI hints."""
        self._stats_write_result("")

    def _stats_update_tp_menu(self) -> None:
        """Populate the timepoint dropdown from loaded wells."""
        all_tps: set = set()
        for label in self._well_paths:
            for row in self._get_rows(label):
                raw = row.get("timepoint_hours")
                try:
                    all_tps.add(float(raw))
                except (TypeError, ValueError):
                    pass
        sorted_tps = sorted(all_tps)
        tp_strs    = [f"{t:.4g}" for t in sorted_tps]
        _set_combo_values(self._stats_tp_cb, tp_strs or ["—"])
        if hasattr(self._stats_tp_cb, "setCurrentText"):
            self._stats_tp_cb.setCurrentText(tp_strs[0] if tp_strs else "—")

    def _stats_write_result(self, text: str) -> None:
        self._stats_result_text.setReadOnly(False)
        self._stats_result_text.setPlainText(text or "")
        self._stats_result_text.setReadOnly(True)

    def _stats_refresh_colors(self) -> None:
        """Refresh matplotlib figure facecolor on theme change.

        Widget colours are driven by the app-level QSS stylesheet; only the
        embedded matplotlib figure needs an explicit repaint.
        """
        from ui.theme import get_color

        if hasattr(self, "_stats_fig"):
            self._stats_fig.set_facecolor(get_color("BG_APP"))
        if hasattr(self, "_stats_canvas_widget"):
            self._stats_canvas_widget.draw()

    def _stats_collect_group_values(
        self, grp: BarGroup, target_t: float
    ) -> List[float]:
        return _stats_collect_group_values(self, grp, target_t)

    def _stats_run(self) -> None:
        _stats_run_controller(
            self,
            collect_group_values_fn=self._stats_collect_group_values,
            draw_ks_cdf_fn=self._stats_draw_ks_cdf,
        )

    def _stats_draw_ks_cdf(
        self,
        group_vals: List[Tuple[str, List[float]]],
        tp_str: str,
    ) -> None:
        _stats_draw_ks_cdf(self, group_vals, tp_str, WELL_COLORS)

    # ── Preview sidebar picker ────────────────────────────────────────────────

    def _build_preview_picker(self, parent) -> None:
        _build_preview_picker_view(
            self,
            parent,
            fm_bold=FM_BOLD,
            fm_tiny=FM_TINY,
            txt_mut=TXT_MUT,
            txt_pri=TXT_PRI,
            bg_side=BG_SIDE,
            bg_cell=BG_CELL,
            bg_panel=BG_PANEL,
            bg_hover=BG_HOVER,
            border=BORDER,
            accent=ACCENT,
            clr_white=CLR_WHITE,
            clr_accent_dark=CLR_ACCENT_DARK,
            build_plate_grid_fn=build_plate_grid,
            extract_well_token_fn=_extract_well_token,
        )

    def _preview_pick_well(self, tok: str) -> None:
        _preview_pick_well_view(self, tok)

    def _refresh_preview_picker(self) -> None:
        from ui.theme import get_color
        _refresh_preview_picker_view(
            self,
            button_bg=get_color("button_bg"),
            button_text=get_color("button_text"),
            button_text_disabled=get_color("button_text_disabled"),
            accent=get_color("ACCENT"),
            clr_white=get_color("CLR_WHITE"),
            clr_accent_dark=get_color("ACCENT_DARK"),
            extract_well_token_fn=_extract_well_token,
        )

    # ── Bar-plot grouping panel ───────────────────────────────────────────────

    def _build_bar_group_panel(self, parent) -> None:
        from well_viewer.views.bar_group_panel_view import build_bar_group_panel as _v
        _v(self, parent)

    def _build_groups_centre(self, parent) -> None:
        """Centre panel for the Sample Definitions tab: well-label editor only."""
        from PySide6.QtWidgets import QVBoxLayout as _QVBoxLayout

        outer_layout = parent.layout()
        if outer_layout is None:
            outer_layout = _QVBoxLayout(parent)
            parent.setLayout(outer_layout)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._build_label_editor(parent)

    # ─────────────────────────────────────────────────────────────────────────
    # Replicate panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_replicate_panel(self, parent) -> None:
        from well_viewer.views.replicate_panel_view import build_replicate_panel as _v
        _v(self, parent)

    # ── Replicate-panel plate map ─────────────────────────────────────────────

    def _rep_refresh_map(self) -> None:
        """Recolour the replicate-panel plate map.

        Each defined ReplicateSet gets a distinct colour. The active set's
        wells are sunken. If a group is the active target instead, its solo
        wells are shown in the group palette colour so they can be edited
        directly from the sidebar.
        """
        if not hasattr(self, "_rep_map_btns"):
            return
        bg, fg, fg_disabled = self._plate_theme_colors()

        tok_color: Dict[str, str] = {}
        tok_active: Dict[str, bool] = {}
        for si, rset in enumerate(self._rep_sets):
            c = WELL_COLORS[si % len(WELL_COLORS)]
            for tok in rset.wells:
                tok_color[tok] = c
                tok_active[tok] = (si == self._active_rep_idx)

        has_rep_active = 0 <= self._active_rep_idx < len(self._rep_sets)
        has_grp_active = 0 <= getattr(self, "_bar_active_grp", -1) < len(self._bar_groups)
        grp_solo_toks: set = set()
        grp_color = ACCENT
        if has_grp_active:
            grp = self._bar_groups[self._bar_active_grp]
            grp_solo_toks = set(grp.solo_wells)
            grp_color = WELL_COLORS[self._bar_active_grp % len(WELL_COLORS)]
        has_active = has_rep_active or has_grp_active

        for tok, btn in self._rep_map_btns.items():
            if tok not in self._well_paths:
                self._plate_apply_disabled(btn, bg, fg, fg_disabled)
            elif tok in grp_solo_toks:
                self._plate_apply_colored(
                    btn, grp_color, active=True, fg_disabled=fg_disabled,
                )
            elif tok in tok_color:
                self._plate_apply_colored(
                    btn, tok_color[tok],
                    active=tok_active.get(tok, False), fg_disabled=fg_disabled,
                )
            else:
                self._plate_apply_neutral(
                    btn, bg, fg, fg_disabled,
                    cursor="hand2" if has_active else "arrow",
                )

    def _rep_map_tok_at(self, event) -> Optional[str]:
        return _gc_rep_map_tok_at(self, event)

    def _rep_map_press(self, event) -> None:
        _gc_rep_map_press(self, event)

    def _rep_map_drag(self, event) -> None:
        _gc_rep_map_drag(self, event)

    def _rep_map_release(self, _event) -> None:
        _gc_rep_map_release(self, _event)

    def _rep_map_apply(self, tok: str) -> None:
        _gc_rep_map_apply(self, tok)

    def _rep_refresh_map_single(self, tok: str) -> None:
        """Update a single rep-map button (cheap mid-drag feedback).

        Delegates to the full refresh to keep group-solo/rep-set colouring
        consistent — the grid is at most 96 cells so the cost is negligible.
        """
        self._rep_refresh_map()

    def _rep_panel_refresh(self) -> None:
        from well_viewer.views.grouping_view import rep_panel_refresh as _rep_panel_refresh_view

        _rep_panel_refresh_view(self)

    def _rep_select(self, idx: int) -> None:
        self._active_rep_idx = idx
        # Replicate-set and group selections are mutually exclusive so the
        # sidebar plate grid has a single unambiguous edit target.
        self._bar_active_grp = -1
        self._groups_centre_refresh()   # card list
        self._rep_refresh_map()         # plate map: highlight selected set

    def _rep_add(self) -> None:
        """Open dialog to create a new named ReplicateSet."""
        dlg = QDialog(self)
        dlg.setWindowTitle("New Replicate Set")
        dlg.setModal(True)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Name:"))
        name_edit = QLineEdit(f"Rep {len(self._rep_sets)+1}")
        v.addWidget(name_edit)
        v.addWidget(QLabel("Select wells:"))
        available = sorted(self._well_paths.keys(),
                           key=lambda l: self._parse_rc(l))
        lb = _wells_multiselect_listbox(dlg, available)
        v.addWidget(lb, 1)
        btn_row = QHBoxLayout()
        v.addLayout(btn_row)
        ok_btn = QPushButton("Create")
        ok_btn.setProperty("variant", "primary")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)

        def _ok():
            sel = _selected_list_values(lb)
            if not sel:
                QMessageBox.warning(dlg, "No wells", "Select at least one well.")
                return
            name = name_edit.text().strip() or f"Rep {len(self._rep_sets)+1}"
            self._rep_sets.append(ReplicateSet(name, sel))
            self._active_rep_idx = len(self._rep_sets) - 1
            dlg.accept()
            self._rebuild_all()

        ok_btn.clicked.connect(_ok)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _rep_rename(self, idx: int) -> None:
        if not (0 <= idx < len(self._rep_sets)):
            return
        name = ask_name_dialog(self, default=self._rep_sets[idx].name)
        if name:
            self._rep_sets[idx].name = name
            self._rebuild_all()

    def _rep_delete(self, idx: int) -> None:
        if not (0 <= idx < len(self._rep_sets)):
            return
        rset = self._rep_sets[idx]
        # Remove from any groups that reference it
        for grp in self._bar_groups:
            if rset in grp.members:
                grp.members.remove(rset)
        self._rep_sets.pop(idx)
        self._active_rep_idx = min(self._active_rep_idx,
                                   len(self._rep_sets) - 1)
        self._rebuild_all()

    def _rep_clear_all(self) -> None:
        if not self._rep_sets:
            return
        resp = QMessageBox.question(
            self, "Clear all replicate sets?",
            f"Remove all {len(self._rep_sets)} set(s)?\n"
            "Groups referencing them will also lose those members.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            for grp in self._bar_groups:
                grp.members.clear()
            self._rep_sets.clear()
            self._active_rep_idx = -1
            self._rep_hidden.clear()
            self._rebuild_all()

    # ─────────────────────────────────────────────────────────────────────────
    # Group definition panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_group_def_panel(self, parent) -> None:
        from well_viewer.views.grouping_view import build_group_def_panel as _v
        _v(self, parent)

    def _grp_panel_refresh(self) -> None:
        from well_viewer.views.grouping_view import grp_panel_refresh as _v
        _v(self)

    def _ask_name_dialog(self, default: str) -> Optional[str]:
        return ask_name_dialog(self, default=default)

    def _grp_select(self, idx: int) -> None:
        _gc_grp_select(self, idx)

    def _grp_add(self) -> None:
        _gc_grp_add(self)

    def _grp_rename(self, idx: int) -> None:
        _gc_grp_rename(self, idx)

    def _grp_delete(self, idx: int) -> None:
        _gc_grp_delete(self, idx)

    def _grp_toggle_visibility(self, idx: int) -> None:
        _gc_grp_toggle_visibility(self, idx)

    def _grp_add_member(self, grp_idx: int, rset: "ReplicateSet") -> None:
        _gc_grp_add_member(self, grp_idx, rset)

    def _grp_remove_member(self, grp_idx: int, rset: "ReplicateSet") -> None:
        _gc_grp_remove_member(self, grp_idx, rset)

    def _grp_add_solo_well(self, grp_idx: int, well: str) -> None:
        """Add a single well to a group as a solo (singleton replicate)."""
        _gc_grp_add_solo_well(self, grp_idx, well)

    def _grp_remove_solo(self, grp_idx: int, well: str) -> None:
        _gc_grp_remove_solo(self, grp_idx, well)

    def _grp_clear_all(self) -> None:
        _gc_grp_clear_all(self)

    # ─────────────────────────────────────────────────────────────────────────
    # Well-label editor
    # ─────────────────────────────────────────────────────────────────────────

    def _build_label_editor(self, parent) -> None:
        from well_viewer.views.label_editor_view import build_label_editor as _v
        _v(self, parent)

    def _label_panel_refresh(self) -> None:
        from well_viewer.views.label_editor_view import label_panel_refresh as _v
        _v(self)

    def _labels_clear_all(self) -> None:
        if self._well_labels:
            self._well_labels.clear()
            self._label_panel_refresh()
            self._invalidate_stats_cache()

    def _groups_centre_refresh(self) -> None:
        """Refresh all Sample Definitions panels.

        Card lists are only rebuilt when the tab is active (expensive).
        Plate maps are always updated (cheap).
        """
        tab_visible = False
        if hasattr(self, "_notebook"):
            try:
                tab_visible = (
                    self._notebook.tabText(self._notebook.currentIndex())
                    == "Sample Definitions")
            except Exception:
                pass

        if tab_visible:
            self._rep_panel_refresh()
            self._grp_panel_refresh()
            self._label_panel_refresh()
        self._rep_refresh_map()

    def _build_bar_perwell_strip(self, parent) -> None:
        from well_viewer.views.bar_group_panel_view import build_bar_perwell_strip as _v
        _v(self, parent)

    # ── Group card list rebuild ───────────────────────────────────────────────

    def _bar_rebuild_groups_ui(self) -> None:
        """
        Debounced card-list rebuild — schedules the actual work via after(0).

        Called frequently during drag interactions; the debounce ensures only
        one widget rebuild runs per event-loop cycle even if multiple wells
        are toggled in rapid succession.
        """
        if getattr(self, "_grp_ui_pending", False):
            return
        self._grp_ui_pending = True
        QTimer.singleShot(0, self._bar_rebuild_groups_ui_now)

    def _bar_rebuild_groups_ui_now(self) -> None:
        from well_viewer.views.bar_group_panel_view import rebuild_groups_ui_now as _v
        _v(self)

    def _update_bar_group_count_label(self) -> None:
        from well_viewer.views.bar_group_panel_view import update_bar_group_count_label as _v
        _v(self)

    def _build_bar_group_row(self, idx: int, grp: "BarGroup") -> None:
        from well_viewer.views.bar_group_panel_view import build_bar_group_row as _v
        _v(self, idx, grp)

    def _build_bar_group_header(self, row, idx: int, grp: "BarGroup", bg: str) -> tuple:
        from well_viewer.views.bar_group_panel_view import build_bar_group_header as _v
        return _v(self, row, idx, grp, bg)

    def _build_bar_group_chip_rows(self, row, idx: int, grp: "BarGroup", bg: str, is_active: bool) -> list:
        from well_viewer.views.bar_group_panel_view import build_bar_group_chip_rows as _v
        return _v(self, row, idx, grp, bg, is_active)

    def _build_bar_group_action_row(self, row, idx: int, bg: str, is_active: bool) -> list:
        from well_viewer.views.bar_group_panel_view import build_bar_group_action_row as _v
        return _v(self, row, idx, bg, is_active)

    def _rebuild_all(self) -> None:
        """
        Single authoritative refresh called after ANY data change.
        Updates both Groups tab panels + bar group sidebar + all plots.
        Always synchronous — no debounce — because it is only called on
        explicit user actions (button clicks / dialog OK), never during drag.
        """
        self._invalidate_stats_cache()
        self._groups_centre_refresh()          # Groups tab: rep panel + map
        self._bar_rebuild_groups_ui_now()      # sidebar card list + bar map
        self._refresh_sidebar_map()            # line-graph picker: rep colours
        self._redraw_bars()
        self._redraw()
        if hasattr(self, "_notebook"):
            try:
                tab = self._notebook.tabText(self._notebook.currentIndex())
            except Exception:
                tab = ""
            if tab == "Line Graphs":
                self._show_line_sidebar()

    def _bar_rebuild_groups(self) -> None:
        """Rebuild card list + map then refresh all plots.

        Call this when the data itself changes (wells added/removed, group
        renamed, group deleted).  For selection-only changes use
        _bar_rebuild_groups_ui() which skips the expensive plot redraws.
        """
        self._invalidate_stats_cache()   # group definitions changed — stale results
        self._bar_rebuild_groups_ui_now()  # always do the UI rebuild synchronously here
        self._redraw_bars()
        self._groups_centre_refresh()
        self._redraw()
        if hasattr(self, "_notebook"):
            try:
                tab = self._notebook.tabText(self._notebook.currentIndex())
            except Exception:
                tab = ""
            if tab == "Line Graphs":
                self._show_line_sidebar()

    # ── Group management ──────────────────────────────────────────────────────

    def _bar_add_group(self) -> None:
        name = ask_name_dialog(self, default=f"Group {len(self._bar_groups) + 1}")
        if name is None:
            return
        self._bar_groups.append(BarGroup(name, members=[]))
        self._bar_active_grp = len(self._bar_groups) - 1
        self._bar_active_rep  = -1
        self._bar_rebuild_groups()

    def _bar_clear_all_groups(self) -> None:
        """Remove all bar groups after confirmation."""
        if not self._bar_groups:
            return
        resp = QMessageBox.question(
            self, "Clear all groups?",
            f"Remove all {len(self._bar_groups)} group(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._bar_groups.clear()
            self._bar_active_grp = -1
            self._bar_active_rep  = -1
            self._bar_rebuild_groups()

    def _bar_select_group(self, idx: int) -> None:
        if idx != self._bar_active_grp:
            self._bar_active_rep = -1
        self._bar_active_grp = idx
        self._bar_rebuild_groups_ui()   # sidebar: fast, no plot redraws
        self._groups_centre_refresh()   # Groups tab centre panels

    def _bar_rename_group(self, idx: int) -> None:
        if not (0 <= idx < len(self._bar_groups)):
            return
        # Group names are edited inline in the Sample Definitions panel.
        self._bar_active_grp = idx
        self._grp_inline_edit_idx = idx
        if hasattr(self, "_notebook") and hasattr(self._notebook, "select_by_text"):
            try:
                self._notebook.select_by_text("Sample Definitions")
            except Exception:
                pass
        self._groups_centre_refresh()

    def _bar_clear_group(self, idx: int) -> None:
        self._bar_groups[idx].replicates.clear()
        self._bar_rebuild_groups()

    def _bar_add_replicate_set(self, group_idx: int) -> None:
        """Open a dialog to define a new named ReplicateSet within the group."""
        if group_idx < 0 or group_idx >= len(self._bar_groups):
            return
        grp = self._bar_groups[group_idx]
        # Wells already assigned to any replicate set in this group
        assigned = {w for rset in grp.replicates for w in rset.wells}
        available = [lbl for lbl in self._well_paths if lbl not in assigned]
        if not available:
            QMessageBox.information(self, "All assigned",
                                    "All loaded wells are already in a replicate set.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("New Replicate Set")
        dlg.setModal(True)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Replicate set name:"))
        name_edit = QLineEdit(f"R{len(grp.replicates)+1}")
        v.addWidget(name_edit)
        v.addWidget(QLabel("Select wells in this replicate set:"))
        sorted_available = sorted(available, key=lambda l: self._parse_rc(l))
        lb = _wells_multiselect_listbox(dlg, sorted_available)
        v.addWidget(lb, 1)
        btn_row = QHBoxLayout()
        v.addLayout(btn_row)
        add_btn = QPushButton("Add Replicate Set")
        add_btn.setProperty("variant", "primary")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(add_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)

        def _ok():
            sel = _selected_list_values(lb)
            if not sel:
                QMessageBox.warning(dlg, "No wells selected",
                                    "Select at least one well.")
                return
            name = name_edit.text().strip() or f"R{len(grp.replicates)+1}"
            grp.replicates.append(ReplicateSet(name, sel))
            dlg.accept()
            self._bar_active_rep = len(grp.replicates) - 1
            self._bar_rebuild_groups()

        add_btn.clicked.connect(_ok)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _bar_remove_replicate_set(self, group_idx: int, set_idx: int) -> None:
        """Remove one ReplicateSet from the group."""
        if 0 <= group_idx < len(self._bar_groups):
            grp = self._bar_groups[group_idx]
            if 0 <= set_idx < len(grp.replicates):
                grp.replicates.pop(set_idx)
                if self._bar_active_rep >= len(grp.replicates):
                    self._bar_active_rep = len(grp.replicates) - 1
                self._bar_rebuild_groups()

    def _bar_clear_replicates(self, idx: int) -> None:
        """Remove all ReplicateSets from the group."""
        if 0 <= idx < len(self._bar_groups):
            self._bar_groups[idx].replicates.clear()
            self._bar_active_rep = -1
            self._bar_rebuild_groups()

    def _bar_toggle_group_visibility(self, idx: int) -> None:
        """Toggle whether group *idx* appears in the bar plot."""
        if 0 <= idx < len(self._bar_groups):
            self._bar_groups[idx].hidden = not self._bar_groups[idx].hidden
            self._bar_rebuild_groups()

    def _bar_remove_group(self, idx: int) -> None:
        self._bar_groups.pop(idx)
        self._bar_active_grp = min(self._bar_active_grp,
                                    len(self._bar_groups) - 1)
        self._bar_rebuild_groups()

    def _bar_select_all(self) -> None:
        if self._rep_sets:
            self._rep_hidden.clear()
        else:
            self._selected_wells = set(self._well_paths.keys())
        self._bar_refresh_map()
        self._redraw_bars()

    def _bar_select_none(self) -> None:
        if self._rep_sets:
            self._rep_hidden = set(range(len(self._rep_sets_loaded())))
        else:
            self._selected_wells.clear()
        self._bar_refresh_map()
        self._redraw_bars()

    # ── Right-click rubber-band: toggle visibility for all groups in rectangle ─

    def _bg_vis_press(self, event) -> None:
        """Record the screen-space anchor and open the rubber-band overlay."""
        gp = event.globalPosition().toPoint()
        sx, sy = gp.x(), gp.y()
        self._vis_anchor_screen: tuple = (sx, sy)

        self._vis_btn_centres: Dict[str, tuple] = {}
        for tok, btn in self._bar_map_btns.items():
            if btn.isVisible() and btn.isEnabled():
                rect = btn.rect()
                centre_local = rect.center()
                centre_global = btn.mapToGlobal(centre_local)
                self._vis_btn_centres[tok] = (centre_global.x(), centre_global.y())

        if self._vis_rubber_win is not None:
            try:
                self._vis_rubber_win.deleteLater()
            except Exception:
                pass
        win = QWidget(self, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        win.setAttribute(Qt.WA_TranslucentBackground, False)
        win.setWindowOpacity(0.30)
        win.setStyleSheet(f"background-color: {WELL_COLOR_2};")
        win.setGeometry(0, 0, 1, 1)
        win.show()
        win.raise_()
        self._vis_rubber_win = win

    def _bg_vis_drag(self, event) -> None:
        """Resize the overlay to span anchor → cursor (screen coords)."""
        if not hasattr(self, "_vis_anchor_screen") or self._vis_rubber_win is None:
            return
        gp = event.globalPosition().toPoint()
        cx, cy = gp.x(), gp.y()
        ax, ay = self._vis_anchor_screen
        x0, y0 = min(ax, cx), min(ay, cy)
        w  = max(2, abs(cx - ax))
        h  = max(2, abs(cy - ay))
        self._vis_rubber_win.setGeometry(x0, y0, w, h)

    def _bg_vis_release(self, event) -> None:
        """Toggle visibility of replicate sets whose wells fall inside the rectangle."""
        if self._vis_rubber_win is not None:
            try:
                self._vis_rubber_win.deleteLater()
            except Exception:
                pass
            self._vis_rubber_win = None

        anchor     = getattr(self, "_vis_anchor_screen", None)
        btn_centres = getattr(self, "_vis_btn_centres", {})
        for attr in ("_vis_anchor_screen", "_vis_btn_centres"):
            try:
                delattr(self, attr)
            except AttributeError:
                pass

        if anchor is None:
            return

        gp = event.globalPosition().toPoint()
        cx, cy = gp.x(), gp.y()
        ax, ay = anchor
        x0, x1 = min(ax, cx), max(ax, cx)
        y0, y1 = min(ay, cy), max(ay, cy)

        # Find tokens of buttons whose screen-space centres fall inside.
        inside_toks: set = set()
        for tok, (bx, by) in btn_centres.items():
            if x0 <= bx <= x1 and y0 <= by <= y1:
                if tok in self._well_paths:
                    inside_toks.add(tok)

        if not inside_toks:
            return

        loaded = self._rep_sets_loaded()
        if loaded:
            affected: set = set()
            for si, rset in enumerate(loaded):
                if any(w in inside_toks for w in rset.wells):
                    affected.add(si)

            if not affected:
                return

            # If the first affected set is visible → hide all; else show all.
            first_hidden = next(iter(affected)) in self._rep_hidden
            for si in affected:
                if first_hidden:
                    self._rep_hidden.discard(si)
                else:
                    self._rep_hidden.add(si)

            self._invalidate_stats_cache()
            self._rep_refresh_map()
            self._refresh_sidebar_map()
            self._bar_refresh_map()
            self._redraw_bars()
            self._redraw()

        else:
            # Fallback: toggle _bar_groups.hidden (no rep-sets defined)
            affected_groups: set = set()
            for tok in inside_toks:
                for i, g in enumerate(self._bar_groups):
                    if tok in g.wells:
                        affected_groups.add(i)

            if affected_groups:
                first_hidden = self._bar_groups[next(iter(affected_groups))].hidden
                new_hidden   = not first_hidden
                for i in affected_groups:
                    self._bar_groups[i].hidden = new_hidden
                self._bar_rebuild_groups()


    # ── Quick-group helpers (bar panel) ──────────────────────────────────────

    def _rep_quick_row_pairs(self) -> None:
        """
        Backward compatibility wrapper: row pairs, row-first iteration.
        Calls the new unified _rep_quick_pairs() function with appropriate settings.
        """
        self._rep_quick_pair_dir = "row"
        self._rep_quick_iter_order = "row"
        self._rep_quick_pairs()

    def _rep_quick_col_pairs(self) -> None:
        """
        Backward compatibility wrapper: column pairs, column-first iteration.
        Calls the new unified _rep_quick_pairs() function with appropriate settings.
        """
        self._rep_quick_pair_dir = "col"
        self._rep_quick_iter_order = "col"
        self._rep_quick_pairs()

    def _rep_quick_pairs(self) -> None:
        """
        Generate quick replicate pairs using current dropdown selections.

        Uses _rep_quick_pair_dir (row or col) and _rep_quick_iter_order (row or col).
        """
        pair_dir = self._rep_quick_pair_dir  # "row" or "col"
        iter_order = self._rep_quick_iter_order  # "row" or "col"
        new_sets: List[ReplicateSet] = []

        # Generate pairs based on direction
        if pair_dir == "row":
            # Row pairs: pair adjacent columns (A01+A02, A03+A04, ...)
            if iter_order == "row":
                # Row-first iteration (same as _rep_quick_row_pairs)
                for row_ltr in _PLATE_ROWS:
                    loaded = [f"{row_ltr}{col}" for col in _PLATE_COLS
                              if f"{row_ltr}{col}" in self._well_paths]
                    new_sets.extend(self._make_replicate_pairs(loaded, row_ltr))
            else:
                # Column-first iteration: collect all row pairs, then sort by column
                by_col = {}  # col -> list of sets from that column
                for row_ltr in _PLATE_ROWS:
                    loaded = [f"{row_ltr}{col}" for col in _PLATE_COLS
                              if f"{row_ltr}{col}" in self._well_paths]
                    row_sets = self._make_replicate_pairs(loaded, row_ltr)
                    # Extract which column(s) each set belongs to
                    for s in row_sets:
                        if s.wells:
                            # Get column from first well (all should be same row)
                            col = _extract_well_token(s.wells[0])
                            if col and len(col) > 1:
                                col = col[1:]  # Extract column part
                                if col not in by_col:
                                    by_col[col] = []
                                by_col[col].append(s)
                # Add sets in column-first order
                for col in _PLATE_COLS:
                    if col in by_col:
                        new_sets.extend(by_col[col])
        else:
            # Column pairs: pair adjacent rows (A01+B01, C01+D01, ...)
            if iter_order == "col":
                # Column-first iteration (same as _rep_quick_col_pairs)
                for col in _PLATE_COLS:
                    loaded = [f"{row_ltr}{col}" for row_ltr in _PLATE_ROWS
                              if f"{row_ltr}{col}" in self._well_paths]
                    new_sets.extend(self._make_replicate_pairs(loaded, col))
            else:
                # Row-first iteration: collect all column pairs, then sort by row
                by_row = {}  # row -> list of sets from that row
                for col in _PLATE_COLS:
                    loaded = [f"{row_ltr}{col}" for row_ltr in _PLATE_ROWS
                              if f"{row_ltr}{col}" in self._well_paths]
                    col_sets = self._make_replicate_pairs(loaded, col)
                    # Extract which row each set belongs to
                    for s in col_sets:
                        if s.wells:
                            # Get row from first well (all should be same column)
                            tok = _extract_well_token(s.wells[0])
                            if tok and len(tok) > 0:
                                row = tok[0]  # Extract row part
                                if row not in by_row:
                                    by_row[row] = []
                                by_row[row].append(s)
                # Add sets in row-first order
                for row in _PLATE_ROWS:
                    if row in by_row:
                        new_sets.extend(by_row[row])

        if not new_sets:
            return
        if self._rep_sets:
            resp = QMessageBox.question(
                self, "Replace replicate sets?",
                f"This will replace the current {len(self._rep_sets)} "
                "replicate set(s). Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return
            for grp in self._bar_groups:
                grp.members.clear()
        self._rep_sets = new_sets
        self._active_rep_idx = 0 if self._rep_sets else -1
        self._rep_hidden.clear()
        self._invalidate_stats_cache()
        self._rep_quick_refresh_ui()

    def _rep_quick_pairs_from_dropdowns(self) -> None:
        """Read dropdown values and update state, then call _rep_quick_pairs()."""
        # Map dropdown display values to internal values
        pair_dir_display = self._rep_quick_pair_dir_var.get()
        self._rep_quick_pair_dir = "row" if "Rows" in pair_dir_display else "col"

        iter_order_display = self._rep_quick_iter_order_var.get()
        self._rep_quick_iter_order = "row" if "Across" in iter_order_display else "col"

        self._rep_quick_pairs()

    def _rep_quick_refresh_ui(self) -> None:
        """
        Lightweight post-assignment refresh for Quick Replicates.

        Rebuilds only what is currently visible:
          - Plate maps (rep panel map + bar sidebar map + line sidebar map)
            are always refreshed — they are cheap (just button colour changes).
          - The card list in the Replicates tab centre is only rebuilt if that
            tab is currently active; with 48 sets it creates hundreds of widgets
            and is invisible when another tab is open.
          - Plot redraws are deferred via after(0) so the UI paints first.
        """
        # Always update the plate-map colourings — these are fast
        self._rep_refresh_map()
        self._refresh_sidebar_map()
        self._bar_refresh_map()

        # Rebuild the Replicates tab card list only if it is visible
        try:
            active_tab = self._notebook.tabText(self._notebook.currentIndex())
        except Exception:
            active_tab = ""
        if active_tab == "Sample Definitions":
            self._rep_panel_refresh()

        # Defer expensive plot redraws — only if the relevant tab is visible.
        # _on_tab_change already triggers redraws on tab switch, so skipping
        # these when the user is on another tab has no visible effect.
        try:
            active_tab = self._notebook.tabText(self._notebook.currentIndex())
        except Exception:
            active_tab = ""
        if active_tab == "Bar Plots":
            QTimer.singleShot(0, self._redraw_bars)
        elif active_tab == "Line Graphs":
            QTimer.singleShot(0, self._redraw)

    def _make_replicate_pairs(self, toks: List[str], prefix: str) -> List[ReplicateSet]:
        """Pair adjacent tokens into ReplicateSets; singletons become solo sets."""
        sets: List[ReplicateSet] = []
        i = 0
        while i < len(toks):
            if i + 1 < len(toks):
                t1, t2 = toks[i], toks[i + 1]
                sets.append(ReplicateSet(f"{t1}/{t2}", [t1, t2]))
                i += 2
            else:
                t = toks[i]
                sets.append(ReplicateSet(t, [t]))
                i += 1
        return sets

    def _bar_quick_groups(self) -> None:
        """
        Generate quick bar groups using current dropdown selections.

        Uses _bar_quick_pair_dir (row or col) and _bar_quick_iter_order (row or col).
        Each group (row or column) contains paired replicate sets.
        """
        pair_dir = self._bar_quick_pair_dir  # "row" or "col"
        iter_order = self._bar_quick_iter_order  # "row" or "col"
        self._bar_groups.clear()
        self._bar_active_grp = -1

        if pair_dir == "row":
            # Row pairs with grouping by row or column
            if iter_order == "row":
                # Group by row (row-first): Same as _bar_quick_groups_row_pairs
                for row_ltr in _PLATE_ROWS:
                    loaded = [f"{row_ltr}{col}" for col in _PLATE_COLS
                              if f"{row_ltr}{col}" in self._well_paths]
                    if not loaded:
                        continue
                    sets = self._make_replicate_pairs(loaded, row_ltr)
                    self._bar_groups.append(BarGroup(f"Row {row_ltr}", members=sets))
            else:
                # Group by column (column-first): Column groups with row pairs within
                for col in _PLATE_COLS:
                    pairs_in_col = []
                    for row_ltr in _PLATE_ROWS:
                        loaded = [f"{row_ltr}{col}"]
                        # Look ahead to pair with next column
                        next_col_idx = _PLATE_COLS.index(col) + 1
                        if next_col_idx < len(_PLATE_COLS):
                            loaded.append(f"{row_ltr}{_PLATE_COLS[next_col_idx]}")
                        loaded = [t for t in loaded if t in self._well_paths]
                        if loaded:
                            pairs_in_col.extend(self._make_replicate_pairs(loaded, col))
                    if pairs_in_col:
                        self._bar_groups.append(BarGroup(f"Col {col}", members=pairs_in_col))
        else:
            # Column pairs with grouping by row or column
            if iter_order == "col":
                # Group by column (column-first): Same as _bar_quick_groups_col_pairs
                for col in _PLATE_COLS:
                    loaded = [f"{row_ltr}{col}" for row_ltr in _PLATE_ROWS
                              if f"{row_ltr}{col}" in self._well_paths]
                    if not loaded:
                        continue
                    sets = self._make_replicate_pairs(loaded, col)
                    self._bar_groups.append(BarGroup(f"Col {col}", members=sets))
            else:
                # Group by row (row-first): Row groups with column pairs within
                for row_ltr in _PLATE_ROWS:
                    pairs_in_row = []
                    for col in _PLATE_COLS:
                        loaded = [f"{row_ltr}{col}"]
                        # Look ahead to pair with next row
                        next_row_idx = _PLATE_ROWS.index(row_ltr) + 1
                        if next_row_idx < len(_PLATE_ROWS):
                            loaded.append(f"{_PLATE_ROWS[next_row_idx]}{col}")
                        loaded = [t for t in loaded if t in self._well_paths]
                        if loaded:
                            pairs_in_row.extend(self._make_replicate_pairs(loaded, col))
                    if pairs_in_row:
                        self._bar_groups.append(BarGroup(f"Row {row_ltr}", members=pairs_in_row))

        if self._bar_groups:
            self._bar_active_grp = 0
        self._bar_rebuild_groups_ui_now()        # instant: show cards
        QTimer.singleShot(50, self._bar_rebuild_groups) # deferred: update plots

    def _bar_quick_groups_from_dropdowns(self) -> None:
        """Read dropdown values and update state, then call _bar_quick_groups()."""
        # Map dropdown display values to internal values
        pair_dir_display = self._bar_quick_pair_dir_var.get()
        self._bar_quick_pair_dir = "row" if "Rows" in pair_dir_display else "col"

        iter_order_display = self._bar_quick_iter_order_var.get()
        self._bar_quick_iter_order = "row" if "Across" in iter_order_display else "col"

        self._bar_quick_groups()

    def _bar_quick_groups_row_pairs(self) -> None:
        """
        Backward compatibility wrapper: row pairs, row-first grouping.
        Calls the new unified _bar_quick_groups() function with appropriate settings.
        """
        self._bar_quick_pair_dir = "row"
        self._bar_quick_iter_order = "row"
        self._bar_quick_groups()

    def _bar_quick_groups_col_pairs(self) -> None:
        """
        Backward compatibility wrapper: column pairs, column-first grouping.
        Calls the new unified _bar_quick_groups() function with appropriate settings.
        """
        self._bar_quick_pair_dir = "col"
        self._bar_quick_iter_order = "col"
        self._bar_quick_groups()

    # ── Bar group persistence ─────────────────────────────────────────────────

    def _bar_groups_to_dict(self) -> List[dict]:
        """Serialise the full state (rep_sets pool + groups) to a dict list.

        Schema:
          {
            "rep_sets": [{"name": str, "wells": [token,…]}, …],
            "groups":   [{"name": str, "hidden": bool,
                          "members": [set_name,…],
                          "solo_wells": [token,…]}, …]
          }
        Returned as a dict (not list) for portability.
        """
        return _bar_groups_to_dict(
            self._rep_sets,
            self._bar_groups,
            extract_well_token=_extract_well_token,
        )

    def _bar_groups_from_dict(self, data) -> None:
        """Restore groups state from a saved dict (new schema) or list (legacy)."""
        self._rep_sets.clear()
        self._bar_groups.clear()
        self._bar_active_grp = -1
        self._active_rep_idx = -1
        self._rep_hidden.clear()
        self._rep_sets, self._bar_groups = _bar_groups_from_data(
            data,
            tok_to_label=self._tok_to_label,
        )
        if self._bar_groups:
            self._bar_active_grp = 0


    def _bar_save_groups(self) -> None:
        """Write current bar groups to a JSON file chosen by the user."""
        if not self._bar_groups:
            QMessageBox.warning(
                self, "Nothing to save",
                "Define at least one group before saving.",
            )
            return
        out_dir = self._data_dir if self._data_dir else None
        init_dir = str(out_dir) if out_dir else ""
        init_path = str(Path(init_dir) / "bar_groups.json") if init_dir else "bar_groups.json"
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Save bar group definitions",
            init_path,
            "Group definitions JSON (*.json);;All files (*.*)",
        )
        if not path_str:
            return
        try:
            with open(path_str, "w", encoding="utf-8") as fh:
                json.dump(self._bar_groups_to_dict(), fh, indent=2)
            _logger.info("Bar groups saved to %s", path_str)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _bar_load_groups(self) -> None:
        """Load bar groups from a previously saved JSON file."""
        out_dir = self._data_dir if self._data_dir else None
        init_dir = str(out_dir) if out_dir else ""
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Load bar group definitions",
            init_dir,
            "Group definitions JSON (*.json);;All files (*.*)",
        )
        if not path_str:
            return
        try:
            with open(path_str, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array at the top level.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            QMessageBox.critical(
                self, "Load failed",
                f"Could not read group definitions:\n{exc}",
            )
            return
        if self._bar_groups:
            resp = QMessageBox.question(
                self, "Replace existing groups?",
                f"Loading will replace the current {len(self._bar_groups)} "
                f"group(s).  Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return
        self._bar_groups_from_dict(data)
        self._bar_rebuild_groups()
        _logger.info("Bar groups loaded from %s (%d group(s))",
                     path_str, len(self._bar_groups))

    def _bar_groups_prune(self) -> None:
        """Remove stale well references after a new dataset is loaded."""
        # Prune global replicate sets
        for rset in self._rep_sets:
            rset.wells = [w for w in rset.wells if w in self._well_paths]
        # Remove now-empty rep sets from pool and from any group members
        empty = {r for r in self._rep_sets if not r.wells}
        self._rep_sets = [r for r in self._rep_sets if r.wells]
        for grp in self._bar_groups:
            grp.members    = [r for r in grp.members if r not in empty and r.wells]
            grp.solo_wells = [w for w in grp.solo_wells if w in self._well_paths]
        self._bar_active_grp = min(self._bar_active_grp, len(self._bar_groups) - 1)

    # ── Bar-map drag helpers ──────────────────────────────────────────────────

    def _bar_map_tok_at(self, event) -> Optional[str]:
        try:
            gp = event.globalPosition().toPoint()
        except Exception:
            return None
        w = QApplication.widgetAt(gp)
        for tok, btn in self._bar_map_btns.items():
            if btn is w:
                return tok
        return None

    # ── Bar-plot drag handlers — unified picker, delegate to _sb_ ─────────────
    # The bar plate map is the same unified picker as the line sidebar.
    # _bg_press/drag/release simply forward to _sb_ equivalents so there is
    # only one set of drag logic.  Legacy group-assignment code (_bg_apply_legacy)
    # is still reachable but only fires when _rep_sets is empty and bar groups
    # exist (a configuration that is no longer exposed in the UI but kept for
    # backward compatibility with saved session files).

    def _bg_press(self, event) -> None:
        self._sb_press(event)

    def _bg_drag(self, event) -> None:
        self._sb_drag(event)

    def _bg_release(self, _event) -> None:
        self._sb_release(None)

    def _bg_on_rep_change(self) -> None:
        self._sb_on_rep_change()

    def _bg_on_well_change(self) -> None:
        _gc_bg_on_well_change(self)

    def _bg_apply_legacy(self, tok: str) -> None:
        """Non-rep-set bar drag: group assignment or per-well selection."""
        _gc_bg_apply_legacy(self, tok)

    def _rep_color_for(self, lbl: str) -> Optional[str]:
        """Return the WELL_COLORS colour for the ReplicateSet that owns *lbl*,
        or None if the well is not assigned to any set."""
        for si, rset in enumerate(getattr(self, "_rep_sets", [])):
            if lbl in rset.wells:
                return WELL_COLORS[si % len(WELL_COLORS)]
        return None

    def _bar_refresh_map(self) -> None:
        """Alias: bar plots share the unified well picker; delegate to sidebar map."""
        self._refresh_sidebar_map()


    def _bar_refresh_single_btn(self, tok: str) -> None:
        """Recolour one bar-map button. Delegates to the full map refresh so
        hidden-group colour logic only lives in one place."""
        self._bar_refresh_map()

    def _build_right_panel(self, parent) -> None:
        from well_viewer.views.preview_panel_view import build_right_panel as _build_right_panel_view

        _build_right_panel_view(self, parent)

    def _build_review_image_panel(self, parent) -> None:
        from well_viewer.views.preview_panel_view import build_review_image_panel as _build_review_image_panel_view

        _build_review_image_panel_view(self, parent)

    def _update_tophat_controls(self, preloaded: Optional[bool] = None) -> None:
        """Sync the top-hat row UI to the actual preload state.

        *preloaded* = True  → tophat images were loaded from disk for this FOV;
                              lock controls, show badge, display filtered images.
        *preloaded* = False → no preloaded images; enable manual filtering.
        *preloaded* = None  → read from self._montage_tophat_preloaded (default).

        This is the single source of truth for the tophat control state.
        Called from _refresh_preview_montage (after FOV-level coverage is known)
        and from _update_preview (to reset before a new well loads).
        """
        if not hasattr(self, "_th_checkbox"):
            return
        if preloaded is None:
            preloaded = getattr(self, "_montage_tophat_preloaded", False)

        # Block toggled() so the programmatic state sync doesn't re-kick off
        # the tophat filter thread via _montage_tophat_toggled.
        _prev = self._th_checkbox.blockSignals(True)
        try:
            if preloaded:
                self._mon_tophat_var.set(True)
                self._th_checkbox.setEnabled(False)
                self._th_checkbox.setText("Top-hat background subtraction")
                self._th_radius_entry.setEnabled(False)
                self._th_preload_badge.setText("\u25cf from output zip")
            else:
                self._mon_tophat_var.set(False)
                self._th_checkbox.setEnabled(True)
                self._th_checkbox.setText("Top-hat background subtraction")
                self._th_radius_entry.setEnabled(True)
                self._th_preload_badge.setText("")
        finally:
            self._th_checkbox.blockSignals(_prev)

    def _refresh_preview_montage(self) -> None:
        """
        Load images for the selected well + FOV and render the inline montage:
        two rows per timepoint column — fluorescence (top) and overlay (bottom).
        """
        if not hasattr(self, "_montage_inner"):
            return

        # Reset zoom to fit on each new well load
        self._montage_zoom = 1.0
        if hasattr(self, "_montage_zoom_lbl"):
            self._montage_zoom_lbl.setText("100%")

        # Clear previous content
        _clear_layout(self._montage_inner.layout())
        self._montage_photos.clear()
        self._montage_fluor_arrays         = []
        self._montage_overlay_arrays     = []
        self._montage_fluor_display_arrays = []   # cleared on new load
        self._montage_th_status          = []
        self._montage_th_overlay_lbls    = []
        self._montage_th_cancel          = True   # no thread running initially

        well = self._preview_selected_well
        if well is None:
            self._montage_status.setText("Select a well in the left panel.")
            return

        fov = self._preview_fov_var.get()
        if fov == "—":
            self._montage_status.setText("No images found for this well.")
            return

        montage_load_debug = (
            _debug_flags.movie_montage_debug_enabled()
            or _debug_flags.movie_montage_load_debug_enabled()
        )

        # Filter refs to this FOV. Prefer pre-generated tophat frames from the
        # out directory for each timepoint, with raw fluor as fallback.
        raw_by_tp = {
            tp: ref for (f, tp), ref in sorted(self._preview_fluor.items())
            if f == fov
        }
        tophat_refs = getattr(self, "_preview_tophat_fluor", {})
        tophat_by_tp = {
            tp: ref for (f, tp), ref in sorted(tophat_refs.items())
            if f == fov
        }
        ordered_tps = list(raw_by_tp.keys())
        for tp in tophat_by_tp.keys():
            if tp not in ordered_tps:
                ordered_tps.append(tp)
        fluor_refs = [(tp, tophat_by_tp.get(tp) or raw_by_tp.get(tp)) for tp in ordered_tps]
        fluor_refs = [(tp, ref) for tp, ref in fluor_refs if ref is not None]
        _used_tophat_as_primary = bool(fluor_refs) and all(tp in tophat_by_tp for tp, _ in fluor_refs)

        overlay_refs = [(tp, ref) for (f, tp), ref in sorted(self._preview_overlay.items())
                        if f == fov]
        # Align by timepoint (use all TPs from GFP; overlay may be subset)
        ov_map = dict(overlay_refs)
        n = len(fluor_refs)

        if n == 0:
            self._montage_status.setText("No images for this FOV.")
            return

        if montage_load_debug:
            _debug_flags.debug_with_source(
                _logger,
                "Movie Montage candidate refs for well=%s fov=%s :: fluor=%d tophat=%d overlay=%d",
                well,
                fov,
                len(raw_by_tp),
                len(tophat_by_tp),
                len(ov_map),
            )
            for tp, ref in fluor_refs:
                _debug_flags.debug_with_source(
                    _logger,
                    "Movie Montage load attempt fluor tp=%s path=%s",
                    tp,
                    getattr(ref, "full_path_str", str(ref)),
                )
            for tp, ref in overlay_refs:
                _debug_flags.debug_with_source(
                    _logger,
                    "Movie Montage load attempt overlay tp=%s path=%s",
                    tp,
                    getattr(ref, "full_path_str", str(ref)),
                )

        self._montage_status.setText(f"Loading {n} timepoint(s)…")
        QApplication.processEvents()

        self._montage_fluor_refs     = [ref for _, ref in fluor_refs]
        self._montage_overlay_refs = [ov_map.get(tp) for tp, _ in fluor_refs]

        # Load arrays
        self._montage_fluor_arrays = [
            open_imgref_as_array(ref, greyscale=True) for ref in self._montage_fluor_refs
        ]
        self._montage_overlay_arrays = [
            (open_imgref_as_array(ref) if ref else None)
            for ref in self._montage_overlay_refs
        ]
        if montage_load_debug:
            for ref in self._montage_overlay_refs:
                if ref is None:
                    continue
                _debug_flags.debug_with_source(
                    _logger,
                    "Movie Montage loaded overlay path=%s",
                    getattr(ref, "full_path_str", str(ref)),
                )

        # Loaded fluorescence refs already apply tophat-first selection.
        self._montage_fluor_display_arrays = list(self._montage_fluor_arrays)
        self._montage_tophat_preloaded = _used_tophat_as_primary or any(
            tp in tophat_by_tp for tp, _ in fluor_refs
        )

        self._montage_status.setText("")
        self._montage_auto_lut(redraw=False)  # set initial LUT from data
        self._update_tophat_controls()        # sync UI to actual preload result
        self._draw_montage_thumbs([(tp, _) for tp, _ in fluor_refs])

    def _draw_montage_thumbs(self, tp_list: list) -> None:
        """Render fluorescence + overlay thumbnail pairs, one column per timepoint."""
        _clear_layout(self._montage_inner.layout())
        self._montage_photos.clear()
        # Overlay label refs must be rebuilt each time since all widgets are destroyed
        self._montage_th_overlay_lbls = []

        try:
            lo = float(self._mon_lmin_var.get())
        except ValueError:
            lo = None
        try:
            hi = float(self._mon_lmax_var.get())
        except ValueError:
            hi = None

        # Use pre-filtered display arrays: either loaded from disk (preloaded)
        # or computed on-the-fly by the tophat thread.
        preloaded = getattr(self, "_montage_tophat_preloaded", False)
        use_display = (
            preloaded
            or (
                getattr(self, "_mon_tophat_var", None) is not None
                and self._mon_tophat_var.get()
                and hasattr(self, "_montage_fluor_display_arrays")
                and len(self._montage_fluor_display_arrays) == len(self._montage_fluor_arrays)
            )
        )
        display_source = (self._montage_fluor_display_arrays
                          if use_display else self._montage_fluor_arrays)

        # Compute thumb size: base size × zoom factor.
        # Base size is the width that fits all timepoints in the canvas at 1×.
        cw = self._montage_canvas.viewport().width() or 400
        n  = len(tp_list)
        GAP = 6
        fit_sz = max(60, (cw - GAP) // max(n, 1) - GAP)
        self._montage_base_sz = fit_sz
        zoom   = getattr(self, "_montage_zoom", 1.0)
        sz_w   = max(40, int(fit_sz * zoom))
        sz_h   = max(35, int(sz_w * 0.8))
        if hasattr(self, "_montage_zoom_lbl"):
            self._montage_zoom_lbl.setText(f"{int(zoom * 100)}%")

        grid = self._montage_inner.layout()
        if grid is not None and not isinstance(grid, QGridLayout):
            # Re-parent the stale (e.g. QHBoxLayout left over from a tophat
            # refresh) to a throwaway so we can install a fresh QGridLayout.
            _tmp = QWidget()
            _tmp.setLayout(grid)
            _tmp.deleteLater()
            grid = None
        if grid is None:
            grid = QGridLayout(self._montage_inner)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(3)
        # Keep the labelled rows/columns at their natural content size. Without
        # these the scroll area's widgetResizable=True grows the grid to fill
        # the viewport, spreads extra space evenly across every row/column, and
        # leaves the "GFP"/"overlay" labels floating in whitespace instead of
        # sitting immediately left of the thumbnails.
        grid.setRowStretch(3, 1)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(len(tp_list) + 1, 1)

        channel_row_lbl = QLabel(self._active_image_channel.upper())
        channel_row_lbl.setObjectName("Muted")
        channel_row_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(channel_row_lbl, 1, 0)
        overlay_row_lbl = QLabel("overlay")
        overlay_row_lbl.setObjectName("Muted")
        overlay_row_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(overlay_row_lbl, 2, 0)

        def _install_montage_events(w, is_fluor):
            def _wheel(ev):
                if ev.modifiers() & Qt.ShiftModifier:
                    self._on_montage_shift_wheel(ev)
                else:
                    self._on_montage_wheel(ev)
            w.wheelEvent = _wheel
            if is_fluor:
                def _move(ev):
                    self._on_montage_fluor_motion(ev)
                def _leave(ev):
                    try:
                        self._montage_tooltip.hide()
                    except Exception:
                        pass
                w.setMouseTracking(True)
                w.mouseMoveEvent = _move
                w.leaveEvent = _leave

        for col_idx, ((tp, _), fluor_arr, ov_arr) in enumerate(
                zip(tp_list, display_source, self._montage_overlay_arrays)):

            tp_lbl = QLabel(tp)
            tp_lbl.setObjectName("Muted")
            tp_lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(tp_lbl, 0, col_idx + 1)

            # fluorescence thumbnail
            fluor_cell = QFrame()
            fluor_cell.setFrameShape(QFrame.Box)
            fluor_cell_layout = QVBoxLayout(fluor_cell)
            fluor_cell_layout.setContentsMargins(1, 1, 1, 1)
            grid.addWidget(fluor_cell, 1, col_idx + 1)
            display_arr = fluor_arr
            pix_fluor = make_fluor_thumb(display_arr, sz_w, sz_h, lo, hi)
            if pix_fluor:
                self._montage_photos.append(pix_fluor)
                lbl_fluor = QLabel()
                lbl_fluor.setPixmap(pix_fluor)
                lbl_fluor.setCursor(Qt.CrossCursor)
                lbl_fluor._raw_arr = display_arr  # type: ignore[attr-defined]
                lbl_fluor._sz_w    = sz_w        # type: ignore[attr-defined]
                lbl_fluor._sz_h    = sz_h        # type: ignore[attr-defined]
                lbl_fluor._lo      = lo          # type: ignore[attr-defined]
                lbl_fluor._hi      = hi          # type: ignore[attr-defined]
                fluor_cell_layout.addWidget(lbl_fluor)
                _install_montage_events(lbl_fluor, is_fluor=True)
            else:
                miss = QLabel(f"{self._active_image_channel.upper()}\nunavail")
                miss.setObjectName("Muted")
                miss.setAlignment(Qt.AlignCenter)
                fluor_cell_layout.addWidget(miss)

            th_on = (getattr(self, "_mon_tophat_var", None) is not None
                     and self._mon_tophat_var.get())
            th_state = (self._montage_th_status[col_idx]
                        if col_idx < len(self._montage_th_status) else "")
            if th_on and th_state == "pending":
                overlay_txt, overlay_bg, overlay_fg = "\u23f3 filtering\u2026", CLR_SLATE_BG, CLR_SLATE_TEXT
            elif th_on and th_state == "done":
                overlay_txt, overlay_bg, overlay_fg = "\u2713 filtered", CLR_SUCCESS_BG_DARK, CLR_SUCCESS_TEXT_SOFT
            else:
                overlay_txt = ""
            if overlay_txt:
                th_lbl = QLabel(overlay_txt, fluor_cell)
                th_lbl.setStyleSheet(f"background: {overlay_bg}; color: {overlay_fg}; padding: 1px 4px;")
                th_lbl.setAlignment(Qt.AlignCenter)
                th_lbl.show()
                self._montage_th_overlay_lbls.append(th_lbl)
            else:
                self._montage_th_overlay_lbls.append(None)

            ov_cell = QFrame()
            ov_cell.setFrameShape(QFrame.Box)
            ov_cell_layout = QVBoxLayout(ov_cell)
            ov_cell_layout.setContentsMargins(1, 1, 1, 1)
            grid.addWidget(ov_cell, 2, col_idx + 1)
            pix_ov = make_overlay_thumb(ov_arr, sz_w, sz_h)
            if pix_ov:
                self._montage_photos.append(pix_ov)
                lbl_ov = QLabel()
                lbl_ov.setPixmap(pix_ov)
                ov_cell_layout.addWidget(lbl_ov)
                _install_montage_events(lbl_ov, is_fluor=False)
            else:
                miss = QLabel("overlay\nunavail")
                miss.setObjectName("Muted")
                miss.setAlignment(Qt.AlignCenter)
                ov_cell_layout.addWidget(miss)
        # Send surplus horizontal space to a virtual empty column at the far
        # right so col 0 (labels) stays pinned against the first image column
        # instead of drifting when the grid is narrower than the viewport.
        for ci in range(grid.columnCount()):
            grid.setColumnStretch(ci, 0)
        grid.setColumnStretch(n + 1, 1)
        n_ov = sum(1 for a in self._montage_overlay_arrays if a is not None)
        self._montage_status.setText(
            f"{n} timepoint(s)  \u00b7  {n_ov} overlay(s)")

    # _montage_make_thumb and _montage_make_overlay_thumb replaced by
    # module-level make_fluor_thumb() / make_overlay_thumb()

    def _montage_tophat_toggled(self) -> None:
        from well_viewer.preview_callbacks import montage_tophat_toggled as _montage_tophat_toggled

        _montage_tophat_toggled(self)

    def _montage_tophat_done(self, filtered_arrays: list, partial: bool = False) -> None:
        _montage_tophat_done_controller(self, filtered_arrays, partial=partial)

    def _montage_auto_lut(self, redraw: bool = True) -> None:
        _montage_auto_lut_controller(self, redraw=redraw)

    def _on_montage_canvas_resize(self, _e=None) -> None:
        _on_montage_canvas_resize_controller(self, _e)

    def _montage_resize_deferred(self) -> None:
        _montage_resize_deferred_controller(self)

    def _on_montage_fluor_motion(self, e) -> None:
        _on_montage_fluor_motion_controller(self, e)

    # ── Montage zoom helpers ──────────────────────────────────────────────────

    def _montage_zoom_step(self, direction: int) -> None:
        _montage_zoom_step_controller(self, direction)

    def _montage_zoom_fit(self) -> None:
        _montage_zoom_fit_controller(self)

    def _on_montage_wheel(self, event) -> None:
        _on_montage_wheel_controller(self, event)

    def _on_montage_shift_wheel(self, event) -> None:
        _on_montage_shift_wheel_controller(self, event)

    def _montage_redraw_at_zoom(self) -> None:
        _montage_redraw_at_zoom_controller(self)

    def _build_bottom(self) -> None:
        from well_viewer.views.status_view import build_bottom as _build_bottom_view

        _build_bottom_view(self)

    def _apply_theme(self) -> None:
        """Apply QSS stylesheet for the active theme."""
        try:
            from ui.theme import build_stylesheet  # type: ignore
            app = QApplication.instance()
            if app is not None:
                app.setStyleSheet(build_stylesheet(self._theme_name))
        except Exception:
            pass

    def _on_theme_change(self, theme_name: str = None) -> None:
        """Re-apply QSS stylesheet when theme switches."""
        new_theme = theme_name or self._theme_name
        self._theme_name = new_theme
        self._apply_theme()

        if hasattr(self, '_rep_cards_frame') and self._rep_cards_frame:
            self._rep_panel_refresh()
        if hasattr(self, '_grp_cards_frame') and self._grp_cards_frame:
            self._grp_panel_refresh()
        if hasattr(self, '_stats_fig') and self._stats_fig:
            self._stats_refresh_colors()
        if hasattr(self, "_sidebar_btns"):
            self._sidebar_map_refresh_pending = False
            self._refresh_sidebar_map_now()
        try:
            from well_viewer.ui_helpers import refresh_plot_toolbar_icons
            refresh_plot_toolbar_icons(self)
        except Exception:
            pass

    # ── Loading ───────────────────────────────────────────────────────────────

    def _browse(self) -> None:
        """Open a directory picker. Expects in/ + out/ subdirs or a flat CSV dir."""
        d = QFileDialog.getExistingDirectory(self, "Open results directory")
        if d:
            # Defer so the dialog closes and the window repaints before load
            QTimer.singleShot(50, lambda: self._load_path(Path(d)))

    def _load_path(self, path):
        _load_path_controller(self, path)


    def _load_directory(self, d: Path, label: Optional[str] = None) -> None:
        _load_directory_controller(self, d, label=label)

    def _read_pipeline_info(self, path: Path):
        return _read_pipeline_info_shared(path, logger=_logger, check_parent=True)

    def _load_well_csv(self, path: Path):
        return load_well_csv(path)

    def _extract_well_token(self, label: str):
        return _extract_well_token(label)

    def _cleanup_tmp(self) -> None:
        if self._tmp_dir and self._tmp_dir.exists():
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._tmp_dir = None

    def _on_close(self) -> None:
        self._cleanup_tmp()
        self.close()

    # ── Plate-map sidebar helpers ─────────────────────────────────────────────

    def _parse_rc(self, label: str) -> Tuple[Optional[str], Optional[str]]:
        m = re.search(r"([A-Ha-h])(\d{1,2})$", label)
        if not m:
            return None, None
        return m.group(1).upper(), f"{int(m.group(2)):02d}"

    def _build_tok_to_label(self) -> None:
        """Rebuild the token→label map after data is loaded."""
        _load_build_tok_to_label(self)

    def _rebuild_all_timepoints_cache(self) -> None:
        """Cache global numeric timepoints for all plot/menu population.

        Sources are merged in this single function so every tab that reads
        ``_all_timepoints_cache`` gets the same canonical timepoint list:
          1) loaded CSV rows (timepoint_hours / parsed timepoint strings)
          2) pipeline_info.json ``available_timepoints`` when present
        """
        all_tps: set[float] = set()
        for rows in self._cache.values():
            for row in rows:
                raw = row.get("timepoint_hours")
                t: Optional[float] = (
                    raw if isinstance(raw, float) and not math.isnan(raw)
                    else parse_timepoint_hours(str(row.get("timepoint", "")))
                )
                if t is not None:
                    all_tps.add(t)
        pipeline_info = getattr(self, "_pipeline_info", {}) or {}
        for tp in pipeline_info.get("available_timepoints", []) or []:
            parsed = parse_timepoint_hours(str(tp))
            if parsed is not None:
                all_tps.add(parsed)
        self._all_timepoints_cache = sorted(all_tps)

    def _rebuild_all_fovs_cache(self) -> None:
        """Cache global FOV labels once per dataset load (no per-refresh rebuilding)."""
        def _norm_fov(value: object) -> str:
            raw = str(value or "").strip()
            if not raw:
                return ""
            try:
                return f"{float(raw):g}"
            except Exception:
                return raw

        all_fovs: set[str] = set()
        for rows in self._cache.values():
            for row in rows:
                fov = _norm_fov(row.get("fov", ""))
                if fov:
                    all_fovs.add(fov)
        pipeline_info = getattr(self, "_pipeline_info", {}) or {}
        for fov in pipeline_info.get("available_fovs", []) or []:
            fov_norm = _norm_fov(fov)
            if fov_norm:
                all_fovs.add(fov_norm)
        if not all_fovs and self._well_paths:
            all_fovs.add("1")

        def _fov_sort_key(token: str) -> tuple[int, float, str]:
            try:
                return (0, float(token), token)
            except ValueError:
                return (1, 0.0, token)

        self._all_fovs_cache = sorted(all_fovs, key=_fov_sort_key)

    @staticmethod
    def _mute_color(hex_color: str, factor: float = 0.5) -> str:
        """Blend *hex_color* 50% toward a neutral mid-grey (#94A3B8).

        Used to dim hidden rep-sets on the plate map so they are visually
        distinct from visible ones while still showing their hue.
        """
        grey = (0x94, 0xA3, 0xB8)
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        mr = int(r + (grey[0] - r) * factor)
        mg = int(g + (grey[1] - g) * factor)
        mb = int(b + (grey[2] - b) * factor)
        return f"#{mr:02X}{mg:02X}{mb:02X}"

    def _rep_visible_sets(self) -> "List[ReplicateSet]":
        """Alias for _rep_sets_active — visible (non-hidden) loaded rep-sets."""
        return self._rep_sets_active()

    def _refresh_sidebar_map(self) -> None:
        """Debounce sidebar recoloring work to one pass per event-loop tick."""
        if self._sidebar_map_refresh_pending:
            return
        self._sidebar_map_refresh_pending = True
        QTimer.singleShot(0, self._refresh_sidebar_map_now)

    def _refresh_sidebar_map_now(self) -> None:
        """Recolour every sidebar button to reflect rep-set visibility.

        Rep-set mode: visible set = full colour sunken, hidden = muted flat,
        unassigned = neutral. Per-well mode: selected = ACCENT sunken, else
        neutral. Missing wells are disabled.
        """
        bg, fg, fg_disabled = self._plate_theme_colors()
        rep_sets = getattr(self, "_rep_sets", [])
        rep_mode = bool(rep_sets)

        tok_rep: Dict[str, tuple] = {}
        for si, rset in enumerate(rep_sets):
            full_c = WELL_COLORS[si % len(WELL_COLORS)]
            hidden = si in self._rep_hidden
            for tok in rset.wells:
                tok_rep[tok] = (full_c, hidden)

        for tok, btn in self._sidebar_btns.items():
            if tok not in self._well_paths:
                self._plate_apply_disabled(btn, bg, fg, fg_disabled)
            elif rep_mode and tok in tok_rep:
                full_c, hidden = tok_rep[tok]
                if hidden:
                    # Hidden sets: muted bg, full colour on hover, flat relief.
                    self._style_plate_button(
                        btn, bg=self._mute_color(full_c), fg="white",
                        state="normal", cursor="hand2", relief="flat",
                        activebackground=full_c, activeforeground="white",
                        disabledforeground=fg_disabled,
                    )
                else:
                    self._plate_apply_colored(
                        btn, full_c, active=True, fg_disabled=fg_disabled,
                    )
            elif rep_mode:
                self._plate_apply_neutral(btn, bg, fg, fg_disabled)
            elif tok in self._selected_wells:
                self._plate_apply_colored(
                    btn, ACCENT, active=True, fg_disabled=fg_disabled,
                )
            else:
                self._plate_apply_neutral(btn, bg, fg, fg_disabled)

        # Count label / hint
        loaded  = self._rep_sets_loaded() if rep_mode else []
        n_vis   = len(self._rep_sets_active()) if rep_mode else len(self._selected_wells)
        n_loaded = len(loaded)
        if hasattr(self, "_sel_count_lbl"):
            if rep_mode:
                n_hid = sum(1 for i in range(n_loaded) if i in self._rep_hidden)
                self._sel_count_lbl.setText((f"{n_vis}/{n_loaded} set(s) visible"
                          if n_hid else f"{n_loaded} set(s) — all visible"))
            else:
                self._sel_count_lbl.setText((f"{n_vis} well{'s' if n_vis != 1 else ''} selected"
                          if n_vis else "No wells selected"))
        if hasattr(self, "_line_group_hint"):
            if rep_mode:
                self._line_group_hint.setText("Click a well to toggle its set's visibility on the plot.")
            else:
                self._line_group_hint.setText("")

        self._sidebar_map_refresh_pending = False

    def _style_plate_button(
        self,
        btn: Any,
        *,
        bg: str,
        fg: str,
        state: str = "normal",
        cursor: str = "hand2",
        relief: str = "flat",
        activebackground: Optional[str] = None,
        activeforeground: Optional[str] = None,
        disabledforeground: Optional[str] = None,
    ) -> None:
        """Apply plate-map button styling to a ``QPushButton``."""
        state_str = str(state).lower()
        relief_str = str(relief).lower()
        is_enabled = not state_str.endswith("disabled")
        is_sunken = relief_str.endswith("sunken")

        btn.setEnabled(is_enabled)
        if hasattr(btn, "setCursor"):
            btn.setCursor(Qt.PointingHandCursor if cursor == "hand2" else Qt.ArrowCursor)

        hover_bg = activebackground or bg
        hover_fg = activeforeground or fg
        disabled_fg = disabledforeground or fg
        # Uniform 2px border width across every state so fixed-size circles
        # never change dimensions. Wells with no data get a transparent
        # border; wells with data get a smooth solid black border. The
        # embossed/depressed 3D cue is painted by WellButton.paintEvent —
        # QSS outset/inset collapses to solid once border-radius is set.
        if not is_enabled:
            border = "2px solid transparent"
        else:
            border = "2px solid #000000"
        # Drive the paint-event-based 3D cue.
        if hasattr(btn, "set_emboss"):
            if not is_enabled:
                btn.set_emboss("none")
            elif is_sunken:
                btn.set_emboss("depressed")
            else:
                btn.set_emboss("raised")

        # Setting a per-widget stylesheet overrides the application QSS for
        # this widget's selector. Restate the plate-well layout properties
        # (fixed size, padding, border-radius) here so wells render as
        # identical circles regardless of which code path styles them. Must
        # match QPushButton#WellButton in dark.qss / light.qss. No font-size
        # is set (Qt rejects <=0pt); button text is always empty anyway.
        base_layout = (
            "min-width: 18px;"
            "min-height: 18px;"
            "max-width: 18px;"
            "max-height: 18px;"
            "padding: 0;"
            "border-radius: 9px;"
        )

        btn.setStyleSheet(
            "\n".join(
                [
                    (
                        "QPushButton{"
                        f"{base_layout}"
                        f"background-color: {bg};"
                        f"color: {fg};"
                        f"border: {border};"
                        "}"
                    ),
                    (
                        "QPushButton:hover{"
                        f"{base_layout}"
                        f"background-color: {hover_bg};"
                        f"color: {hover_fg};"
                        f"border: {border};"
                        "}"
                    ),
                    (
                        "QPushButton:disabled{"
                        f"{base_layout}"
                        f"background-color: {bg};"
                        f"color: {disabled_fg};"
                        f"border: {border};"
                        "}"
                    ),
                ]
            )
        )

    def _plate_theme_colors(self) -> tuple:
        from ui.theme import get_color
        return (
            get_color("button_bg"),
            get_color("button_text"),
            get_color("button_text_disabled"),
        )

    def _plate_apply_disabled(self, btn, bg: str, fg: str, fg_disabled: str) -> None:
        self._style_plate_button(
            btn, bg=bg, fg=fg_disabled, state="disabled", cursor="arrow",
            activebackground=bg, activeforeground=fg,
            disabledforeground=fg_disabled, relief="flat",
        )

    def _plate_apply_colored(
        self, btn, color: str, *, active: bool, fg_disabled: str,
    ) -> None:
        self._style_plate_button(
            btn, bg=color, fg="white", state="normal", cursor="hand2",
            relief="sunken" if active else "flat",
            activebackground=self._mute_color(color, 0.3) if active else color,
            activeforeground="white", disabledforeground=fg_disabled,
        )

    def _plate_apply_neutral(
        self, btn, bg: str, fg: str, fg_disabled: str,
        *, cursor: str = "hand2", relief: str = "flat",
    ) -> None:
        self._style_plate_button(
            btn, bg=bg, fg=fg, state="normal", cursor=cursor, relief=relief,
            activebackground=bg, activeforeground=fg,
            disabledforeground=fg_disabled,
        )

    def _sidebar_tok_at(self, event) -> Optional[str]:
        from well_viewer.selection_controller import sidebar_tok_at as _sidebar_tok_at

        return _sidebar_tok_at(self, event)

    # =========================================================================
    # Shared plate-map drag engine
    # Both the line sidebar (_sidebar_btns / _selected_wells) and the
    # bar sidebar uses identical
    # rep-set toggle logic.  The three helpers below centralise it.
    #
    # Callers supply:
    #   btn_dict  – {tok: QPushButton} for the active map
    #   well_set  – mutable set used in per-well mode
    #   ds        – drag-state dict  {"adding": bool,
    #                                 "visited": set,
    #                                 "rep_toggled": set}
    # =========================================================================

    def _plate_drag_press(self, label: str, well_set: set, ds: dict) -> None:
        from well_viewer.selection_controller import plate_drag_press as _plate_drag_press

        _plate_drag_press(self, label, well_set, ds)

    def _plate_drag_apply(
        self,
        tok: str,
        btn_dict: "Dict[str, QPushButton]",
        well_set: set,
        ds: dict,
    ) -> None:
        from well_viewer.selection_controller import plate_drag_apply as _plate_drag_apply

        _plate_drag_apply(self, tok, btn_dict, well_set, ds)

    def _plate_drag_release(
        self,
        ds: dict,
        on_rep_change,
        on_well_change,
    ) -> None:
        from well_viewer.selection_controller import plate_drag_release as _plate_drag_release

        _plate_drag_release(self, ds, on_rep_change, on_well_change)

    def _rep_idx_for_label(self, label: str) -> Optional[int]:
        """Return _rep_sets_loaded() index of the set owning *label*, or None."""
        for si, rset in enumerate(self._rep_sets_loaded()):
            if label in rset.wells:
                return si
        return None

    # ── Line-graph sidebar wrappers ───────────────────────────────────────────

    def _sb_press(self, event) -> None:
        from well_viewer.selection_controller import sb_press as _sb_press

        _sb_press(self, event)

    def _sb_drag(self, event) -> None:
        from well_viewer.selection_controller import sb_drag as _sb_drag

        _sb_drag(self, event)

    def _sb_release(self, _event=None) -> None:
        from well_viewer.selection_controller import sb_release as _sb_release

        _sb_release(self)

    def _sb_on_rep_change(self) -> None:
        """Rep-set visibility changed — refresh unified picker + both plots."""
        self._refresh_sidebar_map()
        self._redraw()
        self._redraw_bars()

    def _on_plate_sel_change(self) -> None:
        from well_viewer.selection_controller import on_plate_sel_change as _on_plate_sel_change

        _on_plate_sel_change(self)

    def _select_row(self, row: str) -> None:
        from well_viewer.selection_controller import select_row as _select_row

        _select_row(self, row)

    def _select_col(self, col: str) -> None:
        from well_viewer.selection_controller import select_col as _select_col

        _select_col(self, col)

    # ── Threshold ─────────────────────────────────────────────────────────────

    def _recalculate_threshold(self) -> None:
        # Detect channels from the first loaded well
        all_rows_sample = next(
            (self._get_rows(lbl) for lbl in self._well_paths), []
        )
        detected = detect_fluor_channels(all_rows_sample)
        detected_smfish = detect_smfish_channels(all_rows_sample)
        pipeline_fluor_raw = [
            str(tok).strip().lower()
            for tok in (self._pipeline_info.get("fluor_tokens", []) if isinstance(self._pipeline_info, dict) else [])
            if str(tok).strip()
        ]
        pipeline_fluor = normalize_channel_tokens(pipeline_fluor_raw)
        detected = normalize_channel_tokens(detected)
        seg_tok = ""
        if isinstance(self._pipeline_info, dict):
            seg_tok = str(self._pipeline_info.get("nuclear_token", "") or "").strip().lower()
        if not seg_tok:
            seg_tok = detect_nuclear_channel_token(all_rows_sample)
        fluor_channels = merge_fluor_channels(pipeline_fluor, detected, seg_tok)
        if fluor_channels:
            self._fluor_channels = fluor_channels
            # Keep the active channel if it is still present; otherwise
            # default to the first detected channel.
            if not self._active_channel:
                self._active_channel = fluor_channels[0]
            if not self._active_image_channel:
                self._active_image_channel = fluor_channels[0]
        self._seg_channel_token = seg_tok
        self._review_image_channels = detect_review_image_channels(all_rows_sample, self._fluor_channels, seg_tok)
        self._update_channel_selector()

        # Update smFISH channels and reset metric if needed
        self._smfish_channels = set(detected_smfish)
        if self._active_metric == "smfish_count" and self._active_channel not in self._smfish_channels:
            self._active_metric = "mean_intensity"

        # Derive _active_val_col from active channel and metric
        self._active_val_col = f"{self._active_channel}_{self._active_metric}"

        # Update metric selector visibility (both line and bar tabs)
        for frame_attr in ("_metric_selector_frame", "_metric_selector_frame_bar"):
            if hasattr(self, frame_attr):
                frame = getattr(self, frame_attr)
                frame.setVisible(self._active_channel in self._smfish_channels)

        # Always refresh timepoint menus regardless of whether intensity
        # values exist — single-timepoint experiments still need the bar menu.
        if hasattr(self, "_bar_tp_cb"):
            self._update_bar_tp_menu()
        if hasattr(self, "_stats_tp_cb"):
            self._stats_update_tp_menu()

        all_vals = [v for lbl in self._well_paths
                    for v in _all_fluor_values(self._get_rows(lbl),
                                             val_col=self._active_val_col)]
        if not all_vals:
            return
        lo, hi = min(all_vals), max(all_vals)
        if hi <= lo: hi = lo + 1.0
        self._threshold_min = lo
        self._threshold_max = hi

        # Load cell areas in the Cell Gating tab
        if hasattr(self, '_cell_gating_tab') and self._cell_gating_tab is not None:
            self._cell_gating_tab._load_cell_areas()
            # Load saved ThreshFracOn values
            self._cell_gating_tab._load_threshold_frac_on()

    def _set_active_channel(self, channel: str) -> None:
        """Switch the active fluorescent channel and redraw all plots."""
        if not channel or channel == "—":
            return
        if channel == self._active_channel:
            return
        self._active_channel = channel
        # Reset metric to mean_intensity if new channel doesn't have smfish_count
        if channel not in self._smfish_channels:
            self._active_metric = "mean_intensity"
        # Derive val_col from channel and metric
        self._active_val_col = f"{channel}_{self._active_metric}"
        # Keep both plot-tab channel selectors in sync so switching channel
        # on one tab is reflected on the other.
        ch_upper = channel.upper()
        for attr in ("_chan_cb_line", "_chan_cb_bar"):
            cb = getattr(self, attr, None)
            if cb is None:
                continue
            if str(cb.currentText() or "") == ch_upper:
                continue
            idx = cb.findText(ch_upper)
            if idx >= 0:
                blocked = cb.blockSignals(True)
                try:
                    cb.setCurrentIndex(idx)
                finally:
                    cb.blockSignals(blocked)
        # Reset threshold to the range of the new channel.
        self._recalculate_threshold()
        self._invalidate_stats_cache()
        self._redraw()
        if hasattr(self, "_bar_tp_cb"):
            self._redraw_bars()
        if hasattr(self, "_cdf_chan_lbl"):
            self._cdf_chan_lbl.setText(f"({ch_upper} x range)")
        if hasattr(self, "_bar_ylim_chan_lbl"):
            self._bar_ylim_chan_lbl.setText(f"{ch_upper} y:")

    def _set_active_image_channel(self, channel: str, *, preserve_review_view: bool = False) -> None:
        """Switch image-display channel for Movie Montage and Review Image."""
        channel_switch_debug = _debug_flags.review_image_channel_switch_debug_enabled()
        if channel_switch_debug:
            _logger.debug(
                "[RI-CHSW step 3] set_active_image_channel requested=%r current=%r preserve_review_view=%s",
                channel,
                getattr(self, "_active_image_channel", ""),
                preserve_review_view,
            )
        if not channel or channel == "—":
            return
        if channel == self._active_image_channel:
            if preserve_review_view:
                self._review_image_preserve_view_on_refresh = True
                if self._preview_selected_well:
                    self._refresh_review_image()
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 3] no-op channel switch; active remains=%r preserve_review_view=%s",
                    self._active_image_channel,
                    preserve_review_view,
                )
            return
        prev_channel = self._active_image_channel
        self._active_image_channel = channel
        ch_upper = channel.upper()
        if hasattr(self, "_montage_chan_var"):
            self._montage_chan_var.set(ch_upper)
        if hasattr(self, "_review_image_chan_var"):
            self._review_image_chan_var.set(ch_upper)
        if hasattr(self, "_mon_lut_chan_lbl"):
            self._mon_lut_chan_lbl.setText(f"{ch_upper} LUT min:")
        if hasattr(self, "_review_lut_chan_lbl"):
            self._review_lut_chan_lbl.setText(f"{ch_upper} LUT min:")
        saved_review_lut = self._review_image_lut_by_channel.get(channel)
        if saved_review_lut and hasattr(self, "_review_lut_min_var") and hasattr(self, "_review_lut_max_var"):
            self._review_lut_min_var.set(f"{saved_review_lut[0]:.0f}")
            self._review_lut_max_var.set(f"{saved_review_lut[1]:.0f}")
        if preserve_review_view:
            self._review_image_preserve_view_on_refresh = True
        if self._preview_selected_well:
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 3->4] reloading preview for selected_well=%r",
                    self._preview_selected_well,
                )
            self._update_preview(self._preview_selected_well)
        if channel_switch_debug:
            _logger.debug(
                "[RI-CHSW step 3] set_active_image_channel updated before=%r after=%r",
                prev_channel,
                self._active_image_channel,
            )

    def _on_review_image_channel_selected(self, _e=None) -> None:
        """Channel-switch handler that preserves Review Image zoom/pan view."""
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug("[RI-CHSW step 1] Review Image channel ComboboxSelected event received")
        selected_ui_value = ""
        if getattr(self, "_review_image_chan_cb", None) is not None:
            selected_ui_value = str(self._review_image_chan_cb.currentText() or "").strip()
        if not selected_ui_value and hasattr(self, "_review_image_chan_var"):
            selected_ui_value = self._review_image_chan_var.get()
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug(
                "[RI-CHSW step 2] review_image_channel_selected ui_value=%r active_before=%r",
                selected_ui_value,
                getattr(self, "_active_image_channel", ""),
            )
        self._set_active_image_channel(selected_ui_value.lower(), preserve_review_view=True)

    def _on_plot_channel_selected(self, _e=None) -> None:
        """Channel-switch handler for line/bar plot tabs."""
        # _plot_chan_var is bound to _chan_cb_line, so reading it returns a
        # stale value when the user changes _chan_cb_bar. Prefer the sender
        # widget when the signal came from a QComboBox, otherwise fall back
        # to the line-tab ComboVar.
        label = ""
        try:
            sender = self.sender()
        except Exception:
            sender = None
        if sender is not None and hasattr(sender, "currentText"):
            try:
                label = str(sender.currentText() or "")
            except Exception:
                label = ""
        if not label:
            label = self._plot_chan_var.get()
        self._set_active_channel(label.lower())

    def _on_preview_channel_selected(self, _e=None) -> None:
        """Channel-switch handler for the Movie Montage tab."""
        selected_ui_value = ""
        if hasattr(self, "_chan_cb_preview"):
            selected_ui_value = str(self._chan_cb_preview.currentText() or "").strip()
        if not selected_ui_value and hasattr(self, "_montage_chan_var"):
            selected_ui_value = self._montage_chan_var.get()
        if _debug_flags.movie_montage_debug_enabled():
            _logger.debug(
                "preview_channel_selected ui_value=%r active_before=%r",
                selected_ui_value,
                getattr(self, "_active_image_channel", ""),
            )
        self._set_active_image_channel(selected_ui_value.lower())

    def _on_metric_selected(self) -> None:
        """Handle metric selector change in UI."""
        metric_label = self._metric_var.get()
        metric = "smfish_count" if metric_label == "smFISH Count" else "mean_intensity"
        self._set_active_metric(metric)

    def _set_active_metric(self, metric: str) -> None:
        """Switch the active metric (mean_intensity or smfish_count) and redraw."""
        if metric == self._active_metric:
            return
        self._active_metric = metric
        self._active_val_col = f"{self._active_channel}_{self._active_metric}"
        # Update UI to match new metric
        if hasattr(self, "_metric_var"):
            label = "smFISH Count" if metric == "smfish_count" else "Mean Intensity"
            self._metric_var.set(label)
        self._recalculate_threshold()
        self._invalidate_stats_cache()
        self._redraw()
        if hasattr(self, "_bar_tp_cb"):
            self._redraw_bars()

    def _update_channel_selector(self) -> None:
        """Refresh the channel dropdown values and selection to match loaded data."""
        labels = [ch.upper() for ch in self._fluor_channels] or ["—"]
        # Montage/preview includes the segmentation channel token.
        seg_tok = getattr(self, "_seg_channel_token", "")
        montage_chans = list(self._fluor_channels)
        if seg_tok and seg_tok not in montage_chans:
            montage_chans.append(seg_tok)
        montage_labels = [ch.upper() for ch in montage_chans] or ["—"]
        review_labels = [ch.upper() for ch in (self._review_image_channels or self._fluor_channels)] or ["—"]
        # Update channel selector instances
        for attr in ("_chan_cb_line", "_chan_cb_bar"):
            if hasattr(self, attr):
                _set_combo_values(getattr(self, attr), labels)
        if hasattr(self, "_chan_cb_preview"):
            _set_combo_values(self._chan_cb_preview, montage_labels)
        if hasattr(self, "_review_image_chan_cb"):
            _set_combo_values(self._review_image_chan_cb, review_labels)
        active_label = self._active_channel.upper()

        def _pick_valid(current: str, candidates: List[str], fallback_label: str) -> str:
            if current in candidates and current != "—":
                return current
            if fallback_label in candidates and fallback_label != "—":
                return fallback_label
            if candidates and candidates[0] != "—":
                return candidates[0]
            return "—"

        # Plot tabs: only measurement channels.
        plot_label = _pick_valid(self._plot_chan_var.get(), labels, active_label)
        self._plot_chan_var.set(plot_label)

        # Image tabs: each validates against its own channel universe.
        active_image_label = self._active_image_channel.upper()
        montage_label = _pick_valid(self._montage_chan_var.get(), montage_labels, active_image_label)
        review_label = _pick_valid(self._review_image_chan_var.get(), review_labels, active_image_label)
        self._montage_chan_var.set(montage_label)
        self._review_image_chan_var.set(review_label)

        # Keep active image channel anchored only when the current value is invalid.
        if active_image_label not in montage_labels and active_image_label not in review_labels:
            fallback_image_label = montage_label if montage_label != "—" else review_label
            if fallback_image_label != "—":
                self._set_active_image_channel(fallback_image_label.lower())

        # Keep active channel anchored to a valid plot channel.
        if active_label not in labels:
            if plot_label != "—":
                self._set_active_channel(plot_label.lower())
            else:
                self._active_channel = ""

        # Back-compat sync: follow the active tab's selector instead of forcing plot labels.
        if hasattr(self, "_chan_var"):
            tab_label = ""
            if hasattr(self, "_notebook"):
                try:
                    tab_label = self._notebook.tabText(self._notebook.currentIndex())
                except Exception:
                    tab_label = ""
            if tab_label == "Movie Montage":
                self._chan_var.set(montage_label)
            elif tab_label == "Review Image":
                self._chan_var.set(review_label)
            else:
                self._chan_var.set(plot_label)

    def _toggle_sem(self) -> None:
        self._invalidate_stats_cache()
        self._use_sem.set(not self._use_sem.get())
        is_sem = self._use_sem.get()
        text = "SEM" if is_sem else "SD"
        variant = "sem" if is_sem else "sem_warn"
        for btn in list(getattr(self, "_sem_btns", []) or []):
            btn.setText(text)
            btn.setProperty("variant", variant)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._redraw()
        if hasattr(self, "_notebook"):
            if self._notebook.tabText(self._notebook.currentIndex()) == "Bar Plots":
                self._redraw_bars()

    # ── Well selection (plate-map backed) ─────────────────────────────────────

    def _select_all(self) -> None:
        from well_viewer.selection_controller import select_all as _select_all

        _select_all(self)

    def _select_none(self) -> None:
        from well_viewer.selection_controller import select_none as _select_none

        _select_none(self)

    def _selected_labels(self) -> List[str]:
        """Return labels in a stable order (sorted) for consistent plot colours."""
        return sorted(self._selected_wells, key=lambda lbl: self._parse_rc(lbl))

    def _get_rows(self, label: str) -> List[dict]:
        if label not in self._cache:
            self._cache[label] = load_well_csv(self._well_paths[label])
        return self._cache[label]

    # ── Preview panel ─────────────────────────────────────────────────────────

    def _update_preview(self, well_label: Optional[str]) -> None:
        """Load images for *well_label* and render the inline montage."""
        channel_switch_debug = _debug_flags.review_image_channel_switch_debug_enabled()
        if well_label is None:
            if hasattr(self, "_preview_well_lbl"):
                self._preview_well_lbl.setText("No well selected")
            if hasattr(self, "_review_image_well_lbl"):
                self._review_image_well_lbl.setText("No well selected")
            if hasattr(self, "_fov_menu"):
                _set_combo_values(self._fov_menu, ["—"])
                self._preview_fov_var.set("—")
            if hasattr(self, "_review_image_fov_menu"):
                _set_combo_values(self._review_image_fov_menu, ["—"])
            if hasattr(self, "_review_image_tp_menu"):
                _set_combo_values(self._review_image_tp_menu, ["—"])
                self._review_image_tp_var.set("—")
            self._preview_fluor = self._preview_overlay = self._preview_mask = {}
            if hasattr(self, "_montage_inner"):
                _clear_layout(self._montage_inner.layout())
                self._montage_photos.clear()
                self._montage_status.setText("Select a well in the left panel.")
            if hasattr(self, "_review_image_status"):
                self._review_image_status.setText("Select a well in the left panel.")
            if channel_switch_debug:
                _logger.debug("[RI-CHSW step 4] update_preview early return: no well selected")
            return

        if hasattr(self, "_preview_well_lbl"):
            tok = _extract_well_token(well_label) or well_label
            self._preview_well_lbl.setText(tok)
        if hasattr(self, "_review_image_well_lbl"):
            tok = _extract_well_token(well_label) or well_label
            self._review_image_well_lbl.setText(tok)

        try:
            active_image_channel = str(self._active_image_channel or "").strip().lower()
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 4] update_preview start well=%r active_channel=%r",
                    well_label,
                    active_image_channel,
                )
            fluor, overlay, mask, tophat_fluor = find_well_images_and_masks(
                self._data_dir,
                well_label,
                fluor_token=active_image_channel,
                in_dir=self._in_dir,
                _fov_tp_extractor=self._fov_tp_extractor,
                _pipeline_info=self._pipeline_info,
            )
        except Exception as _exc:
            _logger.exception("Unexpected error searching images for %r: %s", well_label, _exc)
            fluor, overlay, mask, tophat_fluor = {}, {}, {}, {}
        self._preview_fluor        = fluor
        self._preview_overlay    = overlay
        self._preview_mask       = mask
        self._preview_tophat_fluor = tophat_fluor
        if channel_switch_debug:
            _logger.debug(
                "[RI-CHSW step 4] update_preview refs loaded well=%r active_channel=%r fluor=%d tophat=%d overlay=%d mask=%d",
                well_label,
                active_image_channel,
                len(fluor),
                len(tophat_fluor),
                len(overlay),
                len(mask),
            )

        # Reset controls to "no preload" state now; _refresh_preview_montage
        # will call _update_tophat_controls() with the authoritative result
        # after it has checked tophat coverage at the current FOV level.
        if hasattr(self, "_th_checkbox"):
            self._update_tophat_controls(preloaded=False)

        def _norm_fov(value: object) -> str:
            raw = str(value or "").strip()
            if not raw:
                return ""
            try:
                return f"{float(raw):g}"
            except Exception:
                return raw

        def _fov_sort_key(token: str) -> tuple[int, float, str]:
            try:
                return (0, float(token), token)
            except ValueError:
                return (1, 0.0, token)

        all_fovs = sorted(
            {
                fov_norm
                for refs in (fluor, overlay, mask, tophat_fluor)
                for (fov, _tp) in refs.keys()
                for fov_norm in [_norm_fov(fov)]
                if fov_norm
            },
            key=_fov_sort_key,
        )
        if channel_switch_debug:
            _logger.debug(
                "[RI-CHSW step 4] update_preview candidate_fovs=%s selected_fov_before=%r",
                all_fovs,
                self._preview_fov_var.get() if hasattr(self, "_preview_fov_var") else "—",
            )

        if not (fluor or overlay or mask or tophat_fluor):
            if hasattr(self, "_fov_menu"):
                _set_combo_values(self._fov_menu, ["—"])
                self._preview_fov_var.set("—")
            tok = _extract_well_token(well_label) or well_label
            dirs = f"in={self._in_dir}  out={self._data_dir}"
            msg = f"No images found for {tok}. Searched: {dirs}"
            _logger.warning(msg)
            if hasattr(self, "_montage_status"):
                self._montage_status.setText(f"No images found for {tok} — check Log for details.")
            return

        if hasattr(self, "_fov_menu"):
            _set_combo_values(self._fov_menu, all_fovs)
            cur = self._preview_fov_var.get()
            if all_fovs:
                self._preview_fov_var.set(cur if cur in all_fovs else all_fovs[0])
            else:
                self._preview_fov_var.set("—")
        if hasattr(self, "_review_image_fov_menu"):
            _set_combo_values(self._review_image_fov_menu, all_fovs or ["—"])

        cur = self._preview_fov_var.get()
        if all_fovs and cur not in all_fovs:
            self._preview_fov_var.set(all_fovs[0])

        self._refresh_preview_montage()
        if channel_switch_debug:
            _logger.debug("[RI-CHSW step 4->6] triggering refresh_review_image after preview reload")
        self._refresh_review_image()

    def _on_preview_sel_change(self, _e=None) -> None:
        self._refresh_preview_montage()

    def _norm_timepoint(self, value: object) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        parsed = parse_timepoint_hours(raw)
        if parsed is not None:
            return f"{parsed:g}"
        return raw

    def _review_row_keys(self, row: dict) -> Tuple[str, str, str]:
        def _norm(v: object) -> str:
            s = str(v or "").strip()
            if not s:
                return ""
            try:
                return f"{float(s):g}"
            except Exception:
                return s
        def _pick(*names: str) -> object:
            for name in names:
                if name in row:
                    return row.get(name, "")
            lowered = {str(k).lower(): v for k, v in row.items()}
            for name in names:
                key = name.lower()
                if key in lowered:
                    return lowered[key]
            return ""
        return (
            _norm(_pick("fov", "FOV")),
            self._norm_timepoint(_pick("timepoint", "tp", "time", "time_h", "timepoint_hours")),
            _norm(_pick("nucleus_id", "nucleus id", "nucleusId", "nucleusID")),
        )

    @staticmethod
    def _review_norm_fov(v: object) -> str:
        s = str(v or "").strip()
        if not s:
            return ""
        try:
            return f"{float(s):g}"
        except Exception:
            return s

    @staticmethod
    def _review_tp_sort_key(tp: str) -> Tuple[int, float, str]:
        parsed = parse_timepoint_hours(str(tp))
        if parsed is not None:
            return (0, parsed, str(tp))
        return (1, 0.0, str(tp))

    def _review_collect_timepoints(self, fov: str) -> list:
        """Sorted list of timepoints available for ``fov`` (fluor + pipeline)."""
        _norm = self._review_norm_fov
        tp_values = sorted(
            {
                self._norm_timepoint(tp)
                for (f, tp) in self._preview_fluor.keys()
                if _norm(f) == fov and self._norm_timepoint(tp)
            },
            key=self._review_tp_sort_key,
        )
        pipeline_tp_values = sorted(
            {
                self._norm_timepoint(tp)
                for tp in (getattr(self, "_pipeline_info", {}) or {}).get("available_timepoints", [])
                if self._norm_timepoint(tp)
            },
            key=self._review_tp_sort_key,
        )
        if pipeline_tp_values:
            tp_values = sorted(set(tp_values) | set(pipeline_tp_values), key=self._review_tp_sort_key)
        return tp_values

    def _review_resolve_image_refs(self, *, fov_raw: str, tp_raw: str):
        """Resolve (fluor_ref, mask_ref), preferring top-hat if available."""
        fluor_ref = _resolve_ref_by_fov_tp(
            getattr(self, "_preview_tophat_fluor", {}),
            fov_raw=fov_raw, tp_raw=tp_raw,
            norm_timepoint=self._norm_timepoint,
        )
        if fluor_ref is None:
            fluor_ref = _resolve_ref_by_fov_tp(
                self._preview_fluor, fov_raw=fov_raw, tp_raw=tp_raw,
                norm_timepoint=self._norm_timepoint,
            )
        mask_ref = _resolve_ref_by_fov_tp(
            self._preview_mask, fov_raw=fov_raw, tp_raw=tp_raw,
            norm_timepoint=self._norm_timepoint,
        )
        return fluor_ref, mask_ref

    def _review_build_include_map(
        self, mask_arr, well: str, fov: str, tp: str,
    ) -> Dict[int, bool]:
        """Build {nid: is_included} for all labels in ``mask_arr``."""
        center = _np.asarray(mask_arr)
        include_by_nid: Dict[int, bool] = {
            int(nid): True for nid in _np.unique(center) if int(nid) > 0
        }
        rows = self._review_load_rows(well)
        for row in rows:
            row_fov, row_tp, row_nid = self._review_row_keys(row)
            if row_fov != fov or row_tp != tp or not row_nid:
                continue
            try:
                nid = int(float(row_nid))
            except Exception:
                continue
            incl = str(row.get("Included", "1")).strip()
            include_by_nid[nid] = (incl != "0")
        return include_by_nid

    def _refresh_review_image(self) -> None:
        if not hasattr(self, "_review_image_label"):
            return
        channel_switch_debug = _debug_flags.review_image_channel_switch_debug_enabled()
        image_load_debug = _debug_flags.review_image_load_debug_enabled()
        well = self._preview_selected_well
        if well is None:
            if channel_switch_debug:
                _logger.debug("[RI-CHSW step 6] refresh_review_image aborted: no selected well")
            return

        fov_raw = str(self._preview_fov_var.get() or "").strip()
        fov = self._review_norm_fov(fov_raw)
        if not fov_raw or fov_raw == "—" or not fov:
            self._review_image_status.setText("No FOV selected.")
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 6] refresh_review_image aborted: invalid fov raw=%r norm=%r",
                    fov_raw, fov,
                )
            return

        tp_values = self._review_collect_timepoints(fov)
        if channel_switch_debug:
            _logger.debug(
                "[RI-CHSW step 6] refresh_review_image start well=%r selected_fov_raw=%r normalized_fov=%r active_channel=%r",
                well, fov_raw, fov, getattr(self, "_active_image_channel", ""),
            )
        _set_combo_values(self._review_image_tp_menu, tp_values or ["—"])
        if tp_values and self._review_image_tp_var.get() not in tp_values:
            self._review_image_tp_var.set(tp_values[0])
        tp_raw = str(self._review_image_tp_var.get() or "").strip()
        tp = self._norm_timepoint(tp_raw)
        if not tp_raw or tp_raw == "—" or not tp:
            self._review_image_status.setText("No timepoint selected.")
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 6] refresh_review_image aborted: invalid timepoint raw=%r norm=%r",
                    tp_raw, tp,
                )
            return

        fluor_ref, mask_ref = self._review_resolve_image_refs(
            fov_raw=fov_raw, tp_raw=tp_raw,
        )
        if image_load_debug:
            fluor_path = getattr(fluor_ref, "full_path_str", str(fluor_ref)) if fluor_ref is not None else None
            mask_path = getattr(mask_ref, "full_path_str", str(mask_ref)) if mask_ref is not None else None
            _debug_flags.debug_with_source(
                _logger,
                "Review Image load attempt well=%s fov=%s tp=%s fluor_path=%s",
                well, fov, tp, fluor_path,
            )
            _debug_flags.debug_with_source(
                _logger,
                "Review Image load attempt well=%s fov=%s tp=%s mask_path=%s",
                well, fov, tp, mask_path,
            )
        if fluor_ref is None or mask_ref is None:
            self._review_image_status.setText("Missing fluorescence image or label map for selected FOV/timepoint.")
            if channel_switch_debug:
                _logger.debug(
                    "[RI-CHSW step 6] refresh_review_image missing refs fluor_ref=%r mask_ref=%r",
                    fluor_ref, mask_ref,
                )
            return
        self._review_image_is_tif = str(getattr(fluor_ref, "name", "")).lower().endswith((".tif", ".tiff"))

        fluor_arr = open_imgref_as_array(fluor_ref, greyscale=True)
        mask_arr = open_imgref_as_array(mask_ref, greyscale=True)
        if fluor_arr is None or mask_arr is None or not _NP_AVAILABLE or not _PIL_AVAILABLE:
            self._review_image_status.setText("Could not render review image (numpy/PIL unavailable).")
            return

        include_by_nid = self._review_build_include_map(mask_arr, well, fov, tp)
        preserve_view = bool(getattr(self, "_review_image_preserve_view_on_refresh", False))
        self._review_image_preserve_view_on_refresh = False
        if channel_switch_debug:
            _logger.debug("[RI-CHSW step 6->7] draw_review_image preserve_view=%s", preserve_view)
        self._draw_review_image(
            fluor_arr, mask_arr, include_by_nid,
            fit_lut=False, preserve_view=preserve_view,
        )

    def _review_image_resolve_lut(self, arr) -> Tuple[float, float]:
        chan = str(self._active_image_channel or "").lower()
        if hasattr(self, "_review_lut_min_var") and hasattr(self, "_review_lut_max_var"):
            try:
                lo = float(self._review_lut_min_var.get().strip())
                hi = float(self._review_lut_max_var.get().strip())
                if hi > lo:
                    self._review_image_lut_by_channel[chan] = (lo, hi)
                    return lo, hi
            except Exception:
                pass
        saved = self._review_image_lut_by_channel.get(chan)
        if saved is not None and saved[1] > saved[0]:
            return saved
        lo = float(arr.min())
        hi = float(arr.max())
        if hi <= lo:
            hi = lo + 1.0
        self._review_image_lut_by_channel[chan] = (lo, hi)
        return lo, hi

    def _review_image_auto_lut(self) -> None:
        arr = getattr(self, "_review_image_last_fluor_arr", None)
        if arr is None or not _NP_AVAILABLE:
            return
        arr_np = _np.asarray(arr, dtype=_np.float32)
        lo = float(arr_np.min())
        hi = float(arr_np.max())
        if hi <= lo:
            hi = lo + 1.0
        self._review_image_lut_by_channel[str(self._active_image_channel or "").lower()] = (lo, hi)
        if hasattr(self, "_review_lut_min_var") and hasattr(self, "_review_lut_max_var"):
            self._review_lut_min_var.set(f"{lo:.0f}")
            self._review_lut_max_var.set(f"{hi:.0f}")
        self._review_image_preserve_view_on_refresh = True
        self._refresh_review_image()

    def _review_image_commit_lut(self) -> None:
        arr = getattr(self, "_review_image_last_fluor_arr", None)
        if arr is None:
            return
        lo, hi = self._review_image_resolve_lut(_np.asarray(arr, dtype=_np.float32))
        if hasattr(self, "_review_lut_min_var") and hasattr(self, "_review_lut_max_var"):
            self._review_lut_min_var.set(f"{lo:.0f}")
            self._review_lut_max_var.set(f"{hi:.0f}")
        self._review_image_preserve_view_on_refresh = True
        self._refresh_review_image()

    def _draw_review_image(
        self,
        fluor_arr,
        mask_arr,
        include_by_nid: Dict[int, bool],
        *,
        fit_lut: bool = False,
        preserve_view: bool = False,
    ) -> None:
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug(
                "[RI-CHSW step 7] draw_review_image channel=%r fit_lut=%s preserve_view=%s",
                getattr(self, "_active_image_channel", ""),
                fit_lut,
                preserve_view,
            )
        arr = _np.asarray(fluor_arr, dtype=_np.float32)
        self._review_image_last_fluor_arr = arr
        m = _np.asarray(mask_arr)
        if fit_lut:
            lo, hi = float(arr.min()), float(arr.max())
            if hi <= lo:
                hi = lo + 1.0
            self._review_image_lut_by_channel[str(self._active_image_channel or "").lower()] = (lo, hi)
        else:
            lo, hi = self._review_image_resolve_lut(arr)
        if hasattr(self, "_review_lut_chan_lbl"):
            self._review_lut_chan_lbl.setText(f"{self._active_image_channel.upper()} LUT min:")
        if hasattr(self, "_review_lut_min_edit") and hasattr(self, "_review_lut_max_edit"):
            self._review_lut_min_edit.setText(f"{lo:.0f}")
            self._review_lut_max_edit.setText(f"{hi:.0f}")
        base = ((_np.clip(arr, lo, hi) - lo) / (hi - lo) * 255).astype(_np.uint8)
        rgb = _np.dstack([base, base, base])

        center_int = _np.rint(m).astype(_np.int32, copy=False)
        padded = _np.pad(center_int, 1, mode="constant", constant_values=0)
        center = padded[1:-1, 1:-1]
        boundary = (center > 0) & (
            (center != padded[:-2, 1:-1]) |
            (center != padded[2:, 1:-1]) |
            (center != padded[1:-1, :-2]) |
            (center != padded[1:-1, 2:])
        )
        include_mask = _np.zeros(center.shape, dtype=bool)
        for nid, included in include_by_nid.items():
            if included:
                include_mask |= (center == nid)
        draw_boundary = boundary & include_mask
        rgb[draw_boundary] = _np.array([255, 64, 64], dtype=_np.uint8)
        sel_nid = self._review_image_selected_nucleus
        if sel_nid is not None:
            sel_boundary = boundary & (center == int(sel_nid))
            rgb[sel_boundary] = _np.array([255, 230, 64], dtype=_np.uint8)

        img = _PILImage.fromarray(rgb, mode="RGB")
        self._review_image_base_pil = img
        if not preserve_view:
            self._review_image_zoom = 1.0
            self._review_image_pan_x = 0.0
            self._review_image_pan_y = 0.0
        self._render_review_image_display()
        self._review_image_label._mask_arr = center  # type: ignore[attr-defined]
        self._review_image_label._raw_arr = arr      # type: ignore[attr-defined]
        lbl = self._review_image_label
        lbl.setMouseTracking(True)

        def _ri_move(ev):
            self._on_review_image_hover(ev)
        def _ri_leave(ev):
            try:
                self._review_image_tooltip.hide()
            except Exception:
                pass
        def _ri_wheel(ev):
            self._on_review_image_wheel(ev)
        def _ri_press(ev):
            self._on_review_image_press(ev)
        def _ri_move_drag(ev):
            if ev.buttons() & Qt.LeftButton:
                self._on_review_image_drag(ev)
            else:
                _ri_move(ev)
        def _ri_release(ev):
            self._on_review_image_release(ev)

        lbl.mouseMoveEvent = _ri_move_drag
        lbl.leaveEvent = _ri_leave
        lbl.wheelEvent = _ri_wheel
        lbl.mousePressEvent = _ri_press
        lbl.mouseReleaseEvent = _ri_release
        lbl.setCursor(Qt.ForbiddenCursor if getattr(self, "_review_image_include_edit_mode", False) else Qt.PointingHandCursor)
        suffix = f"  \u00b7  highlighted nucleus {sel_nid}" if sel_nid is not None else ""
        self._review_image_status.setText(
            f"Showing channel {self._active_image_channel.upper()} with included cell boundaries.{suffix}"
        )
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug(
                "[RI-CHSW step 7] draw_review_image complete status_channel=%r zoom=%.3f pan=(%.1f, %.1f)",
                self._active_image_channel,
                float(getattr(self, "_review_image_zoom", 1.0)),
                float(getattr(self, "_review_image_pan_x", 0.0)),
                float(getattr(self, "_review_image_pan_y", 0.0)),
            )

    def _render_review_image_display(self) -> None:
        if not hasattr(self, "_review_image_label") or self._review_image_base_pil is None:
            return
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug("[RI-CHSW step 7] render_review_image_display start")
        img = self._review_image_base_pil
        iw, ih = img.size
        vp = self._review_image_canvas.viewport()
        cw = max(1, vp.width())
        ch = max(1, vp.height())
        fit = min(cw / max(iw, 1), ch / max(ih, 1))
        scale = max(0.05, fit * max(0.1, float(self._review_image_zoom)))
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        shown = img.resize((nw, nh), _PILImage.NEAREST)
        if shown.mode != "RGBA":
            shown = shown.convert("RGBA")
        data = shown.tobytes("raw", "RGBA")
        qimg = QImage(data, nw, nh, 4 * nw, QImage.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(qimg)
        self._review_image_label.setPixmap(pm)
        self._review_image_label.resize(max(nw, cw), max(nh, ch))
        self._review_image_scale = scale
        pan_x = float(getattr(self, "_review_image_pan_x", 0.0))
        pan_y = float(getattr(self, "_review_image_pan_y", 0.0))
        hbar = self._review_image_canvas.horizontalScrollBar()
        vbar = self._review_image_canvas.verticalScrollBar()
        cx = max(0, (max(nw, cw) - cw) // 2) - int(pan_x)
        cy = max(0, (max(nh, ch) - ch) // 2) - int(pan_y)
        hbar.setValue(max(hbar.minimum(), min(hbar.maximum(), cx)))
        vbar.setValue(max(vbar.minimum(), min(vbar.maximum(), cy)))
        if _debug_flags.review_image_channel_switch_debug_enabled():
            _logger.debug(
                "[RI-CHSW step 7] render_review_image_display done img=%sx%s shown=%sx%s scale=%.4f",
                iw,
                ih,
                nw,
                nh,
                scale,
            )

    def _review_image_zoom_step(self, direction: int) -> None:
        steps = [0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
        cur = getattr(self, "_review_image_zoom", 1.0)
        idx = min(range(len(steps)), key=lambda i: abs(steps[i] - cur))
        idx = max(0, min(len(steps) - 1, idx + direction))
        self._review_image_zoom = steps[idx]
        self._render_review_image_display()

    def _review_image_zoom_fit(self) -> None:
        self._review_image_zoom = 1.0
        self._review_image_pan_x = 0.0
        self._review_image_pan_y = 0.0
        self._render_review_image_display()

    def _on_review_image_wheel(self, event) -> None:
        try:
            dy = int(event.angleDelta().y())
        except Exception:
            dy = 0
        direction = +1 if dy > 0 else -1 if dy < 0 else 0
        if direction:
            self._review_image_zoom_step(direction)

    def _on_review_image_press(self, event) -> None:
        self._review_image_dragging = True
        self._review_image_drag_moved = False
        gp = event.globalPosition().toPoint()
        self._review_image_drag_last_xy = (int(gp.x()), int(gp.y()))

    def _on_review_image_drag(self, event) -> None:
        if not getattr(self, "_review_image_dragging", False):
            return
        gp = event.globalPosition().toPoint()
        gx, gy = int(gp.x()), int(gp.y())
        lx, ly = self._review_image_drag_last_xy
        dx = gx - lx
        dy = gy - ly
        if dx or dy:
            self._review_image_drag_moved = True
        self._review_image_pan_x = float(getattr(self, "_review_image_pan_x", 0.0) + dx)
        self._review_image_pan_y = float(getattr(self, "_review_image_pan_y", 0.0) + dy)
        self._review_image_drag_last_xy = (gx, gy)
        self._render_review_image_display()

    def _on_review_image_release(self, event) -> None:
        was_dragging = getattr(self, "_review_image_dragging", False)
        moved = getattr(self, "_review_image_drag_moved", False)
        self._review_image_dragging = False
        self._review_image_drag_moved = False
        if was_dragging and not moved:
            self._on_review_image_click(event)

    def _on_review_image_hover(self, event: Any) -> None:
        if not hasattr(self, "_review_image_label"):
            return
        pm = self._review_image_label.pixmap()
        if pm is not None and not pm.isNull():
            self._review_image_label._sz_w = int(pm.width())  # type: ignore[attr-defined]
            self._review_image_label._sz_h = int(pm.height())  # type: ignore[attr-defined]
        else:
            self._review_image_label._sz_w = int(self._review_image_label.width())  # type: ignore[attr-defined]
            self._review_image_label._sz_h = int(self._review_image_label.height())  # type: ignore[attr-defined]
        _show_image_pixel_tooltip_controller(
            self,
            event,
            f"{self._active_image_channel.upper()}",
            label=self._review_image_label,
        )

    def _on_review_image_click(self, event: Any) -> None:
        _on_review_image_click_controller(self, event, _logger)

    def _select_review_csv_row_for_cell(self, fov: str, tp: str, nucleus_id: str) -> None:
        _select_review_csv_row_for_cell_controller(self, fov, tp, nucleus_id, _logger)

    def _set_review_image_include_mode(self, enabled: bool) -> None:
        self._review_image_include_edit_mode = bool(enabled)
        if hasattr(self, "_review_image_label"):
            self._review_image_label.setCursor(Qt.ForbiddenCursor if enabled else Qt.PointingHandCursor)
        if enabled:
            self._set_status("Review Image Include edit mode ON: click a cell to set Included=0.")
        else:
            self._set_status("Review Image Include edit mode OFF.")

    def _toggle_selected_review_cell(self) -> None:
        self._set_review_image_include_mode(not getattr(self, "_review_image_include_edit_mode", False))

    def _set_review_cell_included(self, fov: str, tp: str, nid: str, included: str) -> None:
        if self._preview_selected_well is None:
            return
        fov_n, tp_n, nid_n = self._review_row_keys({"fov": fov, "tp": tp, "nucleus_id": nid})
        if not (fov_n and tp_n and nid_n):
            return
        key = (self._preview_selected_well, fov_n, tp_n, nid_n)
        self._review_included_overrides[key] = str(included).strip() or "1"
        prev_zoom = float(getattr(self, "_review_image_zoom", 1.0))
        prev_pan_x = float(getattr(self, "_review_image_pan_x", 0.0))
        prev_pan_y = float(getattr(self, "_review_image_pan_y", 0.0))
        self._refresh_review_csv_rows()
        self._refresh_review_image()
        self._review_image_zoom = prev_zoom
        self._review_image_pan_x = prev_pan_x
        self._review_image_pan_y = prev_pan_y
        self._render_review_image_display()

    def _zoom_review_image_to_selected_nucleus(self, zoom: float = 3.0) -> None:
        if not hasattr(self, "_review_image_label") or not hasattr(self, "_review_image_canvas"):
            return
        nid = self._review_image_selected_nucleus
        mask_arr = getattr(self._review_image_label, "_mask_arr", None)
        if nid is None or mask_arr is None:
            return
        ys, xs = _np.where(mask_arr == int(nid))
        if len(xs) == 0 or len(ys) == 0:
            return
        cx = float(xs.mean())
        cy = float(ys.mean())
        self._review_image_zoom = float(max(1.0, zoom))
        img = self._review_image_base_pil
        if img is None:
            return
        iw, ih = img.size
        vp = self._review_image_canvas.viewport()
        cw = max(1, vp.width())
        ch = max(1, vp.height())
        fit = min(cw / max(iw, 1), ch / max(ih, 1))
        scale = max(0.05, fit * max(0.1, float(self._review_image_zoom)))
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        base_x = max(8, (cw - nw) // 2)
        base_y = max(8, (ch - nh) // 2)
        self._review_image_pan_x = (cw / 2.0) - base_x - (cx * scale)
        self._review_image_pan_y = (ch / 2.0) - base_y - (cy * scale)
        self._render_review_image_display()

    def _on_review_csv_row_double_click(self, event) -> None:
        _on_review_csv_row_double_click_controller(self, event)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_plot_data(self) -> None:
        from well_viewer.export_service import export_plot_data as _export_plot_data

        _export_plot_data(self)

    def _export_raw_data_csv(self) -> None:
        from well_viewer.export_service import export_raw_data_csv as _export_raw_data_csv

        _export_raw_data_csv(self)

    # ── Batch export ──────────────────────────────────────────────────────────

    def _open_batch_export(self) -> None:
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Batch Export.")
            return
        if hasattr(self, "_notebook") and hasattr(self._notebook, "select_by_text"):
            self._notebook.select_by_text("Batch Export")
        if hasattr(self, "_batch_export_set_mode"):
            self._batch_export_set_mode("line")

    # ── Montage ───────────────────────────────────────────────────────────────

    # ── Plotting ──────────────────────────────────────────────────────────────

    def _redraw(self) -> None:
        _plot_redraw_orchestrator(
            self,
            lineplot_redraw=_lineplot_redraw,
            apply_ax_style=apply_ax_style,
            aggregate_with_threshold=aggregate_with_threshold,
            all_fluor_values=_all_fluor_values,
            all_fluor_values_filtered=_all_fluor_values_filtered,
            plot_bg=PLOT_BG,
            plot_spn=PLOT_SPN,
            txt_pri=TXT_PRI,
            txt_mut=TXT_MUT,
            warn=WARN,
            well_colors=WELL_COLORS,
        )
        from well_viewer.figure_export_editor import apply_export_style_to_current

        apply_export_style_to_current(self, self._line_fig, getattr(self, "_line_canvas", None))

    # ── Bar plot tab ──────────────────────────────────────────────────────────

    def _on_tab_change(self, _e=None) -> None:
        """Show/hide the sidebar and refresh whichever tab is now active."""
        if not hasattr(self, "_line_ax_mean"):
            return
        tab = self._notebook.tabText(self._notebook.currentIndex())
        prev_tab = getattr(self, "_last_tab_name", None)
        prev_selected = set(getattr(self, "_selected_wells", set()))

        self._sidebar_main_frame.setVisible(False)
        self._sidebar_preview_frame.setVisible(False)
        self._sidebar_sample_frame.setVisible(False)
        self._sidebar_groups_frame.setVisible(False)
        self._sidebar_stats_frame.setVisible(False)

        if tab == "Movie Montage":
            self._sync_preview_well_for_image_tabs()
            self._sidebar_preview_frame.setVisible(True)
            self._refresh_preview_picker()
            self._update_preview(self._preview_selected_well)

        elif tab == "Review Image":
            self._sync_preview_well_for_image_tabs()
            self._sidebar_preview_frame.setVisible(True)
            self._refresh_preview_picker()
            self._update_preview(self._preview_selected_well)
            self._refresh_review_image()

        elif tab == "Sample Definitions":
            self._sidebar_sample_frame.setVisible(True)
            self._groups_centre_refresh()

        elif tab == "Statistics":
            self._sidebar_stats_frame.setVisible(True)
            # Auto-populate from rep-sets on first visit
            if not self._stats_groups and hasattr(self, "_stats_grp_inner"):
                self._stats_sync_from_app()
            if hasattr(self, "_stats_tp_cb"):
                self._stats_update_tp_menu()

        elif tab == "Batch Export":
            # Batch Export uses the standard sidebar well picker.
            self._sidebar_main_frame.setVisible(True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.setVisible(True)
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.setVisible(True)
            self._refresh_sidebar_map()
            if hasattr(self, "_batch_export_set_mode"):
                mode = getattr(self, "_batch_export_inline_state", {}).get("mode", "line")
                self._batch_export_set_mode(mode)

        elif tab == "Review CSV":
            self._sidebar_main_frame.setVisible(True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.setVisible(True)
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.setVisible(True)
            self._refresh_sidebar_map()
            self._refresh_review_csv()

        elif tab == "smFISH":
            self._sidebar_main_frame.setVisible(True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.setVisible(False)
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.setVisible(False)
            if len(self._selected_wells) > 1:
                keep = self._last_sel if self._last_sel in self._selected_wells else next(iter(self._selected_wells))
                self._selected_wells = {keep}
            self._refresh_sidebar_map()
            if hasattr(self, "_smfish_tab"):
                self._smfish_tab.sync_from_app()

        elif tab == "Cell Gating":
            self._sidebar_main_frame.setVisible(True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.setVisible(True)
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.setVisible(True)
            self._refresh_sidebar_map()
            if hasattr(self, "_cell_gating_tab") and self._cell_gating_tab is not None:
                self._cell_gating_tab._load_cell_areas()

        else:
            # Line Graphs, Bar Plots, or Scatter — unified picker always shown
            self._sidebar_main_frame.setVisible(True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.setVisible(True)
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.setVisible(True)
            self._refresh_sidebar_map()
            if tab == "Bar Plots":
                self._update_bar_tp_menu()
                self._redraw_bars()
            elif tab == "Scatter Plot: Cells":
                self._update_scatter_menus()
                self._redraw_scatter()
            elif tab == "Scatter Plot: Aggregate":
                self._update_scatter_menus()
                self._redraw_scatter_agg()
            else:
                self._redraw()

        self._run_tab_switch_smoke_checks(prev_tab, tab, prev_selected)
        self._last_tab_name = tab

    def _sync_preview_well_for_image_tabs(self) -> None:
        """Keep current preview well unless an active group supplies one."""
        # Preserve explicit user choice when still valid.
        current = getattr(self, "_preview_selected_well", None)
        if current in self._well_paths:
            # If active group has wells, prefer first group well for image tabs.
            if 0 <= self._bar_active_grp < len(self._bar_groups):
                grp = self._bar_groups[self._bar_active_grp]
                for tok in grp.wells:
                    if tok in self._well_paths:
                        self._preview_selected_well = tok
                        return
            return

        # If no valid current well, use first well from active group.
        if 0 <= self._bar_active_grp < len(self._bar_groups):
            grp = self._bar_groups[self._bar_active_grp]
            for tok in grp.wells:
                if tok in self._well_paths:
                    self._preview_selected_well = tok
                    return

        # Final fallback: keep previous behavior of choosing first available well.
        if self._well_paths:
            self._preview_selected_well = sorted(self._well_paths.keys(), key=self._parse_rc)[0]

    def _run_tab_switch_smoke_checks(
        self,
        prev_tab: Optional[str],
        tab: str,
        prev_selected: set,
    ) -> None:
        """Debug guardrails for Line/Bar/Batch sidebar continuity."""
        watched = {"Line Graphs", "Bar Plots", "Batch Export"}
        if tab not in watched:
            return

        # Batch Export should share the same in-memory selection/group objects
        # used by line/bar/scatter render paths.
        expected_ids = (
            id(self._selected_wells),
            id(self._rep_sets),
            id(self._bar_groups),
        )
        if not hasattr(self, "_selection_model_identity"):
            self._selection_model_identity = expected_ids
        elif self._selection_model_identity != expected_ids:
            _logger.warning(
                "Selection model identity changed across tab switch: "
                "_selected_wells/_rep_sets/_bar_groups should be shared."
            )

        # UI smoke check: switching among Line/Bar/Batch must not mutate the
        # current per-well selection by itself.
        if prev_tab in watched and prev_selected != self._selected_wells:
            _logger.warning(
                "Tab switch altered selected wells unexpectedly: %s -> %s",
                prev_tab, tab,
            )

    def _show_line_sidebar(self) -> None:
        """No-op: the unified well picker is always visible for plot tabs."""
        pass

    def _build_review_csv_tab(self, parent) -> None:
        from well_viewer.tabs.review_csv_tab_view import build_review_csv_tab as _v
        _v(self, parent)

    def _refresh_review_csv(self) -> None:
        if not hasattr(self, "_review_csv_table"):
            return
        sels = sorted(self._selected_wells, key=self._parse_rc)
        if not sels:
            self._review_well_lbl.setText("(select well(s))")
            _set_combo_values(self._review_fov_cb, [])
            _set_combo_values(self._review_tp_cb, [])
            self._review_fov_cb.setCurrentText("")
            self._review_tp_cb.setCurrentText("")
            self._refresh_review_csv_rows([])
            self._review_csv_msg_lbl.setText("Select one or more wells in the picker.")
            return

        self._review_well_lbl.setText(
            ", ".join(sels[:3]) + (f" (+{len(sels) - 3} more)" if len(sels) > 3 else "")
        )
        rows: List[dict] = []
        for label in sels:
            rows.extend(self._review_load_rows(label))
        if not rows:
            _set_combo_values(self._review_fov_cb, [])
            _set_combo_values(self._review_tp_cb, [])
            self._review_fov_cb.setCurrentText("")
            self._review_tp_cb.setCurrentText("")
            self._refresh_review_csv_rows([])
            self._review_csv_msg_lbl.setText("No CSV rows loaded for selected well(s).")
            return

        fovs = sorted({
            str(r.get("fov", r.get("FOV", ""))).strip()
            for r in rows
            if str(r.get("fov", r.get("FOV", ""))).strip()
        })
        tps: list[str] = []
        seen_tps: set[str] = set()
        for row in rows:
            raw_tp = str(row.get("timepoint", row.get("tp", row.get("time", "")))).strip()
            norm_tp = self._norm_timepoint(raw_tp)
            if not norm_tp or norm_tp in seen_tps:
                continue
            seen_tps.add(norm_tp)
            tps.append(norm_tp)
        tps.sort(key=lambda tp: (parse_timepoint_hours(tp) is None, parse_timepoint_hours(tp) or 0.0, tp))
        _set_combo_values(self._review_fov_cb, fovs)
        _set_combo_values(self._review_tp_cb, tps)
        if fovs and self._review_fov_cb.currentText() not in fovs:
            self._review_fov_cb.setCurrentText(fovs[0])
        if tps and self._review_tp_cb.currentText() not in tps:
            self._review_tp_cb.setCurrentText(tps[0])
        self._refresh_review_csv_rows(rows)

    def _refresh_review_csv_rows(self, rows: Optional[List[dict]] = None) -> None:
        if not hasattr(self, "_review_csv_table"):
            return
        table = self._review_csv_table
        table.setRowCount(0)

        if rows is None:
            sels = sorted(self._selected_wells, key=self._parse_rc)
            rows = []
            for label in sels:
                rows.extend(self._review_load_rows(label))

        def _norm(v: object) -> str:
            s = str(v or "").strip()
            if not s:
                return ""
            try:
                return f"{float(s):g}"
            except Exception:
                return s

        fov_sel = _norm(self._review_fov_cb.currentText()) if hasattr(self, "_review_fov_cb") else ""
        tp_sel = self._norm_timepoint(self._review_tp_cb.currentText()) if hasattr(self, "_review_tp_cb") else ""
        filtered = []
        for row in rows:
            row_fov = _norm(row.get("fov", row.get("FOV", "")))
            row_tp = self._norm_timepoint(row.get("timepoint", row.get("tp", row.get("time", ""))))
            if fov_sel and row_fov != fov_sel:
                continue
            if tp_sel and row_tp != tp_sel:
                continue
            filtered.append(row)

        if not filtered:
            _logger.warning(
                "No Review CSV rows matched filters: selected_wells=%s fov=%s tp=%s total_rows=%d",
                sorted(self._selected_wells, key=self._parse_rc),
                fov_sel, tp_sel, len(rows),
            )
            if not rows:
                table.setColumnCount(0)
                self._review_csv_msg_lbl.setText("No rows are available for the selected well(s).")
                return
            # Fallback: if the filters are mismatched for any reason, still
            # show all loaded rows from selected well(s) instead of an empty table.
            filtered = list(rows)
            self._review_csv_msg_lbl.setText(
                "No exact Well/FOV/Timepoint match. Showing all selected rows instead."
            )
            ctx = getattr(self, "_review_csv_lookup_context", {}) or {}
            ctx_txt = (
                f" well={ctx.get('well','')} fov={ctx.get('fov','')} tp={ctx.get('tp','')} nucleus_id={ctx.get('nucleus_id','')}"
                if ctx else ""
            )
            self._set_status(
                f"Review CSV fallback active: no exact match for FOV={fov_sel}, TP={tp_sel}; showing {len(filtered)} row(s).{ctx_txt}"
            )

        cols = list(filtered[0].keys())
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for ci in range(len(cols)):
            table.setColumnWidth(ci, 120)
        for row in filtered:
            r = table.rowCount()
            table.insertRow(r)
            for ci, c in enumerate(cols):
                table.setItem(r, ci, QTableWidgetItem(str(row.get(c, ""))))
        self._review_csv_msg_lbl.setText(f"Showing {len(filtered):,} row(s).")

    def _review_load_rows(self, label: str) -> List[dict]:
        try:
            # Use cached/parsed rows so Review CSV reflects runtime-added columns
            # (e.g. Included) and latest gating-driven inclusion updates.
            rows = [dict(row) for row in self._get_rows(label)]
            tok = self._extract_well_token(label) or label
            for row in rows:
                row.setdefault("well", tok)
                if "Included" not in row:
                    # Canonical review flag column; defaults to included.
                    # Promote legacy lowercase field if present.
                    row["Included"] = str(row.get("included", "")).strip() or "1"
                if "included" in row:
                    row.pop("included", None)
                fov, tp, nid = self._review_row_keys(row)
                if fov and tp and nid:
                    key = (label, fov, tp, nid)
                    override = self._review_included_overrides.get(key)
                    if override is not None:
                        row["Included"] = override
            return rows
        except Exception:
            return []

    def _update_bar_tp_menu(self) -> None:
        """
        Populate the timepoint dropdown with the union of all timepoints
        present across all loaded wells.

        The available timepoints are always drawn from the full loaded dataset,
        not from the current selection — the selection controls what is plotted,
        but the dropdown must remain usable even when nothing is selected yet.
        """
        if not self._well_paths:
            _set_combo_values(self._bar_tp_cb, ["—"])
            self._bar_tp_cb.setCurrentText("—")
            return

        all_tps: set = set(self._all_timepoints_cache)

        # If no timepoints were found the schema had no timepoint field.
        # Use 0.0 as a single synthetic timepoint so bar plots remain usable.
        if not all_tps and self._well_paths:
            all_tps.add(0.0)

        sorted_tps = sorted(all_tps)
        tp_strs    = [f"{t:.4g}" for t in sorted_tps]

        cur = self._bar_tp_cb.currentText()
        _set_combo_values(self._bar_tp_cb, tp_strs)
        if cur in tp_strs:
            self._bar_tp_cb.setCurrentText(cur)
        elif tp_strs:
            self._bar_tp_cb.setCurrentText(tp_strs[0])
        else:
            self._bar_tp_cb.setCurrentText("—")

    # ── Bar drag-and-drop reordering ─────────────────────────────────────────

    def _bar_event_xdata(self, event) -> "Optional[float]":
        """Return data-x for a matplotlib MouseEvent over either bar axis.

        Returns None if the cursor is outside the bar plot axes.
        """
        ax = getattr(event, "inaxes", None)
        if ax is not self._ax_bar_mean and ax is not self._ax_bar_frac:
            return None
        xdata = getattr(event, "xdata", None)
        if xdata is None:
            return None
        return float(xdata)

    def _bar_current_keys(self) -> List:
        """Return the ordered list of keys currently rendered on the bar plot.

        In rep-set mode: list of rset.name strings.
        In per-well mode: list of well label strings.
        Respects any existing _bar_order.
        """
        return _bar_ordered_keys(self)

    def _bar_idx_at_x(self, xdata: float, n: int) -> int:
        """Return the bar index nearest to *xdata*, clamped to [0, n-1]."""
        return max(0, min(n - 1, int(round(xdata))))

    def _bar_reset_order(self) -> None:
        self._bar_order = None
        self._bar_reset_order_btn.setProperty("variant", "toggle_muted")
        self._bar_reset_order_btn.style().unpolish(self._bar_reset_order_btn)
        self._bar_reset_order_btn.style().polish(self._bar_reset_order_btn)
        self._redraw_bars()

    def _on_bar_drag_press(self, event) -> None:
        """Begin drag — record which bar was pressed."""
        if getattr(event, "button", None) != 1:
            return
        xdata = self._bar_event_xdata(event)
        if xdata is None:
            return
        keys = self._bar_current_keys()
        n    = len(keys)
        if n < 2:
            return
        idx = self._bar_idx_at_x(xdata, n)
        self._bar_drag_state.update(active=True, src_idx=idx, cur_idx=idx)

    def _on_bar_drag_motion(self, event) -> None:
        """Update drop-target indicator while dragging."""
        ds = self._bar_drag_state
        if not ds["active"]:
            return
        xdata = self._bar_event_xdata(event)
        if xdata is None:
            return
        keys = self._bar_current_keys()
        n    = len(keys)
        if n < 2:
            return
        tgt = self._bar_idx_at_x(xdata, n)
        if tgt == ds["cur_idx"]:
            return
        ds["cur_idx"] = tgt

        # Draw a vertical guide line in both axes at the drop position
        for ax in (self._ax_bar_mean, self._ax_bar_frac):
            for ln in list(ax.lines):
                if getattr(ln, "_bar_drag_guide", False):
                    ln.remove()
            if tgt > ds["src_idx"]:
                guide_x = min(tgt + 0.5, n - 0.5)
            else:
                guide_x = max(tgt - 0.5, -0.5)
            ln = ax.axvline(guide_x, color=ACCENT, lw=1.5, ls="--",
                            alpha=0.8, zorder=10)
            ln._bar_drag_guide = True   # type: ignore[attr-defined]
        self._bar_canvas.draw_idle()

    def _on_bar_drag_release(self, event) -> None:
        """Finalise drop — reorder and redraw (Tk ButtonRelease-1)."""
        ds = self._bar_drag_state
        if not ds["active"]:
            return
        ds["active"] = False

        # Remove guide lines
        for ax in (self._ax_bar_mean, self._ax_bar_frac):
            for ln in list(ax.lines):
                if getattr(ln, "_bar_drag_guide", False):
                    ln.remove()

        src = ds["src_idx"]
        tgt = ds["cur_idx"]
        if src == tgt:
            self._bar_canvas.draw_idle()
            return

        keys = self._bar_current_keys()
        if not (0 <= src < len(keys) and 0 <= tgt < len(keys)):
            self._bar_canvas.draw_idle()
            return

        item = keys.pop(src)
        keys.insert(tgt, item)
        self._bar_order = keys
        self._bar_reset_order_btn.setProperty("variant", "toggle_accent")
        self._bar_reset_order_btn.style().unpolish(self._bar_reset_order_btn)
        self._bar_reset_order_btn.style().polish(self._bar_reset_order_btn)
        self._redraw_bars()

    def _toggle_log_scale(self) -> None:
        """Toggle log y-axis for beeswarm fluor panel."""
        self._bar_log_scale.set(not self._bar_log_scale.get())
        on = self._bar_log_scale.get()
        self._bar_log_btn.setChecked(on)
        self._bar_log_btn.setProperty("variant", "toggle_warn" if on else "toggle")
        self._bar_log_btn.style().unpolish(self._bar_log_btn)
        self._bar_log_btn.style().polish(self._bar_log_btn)
        self._redraw_bars()

    def _apply_bar_ylims(
        self,
        ax_mean: "Axes",
        ax_frac: "Axes",
        log_scale: bool = False,
    ) -> None:
        """Apply user-specified y-axis limits and optional log scale."""
        _bar_apply_ylims(self, ax_mean, ax_frac, log_scale=log_scale)

    def _toggle_swarm(self) -> None:
        """Toggle beeswarm / bar mode and update the button appearance."""
        self._bar_swarm.set(not self._bar_swarm.get())
        on = self._bar_swarm.get()
        self._swarm_btn.setChecked(on)
        if on and self._bar_violin.get():
            # Swarm and violin are mutually exclusive
            self._bar_violin.set(False)
            self._violin_btn.setChecked(False)
            self._violin_slider.setEnabled(False)
        self._redraw_bars()

    def _toggle_violin(self) -> None:
        """Toggle violin / bar mode and update the button appearance."""
        self._bar_violin.set(not self._bar_violin.get())
        on = self._bar_violin.get()
        self._violin_btn.setChecked(on)
        self._violin_slider.setEnabled(on)
        if on and self._bar_swarm.get():
            # Mutually exclusive with beeswarm
            self._bar_swarm.set(False)
            self._swarm_btn.setChecked(False)
        self._redraw_bars()

    def _draw_violin(
        self,
        ax_mean: "Axes",
        ax_frac: "Axes",
        wells: List[str],
        colors: List[str],
        xlabels: List[str],
        target_t: float,
        tp_str: str,
        threshold: float,
    ) -> None:
        """
        Violin plot rendering: one column per well/group, KDE-smoothed distribution.

        Mean fluor panel: filled KDE shape (cells above threshold) with median marker.
        Fraction panel: scalar dot per well (same as beeswarm).

        Bandwidth is controlled by self._violin_bw; higher = smoother.
        """
        try:
            from scipy.stats import gaussian_kde
        except ImportError:
            ax_mean.text(0.5, 0.5, "scipy required for violin plot",
                         transform=ax_mean.transAxes, ha="center", va="center",
                         color=TXT_MUT, fontsize=9)
            return

        import numpy as np_local
        n       = len(wells)
        slider = getattr(self, "_violin_slider", None)
        bw_raw = float(slider.value()) / 100.0 if slider is not None else 1.0
        bw      = max(0.05, bw_raw)
        bar_w   = min(0.4, 3.0 / max(n, 1))   # half-width of each violin

        xs_ticks = list(range(n))
        frac_vals: List[float] = []

        for i, (lbl, color) in enumerate(zip(wells, colors)):
            rows = self._get_rows(lbl)
            vals: List[float] = []
            n_total = n_above = 0
            for row in rows:
                if not row_is_included(row):
                    continue
                raw_t = row.get("timepoint_hours")
                try:
                    t = float(raw_t)
                except (TypeError, ValueError):
                    continue
                if abs(t - target_t) > 1e-6:
                    continue
                try:
                    v = float(row[self._active_val_col])
                except (KeyError, ValueError, TypeError):
                    continue
                n_total += 1
                if v > threshold:
                    n_above += 1
                    vals.append(v)

            frac_vals.append(n_above / n_total if n_total else float("nan"))

            if len(vals) < 3:
                # Too few points for KDE — fall back to a thin bar
                if vals:
                    ax_mean.scatter([i], [vals[0]], c=color, s=20, zorder=4)
                continue

            arr = np_local.array(vals, dtype=float)
            kde = gaussian_kde(arr, bw_method=bw)
            y_min, y_max = arr.min(), arr.max()
            y_pad = (y_max - y_min) * 0.05
            ys = np_local.linspace(y_min - y_pad, y_max + y_pad, 200)
            density = kde(ys)
            # Normalise density to the violin half-width
            max_d = density.max()
            if max_d > 0:
                density = density / max_d * bar_w

            # Draw filled violin (mirrored around x=i)
            ax_mean.fill_betweenx(ys, i - density, i + density,
                                  color=color, alpha=0.55, zorder=2)
            ax_mean.plot(i - density, ys, color=color, lw=0.6, alpha=0.7, zorder=3)
            ax_mean.plot(i + density, ys, color=color, lw=0.6, alpha=0.7, zorder=3)

            # Median marker
            median = float(np_local.median(arr))
            ax_mean.hlines(median, i - bar_w * 0.6, i + bar_w * 0.6,
                           colors="white", lw=2.0, zorder=5)
            ax_mean.hlines(median, i - bar_w * 0.6, i + bar_w * 0.6,
                           colors=color, lw=1.2, zorder=6)

        # Fraction panel — scalar dot per well
        for i, (fv, color) in enumerate(zip(frac_vals, colors)):
            if not math.isnan(fv):
                ax_frac.scatter([i], [fv], c=color, s=30, zorder=3, linewidths=0)
            else:
                ax_frac.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                                marker="x", zorder=3, linewidths=1)

        # Threshold line, tick labels
        ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--", alpha=0.7, zorder=1)
        ax_frac.axhline(0.5, color=BORDER, lw=0.8, ls="--", alpha=0.5, zorder=1)
        for ax in (ax_mean, ax_frac):
            ax.set_xticks(xs_ticks)
            ax.set_xticklabels(xlabels,
                               rotation=45 if n > 8 else 0,
                               ha="right" if n > 8 else "center",
                               fontsize=7)
            ax.set_xlim(-0.6, n - 0.4)
        ax_frac.set_ylim(-0.05, 1.05)
        ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
        ax_mean.set_title(
            f"{self._active_channel.upper()} distribution (violin, bw={bw:.2f})  —  t = {tp_str} h",
            color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)
        ax_frac.set_title(
            f"Fraction above threshold  —  t = {tp_str} h",
            color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)

    def _draw_beeswarm(
        self,
        ax_mean: "Axes",
        ax_frac: "Axes",
        wells: List[str],          # ordered list of well labels to plot
        colors: List[str],         # parallel colour per well
        xlabels: List[str],        # x-tick labels
        target_t: float,
        tp_str: str,
        threshold: float,
        log_scale: bool = False,
    ) -> None:
        """
        Beeswarm rendering: one column per well, each cell a point.

        Mean fluor panel: raw per-cell values above threshold, jittered.
        Fraction panel: per-well fraction (scalar dot, no jitter needed).
        Replicate groupings are ignored — every well is plotted independently.
        When log_scale=True, zero-valued placeholders are omitted.
        """
        n = len(wells)
        xs_ticks = list(range(n))
        bar_w    = min(0.35, 3.0 / max(n, 1))  # narrow spread per column

        for i, (lbl, color) in enumerate(zip(wells, colors)):
            rows = self._get_rows(lbl)
            # Collect raw per-cell values at target_t above threshold
            cell_vals: List[float] = []
            frac_val: Optional[float] = None
            n_above = n_total = 0
            for row in rows:
                if not row_is_included(row):
                    continue
                raw = row.get("timepoint_hours")
                t: Optional[float] = (raw if isinstance(raw, float)
                                      and not math.isnan(raw)
                                      else parse_timepoint_hours(
                                          str(row.get("timepoint", ""))))
                if t is None or abs(t - target_t) > 1e-6:
                    continue
                try:
                    val = float(row[self._active_val_col])
                except (KeyError, ValueError, TypeError):
                    continue
                n_total += 1
                if val > threshold:
                    n_above += 1
                    cell_vals.append(val)
            if n_total > 0:
                frac_val = n_above / n_total

            if cell_vals:
                jx, jy = _beeswarm_jitter(cell_vals, x_center=float(i),
                                           max_spread=bar_w)
                ax_mean.scatter(jx, jy, c=color, s=6, alpha=0.55,
                                zorder=3, linewidths=0)
                # Mean marker
                m = sum(cell_vals) / len(cell_vals)
                ax_mean.plot([i - bar_w * 0.6, i + bar_w * 0.6],
                             [m, m], color=color, lw=1.5, zorder=4)
            else:
                # No data placeholder: tiny cross (omitted in log mode since log(0) undef)
                if not log_scale:
                    ax_mean.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                                    marker="x", zorder=3, linewidths=1)

            if frac_val is not None:
                ax_frac.scatter([i], [frac_val], c=color, s=30,
                                zorder=3, linewidths=0)
            else:
                ax_frac.scatter([i], [0], c=CLR_PLACEHOLDER, s=16,
                                marker="x", zorder=3, linewidths=1)

        ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--",
                        alpha=0.7, zorder=1)
        ax_frac.axhline(0.5, color=BORDER, lw=0.8, ls="--",
                        alpha=0.5, zorder=1)
        for ax in (ax_mean, ax_frac):
            ax.set_xticks(xs_ticks)
            ax.set_xticklabels(xlabels,
                               rotation=45 if n > 8 else 0,
                               ha="right" if n > 8 else "center",
                               fontsize=7)
            ax.set_xlim(-0.6, n - 0.4)
        ax_frac.set_ylim(-0.05, 1.05)
        ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
        ax_mean.set_title(
            f"{self._active_channel.upper()} per cell (above threshold)  —  t = {tp_str} h",
            color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)
        ax_frac.set_title(
            f"Fraction above threshold  —  t = {tp_str} h",
            color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)

    def _redraw_bars(self) -> None:
        """Draw bar/violin/beeswarm views for the selected timepoint."""
        ax_mean = self._ax_bar_mean
        ax_frac = self._ax_bar_frac
        ax_mean.cla()
        ax_frac.cla()

        use_sem = self._use_sem.get()
        band_lbl = "SEM" if use_sem else "SD"
        threshold = self._get_thresh_frac_on(self._active_channel)

        active_rsets = self._rep_sets_active()
        bar_selected = self._selected_bar_wells(active_rsets)

        _ch = self._active_channel.upper()
        apply_ax_style(ax_mean,
                       f"Mean {_ch} (above threshold) ± {band_lbl}",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac,
                       "Fraction of Cells Above Threshold",
                       "Fraction")
        ax_frac.set_ylim(-0.05, 1.05)

        if not bar_selected and not active_rsets:
            self._draw_bar_empty_state(ax_mean, ax_frac, NO_SELECTION_MSG)
            return

        tp_data = self._resolve_bar_timepoint()
        if tp_data is None:
            self._draw_bar_empty_state(ax_mean, ax_frac, "Select a timepoint above")
            return
        target_t, tp_str = tp_data

        if self._draw_per_cell_bar_mode(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            active_rsets=active_rsets,
            target_t=target_t,
            tp_str=tp_str,
            threshold=threshold,
        ):
            return
        self._draw_grouped_bar_mode(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            active_rsets=active_rsets,
            target_t=target_t,
            tp_str=tp_str,
            threshold=threshold,
            band_lbl=band_lbl,
            use_sem=use_sem,
        )
        from well_viewer.figure_export_editor import apply_export_style_to_current

        apply_export_style_to_current(self, self._bar_fig, getattr(self, "_bar_canvas", None))

    def _selected_bar_wells(self, active_rsets: "List[ReplicateSet]") -> List[str]:
        if active_rsets:
            return []
        return sorted(
            (lbl for lbl in self._selected_wells if lbl in self._well_paths),
            key=lambda lbl: self._parse_rc(lbl),
        )

    def _draw_bar_empty_state(self, ax_mean, ax_frac, message: str) -> None:
        for ax in (ax_mean, ax_frac):
            ax.text(
                0.5,
                0.5,
                message,
                transform=ax.transAxes,
                ha="center",
                va="center",
                color=TXT_MUT,
                fontsize=10,
            )
            ax.set_axis_off()
        self._bar_canvas.draw_idle()

    def _resolve_bar_timepoint(self) -> Optional[tuple[float, str]]:
        tp_str = self._bar_tp_var.get()
        if tp_str in ("—", ""):
            return None
        try:
            return float(tp_str), tp_str
        except ValueError:
            return None

    def _draw_per_cell_bar_mode(
        self,
        *,
        ax_mean,
        ax_frac,
        active_rsets: "List[ReplicateSet]",
        target_t: float,
        tp_str: str,
        threshold: float,
    ) -> bool:
        use_per_cell = self._bar_violin.get() or self._bar_swarm.get()
        if not use_per_cell:
            return False
        ordered_keys = self._bar_current_keys()
        if active_rsets:
            rset_by_name = {r.name: r for r in active_rsets}
            all_set_idx = {r.name: i for i, r in enumerate(getattr(self, "_rep_sets", []))}
            plot_wells: List[str] = []
            plot_colors: List[str] = []
            plot_labels: List[str] = []
            for si, key in enumerate(ordered_keys):
                rset = rset_by_name.get(key)
                if rset is None:
                    continue
                color_idx = all_set_idx.get(key, si)
                color = WELL_COLORS[color_idx % len(WELL_COLORS)]
                valid = [w for w in rset.wells if w in self._well_paths]
                for w in valid:
                    plot_wells.append(w)
                    plot_colors.append(color)
                    plot_labels.append(f"{self._well_display_label(w)}\n[{rset.name}]")
        else:
            plot_wells = [k for k in ordered_keys if k in self._well_paths]
            plot_colors = [WELL_COLORS[i % len(WELL_COLORS)] for i in range(len(plot_wells))]
            plot_labels = [self._well_display_label(w) for w in plot_wells]
        if _debug_flags.review_bar_debug_enabled():
            mode = "violin" if self._bar_violin.get() else "beeswarm"
            print(f"DEBUG runtime_app: per-cell mode={mode} wells={plot_wells!r} labels={plot_labels!r}")
        if plot_wells:
            if self._bar_violin.get():
                self._draw_violin(ax_mean, ax_frac, plot_wells, plot_colors, plot_labels, target_t, tp_str, threshold)
            else:
                self._draw_beeswarm(
                    ax_mean,
                    ax_frac,
                    plot_wells,
                    plot_colors,
                    plot_labels,
                    target_t,
                    tp_str,
                    threshold,
                    log_scale=self._bar_log_scale.get(),
                )
            self._apply_bar_ylims(
                ax_mean,
                ax_frac,
                log_scale=self._bar_log_scale.get() and self._bar_swarm.get(),
            )
        self._bar_canvas.draw_idle()
        return True

    def _draw_grouped_bar_mode(
        self,
        *,
        ax_mean,
        ax_frac,
        active_rsets: "List[ReplicateSet]",
        target_t: float,
        tp_str: str,
        threshold: float,
        band_lbl: str,
        use_sem: bool,
    ) -> None:
        use_groups, items, _ = self._collect_bar_items(target_t)
        if use_groups:
            by_key = {r.name: r for r in active_rsets}
            all_set_idx = {r.name: i for i, r in enumerate(getattr(self, "_rep_sets", []))}
            color_by_key = {
                r.name: WELL_COLORS[all_set_idx.get(r.name, i) % len(WELL_COLORS)]
                for i, r in enumerate(active_rsets)
            }
            ordered = []
            for key in self._bar_current_keys():
                rset = by_key.get(key)
                if not rset:
                    continue
                gm, g_err_m, gf, g_err_f = self._compute_rep_stats(rset, target_t, threshold, use_sem)
                base_lbl = self._replicate_display_label(rset)
                display = base_lbl
                ordered.append(
                    (
                        rset.name,
                        display,
                        gm,
                        g_err_m,
                        gf,
                        g_err_f,
                        not math.isnan(gm),
                        color_by_key.get(rset.name, WELL_COLORS[0]),
                    )
                )
            xlabels = [display for _, display, *_ in ordered]
            draw_items = ordered
        else:
            key_to_item = {lbl: (lbl, m, s, f, has) for lbl, m, s, f, has in items}
            ordered_keys = [k for k in self._bar_current_keys() if k in key_to_item]
            draw_items = [key_to_item[k] for k in ordered_keys]
            xlabels = [self._bar_well_display_label(lbl) for lbl, *_ in draw_items]

        _bar_render_items(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            use_groups=use_groups,
            items=draw_items,
            xlabels=xlabels,
            threshold=threshold,
            well_colors=WELL_COLORS,
            warn_color=WARN,
            border_color=BORDER,
            placeholder_color=CLR_PLACEHOLDER,
            disabled_well_color=CLR_DISABLED_WELL,
            err_bar_color=CLR_ERR_BAR,
        )
        ax_frac.set_ylabel("Fraction", fontsize=8, labelpad=5)
        _ch = self._active_channel.upper()
        ax_mean.set_title(
            f"Mean {_ch} (above threshold) ± {band_lbl}  —  t = {tp_str} h",
            color=TXT_PRI,
            fontsize=9,
            fontweight="bold",
            pad=6,
        )
        ax_frac.set_title(
            f"Fraction above threshold  —  t = {tp_str} h",
            color=TXT_PRI,
            fontsize=9,
            fontweight="bold",
            pad=6,
        )
        self._apply_bar_ylims(ax_mean, ax_frac, log_scale=False)
        self._bar_canvas.draw_idle()

    # ── Bar plot export ───────────────────────────────────────────────────────

    def _well_display_label(self, lbl: str) -> str:
        """Return the custom display label for *lbl* if defined, else its token."""
        tok = _extract_well_token(lbl) or lbl
        return self._well_labels.get(tok, tok)

    def _bar_well_display_label(self, lbl: str) -> str:
        """Bar-plot-safe well label that avoids numeric-only tick text."""
        disp = str(self._well_display_label(lbl))
        if re.match(r"^\s*\d+\s*$", disp):
            return _extract_well_token(lbl) or disp
        return disp

    def _replicate_display_label(self, rset: "ReplicateSet") -> str:
        """Human-friendly x-axis label for a replicate set.

        If the replicate set name appears auto-generated (e.g. ``"1"``,
        ``"Replicate 2"``, ``"R3"``), use member well labels so the x-axis
        remains interpretable.
        """
        name = str(getattr(rset, "name", "") or "").strip()
        if not name:
            name = "Replicate"

        generic_name = bool(
            re.match(
                r"^(?:\d+|r\s*\d+|rep(?:licate)?\s*\d+|group\s*\d+|set\s*\d+|batch\s*\d+)$",
                name,
                re.I,
            )
        )
        if not generic_name:
            return name

        wells = [self._well_display_label(w) for w in rset.wells if w in self._well_paths]
        if not wells:
            return name
        if len(wells) <= 3:
            return ",".join(wells)
        return f"{','.join(wells[:3])} +{len(wells)-3}"

    def _rep_sets_loaded(self) -> "List[ReplicateSet]":
        """All ReplicateSets that have at least one loaded well (ignores hidden)."""
        return [r for r in getattr(self, "_rep_sets", [])
                if any(w in self._well_paths for w in r.wells)]

    def _groups_from_rep_sets(self) -> "List[BarGroup]":
        """Mirror of BatchExportPanel._groups_from_rep_sets for app-level callers.

        Returns one BarGroup per loaded ReplicateSet when any are defined,
        otherwise a deep copy of the existing _bar_groups.
        """
        loaded = self._rep_sets_loaded()
        if loaded:
            groups: "List[BarGroup]" = []
            for rset in loaded:
                grp = BarGroup(rset.name)
                grp.members.append(rset)
                groups.append(grp)
            return groups
        return copy.deepcopy(self._bar_groups)

    def _rep_sets_active(self) -> "List[ReplicateSet]":
        """Loaded ReplicateSets that are not hidden — these appear on plots."""
        return [r for i, r in enumerate(self._rep_sets_loaded())
                if i not in self._rep_hidden]

    def _compute_rep_stats(
        self,
        rset: "ReplicateSet",
        target_t: float,
        threshold: float,
        use_sem: bool,
    ) -> tuple:
        """
        Mean fluor ± SD/SEM for a single ReplicateSet at *target_t*.

        Statistics are computed across the loaded wells of the set.
        Each well contributes one mean-fluor value; SD/SEM is across those values.
        Results are cached in _stats_cache.
        """
        if not hasattr(self, "_stats_cache"):
            self._stats_cache = {}
        cell_area_threshold = self._get_cell_area_threshold()
        fluor_gates = self._get_all_fluor_gates()
        cache_key = ("rep", rset.name, tuple(rset.wells), target_t, threshold, use_sem,
                      self._active_val_col, cell_area_threshold, tuple(sorted(fluor_gates.items())))
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        well_means: List[float] = []
        well_fracs: List[float] = []
        for lbl in rset.wells:
            if lbl not in self._well_paths:
                continue
            rows = self._get_rows(lbl)
            pts  = aggregate_with_threshold(rows, threshold, use_sem=False,
                                            val_col=self._active_val_col,
                                            cell_area_threshold=cell_area_threshold,
                                            fluor_gates=fluor_gates)
            matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
            if matched:
                _, m, _sd, f, *_ = matched[0]
                if not math.isnan(m): well_means.append(m)
                if not math.isnan(f): well_fracs.append(f)

        if well_means:
            gm  = statistics.mean(well_means)
            n   = len(well_means)
            gsd = statistics.pstdev(well_means) if n > 1 else 0.0
            gerr = gsd / math.sqrt(n) if (use_sem and n > 1) else gsd
        else:
            gm, gerr = float("nan"), 0.0

        if well_fracs:
            gf  = statistics.mean(well_fracs)
            nf  = len(well_fracs)
            fsd = statistics.pstdev(well_fracs) if nf > 1 else 0.0
            ferr = fsd / math.sqrt(nf) if (use_sem and nf > 1) else fsd
        else:
            gf, ferr = float("nan"), 0.0

        result = (gm, gerr, gf, ferr)
        self._stats_cache[cache_key] = result
        return result

    def _invalidate_stats_cache(self) -> None:
        """Discard cached group statistics. Call whenever group definitions change."""
        self._stats_cache: dict = {}

    def _compute_group_stats(
        self,
        grp: "BarGroup",
        target_t: float,
        threshold: float,
        use_sem: bool,
    ) -> tuple:
        """
        Compute mean ± error for a group at *target_t*, respecting replicate sets.

        Results are cached keyed by (group_name, wells_tuple, target_t, threshold,
        use_sem) so repeated calls during the same redraw are free.  The cache is
        cleared by _invalidate_stats_cache() whenever group definitions change.
        """
        if not hasattr(self, "_stats_cache"):
            self._stats_cache = {}
        cell_area_threshold = self._get_cell_area_threshold()
        fluor_gates = self._get_all_fluor_gates()
        cache_key = (grp.name, tuple(grp.wells), target_t, threshold, use_sem,
                      self._active_val_col, cell_area_threshold, tuple(sorted(fluor_gates.items())))
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        rep_means: List[float] = []
        rep_fracs: List[float] = []

        for rset in grp.replicate_sets():
            set_means: List[float] = []
            set_fracs: List[float] = []
            for lbl in rset:
                if lbl not in self._well_paths:
                    continue
                rows = self._get_rows(lbl)
                pts  = aggregate_with_threshold(rows, threshold, use_sem=False,
                                                val_col=self._active_val_col,
                                                cell_area_threshold=cell_area_threshold,
                                                fluor_gates=fluor_gates)
                matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
                if matched:
                    _, m, _sd, f, *_ = matched[0]
                    if not math.isnan(m): set_means.append(m)
                    if not math.isnan(f): set_fracs.append(f)
            if set_means:
                rep_means.append(statistics.mean(set_means))
            if set_fracs:
                rep_fracs.append(statistics.mean(set_fracs))

        if rep_means:
            gm   = statistics.mean(rep_means)
            n_m  = len(rep_means)
            g_sd = statistics.pstdev(rep_means) if n_m > 1 else 0.0
            g_err_m = g_sd / math.sqrt(n_m) if (use_sem and n_m > 1) else g_sd
        else:
            gm, g_err_m = float("nan"), 0.0

        if rep_fracs:
            gf   = statistics.mean(rep_fracs)
            n_f  = len(rep_fracs)
            f_sd = statistics.pstdev(rep_fracs) if n_f > 1 else 0.0
            g_err_f = f_sd / math.sqrt(n_f) if (use_sem and n_f > 1) else f_sd
        else:
            gf, g_err_f = float("nan"), 0.0

        result = (gm, g_err_m, gf, g_err_f)
        self._stats_cache[cache_key] = result
        return result

    def _collect_bar_items(self, target_t: float) -> tuple:
        """
        Return (use_groups, bar_items_or_well_data, band_lbl) for *target_t*.

        Mirrors the computation in _redraw_bars so that export and on-screen
        rendering always produce identical numbers.

        Returns
        -------
        use_groups : bool
        items      : list
            Grouped mode  → list of (name, mean, err_mean, frac, err_frac, has, color)
            Per-well mode → list of (label, mean, spread, frac, has)
        band_lbl   : str
        """
        return _bar_collect_items(
            self,
            target_t,
            aggregate_with_threshold=aggregate_with_threshold,
            well_colors=WELL_COLORS,
        )

    def _render_bar_figure(self, target_t: float, tp_str: str) -> "Figure":
        """
        Render a standalone bar figure for *target_t* (not embedded in the UI).
        Mirrors _redraw_bars drawing logic onto an off-screen Figure.
        """
        from matplotlib.figure import Figure as _Figure

        use_sem   = self._use_sem.get()
        band_lbl  = "SEM" if use_sem else "SD"
        threshold = self._get_thresh_frac_on(self._active_channel)

        fig = _Figure(figsize=(8, 7), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(2, 1, 1)
        ax_frac = fig.add_subplot(2, 1, 2)
        fig.subplots_adjust(hspace=0.55, top=0.92, bottom=0.12, left=0.13, right=0.97)

        _ch = self._active_channel.upper()
        apply_ax_style(ax_mean, f"Mean {_ch} (above threshold) ± {band_lbl}  —  t = {tp_str} h",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac, f"Fraction above threshold  —  t = {tp_str} h", "Fraction")
        ax_frac.set_ylim(-0.05, 1.05)

        use_groups, items, _ = self._collect_bar_items(target_t)
        if use_groups:
            rep_by_name = {r.name: r for r in self._rep_sets_active()}
            xlabels = [self._replicate_display_label(rep_by_name[name]) if name in rep_by_name else name for name, *_ in items]
            draw_items = [
                (name, xlbl, gm, g_err_m, gf, g_err_f, has, color)
                for (name, gm, g_err_m, gf, g_err_f, has, color), xlbl in zip(items, xlabels)
            ]
        else:
            draw_items = items
            xlabels = [self._bar_well_display_label(lbl) for lbl, *_ in items]

        _bar_render_items(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            use_groups=use_groups,
            items=draw_items,
            xlabels=xlabels,
            threshold=threshold,
            well_colors=WELL_COLORS,
            warn_color=WARN,
            border_color=BORDER,
            placeholder_color=CLR_PLACEHOLDER,
            disabled_well_color=CLR_DISABLED_WELL,
            err_bar_color=CLR_ERR_BAR,
        )
        return fig

    def _export_bar_plot_data(self) -> None:
        from well_viewer.export_service import export_bar_plot_data as _export_bar_plot_data

        _export_bar_plot_data(self)

    def _open_bar_batch_export(self) -> None:
        """Switch Batch Export tab to the inline bar-plot export builder."""
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Bar Batch Export.")
            return
        if hasattr(self, "_notebook") and hasattr(self._notebook, "select_by_text"):
            self._notebook.select_by_text("Batch Export")
        if hasattr(self, "_batch_export_set_mode"):
            self._batch_export_set_mode("bar")

    def _open_scatter_cells_batch_export(self) -> None:
        """Switch Batch Export tab to the inline scatter-cells export builder."""
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Scatter Cells Batch Export.")
            return
        if hasattr(self, "_notebook") and hasattr(self._notebook, "select_by_text"):
            self._notebook.select_by_text("Batch Export")
        if hasattr(self, "_batch_export_set_mode"):
            self._batch_export_set_mode("scatter_cells")

    def _open_scatter_agg_batch_export(self) -> None:
        """Switch Batch Export tab to the inline aggregate-scatter export builder."""
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Scatter Aggregate Batch Export.")
            return
        if hasattr(self, "_notebook") and hasattr(self._notebook, "select_by_text"):
            self._notebook.select_by_text("Batch Export")
        if hasattr(self, "_batch_export_set_mode"):
            self._batch_export_set_mode("scatter_agg")

    # ── Save current figure ───────────────────────────────────────────────────

    _FIG_FILETYPES = [
        ("PNG image",        "*.png"),
        ("SVG vector",       "*.svg"),
        ("PDF document",     "*.pdf"),
        ("EPS vector",       "*.eps"),
        ("All files",        "*.*"),
    ]

    def _save_matplotlib_fig(self, fig: "Figure", default_name: str) -> None:
        """Show a save-file dialog and write *fig* to disk."""
        _plot_save_matplotlib_fig_orchestrator(
            self,
            fig,
            default_name,
            plot_bg=PLOT_BG,
        )

    def _save_line_figure(self) -> None:
        """Save the current Line Graphs figure at high resolution."""
        _plot_save_line_figure_orchestrator(self, plot_bg=PLOT_BG)

    def _save_bar_figure(self) -> None:
        """Save the current Bar Plots figure at high resolution."""
        _plot_save_bar_figure_orchestrator(self, plot_bg=PLOT_BG)

    def _open_export_style_panel(self, plot_key: str) -> None:
        """Open the reusable export-style sidebar for a specific plot."""
        from well_viewer.figure_export_editor import launch_export_editor

        mapping = {
            "line": (getattr(self, "_line_fig", None), getattr(self, "_line_canvas", None), "line_graphs.png"),
            "bar": (getattr(self, "_bar_fig", None), getattr(self, "_bar_canvas", None), "bar_plots.png"),
            "scatter_cells": (getattr(self, "_scatter_fig", None), getattr(self, "_scatter_canvas", None), "scatter_cells.png"),
            "scatter_agg": (getattr(self, "_scatter_agg_fig", None), getattr(self, "_scatter_agg_canvas", None), "scatter_agg.png"),
        }
        fig, canvas, default_name = mapping.get(plot_key, (None, None, "figure.png"))
        if fig is None:
            self._set_status("Export style panel unavailable for this figure.")
            return
        session = launch_export_editor(self, fig, default_name, plot_bg=PLOT_BG, canvas=canvas)
        if session is not None:
            self._set_status("Export style panel opened.")

    # ── Scatter Plot tab ───────────────────────────────────────────────────────

    def _col_for_scatter_entry(self, entry: str) -> str:
        """Map scatter dropdown entry to CSV column name.

        "gfp" -> "gfp_mean_intensity"
        "gfp (spots)" -> "gfp_smfish_count"
        """
        if entry.endswith(" (spots)"):
            ch = entry[:-8]  # Remove " (spots)"
            return f"{ch}_smfish_count"
        else:
            return f"{entry}_mean_intensity"

    def _update_scatter_menus(self) -> None:
        """Populate scatter plot dropdowns with available channels and timepoints."""
        # Update channel dropdowns for cells scatter (include smfish_count variants)
        channels = list(self._fluor_channels) if self._fluor_channels else ["gfp"]
        scatter_ch_options = []
        for ch in channels:
            scatter_ch_options.append(ch)
            if ch in self._smfish_channels:
                scatter_ch_options.append(f"{ch} (spots)")

        _set_combo_values(self._scatter_ch_x_cb, scatter_ch_options)
        _set_combo_values(self._scatter_ch_y_cb, scatter_ch_options)

        if scatter_ch_options:
            if self._scatter_ch_x_var.get() not in scatter_ch_options:
                self._scatter_ch_x_var.set(scatter_ch_options[0])
            if self._scatter_ch_y_var.get() not in scatter_ch_options:
                self._scatter_ch_y_var.set(scatter_ch_options[0 if len(scatter_ch_options) == 1 else 1])

        # Update timepoint dropdown for cells scatter
        timepoints = list(self._all_timepoints_cache) or _scatter_get_timepoints(self)
        tp_strs = [f"{tp:.1f}" for tp in timepoints] if timepoints else ["0"]
        _set_combo_values(self._scatter_tp_cb, tp_strs)

        if tp_strs and self._scatter_tp_var.get() not in tp_strs:
            self._scatter_tp_var.set(tp_strs[0])

        # Update statistic dropdowns for aggregate scatter
        # Build list of available statistics: Mean Fluorescence, Fraction On, and smFISH Count for each channel
        statistics = []
        for ch in channels:
            statistics.append(f"Mean Fluorescence {ch.upper()}")
            statistics.append(f"Fraction On {ch.upper()}")
            if ch in self._smfish_channels:
                statistics.append(f"smFISH Count {ch.upper()}")

        _set_combo_values(self._scatter_agg_stat_x_cb, statistics)
        _set_combo_values(self._scatter_agg_stat_y_cb, statistics)

        if statistics:
            if self._scatter_agg_stat_x_var.get() not in statistics:
                self._scatter_agg_stat_x_var.set(statistics[0])
            if self._scatter_agg_stat_y_var.get() not in statistics:
                self._scatter_agg_stat_y_var.set(statistics[1] if len(statistics) > 1 else statistics[0])

        # Update timepoint selections for aggregate scatter; all default checked.
        from well_viewer.tabs.scatter_agg_tab_view import BoolHolder as _BoolHolder
        if hasattr(self, '_scatter_agg_tp_selections'):
            prev_selected = {tp_str for tp_str, v in self._scatter_agg_tp_selections.items() if v.get()}
            self._scatter_agg_tp_selections.clear()
        else:
            prev_selected = set()
            self._scatter_agg_tp_selections = {}

        for tp_str in tp_strs:
            self._scatter_agg_tp_selections[tp_str] = _BoolHolder(True)

        self._update_tp_selection_display()

    def _update_tp_selection_display(self) -> None:
        """Update the aggregate scatter label showing selected timepoints."""
        count = sum(1 for v in self._scatter_agg_tp_selections.values() if v.get())
        total = len(self._scatter_agg_tp_selections)
        label_text = f"(All {count} selected)" if count == total else f"({count}/{total} selected)"
        if hasattr(self, "_scatter_agg_tp_label") and self._scatter_agg_tp_label is not None:
            self._scatter_agg_tp_label.setText(label_text)

    def _redraw_scatter(self) -> None:
        """Redraw the scatter plot with current selections."""
        try:
            ch_x_entry = self._scatter_ch_x_var.get()
            ch_y_entry = self._scatter_ch_y_var.get()
            tp_str = self._scatter_tp_var.get()
            timepoint_h = float(tp_str) if tp_str else 0.0
        except ValueError:
            return

        # Extract base channel names (e.g., "gfp (spots)" -> "gfp")
        ch_x_base = ch_x_entry.split(" ")[0]
        ch_y_base = ch_y_entry.split(" ")[0]

        cell_area_threshold = self._get_cell_area_threshold()
        fluor_gate_x = self._get_fluor_gate(ch_x_base)
        fluor_gate_y = self._get_fluor_gate(ch_y_base)

        # Resolve to actual column names
        col_x = self._col_for_scatter_entry(ch_x_entry)
        col_y = self._col_for_scatter_entry(ch_y_entry)

        _scatter_redraw(
            self,
            col_x,
            col_y,
            timepoint_h,
            well_colors=WELL_COLORS,
            cell_area_threshold=cell_area_threshold,
            fluor_gate_x=fluor_gate_x,
            fluor_gate_y=fluor_gate_y,
        )
        from well_viewer.figure_export_editor import apply_export_style_to_current

        apply_export_style_to_current(self, self._scatter_fig, getattr(self, "_scatter_canvas", None))

    def _on_scatter_click(self, event) -> None:
        """Handle click events on scatter plot datapoints."""
        if event.inaxes is not self._ax_scatter or event.xdata is None or event.ydata is None:
            return

        if event.button != 1:  # Only respond to left clicks
            return

        try:
            interaction_cache = getattr(self, "_scatter_interaction_cache", None) or {}
            points = interaction_cache.get("points", [])
            if not points:
                return

            # Find nearest point to click
            min_dist = float('inf')
            nearest_well = None
            nearest_filename = None
            nearest_nuclear_id = None
            nearest_row_idx = None

            for x, y, meta in points:
                dx = x - event.xdata
                dy = y - event.ydata
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_well, nearest_filename, nearest_nuclear_id, nearest_row_idx = meta

            if nearest_well is not None:
                self._open_scatter_cell_viewer(nearest_well, nearest_filename, nearest_nuclear_id, nearest_row_idx)

        except Exception as e:
            self._set_status(f"Error handling scatter click: {e}")

    def _on_scatter_motion(self, event) -> None:
        """Handle hover events on scatter plot to show tooltips."""
        if event.inaxes is not self._ax_scatter or event.xdata is None or event.ydata is None:
            return

        try:
            interaction_cache = getattr(self, "_scatter_interaction_cache", None) or {}
            points = interaction_cache.get("points", [])
            if not points:
                return

            # Find nearest point to cursor
            min_dist = float('inf')
            nearest_info = None
            threshold = 0.5  # Distance threshold for tooltip

            for x, y, meta in points:
                dx = x - event.xdata
                dy = y - event.ydata
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_info = meta

            if min_dist < threshold and nearest_info:
                well_label, filename, nuclear_id, row_idx = nearest_info
                tooltip_text = f"File: {filename} | Nuclear ID: {nuclear_id}"
                self._set_status(tooltip_text)
            else:
                self._set_status("")

        except Exception as e:
            pass  # Silently ignore hover errors

    def _open_scatter_cell_viewer(
        self,
        well_label: str,
        filename: str,
        nuclear_id: str,
        row_idx: int,
    ) -> None:
        """Open or update the scatter cell viewer window."""
        from well_viewer.scatter_callbacks import ScatterCellViewer

        existing = getattr(self, "_scatter_cell_viewer", None)
        if existing is None or not existing.isVisible():
            self._scatter_cell_viewer = ScatterCellViewer(
                self,
                self,
                well_label,
                filename,
                nuclear_id,
                row_idx,
            )
            self._scatter_cell_viewer.show()
        else:
            existing.update_cell(well_label, filename, nuclear_id, row_idx)
            existing.raise_()
            existing.activateWindow()

    def _export_scatter_data(self) -> None:
        """Export scatter plot data to CSV."""
        from well_viewer.export_service import export_scatter_data as _export_scatter_data

        _export_scatter_data(self)

    def _save_scatter_figure(self) -> None:
        """Save the current Scatter plot figure at high resolution."""
        from well_viewer.plot_orchestrator import save_scatter_figure as _plot_save_scatter_figure_orchestrator

        _plot_save_scatter_figure_orchestrator(self, plot_bg=PLOT_BG)

    def _redraw_scatter_agg(self) -> None:
        """Redraw the aggregate scatter plot with current selections."""
        try:
            stat_x = self._scatter_agg_stat_x_var.get()
            stat_y = self._scatter_agg_stat_y_var.get()

            # Get selected timepoints from BooleanVars
            if not hasattr(self, '_scatter_agg_tp_selections') or not self._scatter_agg_tp_selections:
                # Clear the plot if no timepoints defined
                self._ax_scatter_agg.clear()
                self._ax_scatter_agg.text(
                    0.5, 0.5,
                    "No timepoints available.",
                    ha='center', va='center',
                    transform=self._ax_scatter_agg.transAxes,
                    fontsize=10,
                    color='gray'
                )
                self._scatter_agg_canvas.draw()
                return

            selected_timepoints = []
            for tp_str, var in self._scatter_agg_tp_selections.items():
                if var.get():
                    try:
                        selected_timepoints.append(float(tp_str))
                    except ValueError:
                        pass

            if not selected_timepoints:
                # Clear the plot if no timepoints selected
                self._ax_scatter_agg.clear()
                self._ax_scatter_agg.text(
                    0.5, 0.5,
                    "Please select timepoints to plot.",
                    ha='center', va='center',
                    transform=self._ax_scatter_agg.transAxes,
                    fontsize=10,
                    color='gray'
                )
                self._scatter_agg_canvas.draw()
                return

        except (ValueError, AttributeError):
            return

        from well_viewer.scatter_controller import redraw_scatter_agg as _scatter_redraw_agg

        _scatter_redraw_agg(
            self,
            stat_x,
            stat_y,
            selected_timepoints,
            well_colors=WELL_COLORS,
            aggregate_with_threshold=aggregate_with_threshold,
        )
        from well_viewer.figure_export_editor import apply_export_style_to_current

        apply_export_style_to_current(self, self._scatter_agg_fig, getattr(self, "_scatter_agg_canvas", None))

    def _export_scatter_agg_data(self) -> None:
        """Export aggregate scatter plot data to CSV."""
        from well_viewer.export_service import export_scatter_agg_data as _export_scatter_agg_data

        _export_scatter_agg_data(self)

    def _save_scatter_agg_figure(self) -> None:
        """Save the current aggregate scatter plot figure at high resolution."""
        from well_viewer.plot_orchestrator import save_scatter_agg_figure as _plot_save_scatter_agg_figure_orchestrator

        _plot_save_scatter_agg_figure_orchestrator(self, plot_bg=PLOT_BG)

    def _save_montage_figure(self) -> None:
        from well_viewer.export_service import save_montage_figure as _save_montage_figure

        _save_montage_figure(self)

    # ── Legend interaction ────────────────────────────────────────────────────

    def _on_fig_click(self, event) -> None:
        """
        Left-click on the CDF axes near the threshold line → start drag.
        Right-click on any axes → toggle that axes' legend.
        """
        if event.inaxes is None:
            return

        # ── Left-click: start threshold drag if near the vline ───────────────
        if event.button == 1 and event.inaxes is self._line_ax_cdf:
            # Accept if click is within 5% of the CDF x-range of the threshold
            try:
                lo, hi = self._line_ax_cdf.get_xlim()
                tol = (hi - lo) * 0.05
            except Exception:
                tol = 5.0
            if abs(event.xdata - self._threshold) <= tol:
                self._thr_dragging = True
                self._set_status("Dragging threshold — release to set")
                return   # don't fall through to legend toggle

        # ── Right-click: toggle legend ────────────────────────────────────────
        if event.button != 3:
            return
        ax_map = {
            id(self._line_ax_mean): "mean",
            id(self._line_ax_frac): "frac",
            id(self._line_ax_cdf):  "cdf",
        }
        clicked_ax = event.inaxes
        key = ax_map.get(id(clicked_ax))
        if key is None:
            return
        self._legend_visible[key] = not self._legend_visible[key]
        leg = clicked_ax.get_legend()
        if leg is not None:
            leg.set_visible(self._legend_visible[key])
            self._line_canvas.draw_idle()
        state = "shown" if self._legend_visible[key] else "hidden"
        self._set_status(f"Legend for '{key}' plot {state}  (right-click to toggle)")

    def _on_cdf_motion(self, event) -> None:
        """Move the threshold line live while dragging."""
        if not self._thr_dragging:
            return
        if event.inaxes is not self._line_ax_cdf or event.xdata is None:
            return
        # Clamp to visible CDF range
        try:
            lo, hi = self._line_ax_cdf.get_xlim()
        except Exception:
            lo, hi = 0.0, 300.0
        new_thr = max(lo, min(hi, event.xdata))
        self._threshold = new_thr
        self._invalidate_stats_cache()
        # Lightweight redraw: just update the vline and axvspan positions
        self._redraw()

    def _on_cdf_release(self, event) -> None:
        """Finalise the threshold drag on mouse release."""
        if not self._thr_dragging:
            return
        self._thr_dragging = False
        # Threshold is now managed by the Cell Gating tab, not by CDF dragging

    # ── Log / status helpers ──────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self._status_lbl.setText(msg)

    def _show_progress(self, maximum: int, msg: str = "") -> None:
        """Display the progress bar and set its maximum value."""
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(max(1, maximum))
        self._progress_bar.setVisible(True)
        if msg:
            self._set_status(msg)
        QApplication.processEvents()

    def _step_progress(self, value: int, msg: str = "") -> None:
        """Advance the progress bar to *value* and repaint immediately."""
        self._progress_bar.setValue(value)
        if msg:
            self._set_status(msg)
        QApplication.processEvents()

    def _hide_progress(self) -> None:
        """Remove the progress bar."""
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)

    def _toggle_log(self) -> None:
        self._log_visible = not self._log_visible
        if self._log_visible:
            self._log_frame.setVisible(True)
            self._log_btn.setText("Log ▼")
        else:
            self._log_frame.setVisible(False)
            self._log_btn.setText("Log ▲")

    def _clear_log(self) -> None:
        if hasattr(self, "_log_text") and self._log_text is not None:
            self._log_text.clear()

# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(description="Well Viewer",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--data_dir", type=Path, default=None,
                    help="Directory of per-well CSVs, or a .zip / .tar.gz archive.")
    args = ap.parse_args()
    qapp = QApplication.instance() or QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("Well Viewer")
    app = WellViewerApp(data_path=args.data_dir)
    win.setCentralWidget(app)
    win.resize(1400, 900)
    win.show()
    qapp.exec()


__all__ = ["WellViewerApp", "BarGroup", "ReplicateSet", "main"]


if __name__ == "__main__":
    main()
