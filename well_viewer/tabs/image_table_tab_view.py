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
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from well_viewer.crop_tool import CropTool
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
    if not hasattr(app, "_image_table_use_tophat"):
        app._image_table_use_tophat = False
    # Shared square-region crop helper. on_change re-runs Generate so the
    # rendered grid follows mode toggles and crop changes automatically.
    if not hasattr(app, "_image_table_crop_tool"):
        app._image_table_crop_tool = CropTool(
            on_change=lambda: app._image_table_generate(),
        )

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
    hdr.setObjectName("TabCtrl")
    hl = QHBoxLayout(hdr)
    hl.setContentsMargins(8, 6, 8, 6)
    hl.setSpacing(6)

    hl.addWidget(QLabel("Rows:", hdr))
    rows_spin = QSpinBox(hdr)
    rows_spin.setRange(1, 12)
    rows_spin.setValue(int(app._image_table_rows))
    rows_spin.setFixedWidth(64)
    rows_spin.valueChanged.connect(lambda _v: app._image_table_apply_dimensions())
    hl.addWidget(rows_spin)
    app._image_table_rows_spin = rows_spin

    hl.addWidget(QLabel("Cols:", hdr))
    cols_spin = QSpinBox(hdr)
    cols_spin.setRange(1, 12)
    cols_spin.setValue(int(app._image_table_cols))
    cols_spin.setFixedWidth(64)
    cols_spin.valueChanged.connect(lambda _v: app._image_table_apply_dimensions())
    hl.addWidget(cols_spin)
    app._image_table_cols_spin = cols_spin
    hl.addStretch(1)
    il.addWidget(hdr)

    # ── Global Options row (channel is now per-row; see selector grid) ──────
    glob = QWidget(inner)
    glob.setObjectName("TabCtrl")
    gl = QHBoxLayout(glob)
    gl.setContentsMargins(8, 6, 8, 6)
    gl.setSpacing(6)
    gl.addWidget(QLabel("Global Options —", glob))

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
    al.addWidget(btn_secondary(
        actions, "Distribute Timepoints", app._image_table_distribute_timepoints,
    ))
    al.addWidget(btn_primary(actions, "Generate", app._image_table_generate))
    al.addWidget(btn_secondary(actions, "Export", app._image_table_export))

    # Raw ↔ Tophat toggle. Checkable so the button doubles as an indicator
    # of the current source (pressed = tophat, released = raw).
    tophat_btn = QPushButton("Tophat", actions)
    tophat_btn.setProperty("variant", "secondary")
    tophat_btn.setCheckable(True)
    tophat_btn.setChecked(bool(app._image_table_use_tophat))
    tophat_btn.setToolTip(
        "Toggle between raw fluorescence and pre-filtered tophat images."
    )
    tophat_btn.clicked.connect(lambda _=False: app._image_table_toggle_tophat())
    app._image_table_tophat_btn = tophat_btn
    al.addWidget(tophat_btn)

    # Reuse the shared CropTool helper (also used by Movie Montage).
    crop_sep = QFrame(actions)
    crop_sep.setFrameShape(QFrame.VLine)
    crop_sep.setFixedWidth(1)
    al.addWidget(crop_sep)
    al.addWidget(app._image_table_crop_tool.make_button(actions))
    al.addWidget(app._image_table_crop_tool.make_reset_button(actions))
    al.addWidget(app._image_table_crop_tool.make_status_label(actions))

    al.addStretch(1)
    il.addWidget(actions)

    sep1 = QFrame(inner)
    sep1.setObjectName("Separator")
    sep1.setFrameShape(QFrame.HLine)
    sep1.setFixedHeight(2)
    il.addWidget(sep1)
    il.addSpacing(6)

    # ── Selector grid (rows × cols of per-cell dropdowns) ───────────────────
    # Wrap selector area in a styled frame so it is visually distinct from
    # the global-options strip above and the LUT row below.
    selector_box = QFrame(inner)
    selector_box.setObjectName("ImageTableSelector")
    selector_box.setFrameShape(QFrame.StyledPanel)
    sb_layout = QVBoxLayout(selector_box)
    sb_layout.setContentsMargins(8, 6, 8, 8)
    sb_layout.setSpacing(4)

    selector_lbl = QLabel("Selector", selector_box)
    selector_lbl.setProperty("role", "section")
    sb_layout.addWidget(selector_lbl)

    selector_host = QWidget(selector_box)
    selector_grid = QGridLayout(selector_host)
    selector_grid.setContentsMargins(0, 0, 0, 0)
    selector_grid.setSpacing(4)
    app._image_table_selector_grid = selector_grid
    sb_layout.addWidget(selector_host)
    il.addWidget(selector_box)
    il.addSpacing(6)

    # ── LUT row (rebuilt per channel by the controller) ─────────────────────
    # Wrap the row in a tinted frame so it visually reads as a global
    # control strip, not as another row of per-cell selectors.
    lut_outer = QFrame(inner)
    lut_outer.setObjectName("ImageTableLutRow")
    lut_outer.setStyleSheet(
        "QFrame#ImageTableLutRow { "
        "background-color: rgba(245, 158, 11, 0.12); "
        "border: 1px solid rgba(245, 158, 11, 0.40); "
        "border-radius: 4px; "
        "}"
    )
    lut_outer_layout = QVBoxLayout(lut_outer)
    lut_outer_layout.setContentsMargins(8, 6, 8, 6)
    lut_outer_layout.setSpacing(4)

    lut_lbl = QLabel("LUT (per channel) — applies to every cell of that channel", lut_outer)
    lut_lbl.setProperty("role", "section")
    lut_outer_layout.addWidget(lut_lbl)

    lut_container = QWidget(lut_outer)
    lut_layout = QHBoxLayout(lut_container)
    lut_layout.setContentsMargins(0, 0, 0, 0)
    lut_layout.setSpacing(6)
    app._image_table_lut_container = lut_container
    lut_outer_layout.addWidget(lut_container)
    il.addWidget(lut_outer)

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
