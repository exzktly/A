"""Image Table tab — centre-pane builder (Qt port).

Top-down layout:
- Header row: rows / cols spinners + Apply button
- Global Options row: channel / timepoint / FOV dropdowns (propagate to cells)
- Action row: Distribute Wells, Generate, Export
- Selector grid (rows × cols of per-cell dropdown groupboxes)
- Per-channel LUT row (one min/max LineEdit pair + Auto button per channel)
- Separator
- Rendered image-table area (built by the controller's Generate)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from well_viewer.ui_helpers import btn_primary, btn_secondary


def build_image_table_tab(app, parent: QWidget) -> None:
    """Construct the Image Table tab inside *parent*."""
    layout = parent.layout()
    if layout is None:
        layout = QVBoxLayout(parent)
        parent.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # State defaults — controller methods read these.
    if not hasattr(app, "_image_table_active_wells"):
        app._image_table_active_wells = set()
    if not hasattr(app, "_image_table_rows"):
        app._image_table_rows = 2
    if not hasattr(app, "_image_table_cols"):
        app._image_table_cols = 3
    if not hasattr(app, "_image_table_cells"):
        app._image_table_cells = []
    if not hasattr(app, "_image_table_lut"):
        app._image_table_lut = {}
    if not hasattr(app, "_image_table_last_render"):
        app._image_table_last_render = {}
    if not hasattr(app, "_image_table_image_cache"):
        app._image_table_image_cache = {}

    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    inner = QWidget()
    il = QVBoxLayout(inner)
    il.setContentsMargins(8, 8, 8, 8)
    il.setSpacing(6)
    scroll.setWidget(inner)
    layout.addWidget(scroll, 1)

    # ── Header: rows / cols spinners ────────────────────────────────────────
    hdr = QWidget(inner)
    hl = QHBoxLayout(hdr)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    hl.addWidget(QLabel("Rows:", hdr))
    rows_spin = QSpinBox(hdr)
    rows_spin.setRange(1, 12)
    rows_spin.setValue(int(app._image_table_rows))
    rows_spin.setFixedWidth(64)
    hl.addWidget(rows_spin)
    app._image_table_rows_spin = rows_spin

    hl.addWidget(QLabel("Cols:", hdr))
    cols_spin = QSpinBox(hdr)
    cols_spin.setRange(1, 12)
    cols_spin.setValue(int(app._image_table_cols))
    cols_spin.setFixedWidth(64)
    hl.addWidget(cols_spin)
    app._image_table_cols_spin = cols_spin

    hl.addWidget(btn_secondary(hdr, "Apply", app._image_table_apply_dimensions))
    hl.addStretch(1)
    il.addWidget(hdr)

    # ── Global Options row ──────────────────────────────────────────────────
    glob = QWidget(inner)
    gl = QHBoxLayout(glob)
    gl.setContentsMargins(0, 0, 0, 0)
    gl.setSpacing(6)
    gl.addWidget(QLabel("Global Options —", glob))

    gl.addWidget(QLabel("Channel:", glob))
    chan_cb = QComboBox(glob)
    chan_cb.currentIndexChanged.connect(
        lambda _i: app._image_table_apply_global("chan")
    )
    gl.addWidget(chan_cb)
    app._image_table_global_chan_cb = chan_cb

    gl.addWidget(QLabel("Timepoint:", glob))
    tp_cb = QComboBox(glob)
    tp_cb.currentIndexChanged.connect(
        lambda _i: app._image_table_apply_global("tp")
    )
    gl.addWidget(tp_cb)
    app._image_table_global_tp_cb = tp_cb

    gl.addWidget(QLabel("FOV:", glob))
    fov_cb = QComboBox(glob)
    fov_cb.currentIndexChanged.connect(
        lambda _i: app._image_table_apply_global("fov")
    )
    gl.addWidget(fov_cb)
    app._image_table_global_fov_cb = fov_cb
    gl.addStretch(1)
    il.addWidget(glob)

    # ── Action buttons ──────────────────────────────────────────────────────
    actions = QWidget(inner)
    al = QHBoxLayout(actions)
    al.setContentsMargins(0, 0, 0, 0)
    al.setSpacing(6)
    al.addWidget(btn_secondary(
        actions, "Distribute Wells", app._image_table_distribute_wells,
    ))
    al.addWidget(btn_primary(actions, "Generate", app._image_table_generate))
    al.addWidget(btn_secondary(actions, "Export", app._image_table_export))
    al.addStretch(1)
    il.addWidget(actions)

    sep1 = QFrame(inner)
    sep1.setObjectName("Separator")
    sep1.setFrameShape(QFrame.HLine)
    sep1.setFixedHeight(1)
    il.addWidget(sep1)

    # ── Selector grid (rows × cols of per-cell dropdowns) ───────────────────
    selector_lbl = QLabel("Selector:", inner)
    selector_lbl.setProperty("role", "section")
    il.addWidget(selector_lbl)

    selector_host = QWidget(inner)
    selector_grid = QGridLayout(selector_host)
    selector_grid.setContentsMargins(0, 0, 0, 0)
    selector_grid.setSpacing(4)
    app._image_table_selector_grid = selector_grid
    il.addWidget(selector_host)

    # ── LUT row (rebuilt per channel by the controller) ─────────────────────
    lut_lbl = QLabel("LUT (per channel):", inner)
    lut_lbl.setProperty("role", "section")
    il.addWidget(lut_lbl)

    lut_container = QWidget(inner)
    lut_layout = QHBoxLayout(lut_container)
    lut_layout.setContentsMargins(0, 0, 0, 0)
    lut_layout.setSpacing(6)
    app._image_table_lut_container = lut_container
    il.addWidget(lut_container)

    sep2 = QFrame(inner)
    sep2.setObjectName("Separator")
    sep2.setFrameShape(QFrame.HLine)
    sep2.setFixedHeight(1)
    il.addWidget(sep2)

    # ── Rendered image table (drawn BELOW the selector, not inside it) ──────
    render_lbl = QLabel("Image Table:", inner)
    render_lbl.setProperty("role", "section")
    il.addWidget(render_lbl)

    render_host = QWidget(inner)
    render_grid = QGridLayout(render_host)
    render_grid.setContentsMargins(0, 0, 0, 0)
    render_grid.setSpacing(6)
    app._image_table_render_grid = render_grid
    il.addWidget(render_host)

    il.addStretch(1)

    # Build the initial grid + LUT row using current pipeline_info.
    app._image_table_repopulate_dropdowns()
    app._image_table_rebuild_grid()
