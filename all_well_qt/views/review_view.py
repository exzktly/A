"""ReviewView — three-column QSplitter: Sidebar | PlotWorkspace | PreviewPanel."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QSplitter, QWidget
from PySide6.QtCore import Qt

from .sidebar import Sidebar
from .plot_workspace import PlotWorkspace
from .preview_panel import PreviewPanel


class ReviewView(QSplitter):
    """Three-pane review layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)

        self.sidebar = Sidebar()
        self.plot_workspace = PlotWorkspace()
        self.preview_panel = PreviewPanel()

        self.addWidget(self.sidebar)
        self.addWidget(self.plot_workspace)
        self.addWidget(self.preview_panel)

        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setStretchFactor(2, 0)

        self.sidebar.hovered_well_changed.connect(
            self.preview_panel.update_well
        )

    def save_state(self, settings: QSettings) -> None:
        settings.setValue("review_splitter", self.saveState())

    def restore_state(self, settings: QSettings) -> None:
        state = settings.value("review_splitter")
        if state:
            self.restoreState(state)
