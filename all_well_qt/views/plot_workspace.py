"""PlotWorkspace — center pane: sub-tabs, chart, legend, metric chips."""

from __future__ import annotations

import logging

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

_log = logging.getLogger("all_well_qt.plot_workspace")


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

        self._empty_lbl = QLabel("Load a dataset to view charts")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setObjectName("muted")
        self._layout.addWidget(self._empty_lbl)

    def set_canvas(self, canvas: QWidget) -> None:
        if self._canvas:
            self._layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
        self._empty_lbl.hide()
        self._canvas = canvas
        self._layout.addWidget(canvas)

    def show_empty(self, message: str = "Load a dataset to view charts") -> None:
        if self._canvas:
            self._layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
            self._canvas = None
        self._empty_lbl.setText(message)
        self._empty_lbl.show()


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

        # State
        self._data_dir: str = ""
        self._live_groups: dict = {}
        self._renderer = None

    # ── Public API ────────────────────────────────────────────────────
    def set_data_dir(self, path: str) -> None:
        self._data_dir = path
        try:
            from ..adapters.plot_renderer import PlotRenderer
            self._renderer = PlotRenderer(path)
        except Exception:
            _log.exception("Failed to create PlotRenderer for %s", path)
            self._renderer = None
        self._render_chart()

    def set_live_groups(self, groups: dict) -> None:
        """Update group→wells mapping; re-renders if a dataset is loaded."""
        self._live_groups = groups
        if self._data_dir:
            self._render_chart()

    # ── Internal ──────────────────────────────────────────────────────
    def _render_chart(self) -> None:
        metric = self._metric_chips.current_label()
        normalize = self._norm_chip.isChecked()
        channel = self._channel_field.value.strip()

        renderer = getattr(self, "_renderer", None)
        if renderer is None:
            self._chart_frame.show_empty()
            return

        groups = dict(self._live_groups)

        # When data is loaded but no groups assigned yet, treat all wells as one group.
        if not groups and renderer.available_wells():
            groups = {
                "_all": {
                    "wells": renderer.available_wells(),
                    "color": "#0E6B52",
                    "name": "All wells",
                }
            }

        if not groups:
            self._chart_frame.show_empty("No wells loaded")
            return

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            fig = renderer.render_kinetics(
                groups, metric=metric, normalize=normalize, channel=channel
            )
        except Exception:
            _log.exception("render_kinetics failed")
            self._chart_frame.show_empty("Chart render error — check log")
            return

        if fig is None:
            self._chart_frame.show_empty("No data matched the selected channel / wells")
            return

        canvas = FigureCanvasQTAgg(fig)
        canvas.setStyleSheet("background: transparent;")
        self._chart_frame.set_canvas(canvas)
        self._populate_legend(groups)

    def _clear_legend(self) -> None:
        while self._legend_layout.count() > 1:
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_legend(self, groups: dict) -> None:
        self._clear_legend()
        for idx, (gid, spec) in enumerate(groups.items()):
            row = LegendRow(gid, spec.get("name", gid), spec.get("color", "#888"))
            self._legend_layout.insertWidget(idx, row)

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
