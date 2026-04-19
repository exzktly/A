"""Phase 4 Slice A: minimal PySide6 Analyze tab vertical slice."""

from __future__ import annotations

import subprocess
from pathlib import Path

from services.input_resolution_service import resolve_input_output
from services.pipeline_service import (
    build_pipeline_args,
    find_pipeline_script,
    spawn_pipeline,
)
from services.ui_state_models import AnalysisPipelineState
from ui.qt_ui import error as show_error
from ui.qt_ui import pick_directory


class AnalyzeTabQt:  # thin wrapper to avoid importing PySide6 at module import time
    def __init__(self, on_pipeline_complete=None):
        from PySide6.QtWidgets import (
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QPlainTextEdit,
            QProgressBar,
            QVBoxLayout,
            QWidget,
        )

        self.widget = QWidget()
        self._on_pipeline_complete = on_pipeline_complete
        self._proc: subprocess.Popen | None = None

        root = QVBoxLayout(self.widget)

        form_box = QGroupBox("Pipeline")
        form = QGridLayout(form_box)

        self._input_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)

        self._nuclear_edit = QLineEdit("NIR")
        self._fluor_edit = QLineEdit("GFP")
        self._csv_prefix_edit = QLineEdit("gfp_measurements")

        form.addWidget(QLabel("Input folder"), 0, 0)
        form.addWidget(self._input_edit, 0, 1)
        form.addWidget(browse, 0, 2)
        form.addWidget(QLabel("Nuclear token"), 1, 0)
        form.addWidget(self._nuclear_edit, 1, 1, 1, 2)
        form.addWidget(QLabel("Fluor tokens (comma-separated)"), 2, 0)
        form.addWidget(self._fluor_edit, 2, 1, 1, 2)
        form.addWidget(QLabel("CSV prefix"), 3, 0)
        form.addWidget(self._csv_prefix_edit, 3, 1, 1, 2)

        root.addWidget(form_box)

        actions = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._status = QLabel("Idle")
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._run_btn.clicked.connect(self._run)
        self._stop_btn.clicked.connect(self._stop)

        actions.addWidget(self._run_btn)
        actions.addWidget(self._stop_btn)
        actions.addWidget(self._status)
        actions.addStretch(1)
        actions.addWidget(self._progress)
        root.addLayout(actions)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        root.addWidget(self._log, stretch=1)

    def _append_log(self, text: str) -> None:
        self._log.appendPlainText(text.rstrip("\n"))

    def _browse(self) -> None:
        path = pick_directory(self.widget, title="Select input folder")
        if path is not None:
            self._input_edit.setText(str(path))

    def _to_state(self) -> AnalysisPipelineState:
        fluor = [t.strip() for t in self._fluor_edit.text().split(",") if t.strip()]
        return AnalysisPipelineState.from_ui_values(
            raw_input=self._input_edit.text(),
            nuclear_token=self._nuclear_edit.text(),
            fluor_tokens=fluor,
            smfish_tokens=[],
            csv_prefix=self._csv_prefix_edit.text(),
            filename_schema="experiment:channel:well:fov:timepoint",
            filename_sep="_",
            segmentation_method="stardist_nuclei",
            cytoplasm_token="",
            min_nucleus_area_px="50",
            tophat_radius_nir="100",
            tophat_radius_fluor="100",
            no_tophat_nir=False,
            no_tophat_fluor=False,
            compress_input_well_folders=True,
            compress_output_well_folders=True,
            force=False,
            cpu_only=False,
            tf_threads="0",
            workers="0",
        )

    def _run(self) -> None:
        state = self._to_state()
        if not str(state.raw_input):
            show_error(self.widget, "Input Error", "No input folder selected.")
            return
        pipeline = find_pipeline_script()
        if pipeline is None:
            show_error(self.widget, "Configuration Error", "Pipeline script not found.")
            return

        opts = state.to_pipeline_options()
        try:
            input_dir, output_dir = resolve_input_output(opts["raw"])
        except Exception as exc:
            show_error(self.widget, "Input Error", str(exc))
            return

        args = build_pipeline_args(pipeline, input_dir, output_dir, opts)
        self._append_log("$ " + " ".join(args))
        self._append_log(f"Input : {input_dir}")
        self._append_log(f"Output: {output_dir}")

        self._proc = spawn_pipeline(args)
        self._status.setText("Running…")
        self._progress.setVisible(True)
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        from PySide6.QtCore import QTimer

        self._poll_timer = QTimer(self.widget)
        self._poll_timer.timeout.connect(lambda: self._poll(output_dir))
        self._poll_timer.start(150)

    def _poll(self, output_dir: Path) -> None:
        if self._proc is None:
            return
        while True:
            line = self._proc.stdout.readline() if self._proc.stdout else ""
            if not line:
                break
            self._append_log(line)

        if self._proc.poll() is None:
            return

        rc = self._proc.returncode
        self._poll_timer.stop()
        self._proc = None
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        if rc == 0:
            self._status.setText("Done")
            self._append_log("\n[done] Pipeline finished.")
            if self._on_pipeline_complete is not None:
                self._on_pipeline_complete(output_dir)
        else:
            self._status.setText("Failed")
            self._append_log(f"\n[error] Pipeline exited with code {rc}.")

    def _stop(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
        except Exception:
            pass
        self._append_log("[info] Stop requested by user.")
