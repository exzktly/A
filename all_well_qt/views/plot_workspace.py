"""PlotWorkspace — center pane: sub-tabs, chart, legend, metric chips."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from ..widgets.chip_group import ChipGroup
from ..widgets.field import Field


class LegendRow(QWidget):
    clicked = Signal(str)  # group_id

    def __init__(
        self, group_id: str, name: str, color: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.group_id = group_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{color}; border-radius: 5px;")
        layout.addWidget(dot)

        lbl = QLabel(name)
        lbl.setObjectName("muted")
        layout.addWidget(lbl)
        layout.addStretch()
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        self.clicked.emit(self.group_id)
        super().mousePressEvent(event)


class ChartFrame(QFrame):
    """Wraps a matplotlib FigureCanvasQTAgg in a styled card frame."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._canvas = None

    def set_canvas(self, canvas: QWidget) -> None:
        if self._canvas:
            self._layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
        self._canvas = canvas
        self._layout.addWidget(canvas)


class PlotWorkspace(QWidget):
    """Center panel: sub-tabs, workspace card with chart + legend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sub-tabs ──────────────────────────────────────────────────
        self._tab_bar = QTabBar()
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDrawBase(False)
        for label in ["Kinetics", "Bar plots", "Scatter", "Stats", "CSV"]:
            self._tab_bar.addTab(label)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tab_bar)

        # ── Workspace card ────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Workspace header
        ws_head = QWidget()
        ws_head_layout = QHBoxLayout(ws_head)
        ws_head_layout.setContentsMargins(14, 10, 14, 10)
        ws_head_layout.setSpacing(8)

        self._title_lbl = QLabel("Kinetics — fold change")
        self._title_lbl.setObjectName("panelTitle")
        ws_head_layout.addWidget(self._title_lbl)
        ws_head_layout.addStretch()

        save_btn = QPushButton("Save figure…")
        save_btn.setObjectName("ghost")
        save_btn.clicked.connect(self._on_save_figure)
        ws_head_layout.addWidget(save_btn)
        card_layout.addWidget(ws_head)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        card_layout.addWidget(sep)

        # Chips row
        chips_row = QWidget()
        cr_layout = QHBoxLayout(chips_row)
        cr_layout.setContentsMargins(14, 8, 14, 8)
        cr_layout.setSpacing(10)

        self._metric_chips = ChipGroup(["Mean", "Median", "Sum", "CDF"])
        self._metric_chips.chip_changed.connect(self._on_metric_changed)
        cr_layout.addWidget(self._metric_chips)

        self._norm_chip = QPushButton("Normalize")
        self._norm_chip.setObjectName("chip")
        self._norm_chip.setCheckable(True)
        self._norm_chip.toggled.connect(self._on_normalize_toggled)
        cr_layout.addWidget(self._norm_chip)
        cr_layout.addStretch()

        self._channel_field = Field("ch", "GFP", width=50)
        cr_layout.addWidget(self._channel_field)
        card_layout.addWidget(chips_row)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFixedHeight(1)
        card_layout.addWidget(sep2)

        # Chart + legend row
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._chart_frame = ChartFrame()
        self._chart_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout.addWidget(self._chart_frame, 1)

        # Legend
        legend_frame = QFrame()
        legend_frame.setFixedWidth(200)
        legend_frame.setObjectName("sunkFrame")
        leg_layout = QVBoxLayout(legend_frame)
        leg_layout.setContentsMargins(8, 10, 8, 10)
        leg_layout.setSpacing(2)

        leg_title = QLabel("LEGEND")
        leg_title.setObjectName("section")
        leg_layout.addWidget(leg_title)

        self._legend_scroll = QScrollArea()
        self._legend_scroll.setWidgetResizable(True)
        self._legend_scroll.setFrameShape(QFrame.NoFrame)
        self._legend_container = QWidget()
        self._legend_layout = QVBoxLayout(self._legend_container)
        self._legend_layout.setContentsMargins(0, 0, 0, 0)
        self._legend_layout.setSpacing(2)
        self._legend_layout.addStretch()
        self._legend_scroll.setWidget(self._legend_container)
        leg_layout.addWidget(self._legend_scroll)
        content_layout.addWidget(legend_frame)
        card_layout.addWidget(content, 1)
        layout.addWidget(card, 1)

        # Build initial demo chart
        self._render_chart()
        self._populate_demo_legend()

    # ── Demo data ─────────────────────────────────────────────────────
    # Shape: (3 groups, 49 time-points, 6 replicate wells)
    _DEMO_GROUPS = [
        ("Control (DMSO)",     "#0E6B52"),
        ("PF-562271 · 100 nM", "#E25C3A"),
        ("PF-562271 · 1 µM",   "#C08A2E"),
    ]

    @staticmethod
    def _demo_raw() -> tuple[np.ndarray, np.ndarray]:
        """Return (t, data[group, time, replicate]) for the demo dataset."""
        rng = np.random.default_rng(42)
        t = np.linspace(0, 12, 49)
        bases = [
            np.exp(-0.05 * t),
            1 + 0.5 * np.sin(t * 0.6),
            1 + 1.2 * np.sin(t * 0.5),
        ]
        data = np.stack([
            b[:, None] + rng.normal(0, 0.06, (len(t), 6))
            for b in bases
        ])  # (3, 49, 6)
        return t, data

    # ── Internal ──────────────────────────────────────────────────────
    def _render_chart(self) -> None:
        metric = self._metric_chips.current_label() if hasattr(self, "_metric_chips") else "Mean"
        normalize = self._norm_chip.isChecked() if hasattr(self, "_norm_chip") else False

        try:
            import matplotlib
            matplotlib.use("QtAgg")
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except Exception:
            placeholder = QLabel("matplotlib not available")
            placeholder.setAlignment(Qt.AlignCenter)
            self._chart_frame._layout.addWidget(placeholder)
            return

        t, data = self._demo_raw()

        # Apply metric reduction across replicates axis
        if metric == "Mean":
            y_all = data.mean(axis=2)
        elif metric == "Median":
            y_all = np.median(data, axis=2)
        elif metric == "Sum":
            y_all = data.sum(axis=2)
        else:  # CDF — show cumulative distribution at final time point; fall back to mean
            y_all = data.mean(axis=2)

        if normalize:
            baseline = y_all[:, :1]
            denom = np.where(np.abs(baseline) < 1e-9, 1.0, baseline)
            y_all = y_all / denom

        try:
            from ..theme.manager import ThemeManager
            t_map = ThemeManager.instance().tokens
            spine_color = t_map["line"]
            tick_color = t_map["mut"]
            ann_color = t_map["warn"]
        except Exception:
            spine_color, tick_color, ann_color = "#DED5C2", "#7C786D", "#C08A2E"

        fig = Figure(facecolor="none")
        ax = fig.add_subplot(111)
        ax.set_facecolor("none")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines["bottom"].set_color(spine_color)
        ax.spines["left"].set_color(spine_color)
        ax.tick_params(colors=tick_color, labelsize=9)
        ylabel = ("Fold change (norm.)" if normalize else "Fold change") if metric != "Sum" else "Sum"
        ax.set_xlabel("Time (h)", color=tick_color, fontsize=9)
        ax.set_ylabel(ylabel, color=tick_color, fontsize=9)
        ax.axvline(6, color=ann_color, linestyle="--", linewidth=0.8, alpha=0.6)
        ax.text(6.15, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else 0.02,
                "drug added · t=6h", color=ann_color, fontsize=7.5)

        for i, (name, color) in enumerate(self._DEMO_GROUPS):
            y = y_all[i]
            ax.plot(t, y, color=color, linewidth=1.5, label=name)
            ax.fill_between(t, y, alpha=0.06, color=color)
            ax.plot(t[-1], y[-1], "o", color=color, markersize=5)

        fig.tight_layout(pad=0.8)
        canvas = FigureCanvasQTAgg(fig)
        canvas.setStyleSheet("background: transparent;")
        self._chart_frame.set_canvas(canvas)

    def _populate_demo_legend(self) -> None:
        groups = [
            ("ctrl",  "Control (DMSO)",     "#0E6B52"),
            ("dose1", "PF-562271 · 100 nM", "#E25C3A"),
            ("dose2", "PF-562271 · 1 µM",   "#C08A2E"),
            ("ripk",  "RIPK1 kd",           "#7A4AB5"),
            ("ripa",  "RIPA co-treat",      "#1F6FB8"),
        ]
        idx = self._legend_layout.count() - 1
        for gid, name, color in groups:
            row = LegendRow(gid, name, color)
            self._legend_layout.insertWidget(idx, row)
            idx += 1

    def _on_tab_changed(self, idx: int) -> None:
        titles = ["Kinetics — fold change", "Bar plots", "Scatter (cells)",
                  "Statistics", "CSV export"]
        self._title_lbl.setText(titles[idx] if idx < len(titles) else "")

    def _on_metric_changed(self, _: int) -> None:
        self._render_chart()

    def _on_normalize_toggled(self, _: bool) -> None:
        self._render_chart()

    def _on_save_figure(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save figure", "figure", "PNG (*.png);;SVG (*.svg)"
        )
        if not path:
            return
        if self._chart_frame._canvas:
            self._chart_frame._canvas.figure.savefig(path, bbox_inches="tight")
