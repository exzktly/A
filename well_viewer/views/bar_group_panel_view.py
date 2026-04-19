"""Bar-plot group panel builders extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def build_bar_group_panel(app, parent: tk.Frame) -> None:
    """
    Left panel of the Bar Plots tab.

    Reuses the export-panel design:
      • Scrollable card list of named groups (+ Add / Rename / Delete)
      • 8×12 plate map for drag-assignment of wells to the active group
      • Each group becomes one bar in the bar plots (mean ± SD/SEM across
        its member wells)

    When no groups are defined the bar plot falls back to one bar per well
    (the original per-well mode).
    """
    from well_viewer.runtime_app import (
        BG_SIDE, FM_BOLD, FM_TINY, TXT_MUT, BORDER,
        build_plate_grid, _bind_drag, make_scrollable_canvas,
    )

    # Title row + group-list actions.
    hdr1 = tk.Frame(parent, bg=BG_SIDE, pady=3, padx=8)
    hdr1.pack(fill=tk.X)
    tk.Label(hdr1, text="PLATE MAP", font=FM_BOLD, fg=TXT_MUT,
             bg=BG_SIDE).pack(side=tk.LEFT)
    tk.Label(hdr1, text="(right-drag to toggle visibility)",
             font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(
             side=tk.LEFT, padx=(6, 0))
    ttk.Button(
        hdr1, text="+ Add Group", command=app._bar_add_group, style="ActionIndigo.TButton"
    ).pack(side=tk.RIGHT)
    ttk.Button(
        hdr1, text="Clear All", command=app._bar_clear_all_groups, style="Secondary.TButton"
    ).pack(side=tk.RIGHT, padx=(0, 6))

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

    # ── Plate map FIRST (top) ─────────────────────────────────────────────
    tk.Label(parent,
             text="Left-drag: add wells to active replicate set  ·  "
                  "Right-click/drag: toggle group bar-plot visibility",
             font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, pady=3,
             anchor="w", wraplength=300).pack(fill=tk.X, padx=6)

    app._bar_map_frame = tk.Frame(parent, bg=BG_SIDE)
    app._bar_map_frame.pack(fill=tk.X, padx=4)

    app._bar_map_btns: dict = {}
    app._bar_drag_adding   = True
    app._bar_drag_visited: set = set()
    build_plate_grid(app._bar_map_frame, app._bar_map_btns)
    _bind_drag(app._bar_map_frame, app._bar_map_btns,
               app._bg_press, app._bg_drag, app._bg_release)
    # Right-click drag: rubber-band rectangle to toggle group visibility
    _bind_drag(app._bar_map_frame, app._bar_map_btns,
               app._bg_vis_press, app._bg_vis_drag, app._bg_vis_release,
               button=3)

    # Rubber-band state — drawn on a transparent canvas overlaid on the
    # plate-map frame.  Using a Canvas avoids the Toplevel z-order and
    # event-capture problems on Windows.
    app._vis_rubber_win  = None
    app._vis_rubber_rect = None

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(4, 0))

    # ── Scrollable group card list BELOW the plate map ────────────────────
    sf = tk.Frame(parent, bg=BG_SIDE)
    sf.pack(fill=tk.BOTH, expand=True)
    app._bar_grp_canvas, app._bar_grp_inner = make_scrollable_canvas(
        sf, bg=BG_SIDE)

    # No-groups hint (shown at the bottom of the groups sidebar)
    app._bar_grp_count_lbl = tk.Label(
        parent, text="No groups defined",
        font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, anchor="w")
    app._bar_grp_count_lbl.pack(fill=tk.X, padx=6, pady=(0, 2))


def build_bar_perwell_strip(app, parent: tk.Frame) -> None:
    """
    Thin bar-specific sidebar strip shown only when Bar Plots tab is active.
    Contains the All/None per-well selection buttons that are irrelevant
    when the Groups tab or Batch Export is active.
    """
    from well_viewer.runtime_app import BORDER, FM_TINY, TXT_MUT, BG_SIDE

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)
    lbl = tk.Label(parent,
                   text="Per-well selection (fallback when no groups)",
                   font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, anchor="w")
    lbl.pack(fill=tk.X, padx=6, pady=(3, 1))
    bar_br = tk.Frame(parent, bg=BG_SIDE)
    bar_br.pack(fill=tk.X, padx=6, pady=(0, 4))
    ttk.Button(bar_br, text="All", command=app._bar_select_all,
               style="PrimaryDark.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
    ttk.Button(bar_br, text="None", command=app._bar_select_none,
               style="PrimaryDark.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True)


def rebuild_groups_ui_now(app) -> None:
    """
    Synchronous card-list rebuild + plate-map recolour — no plot redraws.

    Call _bar_rebuild_groups() instead when plot data has actually changed.
    """
    app._grp_ui_pending = False
    for w in app._bar_grp_inner.winfo_children():
        w.destroy()

    for idx, grp in enumerate(app._bar_groups):
        app._build_bar_group_row(idx, grp)
    update_bar_group_count_label(app)

    app._bar_refresh_map()


def update_bar_group_count_label(app) -> None:
    n_grps = len(app._bar_groups)
    n_vis = sum(1 for g in app._bar_groups if not g.hidden)
    n_hid = n_grps - n_vis
    if not hasattr(app, "_bar_grp_count_lbl"):
        return
    if n_grps == 0:
        txt = "No groups defined"
    elif n_hid == 0:
        txt = f"{n_grps} group(s)  ·  all visible in bar plot"
    else:
        txt = f"{n_vis}/{n_grps} visible in bar plot  ·  {n_hid} hidden"
    app._bar_grp_count_lbl.config(text=txt)


def build_bar_group_row(app, idx: int, grp) -> None:
    from well_viewer.runtime_app import BG_HOVER, BG_PANEL, ACCENT, BORDER

    is_active = idx == app._bar_active_grp
    bg = BG_HOVER if is_active else BG_PANEL
    row = tk.Frame(
        app._bar_grp_inner,
        bg=bg,
        highlightthickness=1,
        highlightbackground=ACCENT if is_active else BORDER,
    )
    row.pack(fill=tk.X, padx=4, pady=2)

    header, bind_widgets = build_bar_group_header(app, row, idx, grp, bg)
    chip_widgets = build_bar_group_chip_rows(app, row, idx, grp, bg, is_active)
    action_widgets = build_bar_group_action_row(app, row, idx, bg, is_active)
    select_cb = lambda _e, i=idx: app._bar_select_group(i)
    for widget in bind_widgets + chip_widgets + action_widgets:
        widget.bind("<Button-1>", select_cb)


def build_bar_group_header(app, row, idx: int, grp, bg: str) -> tuple:
    from well_viewer.runtime_app import (
        WELL_COLORS, CLR_MUTED_DISABLED, FM_BOLD, FM_TINY,
        TXT_MUT, TXT_PRI, BG_CELL, CLR_SUCCESS, CLR_WARN_BG, CLR_WARN_TEXT,
        TXT_SEC, CLR_DANGER_BG, CLR_DANGER, CLR_DANGER_HOVER, BG_HOVER,
    )

    hdr = tk.Frame(row, bg=bg)
    hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
    color = WELL_COLORS[idx % len(WELL_COLORS)]
    dot_color = CLR_MUTED_DISABLED if grp.hidden else color
    name_fg = TXT_MUT if grp.hidden else TXT_PRI
    dot_lbl = tk.Label(hdr, text="●", font=FM_BOLD, fg=dot_color, bg=bg)
    dot_lbl.pack(side=tk.LEFT, padx=(0, 4))
    name_lbl = tk.Label(hdr, text=grp.name, font=FM_BOLD, fg=name_fg, bg=bg)
    name_lbl.pack(side=tk.LEFT)
    hid_lbl = None
    if grp.hidden:
        hid_lbl = tk.Label(hdr, text="[hidden]", font=FM_TINY, fg=TXT_MUT, bg=bg)
        hid_lbl.pack(side=tk.LEFT, padx=(4, 0))

    n_rep = len(grp.replicates) if grp.replicates else len(grp.wells)
    n_well = len(grp.wells)
    count_lbl = tk.Label(
        hdr,
        text=f"({n_rep} replicate set{'s' if n_rep!=1 else ''}  ·  {n_well} well{'s' if n_well!=1 else ''})",
        font=FM_TINY,
        fg=TXT_MUT,
        bg=bg,
    )
    count_lbl.pack(side=tk.LEFT, padx=(4, 0))

    bf = tk.Frame(hdr, bg=bg)
    bf.pack(side=tk.RIGHT)

    def _cmd(action, i=idx):
        app._bar_active_grp = i
        action(i)

    vis_txt = "Show" if grp.hidden else "Hide"
    vis_bg = BG_CELL if grp.hidden else CLR_WARN_BG
    vis_fg = CLR_SUCCESS if grp.hidden else CLR_WARN_TEXT
    tk.Button(
        bf,
        text=vis_txt,
        command=lambda i=idx: _cmd(app._bar_toggle_group_visibility, i),
        font=FM_TINY,
        bg=vis_bg,
        fg=vis_fg,
        relief=tk.FLAT,
        padx=4,
        cursor="hand2",
        activebackground=BG_HOVER,
    ).pack(side=tk.LEFT, padx=1)
    tk.Button(
        bf,
        text="Rename",
        command=lambda i=idx: _cmd(app._bar_rename_group, i),
        font=FM_TINY,
        bg=BG_CELL,
        fg=TXT_SEC,
        relief=tk.FLAT,
        padx=4,
        cursor="hand2",
        activebackground=BG_HOVER,
    ).pack(side=tk.LEFT, padx=1)
    tk.Button(
        bf,
        text="Clear",
        command=lambda i=idx: _cmd(app._bar_clear_group, i),
        font=FM_TINY,
        bg=BG_CELL,
        fg=TXT_SEC,
        relief=tk.FLAT,
        padx=4,
        cursor="hand2",
        activebackground=BG_HOVER,
    ).pack(side=tk.LEFT, padx=1)
    tk.Button(
        bf,
        text="✕",
        command=lambda i=idx: _cmd(app._bar_remove_group, i),
        font=FM_TINY,
        bg=CLR_DANGER_BG,
        fg=CLR_DANGER,
        relief=tk.FLAT,
        padx=4,
        cursor="hand2",
        activebackground=CLR_DANGER_HOVER,
    ).pack(side=tk.LEFT, padx=1)
    return hdr, [row, hdr, bf, dot_lbl, name_lbl, count_lbl] + ([hid_lbl] if hid_lbl else [])


def build_bar_group_chip_rows(app, row, idx: int, grp, bg: str, is_active: bool) -> list:
    from well_viewer.runtime_app import (
        WELL_COLORS, CLR_MUTED_DISABLED, FM_TINY, TXT_MUT, CLR_WHITE,
        CLR_DANGER_BG, CLR_DANGER, CLR_DANGER_HOVER, _extract_well_token,
    )

    color = WELL_COLORS[idx % len(WELL_COLORS)]
    chip_color = CLR_MUTED_DISABLED if grp.hidden else color
    chip_widgets: list = []
    if grp.replicates:
        rep_frame = tk.Frame(row, bg=bg)
        rep_frame.pack(fill=tk.X, padx=6, pady=(2, 0))
        chip_widgets.append(rep_frame)
        for si, rset in enumerate(grp.replicates):
            srow = tk.Frame(rep_frame, bg=bg)
            srow.pack(fill=tk.X, pady=(2, 0))
            chip_widgets.append(srow)
            bracket = tk.Label(srow, text=f"R{si+1}:", font=FM_TINY, fg=color, bg=bg, padx=2)
            bracket.pack(side=tk.LEFT)
            chip_widgets.append(bracket)
            for w in rset:
                wl = tk.Label(srow, text=w, font=FM_TINY, bg=chip_color, fg=CLR_WHITE, padx=3, pady=1)
                wl.pack(side=tk.LEFT, padx=(0, 2))
                chip_widgets.append(wl)
            if is_active:
                rm_btn = tk.Button(
                    srow,
                    text="✕",
                    command=lambda i=idx, s=si: app._bar_remove_replicate_set(i, s),
                    font=FM_TINY,
                    bg=CLR_DANGER_BG,
                    fg=CLR_DANGER,
                    relief=tk.FLAT,
                    padx=3,
                    cursor="hand2",
                    activebackground=CLR_DANGER_HOVER,
                )
                rm_btn.pack(side=tk.LEFT, padx=(2, 0))
                chip_widgets.append(rm_btn)
        assigned = {w for rs in grp.replicates for w in rs}
        singles = [w for w in grp.wells if w not in assigned]
        if singles:
            singles_row = tk.Frame(rep_frame, bg=bg)
            singles_row.pack(fill=tk.X, pady=(2, 0))
            chip_widgets.append(singles_row)
            tk.Label(singles_row, text="solo:", font=FM_TINY, fg=TXT_MUT, bg=bg, padx=2).pack(side=tk.LEFT)
            for w in singles:
                wl = tk.Label(
                    singles_row,
                    text=w,
                    font=FM_TINY,
                    bg=CLR_MUTED_DISABLED,
                    fg=CLR_WHITE,
                    padx=3,
                    pady=1,
                )
                wl.pack(side=tk.LEFT, padx=(0, 2))
                chip_widgets.append(wl)
    elif grp.wells:
        chips = tk.Frame(row, bg=bg)
        chips.pack(fill=tk.X, padx=6, pady=(2, 0))
        chip_widgets.append(chips)
        for lbl in grp.wells:
            cl = tk.Label(chips, text=lbl, font=FM_TINY, bg=chip_color, fg=CLR_WHITE, padx=4, pady=1)
            cl.pack(side=tk.LEFT, padx=(0, 2), pady=1)
            chip_widgets.append(cl)
    else:
        empty_lbl = tk.Label(
            row,
            text="No wells — assign replicates from the map",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=bg,
            padx=6,
        )
        empty_lbl.pack(anchor="w", padx=6, pady=(0, 4))
        chip_widgets.append(empty_lbl)
    return chip_widgets


def build_bar_group_action_row(app, row, idx: int, bg: str, is_active: bool) -> list:
    from well_viewer.runtime_app import FM_TINY, BG_CELL, TXT_SEC, CLR_DANGER_BG, CLR_DANGER, CLR_DANGER_HOVER, BG_HOVER

    if not is_active:
        return []
    act_frame = tk.Frame(row, bg=bg)
    act_frame.pack(fill=tk.X, padx=6, pady=(4, 4))
    tk.Button(
        act_frame,
        text="+ Add replicate set",
        command=lambda i=idx: app._bar_add_replicate_set(i),
        font=FM_TINY,
        bg=BG_CELL,
        fg=TXT_SEC,
        relief=tk.FLAT,
        padx=5,
        cursor="hand2",
        activebackground=BG_HOVER,
    ).pack(side=tk.LEFT)
    tk.Button(
        act_frame,
        text="Clear replicates",
        command=lambda i=idx: app._bar_clear_replicates(i),
        font=FM_TINY,
        bg=BG_CELL,
        fg=TXT_SEC,
        relief=tk.FLAT,
        padx=5,
        cursor="hand2",
        activebackground=BG_HOVER,
    ).pack(side=tk.LEFT, padx=(4, 0))
    return [act_frame]
