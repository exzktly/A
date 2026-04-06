"""Replicate/group card-list UI builders extracted from runtime_app."""

from __future__ import annotations

from well_viewer.ui_support import btn_card, btn_danger


def rep_panel_refresh(app) -> None:
    from well_viewer import runtime_app as rt
    from ui.theme import get_color

    compact_threshold = 8
    if not hasattr(app, "_rep_inner"):
        return
    for w in app._rep_inner.winfo_children():
        w.destroy()

    # Get current theme colors
    txt_mut = get_color("TXT_MUT")
    bg_app = get_color("BG_APP")
    bg_panel = get_color("BG_PANEL")
    bg_hover = get_color("BG_HOVER")
    accent = get_color("ACCENT")
    border = get_color("BORDER")
    txt_pri = get_color("TXT_PRI")
    clr_white = get_color("CLR_WHITE")

    if not app._rep_sets:
        rt.tk.Label(app._rep_inner, text="No replicate sets defined yet.\nClick + Add to create one.", font=rt.FM_TINY, fg=txt_mut, bg=bg_app, justify=rt.tk.LEFT).pack(anchor="w", padx=8, pady=8)
        app._rep_refresh_map()
        return
    compact = len(app._rep_sets) > compact_threshold
    for si, rset in enumerate(app._rep_sets):
        is_sel = si == app._active_rep_idx
        bg = bg_hover if is_sel else bg_panel
        use_full = is_sel or not compact
        card = rt.tk.Frame(app._rep_inner, bg=bg, highlightthickness=1, highlightbackground=accent if is_sel else border)
        card.pack(fill=rt.tk.X, padx=4, pady=1)
        if use_full:
            hdr = rt.tk.Frame(card, bg=bg)
            hdr.pack(fill=rt.tk.X, padx=6, pady=(4, 2))
            rt.tk.Label(hdr, text=rset.name, font=rt.FM_BOLD, fg=txt_pri, bg=bg).pack(side=rt.tk.LEFT)
            n = len(rset.wells)
            rt.tk.Label(hdr, text=f"  {n} well{'s' if n!=1 else ''}", font=rt.FM_TINY, fg=txt_mut, bg=bg).pack(side=rt.tk.LEFT)
            bf = rt.tk.Frame(hdr, bg=bg)
            bf.pack(side=rt.tk.RIGHT)
            btn_card(bf, "Rename", lambda i=si: app._rep_rename(i)).pack(side=rt.tk.LEFT, padx=1)
            btn_card(bf, "Edit wells", lambda i=si: app._rep_edit_wells(i)).pack(side=rt.tk.LEFT, padx=1)
            btn_danger(bf, "\u2715", lambda i=si: app._rep_delete(i)).pack(side=rt.tk.LEFT, padx=1)
            if rset.wells:
                chips = rt.tk.Frame(card, bg=bg)
                chips.pack(fill=rt.tk.X, padx=6, pady=(0, 4))
                for w in rset.wells:
                    tok = rt._extract_well_token(w) or w
                    rt.tk.Label(chips, text=tok, font=rt.FM_TINY, bg=accent, fg=clr_white, padx=4, pady=1).pack(side=rt.tk.LEFT, padx=(0, 2), pady=1)
        else:
            row = rt.tk.Frame(card, bg=bg)
            row.pack(fill=rt.tk.X, padx=6, pady=2)
            color = rt.WELL_COLORS[si % len(rt.WELL_COLORS)]
            rt.tk.Label(row, text="\u25cf", font=rt.FM_TINY, fg=color, bg=bg).pack(side=rt.tk.LEFT, padx=(0, 4))
            rt.tk.Label(row, text=rset.name, font=rt.FM_TINY, fg=txt_pri, bg=bg).pack(side=rt.tk.LEFT)
            n = len(rset.wells)
            rt.tk.Label(row, text=f"  ({n}w)", font=rt.FM_TINY, fg=txt_mut, bg=bg).pack(side=rt.tk.LEFT)
        sel_cb = lambda _e, i=si: app._rep_select(i)
        card.bind("<Button-1>", sel_cb)
        for child in card.winfo_children():
            if not isinstance(child, rt.tk.Button):
                child.bind("<Button-1>", sel_cb)
    app._rep_refresh_map()


