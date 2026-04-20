"""Qt runtime app for the Review tab."""

from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from well_viewer.load_controller import load_path as _load_path_controller
from well_viewer.export_service import (
    export_bar_plot_data as _export_bar_plot_data_service,
    export_plot_data as _export_plot_data_service,
    export_scatter_agg_data as _export_scatter_agg_data_service,
    export_scatter_data as _export_scatter_data_service,
)
from well_viewer.figure_export_editor import launch_export_editor
from well_viewer.review_image_controller import (
    on_review_csv_row_double_click as _on_review_csv_row_double_click_controller,
)
from well_viewer.tabs.bar_plots_tab_view import build_bar_plots_tab
from well_viewer.tabs.batch_export_tab_view import build_batch_export_tab
from well_viewer.tabs.line_graphs_tab_view import build_line_graphs_tab
from well_viewer.tabs.review_csv_tab_view import build_review_csv_tab
from well_viewer.tabs.scatter_agg_tab_view import build_scatter_agg_tab
from well_viewer.tabs.scatter_cells_tab_view import build_scatter_cells_tab


class _Var:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class WellViewerApp(QWidget):
    """Feature-oriented Qt runtime shell used by `all_well.py`."""

    def __init__(self, parent: Optional[QWidget] = None, data_path: Optional[Path] = None) -> None:
        super().__init__(parent)
        self._data_dir: Optional[Path] = None
        self._tmp_dir: Optional[Path] = None
        self._well_paths: dict[str, Path] = {}
        self._cache: dict[str, list[dict]] = {}
        self._selected_wells: set[str] = set()
        self._status_text = ""
        self._active_channel = "gfp"
        self._active_metric = "mean_intensity"
        self._active_val_col = "gfp_mean_intensity"
        self._fluor_channels = ["gfp"]

        # compatibility holders used across tab builders/controllers
        self._plot_chan_var = _Var("GFP")
        self._bar_tp_var = _Var("—")
        self._bar_swarm = _Var(False)
        self._bar_violin = _Var(False)
        self._bar_log_scale = _Var(False)
        self._violin_bw = _Var(0.4)
        self._bar_ylim_mean_lo = _Var("")
        self._bar_ylim_mean_hi = _Var("")
        self._bar_ylim_frac_lo = _Var("")
        self._bar_ylim_frac_hi = _Var("")
        self._cdf_xmin_var = _Var("0")
        self._cdf_xmax_var = _Var("300")
        self._scatter_agg_tp_selections = {}
        self._batch_export_inline_state = "idle"
        self._review_csv_lookup_context: dict[str, str] = {}

        self._build_ui()

        if data_path is not None:
            QTimer.singleShot(0, lambda: self._load_path(data_path))

    @staticmethod
    def _read_value(obj, default=None):
        """Read value from tk-style holders or Qt widgets safely."""
        if obj is None:
            return default
        if hasattr(obj, "get") and callable(getattr(obj, "get")):
            return obj.get()
        if hasattr(obj, "currentText") and callable(getattr(obj, "currentText")):
            return obj.currentText()
        if hasattr(obj, "text") and callable(getattr(obj, "text")):
            return obj.text()
        if hasattr(obj, "isChecked") and callable(getattr(obj, "isChecked")):
            return obj.isChecked()
        if hasattr(obj, "value") and callable(getattr(obj, "value")):
            return obj.value()
        return default

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QWidget(self)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(10, 8, 10, 8)
        self._dir_label = QLabel("No data loaded", top)
        tl.addWidget(self._dir_label, 1)
        open_btn = QPushButton("Open…", top)
        open_btn.clicked.connect(self._browse)
        tl.addWidget(open_btn)
        root.addWidget(top)

        self._split = QSplitter(Qt.Horizontal, self)
        root.addWidget(self._split, 1)

        self._sidebar = QWidget(self._split)
        sl = QVBoxLayout(self._sidebar)
        sl.setContentsMargins(8, 8, 8, 8)
        self._sidebar_title = QLabel("Wells", self._sidebar)
        self._sidebar_count = QLabel("0 selected", self._sidebar)
        sl.addWidget(self._sidebar_title)
        sl.addWidget(self._sidebar_count)
        sl.addStretch(1)

        centre = QWidget(self._split)
        cl = QVBoxLayout(centre)
        cl.setContentsMargins(0, 0, 0, 0)
        self._nb = QTabWidget(centre)
        self._notebook = self._nb  # back-compat name used by controller helpers
        cl.addWidget(self._nb, 1)

        self._tab_line = QWidget(self._nb)
        self._tab_bar = QWidget(self._nb)
        self._tab_scatter = QWidget(self._nb)
        self._tab_scatter_agg = QWidget(self._nb)
        self._tab_review = QWidget(self._nb)
        self._tab_batch = QWidget(self._nb)

        self._nb.addTab(self._tab_line, "Line Graphs")
        self._nb.addTab(self._tab_bar, "Bar Plots")
        self._nb.addTab(self._tab_scatter, "Scatter Cells")
        self._nb.addTab(self._tab_scatter_agg, "Scatter Aggregate")
        self._nb.addTab(self._tab_review, "Review CSV")
        self._nb.addTab(self._tab_batch, "Batch Export")

        build_line_graphs_tab(self, self._tab_line)
        build_bar_plots_tab(self, self._tab_bar)
        build_scatter_cells_tab(self, self._tab_scatter)
        build_scatter_agg_tab(self, self._tab_scatter_agg)
        build_review_csv_tab(self, self._tab_review)
        build_batch_export_tab(self, self._tab_batch)

        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)

    # ---- app actions ----
    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open results directory")
        if path:
            self._load_path(Path(path))

    def _load_path(self, path: Path) -> None:
        self._data_dir = path
        self._dir_label.setText(str(path))
        try:
            _load_path_controller(self, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Load warning", str(exc))

        # Fallback discovery for environments where controller wiring is partial.
        if not self._well_paths and path.exists():
            for p in sorted(path.glob("*.csv")):
                self._well_paths[p.stem] = p
        if not self._selected_wells and self._well_paths:
            self._selected_wells = set(sorted(self._well_paths))

        self._refresh_review_csv_rows()

    def _cleanup_tmp(self) -> None:
        self._tmp_dir = None

    # ---- callbacks expected by tab builders/controllers ----
    def _on_plot_channel_selected(self, _evt=None) -> None:
        txt = (self._chan_cb_line.currentText() if hasattr(self, "_chan_cb_line") else "GFP").strip()
        self._active_channel = txt.lower() or "gfp"
        if hasattr(self, "_cdf_chan_lbl"):
            self._cdf_chan_lbl.setText(f"({self._active_channel.upper()} x range)")
        self._redraw()
        self._redraw_bars()

    def _on_metric_selected(self) -> None:
        self._redraw()
        self._redraw_bars()
        self._redraw_scatter()
        self._redraw_scatter_agg()

    def _redraw(self) -> None:
        if hasattr(self, "_line_canvas"):
            self._line_canvas.draw_idle()

    def _redraw_bars(self) -> None:
        if hasattr(self, "_bar_canvas"):
            self._bar_canvas.draw_idle()

    def _redraw_scatter(self) -> None:
        if hasattr(self, "_scatter_canvas"):
            self._scatter_canvas.draw_idle()

    def _redraw_scatter_agg(self) -> None:
        if hasattr(self, "_scatter_agg_canvas"):
            self._scatter_agg_canvas.draw_idle()

    def _on_fig_click(self, _event) -> None:
        return

    def _on_cdf_motion(self, _event) -> None:
        return

    def _on_cdf_release(self, _event) -> None:
        return

    def _on_scatter_click(self, _event) -> None:
        return

    def _on_scatter_motion(self, _event) -> None:
        return

    def _on_bar_drag_press(self, _event) -> None:
        return

    def _on_bar_drag_motion(self, _event) -> None:
        return

    def _on_bar_drag_release(self, _event) -> None:
        return

    def _open_export_style_panel(self, _kind: str) -> None:
        try:
            kind = (_kind or "").strip().lower()
            if kind == "bar" and hasattr(self, "_bar_fig"):
                launch_export_editor(self, self._bar_fig, "bar_plot.png", plot_bg="#ffffff", canvas=getattr(self, "_bar_canvas", None))
            elif kind in ("scatter", "scatter_cells") and hasattr(self, "_scatter_fig"):
                launch_export_editor(self, self._scatter_fig, "scatter_plot.png", plot_bg="#ffffff", canvas=getattr(self, "_scatter_canvas", None))
            elif kind in ("scatter_agg", "aggregate") and hasattr(self, "_scatter_agg_fig"):
                launch_export_editor(self, self._scatter_agg_fig, "scatter_agg_plot.png", plot_bg="#ffffff", canvas=getattr(self, "_scatter_agg_canvas", None))
            elif hasattr(self, "_line_fig"):
                launch_export_editor(self, self._line_fig, "line_plot.png", plot_bg="#ffffff", canvas=getattr(self, "_line_canvas", None))
            self._set_status(f"Opened export style panel ({kind or 'line'}).")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export Style", str(exc))

    def _export_plot_data(self) -> None:
        try:
            _export_plot_data_service(self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", str(exc))

    def _export_bar_plot_data(self) -> None:
        try:
            _export_bar_plot_data_service(self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", str(exc))

    def _export_scatter_data(self) -> None:
        try:
            _export_scatter_data_service(self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", str(exc))

    def _export_scatter_agg_data(self) -> None:
        try:
            _export_scatter_agg_data_service(self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", str(exc))

    def _toggle_swarm(self) -> None:
        self._bar_swarm.set(not bool(self._read_value(self._bar_swarm, False)))
        self._redraw_bars()

    def _toggle_violin(self) -> None:
        self._bar_violin.set(not bool(self._read_value(self._bar_violin, False)))
        self._redraw_bars()

    def _toggle_log_scale(self) -> None:
        self._bar_log_scale.set(not bool(self._read_value(self._bar_log_scale, False)))
        self._redraw_bars()

    def _bar_reset_order(self) -> None:
        self._redraw_bars()

    def _refresh_review_csv(self) -> None:
        self._refresh_review_csv_rows()

    def _refresh_review_csv_rows(self) -> None:
        if not hasattr(self, "_review_csv_table"):
            return
        table = self._review_csv_table
        table.setRowCount(0)
        table.setColumnCount(0)

        rows: list[dict] = []
        for label in self._selected_labels():
            rows.extend(self._get_rows(label))

        if not rows:
            if hasattr(self, "_review_csv_msg_lbl"):
                self._review_csv_msg_lbl.setText("No rows are available for the selected well(s).")
            return

        fov_filter = self._review_fov_cb.currentText().strip() if hasattr(self, "_review_fov_cb") else ""
        tp_filter = self._review_tp_cb.currentText().strip() if hasattr(self, "_review_tp_cb") else ""
        filtered: list[dict] = []
        for row in rows:
            row_fov = str(row.get("fov", row.get("FOV", ""))).strip()
            row_tp = str(row.get("timepoint", row.get("tp", row.get("time", "")))).strip()
            if fov_filter and row_fov and row_fov != fov_filter:
                continue
            if tp_filter and row_tp and row_tp != tp_filter:
                continue
            filtered.append(row)

        if not filtered:
            filtered = rows

        cols = list(filtered[0].keys())
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(filtered))
        from PySide6.QtWidgets import QTableWidgetItem
        for r_idx, row in enumerate(filtered):
            for c_idx, col in enumerate(cols):
                table.setItem(r_idx, c_idx, QTableWidgetItem(str(row.get(col, ""))))
        if hasattr(self, "_review_csv_msg_lbl"):
            self._review_csv_msg_lbl.setText(f"Showing {len(filtered):,} row(s).")

    def _on_review_csv_row_double_click(self, _event) -> None:
        try:
            _on_review_csv_row_double_click_controller(self, _event)
        except Exception:
            return

    def _update_tp_selection_display(self) -> None:
        if hasattr(self, "_scatter_agg_tp_label"):
            selected = [
                k
                for k, holder in self._scatter_agg_tp_selections.items()
                if bool(self._read_value(holder, False))
            ]
            self._scatter_agg_tp_label.setText(", ".join(selected[:4]) + ("…" if len(selected) > 4 else "") if selected else "All")

    def _batch_export_set_mode(self, mode: str) -> None:
        self._batch_export_inline_state = mode

    def _open_batch_export(self) -> None:
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Batch Export.")
            return
        self._nb.setCurrentWidget(self._tab_batch)
        self._batch_export_set_mode("line")

    def _open_bar_batch_export(self) -> None:
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Bar Batch Export.")
            return
        self._nb.setCurrentWidget(self._tab_batch)
        self._batch_export_set_mode("bar")

    def _open_scatter_cells_batch_export(self) -> None:
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Scatter Cells Batch Export.")
            return
        self._nb.setCurrentWidget(self._tab_batch)
        self._batch_export_set_mode("scatter_cells")

    def _open_scatter_agg_batch_export(self) -> None:
        if not self._well_paths:
            QMessageBox.warning(self, "No data", "Load data before opening Scatter Aggregate Batch Export.")
            return
        self._nb.setCurrentWidget(self._tab_batch)
        self._batch_export_set_mode("scatter_agg")

    def _on_theme_change(self, _theme_name: str) -> None:
        self.update()

    # ---- compatibility helpers consumed by services/controllers ----
    def _set_status(self, msg: str) -> None:
        self._status_text = msg
        if hasattr(self, "_sidebar_count"):
            self._sidebar_count.setText(msg)

    def _selected_labels(self) -> list[str]:
        return sorted(self._selected_wells, key=self._parse_rc)

    def _get_rows(self, label: str) -> list[dict]:
        if label in self._cache:
            return list(self._cache[label])
        src = self._well_paths.get(label)
        if src is None:
            return []
        try:
            with src.open("r", newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            rows = []
        self._cache[label] = rows
        return list(rows)

    def _get_thresh_frac_on(self, _channel: Optional[str] = None) -> float:
        return 50.0

    def _get_cell_area_threshold(self) -> float:
        return 0.0

    def _get_fluor_gate(self, _channel: str) -> float:
        return 0.0

    def _get_all_fluor_gates(self) -> dict[str, float]:
        return {ch: 0.0 for ch in self._fluor_channels}

    def _row_is_included(self, _row: dict) -> bool:
        return True

    @staticmethod
    def _parse_rc(token: str) -> tuple[int, int]:
        s = str(token).strip()
        if not s:
            return (99, 99)
        row_c = s[0].upper()
        col_s = s[1:] if len(s) > 1 else "99"
        row_i = ord(row_c) - ord("A") if "A" <= row_c <= "Z" else 99
        try:
            col_i = int(col_s)
        except ValueError:
            col_i = 99
        return (row_i, col_i)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    w = WellViewerApp()
    w.resize(1600, 960)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
