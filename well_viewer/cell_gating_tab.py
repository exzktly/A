"""Cell Gating tab widget (Qt port)."""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np
import pandas as pd

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from ui.theme import get_color
from well_viewer import debug_flags as _debug_flags
from well_viewer.ui_helpers import attach_plot_toolbar, install_canvas_wheel_scroll

try:
    import numpy as _np
    _NP_AVAILABLE = True
except ImportError:
    _np = None  # type: ignore[assignment]
    _NP_AVAILABLE = False


logger = logging.getLogger("well_viewer.gating_worker")


class GatingWorker(QThread):
    """Apply cell-gating thresholds to every cached well row off the GUI thread.

    Emits ``progress`` after each well is processed so the status bar advances
    incrementally (1/N → 2/N → …). On clean completion, invalidates the stats
    cache and emits ``finished_ok``.

    The cancellation flag is checked between wells; setting it via
    ``cancel()`` aborts cleanly without touching the stats cache.
    """

    progress = Signal(int, int)  # (current, total)
    finished_ok = Signal()

    def __init__(self, app, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self._app = app
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        debug = _debug_flags.cell_gating_debug_enabled()
        cell_area_threshold = self._app._get_cell_area_threshold()
        fluor_gates = self._app._get_all_fluor_gates()
        labels = list(self._app._well_paths)
        total = len(labels)

        if debug:
            logger.info(
                "GatingWorker start: wells=%d cell_area_threshold=%.4f fluor_gates=%s",
                total, cell_area_threshold, fluor_gates,
            )

        included_total = 0
        excluded_total = 0

        for idx, label in enumerate(labels):
            if self._cancelled:
                if debug:
                    logger.info(
                        "GatingWorker cancelled at well %d/%d (%s)",
                        idx, total, label,
                    )
                return

            df = self._app._get_rows(label)
            row_count = 0 if df is None else len(df)
            if df is None or df.empty:
                well_included = 0
            else:
                mask = pd.Series(True, index=df.index)
                if "area_px" in df.columns:
                    area = pd.to_numeric(df["area_px"], errors="coerce")
                    mask &= area.notna() & (area > cell_area_threshold)
                else:
                    mask &= cell_area_threshold < 0
                for channel, gate_threshold in fluor_gates.items():
                    col = f"{channel}_mean_intensity"
                    if col not in df.columns:
                        mask = pd.Series(False, index=df.index)
                        break
                    v = pd.to_numeric(df[col], errors="coerce")
                    mask &= v.notna() & (v > gate_threshold)
                df["Included"] = mask.astype(int)
                well_included = int(mask.sum())

            included_total += well_included
            excluded_total += row_count - well_included

            if debug:
                logger.info(
                    "GatingWorker progress %d/%d well=%s rows=%d included=%d",
                    idx + 1, total, label, row_count, well_included,
                )

            self.progress.emit(idx + 1, total)
            # Yield to the GUI thread so the progress bar can repaint and the
            # cancel button stays responsive between wells.
            time.sleep(0.01)

        if not self._cancelled:
            # Re-apply user overrides on top of the gating-computed Included
            # so per-cell curation in the Segmentation tab is not clobbered by
            # threshold-based recomputes.
            try:
                self._app._apply_review_overrides_to_cache()
            except Exception:
                pass
            # CRITICAL: Only invalidate stats cache, NOT _refresh_review_csv_rows.
            # That call deep-copies every cached row across every well and
            # blows up memory by orders of magnitude.
            self._app._invalidate_stats_cache()
            if debug:
                logger.info(
                    "GatingWorker finished: wells=%d included=%d excluded=%d",
                    total, included_total, excluded_total,
                )
            self.finished_ok.emit()


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
        self._gating_worker: Optional[GatingWorker] = None

        self._build_ui()

    def _build_ui(self) -> None:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        control_frame = QWidget(self)
        control_frame.setObjectName("TabCtrl")
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

        self._toolbar = attach_plot_toolbar(
            root, self._canvas, self, with_sem=False,
        )

        self._status_label = QLabel("No data loaded", self)
        self._status_label.setObjectName("Muted")
        root.addWidget(self._status_label)

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
        import numpy as np
        self._cell_areas = []
        self._fluor_data = {}
        labels = self._cdf_source_wells()

        for label in labels:
            df = self._app._get_rows(label)
            if df is None or df.empty:
                continue
            frame_df, _ = self._first_frame_rows(df)
            if frame_df is None or frame_df.empty:
                continue
            if "area_px" in frame_df.columns:
                area = pd.to_numeric(frame_df["area_px"], errors="coerce").to_numpy()
                self._cell_areas.extend(float(a) for a in area[np.isfinite(area) & (area > 0)])
            for channel in self._app._fluor_channels:
                val_col = f"{channel}_mean_intensity"
                if val_col not in frame_df.columns:
                    continue
                v = pd.to_numeric(frame_df[val_col], errors="coerce").to_numpy()
                positive = v[np.isfinite(v) & (v > 0)]
                if positive.size:
                    self._fluor_data.setdefault(channel, []).extend(float(x) for x in positive)

        self._build_channel_controls()

        if self._cell_areas:
            self._axes_stack = []
            self._plot_cdf()
            self._status_label.setText(
                f"Loaded {len(self._cell_areas)} cells from {len(labels)} selected well(s), first frame of first FOV"
            )
        else:
            self._status_label.setText("No cell data found")

    def _first_frame_rows(self, df) -> tuple:
        """Return (sub_df, description) for the first FOV's first timepoint."""
        if df is None or df.empty:
            return df, ""

        fov_series = (df["fov"].fillna("1").astype(str).str.strip().replace("", "1")
                      if "fov" in df.columns
                      else pd.Series(["1"] * len(df), index=df.index))
        fov_num = pd.to_numeric(fov_series, errors="coerce")

        def _fov_token(token: str) -> tuple:
            try:
                return (0, float(token))
            except ValueError:
                return (1, token.lower())

        unique_fovs = sorted(fov_series.unique(), key=_fov_token)
        first_fov = unique_fovs[0] if unique_fovs else "1"
        same_fov = df.loc[fov_series == first_fov]
        if same_fov.empty:
            return same_fov, ""

        tp_h = (pd.to_numeric(same_fov.get("timepoint_hours"), errors="coerce")
                if "timepoint_hours" in same_fov.columns
                else pd.Series(np.nan, index=same_fov.index, dtype=float))
        tp_str = (same_fov.get("timepoint", pd.Series([""] * len(same_fov), index=same_fov.index))
                  .fillna("").astype(str).str.strip())
        tp_str_num = pd.to_numeric(tp_str, errors="coerce")

        if tp_h.notna().any():
            min_h = float(tp_h.min())
            mask = (tp_h == min_h) | tp_h.isna()
            mask = (tp_h == min_h)
            frame_desc_tp = f"{min_h:g}"
        elif tp_str_num.notna().any():
            min_n = float(tp_str_num.min())
            mask = tp_str_num == min_n
            frame_desc_tp = f"{min_n:g}"
        else:
            non_empty = tp_str[tp_str != ""]
            if non_empty.empty:
                mask = pd.Series(True, index=same_fov.index)
                frame_desc_tp = ""
            else:
                first = sorted(non_empty.unique(), key=str.lower)[0]
                mask = tp_str == first
                frame_desc_tp = first

        frame_df = same_fov.loc[mask]
        frame_desc = f"fov={first_fov}, tp={frame_desc_tp}"
        return frame_df, frame_desc

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

        selected = [
            label for label in self._app._selected_wells
            if label in self._app._well_paths
        ]
        # Fall back to every loaded well so the CDFs render on the first open
        # after a data load (before the user has made an explicit selection).
        # Once they pick wells in the sidebar, that selection scopes the plot.
        if not selected:
            selected = list(self._app._well_paths)
        return sorted(selected, key=self._app._parse_rc)

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

        # Constrain height only; width is driven by the scroll area's
        # setWidgetResizable(True) so the canvas fills the viewport.
        dpi = self._figure.get_dpi()
        fig_h_px = max(1, int(fig_height * dpi))
        self._canvas.setMinimumHeight(fig_h_px)

    def _on_gating_change(self) -> None:
        try:
            float(self._cell_area_edit.text())
            for edit in self._fluor_gate_edits.values():
                float(edit.text())
        except ValueError:
            return

        self._axes_stack = []
        self._plot_cdf()
        self._persist_gating_params()
        self._start_gating_worker()

    def _start_gating_worker(self) -> None:
        # If a previous worker is still running, cancel it before starting
        # a new pass so threshold edits don't pile up.
        prev = self._gating_worker
        if prev is not None and prev.isRunning():
            prev.cancel()
            prev.wait()

        worker = GatingWorker(self._app)
        worker.progress.connect(self._on_gating_progress)
        worker.finished_ok.connect(self._on_gating_finished)
        self._gating_worker = worker
        bar = getattr(self._app, "_progress_bar", None)
        if bar is not None:
            bar.setRange(0, max(1, len(self._app._well_paths)))
            bar.setValue(0)
            bar.show()
        worker.start()

    def _on_gating_progress(self, current: int, total: int) -> None:
        bar = getattr(self._app, "_progress_bar", None)
        if bar is None:
            return
        if bar.maximum() != total:
            bar.setRange(0, total)
        bar.setValue(current)

    def _on_gating_finished(self) -> None:
        bar = getattr(self._app, "_progress_bar", None)
        if bar is not None:
            bar.setValue(0)
            bar.hide()
        self._app._redraw()

    def _on_threshold_frac_on_change(self) -> None:
        try:
            for edit in self._thresh_frac_edits.values():
                float(edit.text())
            self._save_threshold_frac_on()
            self._persist_gating_params()
            self._app._redraw()
        except ValueError:
            pass

    def _persist_gating_params(self) -> None:
        """Save current gating values into pipeline_info.json (no-op when at defaults)."""
        save = getattr(self._app, "_save_gating_to_pipeline_info", None)
        if save is None:
            return
        try:
            save()
        except Exception:
            logger.exception("Failed to save gating params to pipeline_info.json")

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


