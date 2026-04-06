"""Bottom/status/log view builder extracted from runtime_app."""

from __future__ import annotations


def build_bottom(app) -> None:
    """Build the persistent status/log footer strip."""
    from well_viewer import runtime_app as rt

    bottom = rt.tk.Frame(app, bg=rt.BG_SIDE)
    bottom.pack(side=rt.tk.BOTTOM, fill=rt.tk.X)
    rt.tk.Frame(bottom, bg=rt.BORDER, height=1).pack(fill=rt.tk.X)

    ctrl_row = rt.tk.Frame(bottom, bg=rt.BG_SIDE, pady=8, padx=14)
    ctrl_row.pack(fill=rt.tk.X)
    rt.tk.Label(ctrl_row, text="Error Band", font=rt.FM_BOLD, fg=rt.TXT_SEC, bg=rt.BG_SIDE).pack(
        side=rt.tk.LEFT, padx=(0, 6)
    )
    app._sem_btn = rt.ttk.Button(ctrl_row, text="SEM", command=app._toggle_sem,
                                 style="SEM.TButton", width=5)
    app._sem_btn.pack(side=rt.tk.LEFT)
    rt.tk.Frame(bottom, bg=rt.BORDER, height=1).pack(fill=rt.tk.X)

    status_row = rt.tk.Frame(bottom, bg=rt.BG_SIDE)
    status_row.pack(fill=rt.tk.X)
    app._log_btn = rt.ttk.Button(status_row, text="Log ▲", command=app._toggle_log,
                                 style="Secondary.TButton")
    app._log_btn.pack(side=rt.tk.RIGHT, padx=4, pady=2)

    app._progress_var = rt.tk.DoubleVar(value=0.0)
    app._progress_bar = rt.ttk.Progressbar(
        status_row,
        variable=app._progress_var,
        orient=rt.tk.HORIZONTAL,
        mode="determinate",
        length=220,
    )

    app._status_lbl = rt.tk.Label(
        status_row, text="Ready.", font=rt.FM_TINY, fg=rt.TXT_MUT, bg=rt.BG_SIDE, anchor="w", padx=14
    )
    app._status_lbl.pack(side=rt.tk.LEFT, fill=rt.tk.X, expand=True)

    app._log_frame = rt.tk.Frame(bottom, bg=rt.BG_SIDE, height=160)
    app._log_frame.pack_propagate(False)

    log_hdr = rt.tk.Frame(app._log_frame, bg=rt.BG_SIDE)
    log_hdr.pack(fill=rt.tk.X, padx=6, pady=(4, 2))
    rt.tk.Label(log_hdr, text="LOG", font=rt.FM_BOLD, fg=rt.TXT_MUT, bg=rt.BG_SIDE).pack(side=rt.tk.LEFT)
    rt.ttk.Button(log_hdr, text="Clear", command=app._clear_log,
                  style="Secondary.TButton").pack(side=rt.tk.RIGHT)

    tf = rt.tk.Frame(app._log_frame, bg=rt.BG_SIDE)
    tf.pack(fill=rt.tk.BOTH, expand=True, padx=6, pady=(0, 2))
    vsb = rt.tk.Scrollbar(tf, relief=rt.tk.FLAT, width=7, bg=rt.BORDER, troughcolor=rt.BG_SIDE)
    vsb.pack(side=rt.tk.RIGHT, fill=rt.tk.Y)
    app._log_text = rt.tk.Text(
        tf,
        state=rt.tk.DISABLED,
        bg=rt.BG_PANEL,
        fg=rt.TXT_PRI,
        font=rt.FM_TINY,
        relief=rt.tk.FLAT,
        highlightthickness=1,
        highlightbackground=rt.BORDER,
        wrap=rt.tk.NONE,
        yscrollcommand=vsb.set,
        borderwidth=0,
    )
    app._log_text.pack(side=rt.tk.LEFT, fill=rt.tk.BOTH, expand=True)
    vsb.config(command=app._log_text.yview)
    hsb = rt.tk.Scrollbar(app._log_frame, orient=rt.tk.HORIZONTAL, relief=rt.tk.FLAT, width=7, bg=rt.BORDER, troughcolor=rt.BG_SIDE)
    hsb.pack(fill=rt.tk.X, padx=6)
    app._log_text.config(xscrollcommand=hsb.set)
    hsb.config(command=app._log_text.xview)
    app._log_visible = False

    handler = rt._GUILogHandler(app._log_text)
    handler.setFormatter(rt.logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S"))
    handler.setLevel(rt.logging.DEBUG)
    rt._logger.addHandler(handler)
    rt._logger.setLevel(rt.logging.DEBUG)
    rt.logging.getLogger().addHandler(handler)

