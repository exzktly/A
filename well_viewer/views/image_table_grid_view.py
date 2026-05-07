"""Image Table selector grid + per-channel LUT row view builders.

These are pure view-construction helpers extracted from
``well_viewer.image_table_controller`` so the controller module can stay
focused on data loading, applying user choices, and exporting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


def build_image_table_grid(
    app,
    *,
    rows: int,
    cols: int,
    chan_opts: List[str],
    tp_opts: List[str],
    fov_opts: List[str],
    well_opts: List[str],
    lut_color_names: List[str],
    on_apply_row_well,
    on_apply_row_channel,
    on_generate,
) -> Tuple[
    List[List[Dict[str, Any]]],
    List[QComboBox],
    List[QComboBox],
    List[QComboBox],
]:
    """Populate ``app._image_table_selector_grid`` with the selector cells.

    Returns ``(cells, row_chan_cbs, row_lut_color_cbs, row_well_cbs)``. The
    caller (controller) wires those onto ``app`` and re-renders the LUT row.
    """
    from well_viewer.ui_helpers import clear_layout

    layout = app._image_table_selector_grid
    clear_layout(layout)

    prev_lut_cbs: List[QComboBox] = list(
        getattr(app, "_image_table_row_lut_color_cbs", []) or []
    )

    cells: List[List[Dict[str, Any]]] = []
    row_chan_cbs: List[QComboBox] = []
    row_lut_color_cbs: List[QComboBox] = []
    row_well_cbs: List[QComboBox] = []

    for r in range(rows):
        row_box = QGroupBox(f"Row {r + 1}")
        row_box.setObjectName("ImageTableRowOptions")
        row_box.setStyleSheet(
            "QGroupBox#ImageTableRowOptions { "
            "background-color: rgba(99, 102, 241, 0.10); "
            "border: 1px solid rgba(99, 102, 241, 0.35); "
            "border-radius: 4px; margin-top: 8px; "
            "} "
            "QGroupBox#ImageTableRowOptions::title { "
            "subcontrol-origin: margin; left: 8px; padding: 0 4px; "
            "}"
        )
        rbl = QVBoxLayout(row_box)
        rbl.setContentsMargins(6, 8, 6, 6)
        rbl.setSpacing(4)

        well_lbl = QLabel("Well:", row_box)
        well_lbl.setStyleSheet("font-size: 10px;")
        rbl.addWidget(well_lbl)
        row_well_cb = QComboBox(row_box)
        row_well_cb.addItems(well_opts)
        rbl.addWidget(row_well_cb)
        row_well_cb.currentIndexChanged.connect(
            lambda _i, ridx=r: on_apply_row_well(app, ridx)
        )

        chan_lbl = QLabel("Channel:", row_box)
        chan_lbl.setStyleSheet("font-size: 10px;")
        rbl.addWidget(chan_lbl)
        row_chan_cb = QComboBox(row_box)
        row_chan_cb.addItems(chan_opts)
        rbl.addWidget(row_chan_cb)
        row_chan_cb.currentIndexChanged.connect(
            lambda _i, ridx=r: on_apply_row_channel(app, ridx)
        )

        col_lbl = QLabel("LUT colour:", row_box)
        col_lbl.setStyleSheet("font-size: 10px;")
        rbl.addWidget(col_lbl)
        row_color_cb = QComboBox(row_box)
        row_color_cb.addItems(lut_color_names)
        if r < len(prev_lut_cbs):
            prev_text = prev_lut_cbs[r].currentText()
            if prev_text in lut_color_names:
                row_color_cb.setCurrentText(prev_text)
        rbl.addWidget(row_color_cb)
        row_color_cb.currentIndexChanged.connect(
            lambda _i: on_generate(app)
        )

        layout.addWidget(row_box, r, 0)
        row_chan_cbs.append(row_chan_cb)
        row_lut_color_cbs.append(row_color_cb)
        row_well_cbs.append(row_well_cb)

        cell_row: List[Dict[str, Any]] = []
        for c in range(cols):
            cell = build_selector_cell(
                r, c, well_opts, chan_opts, tp_opts, fov_opts,
            )
            layout.addWidget(cell["frame"], r, c + 1)
            cell_row.append(cell)
        cells.append(cell_row)

    return cells, row_chan_cbs, row_lut_color_cbs, row_well_cbs


def build_selector_cell(
    r: int, c: int,
    well_opts: List[str], chan_opts: List[str],
    tp_opts: List[str], fov_opts: List[str],
) -> Dict[str, Any]:
    """Build one (row, col) groupbox containing four dropdowns."""
    box = QGroupBox(f"({r + 1}, {c + 1})")
    inner = QVBoxLayout(box)
    inner.setContentsMargins(6, 8, 6, 6)
    inner.setSpacing(2)

    def _row(label_text: str, options: List[str]) -> QComboBox:
        rl = QHBoxLayout()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        lbl = QLabel(label_text, box)
        lbl.setFixedWidth(54)
        rl.addWidget(lbl)
        cb = QComboBox(box)
        cb.addItems(options)
        rl.addWidget(cb, 1)
        inner.addLayout(rl)
        return cb

    well_cb = _row("Well:", well_opts)
    chan_cb = _row("Channel:", chan_opts)
    tp_cb = _row("Timepoint:", tp_opts)
    fov_cb = _row("FOV:", fov_opts)

    return {
        "frame": box,
        "well_cb": well_cb,
        "chan_cb": chan_cb,
        "tp_cb": tp_cb,
        "fov_cb": fov_cb,
    }


def build_lut_row(
    app,
    *,
    chan_opts: List[str],
    on_generate,
    on_auto_lut,
) -> None:
    """Rebuild the per-channel LUT min/max editors below the selector grid."""
    from well_viewer.ui_helpers import btn_secondary, clear_layout

    container = getattr(app, "_image_table_lut_container", None)
    if container is None:
        return
    layout = container.layout()
    clear_layout(layout)

    app._image_table_lut = {}
    for chan in chan_opts:
        chan_box = QGroupBox(chan, container)
        cb_l = QHBoxLayout(chan_box)
        cb_l.setContentsMargins(6, 8, 6, 4)
        cb_l.setSpacing(4)

        cb_l.addWidget(QLabel("min:", chan_box))
        min_edit = QLineEdit("auto", chan_box)
        min_edit.setFixedWidth(70)
        min_edit.editingFinished.connect(lambda: on_generate(app))
        cb_l.addWidget(min_edit)

        cb_l.addWidget(QLabel("max:", chan_box))
        max_edit = QLineEdit("auto", chan_box)
        max_edit.setFixedWidth(70)
        max_edit.editingFinished.connect(lambda: on_generate(app))
        cb_l.addWidget(max_edit)

        auto_btn = btn_secondary(
            chan_box, "Auto",
            lambda c=chan: on_auto_lut(app, c),
        )
        cb_l.addWidget(auto_btn)

        layout.addWidget(chan_box)
        app._image_table_lut[chan] = {"min": min_edit, "max": max_edit}

    layout.addStretch(1)
