"""Export-style sidebar view (extracted from ``figure_export_editor``).

Hosts the ``_ExportStyleSidebar`` widget that lives inside each plot tab's
right-side dock. Pure view: prefs persistence, profile lookups, and the
matplotlib export pipeline live in ``well_viewer.figure_export_editor``.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from well_viewer.figure_export_editor import (
    DEFAULT_EXPORT_STYLE_PREFS,
    EXPORT_PROFILES,
    _ensure_custom_export_profiles,
    _ensure_export_style_prefs,
    _get_all_profile_names,
    _resolve_export_dock,
    apply_export_style_to_current,
)


class ExportStyleSidebar(QWidget):
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
        close_btn.clicked.connect(lambda _=False: self._close_dock())
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

        # ── Line plot reorder panel (only when bound to the line-plot figure)
        self._line_order_rsets_list: QListWidget | None = None
        self._line_order_wells_list: QListWidget | None = None
        if self._is_line_fig():
            grid.addWidget(QLabel("Replicate Set Order"), row, 0, 1, 2)
            row += 1
            rs_list = QListWidget(body)
            rs_list.setDragDropMode(QAbstractItemView.InternalMove)
            rs_list.setSelectionMode(QAbstractItemView.SingleSelection)
            rs_list.setMaximumHeight(120)
            rs_list.model().rowsMoved.connect(
                lambda *_: self._on_line_order_rsets_changed()
            )
            grid.addWidget(rs_list, row, 0, 1, 2)
            self._line_order_rsets_list = rs_list
            row += 1

            grid.addWidget(QLabel("Well Order"), row, 0, 1, 2)
            row += 1
            w_list = QListWidget(body)
            w_list.setDragDropMode(QAbstractItemView.InternalMove)
            w_list.setSelectionMode(QAbstractItemView.SingleSelection)
            w_list.setMaximumHeight(120)
            w_list.model().rowsMoved.connect(
                lambda *_: self._on_line_order_wells_changed()
            )
            grid.addWidget(w_list, row, 0, 1, 2)
            self._line_order_wells_list = w_list
            row += 1
            self._refresh_line_order_lists()

        # ── Clipboard copy row
        clip = QWidget(body)
        cl = QHBoxLayout(clip)
        cl.setContentsMargins(0, 8, 0, 0)
        copy_png_btn = QPushButton("Copy PNG", clip)
        copy_png_btn.setProperty("variant", "secondary")
        copy_png_btn.clicked.connect(lambda _=False: self._copy_png())
        cl.addWidget(copy_png_btn)
        copy_svg_btn = QPushButton("Copy SVG", clip)
        copy_svg_btn.setProperty("variant", "secondary")
        copy_svg_btn.clicked.connect(lambda _=False: self._copy_svg())
        cl.addWidget(copy_svg_btn)
        grid.addWidget(clip, row, 0, 1, 2)
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

    def _close_dock(self) -> None:
        self.hide()
        dock = _resolve_export_dock(self._app, self._fig)
        if dock is not None:
            dock.setVisible(False)

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

    # ── Clipboard copy ───────────────────────────────────────────────────────

    def _copy_png(self) -> None:
        """Copy the current figure to the clipboard as a PNG image."""
        try:
            self._persist()
            apply_export_style_to_current(self._app, self._fig, self._canvas)
            buf = BytesIO()
            self._fig.savefig(
                buf, format="png", dpi=300,
                bbox_inches="tight", transparent=False,
            )
            img = QImage.fromData(buf.getvalue(), "PNG")
            if img.isNull():
                QMessageBox.critical(self, "Copy failed", "Could not encode PNG.")
                return
            QApplication.clipboard().setPixmap(QPixmap.fromImage(img))
            self._app._set_status("Figure copied to clipboard (PNG)")
        except Exception as exc:
            QMessageBox.critical(self, "Copy PNG failed", str(exc))

    def _copy_svg(self) -> None:
        """Copy the current figure to the clipboard as SVG markup."""
        try:
            self._persist()
            apply_export_style_to_current(self._app, self._fig, self._canvas)
            import matplotlib as _mpl
            from PySide6.QtCore import QMimeData
            orig_svg = _mpl.rcParams.get("svg.fonttype", "path")
            _mpl.rcParams["svg.fonttype"] = "none"
            try:
                buf = BytesIO()
                self._fig.savefig(
                    buf, format="svg",
                    bbox_inches="tight", transparent=True,
                )
            finally:
                _mpl.rcParams["svg.fonttype"] = orig_svg
            data = buf.getvalue()
            mime = QMimeData()
            mime.setData("image/svg+xml", QByteArray(data))
            try:
                mime.setText(data.decode("utf-8"))
            except UnicodeDecodeError:
                pass
            QApplication.clipboard().setMimeData(mime)
            self._app._set_status("Figure copied to clipboard (SVG)")
        except Exception as exc:
            QMessageBox.critical(self, "Copy SVG failed", str(exc))

    # ── Line-plot reorder ────────────────────────────────────────────────────

    def _is_line_fig(self) -> bool:
        return getattr(self._app, "_line_fig", None) is self._fig

    def _refresh_line_order_lists(self) -> None:
        """Repopulate the rep-set / well order lists from current app state."""
        app = self._app
        if self._line_order_rsets_list is not None:
            self._line_order_rsets_list.blockSignals(True)
            self._line_order_rsets_list.clear()
            try:
                active = app._rep_sets_active() or []
            except Exception:
                active = []
            names = [getattr(rs, "name", "") for rs in active if getattr(rs, "name", "")]
            saved = list(getattr(app, "_line_order_rsets", []) or [])
            ordered = [n for n in saved if n in names] + [n for n in names if n not in saved]
            for n in ordered:
                self._line_order_rsets_list.addItem(n)
            self._line_order_rsets_list.blockSignals(False)

        if self._line_order_wells_list is not None:
            self._line_order_wells_list.blockSignals(True)
            self._line_order_wells_list.clear()
            try:
                selected = list(app._selected_labels() or [])
            except Exception:
                selected = []
            saved = list(getattr(app, "_line_order_wells", []) or [])
            ordered = [w for w in saved if w in selected] + [w for w in selected if w not in saved]
            for w in ordered:
                self._line_order_wells_list.addItem(w)
            self._line_order_wells_list.blockSignals(False)

    def _on_line_order_rsets_changed(self) -> None:
        if self._line_order_rsets_list is None:
            return
        order = [
            self._line_order_rsets_list.item(i).text()
            for i in range(self._line_order_rsets_list.count())
        ]
        self._app._line_order_rsets = order
        if hasattr(self._app, "_line_order_schedule_save"):
            self._app._line_order_schedule_save()
        try:
            self._app._redraw()
        except Exception:
            pass

    def _on_line_order_wells_changed(self) -> None:
        if self._line_order_wells_list is None:
            return
        order = [
            self._line_order_wells_list.item(i).text()
            for i in range(self._line_order_wells_list.count())
        ]
        self._app._line_order_wells = order
        if hasattr(self._app, "_line_order_schedule_save"):
            self._app._line_order_schedule_save()
        try:
            self._app._redraw()
        except Exception:
            pass




# Backwards-compat alias for callers that imported the leading-underscore name.
_ExportStyleSidebar = ExportStyleSidebar

