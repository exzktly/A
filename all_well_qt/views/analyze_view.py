"""AnalyzeView — pipeline runner: Stardist, gating, smFISH controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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


class _Section(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        lbl = QLabel(title.upper())
        lbl.setObjectName("section")
        layout.addWidget(lbl)
        self._body = QVBoxLayout()
        self._body.setSpacing(4)
        layout.addLayout(self._body)
        self.body = self._body


class AnalyzeView(QWidget):
    """Port of the Analyze tab controls.

    Does NOT include actual pipeline logic — that stays in
    process_microscopy_v2.py.  This view fires run_requested/stop_requested
    signals which the adapter layer connects to the pipeline service.
    """

    run_requested = Signal(dict)   # config dict
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Left: controls ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedWidth(340)

        controls = QWidget()
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(16)

        # Data directory
        io_sec = _Section("Input")
        cl.addWidget(io_sec.parentWidget() if False else io_sec)

        dir_row = QHBoxLayout()
        self._data_dir = QLineEdit()
        self._data_dir.setPlaceholderText("/path/to/results/")
        dir_row.addWidget(self._data_dir)
        browse = QPushButton("Browse…")
        browse.setObjectName("ghost")
        browse.clicked.connect(self._on_browse)
        dir_row.addWidget(browse)
        io_sec.body.addLayout(dir_row)
        cl.addWidget(io_sec)

        # Stardist
        seg_sec = _Section("Segmentation (Stardist)")
        self._radius_field = Field("radius", "50", unit="px", width=50)
        seg_sec.body.addWidget(self._radius_field)
        self._prob_field = Field("prob thresh", "0.50", width=50)
        seg_sec.body.addWidget(self._prob_field)
        cl.addWidget(seg_sec)

        # Cell gating
        gate_sec = _Section("Cell gating")
        self._min_area_field = Field("min area", "50", unit="px²", width=50)
        gate_sec.body.addWidget(self._min_area_field)
        self._max_area_field = Field("max area", "5000", unit="px²", width=50)
        gate_sec.body.addWidget(self._max_area_field)
        cl.addWidget(gate_sec)

        # smFISH
        fish_sec = _Section("smFISH threshold")
        self._fish_thresh_field = Field("threshold", "auto", width=60)
        fish_sec.body.addWidget(self._fish_thresh_field)
        cl.addWidget(fish_sec)

        cl.addStretch()

        # Run/Stop row
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("run")
        self._run_btn.clicked.connect(self._on_run)
        btn_row.addWidget(self._run_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stop")
        self._stop_btn.clicked.connect(self.stop_requested)
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
        self._log.setObjectName("sunkFrame")
        self._log.setStyleSheet("border-radius: 0; border: none;")
        log_layout.addWidget(self._log, 1)

        outer.addWidget(log_frame, 1)

    def _on_browse(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "Select results directory")
        if d:
            self._data_dir.setText(d)

    def _on_run(self) -> None:
        config = {
            "data_dir": self._data_dir.text(),
            "radius": self._radius_field.value,
            "prob_thresh": self._prob_field.value,
            "min_area": self._min_area_field.value,
            "max_area": self._max_area_field.value,
            "fish_threshold": self._fish_thresh_field.value,
        }
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self.run_requested.emit(config)

    def append_log(self, text: str) -> None:
        self._log.append(text)

    def set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
