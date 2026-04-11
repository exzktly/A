"""View builder extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from well_viewer.runtime_app import (
    ACCENT,
    BG_APP,
    BG_CELL,
    BG_HOVER,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    CLR_SUCCESS,
    FM_BOLD,
    FM_TINY,
    TXT_MUT,
    TXT_PRI,
    TXT_SEC,
)
from well_viewer.views.widgets import _Tooltip
from well_viewer.ui_helpers import btn_card, btn_secondary


def build_right_panel(self, parent: tk.Frame) -> None:
        inner = tk.Frame(parent, bg=BG_SIDE)
        inner.pack(fill=tk.BOTH, expand=True)
    
        # Top controls: well name + channel + FOV dropdown
        ctrl = tk.Frame(inner, bg=BG_SIDE, pady=6, padx=10)
        ctrl.pack(fill=tk.X)
        self._preview_well_lbl = tk.Label(ctrl, text="No well selected",
                                          font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE)
        self._preview_well_lbl.pack(side=tk.LEFT)

        tk.Label(ctrl, text="Channel:", font=FM_BOLD, fg=TXT_SEC,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(14, 6))
        self._chan_cb_preview = ttk.Combobox(ctrl, textvariable=self._chan_var,
                                             values=["GFP"], state="readonly",
                                             width=10, font=FM_BOLD)
        self._chan_cb_preview.pack(side=tk.LEFT, padx=(0, 14))
        self._chan_cb_preview.bind("<<ComboboxSelected>>", lambda _e: self._set_active_channel(self._chan_var.get().lower()))

        tk.Label(ctrl, text="FOV:", font=FM_TINY, fg=TXT_MUT,
                 bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._fov_menu = ttk.Combobox(ctrl, textvariable=self._preview_fov_var,
                                       values=["—"], state="readonly",
                                       width=8, font=FM_TINY)
        self._fov_menu.pack(side=tk.LEFT)
        self._fov_menu.bind("<<ComboboxSelected>>",
                             lambda _e: self._refresh_preview_montage())

        btn_secondary(ctrl, "Save Montage…", self._save_montage_figure,
                      padx=8).pack(side=tk.RIGHT)
    
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X)
    
        # Status / loading label
        self._montage_status = tk.Label(inner, text="", font=FM_TINY,
                                         fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        self._montage_status.pack(fill=tk.X, padx=8, pady=2)
    
        # Scrollable canvas for thumbnail grid
        scroll_outer = tk.Frame(inner, bg=BG_SIDE)
        scroll_outer.pack(fill=tk.BOTH, expand=True)
        vsb = tk.Scrollbar(scroll_outer, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = tk.Scrollbar(scroll_outer, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._montage_canvas = tk.Canvas(scroll_outer, bg=BG_APP,
                                          yscrollcommand=vsb.set,
                                          xscrollcommand=hsb.set,
                                          highlightthickness=0)
        self._montage_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self._montage_canvas.yview)
        hsb.config(command=self._montage_canvas.xview)
        self._montage_inner = tk.Frame(self._montage_canvas, bg=BG_APP)
        self._montage_win   = self._montage_canvas.create_window(
            (0, 0), window=self._montage_inner, anchor="nw")
        self._montage_inner.bind(
            "<Configure>",
            lambda _e: self._montage_canvas.configure(
                scrollregion=self._montage_canvas.bbox("all")))
        self._montage_canvas.bind("<Configure>", self._on_montage_canvas_resize)
    
        # Tooltip for GFP pixel values in montage
        self._montage_tooltip = _Tooltip(inner)
    
        # LUT controls below the canvas
        lut_row = tk.Frame(inner, bg=BG_SIDE, pady=4, padx=8)
        lut_row.pack(fill=tk.X, side=tk.BOTTOM)
        self._mon_lut_chan_lbl = tk.Label(lut_row,
                                          text=f"{self._active_channel.upper()} LUT min:",
                                          font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE)
        self._mon_lut_chan_lbl.pack(side=tk.LEFT)
        self._mon_lmin_var = tk.StringVar(value="auto")
        self._mon_lmax_var = tk.StringVar(value="auto")
        for var, padx in ((self._mon_lmin_var, (3, 8)), (self._mon_lmax_var, (3, 12))):
            prefix = "max:" if var is self._mon_lmax_var else ""
            if prefix:
                tk.Label(lut_row, text=prefix, font=FM_TINY,
                         fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
            e = tk.Entry(lut_row, textvariable=var, width=7, font=FM_TINY,
                         fg=ACCENT, bg=BG_PANEL, relief=tk.FLAT,
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=BORDER)
            e.pack(side=tk.LEFT, padx=padx)
            e.bind("<Return>",   lambda _e: self._montage_redraw_at_zoom())
            e.bind("<FocusOut>", lambda _e: self._montage_redraw_at_zoom())
        btn_secondary(lut_row, "Auto LUT", self._montage_auto_lut,
                      padx=8).pack(side=tk.LEFT)
    
        # Zoom controls — packed on the right of the same lut_row
        tk.Frame(lut_row, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y,
                                                     padx=(12, 8))
        tk.Label(lut_row, text="Zoom:", font=FM_TINY,
                 fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
        btn_card(lut_row, "−", lambda: self._montage_zoom_step(-1),
                 width=2).pack(side=tk.LEFT, padx=(4, 1))
        self._montage_zoom_lbl = tk.Label(lut_row, text="100%", font=FM_TINY,
                                           fg=TXT_SEC, bg=BG_SIDE, width=5)
        self._montage_zoom_lbl.pack(side=tk.LEFT)
        btn_card(lut_row, "+", lambda: self._montage_zoom_step(+1),
                 width=2).pack(side=tk.LEFT, padx=(1, 4))
        btn_secondary(lut_row, "Fit", self._montage_zoom_fit).pack(side=tk.LEFT)
    
        # Top-hat background subtraction controls (second row in controls area)
        th_row = tk.Frame(inner, bg=BG_SIDE, pady=2, padx=8)
        th_row.pack(fill=tk.X, side=tk.BOTTOM)
        self._mon_tophat_var    = tk.BooleanVar(value=False)
        self._mon_tophat_radius = tk.StringVar(value="50")
        self._th_checkbox = tk.Checkbutton(th_row, text="",
                       variable=self._mon_tophat_var,
                       font=FM_TINY, fg=TXT_SEC, bg=BG_SIDE,
                       activebackground=BG_SIDE,
                       command=self._montage_tophat_toggled)
        self._th_checkbox.pack(side=tk.LEFT)
        self._th_label = tk.Label(th_row, text="Top-hat background subtraction",
                                  font=FM_TINY, fg=TXT_SEC, bg=BG_SIDE)
        self._th_label.pack(side=tk.LEFT)
        self._th_radius_label = tk.Label(th_row, text="   radius:",
                                         font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE)
        self._th_radius_label.pack(side=tk.LEFT)
        self._th_radius_entry = tk.Entry(th_row, textvariable=self._mon_tophat_radius,
                        width=5, font=FM_TINY, fg=ACCENT, bg=BG_PANEL,
                        relief=tk.FLAT, highlightthickness=1,
                        highlightcolor=ACCENT, highlightbackground=BORDER)
        self._th_radius_entry.pack(side=tk.LEFT)
        self._th_radius_entry.bind("<Return>",   lambda _e: self._montage_redraw_at_zoom())
        self._th_radius_entry.bind("<FocusOut>", lambda _e: self._montage_redraw_at_zoom())
        self._th_radius_hint = tk.Label(th_row,
                 text="px",
                 font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE)
        self._th_radius_hint.pack(side=tk.LEFT, padx=(4, 0))
        # Status badge: shown when pre-filtered tophat images are loaded from disk
        self._th_preload_badge = tk.Label(th_row, text="",
                 font=FM_TINY, fg=CLR_SUCCESS, bg=BG_SIDE)
        self._th_preload_badge.pack(side=tk.LEFT, padx=(10, 0))
    
        # Storage for loaded arrays (set in _refresh_preview_montage)
        self._montage_fluor_arrays:    List[object]  = []
        self._montage_overlay_arrays: List[object] = []
        self._montage_fluor_refs:      List[object]  = []
        self._montage_overlay_refs:  List[object]  = []
        self._montage_resize_job:    Optional[str] = None
        self._montage_zoom:          float         = 1.0
        self._montage_base_sz:       int           = 120  # base px, updated on fit
    
        # Mouse-wheel zoom on the canvas
        self._montage_canvas.bind("<MouseWheel>",
                                   self._on_montage_wheel)          # Windows / macOS
        self._montage_canvas.bind("<Button-4>",
                                   lambda e: self._montage_zoom_step(+1))  # Linux scroll up
        self._montage_canvas.bind("<Button-5>",
                                   lambda e: self._montage_zoom_step(-1))  # Linux scroll down
    
    # ── Inline preview montage ────────────────────────────────────────────────


def build_review_image_panel(self, parent: tk.Frame) -> None:
        inner = tk.Frame(parent, bg=BG_SIDE)
        inner.pack(fill=tk.BOTH, expand=True)

        ctrl = tk.Frame(inner, bg=BG_SIDE, pady=6, padx=10)
        ctrl.pack(fill=tk.X)
        self._review_image_well_lbl = tk.Label(
            ctrl, text="No well selected", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE
        )
        self._review_image_well_lbl.pack(side=tk.LEFT)

        tk.Label(ctrl, text="Channel:", font=FM_BOLD, fg=TXT_SEC, bg=BG_SIDE).pack(side=tk.LEFT, padx=(14, 6))
        self._review_image_chan_cb = ttk.Combobox(
            ctrl, textvariable=self._chan_var, values=["GFP"], state="readonly", width=10, font=FM_BOLD
        )
        self._review_image_chan_cb.pack(side=tk.LEFT, padx=(0, 10))
        self._review_image_chan_cb.bind("<<ComboboxSelected>>", lambda _e: self._set_active_channel(self._chan_var.get().lower()))

        tk.Label(ctrl, text="FOV:", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._review_image_fov_menu = ttk.Combobox(
            ctrl, textvariable=self._preview_fov_var, values=["—"], state="readonly", width=8, font=FM_TINY
        )
        self._review_image_fov_menu.pack(side=tk.LEFT, padx=(0, 10))
        self._review_image_fov_menu.bind("<<ComboboxSelected>>", lambda _e: self._refresh_review_image())

        tk.Label(ctrl, text="Timepoint:", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 4))
        self._review_image_tp_var = tk.StringVar(value="—")
        self._review_image_tp_menu = ttk.Combobox(
            ctrl, textvariable=self._review_image_tp_var, values=["—"], state="readonly", width=10, font=FM_TINY
        )
        self._review_image_tp_menu.pack(side=tk.LEFT)
        self._review_image_tp_menu.bind("<<ComboboxSelected>>", lambda _e: self._refresh_review_image())

        btn_card(ctrl, "−", lambda: self._review_image_zoom_step(-1), width=2).pack(side=tk.RIGHT, padx=(6, 2))
        btn_card(ctrl, "+", lambda: self._review_image_zoom_step(+1), width=2).pack(side=tk.RIGHT, padx=(2, 6))
        btn_secondary(ctrl, "Fit", self._review_image_zoom_fit, padx=8).pack(side=tk.RIGHT)
        btn_secondary(ctrl, "Toggle Included", self._toggle_selected_review_cell, padx=8).pack(side=tk.RIGHT)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X)

        self._review_image_status = tk.Label(inner, text="", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        self._review_image_status.pack(fill=tk.X, padx=8, pady=2)

        lut_row = tk.Frame(inner, bg=BG_SIDE, pady=2, padx=8)
        lut_row.pack(fill=tk.X)
        self._review_lut_chan_lbl = tk.Label(
            lut_row,
            text=f"{self._active_channel.upper()} LUT min:",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        )
        self._review_lut_chan_lbl.pack(side=tk.LEFT)
        self._review_lut_min_var = tk.StringVar(value="auto")
        self._review_lut_max_var = tk.StringVar(value="auto")
        for var, padx in ((self._review_lut_min_var, (3, 8)), (self._review_lut_max_var, (3, 12))):
            prefix = "max:" if var is self._review_lut_max_var else ""
            if prefix:
                tk.Label(lut_row, text=prefix, font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(side=tk.LEFT)
            entry = tk.Entry(
                lut_row,
                textvariable=var,
                width=7,
                font=FM_TINY,
                fg=ACCENT,
                bg=BG_PANEL,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=ACCENT,
                highlightbackground=BORDER,
            )
            entry.pack(side=tk.LEFT, padx=padx)
            entry.bind("<Return>", lambda _e: self._review_image_commit_lut())
            entry.bind("<FocusOut>", lambda _e: self._review_image_commit_lut())
        btn_secondary(lut_row, "Auto LUT", self._review_image_auto_lut, padx=8).pack(side=tk.LEFT)

        self._review_image_canvas = tk.Canvas(inner, bg=BG_APP, highlightthickness=0)
        self._review_image_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._review_image_label = tk.Label(self._review_image_canvas, bg=BG_APP, bd=0, cursor="hand2")
        self._review_image_window = self._review_image_canvas.create_window((8, 8), window=self._review_image_label, anchor="nw")
        self._review_image_canvas.bind("<Configure>", lambda _e: self._render_review_image_display())
        self._review_image_canvas.bind("<MouseWheel>", self._on_review_image_wheel)
        self._review_image_canvas.bind("<Button-4>", lambda _e: self._review_image_zoom_step(+1))
        self._review_image_canvas.bind("<Button-5>", lambda _e: self._review_image_zoom_step(-1))

        self._review_image_tooltip = _Tooltip(inner)
