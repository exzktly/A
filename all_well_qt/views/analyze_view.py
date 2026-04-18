"""AnalyzeView — pipeline runner: Stardist, gating, smFISH controls.

Run/Stop are wired to the existing services.pipeline_service helpers.
Output is streamed to the log panel via a background QThread.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..widgets.field import Field


class _PipelineWorker(QThread):
    """Runs the pipeline subprocess and streams its output."""

    log_line = Signal(str)
    finished = Signal(int)   # return code

    def __init__(self, args: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._args = args
        self._proc = None

    def run(self) -> None:
        try:
            from services.pipeline_service import spawn_pipeline
            self._proc = spawn_pipeline(self._args)
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                self.log_line.emit(line.rstrip())
            self._proc.wait()
            self.finished.emit(self._proc.returncode)
        except Exception as exc:
            self.log_line.emit(f"[error] Failed to start pipeline: {exc}")
            self.finished.emit(1)

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class _Section(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        lbl = QLabel(title.upper())
        lbl.setObjectName("section")
        layout.addWidget(lbl)
        self.body = QVBoxLayout()
        self.body.setSpacing(4)
        layout.addLayout(self.body)


class AnalyzeView(QWidget):
    """Qt port of the Analyze tab.

    Does NOT contain analysis logic — that runs via ``process_microscopy_v2.py``.
    The ``_PipelineWorker`` thread spawns the subprocess and streams output here.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._worker: _PipelineWorker | None = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Left: controls ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedWidth(360)

        controls = QWidget()
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(14)

        # Input / Output
        io_sec = _Section("Directories")
        cl.addWidget(io_sec)

        in_row = QHBoxLayout()
        self._input_dir = QLineEdit()
        self._input_dir.setPlaceholderText("Input directory…")
        in_row.addWidget(self._input_dir)
        in_browse = QPushButton("Browse…")
        in_browse.setObjectName("ghost")
        in_browse.clicked.connect(lambda: self._browse(self._input_dir))
        in_row.addWidget(in_browse)
        io_sec.body.addLayout(in_row)

        out_row = QHBoxLayout()
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Output directory (leave blank → input/results)")
        out_row.addWidget(self._output_dir)
        out_browse = QPushButton("Browse…")
        out_browse.setObjectName("ghost")
        out_browse.clicked.connect(lambda: self._browse(self._output_dir))
        out_row.addWidget(out_browse)
        io_sec.body.addLayout(out_row)

        # Tokens
        tok_sec = _Section("Channel tokens")
        cl.addWidget(tok_sec)
        self._nuclear_token = Field("nuclear", "NIR", width=60)
        tok_sec.body.addWidget(self._nuclear_token)
        self._fluor_tokens = Field("fluor", "GFP", width=80)
        tok_sec.body.addWidget(self._fluor_tokens)
        csv_row = QHBoxLayout()
        self._csv_prefix = Field("csv prefix", "measurements", width=100)
        csv_row.addWidget(self._csv_prefix)
        csv_row.addStretch()
        tok_sec.body.addLayout(csv_row)

        # Filename schema
        fn_sec = _Section("Filename schema")
        cl.addWidget(fn_sec)
        self._schema = Field("schema", "{well}_{field}_{channel}", width=160)
        fn_sec.body.addWidget(self._schema)
        self._sep = Field("sep", "_", width=30)
        fn_sec.body.addWidget(self._sep)

        # Segmentation
        seg_sec = _Section("Segmentation")
        cl.addWidget(seg_sec)
        self._seg_method = QComboBox()
        self._seg_method.addItems([
            "stardist_nuclei",
            "stardist_seeded_watershed_cell",
        ])
        seg_sec.body.addWidget(self._seg_method)
        self._min_area = Field("min area", "50", unit="px²", width=50)
        seg_sec.body.addWidget(self._min_area)
        tophat_row = QHBoxLayout()
        self._tophat_r_nir = Field("top-hat NIR", "100", unit="px", width=50)
        tophat_row.addWidget(self._tophat_r_nir)
        self._tophat_r_fluor = Field("top-hat fluor", "100", unit="px", width=50)
        tophat_row.addWidget(self._tophat_r_fluor)
        seg_sec.body.addLayout(tophat_row)
        flag_row = QHBoxLayout()
        self._no_tophat_nir = QCheckBox("no top-hat NIR")
        self._no_tophat_fluor = QCheckBox("no top-hat fluor")
        flag_row.addWidget(self._no_tophat_nir)
        flag_row.addWidget(self._no_tophat_fluor)
        seg_sec.body.addLayout(flag_row)

        # smFISH
        fish_sec = _Section("smFISH")
        cl.addWidget(fish_sec)
        self._smfish_tokens = Field("tokens", "", width=80)
        fish_sec.body.addWidget(self._smfish_tokens)

        # Performance
        perf_sec = _Section("Performance")
        cl.addWidget(perf_sec)
        self._workers = Field("workers", "0", width=40)
        perf_sec.body.addWidget(self._workers)
        perf_row = QHBoxLayout()
        self._cpu_only = QCheckBox("CPU only")
        self._force = QCheckBox("Force re-run")
        perf_row.addWidget(self._cpu_only)
        perf_row.addWidget(self._force)
        perf_sec.body.addLayout(perf_row)

        cl.addStretch()

        # Run/Stop row
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("run")
        self._run_btn.clicked.connect(self._on_run)
        btn_row.addWidget(self._run_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stop")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        btn_row.addWidget(self._stop_btn)
        cl.addLayout(btn_row)

        scroll.setWidget(controls)
        outer.addWidget(scroll)

        # ── Right: log output ─────────────────────────────────────────
        log_frame = QFrame()
        log_frame.setObjectName("card")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_head = QWidget()
        lh_layout = QHBoxLayout(log_head)
        lh_layout.setContentsMargins(14, 10, 14, 10)
        lh_layout.addWidget(QLabel("Pipeline log"))
        lh_layout.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("ghost")
        clear_btn.clicked.connect(lambda: self._log.clear())
        lh_layout.addWidget(clear_btn)
        log_layout.addWidget(log_head)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        log_layout.addWidget(sep)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet("border-radius: 0; border: none; font-family: monospace; font-size: 11px;")
        log_layout.addWidget(self._log, 1)

        outer.addWidget(log_frame, 1)

    # ── Helpers ───────────────────────────────────────────────────────
    def _browse(self, target: QLineEdit) -> None:
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "Select directory")
        if d:
            target.setText(d)

    def _build_opts(self) -> dict:
        fluor_raw = self._fluor_tokens.value.strip()
        fluor = [t.strip() for t in fluor_raw.split(",") if t.strip()] or ["GFP"]
        smfish_raw = self._smfish_tokens.value.strip()
        smfish = [t.strip() for t in smfish_raw.split(",") if t.strip()]
        try:
            workers = int(self._workers.value)
        except ValueError:
            workers = 0
        try:
            min_area = int(self._min_area.value)
        except ValueError:
            min_area = 50
        return {
            "nuclear_token":     self._nuclear_token.value.strip() or "NIR",
            "fluor_tokens":      fluor,
            "csv_prefix":        self._csv_prefix.value.strip() or "measurements",
            "filename_schema":   self._schema.value.strip(),
            "filename_sep":      self._sep.value.strip() or "_",
            "segmentation_method": self._seg_method.currentText(),
            "min_nucleus_area_px": min_area,
            "tophat_radius_nir":  self._tophat_r_nir.value,
            "tophat_radius_fluor": self._tophat_r_fluor.value,
            "no_tophat_nir":     self._no_tophat_nir.isChecked(),
            "no_tophat_fluor":   self._no_tophat_fluor.isChecked(),
            "smfish_tokens":     smfish,
            "workers":           workers,
            "cpu_only":          self._cpu_only.isChecked(),
            "force":             self._force.isChecked(),
        }

    def _on_run(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        input_dir = self._input_dir.text().strip()
        if not input_dir:
            QMessageBox.warning(self, "Missing input", "Specify an input directory.")
            return

        output_dir = self._output_dir.text().strip()
        if not output_dir:
            output_dir = str(Path(input_dir) / "results")

        pipeline = Path(__file__).parent.parent.parent / "process_microscopy_v2.py"
        if not pipeline.exists():
            QMessageBox.warning(
                self, "Pipeline not found",
                f"process_microscopy_v2.py not found at:\n{pipeline}"
            )
            return

        try:
            from services.pipeline_service import build_pipeline_args
            args = build_pipeline_args(
                pipeline, Path(input_dir), Path(output_dir), self._build_opts()
            )
        except Exception as exc:
            self._append_log(f"[error] Failed to build pipeline args: {exc}")
            return

        self._append_log(f"$ {' '.join(str(a) for a in args)}\n")
        self._worker = _PipelineWorker(args)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
        self._set_running(True)

    def _on_stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self._append_log("\n[User stopped the pipeline]")

    def _on_finished(self, rc: int) -> None:
        if rc == 0:
            self._append_log("\nPipeline completed successfully.")
        else:
            self._append_log(f"\nPipeline exited with code {rc}.")
        self._set_running(False)

    def _set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

    def _append_log(self, text: str) -> None:
        self._log.append(text)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )
