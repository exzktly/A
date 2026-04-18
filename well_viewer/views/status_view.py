"""Bottom/status/log view builder extracted from runtime_app."""

from __future__ import annotations

import logging
import tkinter as tk


class _GUILogHandler(logging.Handler):
    """Routes logging records into a tk.Text widget on the main thread."""

    def __init__(self, widget: tk.Text) -> None:
        super().__init__()
        self._w = widget
        from well_viewer.runtime_app import CLR_DANGER, CLR_WARN_DARK, FM_TINY, TXT_MUT, TXT_SEC
        widget.tag_configure("ERROR",   foreground=CLR_DANGER,    font=FM_TINY)
        widget.tag_configure("WARNING", foreground=CLR_WARN_DARK,  font=FM_TINY)
        widget.tag_configure("INFO",    foreground=TXT_SEC,        font=FM_TINY)
        widget.tag_configure("DEBUG",   foreground=TXT_MUT,        font=FM_TINY)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) + "\n"
            tag = record.levelname if record.levelname in ("ERROR", "WARNING", "INFO", "DEBUG") else "INFO"
            self._w.after(0, self._append, msg, tag)
        except Exception:
            self.handleError(record)

    def _append(self, msg: str, tag: str) -> None:
        self._w.configure(state=tk.NORMAL)
        self._w.insert(tk.END, msg, tag)
        self._w.see(tk.END)
        self._w.configure(state=tk.DISABLED)


def build_bottom(app) -> None:
    """Build the persistent status/log footer strip."""
    from well_viewer import runtime_app as rt

    bottom = rt.tk.Frame(app, bg=rt.BG_SIDE)
    bottom.pack(side=rt.tk.BOTTOM, fill=rt.tk.X)
    rt.tk.Frame(bottom, bg=rt.BORDER, height=1).pack(fill=rt.tk.X)

    # ── Status strip ─────────────────────────────────────────────────────
    status_row = rt.tk.Frame(bottom, bg=rt.BG_SIDE)
    status_row.pack(fill=rt.tk.X)

    # Log toggle (far right)
    app._log_btn = rt.ttk.Button(status_row, text="Log ▲", command=app._toggle_log,
                                 style="Secondary.TButton")
    app._log_btn.pack(side=rt.tk.RIGHT, padx=4, pady=3)

    # SEM toggle (right, before log button)
    app._sem_btn = rt.ttk.Button(status_row, text="SEM", command=app._toggle_sem,
                                 style="SEM.TButton", width=5)
    app._sem_btn.pack(side=rt.tk.RIGHT, padx=(0, 2), pady=3)

    rt.tk.Frame(status_row, bg=rt.BORDER, width=1).pack(
        side=rt.tk.RIGHT, fill=rt.tk.Y, pady=5, padx=4)

    # Hover-well label (right side)
    app._status_hover_lbl = rt.tk.Label(
        status_row, text="", font=rt.FM_TINY,
        fg=rt.TXT_MUT, bg=rt.BG_SIDE, anchor="e")
    app._status_hover_lbl.pack(side=rt.tk.RIGHT, padx=(0, 6))

    # Progress bar (hidden until a run starts)
    app._progress_var = rt.tk.DoubleVar(value=0.0)
    app._progress_bar = rt.ttk.Progressbar(
        status_row,
        variable=app._progress_var,
        orient=rt.tk.HORIZONTAL,
        mode="determinate",
        length=220,
    )

    # Indicator dot
    app._status_dot = rt.tk.Label(
        status_row, text="●", font=rt.FM_TINY,
        fg=rt.ACCENT, bg=rt.BG_SIDE)
    app._status_dot.pack(side=rt.tk.LEFT, padx=(10, 3), pady=3)

    # Status text
    app._status_lbl = rt.tk.Label(
        status_row, text="Pipeline idle.", font=rt.FM_TINY,
        fg=rt.TXT_MUT, bg=rt.BG_SIDE, anchor="w", padx=0)
    app._status_lbl.pack(side=rt.tk.LEFT, fill=rt.tk.X, expand=True)

    # ── Log panel (hidden by default) ────────────────────────────────────
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
    hsb = rt.tk.Scrollbar(app._log_frame, orient=rt.tk.HORIZONTAL, relief=rt.tk.FLAT,
                          width=7, bg=rt.BORDER, troughcolor=rt.BG_SIDE)
    hsb.pack(fill=rt.tk.X, padx=6)
    app._log_text.config(xscrollcommand=hsb.set)
    hsb.config(command=app._log_text.xview)
    app._log_visible = False

    handler = _GUILogHandler(app._log_text)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S"))
    handler.setLevel(logging.DEBUG)
    rt._logger.addHandler(handler)
    rt._logger.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
