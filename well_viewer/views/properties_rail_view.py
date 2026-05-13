"""Properties rail interior (v2 mockup parity).

Builds the content widget that lives inside the CollapsibleRail on the
Review centre column. Mockup: ``design/mockup-decoded.html`` lines
1690–1955.

Top-down:
  • props-head — title + Save preset / Reset / Collapse IconButtons.
  • Scope ``All / Plot 1 / Plot 2`` SegmentedControl.
  • ``Search properties…`` SearchInput with ``⌘K`` hint.
  • Properties body — a scrollable column of eight CollapsibleSection
    instances:
      Profile & Format / Statistics (Q4 — DESIGN_NOTES §6.2) / Axes /
      Legend / Lines & Markers / Grid / Limits & Scale / Layout.

Phase 12 ships the structure end-to-end and every control widget that
has no host-side state of its own (RangePair, PreviewStrip, chip rows,
SegmentedControls). Sections whose controls bind to the per-figure
pref dict (line width, marker size, etc.) keep their existing routing
via the floating ExportStyleSidebar that the sliders IconButton on
each plot card still opens — re-targeting the rail to the active
figure is Phase 12b.

API
---
* ``build_properties_rail_view(app, parent) -> QWidget``
  Returns the content widget. Caller mounts it on its CollapsibleRail.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QComboBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

import theme  # noqa: E402
from widgets.collapsible_section import CollapsibleSection  # noqa: E402
from widgets.icon_button import IconButton  # noqa: E402
from widgets.preview_strip import PreviewStrip  # noqa: E402
from widgets.range_pair import RangePair  # noqa: E402
from widgets.search_input import SearchInput  # noqa: E402
from widgets.segmented_control import SegmentedControl  # noqa: E402
from widgets.stepper import Stepper  # noqa: E402
from widgets.styled_slider import StyledSlider  # noqa: E402
from widgets.toggle_switch import ToggleSwitch  # noqa: E402


def _row(label: str, control: QWidget, *, label_w: int = 88) -> QWidget:
    """Build a one-row label + control container that matches the mockup's
    ``.row`` style (88-px label column, control fills remainder)."""
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 4, 0, 4)
    lay.setSpacing(theme.Spacing.md)
    lbl = QLabel(label)
    lbl.setFixedWidth(label_w)
    lbl.setStyleSheet(
        f"color: {theme.Colors.text_secondary}; "
        f"font-size: {theme.Typography.small_size}px;"
    )
    lay.addWidget(lbl, 0)
    lay.addWidget(control, 1)
    return host


def _preview_label(text: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {theme.Colors.text_muted}; "
        f"font-family: {theme.Typography.family_mono}; "
        f"font-size: {theme.Typography.caption_size}px;"
    )
    return lbl


def _slider_with_value(*, lo: int, hi: int, default: int, step: int = 1) -> QWidget:
    """A StyledSlider + mono value chip side by side."""
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.sm)
    s = StyledSlider()
    s.setRange(lo, hi)
    s.setValue(default)
    s.setSingleStep(step)
    val = QLabel(str(default))
    val.setFixedWidth(42)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    val.setStyleSheet(
        f"color: {theme.Colors.text_primary}; "
        f"font-family: {theme.Typography.family_mono}; "
        f"font-size: {theme.Typography.small_size}px;"
    )
    s.valueChanged.connect(lambda v: val.setText(str(v)))
    lay.addWidget(s, 1)
    lay.addWidget(val, 0)
    return host


def _chips(*labels: str, default: str | None = None) -> SegmentedControl:
    """A SegmentedControl rendered as a horizontal chip row."""
    seg = SegmentedControl()
    for label in labels:
        seg.addSegment(label, data=label)
    if default is not None:
        seg.setCurrentByData(default)
    return seg


def build_properties_rail_view(app, parent: QWidget) -> QWidget:
    """Return the populated Properties-rail content widget.

    The caller is responsible for mounting it on a ``CollapsibleRail``
    (see ``widgets.collapsible_rail.CollapsibleRail.setContentWidget``).
    """
    host = QWidget(parent)
    host.setObjectName("PropertiesRailContent")
    outer = QVBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    c, t, s = theme.Colors, theme.Typography, theme.Spacing

    # ── props-head ───────────────────────────────────────────────────────
    head = QWidget(host)
    head.setObjectName("PropsHead")
    hl = QHBoxLayout(head)
    hl.setContentsMargins(s.lg, s.md, s.lg, s.sm)
    hl.setSpacing(s.sm)
    sliders_glyph = IconButton("sliders-horizontal")
    sliders_glyph.setEnabled(False)
    hl.addWidget(sliders_glyph)
    title = QLabel("Properties")
    title.setStyleSheet(
        f"color: {c.text_primary}; font-size: {t.h3_size}px; font-weight: 600;"
    )
    hl.addWidget(title)
    hl.addStretch(1)
    head_actions: dict[str, IconButton] = {
        "save_preset": IconButton("bookmark-plus" if False else "plus"),
        "reset":       IconButton("refresh-cw"),
        "collapse":    IconButton("panel-right-close"),
    }
    head_actions["save_preset"].setToolTip("Save current properties as a preset")
    head_actions["reset"].setToolTip("Reset all properties to defaults")
    head_actions["collapse"].setToolTip("Hide the Properties rail")
    for btn in head_actions.values():
        hl.addWidget(btn)
    outer.addWidget(head)

    # Stash for the host's collapse-button to find.
    app._props_rail_head_actions = head_actions

    # ── scope segmented ─────────────────────────────────────────────────
    scope_row = QWidget(host)
    sl = QHBoxLayout(scope_row)
    sl.setContentsMargins(s.lg, 0, s.lg, s.sm)
    sl.setSpacing(s.md)
    scope_lbl = QLabel("Scope")
    scope_lbl.setStyleSheet(
        f"color: {c.text_muted}; font-size: {t.caption_size}px; "
        f"letter-spacing: 0.08em; font-weight: {t.medium};"
    )
    sl.addWidget(scope_lbl, 0)
    app._props_scope_seg = SegmentedControl()
    app._props_scope_seg.addSegment("All", data="all")
    app._props_scope_seg.addSegment("Plot 1", data="plot1")
    app._props_scope_seg.addSegment("Plot 2", data="plot2")
    sl.addWidget(app._props_scope_seg, 1)
    outer.addWidget(scope_row)

    # ── search ──────────────────────────────────────────────────────────
    search_row = QWidget(host)
    sr = QHBoxLayout(search_row)
    sr.setContentsMargins(s.lg, 0, s.lg, s.sm)
    sr.setSpacing(0)
    app._props_search = SearchInput()
    app._props_search.setPlaceholderText("Search properties…")
    try:
        app._props_search.setKbdHint("⌘K")
    except Exception:
        pass
    sr.addWidget(app._props_search, 1)
    outer.addWidget(search_row)

    # ── scroll body ─────────────────────────────────────────────────────
    scroll = QScrollArea(host)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body = QWidget(scroll)
    body.setObjectName("PropertiesBody")
    bl = QVBoxLayout(body)
    bl.setContentsMargins(s.lg, 0, s.lg, s.lg)
    bl.setSpacing(s.sm)

    # ── 1. Profile & Format ─────────────────────────────────────────────
    sec_profile = CollapsibleSection("Profile & Format", expanded=True)
    sec_profile.setValueWidget(_preview_label("Custom · PNG"))
    profile_cb = QComboBox()
    profile_cb.addItems(["Custom", "Publication", "Slide", "Print A4"])
    sec_profile.addWidget(_row("Profile", profile_cb))
    fmt_chips = _chips("PNG", "SVG", "PDF", "TIFF", default="PNG")
    sec_profile.addWidget(_row("Format", fmt_chips))
    bl.addWidget(sec_profile)

    # ── 2. Statistics (Q4 / §6.2) ───────────────────────────────────────
    sec_stats = CollapsibleSection("Statistics", expanded=True)
    sec_stats.setValueWidget(_preview_label("SEM · spread"))
    error_chips = _chips("None", "SEM", "SD", "95% CI", default="SEM")
    sec_stats.addWidget(_row("Error bars", error_chips))
    across_chips = _chips("Replicates", "FOV", default="Replicates")
    sec_stats.addWidget(_row("Across", across_chips))
    show_chips = _chips("Mean", "Mean + spread", "All points", default="Mean + spread")
    sec_stats.addWidget(_row("Show", show_chips))
    bl.addWidget(sec_stats)

    # ── 3. Axes ─────────────────────────────────────────────────────────
    sec_axes = CollapsibleSection("Axes", expanded=False)
    sec_axes.setValueWidget(_preview_label("22 · 22 · 22"))
    for label in ("Axis size", "Tick size", "Title size"):
        sec_axes.addWidget(_row(label, _slider_with_value(lo=6, hi=40, default=22)))
    sec_axes.addWidget(_row("X rotation", _chips("0°", "30°", "45°", "90°", default="0°")))
    sec_axes.addWidget(_row("Tick vis.", _chips("Major", "Minor", "Both", "None", default="Major")))
    sec_axes.addWidget(_row("Tick dir", _chips("In", "Out", "In/Out", default="Out")))
    tick_len = Stepper(minimum=0.0, maximum=20.0, single_step=0.5, value=4.0, decimals=1)
    sec_axes.addWidget(_row("Tick len", tick_len))
    bl.addWidget(sec_axes)

    # ── 4. Legend ───────────────────────────────────────────────────────
    sec_legend = CollapsibleSection("Legend", expanded=False)
    sec_legend.setValueWidget(_preview_label("On · best · 12pt"))
    sec_legend.addWidget(_row("Show legend", ToggleSwitch(checked=True)))
    sec_legend.addWidget(_row("In-plot box", ToggleSwitch(checked=True)))
    legend_sz = Stepper(minimum=6, maximum=24, single_step=1, value=12, decimals=0)
    sec_legend.addWidget(_row("Size", legend_sz))
    legend_loc = QComboBox()
    legend_loc.addItems(["Best", "Upper right", "Upper left", "Lower right",
                         "Lower left", "Outside right"])
    sec_legend.addWidget(_row("Location", legend_loc))
    bl.addWidget(sec_legend)

    # ── 5. Lines & Markers ──────────────────────────────────────────────
    sec_lm = CollapsibleSection("Lines & Markers", expanded=False)
    sec_lm.setValueWidget(_preview_label("· ■ ■"))
    preview = PreviewStrip()
    sec_lm.addWidget(preview)
    sec_lm.addWidget(_row("Line width",
                          _slider_with_value(lo=0, hi=60, default=18)))
    sec_lm.addWidget(_row("Marker size",
                          _slider_with_value(lo=0, hi=28, default=10)))
    me_step = Stepper(minimum=0.0, maximum=5.0, single_step=0.1, value=0.8, decimals=1)
    sec_lm.addWidget(_row("Marker edge", me_step))
    bl.addWidget(sec_lm)
    app._props_preview_strip = preview

    # ── 6. Grid ─────────────────────────────────────────────────────────
    sec_grid = CollapsibleSection("Grid", expanded=False)
    sec_grid.setValueWidget(_preview_label("On · 0.25 · --"))
    sec_grid.addWidget(_row("Show grid", ToggleSwitch(checked=True)))
    sec_grid.addWidget(_row("Opacity",
                            _slider_with_value(lo=0, hi=100, default=25)))
    sec_grid.addWidget(_row("Line style",
                            _chips("—", "- -", "·", "-·", default="- -")))
    bl.addWidget(sec_grid)

    # ── 7. Limits & Scale ───────────────────────────────────────────────
    sec_lim = CollapsibleSection("Limits & Scale", expanded=False)
    sec_lim.setValueWidget(_preview_label("auto · auto"))
    sec_lim.addWidget(_row("X limits",
                           RangePair(separator="–", placeholder=("auto", "auto"))))
    sec_lim.addWidget(_row("Y limits",
                           RangePair(separator="–", placeholder=("auto", "auto"))))
    sec_lim.addWidget(_row("X log", ToggleSwitch()))
    sec_lim.addWidget(_row("Y log", ToggleSwitch()))
    bl.addWidget(sec_lim)

    # ── 8. Layout ───────────────────────────────────────────────────────
    sec_layout = CollapsibleSection("Layout", expanded=False)
    sec_layout.setValueWidget(_preview_label("Constrained"))
    sec_layout.addWidget(_row("Spacing",
                              _chips("Tight", "Constrained", "Manual",
                                     default="Constrained")))
    well_order = QComboBox()
    well_order.addItems(["Plate order", "Selection order", "Custom…"])
    sec_layout.addWidget(_row("Well order", well_order))
    sec_layout.addWidget(_row("Aspect",
                              RangePair(separator="×",
                                        value=("1.618", "1.000"))))
    bl.addWidget(sec_layout)

    bl.addStretch(1)
    scroll.setWidget(body)
    outer.addWidget(scroll, 1)

    host.setStyleSheet(
        f"#PropertiesRailContent {{ background-color: {c.rail}; }}"
        f"#PropsHead {{ background-color: {c.rail}; "
        f"border-bottom: 1px solid {c.border_subtle}; }}"
        f"#PropertiesBody {{ background-color: {c.rail}; }}"
    )

    return host
