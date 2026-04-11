"""WellLabel widget and build_plate_grid helper extracted from runtime_app.

``WellLabel`` is a cross-platform ``tk.Label`` subclass that emulates the
``tk.Button`` API (state, activebackground, command) used by all plate-map
wells.  On macOS, ``tk.Button`` uses native Aqua rendering and ignores ``bg``,
making colour-coding invisible; ``tk.Label`` respects ``bg`` on all platforms.

``build_plate_grid`` fills a frame with an 8×12 header + ``WellLabel`` grid.
"""

from __future__ import annotations

import tkinter as tk
from typing import Dict, Optional


# ── WellLabel ─────────────────────────────────────────────────────────────────

class WellLabel(tk.Label):
    """
    tk.Label subclass that emulates the tk.Button API used by all plate-map
    wells throughout the app.

    Motivation: on macOS, tk.Button uses native Aqua rendering and completely
    ignores the ``bg`` option — making all colour-coding invisible.  tk.Label
    respects ``bg`` on every platform.

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
        """Update cached colors based on color_map during theme changes."""
        if self._normal_bg in color_map:
            new_bg = color_map[self._normal_bg]
            self._normal_bg = new_bg
            if not self._hover:
                tk.Label.config(self, bg=new_bg)

        if self._normal_fg in color_map:
            new_fg = color_map[self._normal_fg]
            self._normal_fg = new_fg
            if not self._hover:
                tk.Label.config(self, fg=new_fg)

        if self._active_bg and self._active_bg in color_map:
            self._active_bg = color_map[self._active_bg]

        if self._active_fg and self._active_fg in color_map:
            self._active_fg = color_map[self._active_fg]

    def update_theme_colors_rebuild(self, old_theme: str, new_theme: str) -> None:
        """Update cached colors using semantic theme rebuild approach.

        This handles the case where multiple colors share same hex value,
        causing dictionary collisions.
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


# ── build_plate_grid ──────────────────────────────────────────────────────────

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
    from well_viewer.runtime_app import (
        BG_CELL, BG_SIDE, FM_TINY, TXT_MUT,
        _PLATE_ROWS, _PLATE_COLS,
    )
    if font is None:
        font = FM_TINY
    # Column headers
    tk.Label(parent, text="", bg=BG_SIDE, font=font).grid(row=col_header_row, column=0)
    for ci, col in enumerate(_PLATE_COLS):
        tk.Label(parent, text=str(int(col)), font=font,
                 fg=TXT_MUT, bg=BG_SIDE).grid(row=col_header_row, column=ci + 1)

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
            lbl.grid(row=ri + row_start, column=ci + 1, padx=0, pady=1, sticky="ew")
            btn_store[tok] = lbl

    # Row-label column fixed; well columns equal-width via uniform group.
    parent.columnconfigure(0, weight=0)
    for col_idx in range(1, len(_PLATE_COLS) + 1):
        parent.columnconfigure(col_idx, weight=1, uniform="well_col")
