"""Plotly-based figure export editor for matplotlib figures."""

from __future__ import annotations

import copy
import tempfile
import webbrowser
from pathlib import Path
from tkinter import colorchooser, messagebox

import tkinter as tk
from tkinter import ttk


def _apply_export_style(
    fig,
    *,
    background_color: str,
    axis_label_size: int,
    tick_label_size: int,
    title_size: int,
    line_marker_face_color: str,
    bar_face_color: str,
    x_tick_angle: int,
) -> None:
    fig.set_facecolor(background_color)
    for ax in fig.axes:
        ax.set_facecolor(background_color)
        ax.xaxis.label.set_fontsize(axis_label_size)
        ax.yaxis.label.set_fontsize(axis_label_size)
        ax.tick_params(axis="x", labelsize=tick_label_size)
        ax.tick_params(axis="y", labelsize=tick_label_size)
        ax.title.set_fontsize(title_size)

        for tick in ax.get_xticklabels():
            tick.set_rotation(x_tick_angle)

        for ln in ax.lines:
            ln.set_markerfacecolor(line_marker_face_color)

        for patch in ax.patches:
            patch.set_facecolor(bar_face_color)


class _PlotlyExportEditorSession:
    def __init__(self, window: tk.Toplevel) -> None:
        self.window = window


class _PlotlyExportEditorDialog(tk.Toplevel):
    def __init__(self, app, fig, default_name: str, plot_bg: str):
        super().__init__(app)
        self._app = app
        self._source_fig = copy.deepcopy(fig)
        self._default_name = default_name
        self._base_dir = Path(app._data_dir) if getattr(app, "_data_dir", None) else Path.cwd()

        self.title("Figure Export Editor")
        self.configure(padx=12, pady=12)
        self.resizable(False, False)

        self._bg_var = tk.StringVar(value=plot_bg)
        self._axis_var = tk.IntVar(value=12)
        self._tick_var = tk.IntVar(value=10)
        self._title_var = tk.IntVar(value=14)
        self._line_color_var = tk.StringVar(value="#1f77b4")
        self._bar_color_var = tk.StringVar(value="#1f77b4")
        self._fmt_var = tk.StringVar(value="png")
        self._xangle_var = tk.IntVar(value=0)
        self._name_var = tk.StringVar(value=default_name)
        self._dir_var = tk.StringVar(value=str(self._base_dir))
        self._status_var = tk.StringVar(value="Edit settings, then preview or export.")

        self._build_ui()

    def _add_row(self, row: int, label: str, widget: tk.Widget) -> None:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        widget.grid(row=row, column=1, sticky="ew", pady=3)

    def _choose_color(self, var: tk.StringVar) -> None:
        chosen = colorchooser.askcolor(color=var.get(), parent=self)[1]
        if chosen:
            var.set(chosen)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self._add_row(0, "Background", ttk.Entry(self, textvariable=self._bg_var, width=20))
        self._add_row(1, "Axis label size", ttk.Spinbox(self, from_=1, to=72, textvariable=self._axis_var, width=8))
        self._add_row(2, "Tick label size", ttk.Spinbox(self, from_=1, to=72, textvariable=self._tick_var, width=8))
        self._add_row(3, "Title size", ttk.Spinbox(self, from_=1, to=96, textvariable=self._title_var, width=8))

        line_frame = ttk.Frame(self)
        ttk.Entry(line_frame, textvariable=self._line_color_var, width=18).pack(side=tk.LEFT)
        ttk.Button(line_frame, text="Pick", command=lambda: self._choose_color(self._line_color_var)).pack(side=tk.LEFT, padx=4)
        self._add_row(4, "Line marker color", line_frame)

        bar_frame = ttk.Frame(self)
        ttk.Entry(bar_frame, textvariable=self._bar_color_var, width=18).pack(side=tk.LEFT)
        ttk.Button(bar_frame, text="Pick", command=lambda: self._choose_color(self._bar_color_var)).pack(side=tk.LEFT, padx=4)
        self._add_row(5, "Bar face color", bar_frame)

        self._add_row(6, "X tick angle", ttk.Spinbox(self, from_=0, to=90, increment=5, textvariable=self._xangle_var, width=8))
        self._add_row(7, "Format", ttk.Combobox(self, values=["png", "svg", "pdf", "eps"], textvariable=self._fmt_var, state="readonly", width=8))
        self._add_row(8, "Filename", ttk.Entry(self, textvariable=self._name_var, width=32))
        self._add_row(9, "Output dir", ttk.Entry(self, textvariable=self._dir_var, width=32))

        btn_row = ttk.Frame(self)
        btn_row.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        ttk.Button(btn_row, text="Preview in Plotly", command=self._preview_plotly).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Export", command=self._export).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="Close", command=self.destroy).pack(side=tk.LEFT)

        ttk.Label(self, textvariable=self._status_var).grid(row=11, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _styled_copy(self):
        work_fig = copy.deepcopy(self._source_fig)
        _apply_export_style(
            work_fig,
            background_color=self._bg_var.get() or "white",
            axis_label_size=int(self._axis_var.get()),
            tick_label_size=int(self._tick_var.get()),
            title_size=int(self._title_var.get()),
            line_marker_face_color=self._line_color_var.get() or "#1f77b4",
            bar_face_color=self._bar_color_var.get() or "#1f77b4",
            x_tick_angle=int(self._xangle_var.get()),
        )
        return work_fig

    def _preview_plotly(self) -> None:
        try:
            import plotly.io as pio
            from plotly.tools import mpl_to_plotly

            pfig = mpl_to_plotly(self._styled_copy())
            html = pio.to_html(pfig, include_plotlyjs="cdn", full_html=True)
            tmp = Path(tempfile.gettempdir()) / "well_viewer_export_preview.html"
            tmp.write_text(html, encoding="utf-8")
            webbrowser.open(tmp.as_uri())
            self._status_var.set(f"Opened preview: {tmp}")
        except Exception as exc:
            messagebox.showerror("Plotly preview failed", str(exc), parent=self)

    def _export(self) -> None:
        try:
            fmt = (self._fmt_var.get() or "png").lower()
            out_name = (self._name_var.get() or self._default_name).strip() or self._default_name
            if not out_name.lower().endswith(f".{fmt}"):
                out_name = f"{Path(out_name).stem}.{fmt}"
            out_path = Path(self._dir_var.get() or str(self._base_dir)) / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            kw = {"format": fmt, "bbox_inches": "tight", "facecolor": self._bg_var.get() or "white"}
            if fmt == "png":
                kw["dpi"] = 300
            self._styled_copy().savefig(str(out_path), **kw)
            self._status_var.set(f"Saved: {out_path}")
            self._app._set_status(f"Figure saved → {out_path.name}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)


def launch_dash_export_editor(app, fig, default_name: str, *, plot_bg: str) -> _PlotlyExportEditorSession | None:
    """Launch the Plotly-based export editor dialog.

    Kept function name for backwards compatibility with existing orchestration calls.
    """
    try:
        dlg = _PlotlyExportEditorDialog(app, fig, default_name=default_name, plot_bg=plot_bg)
        dlg.transient(app)
        dlg.grab_set()
        return _PlotlyExportEditorSession(window=dlg)
    except Exception as exc:
        messagebox.showwarning("Export editor unavailable", str(exc), parent=app)
        return None
