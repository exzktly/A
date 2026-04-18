"""ReviewView — three-column QSplitter: Sidebar | PlotWorkspace | PreviewPanel."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QSplitter, QWidget

from .sidebar import Sidebar
from .plot_workspace import PlotWorkspace
from .preview_panel import PreviewPanel
from ..adapters.image_loader import ImageLoader
from ..widgets.plate_map import GroupSpec


class ReviewView(QSplitter):
    """Three-pane review layout.

    Data flow when user loads a dataset:
      Sidebar.data_dir_changed → _on_data_dir_changed
        → PlotWorkspace.set_data_dir(path)
        → ImageLoader.set_data_dir(path)
        → PreviewPanel.set_image_loader(loader)

    When sidebar selection/groups change:
      Sidebar._well_group_map → _on_groups_changed
        → PlotWorkspace.set_live_groups(groups)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)

        self.sidebar = Sidebar()
        self.plot_workspace = PlotWorkspace()
        self.preview_panel = PreviewPanel()
        self._image_loader = ImageLoader()

        self.addWidget(self.sidebar)
        self.addWidget(self.plot_workspace)
        self.addWidget(self.preview_panel)

        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setStretchFactor(2, 0)

        # Preview updates on hover
        self.sidebar.hovered_well_changed.connect(self.preview_panel.update_well)

        # Dataset load
        self.sidebar.data_dir_changed.connect(self._on_data_dir_changed)

        # Push group map to PlotWorkspace after any group change in sidebar
        self.sidebar.sample_groups.group_renamed.connect(
            lambda *_: self._push_groups_to_workspace()
        )
        self.sidebar.sample_groups.group_deleted.connect(
            lambda *_: self._push_groups_to_workspace()
        )
        self.sidebar.sample_groups.new_group_requested.connect(
            lambda: self._push_groups_to_workspace()
        )

        # Give the panel the loader so hover triggers real loads
        self.preview_panel.set_image_loader(self._image_loader)

    # ── Data flow ─────────────────────────────────────────────────────
    def _on_data_dir_changed(self, path: str) -> None:
        self.plot_workspace.set_data_dir(path)
        self._image_loader.set_data_dir(path)
        # Check for in/out layout
        from pathlib import Path
        p = Path(path)
        in_dir = p.parent / "in"
        if in_dir.is_dir():
            self._image_loader.set_in_dir(str(in_dir))
        # Re-push groups so the new renderer renders with current groups
        self._push_groups_to_workspace()

    def _push_groups_to_workspace(self) -> None:
        """Build a groups dict from sidebar's _well_group_map and push to PlotWorkspace."""
        mapping: dict[str, GroupSpec] = getattr(self.sidebar, "_well_group_map", {})
        # Invert: group_id → {wells, color, name}
        groups: dict[str, dict] = {}
        for well, spec in mapping.items():
            if spec.id not in groups:
                groups[spec.id] = {"wells": [], "color": spec.color, "name": spec.name}
            groups[spec.id]["wells"].append(well)
        self.plot_workspace.set_live_groups(groups)

    # ── Persistence ───────────────────────────────────────────────────
    def save_state(self, settings: QSettings) -> None:
        settings.setValue("review_splitter", self.saveState())

    def restore_state(self, settings: QSettings) -> None:
        state = settings.value("review_splitter")
        if state:
            self.restoreState(state)
