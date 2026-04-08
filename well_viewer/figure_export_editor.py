"""In-tab export style sidebar for matplotlib figures."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk

DEFAULT_EXPORT_STYLE_PREFS = {
    "axis_label_size": 12,
    "tick_label_size": 10,
    "title_size": 14,
    "x_tick_angle": 0,
    "format": "png",
}


def _ensure_export_style_prefs(app) -> dict:
    if not hasattr(app, "_export_style_prefs"):
        app._export_style_prefs = dict(DEFAULT_EXPORT_STYLE_PREFS)
    return app._export_style_prefs


def apply_export_style_prefs(fig, prefs: dict) -> None:
    face = "none"
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

        self._axis = tk.IntVar(value=int(self._prefs["axis_label_size"]))
        self._tick = tk.IntVar(value=int(self._prefs["tick_label_size"]))
        self._title = tk.IntVar(value=int(self._prefs["title_size"]))
        self._xang = tk.IntVar(value=int(self._prefs["x_tick_angle"]))
        self._fmt = tk.StringVar(value=str(self._prefs["format"]))
        self._default_name = default_name

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="Export Style", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Button(self, text="Hide", command=lambda: self.pack_forget(), style="ActionSecondary.TButton").grid(row=0, column=2, sticky="e")

        row = 1
        for label, var in (
            ("Axis", self._axis),
            ("Ticks", self._tick),
            ("Title", self._title),
            ("X°", self._xang),
            ("Fmt", self._fmt),
        ):
            ttk.Label(self, text=label, width=6).grid(row=row, column=0, sticky="w", pady=1)
            if label == "Fmt":
                w = ttk.Combobox(self, values=["png", "svg", "pdf", "eps"], state="readonly", textvariable=var, width=9)
            elif isinstance(var, tk.IntVar):
                lim = 90 if label == "X°" else 96
                w = ttk.Spinbox(self, from_=0 if label == "X°" else 1, to=lim, textvariable=var, width=10)
            else:
                w = ttk.Entry(self, textvariable=var, width=12)
            w.grid(row=row, column=1, columnspan=2, sticky="ew", pady=1)
            row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(btns, text="Apply", command=self._apply, style="ActionSecondary.TButton").pack(side=tk.LEFT)
        ttk.Button(btns, text="Export…", command=self._export, style="ActionSuccess.TButton").pack(side=tk.LEFT, padx=4)

        self.columnconfigure(1, weight=1)

    def _persist(self) -> None:
        self._prefs.update(
            axis_label_size=int(self._axis.get()),
            tick_label_size=int(self._tick.get()),
            title_size=int(self._title.get()),
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
            kw = {"format": fmt, "bbox_inches": "tight", "transparent": True}
            orig_svg = orig_ps = None
            if fmt == "png":
                kw["dpi"] = 300
            elif fmt == "svg":
                import matplotlib as _mpl
                orig_svg = _mpl.rcParams.get("svg.fonttype", "path")
                _mpl.rcParams["svg.fonttype"] = "none"
            elif fmt == "eps":
                import matplotlib as _mpl
                orig_ps = _mpl.rcParams.get("ps.fonttype", 3)
                _mpl.rcParams["ps.fonttype"] = 42
            try:
                self._fig.savefig(str(out_path), **kw)
            finally:
                if fmt == "svg" and orig_svg is not None:
                    import matplotlib as _mpl
                    _mpl.rcParams["svg.fonttype"] = orig_svg
                if fmt == "eps" and orig_ps is not None:
                    import matplotlib as _mpl
                    _mpl.rcParams["ps.fonttype"] = orig_ps
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
