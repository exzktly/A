"""Well label editor builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk


def build_label_editor(app, parent: tk.Frame) -> None:
    """Centre panel of Sample Definitions tab: assign custom display labels to wells."""
    from well_viewer.runtime_app import (
        BORDER, BG_SIDE, FM_BOLD, TXT_MUT, FM_TINY, BG_APP,
        _btn_secondary, make_scrollable_canvas,
    )

    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

    hdr = tk.Frame(parent, bg=BG_SIDE, pady=4, padx=8)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="WELL LABELS", font=FM_BOLD,
             fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
    _btn_secondary(hdr, "Clear All", app._labels_clear_all).pack(side=tk.RIGHT)

    tk.Label(parent,
             text="Custom names used in figure legends and axis labels only. "
                  "Leave blank to use the well token (e.g. A01).",
             font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
             wraplength=320, justify=tk.LEFT).pack(
             fill=tk.X, padx=8, pady=(4, 2))

    # Scrollable list of name → entry rows
    sf = tk.Frame(parent, bg=BG_APP)
    sf.pack(fill=tk.BOTH, expand=True)
    app._lbl_canvas, app._lbl_inner = make_scrollable_canvas(sf, bg=BG_APP)


def label_panel_refresh(app) -> None:
    """Rebuild the well-label entry rows."""
    from well_viewer.runtime_app import (
        FM_TINY, FM_BOLD, FM_MONO, TXT_MUT, TXT_SEC, TXT_PRI,
        BG_APP, BG_PANEL, BORDER, ACCENT,
        _extract_well_token,
    )

    if not hasattr(app, "_lbl_inner"):
        return
    for w in app._lbl_inner.winfo_children():
        w.destroy()

    wells = sorted(app._well_paths.keys(),
                   key=lambda l: app._parse_rc(l))
    if not wells:
        tk.Label(app._lbl_inner,
                 text="No wells loaded yet.",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_APP,
                 justify=tk.LEFT).pack(anchor="w", padx=8, pady=8)
        return

    # Header row
    hdr_row = tk.Frame(app._lbl_inner, bg=BG_APP)
    hdr_row.pack(fill=tk.X, padx=6, pady=(4, 2))
    tk.Label(hdr_row, text="Well", font=FM_BOLD, fg=TXT_MUT,
             bg=BG_APP, width=6, anchor="w").pack(side=tk.LEFT)
    tk.Label(hdr_row, text="Display label (blank = use well token)",
             font=FM_BOLD, fg=TXT_MUT, bg=BG_APP,
             anchor="w").pack(side=tk.LEFT, padx=(4, 0))

    tk.Frame(app._lbl_inner, bg=BORDER, height=1).pack(
        fill=tk.X, padx=6, pady=(0, 2))

    for lbl in wells:
        tok = _extract_well_token(lbl) or lbl
        row = tk.Frame(app._lbl_inner, bg=BG_APP)
        row.pack(fill=tk.X, padx=6, pady=1)

        tk.Label(row, text=tok, font=FM_MONO, fg=TXT_SEC,
                 bg=BG_APP, width=6, anchor="w").pack(side=tk.LEFT)

        var = tk.StringVar(value=app._well_labels.get(tok, ""))
        e = tk.Entry(row, textvariable=var, font=FM_TINY,
                     fg=TXT_PRI, bg=BG_PANEL, relief=tk.FLAT,
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER, width=24)
        e.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)

        def _on_change(t=tok, v=var):
            val = v.get().strip()
            if val:
                app._well_labels[t] = val
            else:
                app._well_labels.pop(t, None)
            app._invalidate_stats_cache()

        var.trace_add("write", lambda *_, t=tok, v=var: _on_change(t, v))
