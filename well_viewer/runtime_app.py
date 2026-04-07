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
import tkinter as tk
import threading
import zipfile
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from well_viewer.batch_models import BarGroup, ReplicateSet
from well_viewer.state import groups_with_loaded_wells as _groups_with_loaded_wells
from well_viewer.state import selected_listbox_values as _selected_listbox_values
from well_viewer.barplot_controller import bar_groups_from_data as _bar_groups_from_data
from well_viewer.barplot_controller import bar_groups_to_dict as _bar_groups_to_dict
from well_viewer.barplot_controller import apply_bar_ylims as _bar_apply_ylims
from well_viewer.barplot_controller import collect_bar_items as _bar_collect_items
from well_viewer.barplot_controller import ordered_bar_keys as _bar_ordered_keys
from well_viewer.barplot_controller import render_bar_items as _bar_render_items
from well_viewer.preview_controller import classify_member as _preview_classify_member
from well_viewer.preview_controller import open_imgref_as_array as _preview_open_imgref_as_array
from well_viewer.preview_controller import read_member_bytes as _preview_read_member_bytes
from well_viewer.preview_controller import scan_zip_members as _preview_scan_zip_members
from well_viewer.preview_view import build_preview_picker as _build_preview_picker_view
from well_viewer.preview_view import preview_pick_well as _preview_pick_well_view
from well_viewer.preview_view import refresh_preview_picker as _refresh_preview_picker_view
from well_viewer.lineplot_controller import redraw_line_plots as _lineplot_redraw
from well_viewer.scatter_controller import get_all_timepoints as _scatter_get_timepoints
from well_viewer.scatter_controller import collect_scatter_data as _scatter_collect_data
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
from well_viewer.montage_controller import on_montage_wheel as _on_montage_wheel_controller
from well_viewer.stats_controller import collect_group_values as _stats_collect_group_values
from well_viewer.stats_controller import draw_ks_cdf as _stats_draw_ks_cdf
from well_viewer.stats_controller import run_stats as _stats_run_controller
from well_viewer.stats_view import build_stats_group_editor as _build_stats_group_editor_view
from well_viewer.stats_view import build_stats_results_panel as _build_stats_results_panel_view
from well_viewer.stats_view import build_stats_tab as _build_stats_tab_view
from well_viewer.state import make_schema_extractor as _make_schema_extractor
from well_viewer.state import read_pipeline_info as _read_pipeline_info_shared
from well_viewer.ui_support import (
    ask_name_dialog as _ui_ask_name_dialog,
    btn_card as _btn_card,
    btn_danger as _btn_danger,
    btn_primary as _btn_primary,
    btn_secondary as _btn_secondary,
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
    from PIL import Image as _PILImage, ImageTk as _PILImageTk
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


def make_scrollable_canvas(
    parent: tk.Widget,
    bg: str = BG_APP,
    scrollbar_width: int = 7,
) -> "tuple[tk.Canvas, tk.Frame]":
    """
    Create a vertically scrollable canvas inside *parent*.

    Returns (canvas, inner_frame).  The caller stores the canvas and inner_frame
    as instance attributes and populates inner_frame with child widgets.  The
    canvas scroll region is kept in sync automatically via a <Configure> binding
    on inner_frame.  The canvas width is propagated to inner_frame via a second
    <Configure> binding on the canvas itself, ensuring cards span the full width.

    Replaces 2 near-identical vsb + canvas + create_window + binding blocks.
    """
    return _ui_make_scrollable_canvas(
        parent,
        bg=bg,
        border=BORDER,
        trough_bg=BG_SIDE,
        scrollbar_width=scrollbar_width,
    )

# =============================================================================
# Shared UI helpers
# =============================================================================

def ask_name_dialog(parent: tk.Widget, title: str = "Name",
                    prompt: str = "Name:", default: str = "",
                    width: int = 24) -> Optional[str]:
    """
    Reusable modal text-input dialog.  Returns the entered string or None.

    Replaces the near-identical _ask_name (BatchExportDialog) and
    _ask_inline_name (WellViewerApp) methods.
    """
    return _ui_ask_name_dialog(
        parent,
        title=title,
        prompt=prompt,
        default=default,
        width=width,
        bg_app=BG_APP,
        txt_pri=TXT_PRI,
        txt_sec=TXT_SEC,
        accent=ACCENT,
        bg_panel=BG_PANEL,
        border=BORDER,
        bg_cell=BG_CELL,
        bg_hover=BG_HOVER,
        fm_ui=FM_UI,
        fm_bold=FM_BOLD,
        clr_white=CLR_WHITE,
    )


class WellLabel(tk.Label):
    """
    tk.Label subclass that emulates the tk.Button API used by all plate-map
    wells throughout the app.

    Motivation: on macOS, tk.Button uses native Aqua rendering and completely
    ignores the `bg` option — making all colour-coding invisible.  tk.Label
    respects `bg` on every platform.

    Emulated Button features:
      • state=NORMAL / DISABLED  — controls cursor and whether click/drag fire
      • activebackground         — applied on <Enter>, reversed on <Leave>
      • activeforeground         — applied on <Enter>, reversed on <Leave>
      • command                  — called on <Button-1> when not disabled
      • relief                   — passed straight through (Label supports it)

    All other kwargs are forwarded to tk.Label unchanged.
    The standard Tk drag event bindings (<ButtonPress-1>, <B1-Motion>,
    <ButtonRelease-1>) work identically on Labels, so no drag code changes.
    """

    def __init__(self, parent: tk.Widget, **kw):
        self._cmd          = kw.pop("command",           None)
        self._active_bg    = kw.pop("activebackground",  None)
        self._active_fg    = kw.pop("activeforeground",  None)
        state              = kw.pop("state",             tk.NORMAL)
        self._disabled     = (state == tk.DISABLED)
        self._normal_bg    = kw.get("bg",  "")
        self._normal_fg    = kw.get("fg",  "")
        super().__init__(parent, **kw)
        self._hover        = False
        self.bind("<Button-1>",      self._on_click)
        self.bind("<Enter>",         self._on_enter)
        self.bind("<Leave>",         self._on_leave)

    # ------------------------------------------------------------------
    def _on_click(self, _event) -> None:
        if not self._disabled and self._cmd:
            self._cmd()

    def _on_enter(self, _event) -> None:
        if self._disabled:
            return
        self._hover = True
        kw: dict = {}
        if self._active_bg:
            kw["bg"] = self._active_bg
        if self._active_fg:
            kw["fg"] = self._active_fg
        if kw:
            tk.Label.config(self, **kw)

    def _on_leave(self, _event) -> None:
        self._hover = False
        kw: dict = {}
        if self._active_bg:
            kw["bg"] = self._normal_bg
        if self._active_fg:
            kw["fg"] = self._normal_fg
        if kw:
            tk.Label.config(self, **kw)

    # ------------------------------------------------------------------
    def config(self, **kw) -> None:  # type: ignore[override]
        if "command" in kw:
            self._cmd = kw.pop("command")
        if "activebackground" in kw:
            self._active_bg = kw.pop("activebackground")
        if "activeforeground" in kw:
            self._active_fg = kw.pop("activeforeground")
        if "state" in kw:
            state = kw.pop("state")
            self._disabled = (state == tk.DISABLED)
            # Mirror cursor if not explicitly overridden
            if "cursor" not in kw:
                kw["cursor"] = "arrow" if self._disabled else "hand2"
        if "bg" in kw:
            self._normal_bg = kw["bg"]
            if self._hover and self._active_bg:
                pass   # leave hover colour in place; will revert on Leave
        if "fg" in kw:
            self._normal_fg = kw["fg"]
        # Store original activebackground if not already stored, for theme updates
        if not hasattr(self, "_active_bg_orig"):
            self._active_bg_orig = self._active_bg
        tk.Label.config(self, **kw)

    def update_theme_colors(self, color_map: dict) -> None:
        """Update cached colors based on color_map during theme changes.

        Args:
            color_map: Dictionary mapping old colors to new colors
        """
        # Update normal bg color if it's in the map
        if self._normal_bg in color_map:
            old_bg = self._normal_bg
            new_bg = color_map[old_bg]
            self._normal_bg = new_bg
            # Update display if not in hover state
            if not self._hover:
                tk.Label.config(self, bg=new_bg)
            # Otherwise it will be updated when _on_leave is called

        # Update normal fg color if it's in the map
        if self._normal_fg in color_map:
            old_fg = self._normal_fg
            new_fg = color_map[old_fg]
            self._normal_fg = new_fg
            # Update display if not in hover state
            if not self._hover:
                tk.Label.config(self, fg=new_fg)

        # Update active background color if it's in the map
        if self._active_bg and self._active_bg in color_map:
            self._active_bg = color_map[self._active_bg]

        # Update active foreground color if it's in the map
        if self._active_fg and self._active_fg in color_map:
            self._active_fg = color_map[self._active_fg]

    def update_theme_colors_rebuild(self, old_theme: str, new_theme: str) -> None:
        """Update cached colors using semantic theme rebuild approach.

        This handles the case where multiple colors share same hex value,
        causing dictionary collisions.

        Args:
            old_theme: Previous theme name ("Dark" or "Light")
            new_theme: New theme name ("Dark" or "Light")
        """
        from ui.theme import THEMES

        old_theme_dict = THEMES.get(old_theme, {})
        new_theme_dict = THEMES.get(new_theme, {})

        # Create reverse mapping for old theme: hex → color name
        old_hex_to_name = {v: k for k, v in old_theme_dict.items()}

        # Update normal background
        if self._normal_bg in old_hex_to_name:
            color_name = old_hex_to_name[self._normal_bg]
            new_bg = new_theme_dict.get(color_name)
            if new_bg:
                self._normal_bg = new_bg
                if not self._hover:
                    tk.Label.config(self, bg=new_bg)

        # Update normal foreground
        if self._normal_fg in old_hex_to_name:
            color_name = old_hex_to_name[self._normal_fg]
            new_fg = new_theme_dict.get(color_name)
            if new_fg:
                self._normal_fg = new_fg
                if not self._hover:
                    tk.Label.config(self, fg=new_fg)

        # Update active background
        if self._active_bg and self._active_bg in old_hex_to_name:
            color_name = old_hex_to_name[self._active_bg]
            new_active_bg = new_theme_dict.get(color_name)
            if new_active_bg:
                self._active_bg = new_active_bg

        # Update active foreground
        if self._active_fg and self._active_fg in old_hex_to_name:
            color_name = old_hex_to_name[self._active_fg]
            new_active_fg = new_theme_dict.get(color_name)
            if new_active_fg:
                self._active_fg = new_active_fg

    configure = config   # Tk alias


def build_plate_grid(
    parent: tk.Widget,
    btn_store: Dict[str, "WellLabel"],
    *,
    row_start: int = 1,
    font: tuple = None,
    btn_width: int = 0,
    btn_height: int = 1,
    col_header_row: int = 0,
) -> None:
    """
    Build an 8×12 plate-map header + WellLabel grid inside *parent*.

    WellLabel is used instead of tk.Button because macOS Aqua rendering
    ignores tk.Button background colours entirely.  WellLabel (a tk.Label
    subclass) respects bg on all platforms while emulating the Button API
    (state, activebackground, command) so all call sites are unchanged.
    """
    if font is None:
        font = FM_TINY
    # Column headers
    tk.Label(parent, text="", bg=BG_SIDE,
             font=font).grid(row=col_header_row, column=0)
    for ci, col in enumerate(_PLATE_COLS):
        tk.Label(parent, text=str(int(col)), font=font,
                 fg=TXT_MUT, bg=BG_SIDE,
                 ).grid(row=col_header_row, column=ci + 1)

    # Row labels + well cells
    for ri, row_ltr in enumerate(_PLATE_ROWS):
        tk.Label(parent, text=row_ltr, font=font,
                 fg=TXT_MUT, bg=BG_SIDE,
                 anchor="e").grid(row=ri + row_start, column=0, padx=(2, 1))
        for ci, col in enumerate(_PLATE_COLS):
            tok = f"{row_ltr}{col}"
            kw: dict = dict(font=font,
                            relief=tk.FLAT,
                            bg=BG_CELL, fg=TXT_MUT,
                            state=tk.DISABLED, cursor="arrow",
                            anchor="center", padx=1, pady=2)
            if btn_width:
                kw["width"] = btn_width
            lbl = WellLabel(parent, text=tok, **kw)
            lbl.grid(row=ri + row_start, column=ci + 1, padx=0, pady=1,
                     sticky="ew")
            btn_store[tok] = lbl

    # Row-label column fixed; well columns equal-width via uniform group.
    parent.columnconfigure(0, weight=0)
    for col_idx in range(1, len(_PLATE_COLS) + 1):
        parent.columnconfigure(col_idx, weight=1, uniform="well_col")


def make_fluor_thumb(arr, sz_w: int, sz_h: int,
                   lo: Optional[float], hi: Optional[float]):
    """
    Render a greyscale float32 array as a (sz_w × sz_h) PhotoImage.
    Applies LUT [lo, hi]; falls back to array min/max if None.
    Returns None if PIL or numpy is unavailable.
    """
    if arr is None or not _PIL_AVAILABLE or not _NP_AVAILABLE:
        return None
    arr = _np.asarray(arr, dtype=_np.float32)
    alo = lo if lo is not None else float(arr.min())
    ahi = hi if hi is not None else float(arr.max())
    if ahi <= alo:
        ahi = alo + 1.0
    disp = ((_np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255).astype(_np.uint8)
    img  = _PILImage.fromarray(disp, mode="L").convert("RGB")
    iw, ih = img.size
    scale  = min(sz_w / iw, sz_h / ih, 1.0)
    img    = img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))),
                        _PILImage.LANCZOS)
    return _PILImageTk.PhotoImage(img)


def make_overlay_thumb(arr, sz_w: int, sz_h: int):
    """
    Render a greyscale or RGB array as a (sz_w × sz_h) PhotoImage.
    Handles both 2-D (greyscale, auto-stretched) and 3-D (RGB/RGBA) arrays.
    Returns None if PIL or numpy is unavailable or the array is empty.
    """
    if arr is None or not _PIL_AVAILABLE or not _NP_AVAILABLE:
        return None
    arr = _np.asarray(arr)
    if arr.ndim == 2:
        arr_f = arr.astype(_np.float32)
        lo, hi = float(arr_f.min()), float(arr_f.max())
        if hi <= lo:
            hi = lo + 1.0
        disp = ((arr_f - lo) / (hi - lo) * 255).astype(_np.uint8)
        img  = _PILImage.fromarray(disp, mode="L").convert("RGB")
    elif arr.ndim == 3 and arr.shape[2] >= 3:
        a = arr[:, :, :3]
        if a.dtype != _np.uint8:
            rng = max(a.max() - a.min(), 1)
            a = ((a.astype(_np.float32) - a.min()) / rng * 255).astype(_np.uint8)
        img = _PILImage.fromarray(a, mode="RGB")
    else:
        return None
    iw, ih = img.size
    scale  = min(sz_w / iw, sz_h / ih, 1.0)
    img    = img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))),
                        _PILImage.LANCZOS)
    return _PILImageTk.PhotoImage(img)


def _bind_drag(frame: tk.Widget, btn_store: Dict[str, "tk.Button"],
               on_press, on_drag, on_release, *, button: int = 1) -> None:
    """
    Bind press/drag/release events for *button* on *frame* and every button
    in *btn_store*.  Centralises the six-line boilerplate that otherwise
    appears once per plate-map panel.
    """
    bp = f"<ButtonPress-{button}>"
    bm = f"<B{button}-Motion>"
    br = f"<ButtonRelease-{button}>"
    frame.bind(bp, on_press)
    frame.bind(bm, on_drag)
    frame.bind(br, on_release)
    for btn in btn_store.values():
        btn.bind(bp, on_press)
        btn.bind(bm, on_drag)
        btn.bind(br, on_release)


