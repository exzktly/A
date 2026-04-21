"""Preview-tab UI helpers (Qt port)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def build_preview_picker(app, parent: QWidget, **_kw) -> None:
    """Compact plate-map preview picker in the sidebar."""
    from well_viewer.views.well_button import build_plate_grid

    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    # Outer margins kept at 0 so the plate-map's own uniform padding (from
    # build_plate_grid) matches every other tab's well picker.
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    title = QLabel("PREVIEW WELL", parent)
    title.setProperty("role", "section")
    layout.addWidget(title)

    help_lbl = QLabel("Click one well to load its images", parent)
    help_lbl.setObjectName("Muted")
    layout.addWidget(help_lbl)

    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    layout.addWidget(sep)

    map_f = QWidget(parent)
    layout.addWidget(map_f)
    app._sidebar_preview_btns = {}
    build_plate_grid(
        map_f,
        app._sidebar_preview_btns,
        on_click=lambda t: app._preview_pick_well(t),
    )

    app._preview_sel_lbl = QLabel("No well selected", parent)
    app._preview_sel_lbl.setObjectName("Muted")
    app._preview_sel_lbl.setAlignment(Qt.AlignLeft)
    layout.addWidget(app._preview_sel_lbl)


def preview_pick_well(app, tok: str) -> None:
    if tok not in app._well_paths:
        return
    app._preview_selected_well = (
        None if app._preview_selected_well == tok else tok
    )
    app._refresh_preview_picker()
    app._update_preview(app._preview_selected_well)


def refresh_preview_picker(app, **_kw) -> None:
    for tok, btn in app._sidebar_preview_btns.items():
        if tok not in app._well_paths:
            btn.setEnabled(False)
            btn.set_state("empty")
        elif tok == app._preview_selected_well:
            btn.setEnabled(True)
            btn.set_state("selected")
        else:
            btn.setEnabled(True)
            btn.set_state("available")
    if hasattr(app, "_preview_sel_lbl"):
        sel = app._preview_selected_well
        app._preview_sel_lbl.setText(
            f"Selected: {sel}" if sel else "No well selected"
        )
