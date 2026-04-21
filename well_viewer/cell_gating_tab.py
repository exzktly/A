"""Cell Gating tab widget (Qt port)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ui.theme import get_color
from well_viewer.ui_helpers import install_canvas_wheel_scroll

try:
    import numpy as _np
    _NP_AVAILABLE = True
except ImportError:
    _np = None  # type: ignore[assignment]
    _NP_AVAILABLE = False


class CellGatingTab(QWidget):
    """Tab for cell inclusion gating (FluorGating) and per-channel settings."""

    def __init__(self, parent: Optional[QWidget], app, **_kw):
        super().__init__(parent)
        self._app = app
        self._cell_areas: list[float] = []
        self._fluor_gate_edits: dict[str, QLineEdit] = {}
        self._thresh_frac_edits: dict[str, QLineEdit] = {}
        self._fluor_data: dict[str, list[float]] = {}
        self._figure: Optional[Figure] = None
        self._canvas: Optional[FigureCanvas] = None
        self._ax = None
        self._axes_stack: list = []

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        control_frame = QWidget(self)
        control_frame.setObjectName("Sidebar")
        cf_layout = QVBoxLayout(control_frame)
        cf_layout.setContentsMargins(6, 6, 6, 6)

        # Cell area threshold
        area_row = QWidget(control_frame)
        ar = QHBoxLayout(area_row)
        ar.setContentsMargins(0, 0, 0, 0)
        ar.addWidget(QLabel("Cell Area Threshold (pixels):", area_row))
        self._cell_area_edit = QLineEdit("0.0", area_row)
        self._cell_area_edit.setFixedWidth(90)
        self._cell_area_edit.editingFinished.connect(self._on_gating_change)
        ar.addWidget(self._cell_area_edit)
        ar.addStretch(1)
        cf_layout.addWidget(area_row)

        title = QLabel("FluorGating (Cell Inclusion)", control_frame)
        title.setProperty("role", "section")
        cf_layout.addWidget(title)

        self._gating_scroll = QScrollArea(control_frame)
        self._gating_scroll.setWidgetResizable(True)
        self._gating_scroll.setFrameShape(QFrame.NoFrame)
        self._gating_scroll.setFixedHeight(120)
        self._gating_inner = QWidget()
        QVBoxLayout(self._gating_inner)
        self._gating_scroll.setWidget(self._gating_inner)
        cf_layout.addWidget(self._gating_scroll)
        root.addWidget(control_frame)

        # CDF plot area
        self._figure = Figure(figsize=(8, 5), dpi=100)
        self._canvas = FigureCanvas(self._figure)

        self._plot_scroll = QScrollArea(self)
        self._plot_scroll.setWidgetResizable(True)
        self._plot_scroll.setFrameShape(QFrame.NoFrame)
        self._plot_scroll.setWidget(self._canvas)
        install_canvas_wheel_scroll(self._canvas, self._plot_scroll)
        root.addWidget(self._plot_scroll, 1)

        self._toolbar = NavigationToolbar(self._canvas, self)
        root.addWidget(self._toolbar)

        self._status_label = QLabel("No data loaded", self)
        self._status_label.setObjectName("Muted")
        root.addWidget(self._status_label)

    # Back-compat accessors for code that reads ``.get()`` on a StringVar.
    @property
    def _cell_area_threshold(self):
        return _StringHolder(self._cell_area_edit)

    @property
    def _fluor_gates(self):
        return {ch: _StringHolder(edit) for ch, edit in self._fluor_gate_edits.items()}

    @property
    def _thresh_frac_on(self):
        return {ch: _StringHolder(edit) for ch, edit in self._thresh_frac_edits.items()}

    def _build_channel_controls(self) -> None:
        inner_layout = self._gating_inner.layout()
        while inner_layout.count():
            item = inner_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        channels = self._app._fluor_channels
        if not channels:
            lbl = QLabel("No channels loaded", self._gating_inner)
            lbl.setObjectName("Muted")
            inner_layout.addWidget(lbl)
            return

        for channel in channels:
            ch_row = QWidget(self._gating_inner)
            rl = QHBoxLayout(ch_row)
            rl.setContentsMargins(0, 0, 0, 0)

            ch_lbl = QLabel(f"{channel.upper()} Channel:", ch_row)
            ch_lbl.setFixedWidth(140)
            rl.addWidget(ch_lbl)

            rl.addWidget(QLabel("FluorGating:", ch_row))
            if channel not in self._fluor_gate_edits:
                gate_edit = QLineEdit("0.0", ch_row)
                gate_edit.setFixedWidth(90)
                gate_edit.editingFinished.connect(self._on_gating_change)
                self._fluor_gate_edits[channel] = gate_edit
            rl.addWidget(self._fluor_gate_edits[channel])

            rl.addWidget(QLabel("ThreshFracOn:", ch_row))
            if channel not in self._thresh_frac_edits:
                thresh_edit = QLineEdit("50.0", ch_row)
                thresh_edit.setFixedWidth(90)
                thresh_edit.editingFinished.connect(self._on_threshold_frac_on_change)
                self._thresh_frac_edits[channel] = thresh_edit
            rl.addWidget(self._thresh_frac_edits[channel])
            rl.addStretch(1)

            inner_layout.addWidget(ch_row)
        inner_layout.addStretch(1)

    def _load_cell_areas(self) -> None:
        self._cell_areas = []
        self._fluor_data = {}
        labels = self._cdf_source_wells()

        for label in labels:
            rows = self._app._get_rows(label)
            frame_rows, _ = self._first_frame_rows(rows)
            for row in frame_rows:
                try:
                    area = float(row.get("area_px", 0))
                    if area > 0:
                        self._cell_areas.append(area)
                except (ValueError, TypeError):
                    pass

                for channel in self._app._fluor_channels:
                    val_col = f"{channel}_mean_intensity"
                    try:
                        val = float(row.get(val_col, 0))
                        if val > 0:
                            self._fluor_data.setdefault(channel, []).append(val)
                    except (ValueError, TypeError):
                        pass

        self._build_channel_controls()

        if self._cell_areas:
            self._axes_stack = []
            self._plot_cdf()
            self._status_label.setText(
                f"Loaded {len(self._cell_areas)} cells from {len(labels)} selected well(s), first frame of first FOV"
            )
        else:
            self._status_label.setText("No cell data found")

    def _first_frame_rows(self, rows: list[dict]) -> tuple[list[dict], str]:
        if not rows:
            return [], ""

        def _fov_sort_key(row: dict):
            raw = str(row.get("fov", "1")).strip() or "1"
            try:
                return (0, float(raw))
            except ValueError:
                return (1, raw.lower())

        def _tp_sort_key(row: dict):
            raw_h = row.get("timepoint_hours")
            if raw_h not in (None, ""):
                try:
                    return (0, float(raw_h))
                except (ValueError, TypeError):
                    pass
            raw_tp = str(row.get("timepoint", "")).strip()
            if raw_tp:
                try:
                    return (1, float(raw_tp))
                except ValueError:
                    return (2, raw_tp.lower())
            return (3, 0.0)

        first_fov = min(rows, key=_fov_sort_key).get("fov", "1")
        same_fov_rows = [r for r in rows if str(r.get("fov", "1")) == str(first_fov)]
        if not same_fov_rows:
            return [], ""

        first_tp_row = min(same_fov_rows, key=_tp_sort_key)
        first_tp_h = first_tp_row.get("timepoint_hours")
        first_tp = first_tp_row.get("timepoint")

        def _tp_matches(row: dict) -> bool:
            if first_tp_h not in (None, "") and row.get("timepoint_hours") == first_tp_h:
                return True
            return str(row.get("timepoint", "")) == str(first_tp)

        frame_rows = [r for r in same_fov_rows if _tp_matches(r)]
        frame_desc = f"fov={first_fov}, tp={first_tp if first_tp not in (None, '') else first_tp_h}"
        return frame_rows, frame_desc

    def _cdf_source_wells(self) -> list[str]:
        active_rsets = []
        if hasattr(self._app, "_rep_sets_active"):
            active_rsets = self._app._rep_sets_active()

        if active_rsets:
            seen: set[str] = set()
            ordered: list[str] = []
            for rset in active_rsets:
                for well in rset.wells:
                    if well in self._app._well_paths and well not in seen:
                        seen.add(well)
                        ordered.append(well)
            return sorted(ordered, key=self._app._parse_rc)

        return sorted(
            (label for label in self._app._selected_wells if label in self._app._well_paths),
            key=self._app._parse_rc,
        )

    def _plot_cdf(self) -> None:
        if not self._cell_areas and not self._fluor_data:
            return

        bg_app = get_color("BG_APP")
        bg_panel = get_color("BG_PANEL")
        txt_pri = get_color("TXT_PRI")
        txt_mut = get_color("TXT_MUT")
        accent = get_color("ACCENT")
        warn = get_color("WARN")

        self._figure.clf()
        self._figure.set_facecolor(bg_app)

        n_plots = 1 + len(self._fluor_data)
        n_cols = 1 if n_plots == 1 else 2
        n_rows = (n_plots + n_cols - 1) // n_cols
        plot_height_per_row = 3.8
        fig_height = max(5.0, n_rows * plot_height_per_row)
        self._figure.set_size_inches(8.0, fig_height, forward=True)

        axes = []
        for i in range(n_plots):
            ax = self._figure.add_subplot(n_rows, n_cols, i + 1, facecolor=bg_panel)
            axes.append(ax)

        if self._cell_areas:
            areas = _np.array(sorted(self._cell_areas))
            cdf = _np.arange(1, len(areas) + 1) / len(areas)
            axes[0].plot(areas, cdf, linewidth=2, color=accent, alpha=0.8)
            axes[0].fill_between(areas, cdf, alpha=0.2, color=accent)
            axes[0].set_xlabel("Cell Area (pixels)", color=txt_pri, fontsize=9)
            axes[0].set_ylabel("Cumulative Probability", color=txt_pri, fontsize=9)
            axes[0].set_title("Cell Area Distribution", color=txt_pri, fontsize=10, fontweight="bold")
            axes[0].grid(True, alpha=0.2, color=txt_mut)
            axes[0].tick_params(colors=txt_mut, labelsize=8)

            try:
                cell_area_threshold = float(self._cell_area_edit.text())
                axes[0].axvline(x=cell_area_threshold, color=warn, linestyle="--", linewidth=2, alpha=0.7)
            except ValueError:
                pass

        colors = [accent, "#FF9500", "#FF3B30", "#34C759"]
        for idx, (channel, values) in enumerate(sorted(self._fluor_data.items()), 1):
            if idx < len(axes):
                ax = axes[idx]
                color = colors[idx % len(colors)]
                vals = _np.array(sorted(values))
                cdf = _np.arange(1, len(vals) + 1) / len(vals)
                ax.plot(vals, cdf, linewidth=2, color=color, alpha=0.8)
                ax.fill_between(vals, cdf, alpha=0.2, color=color)
                ax.set_xlabel(f"{channel.upper()} Intensity", color=txt_pri, fontsize=9)
                ax.set_ylabel("Cumulative Probability", color=txt_pri, fontsize=9)
                ax.set_title(f"{channel.upper()} Distribution", color=txt_pri, fontsize=10, fontweight="bold")
                ax.grid(True, alpha=0.2, color=txt_mut)
                ax.tick_params(colors=txt_mut, labelsize=8)

                try:
                    fluor_gate = float(self._fluor_gate_edits[channel].text())
                    ax.axvline(x=fluor_gate, color=warn, linestyle="--", linewidth=2, alpha=0.7)
                except (ValueError, KeyError):
                    pass

        self._ax = axes[0]

        if not self._axes_stack:
            limits = [(ax.get_xlim(), ax.get_ylim()) for ax in axes]
            self._axes_stack.append(limits)

        self._figure.tight_layout(pad=1.3)
        self._canvas.draw_idle()

        dpi = self._figure.get_dpi()
        fig_h_px = max(1, int(self._figure.get_figheight() * dpi))
        self._canvas.setMinimumHeight(fig_h_px)

    def _on_gating_change(self) -> None:
        try:
            float(self._cell_area_edit.text())
            for edit in self._fluor_gate_edits.values():
                float(edit.text())
            self._axes_stack = []
            self._plot_cdf()
            self._app._apply_cell_gating_to_included()
            self._app._redraw()
        except ValueError:
            pass

    def _on_threshold_frac_on_change(self) -> None:
        try:
            for edit in self._thresh_frac_edits.values():
                float(edit.text())
            self._save_threshold_frac_on()
            self._app._redraw()
        except ValueError:
            pass

    def _save_threshold_frac_on(self) -> None:
        if not hasattr(self._app, '_thresh_frac_on_saved'):
            self._app._thresh_frac_on_saved = {}
        for channel, edit in self._thresh_frac_edits.items():
            try:
                self._app._thresh_frac_on_saved[channel] = float(edit.text())
            except ValueError:
                pass

    def _load_threshold_frac_on(self) -> None:
        if hasattr(self._app, '_thresh_frac_on_saved'):
            for channel, value in self._app._thresh_frac_on_saved.items():
                if channel in self._thresh_frac_edits:
                    self._thresh_frac_edits[channel].setText(str(value))

    def get_fluor_gate(self, channel: str) -> float:
        edit = self._fluor_gate_edits.get(channel)
        if edit is None:
            return 0.0
        try:
            return float(edit.text())
        except ValueError:
            return 0.0

    def get_thresh_frac_on(self, channel: str) -> float:
        edit = self._thresh_frac_edits.get(channel)
        if edit is None:
            return 50.0
        try:
            return float(edit.text())
        except ValueError:
            return 50.0

    def update_theme_colors_rebuild(self, _old_theme: str = "", _new_theme: str = "") -> None:
        if self._figure is not None:
            self._figure.set_facecolor(get_color("BG_APP"))
        if self._cell_areas or self._fluor_data:
            self._plot_cdf()


class _StringHolder:
    """``get()``/``set()`` shim that reads/writes a ``QLineEdit``'s text."""
    __slots__ = ("_edit",)

    def __init__(self, edit: QLineEdit) -> None:
        self._edit = edit

    def get(self) -> str:
        return self._edit.text()

    def set(self, value) -> None:
        self._edit.setText(str(value))
