"""Batch-export dialog classes and launch helpers extracted from well_viewer3."""

from __future__ import annotations

# Dialogs still rely on shared legacy UI constants/utilities while extraction is in progress.
from well_viewer.runtime_app import (
    ACCENT,
    ACCENT_DARK,
    BG_APP,
    BG_CELL,
    BG_HOVER,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    CLR_AVAIL_HOVER,
    CLR_AVAIL_WELL,
    CLR_DANGER,
    CLR_DANGER_BG,
    CLR_DANGER_HOVER,
    CLR_DISABLED_WELL,
    CLR_ERR_BAR,
    CLR_PLACEHOLDER,
    CLR_SUCCESS,
    CLR_SUCCESS_DARK,
    CLR_WHITE,
    FM_BOLD,
    FM_MONO,
    FM_TINY,
    PLOT_BG,
    PLOT_SPN,
    TXT_MUT,
    TXT_PRI,
    TXT_SEC,
    WARN,
    WELL_COLORS,
    _PLATE_COLS,
    _PLATE_ROWS,
    _all_fluor_values,
    _bind_drag,
    _extract_well_token,
    _groups_with_loaded_wells,
    _logger,
    _read_pipeline_info_shared,
    _selected_listbox_values,
    aggregate_with_threshold,
    apply_ax_style,
    ask_name_dialog,
    build_plate_grid,
    make_scrollable_canvas,
    copy,
    csv,
    filedialog,
    json,
    math,
    messagebox,
    re,
    tk,
    ttk,
)
from well_viewer.batch_models import BarGroup
from well_viewer.barplot_controller import render_bar_items as _bar_render_items
from well_viewer.ui_helpers import btn_card, btn_danger, btn_primary, btn_secondary
from pathlib import Path
from typing import Dict, List, Optional


