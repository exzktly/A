"""Reusable image-display panel widget extracted from runtime_app.

``_ImagePanel`` is a toggleable canvas widget that renders a numpy array at
full native bit depth, with an optional LUT min/max editor and pixel-value
tooltip on mouse-over.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional


# ── Categorical label colourmap ───────────────────────────────────────────────

_LABEL_PALETTE = None


def _label_to_rgb(arr: "_np.ndarray") -> "_np.ndarray":  # type: ignore[name-defined]
    global _LABEL_PALETTE
    from well_viewer.runtime_app import _np
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


# ── Image panel widget ────────────────────────────────────────────────────────

class _ImagePanel:
    """
    Toggleable panel showing one image at a time.
    Features:
      • Pixel-intensity tooltip on canvas mouseover
      • Full-path tooltip on filename label mouseover
      • Optional LUT min/max editor with Auto button (for fluorescence panel)
    """

    def __init__(self, parent: tk.Frame, title: str, tooltip,
                 show_lut: bool = False) -> None:
        from well_viewer.runtime_app import (
            ACCENT, BG_CELL, BG_HOVER, BG_PANEL, BG_SIDE, BORDER,
            FM_BOLD, FM_TINY, FM_UI, PLOT_BG, TXT_MUT, TXT_SEC, WELL_COLOR_2,
            _btn_secondary,
        )
        from well_viewer.views.widgets import _Tooltip

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

        # Store theme constants for methods called later
        self._FM_TINY = FM_TINY
        self._FM_UI = FM_UI
        self._PLOT_BG = PLOT_BG
        self._WELL_COLOR_2 = WELL_COLOR_2
        self._TXT_MUT = TXT_MUT

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
        from well_viewer.runtime_app import _NP_AVAILABLE, _np
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
    def render_arr(self, arr, filename: str,
                   full_path: str = "", colourmap: Optional[str] = None) -> None:
        self._file_lbl.config(text=filename)
        self._full_path = full_path or filename
        self._raw_arr   = arr
        self._colourmap = colourmap
        if self._show_lut:   # auto-range on first load
            from well_viewer.runtime_app import _np
            lo, hi = float(arr.min()), float(arr.max())
            if hi <= lo:
                hi = lo + 1.0
            self._lut_min = lo
            self._lut_max = hi
            self._lut_min_var.set(f"{lo:.0f}")
            self._lut_max_var.set(f"{hi:.0f}")
        self._render()

    def show_message(self, text: str, colour: str = "") -> None:
        if not colour:
            colour = self._TXT_MUT
        self._canvas.delete("all")
        self._photo   = None
        self._raw_arr = None
        self._file_lbl.config(text="")
        self._full_path = ""
        cw = self._canvas.winfo_width() or 300
        ch = self._canvas.winfo_height() or 200
        self._canvas.create_text(cw//2, ch//2, text=text, fill=colour,
                                 font=self._FM_UI, justify=tk.CENTER)

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
        from well_viewer.runtime_app import (
            _PIL_AVAILABLE, _NP_AVAILABLE, _np, _PILImage, _PILImageTk,
        )
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
                if hi <= lo:
                    hi = lo + 1.0
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
                               fill=self._WELL_COLOR_2, font=self._FM_TINY,
                               justify=tk.CENTER)

    def _canvas_motion(self, e) -> None:
        from well_viewer.runtime_app import _np
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