def grp_panel_refresh(app) -> None:
    from well_viewer import runtime_app as rt
    from ui.theme import get_color

    if not hasattr(app, "_grp_inner"):
        return
    for w in app._grp_inner.winfo_children():
        w.destroy()

    # Get current theme colors
    txt_mut = get_color("TXT_MUT")
    bg_app = get_color("BG_APP")
    bg_panel = get_color("BG_PANEL")
    bg_hover = get_color("BG_HOVER")
    bg_cell = get_color("BG_CELL")
    accent = get_color("ACCENT")
    border = get_color("BORDER")
    txt_pri = get_color("TXT_PRI")
    clr_muted_disabled = get_color("CLR_MUTED_DISABLED")
    clr_success = get_color("CLR_SUCCESS")
    clr_warn_text = get_color("CLR_WARN_TEXT")
    clr_warn_bg = get_color("CLR_WARN_BG")

    if not app._bar_groups:
        rt.tk.Label(app._grp_inner, text="No groups defined.\nClick + Add to create one.", font=rt.FM_TINY, fg=txt_mut, bg=bg_app, justify=rt.tk.LEFT).pack(anchor="w", padx=8, pady=8)
        return
    for gi, grp in enumerate(app._bar_groups):
        is_sel = gi == app._bar_active_grp
        color = rt.WELL_COLORS[gi % len(rt.WELL_COLORS)]
        dot_c = clr_muted_disabled if grp.hidden else color
        bg = bg_hover if is_sel else bg_panel
        card = rt.tk.Frame(app._grp_inner, bg=bg, highlightthickness=1, highlightbackground=accent if is_sel else border)
        card.pack(fill=rt.tk.X, padx=4, pady=2)
        hdr = rt.tk.Frame(card, bg=bg)
        hdr.pack(fill=rt.tk.X, padx=6, pady=(4, 2))
        rt.tk.Label(hdr, text="●", font=rt.FM_BOLD, fg=dot_c, bg=bg).pack(side=rt.tk.LEFT, padx=(0, 4))
        name_fg = txt_mut if grp.hidden else txt_pri
        rt.tk.Label(hdr, text=grp.name, font=rt.FM_BOLD, fg=name_fg, bg=bg).pack(side=rt.tk.LEFT)
        if grp.hidden:
            rt.tk.Label(hdr, text="[hidden]", font=rt.FM_TINY, fg=txt_mut, bg=bg).pack(side=rt.tk.LEFT, padx=(4, 0))
        n_sets = len(grp.members)
        n_wells = len(grp.wells)
        rt.tk.Label(hdr, text=f"  {n_sets} set{'s' if n_sets!=1 else ''}  ·  {n_wells} well{'s' if n_wells!=1 else ''}", font=rt.FM_TINY, fg=txt_mut, bg=bg).pack(side=rt.tk.LEFT)
        bf = rt.tk.Frame(hdr, bg=bg)
        bf.pack(side=rt.tk.RIGHT)
        vis_txt = "Show" if grp.hidden else "Hide"
        vis_bg = bg_cell if grp.hidden else clr_warn_bg
        vis_fg = clr_success if grp.hidden else clr_warn_text
        rt.tk.Button(bf, text=vis_txt, command=lambda i=gi: app._grp_toggle_visibility(i), font=rt.FM_TINY, bg=vis_bg, fg=vis_fg, relief=rt.tk.FLAT, padx=4, cursor="hand2", activebackground=bg_hover).pack(side=rt.tk.LEFT, padx=1)
        btn_card(bf, "Rename", lambda i=gi: app._grp_rename(i)).pack(side=rt.tk.LEFT, padx=1)
        btn_danger(bf, "✕", lambda i=gi: app._grp_delete(i)).pack(side=rt.tk.LEFT, padx=1)
        sel_cb = lambda _e, i=gi: app._grp_select(i)
        for widget in [card, hdr, bf]:
            widget.bind("<Button-1>", sel_cb)
