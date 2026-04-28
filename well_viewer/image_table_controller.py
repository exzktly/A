"""Image Table tab — non-UI controller logic.

These functions are bound onto the runtime app (via ``runtime_app.py``)
and drive the Image Table tab:

- multi-select sidebar picker (ignores groupings / replicate sets)
- selector grid build / rebuild (rows × cols of dropdowns per cell)
- "Distribute Wells" — assigns active wells row-wise into cells
- Global Options propagation (channel / timepoint / FOV → every cell)
- Generate — loads images and lays them out below the selector
- Per-channel auto-LUT
- Export — matplotlib figure with labels above each image, transparent BG
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout, QWidget,
)


# ── Sidebar picker ───────────────────────────────────────────────────────────


def image_table_pick_well(app, tok: str) -> None:
    """Toggle a well in the active set (sidebar click handler)."""
    if tok not in app._well_paths:
        return
    if tok in app._image_table_active_wells:
        app._image_table_active_wells.discard(tok)
    else:
        app._image_table_active_wells.add(tok)
    image_table_refresh_picker(app)


def image_table_refresh_picker(app) -> None:
    """Repaint the sidebar plate map and update the count label."""
    btns = getattr(app, "_sidebar_image_table_btns", None) or {}
    for tok, btn in btns.items():
        if tok not in app._well_paths:
            btn.setEnabled(False)
            btn.set_state("empty")
        elif tok in app._image_table_active_wells:
            btn.setEnabled(True)
            btn.set_state("selected")
        else:
            btn.setEnabled(True)
            btn.set_state("available")
    lbl = getattr(app, "_image_table_count_lbl", None)
    if lbl is not None:
        n = len(app._image_table_active_wells)
        lbl.setText(f"{n} well{'s' if n != 1 else ''} active")


def image_table_select_all(app) -> None:
    app._image_table_active_wells = set(app._well_paths.keys())
    image_table_refresh_picker(app)


def image_table_clear_active(app) -> None:
    app._image_table_active_wells = set()
    image_table_refresh_picker(app)


# ── Pipeline-info-driven dropdown options ────────────────────────────────────


def _channel_options(app) -> List[str]:
    """All channel tokens available for selection (uppercase for display)."""
    info = getattr(app, "_pipeline_info", None) or {}
    chans: List[str] = []
    nuclear = (info.get("nuclear_token") or "").strip()
    if nuclear:
        chans.append(nuclear)
    for tok in info.get("fluor_tokens", []) or []:
        tok = str(tok).strip()
        if tok and tok not in chans:
            chans.append(tok)
    for tok in info.get("smfish_tokens", []) or []:
        tok = str(tok).strip()
        if tok and tok not in chans:
            chans.append(tok)
    return [c.upper() for c in chans]


def _timepoint_options(app) -> List[str]:
    info = getattr(app, "_pipeline_info", None) or {}
    return [str(tp) for tp in (info.get("available_timepoints") or [])]


def _fov_options(app) -> List[str]:
    info = getattr(app, "_pipeline_info", None) or {}
    return [str(fv) for fv in (info.get("available_fovs") or [])]


def _well_options(app) -> List[str]:
    return sorted(app._well_paths.keys(), key=app._parse_rc)


def image_table_repopulate_dropdowns(app) -> None:
    """Refresh option lists for the global row and every cell.

    Called when pipeline info / wells become available after the tab is
    already built. Existing selections are preserved when still valid.
    """
    chan_opts = _channel_options(app)
    tp_opts = _timepoint_options(app)
    fov_opts = _fov_options(app)
    well_opts = _well_options(app)

    def _reset_combo(cb, options):
        cur = cb.currentText()
        cb.blockSignals(True)
        cb.clear()
        cb.addItems(options)
        if cur in options:
            cb.setCurrentText(cur)
        cb.blockSignals(False)

    if hasattr(app, "_image_table_global_chan_cb"):
        _reset_combo(app._image_table_global_chan_cb, chan_opts)
        _reset_combo(app._image_table_global_tp_cb, tp_opts)
        _reset_combo(app._image_table_global_fov_cb, fov_opts)

    cells = getattr(app, "_image_table_cells", None) or []
    for row in cells:
        for cell in row:
            _reset_combo(cell["well_cb"], well_opts)
            _reset_combo(cell["chan_cb"], chan_opts)
            _reset_combo(cell["tp_cb"], tp_opts)
            _reset_combo(cell["fov_cb"], fov_opts)


# ── Selector-grid build / rebuild ────────────────────────────────────────────


def image_table_apply_dimensions(app) -> None:
    """Read rows / cols spinners and rebuild the selector grid."""
    rows = int(app._image_table_rows_spin.value())
    cols = int(app._image_table_cols_spin.value())
    app._image_table_rows = rows
    app._image_table_cols = cols
    image_table_rebuild_grid(app)


def image_table_rebuild_grid(app) -> None:
    """Rebuild the selector grid (rows × cols of cell groupboxes)."""
    from well_viewer.ui_helpers import clear_layout

    layout = app._image_table_selector_grid
    clear_layout(layout)

    rows = int(getattr(app, "_image_table_rows", 2) or 2)
    cols = int(getattr(app, "_image_table_cols", 3) or 3)

    chan_opts = _channel_options(app)
    tp_opts = _timepoint_options(app)
    fov_opts = _fov_options(app)
    well_opts = _well_options(app)

    cells: List[List[Dict[str, Any]]] = []
    for r in range(rows):
        row: List[Dict[str, Any]] = []
        for c in range(cols):
            cell = _build_selector_cell(
                app, r, c, well_opts, chan_opts, tp_opts, fov_opts,
            )
            layout.addWidget(cell["frame"], r, c)
            row.append(cell)
        cells.append(row)
    app._image_table_cells = cells

    image_table_rebuild_lut_row(app)


def _build_selector_cell(
    app, r: int, c: int,
    well_opts: List[str], chan_opts: List[str],
    tp_opts: List[str], fov_opts: List[str],
) -> Dict[str, Any]:
    from PySide6.QtWidgets import QComboBox

    box = QGroupBox(f"({r + 1}, {c + 1})")
    inner = QVBoxLayout(box)
    inner.setContentsMargins(6, 8, 6, 6)
    inner.setSpacing(2)

    def _row(label_text: str, options: List[str]) -> QComboBox:
        rl = QHBoxLayout()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        lbl = QLabel(label_text, box)
        lbl.setFixedWidth(54)
        rl.addWidget(lbl)
        cb = QComboBox(box)
        cb.addItems(options)
        rl.addWidget(cb, 1)
        inner.addLayout(rl)
        return cb

    well_cb = _row("Well:", well_opts)
    chan_cb = _row("Channel:", chan_opts)
    tp_cb = _row("Timepoint:", tp_opts)
    fov_cb = _row("FOV:", fov_opts)

    return {
        "frame": box,
        "well_cb": well_cb,
        "chan_cb": chan_cb,
        "tp_cb": tp_cb,
        "fov_cb": fov_cb,
    }


def image_table_apply_global(app, field: str) -> None:
    """Copy a global dropdown's current value into every cell's matching combo.

    ``field`` is one of "chan", "tp", "fov".
    """
    if field == "chan":
        src = getattr(app, "_image_table_global_chan_cb", None)
        key = "chan_cb"
    elif field == "tp":
        src = getattr(app, "_image_table_global_tp_cb", None)
        key = "tp_cb"
    elif field == "fov":
        src = getattr(app, "_image_table_global_fov_cb", None)
        key = "fov_cb"
    else:
        return
    if src is None:
        return
    value = src.currentText()
    if not value:
        return
    cells = getattr(app, "_image_table_cells", None) or []
    for row in cells:
        for cell in row:
            cb = cell.get(key)
            if cb is None:
                continue
            cb.blockSignals(True)
            if cb.findText(value) >= 0:
                cb.setCurrentText(value)
            cb.blockSignals(False)


def image_table_distribute_wells(app) -> None:
    """Walk active wells row-wise and assign one to each selector cell."""
    cells = getattr(app, "_image_table_cells", None) or []
    if not cells:
        app._set_status("Image Table: build a grid first (set rows/cols and click Apply).")
        return
    active = sorted(app._image_table_active_wells, key=app._parse_rc)
    if not active:
        app._set_status("Image Table: no active wells in the sidebar picker.")
        return
    idx = 0
    for row in cells:
        for cell in row:
            if idx >= len(active):
                break
            tok = active[idx]
            cb = cell["well_cb"]
            cb.blockSignals(True)
            if cb.findText(tok) >= 0:
                cb.setCurrentText(tok)
            cb.blockSignals(False)
            idx += 1
        if idx >= len(active):
            break
    app._set_status(
        f"Image Table: distributed {min(idx, len(active))} well(s) into the selector grid."
    )


# ── LUT row ──────────────────────────────────────────────────────────────────


def image_table_rebuild_lut_row(app) -> None:
    """Rebuild the per-channel LUT editors (one min/max pair per channel)."""
    from well_viewer.ui_helpers import btn_secondary, clear_layout

    container = getattr(app, "_image_table_lut_container", None)
    if container is None:
        return
    layout = container.layout()
    clear_layout(layout)

    chans = _channel_options(app)
    app._image_table_lut = {}
    for chan in chans:
        chan_box = QGroupBox(chan, container)
        cb_l = QHBoxLayout(chan_box)
        cb_l.setContentsMargins(6, 8, 6, 4)
        cb_l.setSpacing(4)

        cb_l.addWidget(QLabel("min:", chan_box))
        min_edit = QLineEdit("auto", chan_box)
        min_edit.setFixedWidth(70)
        cb_l.addWidget(min_edit)

        cb_l.addWidget(QLabel("max:", chan_box))
        max_edit = QLineEdit("auto", chan_box)
        max_edit.setFixedWidth(70)
        cb_l.addWidget(max_edit)

        auto_btn = btn_secondary(
            chan_box, "Auto",
            lambda c=chan: image_table_auto_lut(app, c),
        )
        cb_l.addWidget(auto_btn)

        layout.addWidget(chan_box)
        app._image_table_lut[chan] = {"min": min_edit, "max": max_edit}

    layout.addStretch(1)


def _parse_lut(app, chan: str) -> Tuple[Optional[float], Optional[float]]:
    """Read (lo, hi) for a channel; returns (None, None) when 'auto'."""
    luts = getattr(app, "_image_table_lut", None) or {}
    entry = luts.get(chan.upper())
    if not entry:
        return None, None

    def _val(le: QLineEdit) -> Optional[float]:
        text = (le.text() or "").strip().lower()
        if not text or text == "auto":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    return _val(entry["min"]), _val(entry["max"])


# ── Image loading + caching ──────────────────────────────────────────────────


def _load_well_channel(app, cache: Dict[Tuple[str, str], Dict], well: str, chan_lower: str) -> Dict:
    """Return the (fov, tp) → ImgRef dict for (well, channel), with caching."""
    from well_viewer.runtime_app import find_well_images_and_masks

    key = (well, chan_lower)
    if key in cache:
        return cache[key]
    try:
        fluor, _overlay, _mask, _tophat = find_well_images_and_masks(
            app._data_dir,
            well,
            fluor_token=chan_lower,
            in_dir=app._in_dir,
            _fov_tp_extractor=app._fov_tp_extractor,
            _pipeline_info=app._pipeline_info,
        )
    except Exception:
        fluor = {}
    cache[key] = fluor
    return fluor


def _load_array(app, cache: Dict, well: str, chan_upper: str, tp: str, fov: str):
    """Load the float32 array for one (well, channel, timepoint, fov)."""
    chan_lower = chan_upper.strip().lower()
    fluor = _load_well_channel(app, cache, well, chan_lower)
    ref = fluor.get((str(fov), str(tp)))
    if ref is None:
        return None
    try:
        return ref.load()
    except Exception:
        return None


# ── Generate (render image table below the selector) ─────────────────────────


def image_table_generate(app) -> None:
    """Load images for every cell and lay out the rendered image table."""
    from well_viewer.runtime_app import make_fluor_thumb
    from well_viewer.ui_helpers import clear_layout

    cells = getattr(app, "_image_table_cells", None) or []
    grid = app._image_table_render_grid
    clear_layout(grid)
    if not cells:
        app._set_status("Image Table: build a grid first (set rows/cols and click Apply).")
        return

    cache: Dict[Tuple[str, str], Dict] = {}
    rendered: Dict[Tuple[int, int], Any] = {}
    crop_tool = getattr(app, "_image_table_crop_tool", None)

    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            well = cell["well_cb"].currentText().strip()
            chan = cell["chan_cb"].currentText().strip()
            tp = cell["tp_cb"].currentText().strip()
            fov = cell["fov_cb"].currentText().strip()

            arr = None
            if well and chan and tp and fov:
                arr = _load_array(app, cache, well, chan, tp, fov)
            rendered[(r, c)] = arr

            lo, hi = _parse_lut(app, chan)
            cell_widget = QWidget()
            cl = QVBoxLayout(cell_widget)
            cl.setContentsMargins(4, 4, 4, 4)
            cl.setSpacing(2)

            header_text = (
                f"{well}  {chan.upper()}  T:{tp}  FOV:{fov}"
                if well and chan and tp and fov
                else "(unset)"
            )
            header = QLabel(header_text, cell_widget)
            header.setAlignment(Qt.AlignCenter)
            cl.addWidget(header)

            img_label = QLabel(cell_widget)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setMinimumSize(220, 220)
            if arr is not None:
                # Apply the shared crop (no-op when not set) and render.
                cropped = crop_tool.apply_to_array(arr) if crop_tool else arr
                pix = make_fluor_thumb(cropped, 240, 240, lo, hi)
                # CropTool needs the FULL source array + the active crop on
                # the label so label-pixel → image-pixel coord conversion
                # works correctly even when the label already shows a crop.
                img_label._raw_arr = arr  # type: ignore[attr-defined]
                img_label._crop = crop_tool.crop if crop_tool else None  # type: ignore[attr-defined]
                if crop_tool is not None:
                    crop_tool.install_events(img_label)
                if pix is not None:
                    img_label.setPixmap(pix)
                else:
                    img_label.setText("(render failed)")
            else:
                img_label.setText("(no image)")
            cl.addWidget(img_label)

            grid.addWidget(cell_widget, r, c)

    app._image_table_last_render = rendered
    app._image_table_image_cache = cache
    n = sum(1 for v in rendered.values() if v is not None)
    app._set_status(f"Image Table: generated {n} of {len(rendered)} cell(s).")


def image_table_auto_lut(app, channel: str) -> None:
    """Pool min/max across loaded cells for one channel; write result and redraw."""
    chan_upper = channel.upper()
    cells = getattr(app, "_image_table_cells", None) or []
    rendered = getattr(app, "_image_table_last_render", None) or {}
    cache = getattr(app, "_image_table_image_cache", None)
    if cache is None:
        cache = {}
        app._image_table_image_cache = cache

    try:
        import numpy as _np
    except Exception:
        app._set_status("Image Table: numpy unavailable; cannot compute auto LUT.")
        return

    pooled_min: Optional[float] = None
    pooled_max: Optional[float] = None
    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            if cell["chan_cb"].currentText().strip().upper() != chan_upper:
                continue
            arr = rendered.get((r, c))
            if arr is None:
                # Lazy-load if Generate hasn't been clicked yet.
                well = cell["well_cb"].currentText().strip()
                tp = cell["tp_cb"].currentText().strip()
                fov = cell["fov_cb"].currentText().strip()
                if well and tp and fov:
                    arr = _load_array(app, cache, well, chan_upper, tp, fov)
            if arr is None:
                continue
            a = _np.asarray(arr, dtype=_np.float32)
            mn = float(a.min())
            mx = float(a.max())
            pooled_min = mn if pooled_min is None else min(pooled_min, mn)
            pooled_max = mx if pooled_max is None else max(pooled_max, mx)

    if pooled_min is None or pooled_max is None:
        app._set_status(
            f"Image Table: no loaded images for channel {chan_upper}; cannot auto-LUT."
        )
        return
    if pooled_max <= pooled_min:
        pooled_max = pooled_min + 1.0

    luts = getattr(app, "_image_table_lut", None) or {}
    entry = luts.get(chan_upper)
    if entry is None:
        return
    entry["min"].setText(f"{pooled_min:.3g}")
    entry["max"].setText(f"{pooled_max:.3g}")
    image_table_generate(app)


# ── Export (transparent background, labels above each image) ─────────────────


def image_table_export(app) -> None:
    """Export the current image table to PNG/PDF/SVG with no background."""
    cells = getattr(app, "_image_table_cells", None) or []
    if not cells:
        app._set_status("Image Table: nothing to export.")
        return
    try:
        from matplotlib.figure import Figure
    except Exception as exc:
        QMessageBox.critical(app, "Export failed", f"matplotlib unavailable: {exc}")
        return
    try:
        import numpy as _np
    except Exception as exc:
        QMessageBox.critical(app, "Export failed", f"numpy unavailable: {exc}")
        return

    rows = int(getattr(app, "_image_table_rows", len(cells)) or len(cells))
    cols = int(getattr(app, "_image_table_cols", len(cells[0])) or len(cells[0]))

    cache: Dict[Tuple[str, str], Dict] = dict(getattr(app, "_image_table_image_cache", None) or {})
    rendered = getattr(app, "_image_table_last_render", None) or {}
    crop_tool = getattr(app, "_image_table_crop_tool", None)

    fig = Figure(
        figsize=(max(2.4, cols * 2.6), max(2.4, rows * 2.8)),
        dpi=300,
        facecolor="none",
    )
    fig.patch.set_alpha(0.0)

    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            ax = fig.add_subplot(rows, cols, r * cols + c + 1)
            ax.set_facecolor("none")
            well = cell["well_cb"].currentText().strip()
            chan = cell["chan_cb"].currentText().strip()
            tp = cell["tp_cb"].currentText().strip()
            fov = cell["fov_cb"].currentText().strip()

            arr = rendered.get((r, c))
            if arr is None and well and chan and tp and fov:
                arr = _load_array(app, cache, well, chan, tp, fov)
            if arr is not None and crop_tool is not None:
                arr = crop_tool.apply_to_array(arr)

            if arr is not None:
                a = _np.asarray(arr, dtype=_np.float32)
                lo, hi = _parse_lut(app, chan)
                vmin = lo if lo is not None else float(a.min())
                vmax = hi if hi is not None else float(a.max())
                if vmax <= vmin:
                    vmax = vmin + 1.0
                ax.imshow(a, cmap="gray", vmin=vmin, vmax=vmax, aspect="equal")
            else:
                ax.text(
                    0.5, 0.5, "(no image)",
                    ha="center", va="center", transform=ax.transAxes, fontsize=7,
                )

            title = (
                f"{well}  {chan.upper()}  T:{tp}  FOV:{fov}"
                if well and chan and tp and fov
                else "(unset)"
            )
            ax.set_title(title, fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
    fig.tight_layout()

    initial_dir = str(app._data_dir) if getattr(app, "_data_dir", None) else ""
    initial = (
        str(Path(initial_dir) / "image_table.png") if initial_dir else "image_table.png"
    )
    out, _ = QFileDialog.getSaveFileName(
        app, "Export image table", initial,
        "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;All files (*.*)",
    )
    if not out:
        return
    fmt = Path(out).suffix.lstrip(".").lower() or "png"
    try:
        kw: Dict[str, Any] = dict(
            format=fmt, bbox_inches="tight", facecolor="none", transparent=True,
        )
        if fmt == "png":
            kw["dpi"] = 300
        fig.savefig(out, **kw)
        app._set_status(f"Image table saved → {Path(out).name}")
    except Exception as exc:
        QMessageBox.critical(app, "Export failed", str(exc))
