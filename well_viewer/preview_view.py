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
    label = app._tok_to_label.get(tok)
    if label is None:
        return
    app._preview_selected_well = None if app._preview_selected_well == label else label
    app._refresh_preview_picker()
    app._update_preview(app._preview_selected_well)


def refresh_preview_picker(
    app,
    *,
    bg_cell: str,
    txt_mut: str,
    txt_pri: str,
    accent: str,
    clr_white: str,
    clr_accent_dark: str,
    bg_panel: str,
    bg_hover: str,
    extract_well_token_fn,
) -> None:
    for tok, btn in app._sidebar_preview_btns.items():
        label = app._tok_to_label.get(tok)
        if label is None:
            btn.config(bg=bg_cell, fg=txt_mut, state=tk.DISABLED, cursor="arrow", relief=tk.FLAT)
        elif label == app._preview_selected_well:
            btn.config(bg=accent, fg=clr_white, state=tk.NORMAL, activebackground=clr_accent_dark, cursor="hand2", relief=tk.SUNKEN)
        else:
            btn.config(bg=bg_panel, fg=txt_pri, state=tk.NORMAL, activebackground=bg_hover, cursor="hand2", relief=tk.FLAT)
    if hasattr(app, "_preview_sel_lbl"):
        if app._preview_selected_well:
            tok = extract_well_token_fn(app._preview_selected_well) or app._preview_selected_well
            app._preview_sel_lbl.config(text=f"Selected: {tok}")
        else:
            app._preview_sel_lbl.config(text="No well selected")

    # Force Tkinter to process pending drawing updates immediately
    app.update_idletasks()
