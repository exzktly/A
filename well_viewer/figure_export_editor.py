"""In-tab export style sidebar for matplotlib figures."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk
from ui.theme import FM_BOLD, FM_TINY

DEFAULT_EXPORT_STYLE_PREFS = {
    "axis_label_size": 12,
    "tick_label_size": 10,
    "title_size": 14,
    "x_tick_angle": 0,
    "format": "png",
    "axis_target": "All",
    "legend_show": True,
    "legend_font_size": 9,
    "legend_loc": "best",
    "line_width": 1.8,
    "marker_size": 5.0,
    "marker_edge_width": 0.8,
    "grid_show": True,
    "grid_alpha": 0.25,
    "grid_style": "--",
    "x_lim_min": "",
    "x_lim_max": "",
    "y_lim_min": "",
    "y_lim_max": "",
    "x_log": False,
    "y_log": False,
    "tick_major": True,
    "tick_minor": False,
    "tick_length": 4.0,
    "tick_direction": "out",
    "layout_tight": False,
    "layout_constrained": False,
    "export_profile": "Custom",
}

EXPORT_PROFILES = {
    "Custom": {},
    "Illustrator SVG": {"format": "svg", "layout_tight": True},
    "High-res PNG": {"format": "png", "layout_tight": True},
    "Print PDF": {"format": "pdf", "layout_tight": True},
}


def _ensure_export_style_prefs(app) -> dict:
    if not hasattr(app, "_export_style_prefs"):
        app._export_style_prefs = dict(DEFAULT_EXPORT_STYLE_PREFS)
    return app._export_style_prefs


def _to_float_or_none(value: str):
    s = str(value).strip()
    if not s:
        return None
    return float(s)


def apply_export_style_prefs(fig, prefs: dict) -> None:
    fig.patch.set_alpha(1.0)

    axis_target = str(prefs.get("axis_target", "All"))
    target_idx = None if axis_target == "All" else int(axis_target)

    for idx, ax in enumerate(fig.axes, start=1):
        ax.patch.set_alpha(1.0)
        ax.xaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.yaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.tick_params(axis="x", labelsize=int(prefs.get("tick_label_size", 10)))
        ax.tick_params(axis="y", labelsize=int(prefs.get("tick_label_size", 10)))
        ax.title.set_fontsize(int(prefs.get("title_size", 14)))

        for tick in ax.get_xticklabels():
            tick.set_rotation(int(prefs.get("x_tick_angle", 0)))

        for ln in ax.lines:
            ln.set_linewidth(float(prefs.get("line_width", 1.8)))
            ln.set_markersize(float(prefs.get("marker_size", 5.0)))
            ln.set_markeredgewidth(float(prefs.get("marker_edge_width", 0.8)))

        show_grid = bool(prefs.get("grid_show", True))
        ax.grid(show_grid, alpha=float(prefs.get("grid_alpha", 0.25)), linestyle=str(prefs.get("grid_style", "--")))

        if target_idx is None or idx == target_idx:
            xlo = _to_float_or_none(prefs.get("x_lim_min", ""))
            xhi = _to_float_or_none(prefs.get("x_lim_max", ""))
            ylo = _to_float_or_none(prefs.get("y_lim_min", ""))
            yhi = _to_float_or_none(prefs.get("y_lim_max", ""))
            if xlo is not None or xhi is not None:
                cur = ax.get_xlim()
                ax.set_xlim(xlo if xlo is not None else cur[0], xhi if xhi is not None else cur[1])
            if ylo is not None or yhi is not None:
                cur = ax.get_ylim()
                ax.set_ylim(ylo if ylo is not None else cur[0], yhi if yhi is not None else cur[1])
            ax.set_xscale("log" if bool(prefs.get("x_log", False)) else "linear")
            ax.set_yscale("log" if bool(prefs.get("y_log", False)) else "linear")

        if bool(prefs.get("tick_minor", False)):
            ax.minorticks_on()
        else:
            ax.minorticks_off()
        length = float(prefs.get("tick_length", 4.0))
        direction = str(prefs.get("tick_direction", "out"))
        if bool(prefs.get("tick_major", True)):
            ax.tick_params(which="major", length=length, direction=direction)
        else:
            ax.tick_params(which="major", length=0)
        if bool(prefs.get("tick_minor", False)):
            ax.tick_params(which="minor", length=max(1.0, length * 0.6), direction=direction)

        leg = ax.get_legend()
        if leg is not None:
            show_leg = bool(prefs.get("legend_show", True))
            leg.set_visible(show_leg)
            if show_leg:
                loc_name = str(prefs.get("legend_loc", "best"))
                try:
                    leg.set_loc(loc_name)  # Matplotlib >=3.8
                except Exception:
                    try:
                        from matplotlib.legend import Legend as _Legend
                        leg._loc = _Legend.codes.get(loc_name, 0)  # fallback for older versions
                    except Exception:
                        pass
            for txt in leg.get_texts():
                txt.set_fontsize(float(prefs.get("legend_font_size", 9)))

    use_constrained = bool(prefs.get("layout_constrained", False))
    use_tight = bool(prefs.get("layout_tight", False))
    try:
        if use_constrained:
            fig.set_layout_engine("constrained")
        elif use_tight:
            fig.set_layout_engine("tight")
        else:
            fig.set_layout_engine(None)
    except Exception:
        # Fallback for older matplotlib
        fig.set_constrained_layout(use_constrained)
        if use_tight and not use_constrained:
            try:
                fig.tight_layout()
            except Exception:
                pass


def apply_export_style_to_current(app, fig, canvas=None) -> None:
    prefs = _ensure_export_style_prefs(app)
    apply_export_style_prefs(fig, prefs)
    if canvas is not None:
        canvas.draw_idle()


class _ExportStyleSidebar(ttk.Frame):
    def __init__(self, app, parent, fig, canvas, default_name: str):
        super().__init__(parent, padding=(8, 8), style="Card.TFrame")
        self.configure(width=220)
        self.pack_propagate(False)
        self._app = app
        self._fig = fig
        self._canvas = canvas
        self._default_name = default_name
        self._base_dir = Path(app._data_dir) if getattr(app, "_data_dir", None) else Path.cwd()
        self._prefs = _ensure_export_style_prefs(app)
        self._updating = False

        self._vars: dict[str, tk.Variable] = {
            "axis_label_size": tk.IntVar(value=int(self._prefs["axis_label_size"])),
            "tick_label_size": tk.IntVar(value=int(self._prefs["tick_label_size"])),
            "title_size": tk.IntVar(value=int(self._prefs["title_size"])),
            "x_tick_angle": tk.IntVar(value=int(self._prefs["x_tick_angle"])),
            "format": tk.StringVar(value=str(self._prefs["format"])),
            "axis_target": tk.StringVar(value=str(self._prefs.get("axis_target", "All"))),
            "legend_show": tk.BooleanVar(value=bool(self._prefs["legend_show"])),
            "legend_font_size": tk.DoubleVar(value=float(self._prefs["legend_font_size"])),
            "legend_loc": tk.StringVar(value=str(self._prefs["legend_loc"])),
            "line_width": tk.DoubleVar(value=float(self._prefs["line_width"])),
            "marker_size": tk.DoubleVar(value=float(self._prefs["marker_size"])),
            "marker_edge_width": tk.DoubleVar(value=float(self._prefs["marker_edge_width"])),
            "grid_show": tk.BooleanVar(value=bool(self._prefs["grid_show"])),
            "grid_alpha": tk.DoubleVar(value=float(self._prefs["grid_alpha"])),
            "grid_style": tk.StringVar(value=str(self._prefs["grid_style"])),
            "x_lim_min": tk.StringVar(value=str(self._prefs["x_lim_min"])),
            "x_lim_max": tk.StringVar(value=str(self._prefs["x_lim_max"])),
            "y_lim_min": tk.StringVar(value=str(self._prefs["y_lim_min"])),
            "y_lim_max": tk.StringVar(value=str(self._prefs["y_lim_max"])),
            "x_log": tk.BooleanVar(value=bool(self._prefs["x_log"])),
            "y_log": tk.BooleanVar(value=bool(self._prefs["y_log"])),
            "tick_major": tk.BooleanVar(value=bool(self._prefs["tick_major"])),
            "tick_minor": tk.BooleanVar(value=bool(self._prefs["tick_minor"])),
            "tick_length": tk.DoubleVar(value=float(self._prefs["tick_length"])),
            "tick_direction": tk.StringVar(value=str(self._prefs["tick_direction"])),
            "layout_tight": tk.BooleanVar(value=bool(self._prefs["layout_tight"])),
            "layout_constrained": tk.BooleanVar(value=bool(self._prefs["layout_constrained"])),
            "export_profile": tk.StringVar(value=str(self._prefs["export_profile"])),
        }

        self._build_ui()
        self._bind_auto_apply()

    def _build_ui(self) -> None:
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text="Export Style", style="Title.TLabel", font=FM_BOLD).pack(side=tk.LEFT)
        ttk.Button(hdr, text="Hide", command=lambda: self.pack_forget(), style="ActionSecondary.TButton").pack(side=tk.RIGHT)

        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        canvas = tk.Canvas(wrap, width=200, height=430, highlightthickness=0, bd=0)
        vs = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
        canvas.configure(yscrollcommand=vs.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vs.pack(side=tk.RIGHT, fill=tk.Y)

        r = 0
        def add(label, widget):
            nonlocal r
            ttk.Label(body, text=label, width=5, font=FM_TINY).grid(row=r, column=0, sticky="w", pady=1)
            widget.grid(row=r, column=1, columnspan=3, sticky="ew", pady=1)
            r += 1

        add("Profile", ttk.Combobox(body, values=list(EXPORT_PROFILES.keys()), textvariable=self._vars["export_profile"], state="readonly", width=9, font=FM_TINY))
        add("Format", ttk.Combobox(body, values=["png", "svg", "pdf", "eps"], textvariable=self._vars["format"], state="readonly", width=7, font=FM_TINY))
        add("Axis #", ttk.Combobox(body, values=["All", *[str(i + 1) for i in range(len(self._fig.axes))]], textvariable=self._vars["axis_target"], state="readonly", width=7, font=FM_TINY))
        add("Axis", ttk.Spinbox(body, from_=1, to=96, textvariable=self._vars["axis_label_size"], width=7))
        add("Ticks", ttk.Spinbox(body, from_=1, to=96, textvariable=self._vars["tick_label_size"], width=7))
        add("Title", ttk.Spinbox(body, from_=1, to=128, textvariable=self._vars["title_size"], width=7))
        add("X°", ttk.Spinbox(body, from_=0, to=90, textvariable=self._vars["x_tick_angle"], width=7))

        add("Legend", ttk.Checkbutton(body, variable=self._vars["legend_show"]))
        add("Leg size", ttk.Spinbox(body, from_=6, to=24, textvariable=self._vars["legend_font_size"], width=7))
        add("Leg loc", ttk.Combobox(body, values=["best", "upper right", "upper left", "lower right", "lower left"], textvariable=self._vars["legend_loc"], state="readonly", width=9, font=FM_TINY))

        add("Line w", ttk.Spinbox(body, from_=0.1, to=8.0, increment=0.1, textvariable=self._vars["line_width"], width=7))
        add("Mkr sz", ttk.Spinbox(body, from_=0.0, to=20.0, increment=0.5, textvariable=self._vars["marker_size"], width=7))
        add("Mkr edge", ttk.Spinbox(body, from_=0.0, to=5.0, increment=0.1, textvariable=self._vars["marker_edge_width"], width=7))

        add("Grid", ttk.Checkbutton(body, variable=self._vars["grid_show"]))
        add("Grid α", ttk.Spinbox(body, from_=0.0, to=1.0, increment=0.05, textvariable=self._vars["grid_alpha"], width=7))
        add("Grid ls", ttk.Combobox(body, values=["-", "--", ":", "-."] , textvariable=self._vars["grid_style"], state="readonly", width=7, font=FM_TINY))

        limrow = ttk.Frame(body)
        ttk.Entry(limrow, textvariable=self._vars["x_lim_min"], width=6).pack(side=tk.LEFT)
        ttk.Label(limrow, text="…", font=FM_TINY).pack(side=tk.LEFT, padx=2)
        ttk.Entry(limrow, textvariable=self._vars["x_lim_max"], width=6).pack(side=tk.LEFT)
        add("X lim", limrow)

        limrow2 = ttk.Frame(body)
        ttk.Entry(limrow2, textvariable=self._vars["y_lim_min"], width=6).pack(side=tk.LEFT)
        ttk.Label(limrow2, text="…", font=FM_TINY).pack(side=tk.LEFT, padx=2)
        ttk.Entry(limrow2, textvariable=self._vars["y_lim_max"], width=6).pack(side=tk.LEFT)
        add("Y lim", limrow2)

        row_scale = ttk.Frame(body)
        ttk.Checkbutton(row_scale, text="X log", variable=self._vars["x_log"]).pack(side=tk.LEFT)
        ttk.Checkbutton(row_scale, text="Y log", variable=self._vars["y_log"]).pack(side=tk.LEFT, padx=6)
        add("Scale", row_scale)

        row_tick = ttk.Frame(body)
        ttk.Checkbutton(row_tick, text="Major", variable=self._vars["tick_major"]).pack(side=tk.LEFT)
        ttk.Checkbutton(row_tick, text="Minor", variable=self._vars["tick_minor"]).pack(side=tk.LEFT, padx=6)
        add("Tick vis", row_tick)
        add("Tick len", ttk.Spinbox(body, from_=0.0, to=20.0, increment=0.5, textvariable=self._vars["tick_length"], width=7))
        add("Tick dir", ttk.Combobox(body, values=["out", "in", "inout"], textvariable=self._vars["tick_direction"], state="readonly", width=7, font=FM_TINY))
        lay = ttk.Frame(body)
        ttk.Checkbutton(lay, text="Tight", variable=self._vars["layout_tight"]).pack(side=tk.LEFT)
        ttk.Checkbutton(lay, text="Constrained", variable=self._vars["layout_constrained"]).pack(side=tk.LEFT, padx=6)
        add("Layout", lay)

        btns = ttk.Frame(body)
        btns.grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Button(btns, text="Reset", command=self._reset_defaults, style="ActionSecondary.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btns, text="Export…", command=self._export, style="ActionSuccess.TButton").pack(side=tk.LEFT)

        for c in (1, 2, 3):
            body.columnconfigure(c, weight=1)

    def _bind_auto_apply(self) -> None:
        for var in self._vars.values():
            var.trace_add("write", lambda *_args: self._on_fields_changed())
        self._vars["export_profile"].trace_add("write", lambda *_args: self._on_profile_selected())

    def _on_profile_selected(self) -> None:
        if self._updating:
            return
        profile = self._vars["export_profile"].get()
        overrides = EXPORT_PROFILES.get(profile, {})
        if not overrides:
            return
        self._updating = True
        try:
            for k, v in overrides.items():
                if k in self._vars:
                    self._vars[k].set(v)
        finally:
            self._updating = False

    def _persist(self) -> None:
        for k, var in self._vars.items():
            self._prefs[k] = var.get()

    def _on_fields_changed(self) -> None:
        if self._updating:
            return
        try:
            self._persist()
            apply_export_style_to_current(self._app, self._fig, self._canvas)
        except Exception:
            pass

    def _reset_defaults(self) -> None:
        self._updating = True
        try:
            defaults = dict(DEFAULT_EXPORT_STYLE_PREFS)
            for k, var in self._vars.items():
                if k in defaults:
                    var.set(defaults[k])
        finally:
            self._updating = False
        self._on_fields_changed()

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
        if canvas_widget is not None and canvas_widget.winfo_manager() == "pack":
            try:
                pinfo = dict(canvas_widget.pack_info())
                canvas_widget.pack_forget()
                pinfo["side"] = tk.LEFT
                canvas_widget.pack(**pinfo)
            except Exception:
                pass
        if not sb.winfo_ismapped():
            sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=(8, 8))
            sb.lift()
        sb._on_fields_changed()
        return _ExportEditorSession(sb)
    except Exception as exc:
        messagebox.showwarning("Export editor unavailable", str(exc), parent=app)
        return None
