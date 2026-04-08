"""Dash-powered figure export editor for matplotlib figures."""

from __future__ import annotations

import base64
import copy
import io
import socket
import threading
import webbrowser
from pathlib import Path


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _render_preview_png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode("ascii")


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


class _DashExportEditorSession:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


def launch_dash_export_editor(app, fig, default_name: str, *, plot_bg: str) -> _DashExportEditorSession | None:
    """Launch a Dash UI for export-only figure styling and saving."""
    try:
        from dash import Dash, Input, Output, State, dcc, html, no_update
    except Exception as exc:
        try:
            app._set_status(f"Dash editor unavailable ({exc}); using classic save dialog.")
        except Exception:
            pass
        return None

    source_fig = copy.deepcopy(fig)
    base_dir = Path(app._data_dir) if getattr(app, "_data_dir", None) else Path.cwd()
    port = _find_free_port()
    host = "127.0.0.1"

    dash_app = Dash(__name__)
    dash_app.layout = html.Div(
        [
            html.H3("Figure Export Editor"),
            html.Div(
                [
                    html.Label("Export background color"),
                    dcc.Input(id="bg", type="text", value=plot_bg, debounce=True),
                    html.Label("Axis label size"),
                    dcc.Input(id="axis_label_size", type="number", value=12, min=1, step=1),
                    html.Label("Tick label size"),
                    dcc.Input(id="tick_label_size", type="number", value=10, min=1, step=1),
                    html.Label("Title size"),
                    dcc.Input(id="title_size", type="number", value=14, min=1, step=1),
                    html.Label("Line marker face color"),
                    dcc.Input(id="line_marker_face_color", type="text", value="#1f77b4", debounce=True),
                    html.Label("Bar face color"),
                    dcc.Input(id="bar_face_color", type="text", value="#1f77b4", debounce=True),
                    html.Label("Export format"),
                    dcc.Dropdown(
                        id="fmt",
                        options=[{"label": x.upper(), "value": x} for x in ("png", "svg", "pdf", "eps")],
                        value="png",
                        clearable=False,
                    ),
                    html.Label("X tick angle"),
                    dcc.Slider(id="x_tick_angle", min=0, max=90, step=5, value=0),
                    html.Label("Output filename"),
                    dcc.Input(id="filename", type="text", value=default_name),
                    html.Label("Output directory"),
                    dcc.Input(id="out_dir", type="text", value=str(base_dir), debounce=True),
                    html.Button("Export", id="export_btn", n_clicks=0),
                    html.Div(id="export_status", style={"marginTop": "8px"}),
                ],
                style={"display": "grid", "gap": "6px", "maxWidth": "520px"},
            ),
            html.Hr(),
            html.Img(id="preview", style={"maxWidth": "95%", "border": "1px solid #ccc"}),
        ],
        style={"fontFamily": "sans-serif", "padding": "16px"},
    )

    @dash_app.callback(
        Output("preview", "src"),
        Input("bg", "value"),
        Input("axis_label_size", "value"),
        Input("tick_label_size", "value"),
        Input("title_size", "value"),
        Input("line_marker_face_color", "value"),
        Input("bar_face_color", "value"),
        Input("x_tick_angle", "value"),
    )
    def _update_preview(bg, axis_label_size, tick_label_size, title_size, line_color, bar_color, x_angle):
        work_fig = copy.deepcopy(source_fig)
        _apply_export_style(
            work_fig,
            background_color=bg or plot_bg,
            axis_label_size=int(axis_label_size or 12),
            tick_label_size=int(tick_label_size or 10),
            title_size=int(title_size or 14),
            line_marker_face_color=line_color or "#1f77b4",
            bar_face_color=bar_color or "#1f77b4",
            x_tick_angle=int(x_angle or 0),
        )
        return f"data:image/png;base64,{_render_preview_png(work_fig)}"

    @dash_app.callback(
        Output("export_status", "children"),
        Input("export_btn", "n_clicks"),
        State("bg", "value"),
        State("axis_label_size", "value"),
        State("tick_label_size", "value"),
        State("title_size", "value"),
        State("line_marker_face_color", "value"),
        State("bar_face_color", "value"),
        State("fmt", "value"),
        State("x_tick_angle", "value"),
        State("filename", "value"),
        State("out_dir", "value"),
        prevent_initial_call=True,
    )
    def _export(
        n_clicks,
        bg,
        axis_label_size,
        tick_label_size,
        title_size,
        line_color,
        bar_color,
        fmt,
        x_angle,
        filename,
        out_dir,
    ):
        if not n_clicks:
            return no_update
        work_fig = copy.deepcopy(source_fig)
        _apply_export_style(
            work_fig,
            background_color=bg or plot_bg,
            axis_label_size=int(axis_label_size or 12),
            tick_label_size=int(tick_label_size or 10),
            title_size=int(title_size or 14),
            line_marker_face_color=line_color or "#1f77b4",
            bar_face_color=bar_color or "#1f77b4",
            x_tick_angle=int(x_angle or 0),
        )
        out_name = (filename or default_name).strip() or default_name
        fmt = (fmt or "png").lower()
        if not out_name.lower().endswith(f".{fmt}"):
            out_name = f"{Path(out_name).stem}.{fmt}"
        out_path = Path(out_dir or str(base_dir)) / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        kw = {"format": fmt, "bbox_inches": "tight", "facecolor": bg or plot_bg}
        if fmt == "png":
            kw["dpi"] = 300
        work_fig.savefig(str(out_path), **kw)
        try:
            app._set_status(f"Figure saved → {out_path.name}")
        except Exception:
            pass
        return f"Saved: {out_path}"

    def _run() -> None:
        dash_app.run(host=host, port=port, debug=False)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    webbrowser.open(f"http://{host}:{port}")
    return _DashExportEditorSession(host=host, port=port)