class BatchExportPanel(tk.Frame):
    """
    Batch export dialog — defines export groups and runs the export.

    The interactive group creator lives here (not in the main Groups tab).
    A group is a named collection of ReplicateSets (or solo wells) that will
    appear together on a single exported figure — one line per member.

    Statistics:
      - Within a ReplicateSet: wells are averaged → one mean fluorescence value per set.
      - Across members of a group: NO combined stat is computed.
        Each member gets its own line on the combined figure.

    Layout
    ------
    Left  : Group editor — plate map + group card list (Quick Setup rows/cols,
            Save, Load).
    Right : Output settings + Run.
    """

    def __init__(
        self,
        app: "WellViewerApp",
        parent: tk.Widget,
        *,
        use_sidebar_groups: bool = False,
    ) -> None:
        super().__init__(parent, bg=BG_APP)
        self._app = app
        self._use_sidebar_groups = bool(use_sidebar_groups)

        default_out = str(app._data_dir) if app._data_dir else ""
        export_prefs = getattr(app, "_export_style_prefs", {}) or {}
        default_fmt = str(export_prefs.get("format", "png")).lower()
        if default_fmt not in {"png", "svg", "eps", "pdf"}:
            default_fmt = "png"
        self._out_dir_var = tk.StringVar(value=default_out)
        self._fmt_var     = tk.StringVar(value=default_fmt)
        self._active_grp  = -1   # index of selected export group

        # Initialise groups from rep-sets (one group per set).
        # Falls back to a deep-copy of _bar_groups if rep-sets are empty,
        # for backward compatibility with saved sessions.
        self._groups: List["BarGroup"] = self._groups_from_rep_sets()

        self._build_ui()
        if not self._use_sidebar_groups:
            self._refresh_group_list()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        tk.Frame(self, bg=BORDER, height=1).pack(side=tk.TOP, fill=tk.X)

        # Body: left = group editor, right = output + run (or right-only when
        # group editing is delegated to the app sidebar).
        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill=tk.BOTH, expand=True)

        if self._use_sidebar_groups:
            self._build_output_panel(body)
            return

        # ── Left: group editor ────────────────────────────────────────────────
        left = tk.Frame(body, bg=BG_SIDE, width=520)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._build_group_editor(left)

        tk.Frame(body, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # ── Right: output settings + run ──────────────────────────────────────
        right = tk.Frame(body, bg=BG_APP)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_output_panel(right)

    def _build_group_editor(self, parent: tk.Frame) -> None:
        """Left panel: plate map + group card list."""
        # Header row 1: title + add/clear
        hdr1 = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
        hdr1.pack(fill=tk.X)
        tk.Label(hdr1, text="EXPORT GROUPS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        btn_primary(hdr1, "+ Add", self._grp_add).pack(side=tk.RIGHT)
        btn_secondary(hdr1, "Clear All", self._grp_clear_all).pack(side=tk.RIGHT, padx=(0, 4))

        # Header row 2: Quick Setup + Save + Load
        hdr2 = tk.Frame(parent, bg=BG_SIDE, pady=2, padx=8)
        hdr2.pack(fill=tk.X)
        qs_btn = ttk.Menubutton(hdr2, text="Quick Setup ▾", style="TButton")
        qs_btn.pack(side=tk.LEFT)
        qs_menu = tk.Menu(qs_btn, tearoff=False)
        qs_menu.add_command(
            label="One group per row  (Row A = all A wells, …)",
            command=self._quick_by_row)
        qs_menu.add_command(
            label="One group per column  (Col 01 = all col-01 wells, …)",
            command=self._quick_by_col)
        qs_btn["menu"] = qs_menu
        btn_secondary(hdr2, "Save…", self._save_groups).pack(side=tk.LEFT, padx=(8, 2))
        btn_secondary(hdr2, "Load…", self._load_groups).pack(side=tk.LEFT, padx=(0, 2))
        btn_secondary(hdr2, "Sync from app", self._sync_from_app).pack(side=tk.LEFT, padx=(8, 0))

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)
        tk.Label(parent,
                 text="Left-drag wells onto the plate map to add them to the selected group.",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, pady=3,
                 anchor="w", wraplength=490).pack(fill=tk.X, padx=6)

        # Plate map
        map_frame = tk.Frame(parent, bg=BG_SIDE)
        map_frame.pack(fill=tk.X, padx=4)
        self._map_btns: Dict[str, tk.Button] = {}
        build_plate_grid(map_frame, self._map_btns)

        # Drag state
        self._drag_adding:  bool = True
        self._drag_visited: set  = set()

        def _tok_at(event) -> Optional[str]:
            sx = event.widget.winfo_rootx() + event.x
            sy = event.widget.winfo_rooty() + event.y
            w  = event.widget.winfo_containing(sx, sy)
            for tok, btn in self._map_btns.items():
                if btn is w:
                    return tok
            return None

        def _press(event):
            tok = _tok_at(event)
            if tok is None or tok not in self._app._tok_to_label:
                return
            grp = self._active_group()
            if grp is None:
                return
            label = self._app._tok_to_label[tok]
            self._drag_adding  = label not in grp.wells
            self._drag_visited = set()
            self._apply_drag(tok)

        def _drag(event):
            tok = _tok_at(event)
            if tok and tok not in self._drag_visited:
                self._apply_drag(tok)

        def _release(_event):
            if self._drag_visited:
                self._refresh_map()
                self._refresh_group_list()
            self._drag_visited = set()

        _bind_drag(map_frame, self._map_btns, _press, _drag, _release)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(4, 0))

        # Scrollable group card list
        sf = tk.Frame(parent, bg=BG_SIDE)
        sf.pack(fill=tk.BOTH, expand=True)
        self._grp_canvas, self._grp_inner = make_scrollable_canvas(sf, bg=BG_SIDE)

    def _build_output_panel(self, parent: tk.Frame) -> None:
        """Right panel: export settings and Run button."""
        hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="OUTPUT SETTINGS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)

        out_row = tk.Frame(parent, bg=BG_APP, pady=6, padx=12)
        out_row.pack(fill=tk.X)
        tk.Label(out_row, text="Folder:", font=FM_BOLD,
                 fg=TXT_SEC, bg=BG_APP).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(out_row, textvariable=self._out_dir_var,
                 font=FM_TINY, fg=TXT_PRI, bg=BG_PANEL,
                 relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
                 anchor="w", padx=6, width=30).pack(side=tk.LEFT)
        btn_secondary(out_row, "Browse…", self._browse_out_dir,
                      padx=8).pack(side=tk.LEFT, padx=(6, 0))

        fmt_row = tk.Frame(parent, bg=BG_APP, padx=12, pady=4)
        fmt_row.pack(fill=tk.X)
        tk.Label(fmt_row, text="Format:", font=FM_BOLD,
                 fg=TXT_SEC, bg=BG_APP).pack(side=tk.LEFT, padx=(0, 6))
        fmt_cb = ttk.Combobox(fmt_row, textvariable=self._fmt_var,
                              values=["png", "svg", "eps", "pdf"],
                              state="readonly", width=6, font=FM_TINY)
        fmt_cb.pack(side=tk.LEFT)
        self._fmt_hint = tk.Label(fmt_row, text="300 DPI raster",
                                  font=FM_TINY, fg=TXT_MUT, bg=BG_APP)
        self._fmt_hint.pack(side=tk.LEFT, padx=(6, 0))
        fmt_cb.bind("<<ComboboxSelected>>", self._on_fmt_change)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(8, 4))

        info = tk.Label(parent,
                        text=("Each export group produces:\n"
                              "  \u2022 One figure with one line per group member\n"
                              "    (ReplicateSet = mean of its wells, Solo well = raw)\n"
                              "  \u2022 One CSV with per-member time-series data\n\n"
                              f"{'Groups come from Sample Definitions in the left sidebar.' if self._use_sidebar_groups else 'Groups are defined in the left panel.'}\n"
                              "No statistics are computed across group members.\n"
                              "SD/SEM is only computed within a ReplicateSet."),
                        font=FM_TINY, fg=TXT_SEC, bg=BG_APP,
                        justify=tk.LEFT, anchor="w")
        info.pack(anchor="w", padx=12)

        run_row = tk.Frame(parent, bg=BG_APP, pady=12, padx=12)
        run_row.pack(fill=tk.X)
        self._run_btn = tk.Button(run_row, text="▶  Run Batch Export",
                                  command=self._run_batch,
                                  font=FM_BOLD, fg=CLR_WHITE, bg=CLR_SUCCESS,
                                  activebackground=CLR_SUCCESS_DARK,
                                  relief=tk.FLAT, padx=16, pady=6,
                                  cursor="hand2", bd=0)
        self._run_btn.pack(side=tk.LEFT)
        self._prog_lbl = tk.Label(run_row, text="", font=FM_TINY,
                                  fg=TXT_MUT, bg=BG_APP)
        self._prog_lbl.pack(side=tk.LEFT, padx=12)
        self._prog_bar = ttk.Progressbar(run_row, orient=tk.HORIZONTAL,
                                          mode="determinate", length=180)
        self._prog_bar.pack(side=tk.LEFT)
        self._prog_bar.pack_forget()

    # ── Group editor helpers ──────────────────────────────────────────────────

    def _active_group(self) -> Optional["BarGroup"]:
        if 0 <= self._active_grp < len(self._groups):
            return self._groups[self._active_grp]
        return None

    def _apply_drag(self, tok: str) -> None:
        if tok in self._drag_visited:
            return
        self._drag_visited.add(tok)
        grp = self._active_group()
        if grp is None or tok not in self._app._tok_to_label:
            return
        label = self._app._tok_to_label[tok]
        # Find if label belongs to a ReplicateSet in the pool
        rset = next((r for r in self._app._rep_sets if label in r.wells), None)
        if rset is not None:
            # Add/remove the whole ReplicateSet
            if self._drag_adding:
                if rset not in grp.members:
                    grp.members.append(rset)
            else:
                if rset in grp.members:
                    grp.members.remove(rset)
        else:
            # Solo well (not in any ReplicateSet)
            if self._drag_adding:
                if label not in grp.solo_wells:
                    grp.solo_wells.append(label)
            else:
                if label in grp.solo_wells:
                    grp.solo_wells.remove(label)
        self._refresh_single_btn(tok)

    def _refresh_single_btn(self, tok: str) -> None:
        grp = self._active_group()
        btn = self._map_btns.get(tok)
        if btn is None:
            return
        if tok not in self._app._tok_to_label:
            return
        label = self._app._tok_to_label[tok]
        # Find group index that owns this well
        for gi, g in enumerate(self._groups):
            if label in g.wells:
                c = WELL_COLORS[gi % len(WELL_COLORS)]
                btn.config(bg=c, fg=CLR_WHITE, activebackground=c)
                return
        btn.config(bg=CLR_AVAIL_WELL, fg=TXT_PRI,
                   activebackground=CLR_AVAIL_HOVER)

    def _refresh_map(self) -> None:
        avail = set(self._app._tok_to_label.keys())
        # Build tok -> (color) from all groups
        tok_color: Dict[str, str] = {}
        for gi, grp in enumerate(self._groups):
            c = WELL_COLORS[gi % len(WELL_COLORS)]
            for w in grp.wells:
                t = _extract_well_token(w) or w
                tok_color.setdefault(t, c)
        active_wells: set = set()
        grp = self._active_group()
        if grp:
            for w in grp.wells:
                active_wells.add(_extract_well_token(w) or w)

        for tok, btn in self._map_btns.items():
            if tok not in avail:
                btn.config(bg=BG_CELL, fg=TXT_MUT, state=tk.DISABLED, cursor="arrow")
            elif tok in tok_color:
                c = tok_color[tok]
                relief = tk.SUNKEN if tok in active_wells else tk.FLAT
                btn.config(bg=c, fg=CLR_WHITE, state=tk.NORMAL,
                           relief=relief, cursor="hand2", activebackground=c)
            else:
                btn.config(bg=CLR_AVAIL_WELL, fg=TXT_PRI, state=tk.NORMAL,
                           relief=tk.FLAT, cursor="hand2",
                           activebackground=CLR_AVAIL_HOVER)

    def _refresh_group_list(self) -> None:
        for w in self._grp_inner.winfo_children():
            w.destroy()
        if not self._groups:
            tk.Label(self._grp_inner,
                     text="No export groups.  Click + Add or use Quick Setup.",
                     font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE,
                     pady=8).pack(anchor="w", padx=8)
            self._refresh_map()
            return

        for gi, grp in enumerate(self._groups):
            is_sel = (gi == self._active_grp)
            color  = WELL_COLORS[gi % len(WELL_COLORS)]
            bg     = BG_HOVER if is_sel else BG_PANEL
            card   = tk.Frame(self._grp_inner, bg=bg, highlightthickness=1,
                              highlightbackground=ACCENT if is_sel else BORDER)
            card.pack(fill=tk.X, padx=4, pady=2)

            hdr = tk.Frame(card, bg=bg)
            hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
            tk.Label(hdr, text="●", font=FM_BOLD, fg=color,
                     bg=bg).pack(side=tk.LEFT, padx=(0, 4))
            tk.Label(hdr, text=grp.name, font=FM_BOLD, fg=TXT_PRI,
                     bg=bg).pack(side=tk.LEFT)
            n_mem = len(grp.members)
            n_sol = len(grp.solo_wells)
            parts = []
            if n_mem: parts.append(f"{n_mem} set{'s' if n_mem!=1 else ''}")
            if n_sol: parts.append(f"{n_sol} solo well{'s' if n_sol!=1 else ''}")
            if not parts: parts = ["empty"]
            tk.Label(hdr, text=f"  ({', '.join(parts)})",
                     font=FM_TINY, fg=TXT_MUT, bg=bg).pack(side=tk.LEFT)

            bf = tk.Frame(hdr, bg=bg)
            bf.pack(side=tk.RIGHT)
            btn_card(bf, "Rename", lambda i=gi: self._grp_rename(i)).pack(side=tk.LEFT, padx=1)
            btn_card(bf, "Clear", lambda i=gi: self._grp_clear(i)).pack(side=tk.LEFT, padx=1)
            btn_danger(bf, "✕", lambda i=gi: self._grp_delete(i)).pack(side=tk.LEFT, padx=1)

            # Members: replicate sets + solo wells
            if grp.members or grp.solo_wells:
                mem_fr = tk.Frame(card, bg=bg)
                mem_fr.pack(fill=tk.X, padx=6, pady=(0, 4))
                for rset in grp.members:
                    mrow = tk.Frame(mem_fr, bg=bg)
                    mrow.pack(fill=tk.X, pady=1)
                    tk.Label(mrow, text=f"[{rset.name}]", font=FM_TINY,
                             fg=color, bg=bg, padx=2).pack(side=tk.LEFT)
                    for w in rset.wells:
                        tok = _extract_well_token(w) or w
                        tk.Label(mrow, text=tok, font=FM_TINY, bg=color,
                                 fg=CLR_WHITE, padx=3, pady=1
                                 ).pack(side=tk.LEFT, padx=(0, 2))
                    if is_sel:
                        btn_danger(mrow, "−", lambda g=gi, r=rset: self._grp_remove_member(g, r),
                                   padx=3).pack(side=tk.LEFT, padx=(4, 0))
                for w in grp.solo_wells:
                    srow = tk.Frame(mem_fr, bg=bg)
                    srow.pack(fill=tk.X, pady=1)
                    tok = _extract_well_token(w) or w
                    tk.Label(srow, text=f"[solo] {tok}", font=FM_TINY,
                             fg=color, bg=bg).pack(side=tk.LEFT)
                    if is_sel:
                        btn_danger(srow, "−", lambda g=gi, wl=w: self._grp_remove_solo(g, wl),
                                   padx=3).pack(side=tk.LEFT, padx=(4, 0))

            sel_cb = lambda _e, i=gi: self._grp_select(i)
            def _bind_grp_card(widget, cb):
                if not isinstance(widget, tk.Button):
                    widget.bind("<Button-1>", cb)
                for child in widget.winfo_children():
                    _bind_grp_card(child, cb)
            _bind_grp_card(card, sel_cb)

        self._refresh_map()

    # ── Group CRUD ────────────────────────────────────────────────────────────

    def _grp_select(self, idx: int) -> None:
        self._active_grp = idx
        self._refresh_group_list()

    def _grp_add(self) -> None:
        name = ask_name_dialog(self, default=f"Group {len(self._groups)+1}")
        if name:
            self._groups.append(BarGroup(name))
            self._active_grp = len(self._groups) - 1
            self._refresh_group_list()

    def _grp_rename(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            name = ask_name_dialog(self, default=self._groups[idx].name)
            if name:
                self._groups[idx].name = name
                self._refresh_group_list()

    def _grp_clear(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            self._groups[idx].members.clear()
            self._groups[idx].solo_wells.clear()
            self._refresh_group_list()

    def _grp_delete(self, idx: int) -> None:
        if 0 <= idx < len(self._groups):
            self._groups.pop(idx)
            self._active_grp = min(self._active_grp, len(self._groups) - 1)
            self._refresh_group_list()

    def _grp_clear_all(self) -> None:
        if not self._groups:
            return
        if messagebox.askyesno("Clear all groups?",
                               f"Remove all {len(self._groups)} group(s)?",
                               parent=self):
            self._groups.clear()
            self._active_grp = -1
            self._refresh_group_list()

    def _grp_remove_member(self, grp_idx: int, rset: "ReplicateSet") -> None:
        if 0 <= grp_idx < len(self._groups):
            grp = self._groups[grp_idx]
            if rset in grp.members:
                grp.members.remove(rset)
            self._refresh_group_list()

    def _grp_remove_solo(self, grp_idx: int, well: str) -> None:
        if 0 <= grp_idx < len(self._groups):
            grp = self._groups[grp_idx]
            if well in grp.solo_wells:
                grp.solo_wells.remove(well)
            self._refresh_group_list()

    # ── Quick Setup ───────────────────────────────────────────────────────────

    def _quick_by_row(self) -> None:
        """One export group per plate row — all loaded wells in that row."""
        self._groups.clear()
        self._active_grp = -1
        for row_ltr in _PLATE_ROWS:
            # Collect rep-sets whose wells are in this row, plus solo wells in the row
            row_rsets = [r for r in self._app._rep_sets
                         if any(_extract_well_token(w) and
                                _extract_well_token(w)[0].upper() == row_ltr
                                for w in r.wells)]
            assigned_wells = {w for r in row_rsets for w in r.wells}
            row_solos = [lbl for tok, lbl in self._app._tok_to_label.items()
                         if tok[0].upper() == row_ltr and lbl not in assigned_wells]
            if not row_rsets and not row_solos:
                continue
            grp = BarGroup(f"Row {row_ltr}", members=row_rsets,
                           solo_wells=row_solos)
            self._groups.append(grp)
        if self._groups:
            self._active_grp = 0
        self._refresh_group_list()

    def _quick_by_col(self) -> None:
        """One export group per plate column — all loaded wells in that column."""
        self._groups.clear()
        self._active_grp = -1
        for col in _PLATE_COLS:
            col_rsets = [r for r in self._app._rep_sets
                         if any(_extract_well_token(w) and
                                _extract_well_token(w)[1:] == col
                                for w in r.wells)]
            assigned_wells = {w for r in col_rsets for w in r.wells}
            col_solos = [lbl for tok, lbl in self._app._tok_to_label.items()
                         if tok[1:] == col and lbl not in assigned_wells]
            if not col_rsets and not col_solos:
                continue
            grp = BarGroup(f"Col {col}", members=col_rsets,
                           solo_wells=col_solos)
            self._groups.append(grp)
        if self._groups:
            self._active_grp = 0
        self._refresh_group_list()

    def _sync_from_app(self) -> None:
        """Re-build groups from the app's current replicate sets (one group per set)."""
        self._groups = self._groups_from_rep_sets()
        self._active_grp = 0 if self._groups else -1
        self._refresh_group_list()

    def _groups_from_rep_sets(self) -> "List[BarGroup]":
        """Build one BarGroup per loaded replicate set.

        Each group contains its replicate set as its sole member.  This gives a
        sensible starting layout for batch export that the user can then merge
        or rearrange.  Falls back to a copy of _bar_groups if no rep-sets exist.
        """
        loaded = self._app._rep_sets_loaded()
        if loaded:
            groups = []
            for rset in loaded:
                grp = BarGroup(rset.name)
                grp.members.append(rset)
                groups.append(grp)
            return groups
        # Legacy fallback
        return copy.deepcopy(self._app._bar_groups)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_groups(self) -> None:
        """Serialise the dialog's local group list to a JSON file."""
        if not self._groups:
            messagebox.showwarning("Nothing to save",
                                   "No groups defined yet.", parent=self)
            return
        # Build the same schema as _bar_groups_to_dict but from self._groups
        rep_set_names: List[str] = []
        seen_sets: set = set()
        grp_list = []
        for grp in self._groups:
            members_names = []
            for rset in grp.members:
                members_names.append(rset.name)
                if rset.name not in seen_sets:
                    seen_sets.add(rset.name)
                    rep_set_names.append(rset.name)
            grp_list.append({
                "name":       grp.name,
                "hidden":     grp.hidden,
                "members":    members_names,
                "solo_wells": [_extract_well_token(w) or w
                               for w in grp.solo_wells],
            })
        # Also save the rep-set definitions so they can be restored on load
        rep_list = []
        for rset in self._app._rep_sets:
            rep_list.append({
                "name":  rset.name,
                "wells": [_extract_well_token(w) or w for w in rset.wells],
            })
        data = {"rep_sets": rep_list, "groups": grp_list}

        path_str = filedialog.asksaveasfilename(
            parent=self, title="Save export groups",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            initialfile="export_groups.json")
        if not path_str:
            return
        try:
            with open(path_str, "w") as fh:
                json.dump(data, fh, indent=2)
            self._prog_lbl.config(text=f"Saved → {Path(path_str).name}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)

    def _load_groups(self) -> None:
        """Load group definitions from a JSON file into the dialog's local list."""
        path_str = filedialog.askopenfilename(
            parent=self, title="Load export groups",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path_str:
            return
        try:
            with open(path_str) as fh:
                data = json.load(fh)
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc), parent=self)
            return

        # Resolve tokens to well labels using the app's tok_to_label map
        def _norm(tok: str) -> str:
            tok = tok.strip().upper()
            m = re.match(r"^([A-H])(\d{1,2})$", tok, re.I)
            return f"{m.group(1).upper()}{int(m.group(2)):02d}" if m else tok

        def _tok_label(tok: str) -> Optional[str]:
            return self._app._tok_to_label.get(_norm(tok))

        # Build a name → ReplicateSet map from the app's pool
        rep_by_name = {r.name: r for r in self._app._rep_sets}

        # If the file contains rep_set definitions not in the app pool, skip them
        # (they were saved from a different session)
        new_groups: List["BarGroup"] = []
        if isinstance(data, dict):
            for item in data.get("groups", []):
                grp = BarGroup(item.get("name", "Group"),
                               hidden=bool(item.get("hidden", False)))
                for rname in item.get("members", []):
                    if rname in rep_by_name:
                        grp.members.append(rep_by_name[rname])
                for tok in item.get("solo_wells", []):
                    lbl = _tok_label(tok)
                    if lbl:
                        grp.solo_wells.append(lbl)
                new_groups.append(grp)
        elif isinstance(data, list):
            # Legacy schema
            for item in data:
                name = str(item.get("name", "Group"))
                grp  = BarGroup(name, hidden=bool(item.get("hidden", False)))
                for rdata in item.get("replicates", []):
                    rname = rdata.get("name", "R")
                    if rname in rep_by_name:
                        grp.members.append(rep_by_name[rname])
                new_groups.append(grp)

        if not new_groups:
            messagebox.showwarning(
                "No groups loaded",
                "The file contained no groups that could be matched to the "
                "currently loaded wells and replicate sets.",
                parent=self)
            return

        self._groups = new_groups
        self._active_grp = 0
        self._refresh_group_list()
        self._prog_lbl.config(
            text=f"Loaded {len(self._groups)} group(s) from {Path(path_str).name}")

    # ── Output helpers ────────────────────────────────────────────────────────

    def _browse_out_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Select output directory",
                                         parent=self,
                                         initialdir=self._out_dir_var.get() or None)
        if chosen:
            self._out_dir_var.set(chosen)

    def _on_fmt_change(self, _e=None) -> None:
        hints = {"png": "300 DPI raster", "svg": "vector — text editable",
                 "eps": "vector — text editable", "pdf": "vector"}
        self._fmt_hint.config(text=hints.get(self._fmt_var.get(), ""))

    def _resolve_out_dir(self) -> Optional[Path]:
        val = self._out_dir_var.get().strip()
        if val:
            p = Path(val)
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except OSError as exc:
                messagebox.showerror("Output directory error",
                                     f"Cannot create:\n{p}\n{exc}", parent=self)
                return None
        d = self._app._data_dir
        if d and d.is_dir():
            return d
        messagebox.showerror("No output directory",
                             "Load data or choose an output folder.", parent=self)
        return None

    def _run_batch_jobs(
        self,
        *,
        jobs: list,
        progress_text_fn,
        run_job_fn,
        success_text: str,
        status_text: str,
    ) -> None:
        self._prog_bar.pack(side=tk.LEFT)
        self._prog_bar.config(maximum=max(len(jobs), 1))
        self._run_btn.config(state=tk.DISABLED)
        errors: List[str] = []
        for step, job in enumerate(jobs, 1):
            self._prog_lbl.config(text=progress_text_fn(job, step, len(jobs)))
            self._prog_bar["value"] = step - 1
            self.update_idletasks()
            err = run_job_fn(job)
            if err:
                errors.append(err)
        self._prog_bar["value"] = len(jobs)
        self._run_btn.config(state=tk.NORMAL)
        self._prog_bar.pack_forget()
        if errors:
            self._prog_lbl.config(text=f"Done with {len(errors)} error(s). See log.", fg=CLR_DANGER)
            for err in errors:
                _logger.error("Batch export error: %s", err)
            return
        self._prog_lbl.config(text=success_text, fg=CLR_SUCCESS_DARK)
        self._app._set_status(status_text)

    def _save_figure(self, fig, fig_path: Path, fmt: str) -> None:
        import matplotlib as _mpl
        import matplotlib.pyplot as _plt
        from well_viewer.figure_export_editor import (
            _ensure_export_style_prefs,
            apply_export_style_prefs,
        )

        apply_export_style_prefs(fig, _ensure_export_style_prefs(self._app))

        orig_svg = _mpl.rcParams.get("svg.fonttype", "path")
        orig_ps = _mpl.rcParams.get("ps.fonttype", 3)
        try:
            if fmt == "svg":
                _mpl.rcParams["svg.fonttype"] = "none"
            elif fmt == "eps":
                _mpl.rcParams["ps.fonttype"] = 42
            kw = dict(bbox_inches="tight", facecolor=PLOT_BG, format=fmt)
            if fmt == "png":
                kw["dpi"] = 300
            fig.savefig(str(fig_path), **kw)
        finally:
            _mpl.rcParams["svg.fonttype"] = orig_svg
            _mpl.rcParams["ps.fonttype"] = orig_ps
            _plt.close(fig)

    # ── Export execution ──────────────────────────────────────────────────────

    def _groups_for_export(self) -> "List[BarGroup]":
        if self._use_sidebar_groups:
            return copy.deepcopy(self._app._bar_groups)
        return list(self._groups)

    def _run_batch(self) -> None:
        """Export each group: CSV + combined figure (one line per member)."""
        groups_with_data = [g for g in self._groups_for_export()
                            if any(w in self._app._well_paths for w in g.wells)]
        if not groups_with_data:
            msg = (
                "Define at least one non-empty group in Sample Definitions."
                if self._use_sidebar_groups
                else "Define at least one non-empty group."
            )
            messagebox.showwarning("No groups", msg,
                                   parent=self)
            return
        out_dir = self._resolve_out_dir()
        if out_dir is None:
            return

        threshold = self._app._get_thresh_frac_on(self._app._active_channel)
        use_sem   = self._app._use_sem.get()
        band_lbl  = "SEM" if use_sem else "SD"
        fmt       = self._fmt_var.get()
        def _progress(grp: "BarGroup", step: int, total: int) -> str:
            return f"Exporting '{grp.name}' ({step}/{total})…"

        def _run_group(grp: "BarGroup") -> Optional[str]:
            safe     = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
            csv_path = out_dir / f"batch_{safe}.csv"
            fig_path = out_dir / f"batch_{safe}.{fmt}"

            # ── CSV: per-member, per-timepoint data ──────────────────────────
            try:
                rows_out: List[dict] = []
                # Each ReplicateSet → one "member" row (mean across its wells)
                for rset in grp.members:
                    valid_wells = [w for w in rset.wells if w in self._app._well_paths]
                    if not valid_wells:
                        continue
                    # Collect all timepoints from the first valid well
                    all_rows: List[dict] = []
                    for w in valid_wells:
                        all_rows.extend(self._app._get_rows(w))
                    _val_col = self._app._active_val_col
                    _ch      = self._app._active_channel
                    _cell_area_threshold = self._app._get_cell_area_threshold()
                    _fluor_gates = self._app._get_all_fluor_gates()
                    pts = aggregate_with_threshold(all_rows, threshold, use_sem=use_sem,
                                                   val_col=_val_col, cell_area_threshold=_cell_area_threshold, fluor_gates=_fluor_gates)
                    for t, mean, sd, frac, n_above, n_total in pts:
                        rows_out.append({
                            "group":        grp.name,
                            "member":       rset.name,
                            "member_type":  "replicate_set",
                            "wells":        ";".join(_extract_well_token(w) or w
                                                     for w in valid_wells),
                            "n_wells":      len(valid_wells),
                            "time_h":       f"{t:.4f}",
                            f"mean_{_ch}":  f"{mean:.6f}" if not math.isnan(mean) else "",
                            f"{'sem' if use_sem else 'sd'}_{_ch}": f"{sd:.6f}",
                            "fraction_above": f"{frac:.6f}" if not math.isnan(frac) else "",
                            "threshold":    f"{threshold:.4f}",
                        })
                # Solo wells → their own rows
                for w in grp.solo_wells:
                    if w not in self._app._well_paths:
                        continue
                    _val_col = self._app._active_val_col
                    _ch      = self._app._active_channel
                    tok = _extract_well_token(w) or w
                    _cell_area_threshold = self._app._get_cell_area_threshold()
                    _fluor_gates = self._app._get_all_fluor_gates()
                    pts = aggregate_with_threshold(
                        self._app._get_rows(w), threshold, use_sem=use_sem,
                        val_col=_val_col, cell_area_threshold=_cell_area_threshold, fluor_gates=_fluor_gates)
                    for t, mean, sd, frac, n_above, n_total in pts:
                        rows_out.append({
                            "group":        grp.name,
                            "member":       tok,
                            "member_type":  "solo_well",
                            "wells":        tok,
                            "n_wells":      1,
                            "time_h":       f"{t:.4f}",
                            f"mean_{_ch}":  f"{mean:.6f}" if not math.isnan(mean) else "",
                            f"{'sem' if use_sem else 'sd'}_{_ch}": f"{sd:.6f}",
                            "fraction_above": f"{frac:.6f}" if not math.isnan(frac) else "",
                            "threshold":    f"{threshold:.4f}",
                        })
                if rows_out:
                    _ch = self._app._active_channel
                    fieldnames = ["group", "member", "member_type", "wells", "n_wells",
                                  "time_h", f"mean_{_ch}",
                                  f"{'sem' if use_sem else 'sd'}_{_ch}",
                                  "fraction_above", "threshold"]
                    with open(csv_path, "w", newline="") as fh:
                        writer = csv.DictWriter(fh, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows_out)
            except OSError as exc:
                return f"{grp.name} CSV: {exc}"

            # ── Figure: one line per member ───────────────────────────────────
            try:
                fig = self._render_group_figure(grp, threshold, use_sem, band_lbl)
                self._save_figure(fig, fig_path, fmt)
            except Exception as exc:
                return f"{grp.name} figure: {exc}"

            _logger.info("Batch: wrote %s and %s", csv_path.name, fig_path.name)
            return None

        self._run_batch_jobs(
            jobs=groups_with_data,
            progress_text_fn=_progress,
            run_job_fn=_run_group,
            success_text=f"\u2713 {len(groups_with_data)} group(s) \u2192 {out_dir.name}/",
            status_text=f"Batch export: {len(groups_with_data)} group(s) \u2192 {out_dir}",
        )

    def _render_group_figure(
        self,
        grp: "BarGroup",
        threshold: float,
        use_sem: bool,
        band_lbl: str,
    ) -> "Figure":
        """
        Render a combined line-graph figure for one export group.

        One line per group member:
          - ReplicateSet  →  mean of its wells ± SD/SEM (stats within the set)
          - Solo well     →  raw per-cell mean ± within-well SD/SEM

        No statistics are computed across members.
        """
        from matplotlib.figure import Figure as _Figure

        fig = _Figure(figsize=(10, 11), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(3, 1, 1)
        ax_frac = fig.add_subplot(3, 1, 2, sharex=ax_mean)
        ax_cdf  = fig.add_subplot(3, 1, 3)
        fig.subplots_adjust(hspace=0.55, top=0.92, bottom=0.07, left=0.13, right=0.97)
        fig.suptitle(grp.name, fontsize=11, fontweight="bold", color=TXT_PRI, y=0.97)

        legend_kw = dict(fontsize=7, framealpha=0.9, facecolor=PLOT_BG,
                         edgecolor=PLOT_SPN, labelcolor=TXT_PRI)
        _ch = self._app._active_channel.upper()
        apply_ax_style(ax_mean, f"Mean {_ch} (above threshold) \u00b1 {band_lbl}",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac, "Fraction of Cells Above Threshold", "Fraction")
        apply_ax_style(ax_cdf,  f"{_ch} Value CDF", "Cumulative fraction")
        ax_frac.set_xlabel("Time (hours)", fontsize=8, labelpad=5)
        ax_frac.set_ylim(-0.05, 1.05)
        ax_cdf.set_xlabel(f"{_ch} mean intensity", fontsize=8, labelpad=5)
        ax_cdf.set_ylim(-0.02, 1.05)

        any_ts = any_cdf = False
        all_fluor_vals: List[float] = []

        # Build member list aligned with runtime line-plot semantics:
        # replicate sets use _compute_rep_stats at each timepoint; solo wells
        # use aggregate_with_threshold directly on their rows.
        members: List[tuple] = []
        for rset in grp.members:
            valid = [w for w in rset.wells if w in self._app._well_paths]
            if not valid:
                continue
            members.append(("replicate", rset, valid, self._app._replicate_display_label(rset)))
        for w in grp.solo_wells:
            if w not in self._app._well_paths:
                continue
            tok = _extract_well_token(w) or w
            members.append(("well", w, [w], tok))

        _val_col = self._app._active_val_col
        _cell_area_threshold = self._app._get_cell_area_threshold()
        _fluor_gates = self._app._get_all_fluor_gates()
        for mi, (member_type, member_key, valid_wells, display_name) in enumerate(members):
            color = WELL_COLORS[mi % len(WELL_COLORS)]
            if member_type == "replicate":
                rset = member_key
                all_tps: set[float] = set()
                fluor_vals_raw: List[float] = []
                for lbl in valid_wells:
                    rows = self._app._get_rows(lbl)
                    for t, *_ in aggregate_with_threshold(
                        rows,
                        threshold,
                        use_sem=False,
                        val_col=_val_col,
                        cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    ):
                        all_tps.add(t)
                    fluor_vals_raw.extend(
                        _all_fluor_values(rows, val_col=_val_col)
                    )
                agg_times: List[float] = []
                agg_means: List[float] = []
                agg_errs: List[float] = []
                agg_fracs: List[float] = []
                for t in sorted(all_tps):
                    gm, gerr, gf, _ = self._app._compute_rep_stats(rset, t, threshold, use_sem)
                    if not math.isnan(gm):
                        agg_times.append(t)
                        agg_means.append(gm)
                        agg_errs.append(gerr)
                        agg_fracs.append(gf)

                if agg_times:
                    ax_mean.plot(agg_times, agg_means, color=color, lw=2, marker="o",
                                 markersize=4, label=display_name, zorder=3)
                    ax_mean.fill_between(
                        agg_times,
                        [m - e for m, e in zip(agg_means, agg_errs)],
                        [m + e for m, e in zip(agg_means, agg_errs)],
                        color=color,
                        alpha=0.15,
                        zorder=2,
                    )
                    vf = [(t, f) for t, f in zip(agg_times, agg_fracs) if not math.isnan(f)]
                    if vf:
                        vt2, vf2 = zip(*vf)
                        ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s",
                                     markersize=3, label=display_name, zorder=3)
                        ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                    any_ts = True

                fluor_vals = sorted(fluor_vals_raw)
            else:
                rows = self._app._get_rows(member_key)
                pts = aggregate_with_threshold(
                    rows,
                    threshold,
                    use_sem=use_sem,
                    val_col=_val_col,
                    cell_area_threshold=_cell_area_threshold,
                    fluor_gates=_fluor_gates,
                )
                if pts:
                    times, means, spreads, fracs, *_ = zip(*pts)
                    vm = [(t, m, s) for t, m, s in zip(times, means, spreads) if not math.isnan(m)]
                    if vm:
                        vt, vmm, vs = zip(*vm)
                        ax_mean.plot(vt, vmm, color=color, lw=2, marker="o",
                                     markersize=4, label=display_name, zorder=3)
                        ax_mean.fill_between(
                            vt,
                            [m - s for m, s in zip(vmm, vs)],
                            [m + s for m, s in zip(vmm, vs)],
                            color=color,
                            alpha=0.15,
                            zorder=2,
                        )
                    vf = [(t, f) for t, f in zip(times, fracs) if not math.isnan(f)]
                    if vf:
                        vt2, vf2 = zip(*vf)
                        ax_frac.plot(vt2, vf2, color=color, lw=2, marker="s",
                                     markersize=3, label=display_name, zorder=3)
                        ax_frac.fill_between(vt2, 0, vf2, color=color, alpha=0.10, zorder=2)
                    any_ts = True

                fluor_vals = sorted(_all_fluor_values(rows, val_col=_val_col))

            all_fluor_vals.extend(fluor_vals)
            if fluor_vals:
                n = len(fluor_vals)
                ax_cdf.plot(fluor_vals, [(k + 1) / n for k in range(n)],
                            color=color, lw=1.8,
                            label=f"{display_name} (n={n:,})", zorder=3)
                any_cdf = True

        if any_ts:
            ax_mean.axhline(threshold, color=WARN, lw=1.0, ls="--", alpha=0.8)
            ax_mean.legend(**legend_kw)
            ax_frac.legend(**legend_kw)
        if any_cdf:
            ax_cdf.axvline(threshold, color=WARN, lw=1.2, ls="--",
                           label=f"threshold={threshold:.2f}", zorder=5)
            if all_fluor_vals:
                lo, hi = min(all_fluor_vals), max(all_fluor_vals)
                ax_cdf.axvspan(threshold, hi, alpha=0.05, color=WARN, zorder=1)
                ax_cdf.set_xlim(lo, hi)
            ax_cdf.legend(**legend_kw)

        return fig


class BarBatchExportPanel(BatchExportPanel):
    """
    Bar-plot batch export — same group editor as the line-graph BatchExportDialog,
    with an added timepoint selector on the right panel.

    Inherits entirely:
      _build_group_editor, all CRUD methods, quick setup, save/load, drag handlers.

    Overrides:
      _build_output_panel, _run_batch
    """

    def __init__(
        self,
        app: "WellViewerApp",
        parent: tk.Widget,
        *,
        use_sidebar_groups: bool = False,
    ) -> None:
        super().__init__(app, parent, use_sidebar_groups=use_sidebar_groups)

    # ── Right panel ────────────────────────────────────────────────────────────

    def _build_output_panel(self, parent: tk.Frame) -> None:
        """Same as parent but adds a timepoint multi-select."""
        hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="OUTPUT SETTINGS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)

        out_row = tk.Frame(parent, bg=BG_APP, pady=6, padx=12)
        out_row.pack(fill=tk.X)
        tk.Label(out_row, text="Folder:", font=FM_BOLD,
                 fg=TXT_SEC, bg=BG_APP).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(out_row, textvariable=self._out_dir_var,
                 font=FM_TINY, fg=TXT_PRI, bg=BG_PANEL,
                 relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
                 anchor="w", padx=6, width=30).pack(side=tk.LEFT)
        btn_secondary(out_row, "Browse…", self._browse_out_dir,
                      padx=8).pack(side=tk.LEFT, padx=(6, 0))

        fmt_row = tk.Frame(parent, bg=BG_APP, padx=12, pady=4)
        fmt_row.pack(fill=tk.X)
        tk.Label(fmt_row, text="Format:", font=FM_BOLD,
                 fg=TXT_SEC, bg=BG_APP).pack(side=tk.LEFT, padx=(0, 6))
        fmt_cb = ttk.Combobox(fmt_row, textvariable=self._fmt_var,
                              values=["png", "svg", "eps", "pdf"],
                              state="readonly", width=6, font=FM_TINY)
        fmt_cb.pack(side=tk.LEFT)
        self._fmt_hint = tk.Label(fmt_row, text="300 DPI raster",
                                  font=FM_TINY, fg=TXT_MUT, bg=BG_APP)
        self._fmt_hint.pack(side=tk.LEFT, padx=(6, 0))
        fmt_cb.bind("<<ComboboxSelected>>", self._on_fmt_change)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(8, 4))

        # ── Timepoint selector ────────────────────────────────────────────────
        tp_hdr = tk.Frame(parent, bg=BG_APP, padx=12)
        tp_hdr.pack(fill=tk.X, pady=(0, 2))
        tk.Label(tp_hdr, text="TIMEPOINTS", font=FM_BOLD,
                 fg=TXT_MUT, bg=BG_APP).pack(side=tk.LEFT)
        tk.Button(tp_hdr, text="None",
                  command=lambda: self._tp_lb.select_clear(0, tk.END),
                  font=FM_TINY, bg=ACCENT_DARK, fg=CLR_WHITE,
                  relief=tk.FLAT, padx=6, cursor="hand2",
                  activebackground=ACCENT,
                  activeforeground=CLR_WHITE, bd=0, highlightthickness=0).pack(side=tk.RIGHT)
        tk.Button(tp_hdr, text="All",
                  command=lambda: self._tp_lb.select_set(0, tk.END),
                  font=FM_TINY, bg=ACCENT_DARK, fg=CLR_WHITE,
                  relief=tk.FLAT, padx=6, cursor="hand2",
                  activebackground=ACCENT,
                  activeforeground=CLR_WHITE, bd=0, highlightthickness=0).pack(side=tk.RIGHT, padx=(0, 4))

        tp_frame = tk.Frame(parent, bg=BG_APP, padx=12)
        tp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        vsb = tk.Scrollbar(tp_frame, relief=tk.FLAT, width=7,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tp_lb = tk.Listbox(
            tp_frame, selectmode=tk.MULTIPLE,
            bg=BG_PANEL, fg=TXT_PRI, font=FM_MONO,
            selectbackground=ACCENT, selectforeground=CLR_WHITE,
            activestyle="none", relief=tk.FLAT,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=BORDER, yscrollcommand=vsb.set,
            exportselection=False, borderwidth=0)
        self._tp_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self._tp_lb.yview)
        # Ensure the timepoint menu is populated (may not have been if the
        # Bar Plots tab hasn't been viewed yet).
        self._app._update_bar_tp_menu()
        # _bar_tp_cb["values"] returns the tuple of values (subscript, not .get())
        tp_vals = self._app._bar_tp_cb["values"]
        for tp in tp_vals:
            if tp and tp != "—":
                self._tp_lb.insert(tk.END, tp)
        if self._tp_lb.size() > 0:
            self._tp_lb.select_set(0, tk.END)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(4, 4))

        info = tk.Label(parent,
                        text=("Each group \u00d7 timepoint produces:\n"
                              "  \u2022 One bar figure (one bar per replicate set or well)\n"
                              "  \u2022 One CSV row per member at that timepoint\n\n"
                              f"{'Groups come from Sample Definitions in the left sidebar.' if self._use_sidebar_groups else 'Groups are defined in the left panel.'}\n"
                              "SD/SEM is computed within each ReplicateSet only."),
                        font=FM_TINY, fg=TXT_SEC, bg=BG_APP,
                        justify=tk.LEFT, anchor="w")
        info.pack(anchor="w", padx=12, pady=(0, 4))

        run_row = tk.Frame(parent, bg=BG_APP, pady=8, padx=12)
        run_row.pack(fill=tk.X)
        self._run_btn = tk.Button(run_row, text="▶  Run Batch Export",
                                  command=self._run_batch,
                                  font=FM_BOLD, fg=CLR_WHITE, bg=CLR_SUCCESS,
                                  activebackground=CLR_SUCCESS_DARK,
                                  relief=tk.FLAT, padx=16, pady=6,
                                  cursor="hand2", bd=0)
        self._run_btn.pack(side=tk.LEFT)
        self._prog_lbl = tk.Label(run_row, text="", font=FM_TINY,
                                  fg=TXT_MUT, bg=BG_APP)
        self._prog_lbl.pack(side=tk.LEFT, padx=12)
        self._prog_bar = ttk.Progressbar(run_row, orient=tk.HORIZONTAL,
                                          mode="determinate", length=180)
        self._prog_bar.pack(side=tk.LEFT)
        self._prog_bar.pack_forget()

    # ── Export execution ──────────────────────────────────────────────────────

    def _run_batch(self) -> None:
        """Export: for each group, one bar figure + CSV per selected timepoint."""
        groups_with_data = _groups_with_loaded_wells(self._groups_for_export(), self._app._well_paths)
        if not groups_with_data:
            msg = (
                "Define at least one non-empty group in Sample Definitions."
                if self._use_sidebar_groups
                else "Define at least one non-empty group."
            )
            messagebox.showwarning("No groups",
                                   msg,
                                   parent=self)
            return

        selected_tps = _selected_listbox_values(self._tp_lb)
        if not selected_tps:
            messagebox.showwarning("No timepoints",
                                   "Select at least one timepoint.", parent=self)
            return

        out_dir = self._resolve_out_dir()
        if out_dir is None:
            return

        threshold = self._app._get_thresh_frac_on(self._app._active_channel)
        use_sem   = self._app._use_sem.get()
        band_lbl  = "SEM" if use_sem else "SD"
        fmt       = self._fmt_var.get()
        jobs = [(grp, tp_str) for grp in groups_with_data for tp_str in selected_tps]

        def _progress(job, step: int, total: int) -> str:
            grp, tp_str = job
            return f"'{grp.name}' @ t={tp_str}h  ({step}/{total})"

        def _run_job(job) -> Optional[str]:
            grp, tp_str = job
            safe_grp = re.sub(r"[^A-Za-z0-9_\-]", "_", grp.name)
            try:
                target_t = float(tp_str)
            except ValueError:
                return f"{grp.name} t={tp_str}: invalid timepoint"

            safe_tp = tp_str.replace(".", "_").replace("-", "m")
            base = out_dir / f"bar_{safe_grp}_t{safe_tp}"

            try:
                _val_col = self._app._active_val_col
                _ch = self._app._active_channel
                rows_csv: List[dict] = []
                _cell_area_threshold = self._app._get_cell_area_threshold()
                _fluor_gates = self._app._get_all_fluor_gates()
                for rset in grp.members:
                    valid = [w for w in rset.wells if w in self._app._well_paths]
                    if not valid:
                        continue
                    combined: List[dict] = []
                    for w in valid:
                        combined.extend(self._app._get_rows(w))
                    pts = aggregate_with_threshold(combined, threshold, use_sem=use_sem, val_col=_val_col, cell_area_threshold=_cell_area_threshold, fluor_gates=_fluor_gates)
                    matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
                    if matched:
                        _, m, s, f, *_ = matched[0]
                        rows_csv.append(
                            {
                                "group": grp.name,
                                "member": rset.name,
                                "member_type": "replicate_set",
                                "n_wells": len(valid),
                                "timepoint_h": tp_str,
                                f"mean_{_ch}": f"{m:.6f}" if not math.isnan(m) else "",
                                f"{band_lbl.lower()}_{_ch}": f"{s:.6f}",
                                "fraction_above": f"{f:.6f}" if not math.isnan(f) else "",
                                "threshold": f"{threshold:.4f}",
                            }
                        )
                for w in grp.solo_wells:
                    if w not in self._app._well_paths:
                        continue
                    tok = _extract_well_token(w) or w
                    pts = aggregate_with_threshold(
                        self._app._get_rows(w),
                        threshold,
                        use_sem=use_sem,
                        val_col=_val_col,
                        cell_area_threshold=_cell_area_threshold,
                        fluor_gates=_fluor_gates,
                    )
                    matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
                    if matched:
                        _, m, s, f, *_ = matched[0]
                        rows_csv.append(
                            {
                                "group": grp.name,
                                "member": tok,
                                "member_type": "solo_well",
                                "n_wells": 1,
                                "timepoint_h": tp_str,
                                f"mean_{_ch}": f"{m:.6f}" if not math.isnan(m) else "",
                                f"{band_lbl.lower()}_{_ch}": f"{s:.6f}",
                                "fraction_above": f"{f:.6f}" if not math.isnan(f) else "",
                                "threshold": f"{threshold:.4f}",
                            }
                        )
                if rows_csv:
                    fnames = list(rows_csv[0].keys())
                    with open(str(base) + ".csv", "w", newline="") as fh:
                        wrt = csv.DictWriter(fh, fieldnames=fnames)
                        wrt.writeheader()
                        wrt.writerows(rows_csv)
            except Exception as exc:
                return f"{grp.name} t={tp_str} CSV: {exc}"

            try:
                fig = self._render_bar_group_figure(grp, target_t, tp_str, threshold, use_sem, band_lbl)
                self._save_figure(fig, Path(str(base) + f".{fmt}"), fmt)
            except Exception as exc:
                return f"{grp.name} t={tp_str} figure: {exc}"
            return None

        self._run_batch_jobs(
            jobs=jobs,
            progress_text_fn=_progress,
            run_job_fn=_run_job,
            success_text=f"✓ {len(groups_with_data)}g × {len(selected_tps)}t → {out_dir.name}/",
            status_text=f"Bar batch export complete → {out_dir}",
        )

    def _render_bar_group_figure(
        self,
        grp: "BarGroup",
        target_t: float,
        tp_str: str,
        threshold: float,
        use_sem: bool,
        band_lbl: str,
    ) -> "Figure":
        """One bar per group member at *target_t* using shared bar renderer."""
        from matplotlib.figure import Figure as _Figure

        fig = _Figure(figsize=(8, 7), dpi=300, facecolor=PLOT_BG)
        ax_mean = fig.add_subplot(2, 1, 1)
        ax_frac = fig.add_subplot(2, 1, 2)
        fig.subplots_adjust(hspace=0.55, top=0.92, bottom=0.12,
                            left=0.13, right=0.97)
        fig.suptitle(f"{grp.name}  —  t = {tp_str} h",
                     fontsize=10, fontweight="bold", color=TXT_PRI, y=0.97)
        _ch = self._app._active_channel.upper()
        apply_ax_style(ax_mean,
                       f"Mean {_ch} (above threshold) ± {band_lbl}",
                       f"Mean {_ch}")
        apply_ax_style(ax_frac, "Fraction of Cells Above Threshold",
                       "Fraction")
        ax_frac.set_ylim(-0.05, 1.05)

        members: List[tuple] = []
        for rset in grp.members:
            valid = [w for w in rset.wells if w in self._app._well_paths]
            if not valid:
                continue
            combined: List[dict] = []
            for w in valid:
                combined.extend(self._app._get_rows(w))
            members.append((
                self._app._replicate_display_label(rset),
                combined))
        for w in grp.solo_wells:
            if w not in self._app._well_paths:
                continue
            members.append((_extract_well_token(w) or w,
                            self._app._get_rows(w)))

        if not members:
            return fig

        _cell_area_threshold = self._app._get_cell_area_threshold()
        _fluor_gates = self._app._get_all_fluor_gates()
        draw_items: List[tuple] = []
        xlabels: List[str] = []
        for i, (name, rows) in enumerate(members):
            color = WELL_COLORS[i % len(WELL_COLORS)]
            pts = aggregate_with_threshold(rows, threshold, use_sem=use_sem, cell_area_threshold=_cell_area_threshold, fluor_gates=_fluor_gates)
            matched = [pt for pt in pts if abs(pt[0] - target_t) < 1e-6]
            xlabels.append(name)
            if matched:
                _t, m, s, f, *extra = matched[0]
                frac_spread = float(extra[0]) if extra else 0.0
                has_data = not math.isnan(m)
                draw_items.append((name, name, m, s, f, frac_spread, has_data, color))
            else:
                draw_items.append((name, name, float("nan"), 0.0, float("nan"), 0.0, False, color))

        _bar_render_items(
            ax_mean=ax_mean,
            ax_frac=ax_frac,
            use_groups=True,
            items=draw_items,
            xlabels=xlabels,
            threshold=threshold,
            well_colors=WELL_COLORS,
            warn_color=WARN,
            border_color=BORDER,
            placeholder_color=CLR_PLACEHOLDER,
            disabled_well_color=CLR_DISABLED_WELL,
            err_bar_color=CLR_ERR_BAR,
        )

        return fig


# Backwards-compatible aliases while call sites migrate away from dialog naming.
BatchExportDialog = BatchExportPanel
BarBatchExportDialog = BarBatchExportPanel


# ---------------------------------------------------------------------------
# pipeline_info.json reader
# ---------------------------------------------------------------------------

def _read_pipeline_info(out_dir: Path):
    """
    Read the pipeline_info.json sidecar written by analyze_tab.py and return
    (extractor, fluor_tokens) where extractor is a callable(stem) -> (fov, tp)
    suitable for passing to find_well_images_and_masks, and fluor_tokens is a
    list of lowercase channel token strings.

    Returns (None, []) when the file is absent (legacy output directory — the
    caller falls back to the classic _FNAME_RE regex in that case).
    """
    return _read_pipeline_info_shared(out_dir, logger=_logger, check_parent=True)