def save_json_file(parent: tk.Widget, data: object, *,
                   title: str = "Save", default_name: str = "data.json",
                   initial_dir: Optional[str] = None) -> bool:
    """
    Show a save-file dialog and write *data* as indented JSON.
    Returns True on success, False if cancelled or on error.
    """
    path_str = filedialog.asksaveasfilename(
        parent=parent, title=title,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialfile=default_name,
        initialdir=initial_dir,
    )
    if not path_str:
        return False
    try:
        with open(path_str, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
    except OSError as exc:
        messagebox.showerror("Save failed", str(exc), parent=parent)
        return False


def load_json_file(parent: tk.Widget, *,
                   title: str = "Load",
                   initial_dir: Optional[str] = None) -> Optional[object]:
    """
    Show an open-file dialog and return the parsed JSON object, or None if
    cancelled or on error.
    """
    path_str = filedialog.askopenfilename(
        parent=parent, title=title,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialdir=initial_dir,
    )
    if not path_str:
        return None
    try:
        with open(path_str, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        messagebox.showerror("Load failed", str(exc), parent=parent)
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


# =============================================================================
# Timepoint parser
# =============================================================================

def parse_timepoint_hours(tp: str) -> Optional[float]:
    """
    Convert a timepoint string to fractional hours.
    Returns None when the string cannot be parsed at all.

    Formats tried in order:
      1. DDdHHhMMm  e.g. "02d04h30m" -> 52.5
      2. Standalone unit suffix  e.g. "48h", "2d", "30m"
      3. Pure number  e.g. "48" or "1.5" -> treated as hours
      4. Prefixed ordinal  e.g. "T01", "day2" -> numeric suffix as index
    """
    s = tp.strip()
    if not s:
        return None

    # 1. DDdHHhMMm (all components optional, at least one required)
    m = re.fullmatch(r"(?:(\d{1,4})d)?(?:(\d{1,2})h)?(?:(\d{1,2})m)?", s, re.I)
    if m and any(m.groups()):
        return int(m.group(1) or 0)*24.0 + int(m.group(2) or 0) + int(m.group(3) or 0)/60.0

    # 2. Standalone unit: "48h", "2d", "30m", "90min"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(h(?:ours?)?|d(?:ays?)?|m(?:in(?:utes?)?)?)",
                     s, re.I)
    if m:
        val, unit = float(m.group(1)), m.group(2)[0].lower()
        if unit == "h": return val
        if unit == "d": return val * 24.0
        if unit == "m": return val / 60.0

    # 3. Pure number (treated as hours)
    try:
        return float(s)
    except ValueError:
        pass

    # 4. Prefixed ordinal: strip leading non-digit chars, keep trailing number
    #    e.g. "T01" -> 1.0, "day02" -> 2.0, "tp_3" -> 3.0
    m = re.search(r"(\d+(?:\.\d+)?)$", s)
    if m:
        return float(m.group(1))

    return None

# =============================================================================
# CSV loading and aggregation
# =============================================================================

# Columns kept as strings (not coerced to float)
_STRING_COLS = {"filename", "experiment", "channel", "well", "fov", "timepoint"}


def load_well_csv(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            coerced: dict = {}
            for k, v in row.items():
                if k in _STRING_COLS:
                    coerced[k] = v
                else:
                    try:
                        coerced[k] = float(v)
                    except (ValueError, TypeError):
                        coerced[k] = v
            rows.append(coerced)
    return rows


def detect_fluor_channels(rows: List[dict]) -> List[str]:
    """
    Inspect column names in *rows* and return a sorted list of fluorescent
    channel prefixes that have a *_mean_intensity column.

    e.g. columns ["gfp_mean_intensity", "mcherry_mean_intensity", ...]
         -> ["gfp", "mcherry"]
    """
    if not rows:
        return []
    channels = []
    for col in rows[0].keys():
        if col.endswith("_mean_intensity"):
            prefix = col[: -len("_mean_intensity")]
            if prefix:
                channels.append(prefix)
    return sorted(channels)


# (time_h, mean_above_threshold, sd_above, fraction_above, n_above, n_total)
# n_above : cells above threshold at this timepoint  → denominator for plot 1
# n_total : all cells at this timepoint              → denominator for plot 2
# These differ because plot 1 (mean GFP) only averages cells above threshold,
# while plot 2 (fraction) counts ALL cells to form the denominator.
AggPoint = Tuple[float, float, float, float, int, int]


def _ordinal_timepoints(rows: List[dict], tp_col: str = "timepoint_hours") -> Dict[str, float]:
    """
    Build a string->ordinal mapping for rows whose numeric timepoint is NaN/missing.

    Collects every distinct raw "timepoint" string that failed numeric parsing,
    sorts them lexicographically, and assigns 0-based ordinal floats so that
    T01 < T02 < T03, day1 < day2, etc. still plot in the right order.
    """
    raw_strings: set = set()
    for row in rows:
        raw = row.get(tp_col)
        numeric_ok = isinstance(raw, float) and not math.isnan(raw)
        if not numeric_ok:
            tp_str = str(row.get("timepoint", ""))
            if tp_str and parse_timepoint_hours(tp_str) is None:
                raw_strings.add(tp_str)
    return {s: float(i) for i, s in enumerate(sorted(raw_strings))}


def aggregate_with_threshold(
    rows: List[dict],
    threshold: float,
    use_sem: bool = False,
    tp_col: str = "timepoint_hours",
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
) -> List[AggPoint]:
    """Group rows by timepoint; compute stats for cells above threshold.

    Applies consistent gating criteria across all channels upfront, then computes
    statistics on the filtered cell population. This ensures that "Fraction On"
    and other metrics are computed on the same set of cells regardless of which
    channel or metric is being plotted.

    Timepoints are resolved in priority order:
      1. Numeric value already in tp_col (written by the pipeline).
      2. parse_timepoint_hours() on the raw timepoint string.
      3. Lexicographic ordinal fallback: rows whose timepoint cannot be
         parsed numerically are still included, sorted by string order.

    Gating criteria (applied upfront to all rows):
      - Cells with area_px <= cell_area_threshold are excluded
      - Cells with any channel's intensity <= its gate threshold are excluded

    Then, within the filtered population:
      - val_col: the column to compute statistics on
      - threshold: cells in val_col > threshold are counted for "Fraction On"

    Args:
        rows: List of cell dictionaries from CSV data
        threshold: ThreshFracOn value for computing fraction above threshold
        use_sem: If True, compute SEM; if False, compute SD
        tp_col: Column name for timepoint
        val_col: Column name for the value to aggregate
        cell_area_threshold: Minimum cell area (FluorGating)
        fluor_gates: Dict mapping channel name -> gate threshold (FluorGating).
                     Cells below any gate are excluded. E.g., {"gfp": 10.0, "mcherry": 20.0}

    Returns:
        List of AggPoint tuples: (timepoint, mean, spread, fraction_above, n_above, n_total)
    """
    if fluor_gates is None:
        fluor_gates = {}

    all_v:   Dict[float, List[float]] = defaultdict(list)
    above_v: Dict[float, List[float]] = defaultdict(list)

    # Pre-build ordinal map for any unparseable timepoint strings.
    ordinals = _ordinal_timepoints(rows, tp_col)

    for row in rows:
        # Step 1: Filter by cell area threshold (applies to all rows)
        try:
            area = float(row.get("area_px", 0))
            if area <= cell_area_threshold:
                continue
        except (ValueError, TypeError):
            continue

        # Step 2: Filter by all channel fluorescence gates (applies to all rows)
        # This ensures we only include cells that pass ALL QC criteria
        gates_passed = True
        for channel, gate_threshold in fluor_gates.items():
            col = f"{channel}_mean_intensity"
            try:
                fluor = float(row.get(col, float('nan')))
                if fluor != fluor or fluor <= gate_threshold:  # NaN or below gate
                    gates_passed = False
                    break
            except (ValueError, TypeError):
                gates_passed = False
                break

        if not gates_passed:
            continue

        # Step 3: Extract timepoint (same as before)
        raw = row.get(tp_col)
        if isinstance(raw, float) and not math.isnan(raw):
            t: Optional[float] = raw
        else:
            tp_str = str(row.get("timepoint", ""))
            t = parse_timepoint_hours(tp_str)
            if t is None:
                t = ordinals.get(tp_str)  # lexicographic ordinal
            # No timepoint field in schema at all — treat all rows as t=0.
            if t is None and not tp_str:
                t = 0.0
        if t is None:
            continue

        # Step 4: Get the value to aggregate on
        try:
            val = float(row[val_col])
        except (KeyError, ValueError, TypeError):
            continue

        # At this point, row passes all gating criteria. Include in aggregation.
        all_v[t].append(val)
        if val > threshold:
            above_v[t].append(val)

    result: List[AggPoint] = []
    for t in sorted(all_v):
        above   = above_v.get(t, [])
        n_total = len(all_v[t])
        n_above = len(above)
        mean    = sum(above) / n_above if n_above else float("nan")
        spread  = 0.0
        if n_above > 1:
            sd     = statistics.pstdev(above)
            spread = sd / math.sqrt(n_above) if use_sem else sd
        result.append((t, mean, spread,
                       n_above / n_total if n_total else float("nan"),
                       n_above, n_total))
    return result


def _all_fluor_values(rows: List[dict], val_col: str = "gfp_mean_intensity") -> List[float]:
    return [float(row[val_col]) for row in rows
            if val_col in row and math.isfinite(float(row[val_col]))
            if isinstance(row[val_col], (int, float)) and not isinstance(row[val_col], bool)]


def _all_fluor_values_filtered(
    rows: List[dict],
    val_col: str = "gfp_mean_intensity",
    cell_area_threshold: float = 0.0,
    fluor_gates: Optional[Dict[str, float]] = None,
) -> List[float]:
    """Extract fluorescence values from rows, filtering by cell area and all fluorescence gates.

    Args:
        rows: List of cell dictionaries
        val_col: Column to extract values from
        cell_area_threshold: Minimum cell area (FluorGating)
        fluor_gates: Dict mapping channel -> gate threshold (FluorGating).
                     Cells below any gate are excluded.
    """
    if fluor_gates is None:
        fluor_gates = {}

    result = []
    for row in rows:
        # Filter by cell area threshold
        try:
            area = float(row.get("area_px", 0))
            if area <= cell_area_threshold:
                continue
        except (ValueError, TypeError):
            continue

        # Filter by all fluorescence gates
        gates_passed = True
        for channel, gate_threshold in fluor_gates.items():
            col = f"{channel}_mean_intensity"
            try:
                fluor = float(row.get(col, float('nan')))
                if fluor != fluor or fluor <= gate_threshold:  # NaN or below gate
                    gates_passed = False
                    break
            except (ValueError, TypeError):
                gates_passed = False
                break

        if not gates_passed:
            continue

        # Extract the target value
        try:
            val = float(row[val_col])
            if not math.isfinite(val):
                continue
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                continue
            result.append(val)
        except (KeyError, ValueError, TypeError):
            continue

    return result


def _beeswarm_jitter(
    values: List[float],
    x_center: float = 0.0,
    max_spread: float = 0.35,
    n_bins: int = 40,
) -> Tuple[List[float], List[float]]:
    """
    Compute x-jitter positions for a beeswarm column.

    Values are binned vertically (by value magnitude); within each bin points
    are spread left/right alternately from the centre.  Returns parallel lists
    (xs, ys) ready for ax.scatter().

    Pure Python + no external dependencies beyond what is already imported.
    """
    if not values:
        return [], []

    sorted_v = sorted(values)
    lo, hi = sorted_v[0], sorted_v[-1]
    rng = hi - lo if hi > lo else 1.0
    bin_w = rng / n_bins

    # Group indices by bin
    bins: Dict[int, List[int]] = {}
    for i, v in enumerate(values):
        b = min(int((v - lo) / bin_w), n_bins - 1)
        bins.setdefault(b, []).append(i)

    step = max_spread / max(max(len(idxs) for idxs in bins.values()), 1)

    xs = [0.0] * len(values)
    ys = list(values)
    for idxs in bins.values():
        n = len(idxs)
        # Sort by original value for visual consistency
        idxs_sorted = sorted(idxs, key=lambda k: values[k])
        for rank, idx in enumerate(idxs_sorted):
            # Alternate: 0, +1, -1, +2, -2 …
            offset = ((rank + 1) // 2) * (1 if rank % 2 == 1 else -1)
            xs[idx] = x_center + offset * step

    return xs, ys


# =============================================================================
# Image reference and finders
# =============================================================================

_IMAGE_EXTS   = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
_MASK_RE      = re.compile(r"_labels\.(tif{1,2}|png)$", re.I)
_OVERLAY_RE   = re.compile(r"_overlay\.(tif{1,2}|png|jpe?g)$", re.I)
_TOPHAT_FLUOR_RE = re.compile(r"_tophat_\w+\.tif{1,2}$", re.I)  # output of process_microscopy: <base>_tophat_<channel>.tif
_OUT_ZIP_RE   = re.compile(r"^([A-Ha-h])(\d{1,2})_out\.zip$", re.I)
_PLAIN_ZIP_RE = re.compile(r"^([A-Ha-h])(\d{1,2})\.zip$",     re.I)
_FNAME_RE     = re.compile(
    r"^(?P<exp>[^_]+)_(?P<channel>[^_]*)_(?P<well>[^_]+)_(?P<fov>[^_]+)_(?P<tp>[^_.]+)",
    re.I,
)


def _norm_well(raw: str) -> Optional[str]:
    m = re.match(r"([A-Ha-h])(\d{1,2})$", raw.strip(), re.I)
    return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else None


def _extract_well_token(label: str) -> Optional[str]:
    """'gfp_measurements_B10' → 'B10'."""
    m = re.search(r"([A-Ha-h])(\d{1,2})$", label)
    return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else None


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


def _classify_member(
    name: str,
    fluor_lower: str,
    _fov_tp_extractor=None,
) -> Tuple[str, str, str]:
    """Return (kind, fov, tp) where kind is 'fluor', 'tophat_fluor', 'mask', 'overlay', or ''.

    *fluor_lower* is the lowercase fluorescent channel token (e.g. 'gfp', 'mcherry').
    *_fov_tp_extractor* is an optional callable(stem) -> (fov, tp).  When
    None the legacy hardcoded _FNAME_RE is used as a fallback so that results
    directories produced before pipeline_info.json was introduced still work.
    """
    return _preview_classify_member(
        name=name,
        fluor_lower=fluor_lower,
        mask_re=_MASK_RE,
        overlay_re=_OVERLAY_RE,
        tophat_fluor_re=_TOPHAT_FLUOR_RE,
        fov_tp_extractor=_fov_tp_extractor,
        legacy_extractor=_legacy_extractor,
    )


def _scan_zip_members(
    zip_path: Path,
    fluor_lower: str,
    member_prefix: str = "",
    _fov_tp_extractor=None,
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


def find_well_images_and_masks(
    data_dir: Optional[Path],
    well_label: str,
    fluor_token: str = "GFP",
    in_dir: Optional[Path] = None,
    _fov_tp_extractor=None,
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

    # ── 1. Structured in/out directory layout ────────────────────────────────
    # in_dir  → plain <well>.zip files → GFP source images
    # data_dir → <well>_out.zip files  → masks and overlays
    if in_dir and in_dir.is_dir() and well_token:
        in_zips = _find_plain_well_zips_in_dir(in_dir, well_token)
        for wzip in in_zips:
            g, ov, mk, th, _sm = _scan_zip_members(wzip, fluor_lower,
                                                   _fov_tp_extractor=_fov_tp_extractor)
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
                                                   _fov_tp_extractor=_fov_tp_extractor)
            for k, v in g.items():
                fluor.setdefault(k, v)
            for k, v in ov.items():
                overlay.setdefault(k, v)
            for k, v in mk.items():
                mask.setdefault(k, v)
            for k, v in th.items():
                tophat_fluor.setdefault(k, v)

    # ── 2. Flat directory: all zips in data_dir ───────────────────────────────
    if in_dir is None and data_dir and data_dir.is_dir() and well_token:
        for wzip in _find_well_zips_in_dir(data_dir, well_token):
            g, ov, mk, th, _sm = _scan_zip_members(wzip, fluor_lower,
                                                   _fov_tp_extractor=_fov_tp_extractor)
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
                kind, fov, tp = _classify_member(p.name, fluor_lower, _fov_tp_extractor)
                if not kind:
                    continue
                if well_token:
                    # Filter by well: when a schema extractor is present we have
                    # no dedicated well-field extractor here, so we use a safe
                    # substring match.  With the legacy path we keep the old
                    # regex-based well comparison for backward compatibility.
                    if _fov_tp_extractor is not None:
                        if well_token.lower() not in p.name.lower():
                            continue
                    else:
                        m = _FNAME_RE.match(p.stem)
                        fw = _norm_well(m.group("well")) if m else None
                        if fw and fw != well_token:
                            continue
                        if not fw and well_token.lower() not in p.name.lower():
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

    return (dict(sorted(fluor.items())), dict(sorted(overlay.items())),
            dict(sorted(mask.items())), dict(sorted(tophat_fluor.items())))

# =============================================================================
# Categorical label colourmap
# =============================================================================

_LABEL_PALETTE = None


def _label_to_rgb(arr: "_np.ndarray") -> "_np.ndarray":
    global _LABEL_PALETTE
    if _LABEL_PALETTE is None:
        _LABEL_PALETTE = _np.array([
            [255,255,255], [31,119,180], [255,127,14], [44,160,44], [214,39,40],
            [148,103,189], [140,86,75],  [227,119,194],[127,127,127],[188,189,34],
            [23,190,207],  [57,220,205], [255,187,51], [166,206,227],[178,223,138],
            [251,154,153], [253,191,111],[202,178,214],[106,61,154], [177,89,40],
        ], dtype=_np.uint8)
    h, w  = arr.shape[:2]
    rgb   = _np.zeros((h, w, 3), dtype=_np.uint8)
    for uid in _np.unique(arr):
        rgb[arr == uid] = _LABEL_PALETTE[int(uid) % len(_LABEL_PALETTE)]
    return rgb

# =============================================================================
# Tooltip
# =============================================================================

class _Tooltip:
    """Floating label that stays within screen bounds."""

    def __init__(self, widget: tk.Widget) -> None:
        self._w   = widget
        self._win: Optional[tk.Toplevel] = None
        self._lbl: Optional[tk.Label]   = None

    def show(self, text: str, sx: int, sy: int) -> None:
        if self._win is None:
            self._win = tk.Toplevel(self._w)
            self._win.wm_overrideredirect(True)
            self._win.wm_attributes("-topmost", True)
            self._lbl = tk.Label(self._win, text=text, font=FM_TINY,
                                 background=TOOLTIP_BG, foreground=TOOLTIP_FG,
                                 padx=6, pady=3, relief=tk.FLAT, bd=1)
            self._lbl.pack()
        else:
            self._lbl.config(text=text)   # type: ignore[union-attr]
        self._win.update_idletasks()
        tw = self._win.winfo_width()
        th = self._win.winfo_height()
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        OFF = 16
        tx = sx + OFF if sx + OFF + tw <= sw else sx - tw - OFF
        ty = sy + OFF if sy + OFF + th <= sh else sy - th - OFF
        self._win.wm_geometry(f"+{max(0,tx)}+{max(0,ty)}")

    def hide(self) -> None:
        if self._win:
            self._win.destroy()
        self._win = None
        self._lbl = None

# =============================================================================
# Reusable image panel
# =============================================================================

class _ImagePanel:
    """
    Toggleable panel showing one image at a time.
    Features:
      • Pixel-intensity tooltip on canvas mouseover
      • Full-path tooltip on filename label mouseover
      • Optional LUT min/max editor with Auto button (for fluorescence panel)
    """

    def __init__(self, parent: tk.Frame, title: str, tooltip: _Tooltip,
                 show_lut: bool = False) -> None:
        self._tooltip    = tooltip
        self._photo:     Optional[object]  = None
        self._raw_arr:   Optional[object]  = None
        self._img_x0     = 0
        self._img_y0     = 0
        self._img_scale  = 1.0
        self._full_path  = ""
        self._colourmap: Optional[str] = None
        self._show_lut   = show_lut
        self._lut_min    = 0.0
        self._lut_max    = 65535.0

        # Header
        hdr = tk.Frame(parent, bg=BG_SIDE)
        hdr.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(hdr, text=title, font=FM_BOLD, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        self._toggle_btn = _btn_secondary(hdr, "Hide", self._toggle, padx=8)
        self._toggle_btn.pack(side=tk.RIGHT)

        # Filename label with path tooltip
        self._file_lbl = tk.Label(parent, text="", font=FM_TINY, fg=TXT_MUT,
                                  bg=BG_SIDE, wraplength=310, justify=tk.LEFT,
                                  cursor="question_arrow")
        self._file_lbl.pack(fill=tk.X, padx=10)
        self._path_tip = _Tooltip(self._file_lbl)
        self._file_lbl.bind("<Enter>",  self._path_enter)
        self._file_lbl.bind("<Motion>", self._path_motion)
        self._file_lbl.bind("<Leave>",  lambda _e: self._path_tip.hide())

        # Collapsible body
        self._body = tk.Frame(parent, bg=BG_SIDE)
        self._body.pack(fill=tk.BOTH, expand=True)

        # LUT editor
        if show_lut:
            row = tk.Frame(self._body, bg=BG_SIDE)
            row.pack(fill=tk.X, padx=10, pady=(2, 0))
            tk.Label(row, text="LUT min", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
            self._lut_min_var = tk.StringVar(value="0")
            self._lut_max_var = tk.StringVar(value="65535")
            for var, side in ((self._lut_min_var, "LEFT"), (self._lut_max_var, "LEFT")):
                e = tk.Entry(row, textvariable=var, font=FM_TINY, width=7,
                             justify="center", fg=ACCENT, bg=BG_PANEL,
                             insertbackground=ACCENT, relief=tk.FLAT,
                             highlightthickness=1, highlightcolor=ACCENT,
                             highlightbackground=BORDER)
                e.pack(side=getattr(tk, side), padx=(3, 8))
                e.bind("<Return>",   self._lut_commit)
                e.bind("<FocusOut>", self._lut_commit)
                if var is self._lut_min_var:
                    tk.Label(row, text="max", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
            tk.Button(row, text="Auto", command=self._lut_auto, font=FM_TINY,
                      bg=BG_CELL, fg=TXT_SEC, activebackground=BG_HOVER,
                      relief=tk.FLAT, padx=6, pady=1, cursor="hand2").pack(side=tk.LEFT)

        self._canvas = tk.Canvas(self._body, bg=PLOT_BG,
                                 highlightthickness=1, highlightbackground=BORDER)
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 8))
        self._canvas.bind("<Configure>", lambda _e: self._render())
        self._canvas.bind("<Motion>",    self._canvas_motion)
        self._canvas.bind("<Leave>",     lambda _e: self._tooltip.hide())

    # ── path tooltip ──────────────────────────────────────────────────────────
    def _path_enter(self, _e=None) -> None:
        if self._full_path:
            sx = self._file_lbl.winfo_rootx()
            sy = self._file_lbl.winfo_rooty() + self._file_lbl.winfo_height()
            self._path_tip.show(self._full_path, sx, sy)

    def _path_motion(self, e) -> None:
        if self._full_path:
            sx = self._file_lbl.winfo_rootx() + e.x
            sy = self._file_lbl.winfo_rooty() + e.y
            self._path_tip.show(self._full_path, sx, sy)

    # ── toggle ────────────────────────────────────────────────────────────────
    def _toggle(self) -> None:
        if self._body.winfo_ismapped():
            self._body.pack_forget()
            self._toggle_btn.config(text="Show")
        else:
            self._body.pack(fill=tk.BOTH, expand=True)
            self._toggle_btn.config(text="Hide")

    # ── LUT ───────────────────────────────────────────────────────────────────
    def _lut_commit(self, _e=None) -> None:
        if not self._show_lut:
            return
        try:
            lo = float(self._lut_min_var.get())
        except ValueError:
            lo = self._lut_min
        try:
            hi = float(self._lut_max_var.get())
        except ValueError:
            hi = self._lut_max
        if hi <= lo:
            hi = lo + 1.0
        self._lut_min = lo
        self._lut_max = hi
        self._lut_min_var.set(f"{lo:.0f}")
        self._lut_max_var.set(f"{hi:.0f}")
        self._render()

    def _lut_auto(self) -> None:
        if self._raw_arr is None or not _NP_AVAILABLE:
            return
        arr = _np.asarray(self._raw_arr, dtype=_np.float32)
        lo, hi = float(arr.min()), float(arr.max())
        if hi <= lo:
            hi = lo + 1.0
        self._lut_min = lo
        self._lut_max = hi
        if self._show_lut:
            self._lut_min_var.set(f"{lo:.0f}")
            self._lut_max_var.set(f"{hi:.0f}")
        self._render()

    # ── public API ────────────────────────────────────────────────────────────
    def render_arr(self, arr: "_np.ndarray", filename: str,
                   full_path: str = "", colourmap: Optional[str] = None) -> None:
        self._file_lbl.config(text=filename)
        self._full_path = full_path or filename
        self._raw_arr   = arr
        self._colourmap = colourmap
        if self._show_lut:   # auto-range on first load
            lo, hi = float(arr.min()), float(arr.max())
            if hi <= lo: hi = lo + 1.0
            self._lut_min = lo
            self._lut_max = hi
            self._lut_min_var.set(f"{lo:.0f}")
            self._lut_max_var.set(f"{hi:.0f}")
        self._render()

    def show_message(self, text: str, colour: str = TXT_MUT) -> None:
        self._canvas.delete("all")
        self._photo   = None
        self._raw_arr = None
        self._file_lbl.config(text="")
        self._full_path = ""
        cw = self._canvas.winfo_width() or 300
        ch = self._canvas.winfo_height() or 200
        self._canvas.create_text(cw//2, ch//2, text=text, fill=colour,
                                 font=FM_UI, justify=tk.CENTER)

    def clear(self, message: str = "") -> None:
        self._raw_arr = None
        self._photo   = None
        self._canvas.delete("all")
        self._file_lbl.config(text="")
        self._full_path = ""
        if message:
            self.show_message(message)

    # ── rendering ─────────────────────────────────────────────────────────────
    def _render(self) -> None:
        if not _PIL_AVAILABLE or not _NP_AVAILABLE or self._raw_arr is None:
            return
        canvas = self._canvas
        canvas.delete("all")
        self._photo = None
        cw = canvas.winfo_width()  or 300
        ch = canvas.winfo_height() or 200
        try:
            arr = _np.asarray(self._raw_arr, dtype=_np.float32)
            if self._colourmap == "label":
                rgb_arr = _label_to_rgb(arr.astype(_np.int32))
                img = _PILImage.fromarray(rgb_arr, mode="RGB")
            else:
                lo = self._lut_min if self._show_lut else float(arr.min())
                hi = self._lut_max if self._show_lut else float(arr.max())
                if hi <= lo: hi = lo + 1.0
                display = ((_np.clip(arr, lo, hi) - lo) / (hi - lo) * 255).astype(_np.uint8)
                img = _PILImage.fromarray(display, mode="L").convert("RGB")
            iw, ih = img.size
            scale = min(cw / iw, ch / ih, 1.0)
            nw, nh = max(1, int(iw*scale)), max(1, int(ih*scale))
            img = img.resize((nw, nh), _PILImage.LANCZOS)
            self._img_scale = scale
            self._img_x0    = (cw - nw) // 2
            self._img_y0    = (ch - nh) // 2
            self._photo     = _PILImageTk.PhotoImage(img)
            canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=self._photo)
        except Exception as exc:
            canvas.create_text(cw//2, ch//2, text=f"Render error:\n{exc}",
                               fill=WELL_COLOR_2, font=FM_TINY, justify=tk.CENTER)

    def _canvas_motion(self, e) -> None:
        if self._raw_arr is None or self._img_scale <= 0:
            self._tooltip.hide()
            return
        ix = (e.x - self._img_x0) / self._img_scale
        iy = (e.y - self._img_y0) / self._img_scale
        arr = _np.asarray(self._raw_arr)
        h, w = arr.shape[:2]
        if not (0 <= ix < w and 0 <= iy < h):
            self._tooltip.hide()
            return
        px, py = int(ix), int(iy)
        val    = arr[py, px]
        vstr   = ("  ".join(f"{v:.0f}" for v in val)
                  if hasattr(val, "__len__") else f"{float(val):.1f}")
        sx = e.widget.winfo_rootx() + e.x
        sy = e.widget.winfo_rooty() + e.y
        self._tooltip.show(f"x={px}  y={py}   value: {vstr}", sx, sy)

# =============================================================================
# GUI log handler
# =============================================================================

class _GUILogHandler(logging.Handler):
    """Routes logging records into a tk.Text widget on the main thread."""

    def __init__(self, widget: tk.Text) -> None:
        super().__init__()
        self._w = widget
        widget.tag_configure("ERROR",   foreground=CLR_DANGER, font=FM_TINY)
        widget.tag_configure("WARNING", foreground=CLR_WARN_DARK, font=FM_TINY)
        widget.tag_configure("INFO",    foreground=TXT_SEC,   font=FM_TINY)
        widget.tag_configure("DEBUG",   foreground=TXT_MUT,   font=FM_TINY)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) + "\n"
            tag = record.levelname if record.levelname in ("ERROR","WARNING","INFO","DEBUG") else "INFO"
            self._w.after(0, self._append, msg, tag)
        except Exception:
            self.handleError(record)

    def _append(self, msg: str, tag: str) -> None:
        self._w.configure(state=tk.NORMAL)
        self._w.insert(tk.END, msg, tag)
        self._w.see(tk.END)
        self._w.configure(state=tk.DISABLED)

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


# ---------------------------------------------------------------------------
# CellGatingTab
# ---------------------------------------------------------------------------
class CellGatingTab(tk.Frame):
    """Tab for cell inclusion gating (FluorGating) and per-channel settings."""

    def __init__(self, parent: tk.Widget, app: "WellViewerApp", **kw):
        super().__init__(parent, bg=BG_APP, **kw)
        self._app = app
        self._cell_areas: list[float] = []
        self._cell_area_threshold = tk.StringVar(value="0.0")  # Cell area gating threshold
        self._fluor_gates: dict[str, tk.StringVar] = {}  # channel -> threshold StringVar
        self._thresh_frac_on: dict[str, tk.StringVar] = {}  # channel -> ThreshFracOn StringVar
        self._fluor_data: dict[str, list[float]] = {}  # channel -> list of values
        self._figure: Optional[Figure] = None
        self._canvas: Optional[FigureCanvasTkAgg] = None
        self._ax: Optional[any] = None
        self._axes_stack: list[tuple] = []  # For zoom history
        self._gating_controls_frame: Optional[tk.Frame] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the UI layout."""
        # Main vertical layout
        main_frame = tk.Frame(self, bg=BG_APP)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Top: Control panels ────────────────────────────────────────
        control_frame = tk.Frame(main_frame, bg=BG_SIDE, height=100)
        control_frame.pack(fill=tk.X, padx=8, pady=8)

        # Cell area gating threshold
        cell_area_frame = tk.Frame(control_frame, bg=BG_SIDE)
        cell_area_frame.pack(fill=tk.X, padx=4, pady=(4, 8))

        tk.Label(
            cell_area_frame, text="Cell Area Threshold (pixels):",
            font=FM_UI, fg=TXT_PRI, bg=BG_SIDE
        ).pack(side=tk.LEFT, padx=(0, 8))

        cell_area_entry = tk.Entry(
            cell_area_frame,
            textvariable=self._cell_area_threshold,
            font=FM_MONO,
            fg=ACCENT,
            bg=BG_PANEL,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=BORDER,
            width=10
        )
        cell_area_entry.pack(side=tk.LEFT, padx=(0, 8))
        cell_area_entry.bind("<FocusOut>", self._on_gating_change)
        cell_area_entry.bind("<Return>", self._on_gating_change)

        # Title for FluorGating (cell inclusion)
        tk.Label(
            control_frame, text="FluorGating (Cell Inclusion)",
            font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE
        ).pack(fill=tk.X, padx=4, pady=(4, 8))

        # Scrollable frame for per-channel gating controls
        canvas = tk.Canvas(control_frame, bg=BG_SIDE, highlightthickness=0, bd=0, height=80)
        scrollbar = tk.Scrollbar(control_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_SIDE)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._gating_controls_frame = scrollable_frame

        # ── Bottom: CDF plot ───────────────────────────────────────────
        plot_frame = tk.Frame(main_frame, bg=BG_APP)
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._figure = Figure(figsize=(8, 5), dpi=100, facecolor=BG_APP)
        self._canvas = FigureCanvasTkAgg(self._figure, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar_frame = tk.Frame(plot_frame, bg=BG_APP)
        toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        toolbar.update()
        toolbar_frame.pack(fill=tk.X)

        # Status label
        self._status_label = tk.Label(
            main_frame, text="No data loaded",
            font=FM_TINY, fg=TXT_MUT, bg=BG_APP
        )
        self._status_label.pack(fill=tk.X, padx=8, pady=(0, 8))

    def _build_channel_controls(self) -> None:
        """Build per-channel gating controls."""
        # Clear existing controls
        for widget in self._gating_controls_frame.winfo_children():
            widget.destroy()

        channels = self._app._fluor_channels
        if not channels:
            tk.Label(
                self._gating_controls_frame,
                text="No channels loaded",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(fill=tk.X, padx=4, pady=4)
            # Force redraw
            self._gating_controls_frame.update_idletasks()
            return

        for channel in channels:
            # Channel label
            ch_frame = tk.Frame(self._gating_controls_frame, bg=BG_SIDE)
            ch_frame.pack(fill=tk.X, padx=4, pady=4)

            tk.Label(
                ch_frame,
                text=f"{channel.upper()} Channel:",
                font=FM_BOLD,
                fg=TXT_SEC,
                bg=BG_SIDE,
                width=18,
                anchor="w"
            ).pack(side=tk.LEFT, padx=(0, 8))

            # FluorGating threshold input
            if channel not in self._fluor_gates:
                self._fluor_gates[channel] = tk.StringVar(value="0.0")

            tk.Label(
                ch_frame,
                text="FluorGating:",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(side=tk.LEFT, padx=(0, 4))

            gate_entry = tk.Entry(
                ch_frame,
                textvariable=self._fluor_gates[channel],
                font=FM_MONO,
                fg=ACCENT,
                bg=BG_PANEL,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=ACCENT,
                highlightbackground=BORDER,
                width=10
            )
            gate_entry.pack(side=tk.LEFT, padx=(0, 12))
            gate_entry.bind("<FocusOut>", self._on_gating_change)
            gate_entry.bind("<Return>", self._on_gating_change)

            # ThreshFracOn input
            if channel not in self._thresh_frac_on:
                self._thresh_frac_on[channel] = tk.StringVar(value="50.0")

            tk.Label(
                ch_frame,
                text="ThreshFracOn:",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(side=tk.LEFT, padx=(0, 4))

            thresh_entry = tk.Entry(
                ch_frame,
                textvariable=self._thresh_frac_on[channel],
                font=FM_MONO,
                fg=ACCENT,
                bg=BG_PANEL,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=ACCENT,
                highlightbackground=BORDER,
                width=10
            )
            thresh_entry.pack(side=tk.LEFT, padx=(0, 8))
            thresh_entry.bind("<FocusOut>", self._on_threshold_frac_on_change)
            thresh_entry.bind("<Return>", self._on_threshold_frac_on_change)

        # Force redraw of the scrollable frame
        self._gating_controls_frame.update_idletasks()

    def _load_cell_areas(self) -> None:
        """Load cell areas and fluorescence values from currently loaded wells."""
        self._cell_areas = []
        self._fluor_data: dict[str, list[float]] = {}  # channel -> list of values

        # Get cell areas and fluorescence values from all loaded wells
        for label in self._app._well_paths:
            rows = self._app._get_rows(label)
            for row in rows:
                # Get cell area
                try:
                    area = float(row.get("area_px", 0))
                    if area > 0:
                        self._cell_areas.append(area)
                except (ValueError, TypeError):
                    pass

                # Get fluorescence values for each channel
                for channel in self._app._fluor_channels:
                    val_col = f"{channel}_mean_intensity"
                    try:
                        val = float(row.get(val_col, 0))
                        if val > 0:
                            if channel not in self._fluor_data:
                                self._fluor_data[channel] = []
                            self._fluor_data[channel].append(val)
                    except (ValueError, TypeError):
                        pass

        # Build per-channel controls
        self._build_channel_controls()

        if self._cell_areas:
            self._axes_stack = []  # Reset zoom history
            self._plot_cdf()
            self._status_label.config(
                text=f"Loaded {len(self._cell_areas)} cells",
                fg=TXT_PRI
            )
        else:
            self._status_label.config(
                text="No cell data found",
                fg=TXT_MUT
            )

    def _plot_cdf(self) -> None:
        """Plot CDFs for cell area and all fluorescence channels."""
        if not self._cell_areas and not self._fluor_data:
            return

        self._figure.clear()

        # Determine number of plots needed (cell area + channels)
        n_plots = 1 + len(self._fluor_data)  # 1 for cell area, rest for channels

        # Create subplots
        axes = []
        for i in range(n_plots):
            ax = self._figure.add_subplot(2, (n_plots + 1) // 2, i + 1, facecolor=BG_PANEL)
            axes.append(ax)

        # Plot cell area CDF
        if self._cell_areas:
            areas = _np.array(sorted(self._cell_areas))
            cdf = _np.arange(1, len(areas) + 1) / len(areas)
            axes[0].plot(areas, cdf, linewidth=2, color=ACCENT, alpha=0.8)
            axes[0].fill_between(areas, cdf, alpha=0.2, color=ACCENT)
            axes[0].set_xlabel("Cell Area (pixels)", color=TXT_PRI, fontsize=9)
            axes[0].set_ylabel("Cumulative Probability", color=TXT_PRI, fontsize=9)
            axes[0].set_title("Cell Area Distribution", color=TXT_PRI, fontsize=10, fontweight="bold")
            axes[0].grid(True, alpha=0.2, color=TXT_MUT)
            axes[0].tick_params(colors=TXT_MUT, labelsize=8)

            # Add cell area threshold line
            try:
                cell_area_threshold = float(self._cell_area_threshold.get())
                axes[0].axvline(x=cell_area_threshold, color=WARN, linestyle="--", linewidth=2, alpha=0.7)
            except ValueError:
                pass

        # Plot CDFs for each fluorescence channel
        colors = [ACCENT, "#FF9500", "#FF3B30", "#34C759"]  # Predefined colors
        for idx, (channel, values) in enumerate(sorted(self._fluor_data.items()), 1):
            if idx < len(axes):
                ax = axes[idx]
                color = colors[idx % len(colors)]
                vals = _np.array(sorted(values))
                cdf = _np.arange(1, len(vals) + 1) / len(vals)
                ax.plot(vals, cdf, linewidth=2, color=color, alpha=0.8)
                ax.fill_between(vals, cdf, alpha=0.2, color=color)
                ax.set_xlabel(f"{channel.upper()} Intensity", color=TXT_PRI, fontsize=9)
                ax.set_ylabel("Cumulative Probability", color=TXT_PRI, fontsize=9)
                ax.set_title(f"{channel.upper()} Distribution", color=TXT_PRI, fontsize=10, fontweight="bold")
                ax.grid(True, alpha=0.2, color=TXT_MUT)
                ax.tick_params(colors=TXT_MUT, labelsize=8)

                # Add FluorGating threshold line for this channel
                try:
                    fluor_gate = float(self._fluor_gates[channel].get())
                    ax.axvline(x=fluor_gate, color=WARN, linestyle="--", linewidth=2, alpha=0.7)
                except (ValueError, KeyError):
                    pass

        self._ax = axes[0]  # Keep reference to first axis for zoom

        # Save current axis limits for zoom
        if not self._axes_stack:
            limits = [(ax.get_xlim(), ax.get_ylim()) for ax in axes]
            self._axes_stack.append(limits)

        self._figure.tight_layout()
        self._canvas.draw()

    def _on_gating_change(self, _e=None) -> None:
        """Handle FluorGating threshold change (when focus leaves field)."""
        try:
            # Validate cell area threshold
            float(self._cell_area_threshold.get())
            # Validate all inputs
            for channel in self._fluor_gates:
                float(self._fluor_gates[channel].get())
            # Redraw the CDF with new thresholds
            self._plot_cdf()
            # Redraw the app to reflect the new thresholds
            self._app._redraw()
        except ValueError:
            # Invalid input - revert to previous value (do nothing, field keeps old value)
            pass

    def _on_threshold_frac_on_change(self, _e=None) -> None:
        """Handle ThreshFracOn threshold change (when focus leaves field)."""
        try:
            # Validate all inputs
            for channel in self._thresh_frac_on:
                float(self._thresh_frac_on[channel].get())
            # Save the values
            self._save_threshold_frac_on()
            # Redraw the app to reflect the new thresholds
            self._app._redraw()
        except ValueError:
            # Invalid input - revert to previous value (do nothing, field keeps old value)
            pass

    def _save_threshold_frac_on(self) -> None:
        """Save ThreshFracOn values for all channels."""
        # Store in app state for persistence
        if not hasattr(self._app, '_thresh_frac_on_saved'):
            self._app._thresh_frac_on_saved = {}
        for channel, var in self._thresh_frac_on.items():
            try:
                self._app._thresh_frac_on_saved[channel] = float(var.get())
            except ValueError:
                pass

    def _load_threshold_frac_on(self) -> None:
        """Load saved ThreshFracOn values for all channels."""
        if hasattr(self._app, '_thresh_frac_on_saved'):
            for channel, value in self._app._thresh_frac_on_saved.items():
                if channel in self._thresh_frac_on:
                    self._thresh_frac_on[channel].set(str(value))

    def get_fluor_gate(self, channel: str) -> float:
        """Get FluorGating threshold for a channel."""
        if channel in self._fluor_gates:
            try:
                return float(self._fluor_gates[channel].get())
            except ValueError:
                return 0.0
        return 0.0

    def get_thresh_frac_on(self, channel: str) -> float:
        """Get ThreshFracOn threshold for a channel."""
        if channel in self._thresh_frac_on:
            try:
                return float(self._thresh_frac_on[channel].get())
            except ValueError:
                return 50.0
        return 50.0


class WellViewerApp(tk.Frame):

    def __init__(self, parent=None, data_path: Optional[Path] = None) -> None:
        # Support both embedded use (parent is a tk.Frame/Notebook tab)
        # and standalone use (parent is None → create a tk.Tk root).
        if parent is None:
            self._tk_root = tk.Tk()
            self._tk_root.title("Well Viewer")
            self._tk_root.configure(bg=BG_APP)
            self._tk_root.minsize(1000, 800)
            self._tk_root.geometry("1600x960")
            super().__init__(self._tk_root)
            self._tk_root.protocol("WM_DELETE_WINDOW", self._on_close)
        else:
            self._tk_root = None
            super().__init__(parent)
        self.configure(bg=BG_APP)
        self._NP_AVAILABLE = _NP_AVAILABLE
        self._np = _np

        # Data state
        self._data_dir:   Optional[Path]        = None   # dir with CSVs (and out-zips)
        self._in_dir:     Optional[Path]        = None   # dir with input well zips (fluor)
        self._tmp_dir:    Optional[Path]        = None
        self._well_paths: Dict[str, Path]       = {}
        self._cache:      Dict[str, List[dict]] = {}
        self._last_sel:   Optional[str]         = None
        self._prev_sel:   set                   = set()   # tracks prior selection for diffing

        # Active fluorescent channel (set when CSVs are loaded)
        self._fluor_channels: List[str] = []          # e.g. ["gfp", "mcherry"]
        self._active_channel: str       = "gfp"       # column prefix (overwritten on CSV load)
        self._active_val_col: str       = "gfp_mean_intensity"  # overwritten on CSV load

        # Plot controls
        self._threshold_min = 0.0
        self._threshold_max = 1.0
        self._threshold     = 50.0
        self._use_sem       = tk.BooleanVar(value=True)
        # Per-axes legend visibility; True = show, False = hidden
        self._legend_visible: Dict[str, bool] = {
            "mean": True, "frac": True, "cdf": True,
        }
        self._chan_var      = tk.StringVar(value="GFP")  # selected channel dropdown
        self._bar_tp_var    = tk.StringVar(value="—")  # selected timepoint for bar plots
        self._bar_swarm     = tk.BooleanVar(value=False)  # beeswarm mode toggle
        self._bar_violin    = tk.BooleanVar(value=False)  # violin mode toggle
        self._violin_bw     = tk.DoubleVar(value=0.4)     # KDE bandwidth (smoothing)
        self._bar_log_scale = tk.BooleanVar(value=False)  # log y-axis (beeswarm)
        self._bar_ylim_mean_lo = tk.StringVar(value="")   # fluor axis lower limit (auto="")
        self._bar_ylim_mean_hi = tk.StringVar(value="")   # fluor axis upper limit
        self._bar_ylim_frac_lo = tk.StringVar(value="")   # Fraction axis lower limit
        self._bar_ylim_frac_hi = tk.StringVar(value="")   # Fraction axis upper limit
        self._bar_order: Optional[List] = None            # custom bar ordering (None = natural)
        self._rep_sets:          List[ReplicateSet] = []  # global pool of replicate sets
        self._active_rep_idx:    int               = -1   # selected ReplicateSet in panel
        self._rep_hidden:        set               = set()  # indices of hidden rep-sets
        self._well_labels:       Dict[str, str]    = {}   # tok -> custom display label
        self._bar_groups:        List[BarGroup]    = []   # grouping definitions
        self._bar_active_grp:    int               = -1   # index of group being edited
        # Quick replicate arrangement preferences
        self._rep_quick_pair_dir   = "row"   # "row" or "col" — how pairs are formed
        self._rep_quick_iter_order = "row"   # "row" or "col" — iteration direction
        # Quick bar group arrangement preferences
        self._bar_quick_pair_dir   = "row"   # "row" or "col" — how pairs are formed
        self._bar_quick_iter_order = "row"   # "row" or "col" — iteration direction
        self._entry_var     = tk.StringVar(value="50.0")
        self._cdf_xmin_var  = tk.StringVar(value="0")
        self._cdf_xmax_var  = tk.StringVar(value="300")
        self._thr_dragging  = False   # True while the threshold line is being dragged

        # Plate-map well selection
        self._selected_wells: set  = set()   # set of well labels currently selected
        self._tok_to_label:   Dict[str, str] = {}   # e.g. "B03" -> "gfp_measurements_B03"

        # Preview state
        self._fov_tp_extractor = None          # set by _load_path from pipeline_info.json
        self._preview_selected_well: Optional[str] = None  # preview tab single selection
        self._preview_fov_var = tk.StringVar(value="—")     # selected FOV for montage
        self._montage_photos: List[object] = []             # keep PhotoImage refs alive
        self._preview_fov_var = tk.StringVar(value="—")
        self._preview_fluor:   Dict[Tuple[str,str], _ImgRef] = {}
        self._preview_overlay: Dict[Tuple[str,str], _ImgRef] = {}
        self._preview_mask:    Dict[Tuple[str,str], _ImgRef] = {}

        self._build_ui()
        self._apply_theme()

        if data_path is not None:
            # Defer until after mainloop() so the window is mapped and
            # the progress bar can actually render during the load.
            self.after(100, lambda: self._load_path(data_path))

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
        # Topbar
        top = tk.Frame(self, bg=BG_APP, pady=8, padx=14)
        top.pack(side=tk.TOP, fill=tk.X)
        self._dir_label = tk.Label(top, text="No data loaded", font=FM_UI, fg=TXT_MUT, bg=BG_APP)
        self._dir_label.pack(side=tk.LEFT)

        # Single "Open…" button – accepts directory or archive
        ttk.Button(top, text="Open…", command=self._browse,
                   style="PrimaryDark.TButton").pack(side=tk.RIGHT, padx=(6, 0))

        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)

        # Status + log — MUST be packed side=BOTTOM before the expanding
        # paned window so it claims its space first.
        self._build_bottom()

        # ── Horizontal PanedWindow: sidebar | plots ────────────────────────
        self._h_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._h_pane.pack(fill=tk.BOTH, expand=True)

        # Sidebar — contains two swappable panels:
        #   _sidebar_line_frame: well picker (used by Line Graphs tab)
        #   _sidebar_bar_frame:  group picker (used by Bar Plots tab)
        sidebar = tk.Frame(self._h_pane, bg=BG_SIDE, width=340)
        sidebar.pack_propagate(False)
        self._h_pane.add(sidebar, weight=0)

        # Single persistent well picker — shown for Line Graphs and Bar Plots.
        self._sidebar_main_frame = tk.Frame(sidebar, bg=BG_SIDE)
        self._sidebar_main_frame.pack(fill=tk.BOTH, expand=True)

        # Keep _sidebar_line_frame as an alias so nothing else breaks.
        self._sidebar_line_frame = self._sidebar_main_frame

        # Off-screen frame used to build bar-map widgets that are now unused
        # in the sidebar (bar plot uses the unified picker instead).
        self._sidebar_groups_frame = tk.Frame(sidebar, bg=BG_SIDE)
        self._sidebar_bar_frame    = tk.Frame(sidebar, bg=BG_SIDE)

        self._sidebar_preview_frame = tk.Frame(sidebar, bg=BG_SIDE)
        self._sidebar_sample_frame = tk.Frame(sidebar, bg=BG_SIDE)
        self._sidebar_stats_frame = tk.Frame(sidebar, bg=BG_SIDE)
        # Not packed yet — shown only when tab-specific sidebars are active

        self._build_sidebar(self._sidebar_main_frame)
        # Groups panel and preview picker built inside _build_centre.

        # Centre plots
        centre = tk.Frame(self._h_pane, bg=BG_APP)
        self._h_pane.add(centre, weight=3)
        self._build_centre(centre)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        """Build the 8×12 plate-map well selector in the sidebar."""
        tk.Label(parent, text="WELLS", font=FM_BOLD, fg=TXT_MUT,
                 bg=BG_SIDE, pady=6).pack(fill=tk.X, padx=10)

        # ── Row / Col quick-select buttons ────────────────────────────────────
        # Two rows of compact buttons: one per row letter (A-H), one per column.
        rc_frame = tk.Frame(parent, bg=BG_SIDE)
        rc_frame.pack(fill=tk.X, padx=6, pady=(0, 4))
        self._sidebar_rc_frame = rc_frame

        # Row quick-select — grid so buttons scale to available width like the
        # plate map.  uniform="rc_row" forces all 8 columns to equal widths.
        row_frame = tk.Frame(rc_frame, bg=BG_SIDE)
        row_frame.pack(fill=tk.X)
        tk.Label(row_frame, text="Row:", font=FM_TINY, fg=TXT_MUT,
                 bg=BG_SIDE, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 2))
        for ci, r in enumerate(_PLATE_ROWS):
            ttk.Button(
                row_frame,
                text=r,
                style="QuickSelect.TButton",
                command=lambda row=r: self._select_row(row),
                cursor="hand2",
            ).grid(row=0, column=ci + 1, sticky="ew", padx=1)
        row_frame.columnconfigure(0, weight=0)
        for ci in range(1, len(_PLATE_ROWS) + 1):
            row_frame.columnconfigure(ci, weight=1, uniform="rc_row")

        # Col quick-select — same approach; 12 columns need uniform= to keep
        # equal widths on macOS where Tk uses pixel units for button width.
        col_frame = tk.Frame(rc_frame, bg=BG_SIDE)
        col_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(col_frame, text="Col:", font=FM_TINY, fg=TXT_MUT,
                 bg=BG_SIDE, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 2))
        for ci, c in enumerate(_PLATE_COLS):
            ttk.Button(
                col_frame,
                text=c.lstrip("0") or "0",
                style="QuickSelect.TButton",
                command=lambda col=c: self._select_col(col),
                cursor="hand2",
            ).grid(row=0, column=ci + 1, sticky="ew", padx=1)
        col_frame.columnconfigure(0, weight=0)
        for ci in range(1, len(_PLATE_COLS) + 1):
            col_frame.columnconfigure(ci, weight=1, uniform="rc_col")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=6, pady=(4, 4))

        # ── Plate map grid — same styling as the export panel ─────────────────
        map_outer = tk.Frame(parent, bg=BG_SIDE)
        map_outer.pack(fill=tk.X, padx=4)

        self._sidebar_btns: Dict[str, tk.Button] = {}
        self._sidebar_drag_adding   = True    # kept for _select_all/_none compat
        self._sidebar_drag_visited: set = set()
        self._sb_ds: dict = {"adding": True, "visited": set(), "rep_toggled": set()}
        self._bg_ds: dict = {"adding": True, "visited": set(), "rep_toggled": set()}
        build_plate_grid(map_outer, self._sidebar_btns)
        _bind_drag(map_outer, self._sidebar_btns,
                   self._sb_press, self._sb_drag, self._sb_release)

        # ── All / None buttons ────────────────────────────────────────────────
        br = tk.Frame(parent, bg=BG_SIDE)
        br.pack(fill=tk.X, padx=6, pady=(4, 6))
        self._sidebar_allnone_frame = br
        for txt, cmd in (("All", self._select_all), ("None", self._select_none)):
            ttk.Button(br, text=txt, command=cmd,
                       style="PrimaryDark.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        # ── Selected well count label ─────────────────────────────────────────
        self._sel_count_lbl = tk.Label(parent, text="", font=FM_TINY,
                                       fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        self._sel_count_lbl.pack(fill=tk.X, padx=10, pady=(0, 4))

        # ── Group-mode hint: shown instead of well count when groups exist ────
        self._line_group_hint = tk.Label(
            parent,
            text="",
            font=FM_TINY, fg=ACCENT, bg=BG_SIDE,
            anchor="w", wraplength=280, justify=tk.LEFT)
        self._line_group_hint.pack(fill=tk.X, padx=10, pady=(0, 4))

    def _build_centre(self, parent: tk.Frame) -> None:
        from well_viewer.views.centre_view import build_centre as _build_centre_view

        _build_centre_view(self, parent)

    # ── Statistics tab ────────────────────────────────────────────────────────

    def _build_stats_tab(self, parent: tk.Frame) -> None:
        _build_stats_tab_view(self, parent, bg_app=BG_APP, bg_side=BG_SIDE)

    # ── Stats left: group editor ──────────────────────────────────────────────

    def _build_stats_group_editor(self, parent: tk.Frame) -> None:
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
        if grp is None or tok not in self._tok_to_label:
            return
        label = self._tok_to_label[tok]
        rset = next((r for r in self._rep_sets if label in r.wells), None)
        if rset is not None:
            if self._stats_drag_adding:
                if rset not in grp.members:
                    grp.members.append(rset)
            else:
                if rset in grp.members:
                    grp.members.remove(rset)
        else:
            if self._stats_drag_adding:
                if label not in grp.solo_wells:
                    grp.solo_wells.append(label)
            else:
                if label in grp.solo_wells:
                    grp.solo_wells.remove(label)
        self._stats_refresh_single_btn(tok)

    def _stats_refresh_single_btn(self, tok: str) -> None:
        btn = self._stats_map_btns.get(tok)
        if btn is None or tok not in self._tok_to_label:
            return
        label = self._tok_to_label[tok]
        for gi, g in enumerate(self._stats_groups):
            if label in g.wells:
                btn.config(
                    bg=button_bg,
                    fg=button_text,
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )
                return
        btn.config(
            bg=button_bg,
            fg=button_text,
            activebackground=button_bg,
            activeforeground=button_text,
            disabledforeground=button_text_disabled,
        )

    def _stats_refresh_map(self) -> None:
        avail = set(self._tok_to_label.keys())
        tok_color: Dict[str, str] = {}
        for gi, grp in enumerate(self._stats_groups):
            c = WELL_COLORS[gi % len(WELL_COLORS)]
            for w in grp.wells:
                t = _extract_well_token(w) or w
                tok_color.setdefault(t, c)
        active_wells: set = set()
        grp = self._stats_active_group()
        if grp:
            for w in grp.wells:
                active_wells.add(_extract_well_token(w) or w)
        for tok, btn in self._stats_map_btns.items():
            if tok not in avail:
                btn.config(
                    bg=button_bg,
                    fg=button_text_disabled,
                    state=tk.DISABLED,
                    cursor="arrow",
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )
            elif tok in tok_color:
                relief = tk.SUNKEN if tok in active_wells else tk.FLAT
                btn.config(
                    bg=button_bg,
                    fg=button_text,
                    state=tk.NORMAL,
                    relief=relief,
                    cursor="hand2",
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )
            else:
                btn.config(
                    bg=button_bg,
                    fg=button_text,
                    state=tk.NORMAL,
                    relief=tk.FLAT,
                    cursor="hand2",
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )

    def _stats_refresh_group_list(self) -> None:
        for w in self._stats_grp_inner.winfo_children():
            w.destroy()
        if not self._stats_groups:
            tk.Label(self._stats_grp_inner,
                     text="No groups.  Click + Add to create one.",
                     font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE,
                     pady=8).pack(anchor="w", padx=8)
            self._stats_refresh_map()
            return
        for gi, grp in enumerate(self._stats_groups):
            is_sel = (gi == self._stats_active_grp)
            color  = WELL_COLORS[gi % len(WELL_COLORS)]
            bg     = BG_HOVER if is_sel else BG_PANEL
            card   = tk.Frame(self._stats_grp_inner, bg=bg,
                              highlightthickness=1,
                              highlightbackground=ACCENT if is_sel else BORDER)
            card.pack(fill=tk.X, padx=4, pady=2)

            hdr = tk.Frame(card, bg=bg)
            hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
            tk.Label(hdr, text="●", font=FM_BOLD, fg=color,
                     bg=bg).pack(side=tk.LEFT, padx=(0, 4))
            tk.Label(hdr, text=grp.name, font=FM_BOLD, fg=TXT_PRI,
                     bg=bg).pack(side=tk.LEFT)
            n_mem = len(grp.members)
            n_sol = len(grp.solo_wells)
            parts = []
            if n_mem: parts.append(f"{n_mem} set{'s' if n_mem!=1 else ''}")
            if n_sol: parts.append(f"{n_sol} solo well{'s' if n_sol!=1 else ''}")
            if not parts: parts = ["empty"]
            tk.Label(hdr, text=f"  ({', '.join(parts)})",
                     font=FM_TINY, fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)

            bf = tk.Frame(hdr, bg=bg)
            bf.pack(side=tk.RIGHT)
            idx = gi
            tk.Button(bf, text="✕", font=FM_TINY, bg=bg, fg=TXT_MUT,
                      relief=tk.FLAT, padx=4, cursor="hand2",
                      command=lambda i=idx: self._stats_grp_delete(i)
                      ).pack(side=tk.RIGHT)
            tk.Button(bf, text="✎", font=FM_TINY, bg=bg, fg=TXT_MUT,
                      relief=tk.FLAT, padx=4, cursor="hand2",
                      command=lambda i=idx: self._stats_grp_rename(i)
                      ).pack(side=tk.RIGHT)

            card.bind("<Button-1>", lambda _e, i=idx: self._stats_select_grp(i))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda _e, i=idx: self._stats_select_grp(i))

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
        dlg = tk.Toplevel(self)
        dlg.title("Rename group")
        dlg.grab_set()
        dlg.configure(bg=BG_APP)
        tk.Label(dlg, text="Name:", font=FM_TINY, bg=BG_APP,
                 fg=TXT_SEC).pack(padx=12, pady=(10, 2), anchor="w")
        var = tk.StringVar(value=old)
        e = tk.Entry(dlg, textvariable=var, font=FM_TINY,
                     relief=tk.FLAT, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER,
                     width=26)
        e.pack(padx=12, pady=2)
        e.select_range(0, tk.END)
        e.focus_set()
        def _ok():
            v = var.get().strip()
            if v:
                self._stats_groups[idx].name = v
            dlg.destroy()
            self._stats_refresh_group_list()
        e.bind("<Return>", lambda _: _ok())
        _btn_primary(dlg, "OK", _ok, padx=12, pady=4).pack(pady=(6, 10))

    def _stats_grp_clear_all(self) -> None:
        self._stats_groups.clear()
        self._stats_active_grp = -1
        self._stats_refresh_group_list()

    def _stats_sync_from_app(self) -> None:
        self._stats_groups = copy.deepcopy(self._groups_from_rep_sets())
        self._stats_active_grp = 0 if self._stats_groups else -1
        self._stats_refresh_group_list()

    # ── Stats right: test selector + results ─────────────────────────────────

    def _build_stats_results_panel(self, parent: tk.Frame) -> None:
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
        self._stats_tp_cb["values"] = tp_strs or ["—"]
        if tp_strs:
            self._stats_tp_var.set(tp_strs[0])
        else:
            self._stats_tp_var.set("—")

    def _stats_write_result(self, text: str) -> None:
        self._stats_result_text.config(state=tk.NORMAL)
        self._stats_result_text.delete("1.0", tk.END)
        if text:
            self._stats_result_text.insert(tk.END, text)
        self._stats_result_text.config(state=tk.DISABLED)

    def _stats_refresh_colors(self) -> None:
        """Refresh all statistics tab colors when theme changes."""
        from ui.theme import get_color

        # Get current theme colors
        bg_app = get_color("BG_APP")
        bg_side = get_color("BG_SIDE")
        bg_panel = get_color("BG_PANEL")
        txt_pri = get_color("TXT_PRI")
        txt_sec = get_color("TXT_SEC")
        txt_mut = get_color("TXT_MUT")
        border = get_color("BORDER")

        # Update header frame
        if hasattr(self, "_stats_hdr"):
            self._stats_hdr.configure(bg=bg_side)
            self._stats_hdr_label.configure(bg=bg_side, fg=txt_mut)

        # Update control frame
        if hasattr(self, "_stats_ctrl"):
            self._stats_ctrl.configure(bg=bg_app)
            self._stats_test_label.configure(bg=bg_app, fg=txt_sec)
            self._stats_tp_label.configure(bg=bg_app, fg=txt_sec)

        # Update separator
        if hasattr(self, "_stats_sep"):
            self._stats_sep.configure(bg=border)

        # Update figure frame and matplotlib figure
        if hasattr(self, "_stats_fig_frame"):
            self._stats_fig_frame.configure(bg=bg_app)
        if hasattr(self, "_stats_fig"):
            self._stats_fig.set_facecolor(bg_app)

        # Update results frame
        if hasattr(self, "_stats_res_frame"):
            self._stats_res_frame.configure(bg=bg_app)

        # Update results text widget
        if hasattr(self, "_stats_result_text"):
            self._stats_result_text.configure(bg=bg_panel, fg=txt_pri, highlightbackground=border)

        # Redraw the canvas
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

    def _build_preview_picker(self, parent: tk.Frame) -> None:
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
        # Fetch colors dynamically to support theme changes
        from ui.theme import get_color
        _refresh_preview_picker_view(
            self,
            bg_cell=get_color("BG_CELL"),
            txt_mut=get_color("TXT_MUT"),
            txt_pri=get_color("TXT_PRI"),
            accent=get_color("ACCENT"),
            clr_white=get_color("CLR_WHITE"),
            clr_accent_dark=get_color("CLR_ACCENT_DARK"),
            bg_panel=get_color("BG_PANEL"),
            bg_hover=get_color("BG_HOVER"),
            extract_well_token_fn=_extract_well_token,
        )

    # ── Bar-plot grouping panel ───────────────────────────────────────────────

    def _build_bar_group_panel(self, parent: tk.Frame) -> None:
        """
        Left panel of the Bar Plots tab.

        Reuses the export-panel design:
          • Scrollable card list of named groups (+ Add / Rename / Delete)
          • 8×12 plate map for drag-assignment of wells to the active group
          • Each group becomes one bar in the bar plots (mean ± SD/SEM across
            its member wells)

        When no groups are defined the bar plot falls back to one bar per well
        (the original per-well mode).
        """
        # Title row only — Add/Clear/Save/Load removed; groups are now
        # managed exclusively via the bar-plot drag interactions.
        hdr1 = tk.Frame(parent, bg=BG_SIDE, pady=3, padx=8)
        hdr1.pack(fill=tk.X)
        tk.Label(hdr1, text="PLATE MAP", font=FM_BOLD, fg=TXT_MUT,
                 bg=BG_SIDE).pack(side=tk.LEFT)
        tk.Label(hdr1, text="(right-drag to toggle visibility)",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(
                 side=tk.LEFT, padx=(6, 0))

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        # ── Plate map FIRST (top) ─────────────────────────────────────────────
        tk.Label(parent,
                 text="Left-drag: add wells to active replicate set  ·  "
                      "Right-click/drag: toggle group bar-plot visibility",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, pady=3,
                 anchor="w", wraplength=300).pack(fill=tk.X, padx=6)

        self._bar_map_frame = tk.Frame(parent, bg=BG_SIDE)
        self._bar_map_frame.pack(fill=tk.X, padx=4)

        self._bar_map_btns: Dict[str, tk.Button] = {}
        self._bar_drag_adding   = True
        self._bar_drag_visited: set = set()
        build_plate_grid(self._bar_map_frame, self._bar_map_btns)
        _bind_drag(self._bar_map_frame, self._bar_map_btns,
                   self._bg_press, self._bg_drag, self._bg_release)
        # Right-click drag: rubber-band rectangle to toggle group visibility
        _bind_drag(self._bar_map_frame, self._bar_map_btns,
                   self._bg_vis_press, self._bg_vis_drag, self._bg_vis_release,
                   button=3)

        # Rubber-band state — drawn on a transparent canvas overlaid on the
        # plate-map frame.  Using a Canvas avoids the Toplevel z-order and
        # event-capture problems on Windows.
        self._vis_rubber_win:    Optional[tk.Toplevel] = None
        self._vis_rubber_rect:   Optional[int]         = None

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(4, 0))

        # ── Scrollable group card list BELOW the plate map ────────────────────
        sf = tk.Frame(parent, bg=BG_SIDE)
        sf.pack(fill=tk.BOTH, expand=True)
        self._bar_grp_canvas, self._bar_grp_inner = make_scrollable_canvas(
            sf, bg=BG_SIDE)

        # No-groups hint (shown at the bottom of the groups sidebar)
        self._bar_grp_count_lbl = tk.Label(
            parent, text="No groups defined",
            font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        self._bar_grp_count_lbl.pack(fill=tk.X, padx=6, pady=(0, 2))

    def _build_groups_centre(self, parent: tk.Frame) -> None:
        """Centre panel for the Sample Definitions tab (label editor only)."""
        self._build_label_editor(parent)

    # ─────────────────────────────────────────────────────────────────────────
    # Replicate panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_replicate_panel(self, parent: tk.Frame) -> None:
        """Left panel: define named ReplicateSets from the global well pool."""
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="REPLICATE SETS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        _btn_primary(hdr, "+ Add", self._rep_add).pack(side=tk.RIGHT)
        _btn_secondary(hdr, "Clear All", self._rep_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

        # Second row: Quick Replicates dropdowns
        hdr2r = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr2r.pack(fill=tk.X)

        # Pair direction dropdown
        tk.Label(hdr2r, text="Pair:", font=FM_TINY, fg=TXT_PRI,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._rep_quick_pair_dir_var = tk.StringVar(value="Rows (A01+A02)")
        pair_dir_cb = ttk.Combobox(
            hdr2r,
            textvariable=self._rep_quick_pair_dir_var,
            values=["Rows (A01+A02)", "Columns (A01+B01)"],
            state="readonly",
            width=18)
        pair_dir_cb.pack(side=tk.LEFT, padx=(0, 8))

        # Iteration order dropdown
        tk.Label(hdr2r, text="Order:", font=FM_TINY, fg=TXT_PRI,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._rep_quick_iter_order_var = tk.StringVar(value="Across rows")
        iter_order_cb = ttk.Combobox(
            hdr2r,
            textvariable=self._rep_quick_iter_order_var,
            values=["Across rows", "Down columns"],
            state="readonly",
            width=14)
        iter_order_cb.pack(side=tk.LEFT, padx=(0, 4))

        # Apply button on separate row below dropdowns
        btn_row = tk.Frame(parent, bg=BG_SIDE, pady=2, padx=8)
        btn_row.pack(fill=tk.X)
        _btn_primary(btn_row, "Apply Quick Replicates", self._rep_quick_pairs_from_dropdowns).pack(side=tk.LEFT)

        tk.Label(parent,
                 text="Select a set below, then drag wells on the map to add/remove.",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                 wraplength=580, justify=tk.LEFT).pack(
                 fill=tk.X, padx=8, pady=(4, 2))

        # Plate map — shows all rep-set colours; drag edits the selected set
        rep_map_outer = tk.Frame(parent, bg=BG_SIDE)
        rep_map_outer.pack(fill=tk.X, padx=4)
        self._rep_map_btns: Dict[str, tk.Button] = {}
        build_plate_grid(rep_map_outer, self._rep_map_btns)
        _bind_drag(rep_map_outer, self._rep_map_btns,
                   self._rep_map_press, self._rep_map_drag, self._rep_map_release)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(4, 0))

        sf = tk.Frame(parent, bg=BG_APP)
        sf.pack(fill=tk.BOTH, expand=True)
        self._rep_canvas, self._rep_inner = make_scrollable_canvas(sf, bg=BG_APP)

    # ── Replicate-panel plate map ─────────────────────────────────────────────

    def _rep_refresh_map(self) -> None:
        """Recolour the replicate-panel plate map.

        Each defined ReplicateSet gets a distinct colour (WELL_COLORS index).
        The active (selected) set's wells are rendered slightly brighter.
        Unassigned loaded wells are shown in a neutral available colour.
        No active set → all sets shown in colour, map not drag-editable (greyed hint).
        """
        from ui.theme import get_color

        if not hasattr(self, "_rep_map_btns"):
            return

        # Get current colors from theme
        button_bg = get_color("button_bg")
        button_text = get_color("button_text")
        button_text_disabled = get_color("button_text_disabled")

        # Build tok -> (color, is_active_set)
        tok_color: Dict[str, str] = {}
        tok_active: Dict[str, bool] = {}
        for si, rset in enumerate(self._rep_sets):
            c = WELL_COLORS[si % len(WELL_COLORS)]
            for lbl in rset.wells:
                tok = _extract_well_token(lbl) or lbl
                tok_color[tok] = c
                tok_active[tok] = (si == self._active_rep_idx)

        has_active = 0 <= self._active_rep_idx < len(self._rep_sets)
        active_color = (WELL_COLORS[self._active_rep_idx % len(WELL_COLORS)]
                        if has_active else ACCENT)

        for tok, btn in self._rep_map_btns.items():
            lbl = self._tok_to_label.get(tok)
            if lbl is None:
                btn.config(
                    bg=button_bg,
                    fg=button_text_disabled,
                    state=tk.DISABLED,
                    cursor="arrow",
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )
            elif tok in tok_color:
                act = tok_active.get(tok, False)
                # Active-set wells: solid bright colour; other sets: dimmed (70 % alpha via lighter shade)
                grp_color = tok_color[tok]
                btn.config(
                    bg=grp_color,
                    fg="white",
                    state=tk.NORMAL,
                    cursor="hand2",
                    relief=tk.SUNKEN if act else tk.FLAT,
                    activebackground=self._mute_color(grp_color, 0.3) if act else grp_color,
                    activeforeground="white",
                    disabledforeground=button_text_disabled,
                )
            else:
                # Unassigned well — editable if a set is selected
                if has_active:
                    btn.config(
                        bg=button_bg,
                        fg=button_text,
                        state=tk.NORMAL,
                        cursor="hand2",
                        relief=tk.FLAT,
                        activebackground=button_bg,
                        activeforeground=button_text,
                        disabledforeground=button_text_disabled,
                    )
                else:
                    btn.config(
                        bg=button_bg,
                        fg=button_text,
                        state=tk.NORMAL,
                        cursor="arrow",
                        relief=tk.FLAT,
                        activebackground=button_bg,
                        activeforeground=button_text,
                        disabledforeground=button_text_disabled,
                    )

    def _rep_map_tok_at(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        return _gc_rep_map_tok_at(self, event)

    def _rep_map_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        _gc_rep_map_press(self, event)

    def _rep_map_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        _gc_rep_map_drag(self, event)

    def _rep_map_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        _gc_rep_map_release(self, _event)

    def _rep_map_apply(self, tok: str) -> None:
        _gc_rep_map_apply(self, tok)

    def _rep_refresh_map_single(self, tok: str) -> None:
        """Update a single rep-map button (cheap mid-drag feedback)."""
        if not hasattr(self, "_rep_map_btns"):
            return
        btn = self._rep_map_btns.get(tok)
        if btn is None:
            return
        lbl = self._tok_to_label.get(tok)
        if lbl is None:
            return
        # Find which set owns this well now
        for si, rset in enumerate(self._rep_sets):
            if lbl in rset.wells:
                act = (si == self._active_rep_idx)
                btn.config(
                    bg=button_bg,
                    fg=button_text,
                    state=tk.NORMAL,
                    cursor="hand2",
                    relief=tk.SUNKEN if act else tk.FLAT,
                    activebackground=button_bg,
                    activeforeground=button_text,
                    disabledforeground=button_text_disabled,
                )
                return
        # Unassigned
        has_active = 0 <= self._active_rep_idx < len(self._rep_sets)
        btn.config(
            bg=button_bg,
            fg=button_text,
            state=tk.NORMAL,
            cursor="hand2" if has_active else "arrow",
            relief=tk.FLAT,
            activebackground=button_bg,
            activeforeground=button_text,
            disabledforeground=button_text_disabled,
        )

    def _rep_panel_refresh(self) -> None:
        from well_viewer.grouping_view import rep_panel_refresh as _rep_panel_refresh_view

        _rep_panel_refresh_view(self)

    def _rep_select(self, idx: int) -> None:
        self._active_rep_idx = idx
        self._groups_centre_refresh()   # card list
        self._rep_refresh_map()         # plate map: highlight selected set

    def _rep_add(self) -> None:
        """Open dialog to create a new named ReplicateSet."""
        dlg = tk.Toplevel(self)
        dlg.title("New Replicate Set")
        dlg.configure(bg=BG_APP)
        dlg.grab_set()
        dlg.resizable(False, False)

        name_var = tk.StringVar(value=f"Rep {len(self._rep_sets)+1}")
        tk.Label(dlg, text="Name:", font=FM_BOLD, fg=TXT_SEC,
                 bg=BG_APP).pack(padx=16, pady=(12, 2), anchor="w")
        tk.Entry(dlg, textvariable=name_var, font=FM_UI,
                 bg=BG_PANEL, fg=TXT_PRI, relief=tk.FLAT,
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER, width=24).pack(padx=16, anchor="w")

        tk.Label(dlg, text="Select wells:", font=FM_BOLD, fg=TXT_SEC,
                 bg=BG_APP).pack(padx=16, pady=(10, 2), anchor="w")

        available = sorted(self._well_paths.keys(),
                           key=lambda l: self._parse_rc(l))
        lb_fr = tk.Frame(dlg, bg=BG_APP)
        lb_fr.pack(fill=tk.BOTH, expand=True, padx=16)
        vsb = tk.Scrollbar(lb_fr, relief=tk.FLAT, width=7,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(lb_fr, selectmode=tk.MULTIPLE,
                        bg=BG_PANEL, fg=TXT_PRI, font=FM_MONO,
                        selectbackground=ACCENT, selectforeground=CLR_WHITE,
                        activestyle="none", relief=tk.FLAT,
                        highlightthickness=1, highlightcolor=ACCENT,
                        highlightbackground=BORDER,
                        yscrollcommand=vsb.set, exportselection=False,
                        height=min(len(available), 12))
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=lb.yview)
        for w in available:
            lb.insert(tk.END, _extract_well_token(w) or w)

        btn_row = tk.Frame(dlg, bg=BG_APP)
        btn_row.pack(fill=tk.X, padx=16, pady=(8, 12))

        def _ok():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("No wells", "Select at least one well.",
                                       parent=dlg)
                return
            wells = [available[i] for i in sel]
            name  = name_var.get().strip() or f"Rep {len(self._rep_sets)+1}"
            self._rep_sets.append(ReplicateSet(name, wells))
            self._active_rep_idx = len(self._rep_sets) - 1
            dlg.destroy()
            self._rebuild_all()

        _btn_primary(btn_row, "Create", _ok, padx=12, pady=4).pack(side=tk.LEFT)
        _btn_secondary(btn_row, "Cancel", dlg.destroy, padx=8, pady=4).pack(side=tk.LEFT, padx=(6, 0))

    def _rep_rename(self, idx: int) -> None:
        if not (0 <= idx < len(self._rep_sets)):
            return
        name = ask_name_dialog(self, default=self._rep_sets[idx].name)
        if name:
            self._rep_sets[idx].name = name
            self._rebuild_all()

    def _rep_edit_wells(self, idx: int) -> None:
        """Re-open well-selection dialog for an existing ReplicateSet."""
        if not (0 <= idx < len(self._rep_sets)):
            return
        rset = self._rep_sets[idx]
        available = sorted(self._well_paths.keys(), key=lambda l: self._parse_rc(l))

        dlg = tk.Toplevel(self)
        dlg.title(f"Edit wells — {rset.name}")
        dlg.configure(bg=BG_APP)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(dlg, text=f"Select wells for \"{rset.name}\":",
                 font=FM_BOLD, fg=TXT_SEC, bg=BG_APP
                 ).pack(padx=16, pady=(12, 2), anchor="w")

        lb_fr = tk.Frame(dlg, bg=BG_APP)
        lb_fr.pack(fill=tk.BOTH, expand=True, padx=16)
        vsb = tk.Scrollbar(lb_fr, relief=tk.FLAT, width=7,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(lb_fr, selectmode=tk.MULTIPLE,
                        bg=BG_PANEL, fg=TXT_PRI, font=FM_MONO,
                        selectbackground=ACCENT, selectforeground=CLR_WHITE,
                        activestyle="none", relief=tk.FLAT,
                        highlightthickness=1, highlightcolor=ACCENT,
                        highlightbackground=BORDER,
                        yscrollcommand=vsb.set, exportselection=False,
                        height=min(len(available), 12))
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=lb.yview)
        for i, w in enumerate(available):
            lb.insert(tk.END, _extract_well_token(w) or w)
            if w in rset.wells:
                lb.selection_set(i)

        btn_row = tk.Frame(dlg, bg=BG_APP)
        btn_row.pack(fill=tk.X, padx=16, pady=(8, 12))

        def _ok():
            sel = lb.curselection()
            rset.wells = [available[i] for i in sel]
            dlg.destroy()
            self._rebuild_all()

        _btn_primary(btn_row, "Save", _ok, padx=12, pady=4).pack(side=tk.LEFT)
        _btn_secondary(btn_row, "Cancel", dlg.destroy, padx=8, pady=4).pack(side=tk.LEFT, padx=(6, 0))

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
        if messagebox.askyesno("Clear all replicate sets?",
                               f"Remove all {len(self._rep_sets)} set(s)?\n"
                               "Groups referencing them will also lose those members.",
                               parent=self):
            for grp in self._bar_groups:
                grp.members.clear()
            self._rep_sets.clear()
            self._active_rep_idx = -1
            self._rep_hidden.clear()
            self._rebuild_all()

    # ─────────────────────────────────────────────────────────────────────────
    # Group definition panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_group_def_panel(self, parent: tk.Frame) -> None:
        """Right panel: combine ReplicateSets into BarGroups for plotting."""
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="GROUPS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        _btn_primary(hdr, "+ Add", self._grp_add).pack(side=tk.RIGHT)
        _btn_secondary(hdr, "Clear All", self._grp_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

        # Second row: Quick Groups dropdowns (full setup: replicates + groups)
        hdr2g = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr2g.pack(fill=tk.X)

        # Pair direction dropdown
        tk.Label(hdr2g, text="Pair:", font=FM_TINY, fg=TXT_PRI,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._bar_quick_pair_dir_var = tk.StringVar(value="Rows (A01+A02)")
        pair_dir_cb_bar = ttk.Combobox(
            hdr2g,
            textvariable=self._bar_quick_pair_dir_var,
            values=["Rows (A01+A02)", "Columns (A01+B01)"],
            state="readonly",
            width=18)
        pair_dir_cb_bar.pack(side=tk.LEFT, padx=(0, 8))

        # Iteration order dropdown
        tk.Label(hdr2g, text="Order:", font=FM_TINY, fg=TXT_PRI,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._bar_quick_iter_order_var = tk.StringVar(value="Across rows")
        iter_order_cb_bar = ttk.Combobox(
            hdr2g,
            textvariable=self._bar_quick_iter_order_var,
            values=["Across rows", "Down columns"],
            state="readonly",
            width=14)
        iter_order_cb_bar.pack(side=tk.LEFT, padx=(0, 4))

        # Apply button on separate row below dropdowns
        btn_row_bar = tk.Frame(parent, bg=BG_SIDE, pady=2, padx=8)
        btn_row_bar.pack(fill=tk.X)
        _btn_primary(btn_row_bar, "Apply Quick Groups", self._bar_quick_groups_from_dropdowns).pack(side=tk.LEFT, padx=(0, 4))
        _btn_secondary(btn_row_bar, "Save…", self._bar_save_groups).pack(side=tk.LEFT, padx=(0, 2))
        _btn_secondary(btn_row_bar, "Load…", self._bar_load_groups).pack(side=tk.LEFT, padx=(0, 2))

        tk.Label(parent,
                 text="Each group produces one bar/line on the plot. "
                      "Add replicate sets or individual wells to a group.",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                 wraplength=280, justify=tk.LEFT).pack(
                 fill=tk.X, padx=8, pady=(4, 2))

        sf = tk.Frame(parent, bg=BG_APP)
        sf.pack(fill=tk.BOTH, expand=True)
        self._grp_canvas, self._grp_inner = make_scrollable_canvas(sf, bg=BG_APP)

    def _grp_panel_refresh(self) -> None:
        """Rebuild the group card list."""
        if not hasattr(self, "_grp_inner"):
            return
        for w in self._grp_inner.winfo_children():
            w.destroy()

        if not self._bar_groups:
            tk.Label(self._grp_inner,
                     text="No groups defined.\nClick + Add to create one.",
                     font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                     justify=tk.LEFT).pack(anchor="w", padx=8, pady=8)
            return

        for gi, grp in enumerate(self._bar_groups):
            is_sel = (gi == self._bar_active_grp)
            color  = WELL_COLORS[gi % len(WELL_COLORS)]
            dot_c  = CLR_MUTED_DISABLED if grp.hidden else color
            bg     = BG_HOVER if is_sel else BG_PANEL

            card = tk.Frame(self._grp_inner, bg=bg,
                            highlightthickness=1,
                            highlightbackground=ACCENT if is_sel else BORDER)
            card.pack(fill=tk.X, padx=4, pady=2)

            hdr = tk.Frame(card, bg=bg)
            hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
            tk.Label(hdr, text="●", font=FM_BOLD, fg=dot_c,
                     bg=bg).pack(side=tk.LEFT, padx=(0, 4))
            name_fg = TXT_MUT if grp.hidden else TXT_PRI
            tk.Label(hdr, text=grp.name, font=FM_BOLD,
                     fg=name_fg, bg=bg).pack(side=tk.LEFT)
            if grp.hidden:
                tk.Label(hdr, text="[hidden]", font=FM_TINY,
                         fg=TXT_MUT, bg=bg).pack(side=tk.LEFT, padx=(4, 0))

            n_sets  = len(grp.members)
            n_wells = len(grp.wells)
            tk.Label(hdr,
                     text=f"  {n_sets} set{'s' if n_sets!=1 else ''}  ·  "
                          f"{n_wells} well{'s' if n_wells!=1 else ''}",
                     font=FM_TINY, fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)

            bf = tk.Frame(hdr, bg=bg)
            bf.pack(side=tk.RIGHT)
            vis_txt = "Show" if grp.hidden else "Hide"
            vis_bg  = BG_CELL if grp.hidden else CLR_WARN_BG
            vis_fg  = CLR_SUCCESS if grp.hidden else CLR_WARN_TEXT
            tk.Button(bf, text=vis_txt,
                      command=lambda i=gi: self._grp_toggle_visibility(i),
                      font=FM_TINY, bg=vis_bg, fg=vis_fg,
                      relief=tk.FLAT, padx=4, cursor="hand2",
                      activebackground=BG_HOVER).pack(side=tk.LEFT, padx=1)
            _btn_card(bf, "Rename", lambda i=gi: self._grp_rename(i)).pack(side=tk.LEFT, padx=1)
            _btn_danger(bf, "✕", lambda i=gi: self._grp_delete(i)).pack(side=tk.LEFT, padx=1)

            # Members: replicate sets
            if grp.members or grp.solo_wells:
                mem_frame = tk.Frame(card, bg=bg)
                mem_frame.pack(fill=tk.X, padx=6, pady=(2, 2))
                for rset in grp.members:
                    mrow = tk.Frame(mem_frame, bg=bg)
                    mrow.pack(fill=tk.X, pady=1)
                    tk.Label(mrow, text=f"[{rset.name}]", font=FM_TINY,
                             fg=dot_c, bg=bg, padx=2).pack(side=tk.LEFT)
                    for w in rset.wells:
                        tok = _extract_well_token(w) or w
                        tk.Label(mrow, text=tok, font=FM_TINY,
                                 bg=dot_c, fg=CLR_WHITE,
                                 padx=3, pady=1).pack(side=tk.LEFT, padx=(0, 2))
                    if is_sel:
                        _btn_danger(mrow, "−", lambda g=gi, r=rset: self._grp_remove_member(g, r),
                                    padx=3).pack(side=tk.LEFT, padx=(4, 0))
                for w in grp.solo_wells:
                    tok = _extract_well_token(w) or w
                    srow = tk.Frame(mem_frame, bg=bg)
                    srow.pack(fill=tk.X, pady=1)
                    tk.Label(srow, text=f"[solo] {tok}", font=FM_TINY,
                             fg=dot_c, bg=bg).pack(side=tk.LEFT)
                    if is_sel:
                        _btn_danger(srow, "−", lambda g=gi, wl=w: self._grp_remove_solo(g, wl),
                                    padx=3).pack(side=tk.LEFT, padx=(4, 0))
            else:
                tk.Label(card, text="Empty — add replicate sets or wells below",
                         font=FM_TINY, fg=TXT_MUT, bg=bg,
                         padx=6).pack(anchor="w", padx=6, pady=(0, 2))

            # Active group: add replicate sets and/or individual wells
            if is_sel:
                # Row 1 — add replicate sets
                act_rep = tk.Frame(card, bg=bg)
                act_rep.pack(fill=tk.X, padx=6, pady=(2, 0))
                if self._rep_sets:
                    tk.Label(act_rep, text="+ Set:", font=FM_TINY,
                             fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)
                    for rset in self._rep_sets:
                        if rset not in grp.members:
                            _btn_card(act_rep, rset.name,
                                      lambda r=rset, g=gi: self._grp_add_member(g, r)
                                      ).pack(side=tk.LEFT, padx=2)
                else:
                    tk.Label(act_rep,
                             text="(No replicate sets — define them in the left panel)",
                             font=FM_TINY, fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)

                # Row 2 — add individual wells not already in the group
                assigned_wells = set(grp.wells)
                unassigned = [lbl for lbl in sorted(
                                  self._well_paths.keys(),
                                  key=lambda l: self._parse_rc(l))
                              if lbl not in assigned_wells]
                if unassigned:
                    act_well = tk.Frame(card, bg=bg)
                    act_well.pack(fill=tk.X, padx=6, pady=(2, 4))
                    tk.Label(act_well, text="+ Well:", font=FM_TINY,
                             fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)
                    for lbl in unassigned:
                        tok = _extract_well_token(lbl) or lbl
                        _btn_card(act_well, tok,
                                  lambda wl=lbl, g=gi: self._grp_add_solo_well(g, wl)
                                  ).pack(side=tk.LEFT, padx=2)
                else:
                    tk.Frame(card, bg=bg, height=4).pack()  # spacing

            sel_cb = lambda _e, i=gi: self._grp_select(i)
            for widget in [card, hdr, bf]:
                widget.bind("<Button-1>", sel_cb)

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

    def _build_label_editor(self, parent: tk.Frame) -> None:
        """Right panel: assign custom display labels to wells."""
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="WELL LABELS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        _btn_secondary(hdr, "Clear All", self._labels_clear_all).pack(side=tk.RIGHT)

        tk.Label(parent,
                 text="Custom names used in figure legends and axis labels only. "
                      "Leave blank to use the well token (e.g. A01).",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                 wraplength=320, justify=tk.LEFT).pack(
                 fill=tk.X, padx=8, pady=(4, 2))

        # Scrollable list of name → entry rows
        sf = tk.Frame(parent, bg=BG_APP)
        sf.pack(fill=tk.BOTH, expand=True)
        self._lbl_canvas, self._lbl_inner = make_scrollable_canvas(sf, bg=BG_APP)

    def _label_panel_refresh(self) -> None:
        """Rebuild the well-label entry rows."""
        if not hasattr(self, "_lbl_inner"):
            return
        for w in self._lbl_inner.winfo_children():
            w.destroy()

        wells = sorted(self._well_paths.keys(),
                       key=lambda l: self._parse_rc(l))
        if not wells:
            tk.Label(self._lbl_inner,
                     text="No wells loaded yet.",
                     font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                     justify=tk.LEFT).pack(anchor="w", padx=8, pady=8)
            return

        # Header row
        hdr_row = tk.Frame(self._lbl_inner, bg=BG_APP)
        hdr_row.pack(fill=tk.X, padx=6, pady=(4, 2))
        tk.Label(hdr_row, text="Well", font=FM_BOLD, fg=TXT_MUT,
                 bg=BG_APP, width=6, anchor="w").pack(side=tk.LEFT)
        tk.Label(hdr_row, text="Display label (blank = use well token)",
                 font=FM_BOLD, fg=TXT_MUT, bg=BG_APP,
                 anchor="w").pack(side=tk.LEFT, padx=(4, 0))

        tk.Frame(self._lbl_inner, bg=BORDER, height=1).pack(
            fill=tk.X, padx=6, pady=(0, 2))

        for lbl in wells:
            tok = _extract_well_token(lbl) or lbl
            row = tk.Frame(self._lbl_inner, bg=BG_APP)
            row.pack(fill=tk.X, padx=6, pady=1)

            tk.Label(row, text=tok, font=FM_MONO, fg=TXT_SEC,
                     bg=BG_APP, width=6, anchor="w").pack(side=tk.LEFT)

            var = tk.StringVar(value=self._well_labels.get(tok, ""))
            e = tk.Entry(row, textvariable=var, font=FM_TINY,
                         fg=TXT_PRI, bg=BG_PANEL, relief=tk.FLAT,
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER, width=24)
            e.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)

            def _on_change(t=tok, v=var):
                val = v.get().strip()
                if val:
                    self._well_labels[t] = val
                else:
                    self._well_labels.pop(t, None)
                # Invalidate stats cache so legend labels refresh on next draw
                self._invalidate_stats_cache()

            var.trace_add("write", lambda *_, t=tok, v=var: _on_change(t, v))

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
                    self._notebook.tab(self._notebook.select(), "text")
                    == "Sample Definitions")
            except Exception:
                pass

        if tab_visible:
            self._rep_panel_refresh()
            self._grp_panel_refresh()
            self._label_panel_refresh()
        self._rep_refresh_map()

    def _build_bar_perwell_strip(self, parent: tk.Frame) -> None:
        """
        Thin bar-specific sidebar strip shown only when Bar Plots tab is active.
        Contains the All/None per-well selection buttons that are irrelevant
        when the Groups tab or Batch Export is active.
        """
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)
        lbl = tk.Label(parent,
                       text="Per-well selection (fallback when no groups)",
                       font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        lbl.pack(fill=tk.X, padx=6, pady=(3, 1))
        bar_br = tk.Frame(parent, bg=BG_SIDE)
        bar_br.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Button(bar_br, text="All", command=self._bar_select_all,
                   style="PrimaryDark.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(bar_br, text="None", command=self._bar_select_none,
                   style="PrimaryDark.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True)

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
        self.after(0, self._bar_rebuild_groups_ui_now)

    def _bar_rebuild_groups_ui_now(self) -> None:
        """
        Synchronous card-list rebuild + plate-map recolour — no plot redraws.

        Call _bar_rebuild_groups() instead when plot data has actually changed.
        """
        self._grp_ui_pending = False
        for w in self._bar_grp_inner.winfo_children():
            w.destroy()

        for idx, grp in enumerate(self._bar_groups):
            self._build_bar_group_row(idx, grp)
        self._update_bar_group_count_label()

        self._bar_refresh_map()

    def _update_bar_group_count_label(self) -> None:
        n_grps = len(self._bar_groups)
        n_vis = sum(1 for g in self._bar_groups if not g.hidden)
        n_hid = n_grps - n_vis
        if not hasattr(self, "_bar_grp_count_lbl"):
            return
        if n_grps == 0:
            txt = "No groups defined"
        elif n_hid == 0:
            txt = f"{n_grps} group(s)  ·  all visible in bar plot"
        else:
            txt = f"{n_vis}/{n_grps} visible in bar plot  ·  {n_hid} hidden"
        self._bar_grp_count_lbl.config(text=txt)

    def _build_bar_group_row(self, idx: int, grp: "BarGroup") -> None:
        is_active = idx == self._bar_active_grp
        bg = BG_HOVER if is_active else BG_PANEL
        row = tk.Frame(
            self._bar_grp_inner,
            bg=bg,
            highlightthickness=1,
            highlightbackground=ACCENT if is_active else BORDER,
        )
        row.pack(fill=tk.X, padx=4, pady=2)

        header, bind_widgets = self._build_bar_group_header(row, idx, grp, bg)
        chip_widgets = self._build_bar_group_chip_rows(row, idx, grp, bg, is_active)
        action_widgets = self._build_bar_group_action_row(row, idx, bg, is_active)
        select_cb = lambda _e, i=idx: self._bar_select_group(i)
        for widget in bind_widgets + chip_widgets + action_widgets:
            widget.bind("<Button-1>", select_cb)

    def _build_bar_group_header(self, row, idx: int, grp: "BarGroup", bg: str) -> tuple[tk.Frame, list]:
        hdr = tk.Frame(row, bg=bg)
        hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
        color = WELL_COLORS[idx % len(WELL_COLORS)]
        dot_color = CLR_MUTED_DISABLED if grp.hidden else color
        name_fg = TXT_MUT if grp.hidden else TXT_PRI
        dot_lbl = tk.Label(hdr, text="●", font=FM_BOLD, fg=dot_color, bg=bg)
        dot_lbl.pack(side=tk.LEFT, padx=(0, 4))
        name_lbl = tk.Label(hdr, text=grp.name, font=FM_BOLD, fg=name_fg, bg=bg)
        name_lbl.pack(side=tk.LEFT)
        hid_lbl = None
        if grp.hidden:
            hid_lbl = tk.Label(hdr, text="[hidden]", font=FM_TINY, fg=TXT_MUT, bg=bg)
            hid_lbl.pack(side=tk.LEFT, padx=(4, 0))

        n_rep = len(grp.replicates) if grp.replicates else len(grp.wells)
        n_well = len(grp.wells)
        count_lbl = tk.Label(
            hdr,
            text=f"({n_rep} replicate set{'s' if n_rep!=1 else ''}  ·  {n_well} well{'s' if n_well!=1 else ''})",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=bg,
        )
        count_lbl.pack(side=tk.LEFT, padx=(4, 0))

        bf = tk.Frame(hdr, bg=bg)
        bf.pack(side=tk.RIGHT)

        def _cmd(action, i=idx):
            self._bar_active_grp = i
            action(i)

        vis_txt = "Show" if grp.hidden else "Hide"
        vis_bg = BG_CELL if grp.hidden else CLR_WARN_BG
        vis_fg = CLR_SUCCESS if grp.hidden else CLR_WARN_TEXT
        tk.Button(
            bf,
            text=vis_txt,
            command=lambda i=idx: _cmd(self._bar_toggle_group_visibility, i),
            font=FM_TINY,
            bg=vis_bg,
            fg=vis_fg,
            relief=tk.FLAT,
            padx=4,
            cursor="hand2",
            activebackground=BG_HOVER,
        ).pack(side=tk.LEFT, padx=1)
        tk.Button(
            bf,
            text="Rename",
            command=lambda i=idx: _cmd(self._bar_rename_group, i),
            font=FM_TINY,
            bg=BG_CELL,
            fg=TXT_SEC,
            relief=tk.FLAT,
            padx=4,
            cursor="hand2",
            activebackground=BG_HOVER,
        ).pack(side=tk.LEFT, padx=1)
        tk.Button(
            bf,
            text="Clear",
            command=lambda i=idx: _cmd(self._bar_clear_group, i),
            font=FM_TINY,
            bg=BG_CELL,
            fg=TXT_SEC,
            relief=tk.FLAT,
            padx=4,
            cursor="hand2",
            activebackground=BG_HOVER,
        ).pack(side=tk.LEFT, padx=1)
        tk.Button(
            bf,
            text="✕",
            command=lambda i=idx: _cmd(self._bar_remove_group, i),
            font=FM_TINY,
            bg=CLR_DANGER_BG,
            fg=CLR_DANGER,
            relief=tk.FLAT,
            padx=4,
            cursor="hand2",
            activebackground=CLR_DANGER_HOVER,
        ).pack(side=tk.LEFT, padx=1)
        return hdr, [row, hdr, bf, dot_lbl, name_lbl, count_lbl] + ([hid_lbl] if hid_lbl else [])

    def _build_bar_group_chip_rows(self, row, idx: int, grp: "BarGroup", bg: str, is_active: bool) -> list:
        color = WELL_COLORS[idx % len(WELL_COLORS)]
        chip_color = CLR_MUTED_DISABLED if grp.hidden else color
        chip_widgets: list = []
        if grp.replicates:
            rep_frame = tk.Frame(row, bg=bg)
            rep_frame.pack(fill=tk.X, padx=6, pady=(2, 0))
            chip_widgets.append(rep_frame)
            for si, rset in enumerate(grp.replicates):
                srow = tk.Frame(rep_frame, bg=bg)
                srow.pack(fill=tk.X, pady=(2, 0))
                chip_widgets.append(srow)
                bracket = tk.Label(srow, text=f"R{si+1}:", font=FM_TINY, fg=color, bg=bg, padx=2)
                bracket.pack(side=tk.LEFT)
                chip_widgets.append(bracket)
                for w in rset:
                    tok = _extract_well_token(w) or w
                    wl = tk.Label(srow, text=tok, font=FM_TINY, bg=chip_color, fg=CLR_WHITE, padx=3, pady=1)
                    wl.pack(side=tk.LEFT, padx=(0, 2))
                    chip_widgets.append(wl)
                if is_active:
                    rm_btn = tk.Button(
                        srow,
                        text="✕",
                        command=lambda i=idx, s=si: self._bar_remove_replicate_set(i, s),
                        font=FM_TINY,
                        bg=CLR_DANGER_BG,
                        fg=CLR_DANGER,
                        relief=tk.FLAT,
                        padx=3,
                        cursor="hand2",
                        activebackground=CLR_DANGER_HOVER,
                    )
                    rm_btn.pack(side=tk.LEFT, padx=(2, 0))
                    chip_widgets.append(rm_btn)
            assigned = {w for rs in grp.replicates for w in rs}
            singles = [w for w in grp.wells if w not in assigned]
            if singles:
                singles_row = tk.Frame(rep_frame, bg=bg)
                singles_row.pack(fill=tk.X, pady=(2, 0))
                chip_widgets.append(singles_row)
                tk.Label(singles_row, text="solo:", font=FM_TINY, fg=TXT_MUT, bg=bg, padx=2).pack(side=tk.LEFT)
                for w in singles:
                    tok = _extract_well_token(w) or w
                    wl = tk.Label(
                        singles_row,
                        text=tok,
                        font=FM_TINY,
                        bg=CLR_MUTED_DISABLED,
                        fg=CLR_WHITE,
                        padx=3,
                        pady=1,
                    )
                    wl.pack(side=tk.LEFT, padx=(0, 2))
                    chip_widgets.append(wl)
        elif grp.wells:
            chips = tk.Frame(row, bg=bg)
            chips.pack(fill=tk.X, padx=6, pady=(2, 0))
            chip_widgets.append(chips)
            for lbl in grp.wells:
                tok = _extract_well_token(lbl) or lbl
                cl = tk.Label(chips, text=tok, font=FM_TINY, bg=chip_color, fg=CLR_WHITE, padx=4, pady=1)
                cl.pack(side=tk.LEFT, padx=(0, 2), pady=1)
                chip_widgets.append(cl)
        else:
            empty_lbl = tk.Label(
                row,
                text="No wells — assign replicates from the map",
                font=FM_TINY,
                fg=TXT_MUT,
                bg=bg,
                padx=6,
            )
            empty_lbl.pack(anchor="w", padx=6, pady=(0, 4))
            chip_widgets.append(empty_lbl)
        return chip_widgets

    def _build_bar_group_action_row(self, row, idx: int, bg: str, is_active: bool) -> list:
        if not is_active:
            return []
        act_frame = tk.Frame(row, bg=bg)
        act_frame.pack(fill=tk.X, padx=6, pady=(4, 4))
        tk.Button(
            act_frame,
            text="+ Add replicate set",
            command=lambda i=idx: self._bar_add_replicate_set(i),
            font=FM_TINY,
            bg=BG_CELL,
            fg=TXT_SEC,
            relief=tk.FLAT,
            padx=5,
            cursor="hand2",
            activebackground=BG_HOVER,
        ).pack(side=tk.LEFT)
        tk.Button(
            act_frame,
            text="Clear replicates",
            command=lambda i=idx: self._bar_clear_replicates(i),
            font=FM_TINY,
            bg=BG_CELL,
            fg=TXT_SEC,
            relief=tk.FLAT,
            padx=5,
            cursor="hand2",
            activebackground=BG_HOVER,
        ).pack(side=tk.LEFT, padx=(4, 0))
        return [act_frame]

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
                tab = self._notebook.tab(self._notebook.select(), "text")
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
                tab = self._notebook.tab(self._notebook.select(), "text")
            except Exception:
                tab = ""
            if tab == "Line Graphs":
                self._show_line_sidebar()

    # ── Group management ──────────────────────────────────────────────────────

    def _bar_add_group(self) -> None:
        name = ask_name_dialog(self, default=f"Group {len(self._bar_groups) + 1}")
        if name is None:
            return
        self._bar_groups.append(BarGroup(name, replicates=[]))
        self._bar_active_grp = len(self._bar_groups) - 1
        self._bar_active_rep  = -1
        self._bar_rebuild_groups()

    def _bar_clear_all_groups(self) -> None:
        """Remove all bar groups after confirmation."""
        if not self._bar_groups:
            return
        if messagebox.askyesno("Clear all groups?",
                               f"Remove all {len(self._bar_groups)} group(s)?",
                               parent=self):
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
        name = ask_name_dialog(self, default=self._bar_groups[idx].name)
        if name is None:
            return
        self._bar_groups[idx].name = name
        self._bar_rebuild_groups()

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
            messagebox.showinfo("All assigned",
                                "All loaded wells are already in a replicate set.",
                                parent=self)
            return

        dlg = tk.Toplevel(self)
        dlg.title("New Replicate Set")
        dlg.configure(bg=BG_APP)
        dlg.grab_set()
        dlg.resizable(False, False)

        name_var = tk.StringVar(value=f"R{len(grp.replicates)+1}")
        tk.Label(dlg, text="Replicate set name:", font=FM_BOLD,
                 fg=TXT_SEC, bg=BG_APP).pack(padx=16, pady=(12, 2), anchor="w")
        tk.Entry(dlg, textvariable=name_var, font=FM_UI,
                 bg=BG_PANEL, fg=TXT_PRI, relief=tk.FLAT,
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER, width=24).pack(padx=16, anchor="w")

        tk.Label(dlg, text="Select wells in this replicate set:",
                 font=FM_BOLD, fg=TXT_SEC, bg=BG_APP).pack(
                 padx=16, pady=(10, 2), anchor="w")

        lb_frame = tk.Frame(dlg, bg=BG_APP)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=16)
        vsb = tk.Scrollbar(lb_frame, relief=tk.FLAT, width=7,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(lb_frame, selectmode=tk.MULTIPLE,
                        bg=BG_PANEL, fg=TXT_PRI, font=FM_MONO,
                        selectbackground=ACCENT, selectforeground=CLR_WHITE,
                        activestyle="none", relief=tk.FLAT,
                        highlightthickness=1, highlightcolor=ACCENT,
                        highlightbackground=BORDER,
                        yscrollcommand=vsb.set, exportselection=False,
                        height=min(len(available), 10))
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=lb.yview)
        for w in sorted(available, key=lambda l: self._parse_rc(l)):
            lb.insert(tk.END, _extract_well_token(w) or w)

        btn_row = tk.Frame(dlg, bg=BG_APP)
        btn_row.pack(fill=tk.X, padx=16, pady=(8, 12))

        def _ok():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("No wells selected",
                                       "Select at least one well.", parent=dlg)
                return
            wells = [available[i] for i in sel]
            name  = name_var.get().strip() or f"R{len(grp.replicates)+1}"
            grp.replicates.append(ReplicateSet(name, wells))
            dlg.destroy()
            self._bar_active_rep = len(grp.replicates) - 1
            self._bar_rebuild_groups()

        tk.Button(btn_row, text="Add Replicate Set", command=_ok,
                  font=FM_BOLD, bg=ACCENT, fg=CLR_WHITE,
                  activebackground=ACCENT, relief=tk.FLAT,
                  padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(btn_row, text="Cancel", command=dlg.destroy,
                  font=FM_TINY, bg=BG_CELL, fg=TXT_SEC,
                  activebackground=BG_HOVER, relief=tk.FLAT,
                  padx=8, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(6, 0))

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

    def _bg_vis_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Record the screen-space anchor and open the rubber-band Toplevel."""
        sx = event.widget.winfo_rootx() + event.x
        sy = event.widget.winfo_rooty() + event.y
        self._vis_anchor_screen: tuple = (sx, sy)

        # Snapshot each button's screen-space centre for release hit-testing.
        self._vis_btn_centres: Dict[str, tuple] = {}
        for tok, btn in self._bar_map_btns.items():
            if btn.winfo_ismapped() and btn.cget("state") != tk.DISABLED:
                cx = btn.winfo_rootx() + btn.winfo_width()  // 2
                cy = btn.winfo_rooty() + btn.winfo_height() // 2
                self._vis_btn_centres[tok] = (cx, cy)

        # Destroy any previous rubber-band window.
        if self._vis_rubber_win is not None:
            try:
                self._vis_rubber_win.destroy()
            except Exception:
                pass
        # Floating Toplevel: no decorations, semi-transparent red fill.
        # Drawn entirely outside the main window's widget hierarchy so it
        # renders on top of all buttons without intercepting their events.
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        try:
            win.attributes("-alpha", 0.30)
        except Exception:
            pass
        win.configure(bg=WELL_COLOR_2)
        win.geometry("1x1+0+0")
        win.lift()
        self._vis_rubber_win = win

    def _bg_vis_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Resize the floating Toplevel to span anchor → cursor (screen coords)."""
        if not hasattr(self, "_vis_anchor_screen") or self._vis_rubber_win is None:
            return
        cx = event.widget.winfo_rootx() + event.x
        cy = event.widget.winfo_rooty() + event.y
        ax, ay = self._vis_anchor_screen
        x0, y0 = min(ax, cx), min(ay, cy)
        w  = max(2, abs(cx - ax))
        h  = max(2, abs(cy - ay))
        self._vis_rubber_win.geometry(f"{w}x{h}+{x0}+{y0}")

    def _bg_vis_release(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """
        Toggle visibility of replicate sets whose wells fall inside the
        rubber-band rectangle, then destroy the floating Toplevel.
        """
        # Tear down the rubber-band window first — must happen regardless.
        if self._vis_rubber_win is not None:
            try:
                self._vis_rubber_win.destroy()
            except Exception:
                pass
            self._vis_rubber_win = None

        # Collect state set by _bg_vis_press, then clear it.
        anchor     = getattr(self, "_vis_anchor_screen", None)
        btn_centres = getattr(self, "_vis_btn_centres", {})
        for attr in ("_vis_anchor_screen", "_vis_btn_centres"):
            try:
                delattr(self, attr)
            except AttributeError:
                pass

        if anchor is None:
            return

        # Rectangle in screen coordinates.
        cx = event.widget.winfo_rootx() + event.x
        cy = event.widget.winfo_rooty() + event.y
        ax, ay = anchor
        x0, x1 = min(ax, cx), max(ax, cx)
        y0, y1 = min(ay, cy), max(ay, cy)

        # Find labels of buttons whose screen-space centres fall inside.
        inside_labels: set = set()
        for tok, (bx, by) in btn_centres.items():
            if x0 <= bx <= x1 and y0 <= by <= y1:
                lbl = self._tok_to_label.get(tok)
                if lbl:
                    inside_labels.add(lbl)

        if not inside_labels:
            return

        loaded = self._rep_sets_loaded()
        if loaded:
            affected: set = set()
            for si, rset in enumerate(loaded):
                if any(w in inside_labels for w in rset.wells):
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
            for lbl in inside_labels:
                for i, g in enumerate(self._bar_groups):
                    if lbl in g.wells:
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
                              if f"{row_ltr}{col}" in self._tok_to_label]
                    new_sets.extend(self._make_replicate_pairs(loaded, row_ltr))
            else:
                # Column-first iteration: collect all row pairs, then sort by column
                by_col = {}  # col -> list of sets from that column
                for row_ltr in _PLATE_ROWS:
                    loaded = [f"{row_ltr}{col}" for col in _PLATE_COLS
                              if f"{row_ltr}{col}" in self._tok_to_label]
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
                              if f"{row_ltr}{col}" in self._tok_to_label]
                    new_sets.extend(self._make_replicate_pairs(loaded, col))
            else:
                # Row-first iteration: collect all column pairs, then sort by row
                by_row = {}  # row -> list of sets from that row
                for col in _PLATE_COLS:
                    loaded = [f"{row_ltr}{col}" for row_ltr in _PLATE_ROWS
                              if f"{row_ltr}{col}" in self._tok_to_label]
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
            if not messagebox.askyesno(
                    "Replace replicate sets?",
                    f"This will replace the current {len(self._rep_sets)} "
                    "replicate set(s). Continue?",
                    parent=self):
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
            active_tab = self._notebook.tab(self._notebook.select(), "text")
        except Exception:
            active_tab = ""
        if active_tab == "Sample Definitions":
            self._rep_panel_refresh()

        # Defer expensive plot redraws — only if the relevant tab is visible.
        # _on_tab_change already triggers redraws on tab switch, so skipping
        # these when the user is on another tab has no visible effect.
        try:
            active_tab = self._notebook.tab(self._notebook.select(), "text")
        except Exception:
            active_tab = ""
        if active_tab == "Bar Plots":
            self.after(0, self._redraw_bars)
        elif active_tab == "Line Graphs":
            self.after(0, self._redraw)

    def _make_replicate_pairs(self, toks: List[str], prefix: str) -> List[ReplicateSet]:
        """Pair adjacent tokens into ReplicateSets; singletons become solo sets."""
        sets: List[ReplicateSet] = []
        i = 0
        while i < len(toks):
            if i + 1 < len(toks):
                w1 = self._tok_to_label[toks[i]]
                w2 = self._tok_to_label[toks[i + 1]]
                t1 = _extract_well_token(w1) or toks[i]
                t2 = _extract_well_token(w2) or toks[i+1]
                sets.append(ReplicateSet(f"{t1}/{t2}", [w1, w2]))
                i += 2
            else:
                w = self._tok_to_label[toks[i]]
                t = _extract_well_token(w) or toks[i]
                sets.append(ReplicateSet(t, [w]))
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
                              if f"{row_ltr}{col}" in self._tok_to_label]
                    if not loaded:
                        continue
                    sets = self._make_replicate_pairs(loaded, row_ltr)
                    self._bar_groups.append(BarGroup(f"Row {row_ltr}", replicates=sets))
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
                        loaded = [t for t in loaded if t in self._tok_to_label]
                        if loaded:
                            pairs_in_col.extend(self._make_replicate_pairs(loaded, col))
                    if pairs_in_col:
                        self._bar_groups.append(BarGroup(f"Col {col}", replicates=pairs_in_col))
        else:
            # Column pairs with grouping by row or column
            if iter_order == "col":
                # Group by column (column-first): Same as _bar_quick_groups_col_pairs
                for col in _PLATE_COLS:
                    loaded = [f"{row_ltr}{col}" for row_ltr in _PLATE_ROWS
                              if f"{row_ltr}{col}" in self._tok_to_label]
                    if not loaded:
                        continue
                    sets = self._make_replicate_pairs(loaded, col)
                    self._bar_groups.append(BarGroup(f"Col {col}", replicates=sets))
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
                        loaded = [t for t in loaded if t in self._tok_to_label]
                        if loaded:
                            pairs_in_row.extend(self._make_replicate_pairs(loaded, col))
                    if pairs_in_row:
                        self._bar_groups.append(BarGroup(f"Row {row_ltr}", replicates=pairs_in_row))

        if self._bar_groups:
            self._bar_active_grp = 0
        self._bar_rebuild_groups_ui_now()        # instant: show cards
        self.after(50, self._bar_rebuild_groups) # deferred: update plots

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
            messagebox.showwarning(
                "Nothing to save",
                "Define at least one group before saving.",
                parent=self,
            )
            return
        out_dir = self._app._data_dir if self._app._data_dir else None
        path_str = filedialog.asksaveasfilename(
            parent=self,
            title="Save bar group definitions",
            defaultextension=".json",
            filetypes=[("Group definitions JSON", "*.json"),
                       ("All files", "*.*")],
            initialfile="bar_groups.json",
            initialdir=str(out_dir) if out_dir else None,
        )
        if not path_str:
            return
        try:
            with open(path_str, "w", encoding="utf-8") as fh:
                json.dump(self._bar_groups_to_dict(), fh, indent=2)
            _logger.info("Bar groups saved to %s", path_str)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)

    def _bar_load_groups(self) -> None:
        """Load bar groups from a previously saved JSON file."""
        out_dir = self._app._data_dir if self._app._data_dir else None
        path_str = filedialog.askopenfilename(
            parent=self,
            title="Load bar group definitions",
            filetypes=[("Group definitions JSON", "*.json"),
                       ("All files", "*.*")],
            initialdir=str(out_dir) if out_dir else None,
        )
        if not path_str:
            return
        try:
            with open(path_str, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array at the top level.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror(
                "Load failed",
                f"Could not read group definitions:\n{exc}",
                parent=self,
            )
            return
        if self._bar_groups:
            if not messagebox.askyesno(
                "Replace existing groups?",
                f"Loading will replace the current {len(self._bar_groups)} "
                f"group(s).  Continue?",
                parent=self,
            ):
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

    def _bar_map_tok_at(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        sx = event.widget.winfo_rootx() + event.x
        sy = event.widget.winfo_rooty() + event.y
        w  = event.widget.winfo_containing(sx, sy)
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

    def _bg_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._sb_press(event)

    def _bg_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._sb_drag(event)

    def _bg_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._sb_release(event=None)

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

    def _build_right_panel(self, parent: tk.Frame) -> None:
        from well_viewer.views.preview_panel_view import build_right_panel as _build_right_panel_view

        _build_right_panel_view(self, parent)

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

        if preloaded:
            self._mon_tophat_var.set(True)
            self._th_checkbox.config(state=tk.DISABLED)
            self._th_label.config(
                text="Top-hat background subtraction",
                fg=TXT_MUT)
            self._th_radius_label.config(fg=TXT_MUT)
            self._th_radius_hint.config(fg=TXT_MUT)
            self._th_radius_entry.config(state=tk.DISABLED)
            self._th_preload_badge.config(text="● from output zip")
        else:
            self._mon_tophat_var.set(False)
            self._th_checkbox.config(state=tk.NORMAL)
            self._th_label.config(
                text="Top-hat background subtraction",
                fg=TXT_SEC)
            self._th_radius_label.config(fg=TXT_MUT)
            self._th_radius_hint.config(fg=TXT_MUT)
            self._th_radius_entry.config(state=tk.NORMAL)
            self._th_preload_badge.config(text="")

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
            self._montage_zoom_lbl.config(text="100%")

        # Clear previous content
        for w in self._montage_inner.winfo_children():
            w.destroy()
        self._montage_photos.clear()
        self._montage_fluor_arrays         = []
        self._montage_overlay_arrays     = []
        self._montage_fluor_display_arrays = []   # cleared on new load
        self._montage_th_status          = []
        self._montage_th_overlay_lbls    = []
        self._montage_th_cancel          = True   # no thread running initially

        well = self._preview_selected_well
        if well is None:
            self._montage_status.config(text="Select a well in the left panel.")
            return

        fov = self._preview_fov_var.get()
        if fov == "—":
            self._montage_status.config(text="No images found for this well.")
            return

        # Filter refs to this FOV
        fluor_refs     = [(tp, ref) for (f, tp), ref in sorted(self._preview_fluor.items())
                        if f == fov]

        # If no raw fluor images exist for this FOV, fall back to tophat images
        # as the primary source (normal case: pipeline only saves tophat output).
        tophat_refs = getattr(self, "_preview_tophat_fluor", {})
        _used_tophat_as_primary = False
        if not fluor_refs:
            fluor_refs = [(tp, ref) for (f, tp), ref in sorted(tophat_refs.items())
                        if f == fov]
            _used_tophat_as_primary = bool(fluor_refs)

        overlay_refs = [(tp, ref) for (f, tp), ref in sorted(self._preview_overlay.items())
                        if f == fov]
        # Align by timepoint (use all TPs from GFP; overlay may be subset)
        ov_map = dict(overlay_refs)
        n = len(fluor_refs)

        if n == 0:
            self._montage_status.config(text="No images for this FOV.")
            return

        self._montage_status.config(text=f"Loading {n} timepoint(s)…")
        self.update_idletasks()

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

        # If tophat images were used as the primary source, the arrays we just
        # loaded ARE the display arrays — no re-load needed.
        if _used_tophat_as_primary:
            self._montage_fluor_display_arrays = list(self._montage_fluor_arrays)
            self._montage_tophat_preloaded   = True
        else:
            # Prefer pre-filtered tophat frames by default when present;
            # fall back to raw fluor frames for any timepoints without a
            # matching tophat image.
            raw_by_tp = {
                tp: arr for (tp, _), arr in zip(fluor_refs, self._montage_fluor_arrays)
            }
            self._montage_fluor_display_arrays = []
            _used_any_tophat = False
            for tp, _ in fluor_refs:
                th_ref = tophat_refs.get((fov, tp))
                if th_ref is not None:
                    self._montage_fluor_display_arrays.append(
                        open_imgref_as_array(th_ref, greyscale=True)
                    )
                    _used_any_tophat = True
                else:
                    self._montage_fluor_display_arrays.append(raw_by_tp[tp])
            self._montage_tophat_preloaded = _used_any_tophat

        self._montage_status.config(text="")
        self._montage_auto_lut(redraw=False)  # set initial LUT from data
        self._update_tophat_controls()        # sync UI to actual preload result
        self._draw_montage_thumbs([(tp, _) for tp, _ in fluor_refs])

    def _draw_montage_thumbs(self, tp_list: list) -> None:
        """Render fluorescence + overlay thumbnail pairs, one column per timepoint."""
        for w in self._montage_inner.winfo_children():
            w.destroy()
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
        cw = self._montage_canvas.winfo_width() or 400
        n  = len(tp_list)
        GAP = 6
        fit_sz = max(60, (cw - GAP) // max(n, 1) - GAP)
        self._montage_base_sz = fit_sz
        zoom   = getattr(self, "_montage_zoom", 1.0)
        sz_w   = max(40, int(fit_sz * zoom))
        sz_h   = max(35, int(sz_w * 0.8))
        # Update zoom label
        if hasattr(self, "_montage_zoom_lbl"):
            self._montage_zoom_lbl.config(text=f"{int(zoom * 100)}%")

        for col_idx, ((tp, _), fluor_arr, ov_arr) in enumerate(
                zip(tp_list, display_source, self._montage_overlay_arrays)):

            col = tk.Frame(self._montage_inner, bg=BG_APP)
            col.grid(row=0, column=col_idx, padx=3, pady=4, sticky="n")

            tk.Label(col, text=tp, font=FM_TINY, fg=TXT_MUT,
                     bg=BG_APP, pady=2).pack()

            # ── GFP thumbnail ───────────────────────────────────────────────
            fluor_cell = tk.Frame(col, bg=BG_CELL, highlightthickness=1,
                                highlightbackground=BORDER)
            fluor_cell.pack(pady=(0, 2))
            # Use pre-filtered array (computed in background thread) or raw
            display_arr = fluor_arr
            photo_fluor = make_fluor_thumb(display_arr, sz_w, sz_h, lo, hi)
            if photo_fluor:
                self._montage_photos.append(photo_fluor)
                lbl_fluor = tk.Label(fluor_cell, image=photo_fluor, bg=BG_APP,
                                   cursor="crosshair", bd=0)
                lbl_fluor._raw_arr = display_arr  # type: ignore[attr-defined]
                lbl_fluor._sz_w    = sz_w        # type: ignore[attr-defined]
                lbl_fluor._sz_h    = sz_h        # type: ignore[attr-defined]
                lbl_fluor._lo      = lo          # type: ignore[attr-defined]
                lbl_fluor._hi      = hi          # type: ignore[attr-defined]
                lbl_fluor.pack()
                lbl_fluor.bind("<Motion>", self._on_montage_fluor_motion)
                lbl_fluor.bind("<Leave>",  lambda _e: self._montage_tooltip.hide())
            else:
                tk.Label(fluor_cell, text=f"{self._active_channel.upper()}\nunavail", font=FM_TINY,
                         fg=TXT_MUT, bg=BG_CELL, width=sz_w // 7,
                         height=sz_h // 16).pack()

            # ── Top-hat status overlay ───────────────────────────────────────
            # Shows "⏳ filtering…" or "✓ filtered" on top of the GFP cell.
            # Only visible while top-hat is enabled.
            th_on = (getattr(self, "_mon_tophat_var", None) is not None
                     and self._mon_tophat_var.get())
            th_state = (self._montage_th_status[col_idx]
                        if col_idx < len(self._montage_th_status) else "")
            if th_on and th_state == "pending":
                overlay_txt, overlay_bg, overlay_fg = "⏳ filtering…", CLR_SLATE_BG, CLR_SLATE_TEXT
            elif th_on and th_state == "done":
                overlay_txt, overlay_bg, overlay_fg = "✓ filtered",   CLR_SUCCESS_BG_DARK, CLR_SUCCESS_TEXT_SOFT
            else:
                overlay_txt = ""
            if overlay_txt:
                th_lbl = tk.Label(fluor_cell, text=overlay_txt,
                                  font=FM_TINY, fg=overlay_fg, bg=overlay_bg,
                                  padx=4, pady=1, anchor="center")
                th_lbl.place(relx=0.0, rely=1.0, relwidth=1.0, anchor="sw")
                self._montage_th_overlay_lbls.append(th_lbl)
            else:
                self._montage_th_overlay_lbls.append(None)

            tk.Label(col, text=self._active_channel.upper(), font=FM_TINY, fg=TXT_MUT, bg=BG_APP).pack()

            # ── Overlay thumbnail ────────────────────────────────────────────
            ov_cell = tk.Frame(col, bg=BG_CELL, highlightthickness=1,
                               highlightbackground=BORDER)
            ov_cell.pack(pady=(2, 0))
            photo_ov = make_overlay_thumb(ov_arr, sz_w, sz_h)
            if photo_ov:
                self._montage_photos.append(photo_ov)
                tk.Label(ov_cell, image=photo_ov, bg=BG_APP, bd=0).pack()
            else:
                tk.Label(ov_cell, text="overlay\nunavail", font=FM_TINY,
                         fg=TXT_MUT, bg=BG_CELL, width=sz_w // 7,
                         height=sz_h // 16).pack()
            tk.Label(col, text="overlay", font=FM_TINY, fg=TXT_MUT, bg=BG_APP).pack()

        n_ov = sum(1 for a in self._montage_overlay_arrays if a is not None)
        self._montage_status.config(
            text=f"{n} timepoint(s)  ·  {n_ov} overlay(s)")

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

    def _on_montage_fluor_motion(self, e: tk.Event) -> None:  # type: ignore[type-arg]
        _on_montage_fluor_motion_controller(self, e)

    # ── Montage zoom helpers ──────────────────────────────────────────────────

    # Zoom levels: 25 % … 400 % in fixed steps
    _ZOOM_STEPS = [0.25, 0.33, 0.5, 0.67, 0.75, 1.0,
                   1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]

    def _montage_zoom_step(self, direction: int) -> None:
        _montage_zoom_step_controller(self, direction)

    def _montage_zoom_fit(self) -> None:
        _montage_zoom_fit_controller(self)

    def _on_montage_wheel(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        _on_montage_wheel_controller(self, event)

    def _montage_redraw_at_zoom(self) -> None:
        _montage_redraw_at_zoom_controller(self)

    def _build_bottom(self) -> None:
        from well_viewer.views.status_view import build_bottom as _build_bottom_view

        _build_bottom_view(self)

    def _apply_theme(self) -> None:
        from ui.theme import apply_all_well_theme
        apply_all_well_theme(ttk.Style(self))

    def _on_theme_change(self, theme_name: str = None) -> None:
        """Handle theme change notifications from ThemeManager.

        Refreshes all UI components to use the new theme colors.
        """
        # Apply TTK style changes
        self._apply_theme()

        # Refresh preview tab colors
        if self._sidebar_preview_frame and self._sidebar_preview_frame.winfo_children():
            self._refresh_preview_picker()

        # Refresh replicate sets panel colors
        if hasattr(self, '_rep_cards_frame') and self._rep_cards_frame:
            self._rep_panel_refresh()

        # Refresh groups panel colors
        if hasattr(self, '_grp_cards_frame') and self._grp_cards_frame:
            self._grp_panel_refresh()

        # Refresh statistics tab colors
        if hasattr(self, '_stats_fig') and self._stats_fig:
            self._stats_refresh_colors()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _browse(self) -> None:
        """Open a directory picker. Expects in/ + out/ subdirs or a flat CSV dir."""
        d = filedialog.askdirectory(title="Open results directory")
        if d:
            # Defer so the dialog closes and the window repaints before load
            self.after(50, lambda: self._load_path(Path(d)))

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
        if self._tk_root is not None:
            self._tk_root.destroy()
        else:
            self.destroy()

    # ── Plate-map sidebar helpers ─────────────────────────────────────────────

    def _parse_rc(self, label: str) -> Tuple[Optional[str], Optional[str]]:
        m = re.search(r"([A-Ha-h])(\d{1,2})$", label)
        if not m:
            return None, None
        return m.group(1).upper(), f"{int(m.group(2)):02d}"

    def _build_tok_to_label(self) -> None:
        """Rebuild the token→label map after data is loaded."""
        _load_build_tok_to_label(self)

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
        """Recolour every sidebar button to reflect rep-set visibility.

        Rep-set mode (when _rep_sets are defined):
          • Visible set  → full WELL_COLOR, normal relief
          • Hidden set   → muted (grey-blended) colour, flat relief
          • Not in any set → neutral, available for individual selection

        Per-well mode (no rep-sets):
          • Selected → ACCENT blue
          • Unselected → neutral
          • Missing → disabled
        """
        from ui.theme import get_color

        # Get current colors from theme (not cached imports)
        button_bg_color = get_color("button_bg")
        button_text_color = get_color("button_text")
        button_text_disabled_color = get_color("button_text_disabled")

        rep_sets = getattr(self, "_rep_sets", [])
        rep_mode = bool(rep_sets)

        # Build tok -> (full_color, muted_color, si, is_hidden)
        tok_rep: Dict[str, tuple] = {}
        for si, rset in enumerate(rep_sets):
            full_c  = WELL_COLORS[si % len(WELL_COLORS)]
            muted_c = self._mute_color(full_c)
            hidden  = si in self._rep_hidden
            for lbl in rset.wells:
                t = _extract_well_token(lbl) or lbl
                tok_rep[t] = (full_c, muted_c, si, hidden)

        for tok, btn in self._sidebar_btns.items():
            label = self._tok_to_label.get(tok)
            if label is None:
                btn.config(
                    bg=button_bg_color,
                    fg=button_text_disabled_color,
                    state=tk.DISABLED,
                    activebackground=button_bg_color,
                    activeforeground=button_text_color,
                    disabledforeground=button_text_disabled_color,
                    cursor="arrow",
                    relief=tk.FLAT,
                )
            elif rep_mode and tok in tok_rep:
                _full_c, _muted_c, _si, hidden = tok_rep[tok]
                if hidden:
                    # Dimmed: muted colour, lighter text, FLAT relief
                    btn.config(
                        bg=_muted_c,
                        fg="white",
                        state=tk.NORMAL,
                        activebackground=_full_c,
                        activeforeground="white",
                        disabledforeground=button_text_disabled_color,
                        cursor="hand2",
                        relief=tk.FLAT,
                    )
                else:
                    # Visible: full colour, SUNKEN relief
                    btn.config(
                        bg=_full_c,
                        fg="white",
                        state=tk.NORMAL,
                        activebackground=self._mute_color(_full_c, 0.3),
                        activeforeground="white",
                        disabledforeground=button_text_disabled_color,
                        cursor="hand2",
                        relief=tk.SUNKEN,
                    )
            elif rep_mode:
                # Well exists but not in any rep-set — neutral
                btn.config(
                    bg=button_bg_color,
                    fg=button_text_color,
                    state=tk.NORMAL,
                    activebackground=button_bg_color,
                    activeforeground=button_text_color,
                    disabledforeground=button_text_disabled_color,
                    cursor="hand2",
                    relief=tk.FLAT,
                )
            elif label in self._selected_wells:
                btn.config(
                    bg=button_bg_color,
                    fg=button_text_color,
                    state=tk.NORMAL,
                    activebackground=button_bg_color,
                    activeforeground=button_text_color,
                    disabledforeground=button_text_disabled_color,
                    cursor="hand2",
                    relief=tk.FLAT,
                )
            else:
                btn.config(
                    bg=button_bg_color,
                    fg=button_text_color,
                    state=tk.NORMAL,
                    activebackground=button_bg_color,
                    activeforeground=button_text_color,
                    disabledforeground=button_text_disabled_color,
                    cursor="hand2",
                    relief=tk.FLAT,
                )

        # Count label / hint
        loaded  = self._rep_sets_loaded() if rep_mode else []
        n_vis   = len(self._rep_sets_active()) if rep_mode else len(self._selected_wells)
        n_loaded = len(loaded)
        if hasattr(self, "_sel_count_lbl"):
            if rep_mode:
                n_hid = sum(1 for i in range(n_loaded) if i in self._rep_hidden)
                self._sel_count_lbl.config(
                    text=(f"{n_vis}/{n_loaded} set(s) visible"
                          if n_hid else f"{n_loaded} set(s) — all visible"))
            else:
                self._sel_count_lbl.config(
                    text=(f"{n_vis} well{'s' if n_vis != 1 else ''} selected"
                          if n_vis else "No wells selected"))
        if hasattr(self, "_line_group_hint"):
            if rep_mode:
                self._line_group_hint.config(
                    text="Click a well to toggle its set's visibility on the plot.")
            else:
                self._line_group_hint.config(text="")

        # Force Tkinter to process pending drawing updates immediately
        self.update_idletasks()

    def _sidebar_tok_at(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        from well_viewer.selection_controller import sidebar_tok_at as _sidebar_tok_at

        return _sidebar_tok_at(self, event)

    # =========================================================================
    # Shared plate-map drag engine
    # Both the line sidebar (_sidebar_btns / _selected_wells) and the
    # bar sidebar uses identical
    # rep-set toggle logic.  The three helpers below centralise it.
    #
    # Callers supply:
    #   btn_dict  – {tok: tk.Button} for the active map
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
        btn_dict: "Dict[str, tk.Button]",
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

    def _sb_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        from well_viewer.selection_controller import sb_press as _sb_press

        _sb_press(self, event)

    def _sb_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        from well_viewer.selection_controller import sb_drag as _sb_drag

        _sb_drag(self, event)

    def _sb_release(self, _event=None) -> None:  # type: ignore[type-arg]
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
        if detected and detected != self._fluor_channels:
            self._fluor_channels = detected
            # Keep the active channel if it is still present; otherwise
            # default to the first detected channel.
            if self._active_channel not in detected:
                self._active_channel = detected[0]
            self._active_val_col = f"{self._active_channel}_mean_intensity"
            self._update_channel_selector()

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
        if channel == self._active_channel:
            return
        self._active_channel = channel
        self._active_val_col = f"{channel}_mean_intensity"
        # Reset threshold to the range of the new channel.
        self._recalculate_threshold()
        self._invalidate_stats_cache()
        self._redraw()
        if hasattr(self, "_bar_tp_cb"):
            self._redraw_bars()
        # Update channel-sensitive UI labels.
        ch_upper = channel.upper()
        if hasattr(self, "_mon_lut_chan_lbl"):
            self._mon_lut_chan_lbl.config(text=f"{ch_upper} LUT min:")
        if hasattr(self, "_cdf_chan_lbl"):
            self._cdf_chan_lbl.config(text=f"({ch_upper} x range)")
        if hasattr(self, "_bar_ylim_chan_lbl"):
            self._bar_ylim_chan_lbl.config(text=f"{ch_upper} y:")
        # Reload preview images for the new channel if Preview tab is active.
        if hasattr(self, "_notebook") and self._preview_selected_well:
            tab = self._notebook.tab(self._notebook.select(), "text")
            if tab == "Preview":
                self._update_preview(self._preview_selected_well)

    def _update_channel_selector(self) -> None:
        """Refresh the channel dropdown values and selection to match loaded data."""
        labels = [ch.upper() for ch in self._fluor_channels]
        # Update all channel selector instances
        for attr in ("_chan_cb_line", "_chan_cb_bar", "_chan_cb_preview"):
            if hasattr(self, attr):
                getattr(self, attr).config(values=labels)
        active_label = self._active_channel.upper()
        if active_label in labels:
            self._chan_var.set(active_label)
        elif labels:
            self._chan_var.set(labels[0])

    def _toggle_sem(self) -> None:
        self._invalidate_stats_cache()
        self._use_sem.set(not self._use_sem.get())
        is_sem = self._use_sem.get()
        self._sem_btn.config(text="SEM" if is_sem else "SD")
        self._sem_btn.configure(style="SEM.TButton" if is_sem else "SEMWarn.TButton")
        self._redraw()
        if hasattr(self, "_notebook"):
            if self._notebook.tab(self._notebook.select(), "text") == "Bar Plots":
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
        if well_label is None:
            if hasattr(self, "_preview_well_lbl"):
                self._preview_well_lbl.config(text="No well selected")
            if hasattr(self, "_fov_menu"):
                self._fov_menu["values"] = ["—"]
                self._preview_fov_var.set("—")
            self._preview_fluor = self._preview_overlay = self._preview_mask = {}
            if hasattr(self, "_montage_inner"):
                for w in self._montage_inner.winfo_children():
                    w.destroy()
                self._montage_photos.clear()
                self._montage_status.config(text="Select a well in the left panel.")
            return

        if hasattr(self, "_preview_well_lbl"):
            tok = _extract_well_token(well_label) or well_label
            self._preview_well_lbl.config(text=tok)

        fluor, overlay, mask, tophat_fluor = find_well_images_and_masks(
            self._data_dir, well_label,
            fluor_token=self._active_channel,
            in_dir=self._in_dir,
            _fov_tp_extractor=self._fov_tp_extractor,
        )
        self._preview_fluor        = fluor
        self._preview_overlay    = overlay
        self._preview_mask       = mask
        self._preview_tophat_fluor = tophat_fluor

        # Reset controls to "no preload" state now; _refresh_preview_montage
        # will call _update_tophat_controls() with the authoritative result
        # after it has checked tophat coverage at the current FOV level.
        if hasattr(self, "_th_checkbox"):
            self._update_tophat_controls(preloaded=False)

        all_fovs = sorted({k[0] for k in {**fluor, **overlay, **mask, **tophat_fluor}})

        if not all_fovs:
            if hasattr(self, "_fov_menu"):
                self._fov_menu["values"] = ["—"]
                self._preview_fov_var.set("—")
            tok = _extract_well_token(well_label) or well_label
            dirs = f"in={self._in_dir}  out={self._data_dir}"
            msg = f"No images found for {tok}. Searched: {dirs}"
            _logger.warning(msg)
            if hasattr(self, "_montage_status"):
                self._montage_status.config(text=f"No images found for {tok} — check Log for details.")
            return

        if hasattr(self, "_fov_menu"):
            self._fov_menu["values"] = all_fovs
            cur = self._preview_fov_var.get()
            self._preview_fov_var.set(cur if cur in all_fovs else all_fovs[0])

        self._refresh_preview_montage()

    def _on_preview_sel_change(self, _e=None) -> None:
        self._refresh_preview_montage()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_plot_data(self) -> None:
        from well_viewer.export_service import export_plot_data as _export_plot_data

        _export_plot_data(self)

    def _export_raw_data_csv(self) -> None:
        from well_viewer.export_service import export_raw_data_csv as _export_raw_data_csv

        _export_raw_data_csv(self)

    # ── Batch export ──────────────────────────────────────────────────────────

    def _open_batch_export(self) -> None:
        from well_viewer.batch_export_dialogs import BatchExportDialog, open_line_batch_export

        open_line_batch_export(self, BatchExportDialog)

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

    # ── Bar plot tab ──────────────────────────────────────────────────────────

    def _on_tab_change(self, _e=None) -> None:
        """Show/hide the sidebar and refresh whichever tab is now active."""
        tab = self._notebook.tab(self._notebook.select(), "text")

        self._sidebar_main_frame.pack_forget()
        self._sidebar_preview_frame.pack_forget()
        self._sidebar_sample_frame.pack_forget()
        self._sidebar_stats_frame.pack_forget()

        if tab == "Preview":
            self._sidebar_preview_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_preview_picker()
            self._update_preview(self._preview_selected_well)

        elif tab == "Sample Definitions":
            self._sidebar_sample_frame.pack(fill=tk.BOTH, expand=True)
            self._groups_centre_refresh()

        elif tab == "Statistics":
            self._sidebar_stats_frame.pack(fill=tk.BOTH, expand=True)
            # Auto-populate from rep-sets on first visit
            if not self._stats_groups and hasattr(self, "_stats_grp_inner"):
                self._stats_sync_from_app()
            if hasattr(self, "_stats_tp_cb"):
                self._stats_update_tp_menu()

        elif tab == "Batch Export":
            self._sidebar_main_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_sidebar_map()

        elif tab == "smFISH":
            self._sidebar_main_frame.pack(fill=tk.BOTH, expand=True)
            if hasattr(self, "_sidebar_rc_frame"):
                self._sidebar_rc_frame.pack_forget()
            if hasattr(self, "_sidebar_allnone_frame"):
                self._sidebar_allnone_frame.pack_forget()
            if len(self._selected_wells) > 1:
                keep = self._last_sel if self._last_sel in self._selected_wells else next(iter(self._selected_wells))
                self._selected_wells = {keep}
            self._refresh_sidebar_map()
            if hasattr(self, "_smfish_tab"):
                self._smfish_tab.sync_from_app()

        else:
            # Line Graphs, Bar Plots, or Scatter — unified picker always shown
            self._sidebar_main_frame.pack(fill=tk.BOTH, expand=True)
            if hasattr(self, "_sidebar_rc_frame") and not self._sidebar_rc_frame.winfo_manager():
                self._sidebar_rc_frame.pack(fill=tk.X, padx=6, pady=(0, 4), before=self._sidebar_allnone_frame)
            if hasattr(self, "_sidebar_allnone_frame") and not self._sidebar_allnone_frame.winfo_manager():
                self._sidebar_allnone_frame.pack(fill=tk.X, padx=6, pady=(4, 6), before=self._sel_count_lbl)
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

    def _show_line_sidebar(self) -> None:
        """No-op: the unified well picker is always visible for plot tabs."""
        pass

    def _update_bar_tp_menu(self) -> None:
        """
        Populate the timepoint dropdown with the union of all timepoints
        present across all loaded wells.

        The available timepoints are always drawn from the full loaded dataset,
        not from the current selection — the selection controls what is plotted,
        but the dropdown must remain usable even when nothing is selected yet.
        """
        if not self._well_paths:
            self._bar_tp_cb["values"] = ["—"]
            self._bar_tp_var.set("—")
            return

        all_tps: set = set()
        for label in self._well_paths:
            for row in self._get_rows(label):
                raw = row.get("timepoint_hours")
                t: Optional[float] = (
                    raw if isinstance(raw, float) and not math.isnan(raw)
                    else parse_timepoint_hours(str(row.get("timepoint", "")))
                )
                if t is not None:
                    all_tps.add(t)

        # If no timepoints were found the schema had no timepoint field.
        # Use 0.0 as a single synthetic timepoint so bar plots remain usable.
        if not all_tps and self._well_paths:
            all_tps.add(0.0)

        sorted_tps = sorted(all_tps)
        tp_strs    = [f"{t:.4g}" for t in sorted_tps]

        cur = self._bar_tp_var.get()
        self._bar_tp_cb["values"] = tp_strs
        if cur in tp_strs:
            self._bar_tp_var.set(cur)
        elif tp_strs:
            self._bar_tp_var.set(tp_strs[0])
        else:
            self._bar_tp_var.set("—")

    # ── Bar drag-and-drop reordering ─────────────────────────────────────────

    def _bar_pixel_to_data_x(self, tk_x: int) -> "Optional[float]":
        """Convert a Tk widget pixel x to data-x in _ax_bar_mean.

        Returns None if the pixel is outside the axes bounding box.
        Tk widget origin is top-left; matplotlib figure origin is bottom-left.
        The x-axis direction matches so no horizontal offset correction is needed.
        """
        ax  = self._ax_bar_mean
        fig = self._bar_fig
        try:
            renderer = fig.canvas.get_renderer()
        except Exception as exc:
            return None
        bbox  = ax.get_window_extent(renderer=renderer)
        mpl_x = float(tk_x)
        if not (bbox.x0 <= mpl_x <= bbox.x1):
            return None
        inv     = ax.transData.inverted()
        data_pt = inv.transform((mpl_x, (bbox.y0 + bbox.y1) / 2.0))
        xdata   = float(data_pt[0])
        return xdata

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
        self._bar_reset_order_btn.configure(style="ToggleMuted.TButton")
        self._redraw_bars()

    def _on_bar_drag_press(self, event) -> None:
        """Begin drag — record which bar was pressed (Tk ButtonPress-1)."""
        xdata = self._bar_pixel_to_data_x(event.x)
        if xdata is None:
            return
        keys = self._bar_current_keys()
        n    = len(keys)
        if n < 2:
            return
        idx = self._bar_idx_at_x(xdata, n)
        self._bar_drag_state.update(active=True, src_idx=idx, cur_idx=idx)

    def _on_bar_drag_motion(self, event) -> None:
        """Update drop-target indicator while dragging (Tk B1-Motion)."""
        ds = self._bar_drag_state
        if not ds["active"]:
            return
        xdata = self._bar_pixel_to_data_x(event.x)
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
        self._bar_reset_order_btn.configure(style="ToggleAccent.TButton")
        self._redraw_bars()

    def _toggle_log_scale(self) -> None:
        """Toggle log y-axis for beeswarm fluor panel."""
        self._bar_log_scale.set(not self._bar_log_scale.get())
        on = self._bar_log_scale.get()
        self._bar_log_btn.configure(style="ToggleWarn.TButton" if on else "Toggle.TButton")
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
        self._swarm_btn.configure(style="ToggleActive.TButton" if on else "Toggle.TButton")
        if on and self._bar_violin.get():
            # Swarm and violin are mutually exclusive
            self._bar_violin.set(False)
            self._violin_btn.configure(style="Toggle.TButton")
            self._violin_slider.config(state=tk.DISABLED)
        self._redraw_bars()

    def _toggle_violin(self) -> None:
        """Toggle violin / bar mode and update the button appearance."""
        self._bar_violin.set(not self._bar_violin.get())
        on = self._bar_violin.get()
        self._violin_btn.configure(style="ToggleActive.TButton" if on else "Toggle.TButton")
        self._violin_slider.config(
            state=tk.NORMAL if on else tk.DISABLED,
            fg=TXT_SEC if on else TXT_MUT)
        if on and self._bar_swarm.get():
            # Mutually exclusive with beeswarm
            self._bar_swarm.set(False)
            self._swarm_btn.configure(style="Toggle.TButton")
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
        bw      = max(0.05, self._violin_bw.get())
        bar_w   = min(0.4, 3.0 / max(n, 1))   # half-width of each violin

        xs_ticks = list(range(n))
        frac_vals: List[float] = []

        for i, (lbl, color) in enumerate(zip(wells, colors)):
            rows = self._get_rows(lbl)
            vals: List[float] = []
            n_total = n_above = 0
            for row in rows:
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
            self._draw_bar_empty_state(ax_mean, ax_frac, "Select wells on the left panel")
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
            plot_wells: List[str] = []
            plot_colors: List[str] = []
            plot_labels: List[str] = []
            for si, key in enumerate(ordered_keys):
                rset = rset_by_name.get(key)
                if rset is None:
                    continue
                color = WELL_COLORS[si % len(WELL_COLORS)]
                valid = [w for w in rset.wells if w in self._well_paths]
                for w in valid:
                    plot_wells.append(w)
                    plot_colors.append(color)
                    plot_labels.append(f"{self._well_display_label(w)}\n[{rset.name}]")
        else:
            plot_wells = [k for k in ordered_keys if k in self._well_paths]
            plot_colors = [WELL_COLORS[i % len(WELL_COLORS)] for i in range(len(plot_wells))]
            plot_labels = [self._well_display_label(w) for w in plot_wells]
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
            color_by_key = {r.name: WELL_COLORS[i % len(WELL_COLORS)] for i, r in enumerate(active_rsets)}
            ordered = []
            for key in self._bar_current_keys():
                rset = by_key.get(key)
                if not rset:
                    continue
                gm, g_err_m, gf, g_err_f = self._compute_rep_stats(rset, target_t, threshold, use_sem)
                n_w = sum(1 for w in rset.wells if w in self._well_paths)
                display = f"{rset.name} (n={n_w})" if n_w != 1 else rset.name
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
            xlabels = [self._well_display_label(lbl) for lbl, *_ in draw_items]

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

    def _rep_sets_loaded(self) -> "List[ReplicateSet]":
        """All ReplicateSets that have at least one loaded well (ignores hidden)."""
        return [r for r in getattr(self, "_rep_sets", [])
                if any(w in self._well_paths for w in r.wells)]

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
            xlabels = [name for name, *_ in items]
            draw_items = [(name, name, gm, g_err_m, gf, g_err_f, has, color) for name, gm, g_err_m, gf, g_err_f, has, color in items]
        else:
            draw_items = items
            xlabels = [self._well_display_label(lbl) for lbl, *_ in items]

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
        """Open the bar-plot batch export dialog."""
        from well_viewer.batch_export_dialogs import BarBatchExportDialog, open_bar_batch_export

        open_bar_batch_export(self, BarBatchExportDialog)

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

    # ── Scatter Plot tab ───────────────────────────────────────────────────────

    def _update_scatter_menus(self) -> None:
        """Populate scatter plot dropdowns with available channels and timepoints."""
        # Update channel dropdowns for cells scatter
        channels = list(self._fluor_channels) if self._fluor_channels else ["gfp"]
        self._scatter_ch_x_cb.config(values=channels)
        self._scatter_ch_y_cb.config(values=channels)

        if channels:
            if self._scatter_ch_x_var.get() not in channels:
                self._scatter_ch_x_var.set(channels[0])
            if self._scatter_ch_y_var.get() not in channels:
                self._scatter_ch_y_var.set(channels[0 if len(channels) == 1 else 1])

        # Update timepoint dropdown for cells scatter
        timepoints = _scatter_get_timepoints(self)
        tp_strs = [f"{tp:.1f}" for tp in timepoints] if timepoints else ["0"]
        self._scatter_tp_cb.config(values=tp_strs)

        if tp_strs and self._scatter_tp_var.get() not in tp_strs:
            self._scatter_tp_var.set(tp_strs[0])

        # Update statistic dropdowns for aggregate scatter
        # Build list of available statistics: Mean Fluorescence and Fraction On for each channel
        statistics = []
        for ch in channels:
            statistics.append(f"Mean Fluorescence {ch.upper()}")
            statistics.append(f"Fraction On {ch.upper()}")

        self._scatter_agg_stat_x_cb.config(values=statistics)
        self._scatter_agg_stat_y_cb.config(values=statistics)

        if statistics:
            if self._scatter_agg_stat_x_var.get() not in statistics:
                self._scatter_agg_stat_x_var.set(statistics[0])
            if self._scatter_agg_stat_y_var.get() not in statistics:
                self._scatter_agg_stat_y_var.set(statistics[1] if len(statistics) > 1 else statistics[0])

        # Update timepoint selections for aggregate scatter
        # Initialize or rebuild with all timepoints checked by default
        if hasattr(self, '_scatter_agg_tp_selections'):
            # Save previously selected timepoints
            prev_selected = {tp_str for tp_str, var in self._scatter_agg_tp_selections.items() if var.get()}
            self._scatter_agg_tp_selections.clear()
        else:
            prev_selected = set()
            self._scatter_agg_tp_selections = {}

        # Rebuild with new timepoints, all checked by default
        for tp_str in tp_strs:
            var = tk.BooleanVar(value=True)  # All timepoints checked by default
            self._scatter_agg_tp_selections[tp_str] = var

        # Update the display label
        from well_viewer.views.centre_view import _update_tp_selection_display
        _update_tp_selection_display(self)

    def _redraw_scatter(self) -> None:
        """Redraw the scatter plot with current selections."""
        try:
            ch_x = self._scatter_ch_x_var.get()
            ch_y = self._scatter_ch_y_var.get()
            tp_str = self._scatter_tp_var.get()
            timepoint_h = float(tp_str) if tp_str else 0.0
        except ValueError:
            return

        cell_area_threshold = self._get_cell_area_threshold()
        fluor_gate_x = self._get_fluor_gate(ch_x)
        fluor_gate_y = self._get_fluor_gate(ch_y)

        _scatter_redraw(
            self,
            ch_x,
            ch_y,
            timepoint_h,
            well_colors=WELL_COLORS,
            cell_area_threshold=cell_area_threshold,
            fluor_gate_x=fluor_gate_x,
            fluor_gate_y=fluor_gate_y,
        )

    def _on_scatter_click(self, event) -> None:
        """Handle click events on scatter plot datapoints."""
        print(f"DEBUG scatter click: axes={event.inaxes}, button={event.button}, xdata={event.xdata}, ydata={event.ydata}")

        if event.inaxes is not self._ax_scatter or event.xdata is None or event.ydata is None:
            print(f"DEBUG: Ignoring click - wrong axes or no data")
            return

        if event.button != 1:  # Only respond to left clicks
            print(f"DEBUG: Ignoring non-left click (button={event.button})")
            return

        # Simple nearest-neighbor finder
        try:
            ch_x = self._scatter_ch_x_var.get()
            ch_y = self._scatter_ch_y_var.get()
            tp_str = self._scatter_tp_var.get()
            timepoint_h = float(tp_str) if tp_str else 0.0

            print(f"DEBUG: Collecting scatter data for {ch_x} vs {ch_y} at t={timepoint_h}")

            scatter_data = _scatter_collect_data(
                self,
                ch_x,
                ch_y,
                timepoint_h,
                well_colors=WELL_COLORS,
            )

            print(f"DEBUG: Got scatter_data with {len(scatter_data)} groups")

            # Find nearest point to click
            min_dist = float('inf')
            nearest_well = None
            nearest_filename = None
            nearest_nuclear_id = None
            nearest_row_idx = None

            for label, data in scatter_data.items():
                x_vals = data['x']
                y_vals = data['y']
                metadata = data['metadata']

                print(f"DEBUG: Group {label} has {len(x_vals)} points")

                for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                    dx = x - event.xdata
                    dy = y - event.ydata
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_well, nearest_filename, nearest_nuclear_id, nearest_row_idx = metadata[i]

            print(f"DEBUG: Nearest point: dist={min_dist}, well={nearest_well}, file={nearest_filename}, nuc_id={nearest_nuclear_id}")

            if nearest_well is not None:
                self._open_scatter_cell_viewer(nearest_well, nearest_filename, nearest_nuclear_id, nearest_row_idx)
            else:
                print(f"DEBUG: No point found")

        except Exception as e:
            print(f"DEBUG: Exception in scatter click: {e}")
            import traceback
            traceback.print_exc()
            self._set_status(f"Error handling scatter click: {e}")

    def _on_scatter_motion(self, event) -> None:
        """Handle hover events on scatter plot to show tooltips."""
        if event.inaxes is not self._ax_scatter or event.xdata is None or event.ydata is None:
            return

        try:
            ch_x = self._scatter_ch_x_var.get()
            ch_y = self._scatter_ch_y_var.get()
            tp_str = self._scatter_tp_var.get()
            timepoint_h = float(tp_str) if tp_str else 0.0

            scatter_data = _scatter_collect_data(
                self,
                ch_x,
                ch_y,
                timepoint_h,
                well_colors=WELL_COLORS,
            )

            # Find nearest point to cursor
            min_dist = float('inf')
            nearest_info = None
            threshold = 0.5  # Distance threshold for tooltip

            for label, data in scatter_data.items():
                x_vals = data['x']
                y_vals = data['y']
                metadata = data['metadata']

                for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                    dx = x - event.xdata
                    dy = y - event.ydata
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_info = metadata[i]

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

        if not hasattr(self, '_scatter_cell_viewer') or self._scatter_cell_viewer is None or not self._scatter_cell_viewer.winfo_exists():
            self._scatter_cell_viewer = ScatterCellViewer(
                self,
                self,
                well_label,
                filename,
                nuclear_id,
                row_idx,
            )
        else:
            self._scatter_cell_viewer.update_cell(well_label, filename, nuclear_id, row_idx)
            self._scatter_cell_viewer.lift()
            self._scatter_cell_viewer.focus()

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
        if event.button == 1 and event.inaxes is self._ax_cdf:
            # Accept if click is within 5% of the CDF x-range of the threshold
            try:
                lo, hi = self._ax_cdf.get_xlim()
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
            id(self._ax_mean): "mean",
            id(self._ax_frac): "frac",
            id(self._ax_cdf):  "cdf",
        }
        clicked_ax = event.inaxes
        key = ax_map.get(id(clicked_ax))
        if key is None:
            return
        self._legend_visible[key] = not self._legend_visible[key]
        leg = clicked_ax.get_legend()
        if leg is not None:
            leg.set_visible(self._legend_visible[key])
            self._mpl_canvas.draw_idle()
        state = "shown" if self._legend_visible[key] else "hidden"
        self._set_status(f"Legend for '{key}' plot {state}  (right-click to toggle)")

    def _on_cdf_motion(self, event) -> None:
        """Move the threshold line live while dragging."""
        if not self._thr_dragging:
            return
        if event.inaxes is not self._ax_cdf or event.xdata is None:
            return
        # Clamp to visible CDF range
        try:
            lo, hi = self._ax_cdf.get_xlim()
        except Exception:
            lo, hi = 0.0, 300.0
        new_thr = max(lo, min(hi, event.xdata))
        # Update the stored value and the Entry field
        self._threshold = new_thr
        self._entry_var.set(f"{new_thr:.2f}")
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
        self._status_lbl.config(text=msg)

    def _show_progress(self, maximum: int, msg: str = "") -> None:
        """Display the progress bar and set its maximum value."""
        self._progress_var.set(0)
        self._progress_bar.config(maximum=max(1, maximum))
        # Pack before the log button (which is already packed on the right)
        self._progress_bar.pack(side=tk.RIGHT, padx=(4, 2), pady=2,
                                before=self._log_btn)
        if msg:
            self._set_status(msg)
        self.update()

    def _step_progress(self, value: int, msg: str = "") -> None:
        """Advance the progress bar to *value* and repaint immediately."""
        self._progress_var.set(value)
        if msg:
            self._set_status(msg)
        self.update()

    def _hide_progress(self) -> None:
        """Remove the progress bar."""
        self._progress_bar.pack_forget()
        self._progress_var.set(0)

    def _toggle_log(self) -> None:
        self._log_visible = not self._log_visible
        if self._log_visible:
            self._log_frame.pack(fill=tk.X, before=self._status_lbl.master)
            self._log_btn.config(text="Log ▼")
        else:
            self._log_frame.pack_forget()
            self._log_btn.config(text="Log ▲")

    def _clear_log(self) -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state=tk.DISABLED)

# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(description="Well Viewer",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--data_dir", type=Path, default=None,
                    help="Directory of per-well CSVs, or a .zip / .tar.gz archive.")
    args = ap.parse_args()
    app = WellViewerApp(data_path=args.data_dir)
    app.pack(fill=tk.BOTH, expand=True)
    app._tk_root.mainloop()


__all__ = ["WellViewerApp", "BarGroup", "ReplicateSet", "main"]


if __name__ == "__main__":
    main()
