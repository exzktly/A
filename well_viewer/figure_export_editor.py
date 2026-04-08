"""In-tab export style sidebar for matplotlib figures."""

from __future__ import annotations

from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox

import tkinter as tk
from tkinter import ttk

DEFAULT_EXPORT_STYLE_PREFS = {
    "background_color": "transparent",
    "axis_label_size": 12,
    "tick_label_size": 10,
    "title_size": 14,
    "line_marker_face_color": "#1f77b4",
    "bar_face_color": "#1f77b4",
    "x_tick_angle": 0,
    "format": "png",
}


def _normalize_facecolor(bg_value: str | None):
    v = (bg_value or "").strip().lower()
    return "none" if (not v or v == "transparent") else bg_value


def _ensure_export_style_prefs(app) -> dict:
    if not hasattr(app, "_export_style_prefs"):
        app._export_style_prefs = dict(DEFAULT_EXPORT_STYLE_PREFS)
    return app._export_style_prefs


def apply_export_style_prefs(fig, prefs: dict) -> None:
    face = _normalize_facecolor(prefs.get("background_color"))
    fig.set_facecolor(face)
    for ax in fig.axes:
        ax.set_facecolor(face)
        ax.xaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.yaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.tick_params(axis="x", labelsize=int(prefs.get("tick_label_size", 10)))
        ax.tick_params(axis="y", labelsize=int(prefs.get("tick_label_size", 10)))
        ax.title.set_fontsize(int(prefs.get("title_size", 14)))
        for tick in ax.get_xticklabels():
            tick.set_rotation(int(prefs.get("x_tick_angle", 0)))
        for ln in ax.lines:
            ln.set_markerfacecolor(prefs.get("line_marker_face_color", "#1f77b4"))
        for patch in ax.patches:
            patch.set_facecolor(prefs.get("bar_face_color", "#1f77b4"))


def apply_export_style_to_current(app, fig, canvas=None) -> None:
    prefs = _ensure_export_style_prefs(app)
    apply_export_style_prefs(fig, prefs)
    if canvas is not None:
        canvas.draw_idle()


