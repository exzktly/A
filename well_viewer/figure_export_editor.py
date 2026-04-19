"""In-tab export style sidebar for matplotlib figures (Qt port)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

DEFAULT_EXPORT_STYLE_PREFS = {
    "axis_label_size": 22,
    "tick_label_size": 22,
    "title_size": 22,
    "x_tick_angle": 0,
    "format": "png",
    "axis_target": "All",
    "legend_show": True,
    "legend_font_size": 12,
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
    "Helvetica 22": {
        "axis_label_size": 22,
        "tick_label_size": 22,
        "title_size": 22,
        "legend_font_size": 22,
    },
}


def _ensure_export_style_prefs(app) -> dict:
    if not hasattr(app, "_export_style_prefs"):
        app._export_style_prefs = dict(DEFAULT_EXPORT_STYLE_PREFS)
    return app._export_style_prefs


def _ensure_custom_export_profiles(app) -> dict:
    if not hasattr(app, "_export_style_custom_profiles"):
        app._export_style_custom_profiles = {}
    return app._export_style_custom_profiles


def _get_all_profile_names(app) -> list[str]:
    custom = _ensure_custom_export_profiles(app)
    return [*EXPORT_PROFILES.keys(), *custom.keys()]


def _to_float_or_none(value: str):
    s = str(value).strip()
    if not s:
        return None
    return float(s)


def apply_export_style_prefs(fig, prefs: dict) -> None:
    for ax in fig.axes:
        if not hasattr(ax, "_fixed_axes_position"):
            ax._fixed_axes_position = ax.get_position().frozen()

    fig.patch.set_alpha(1.0)

    axis_target = str(prefs.get("axis_target", "All"))
    target_idx = None if axis_target == "All" else int(axis_target)

    for idx, ax in enumerate(fig.axes, start=1):
        ax.patch.set_alpha(1.0)
        ax.xaxis.label.set_color("black")
        ax.yaxis.label.set_color("black")
        ax.xaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.yaxis.label.set_fontsize(int(prefs.get("axis_label_size", 12)))
        ax.tick_params(axis="x", labelsize=int(prefs.get("tick_label_size", 10)), colors="black")
        ax.tick_params(axis="y", labelsize=int(prefs.get("tick_label_size", 10)), colors="black")
        ax.title.set_fontsize(int(prefs.get("title_size", 14)))
        ax.title.set_color("black")

        for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            tick.set_color("black")
            tick.set_fontfamily("Helvetica")
            tick.set_fontsize(int(prefs.get("tick_label_size", 10)))

        ax.xaxis.label.set_fontfamily("Helvetica")
        ax.yaxis.label.set_fontfamily("Helvetica")
        ax.title.set_fontfamily("Helvetica")

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
            if not getattr(ax, "_categorical_xaxis", False):
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
                    leg.set_loc(loc_name)
                except Exception:
                    try:
                        from matplotlib.legend import Legend as _Legend
                        leg._loc = _Legend.codes.get(loc_name, 0)
                    except Exception:
                        pass
            for txt in leg.get_texts():
                txt.set_fontsize(float(prefs.get("legend_font_size", 9)))
                txt.set_color("black")
                txt.set_fontfamily("Helvetica")

        fixed_pos = getattr(ax, "_fixed_axes_position", None)
        if fixed_pos is not None:
            ax.set_position(fixed_pos)

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


class _ExportStyleSidebar(QWidget):
    def __init__(self, app, parent, fig, canvas, default_name: str):
        super().__init__(parent)
        self.setObjectName("Card")
        self._app = app
        self._fig = fig
        self._canvas = canvas
        self._default_name = default_name
        self._base_dir = Path(app._data_dir) if getattr(app, "_data_dir", None) else Path.cwd()
        self._prefs = _ensure_export_style_prefs(app)
        self._updating = False
        self._getters: dict[str, Callable[[], object]] = {}
        self._setters: dict[str, Callable[[object], None]] = {}

        self.setFixedWidth(260)
        self._build_ui()

    def _bind_getter_setter(self, key: str, widget) -> None:
        """Register read/write hooks and wire a change signal to auto-apply."""
        if isinstance(widget, QSpinBox):
            self._getters[key] = widget.value
            self._setters[key] = lambda v, w=widget: w.setValue(int(v))
            widget.valueChanged.connect(lambda _v: self._on_fields_changed())
        elif isinstance(widget, QDoubleSpinBox):
            self._getters[key] = widget.value
            self._setters[key] = lambda v, w=widget: w.setValue(float(v))
            widget.valueChanged.connect(lambda _v: self._on_fields_changed())
        elif isinstance(widget, QComboBox):
            self._getters[key] = widget.currentText
            self._setters[key] = lambda v, w=widget: w.setCurrentText(str(v))
            widget.currentTextChanged.connect(lambda _t: self._on_fields_changed())
        elif isinstance(widget, QCheckBox):
            self._getters[key] = widget.isChecked
            self._setters[key] = lambda v, w=widget: w.setChecked(bool(v))
            widget.toggled.connect(lambda _c: self._on_fields_changed())
        elif isinstance(widget, QLineEdit):
            self._getters[key] = widget.text
            self._setters[key] = lambda v, w=widget: w.setText(str(v))
            widget.textChanged.connect(lambda _t: self._on_fields_changed())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        hdr = QWidget(self)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Export Style", hdr)
        title.setProperty("role", "section")
        hl.addWidget(title)
        hl.addStretch(1)
        close_btn = QPushButton("◂", hdr)
        close_btn.setProperty("variant", "secondary")
        close_btn.setFixedWidth(28)
        close_btn.clicked.connect(lambda _=False: self.hide())
        hl.addWidget(close_btn)
        root.addWidget(hdr)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("Card")
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        row = 0

        def add_row(label: str, widget: QWidget, key: str | None = None) -> None:
            nonlocal row
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
            if key is not None:
                self._bind_getter_setter(key, widget)
            row += 1

        self._profile_combo = QComboBox(body)
        self._profile_combo.addItems(_get_all_profile_names(self._app))
        self._profile_combo.setCurrentText(str(self._prefs.get("export_profile", "Custom")))
        self._profile_combo.currentTextChanged.connect(lambda _t: self._on_profile_selected())
        add_row("Profile", self._profile_combo, "export_profile")

        fmt_cb = QComboBox(body)
        fmt_cb.addItems(["png", "svg", "pdf", "eps"])
        fmt_cb.setCurrentText(str(self._prefs["format"]))
        add_row("Format", fmt_cb, "format")

        axis_cb = QComboBox(body)
        axis_cb.addItems(["All", *[str(i + 1) for i in range(len(self._fig.axes))]])
        axis_cb.setCurrentText(str(self._prefs.get("axis_target", "All")))
        add_row("Axis #", axis_cb, "axis_target")

        for key, label, lo, hi in [
            ("axis_label_size", "Axis", 1, 96),
            ("tick_label_size", "Ticks", 1, 96),
            ("title_size", "Title", 1, 128),
            ("x_tick_angle", "X°", 0, 90),
        ]:
            sp = QSpinBox(body)
            sp.setRange(lo, hi)
            sp.setValue(int(self._prefs[key]))
            add_row(label, sp, key)

        cb = QCheckBox(body)
        cb.setChecked(bool(self._prefs["legend_show"]))
        add_row("Legend", cb, "legend_show")

        sp = QSpinBox(body)
        sp.setRange(6, 24)
        sp.setValue(int(self._prefs["legend_font_size"]))
        add_row("Leg size", sp, "legend_font_size")

        loc_cb = QComboBox(body)
        loc_cb.addItems(["best", "upper right", "upper left", "lower right", "lower left"])
        loc_cb.setCurrentText(str(self._prefs["legend_loc"]))
        add_row("Leg loc", loc_cb, "legend_loc")

        for key, label, lo, hi, step in [
            ("line_width", "Line w", 0.1, 8.0, 0.1),
            ("marker_size", "Mkr sz", 0.0, 20.0, 0.5),
            ("marker_edge_width", "Mkr edge", 0.0, 5.0, 0.1),
        ]:
            dsp = QDoubleSpinBox(body)
            dsp.setRange(lo, hi)
            dsp.setSingleStep(step)
            dsp.setValue(float(self._prefs[key]))
            add_row(label, dsp, key)

        gshow = QCheckBox(body)
        gshow.setChecked(bool(self._prefs["grid_show"]))
        add_row("Grid", gshow, "grid_show")

        galpha = QDoubleSpinBox(body)
        galpha.setRange(0.0, 1.0)
        galpha.setSingleStep(0.05)
        galpha.setValue(float(self._prefs["grid_alpha"]))
        add_row("Grid α", galpha, "grid_alpha")

        gstyle = QComboBox(body)
        gstyle.addItems(["-", "--", ":", "-."])
        gstyle.setCurrentText(str(self._prefs["grid_style"]))
        add_row("Grid ls", gstyle, "grid_style")

        for lim_key, label in [("x_lim", "X lim"), ("y_lim", "Y lim")]:
            row_widget = QWidget(body)
            rl = QHBoxLayout(row_widget)
            rl.setContentsMargins(0, 0, 0, 0)
            lo_edit = QLineEdit(str(self._prefs[f"{lim_key}_min"]), row_widget)
            lo_edit.setFixedWidth(60)
            rl.addWidget(lo_edit)
            rl.addWidget(QLabel("…", row_widget))
            hi_edit = QLineEdit(str(self._prefs[f"{lim_key}_max"]), row_widget)
            hi_edit.setFixedWidth(60)
            rl.addWidget(hi_edit)
            self._bind_getter_setter(f"{lim_key}_min", lo_edit)
            self._bind_getter_setter(f"{lim_key}_max", hi_edit)
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(row_widget, row, 1)
            row += 1

        scale_row = QWidget(body)
        srl = QHBoxLayout(scale_row)
        srl.setContentsMargins(0, 0, 0, 0)
        xlog_cb = QCheckBox("X log", scale_row)
        xlog_cb.setChecked(bool(self._prefs["x_log"]))
        srl.addWidget(xlog_cb)
        ylog_cb = QCheckBox("Y log", scale_row)
        ylog_cb.setChecked(bool(self._prefs["y_log"]))
        srl.addWidget(ylog_cb)
        self._bind_getter_setter("x_log", xlog_cb)
        self._bind_getter_setter("y_log", ylog_cb)
        grid.addWidget(QLabel("Scale"), row, 0)
        grid.addWidget(scale_row, row, 1)
        row += 1

        tick_row = QWidget(body)
        trl = QHBoxLayout(tick_row)
        trl.setContentsMargins(0, 0, 0, 0)
        maj_cb = QCheckBox("Major", tick_row)
        maj_cb.setChecked(bool(self._prefs["tick_major"]))
        trl.addWidget(maj_cb)
        min_cb = QCheckBox("Minor", tick_row)
        min_cb.setChecked(bool(self._prefs["tick_minor"]))
        trl.addWidget(min_cb)
        self._bind_getter_setter("tick_major", maj_cb)
        self._bind_getter_setter("tick_minor", min_cb)
        grid.addWidget(QLabel("Tick vis"), row, 0)
        grid.addWidget(tick_row, row, 1)
        row += 1

        tlen = QDoubleSpinBox(body)
        tlen.setRange(0.0, 20.0)
        tlen.setSingleStep(0.5)
        tlen.setValue(float(self._prefs["tick_length"]))
        add_row("Tick len", tlen, "tick_length")

        tdir = QComboBox(body)
        tdir.addItems(["out", "in", "inout"])
        tdir.setCurrentText(str(self._prefs["tick_direction"]))
        add_row("Tick dir", tdir, "tick_direction")

        lay_row = QWidget(body)
        lrl = QHBoxLayout(lay_row)
        lrl.setContentsMargins(0, 0, 0, 0)
        tight_cb = QCheckBox("Tight", lay_row)
        tight_cb.setChecked(bool(self._prefs["layout_tight"]))
        lrl.addWidget(tight_cb)
        cons_cb = QCheckBox("Constrained", lay_row)
        cons_cb.setChecked(bool(self._prefs["layout_constrained"]))
        lrl.addWidget(cons_cb)
        self._bind_getter_setter("layout_tight", tight_cb)
        self._bind_getter_setter("layout_constrained", cons_cb)
        grid.addWidget(QLabel("Layout"), row, 0)
        grid.addWidget(lay_row, row, 1)
        row += 1

        btns = QWidget(body)
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 8, 0, 0)
        reset_btn = QPushButton("Reset", btns)
        reset_btn.setProperty("variant", "secondary")
        reset_btn.clicked.connect(lambda _=False: self._reset_defaults())
        bl.addWidget(reset_btn)
        save_btn = QPushButton("Save Preset", btns)
        save_btn.setProperty("variant", "secondary")
        save_btn.clicked.connect(lambda _=False: self._save_preset())
        bl.addWidget(save_btn)
        exp_btn = QPushButton("Export…", btns)
        exp_btn.setProperty("variant", "primary")
        exp_btn.clicked.connect(lambda _=False: self._export())
        bl.addWidget(exp_btn)
        grid.addWidget(btns, row, 0, 1, 2)
        row += 1

        grid.setColumnStretch(1, 1)

    def _on_profile_selected(self) -> None:
        if self._updating:
            return
        profile = self._profile_combo.currentText()
        overrides = EXPORT_PROFILES.get(profile, {})
        if not overrides:
            custom_profiles = _ensure_custom_export_profiles(self._app)
            overrides = custom_profiles.get(profile, {})
        if not overrides:
            self._on_fields_changed()
            return
        self._updating = True
        try:
            for k, v in overrides.items():
                if k in self._setters:
                    self._setters[k](v)
        finally:
            self._updating = False
        self._on_fields_changed()

    def _persist(self) -> None:
        for k, getter in self._getters.items():
            self._prefs[k] = getter()

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
            for k, v in DEFAULT_EXPORT_STYLE_PREFS.items():
                if k in self._setters:
                    self._setters[k](v)
        finally:
            self._updating = False
        self._on_fields_changed()

    def _save_preset(self) -> None:
        try:
            self._persist()
            name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
            if not ok:
                return
            preset_name = name.strip()
            if not preset_name:
                return
            if preset_name in EXPORT_PROFILES:
                QMessageBox.warning(self, "Preset exists", "Cannot overwrite built-in preset name.")
                return
            custom_profiles = _ensure_custom_export_profiles(self._app)
            custom_profiles[preset_name] = dict(self._prefs)
            self._profile_combo.blockSignals(True)
            self._profile_combo.clear()
            self._profile_combo.addItems(_get_all_profile_names(self._app))
            self._profile_combo.setCurrentText(preset_name)
            self._profile_combo.blockSignals(False)
            self._app._set_status(f"Saved export preset: {preset_name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save preset failed", str(exc))

    def _export(self) -> None:
        try:
            self._persist()
            fmt = (self._prefs.get("format") or "png").lower()
            initialfile = self._default_name
            if not initialfile.lower().endswith(f".{fmt}"):
                initialfile = f"{Path(initialfile).stem}.{fmt}"
            start = str(self._base_dir / initialfile)
            out, _filter = QFileDialog.getSaveFileName(
                self, "Save figure", start,
                f"Image (*.{fmt});;All files (*.*)",
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
            QMessageBox.critical(self, "Export failed", str(exc))


class _ExportEditorSession:
    def __init__(self, sidebar: _ExportStyleSidebar) -> None:
        self.sidebar = sidebar


def launch_export_editor(app, fig, default_name: str, *, plot_bg: str = "",
                          canvas=None) -> _ExportEditorSession | None:
    try:
        parent = canvas.parent() if canvas is not None else app
        if not hasattr(app, "_export_style_sidebars"):
            app._export_style_sidebars = {}
        key = id(fig)
        sb = app._export_style_sidebars.get(key)
        if sb is None:
            sb = _ExportStyleSidebar(app, parent, fig, canvas, default_name=default_name)
            app._export_style_sidebars[key] = sb

            # Attach sidebar into the canvas's parent layout on first show so it
            # sits next to the figure.
            if canvas is not None:
                canvas_parent = canvas.parentWidget()
                if canvas_parent is not None:
                    parent_layout = canvas_parent.layout()
                    if parent_layout is not None and hasattr(parent_layout, "addWidget"):
                        parent_layout.addWidget(sb)

        sb.show()
        sb.raise_()
        sb._on_fields_changed()
        return _ExportEditorSession(sb)
    except Exception as exc:
        QMessageBox.warning(app if isinstance(app, QWidget) else None,
                            "Export editor unavailable", str(exc))
        return None
