"""Preview-tab UI helpers extracted from well_viewer3."""

from __future__ import annotations

import tkinter as tk


def build_preview_picker(
    app,
    parent: tk.Frame,
    *,
    fm_bold,
    fm_tiny,
    txt_mut: str,
    txt_pri: str,
    bg_side: str,
    bg_cell: str,
    bg_panel: str,
    bg_hover: str,
    border: str,
    accent: str,
    clr_white: str,
    clr_accent_dark: str,
    build_plate_grid_fn,
    extract_well_token_fn,
) -> None:
    tk.Label(parent, text="PREVIEW WELL", font=fm_bold, fg=txt_mut, bg=bg_side, pady=6).pack(fill=tk.X, padx=10)
    tk.Label(parent, text="Click one well to load its images", font=fm_tiny, fg=txt_mut, bg=bg_side, anchor="w").pack(fill=tk.X, padx=10, pady=(0, 4))
    tk.Frame(parent, bg=border, height=1).pack(fill=tk.X, padx=6, pady=(0, 4))

    map_f = tk.Frame(parent, bg=bg_side)
    map_f.pack(fill=tk.X, padx=4)
    app._sidebar_preview_btns = {}
    build_plate_grid_fn(map_f, app._sidebar_preview_btns)
    for tok, btn in app._sidebar_preview_btns.items():
        btn.config(command=lambda t=tok: app._preview_pick_well(t))

    app._preview_sel_lbl = tk.Label(parent, text="No well selected", font=fm_tiny, fg=txt_mut, bg=bg_side, anchor="w")
    app._preview_sel_lbl.pack(fill=tk.X, padx=10, pady=(6, 2))


def preview_pick_well(app, tok: str) -> None:
    if tok not in app._well_paths:
        return
    app._preview_selected_well = None if app._preview_selected_well == tok else tok
    app._refresh_preview_picker()
    app._update_preview(app._preview_selected_well)


def refresh_preview_picker(
    app,
    *,
    button_bg: str,
    button_text: str,
    button_text_disabled: str,
    accent: str,
    clr_white: str,
    clr_accent_dark: str,
    extract_well_token_fn,
) -> None:
    for tok, btn in app._sidebar_preview_btns.items():
        if tok not in app._well_paths:
            btn.config(
                bg=button_bg,
                fg=button_text_disabled,
                state=tk.DISABLED,
                cursor="arrow",
                relief=tk.FLAT,
                activebackground=button_bg,
                activeforeground=button_text,
                disabledforeground=button_text_disabled,
            )
        elif tok == app._preview_selected_well:
            btn.config(
                bg=accent,
                fg=clr_white,
                state=tk.NORMAL,
                cursor="hand2",
                relief=tk.SUNKEN,
                activebackground=clr_accent_dark,
                activeforeground=clr_white,
                disabledforeground=button_text_disabled,
            )
        else:
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
    if hasattr(app, "_preview_sel_lbl"):
        if app._preview_selected_well:
            app._preview_sel_lbl.config(text=f"Selected: {app._preview_selected_well}")
        else:
            app._preview_sel_lbl.config(text="No well selected")

    # Force Tkinter to process pending drawing updates immediately
    app.update_idletasks()
