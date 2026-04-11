"""Data-load/path lifecycle helpers for WellViewerApp."""

from __future__ import annotations

import logging

from pathlib import Path
from tkinter import messagebox


def load_path(app, path: Path) -> None:
    if not path.is_dir():
        messagebox.showerror("Not a directory", f"Expected a directory:\n{path}")
        return
    app._cleanup_tmp()
    in_dir = path / "in"
    out_dir = path / "out"
    if in_dir.is_dir() and out_dir.is_dir():
        logger = logging.getLogger("well_viewer")
        logger.info("Detected in/out layout: in=%s  out=%s", in_dir, out_dir)
        logger.info("Fluor images from: %s  |  masks/overlays from: %s", in_dir, out_dir)
        app._in_dir = in_dir
        app._fov_tp_extractor, _fluor_tokens, _smfish_tokens = app._read_pipeline_info(out_dir)
        app._smfish_channels = _smfish_tokens
        app._load_directory(out_dir, label=f"{path.name}/out")
    else:
        app._in_dir = None
        app._fov_tp_extractor, _fluor_tokens, _smfish_tokens = app._read_pipeline_info(path)
        app._smfish_channels = _smfish_tokens
        app._load_directory(path)


def load_directory(app, d: Path, label=None) -> None:
    csvs = [p for p in sorted(d.glob("*.csv")) if not p.name.startswith(".")]
    if not csvs:
        messagebox.showwarning("No CSVs", f"No .csv files found in:\n{d}")
        return
    app._data_dir = d
    app._well_paths.clear()
    app._cache.clear()
    app._selected_wells.clear()
    app._last_sel = None
    app._prev_sel = set()
    app._bar_order = None
    n = len(csvs)
    app._show_progress(n, f"Loading {n} CSV file(s)…")
    for i, p in enumerate(csvs, 1):
        app._well_paths[p.stem] = p
        app._cache[p.stem] = app._load_well_csv(p)
        app._step_progress(i, f"Loading {i}/{n}: {p.name}")
    app._hide_progress()
    app._rebuild_all_timepoints_cache()
    app._build_tok_to_label()
    app._refresh_sidebar_map()
    app._bar_groups_prune()
    if hasattr(app, "_bar_map_btns"):
        app._bar_refresh_map()
    if app._preview_selected_well not in app._well_paths:
        app._preview_selected_well = None
    if hasattr(app, "_sidebar_preview_btns"):
        app._refresh_preview_picker()
    app._label_panel_refresh()
    display = label or str(d)
    app._dir_label.config(text=display)
    app._set_status(f"Loaded {n} well(s) — {display}")
    app._recalculate_threshold()
    app._redraw()


def build_tok_to_label(app) -> None:
    app._tok_to_label = {}
    for label in app._well_paths:
        tok = app._extract_well_token(label)
        if tok:
            app._tok_to_label[tok] = label
    if hasattr(app, "_sidebar_btns"):
        for btn in app._sidebar_btns.values():
            btn.bind("<ButtonPress-1>", app._sb_press)
            btn.bind("<B1-Motion>", app._sb_drag)
            btn.bind("<ButtonRelease-1>", app._sb_release)
