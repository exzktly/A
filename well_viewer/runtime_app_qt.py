"""Phase 4 Slice B/C/D: Qt runtime shell, plot tabs, and specialized dialogs."""

from __future__ import annotations

import csv
from pathlib import Path

from ui.qt_plot_host import draw_message, make_plot_host
from ui.qt_ui import make_labeled_field, make_section, modal_note, pick_directory, warn as show_warn
from well_viewer.qt_tools import BatchExportDialogQt, ExportStyleSettings, FigureExportEditorDialog


class WellViewerRuntimeQt:
    def __init__(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QHBoxLayout,
            QLabel,
            QListWidget,
            QPushButton,
            QSplitter,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

        self.widget = QWidget()
        self._data_dir: Path | None = None
        self._export_style = ExportStyleSettings()
        self._batch_export_options: dict | None = None

        root = QVBoxLayout(self.widget)

        toolbar = QHBoxLayout()
        self._open_btn = QPushButton("Open Results…")
        self._open_btn.clicked.connect(self._open_results)
        self._status = QLabel("No data loaded")
        toolbar.addWidget(self._open_btn)
        toolbar.addWidget(self._status, stretch=1)
        root.addLayout(toolbar)
        self._path_label = QLabel("—")
        root.addWidget(make_labeled_field("Loaded path:", self._path_label))

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, stretch=1)

        # Slice B: runtime shell + sidebars
        left = make_section("Wells")
        self._well_list = QListWidget()
        left.layout().addWidget(self._well_list)
        split.addWidget(left)

        center = make_section("Plots")
        self._plot_tabs = QTabWidget()
        self._line_host = make_plot_host(title="Line")
        self._bar_host = make_plot_host(title="Bar")
        self._scatter_host = make_plot_host(title="Scatter")
        self._cdf_host = make_plot_host(title="CDF")
        self._plot_tabs.addTab(self._line_host["widget"], "Line")
        self._plot_tabs.addTab(self._bar_host["widget"], "Bar")
        self._plot_tabs.addTab(self._scatter_host["widget"], "Scatter")
        self._plot_tabs.addTab(self._cdf_host["widget"], "CDF")
        center.layout().addWidget(self._plot_tabs)
        split.addWidget(center)

        right = make_section("Tools")
        right.layout().addWidget(QLabel("Specialized editors/dialogs"))

        self._btn_export_editor = QPushButton("Figure Export Editor")
        self._btn_export_editor.clicked.connect(self._open_export_editor)
        right.layout().addWidget(self._btn_export_editor)

        self._btn_batch_export = QPushButton("Batch Export")
        self._btn_batch_export.clicked.connect(self._open_batch_export)
        right.layout().addWidget(self._btn_batch_export)

        self._btn_smfish = QPushButton("smFISH")
        self._btn_smfish.clicked.connect(lambda: self._open_tool("smFISH"))
        right.layout().addWidget(self._btn_smfish)

        self._btn_cell_gating = QPushButton("Cell Gating")
        self._btn_cell_gating.clicked.connect(lambda: self._open_tool("Cell Gating"))
        right.layout().addWidget(self._btn_cell_gating)

        self._info = QTextEdit()
        self._info.setReadOnly(True)
        self._info.setPlainText("Load a results directory to populate wells and enable plot updates.")
        right.layout().addWidget(self._info, stretch=1)
        split.addWidget(right)

        split.setSizes([220, 620, 320])

    def _open_tool(self, title: str) -> None:
        modal_note(self.widget, title, f"{title} Qt migration stub is active for Phase 4.")

    def _open_export_editor(self) -> None:
        dlg = FigureExportEditorDialog(self.widget, settings=self._export_style)
        result = dlg.exec()
        if result is None:
            return
        self._export_style = result
        self._info.append(f"Updated export style: dpi={result.dpi}, title={result.title_size}")

    def _open_batch_export(self) -> None:
        dlg = BatchExportDialogQt(self.widget)
        result = dlg.exec()
        if result is None:
            return
        self._batch_export_options = result
        self._info.append(f"Updated batch export options: {result}")

    def _open_results(self) -> None:
        selected = pick_directory(self.widget, title="Open results directory")
        if selected is None:
            return
        self._load_path(selected)

    def _load_path(self, path: Path) -> None:
        if not path.exists() or not path.is_dir():
            show_warn(self.widget, "Load failed", "Selected path is not a directory.")
            return
        self._data_dir = path
        self._path_label.setText(str(path))
        wells = self._discover_wells(path)
        self._well_list.clear()
        self._well_list.addItems(wells)
        self._status.setText(f"Loaded {len(wells)} wells from {path.name}")
        self._redraw_plots(wells)

    def _redraw_plots(self, wells: list[str]) -> None:
        line_ax = self._line_host["axis"]
        line_ax.clear()
        line_ax.plot(list(range(len(wells))), list(range(len(wells))), marker="o")
        line_ax.set_title("Loaded wells (index)")
        line_ax.set_xlabel("Well index")
        line_ax.set_ylabel("Ordinal value")
        self._line_host["canvas"].draw_idle()

        row_counts: dict[str, int] = {}
        for well in wells:
            key = well[:1].upper() if well else "?"
            row_counts[key] = row_counts.get(key, 0) + 1
        bar_ax = self._bar_host["axis"]
        bar_ax.clear()
        labels = sorted(row_counts)
        vals = [row_counts[k] for k in labels]
        bar_ax.bar(labels, vals)
        bar_ax.set_title("Wells by row")
        self._bar_host["canvas"].draw_idle()

        draw_message(self._scatter_host, f"Scatter host ready ({len(wells)} wells loaded)")
        draw_message(self._cdf_host, f"CDF host ready ({len(wells)} wells loaded)")

    @staticmethod
    def _discover_wells(path: Path) -> list[str]:
        wells: set[str] = set()
        for csv_file in path.glob("*.csv"):
            try:
                with csv_file.open(newline="", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        tok = str(row.get("well", "")).strip()
                        if tok:
                            wells.add(tok)
            except Exception:
                continue
        return sorted(wells)
