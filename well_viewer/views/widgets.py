"""Reusable small GUI widgets extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from typing import Optional


class _Tooltip:
    """Floating label that stays within screen bounds."""

    def __init__(self, widget: tk.Widget) -> None:
        self._w   = widget
        self._win: Optional[tk.Toplevel] = None
        self._lbl: Optional[tk.Label]   = None

    def show(self, text: str, sx: int, sy: int) -> None:
        from well_viewer.runtime_app import FM_TINY, TOOLTIP_BG, TOOLTIP_FG
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
