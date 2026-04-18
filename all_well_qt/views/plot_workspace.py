"""PlotWorkspace — center pane: sub-tabs, chart, legend, metric chips."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGraphicsDropShadowEffect, QColor
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
        self._build_demo_chart()
        self._populate_demo_legend()

    # ── Internal ──────────────────────────────────────────────────────
    def _build_demo_chart(self) -> None:
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

        fig = Figure(facecolor="none")
        ax = fig.add_subplot(111)
        t = np.linspace(0, 12, 49)
        groups = [
            ("Control",        "#0E6B52", np.exp(-0.05 * t)),
            ("PF · 100 nM",    "#E25C3A", 1 + 0.5 * np.sin(t * 0.6)),
            ("PF · 1 µM",      "#C08A2E", 1 + 1.2 * np.sin(t * 0.5)),
        ]
        ax.set_facecolor("none")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines["bottom"].set_color("#DED5C2")
        ax.spines["left"].set_color("#DED5C2")
        ax.tick_params(colors="#7C786D", labelsize=9)
        ax.set_xlabel("Time (h)", color="#7C786D", fontsize=9)
        ax.set_ylabel("Fold change", color="#7C786D", fontsize=9)
        ax.axvline(6, color="#C08A2E", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.text(6.1, ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else 0.1,
                "drug added · t=6h", color="#C08A2E", fontsize=7.5)
        for name, color, y in groups:
            ax.plot(t, y, color=color, linewidth=1.5)
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
        pass  # re-render chart with new metric reduction

    def _on_save_figure(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save figure", "figure", "PNG (*.png);;SVG (*.svg)"
        )
        if not path:
            return
        if self._chart_frame._canvas:
            self._chart_frame._canvas.figure.savefig(path, bbox_inches="tight")
