"""Reusable UI helpers extracted from the legacy well_viewer3 surface."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional


def btn_primary(parent: tk.Widget, text: str, command, *, padx: int = 8, pady: int = 2, **kw) -> ttk.Button:
    """Accent-blue primary action button."""
    return ttk.Button(parent, text=text, command=command,
                      style="Primary.TButton", padding=(padx, pady), **kw)


def btn_secondary(parent: tk.Widget, text: str, command, *, padx: int = 6, pady: int = 2, **kw) -> ttk.Button:
    """Neutral secondary/toolbar button."""
    return ttk.Button(parent, text=text, command=command,
                      style="Secondary.TButton", padding=(padx, pady), **kw)


def btn_card(parent: tk.Widget, text: str, command, *, padx: int = 4, **kw) -> ttk.Button:
    """Compact inline card button."""
    return ttk.Button(parent, text=text, command=command,
                      style="Card.TButton", padding=(padx, 2), **kw)


def btn_danger(parent: tk.Widget, text: str, command, *, padx: int = 4, **kw) -> ttk.Button:
    """Red destructive action button."""
    return ttk.Button(parent, text=text, command=command,
                      style="Danger.TButton", padding=(padx, 2), **kw)


def tok_at_event(event: tk.Event, btn_dict: dict) -> Optional[str]:
    """Return the token key whose button widget is under the pointer, or None."""
    sx = event.widget.winfo_rootx() + event.x
    sy = event.widget.winfo_rooty() + event.y
    w = event.widget.winfo_containing(sx, sy)
    for tok, btn in btn_dict.items():
        if btn is w:
            return tok
    return None


def make_scrollable_canvas(
    parent: tk.Widget,
    *,
    bg: str,
    border: str,
    trough_bg: str,
    scrollbar_width: int = 7,
) -> tuple[tk.Canvas, tk.Frame]:
    vsb = tk.Scrollbar(parent, relief=tk.FLAT, width=scrollbar_width, bg=border, troughcolor=trough_bg)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, yscrollcommand=vsb.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.config(command=canvas.yview)

    inner = tk.Frame(canvas, bg=bg)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
    return canvas, inner


def ask_name_dialog(
    parent: tk.Widget,
    *,
    title: str,
    prompt: str,
    default: str,
    width: int,
    bg_app: str,
    txt_pri: str,
    txt_sec: str,
    accent: str,
    bg_panel: str,
    border: str,
    bg_cell: str,
    bg_hover: str,
    fm_ui,
    fm_bold,
    clr_white: str,
) -> Optional[str]:
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=bg_app)
    dlg.resizable(False, False)
    dlg.grab_set()
    tk.Label(dlg, text=prompt, font=fm_ui, fg=txt_pri, bg=bg_app, padx=14, pady=8).pack(anchor="w")

    var = tk.StringVar(value=default)
    e = tk.Entry(
        dlg,
        textvariable=var,
        font=fm_ui,
        width=width,
        fg=accent,
        bg=bg_panel,
        insertbackground=accent,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightcolor=accent,
        highlightbackground=border,
    )
    e.pack(padx=14, pady=(0, 8))
    e.select_range(0, tk.END)
    e.focus_set()

    result = [None]

    def _ok(_e=None):
        v = var.get().strip()
        if v:
            result[0] = v
        dlg.destroy()

    def _cancel(_e=None):
        dlg.destroy()

    e.bind("<Return>", _ok)
    e.bind("<Escape>", _cancel)

    br = tk.Frame(dlg, bg=bg_app)
    br.pack(fill=tk.X, padx=14, pady=(0, 10))
    tk.Button(
        br,
        text="OK",
        command=_ok,
        font=fm_bold,
        fg=clr_white,
        bg=accent,
        activebackground=accent,
        activeforeground=clr_white,
        relief=tk.FLAT,
        padx=10,
        pady=3,
        cursor="hand2",
    ).pack(side=tk.RIGHT, padx=(4, 0))
    tk.Button(
        br,
        text="Cancel",
        command=_cancel,
        font=fm_bold,
        fg=txt_sec,
        bg=bg_cell,
        activebackground=bg_hover,
        relief=tk.FLAT,
        padx=10,
        pady=3,
        cursor="hand2",
    ).pack(side=tk.RIGHT)
    dlg.wait_window()
    return result[0]
