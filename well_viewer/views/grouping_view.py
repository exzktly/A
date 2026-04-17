"""Replicate/group card-list UI builders extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from well_viewer.ui_helpers import btn_card, btn_danger


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
                    rt.tk.Label(chips, text=w, font=rt.FM_TINY, bg=accent, fg=clr_white, padx=4, pady=1).pack(side=rt.tk.LEFT, padx=(0, 2), pady=1)
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
    """Rebuild the group card list in the Sample Definitions tab."""
    from well_viewer.runtime_app import (
        FM_BOLD, FM_TINY, WELL_COLORS, CLR_MUTED_DISABLED, BG_HOVER, BG_PANEL,
        ACCENT, BORDER, TXT_MUT, TXT_PRI, BG_APP, BG_CELL,
        CLR_SUCCESS, CLR_WARN_TEXT, CLR_WARN_BG, CLR_WHITE,
        _extract_well_token, _btn_card, _btn_danger,
    )

    if not hasattr(app, "_grp_inner"):
        return
    for w in app._grp_inner.winfo_children():
        w.destroy()

    if not app._bar_groups:
        tk.Label(app._grp_inner,
                 text="No groups defined.\nClick + Add to create one.",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                 justify=tk.LEFT).pack(anchor="w", padx=8, pady=8)
        return

    for gi, grp in enumerate(app._bar_groups):
        is_sel = (gi == app._bar_active_grp)
        color  = WELL_COLORS[gi % len(WELL_COLORS)]
        dot_c  = CLR_MUTED_DISABLED if grp.hidden else color
        bg     = BG_HOVER if is_sel else BG_PANEL

        card = tk.Frame(app._grp_inner, bg=bg,
                        highlightthickness=1,
                        highlightbackground=ACCENT if is_sel else BORDER)
        card.pack(fill=tk.X, padx=4, pady=2)

        hdr = tk.Frame(card, bg=bg)
        hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
        tk.Label(hdr, text="●", font=FM_BOLD, fg=dot_c,
                 bg=bg).pack(side=tk.LEFT, padx=(0, 4))
        name_fg = TXT_MUT if grp.hidden else TXT_PRI
        if is_sel:
            name_var = tk.StringVar(value=grp.name)
            name_ent = tk.Entry(
                hdr,
                textvariable=name_var,
                font=FM_BOLD,
                fg=name_fg,
                bg=bg,
                relief=tk.FLAT,
                insertbackground=name_fg,
                highlightthickness=1,
                highlightbackground=BORDER,
                highlightcolor=ACCENT,
                width=max(10, len(grp.name) + 2),
            )
            name_ent.pack(side=tk.LEFT, padx=(0, 4))

            def _commit_name(_e=None, i=gi, var=name_var):
                new_name = str(var.get() or "").strip()
                if not new_name:
                    var.set(app._bar_groups[i].name)
                    return
                if new_name != app._bar_groups[i].name:
                    app._bar_groups[i].name = new_name
                    app._rebuild_all()

            name_ent.bind("<Return>", _commit_name)
            name_ent.bind("<FocusOut>", _commit_name)
        else:
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
                  command=lambda i=gi: app._grp_toggle_visibility(i),
                  font=FM_TINY, bg=vis_bg, fg=vis_fg,
                  relief=tk.FLAT, padx=4, cursor="hand2",
                  activebackground=BG_HOVER).pack(side=tk.LEFT, padx=1)
        _btn_danger(bf, "✕", lambda i=gi: app._grp_delete(i)).pack(side=tk.LEFT, padx=1)

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
                    tk.Label(mrow, text=w, font=FM_TINY,
                             bg=dot_c, fg=CLR_WHITE,
                             padx=3, pady=1).pack(side=tk.LEFT, padx=(0, 2))
                if is_sel:
                    _btn_danger(mrow, "−", lambda g=gi, r=rset: app._grp_remove_member(g, r),
                                padx=3).pack(side=tk.LEFT, padx=(4, 0))
            for w in grp.solo_wells:
                srow = tk.Frame(mem_frame, bg=bg)
                srow.pack(fill=tk.X, pady=1)
                tk.Label(srow, text=f"[solo] {w}", font=FM_TINY,
                         fg=dot_c, bg=bg).pack(side=tk.LEFT)
                if is_sel:
                    _btn_danger(srow, "−", lambda g=gi, wl=w: app._grp_remove_solo(g, wl),
                                padx=3).pack(side=tk.LEFT, padx=(4, 0))
        else:
            tk.Label(card, text="Empty — add replicate sets or wells below",
                     font=FM_TINY, fg=TXT_MUT, bg=bg,
                     padx=6).pack(anchor="w", padx=6, pady=(0, 2))

        # Active group: add replicate sets and/or individual wells
        if is_sel:
            act_rep = tk.Frame(card, bg=bg)
            act_rep.pack(fill=tk.X, padx=6, pady=(2, 0))
            if app._rep_sets:
                tk.Label(act_rep, text="+ Set:", font=FM_TINY,
                         fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)
                for rset in app._rep_sets:
                    if rset not in grp.members:
                        _btn_card(act_rep, rset.name,
                                  lambda r=rset, g=gi: app._grp_add_member(g, r)
                                  ).pack(side=tk.LEFT, padx=2)
            else:
                tk.Label(act_rep,
                         text="(No replicate sets — define them in the left panel)",
                         font=FM_TINY, fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)

            assigned_wells = set(grp.wells)
            unassigned = [tok for tok in sorted(
                              app._well_paths.keys(),
                              key=lambda t: app._parse_rc(t))
                          if tok not in assigned_wells]
            if unassigned:
                act_well = tk.Frame(card, bg=bg)
                act_well.pack(fill=tk.X, padx=6, pady=(2, 4))
                tk.Label(act_well, text="+ Well:", font=FM_TINY,
                         fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)
                for tok in unassigned:
                    _btn_card(act_well, tok,
                              lambda wl=tok, g=gi: app._grp_add_solo_well(g, wl)
                              ).pack(side=tk.LEFT, padx=2)
            else:
                tk.Frame(card, bg=bg, height=4).pack()  # spacing

        sel_cb = lambda _e, i=gi: app._grp_select(i)
        for widget in [card, hdr, bf]:
            widget.bind("<Button-1>", sel_cb)


def build_group_def_panel(app, parent: tk.Frame) -> None:
    """Right panel of Sample Definitions tab: combine ReplicateSets into BarGroups."""
    from well_viewer.runtime_app import (
        BORDER, BG_SIDE, FM_BOLD, TXT_MUT, FM_TINY, TXT_PRI, BG_APP,
        _btn_primary, _btn_secondary, make_scrollable_canvas,
    )

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

    hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="GROUPS", font=FM_BOLD,
             fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
    _btn_primary(hdr, "+ Add", app._grp_add).pack(side=tk.RIGHT)
    _btn_secondary(hdr, "Clear All", app._grp_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

    # Second row: Quick Groups dropdowns (full setup: replicates + groups)
    hdr2g = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
    hdr2g.pack(fill=tk.X)

    # Pair direction dropdown
    tk.Label(hdr2g, text="Pair:", font=FM_TINY, fg=TXT_PRI,
             bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
    app._bar_quick_pair_dir_var = tk.StringVar(value="Rows (A01+A02)")
    pair_dir_cb_bar = ttk.Combobox(
        hdr2g,
        textvariable=app._bar_quick_pair_dir_var,
        values=["Rows (A01+A02)", "Columns (A01+B01)"],
        state="readonly",
        width=18)
    pair_dir_cb_bar.pack(side=tk.LEFT, padx=(0, 8))

    # Iteration order dropdown
    tk.Label(hdr2g, text="Order:", font=FM_TINY, fg=TXT_PRI,
             bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
    app._bar_quick_iter_order_var = tk.StringVar(value="Across rows")
    iter_order_cb_bar = ttk.Combobox(
        hdr2g,
        textvariable=app._bar_quick_iter_order_var,
        values=["Across rows", "Down columns"],
        state="readonly",
        width=14)
    iter_order_cb_bar.pack(side=tk.LEFT, padx=(0, 4))

    # Apply button on separate row below dropdowns
    btn_row_bar = tk.Frame(parent, bg=BG_SIDE, pady=2, padx=8)
    btn_row_bar.pack(fill=tk.X)
    _btn_primary(btn_row_bar, "Apply Quick Groups", app._bar_quick_groups_from_dropdowns).pack(side=tk.LEFT, padx=(0, 4))
    _btn_secondary(btn_row_bar, "Save…", app._bar_save_groups).pack(side=tk.LEFT, padx=(0, 2))
    _btn_secondary(btn_row_bar, "Load…", app._bar_load_groups).pack(side=tk.LEFT, padx=(0, 2))

    tk.Label(parent,
             text="Each group produces one bar/line on the plot. "
                  "Add replicate sets or individual wells to a group.",
             font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
             wraplength=280, justify=tk.LEFT).pack(
             fill=tk.X, padx=8, pady=(4, 2))

    sf = tk.Frame(parent, bg=BG_APP)
    sf.pack(fill=tk.BOTH, expand=True)
    app._grp_canvas, app._grp_inner = make_scrollable_canvas(sf, bg=BG_APP)