class _ExportStyleSidebar(ttk.Frame):
    def __init__(self, app, parent, fig, canvas, default_name: str):
        super().__init__(parent, padding=(8, 8), style="Card.TFrame")
        self._app = app
        self._fig = fig
        self._canvas = canvas
        self._default_name = default_name
        self._base_dir = Path(app._data_dir) if getattr(app, "_data_dir", None) else Path.cwd()
        self._prefs = _ensure_export_style_prefs(app)

        self._bg = tk.StringVar(value=str(self._prefs["background_color"]))
        self._axis = tk.IntVar(value=int(self._prefs["axis_label_size"]))
        self._tick = tk.IntVar(value=int(self._prefs["tick_label_size"]))
        self._title = tk.IntVar(value=int(self._prefs["title_size"]))
        self._line = tk.StringVar(value=str(self._prefs["line_marker_face_color"]))
        self._bar = tk.StringVar(value=str(self._prefs["bar_face_color"]))
        self._xang = tk.IntVar(value=int(self._prefs["x_tick_angle"]))
        self._fmt = tk.StringVar(value=str(self._prefs["format"]))
        self._default_name = default_name

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="Export Style", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Button(self, text="Hide", command=lambda: self.pack_forget(), style="ActionSecondary.TButton").grid(row=0, column=2, sticky="e")

        row = 1
        for label, var in (
            ("Canvas", self._bg),
            ("Axis", self._axis),
            ("Ticks", self._tick),
            ("Title", self._title),
            ("Line", self._line),
            ("Bars", self._bar),
            ("X°", self._xang),
            ("Fmt", self._fmt),
        ):
            ttk.Label(self, text=label, width=6).grid(row=row, column=0, sticky="w", pady=1)
            if label == "Canvas":
                w = ttk.Frame(self)
                ttk.Entry(w, textvariable=var, width=10).pack(side=tk.LEFT)
                ttk.Button(w, text="◌", width=2, style="ActionSecondary.TButton",
                           command=lambda v=var: v.set("transparent")).pack(side=tk.LEFT, padx=(2, 0))
                ttk.Button(w, text="✎", width=2, style="ActionSecondary.TButton",
                           command=lambda v=var: self._pick_color(v)).pack(side=tk.LEFT, padx=(2, 0))
            elif label == "Fmt":
                w = ttk.Combobox(self, values=["png", "svg", "pdf", "eps"], state="readonly", textvariable=var, width=9)
            elif isinstance(var, tk.IntVar):
                lim = 90 if label == "X°" else 96
                w = ttk.Spinbox(self, from_=0 if label == "X°" else 1, to=lim, textvariable=var, width=10)
            elif label in ("Line", "Bars"):
                w = ttk.Frame(self)
                ttk.Entry(w, textvariable=var, width=10).pack(side=tk.LEFT)
                ttk.Button(w, text="✎", width=2, style="ActionSecondary.TButton",
                           command=lambda v=var: self._pick_color(v)).pack(side=tk.LEFT, padx=(2, 0))
            else:
                w = ttk.Entry(self, textvariable=var, width=12)
            w.grid(row=row, column=1, columnspan=2, sticky="ew", pady=1)
            row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(btns, text="Apply", command=self._apply, style="ActionSecondary.TButton").pack(side=tk.LEFT)
        ttk.Button(btns, text="Export…", command=self._export, style="ActionSuccess.TButton").pack(side=tk.LEFT, padx=4)

        self.columnconfigure(1, weight=1)

    @staticmethod
    def _pick_color(var: tk.StringVar) -> None:
        picked = colorchooser.askcolor(color=var.get())[1]
        if picked:
            var.set(picked)

    def _persist(self) -> None:
        self._prefs.update(
            background_color=self._bg.get(),
            axis_label_size=int(self._axis.get()),
            tick_label_size=int(self._tick.get()),
            title_size=int(self._title.get()),
            line_marker_face_color=self._line.get(),
            bar_face_color=self._bar.get(),
            x_tick_angle=int(self._xang.get()),
            format=self._fmt.get(),
        )

    def _apply(self) -> None:
        self._persist()
        apply_export_style_to_current(self._app, self._fig, self._canvas)

    def _export(self) -> None:
        try:
            self._persist()
            fmt = (self._prefs.get("format") or "png").lower()
            initialfile = self._default_name
            if not initialfile.lower().endswith(f".{fmt}"):
                initialfile = f"{Path(initialfile).stem}.{fmt}"
            out = filedialog.asksaveasfilename(
                parent=self,
                title="Save figure",
                defaultextension=f".{fmt}",
                filetypes=[("Image", f"*.{fmt}"), ("All files", "*.*")],
                initialdir=str(self._base_dir),
                initialfile=initialfile,
            )
            if not out:
                return
            out_path = Path(out)
            face = _normalize_facecolor(self._prefs.get("background_color"))
            kw = {"format": fmt, "bbox_inches": "tight", "transparent": face == "none"}
            if face != "none":
                kw["facecolor"] = face
            if fmt == "png":
                kw["dpi"] = 300
            self._fig.savefig(str(out_path), **kw)
            self._app._set_status(f"Figure saved → {out_path.name}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)


class _ExportEditorSession:
    def __init__(self, sidebar: _ExportStyleSidebar) -> None:
        self.sidebar = sidebar


def launch_export_editor(app, fig, default_name: str, *, plot_bg: str, canvas=None) -> _ExportEditorSession | None:
    try:
        parent = canvas.get_tk_widget().master if canvas is not None else app
        canvas_widget = canvas.get_tk_widget() if canvas is not None else None
        if not hasattr(app, "_export_style_sidebars"):
            app._export_style_sidebars = {}
        key = id(fig)
        sb = app._export_style_sidebars.get(key)
        if sb is None or not sb.winfo_exists():
            sb = _ExportStyleSidebar(app, parent, fig, canvas, default_name=default_name)
            app._export_style_sidebars[key] = sb
        # Ensure there is physical room for the right sidebar by making the
        # plot canvas occupy the left side of the same parent container.
        if canvas_widget is not None and canvas_widget.winfo_manager() == "pack":
            try:
                pinfo = dict(canvas_widget.pack_info())
                canvas_widget.pack_forget()
                pinfo["side"] = tk.LEFT
                canvas_widget.pack(**pinfo)
            except Exception:
                # Fall back to original layout if repack fails.
                pass
        if not sb.winfo_ismapped():
            sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=(8, 8))
            sb.lift()
        sb._apply()
        return _ExportEditorSession(sb)
    except Exception as exc:
        messagebox.showwarning("Export editor unavailable", str(exc), parent=app)
        return None
