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


# ── Phase 12b: rail → active-figure binding pipeline ─────────────────────
def _bind_to_prefs(app, key: str, getter, setter, change_signal):
    """Connect a rail widget to ``app._export_style_prefs[key]``.

    The rail is the single source of truth at the UX layer; the existing
    per-figure ``_export_style_prefs`` is the single source of truth at the
    model layer. Writes go through ``apply_export_style_to_current`` on
    whichever PlotCard is currently visible, mirroring the floating
    ExportStyleSidebar's behaviour.
    """
    from well_viewer.figure_export_editor import (
        _ensure_export_style_prefs, apply_export_style_to_current,
    )

    def _initial():
        prefs = _ensure_export_style_prefs(app)
        if key in prefs:
            try:
                setter(prefs[key])
            except Exception:
                pass

    _initial()

    # Prefs that only matter at save time — changing them shouldn't trigger
    # a figure redraw / rescale on the live canvas. Adding ``format`` here
    # fixes the bug where clicking PNG/SVG/PDF/TIFF re-rendered the plot.
    _SAVE_ONLY_KEYS = {"format", "export_profile"}

    def _on_change(*_args):
        prefs = _ensure_export_style_prefs(app)
        try:
            prefs[key] = getter()
        except Exception:
            return
        if key in _SAVE_ONLY_KEYS:
            return
        # Apply to whichever PlotCard is currently visible. Each renderer
        # also has a per-card sidebar that mirrors the same prefs dict;
        # we just re-use the existing apply_export_style_to_current entry
        # point so both stay in sync.
        for attr in ("_line_card", "_bar_card", "_scatter_card",
                     "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
            card = getattr(app, attr, None)
            if card is None or not card.isVisible():
                continue
            try:
                apply_export_style_to_current(app, card.figure, card.canvas)
            except Exception:
                pass
            break

    change_signal.connect(_on_change)


def _slider_pref(app, key: str, *, lo: int, hi: int, default: int, scale: float = 1.0,
                 default_fmt: str = "{:.0f}") -> QWidget:
    """A StyledSlider + numeric chip pair bound to ``_export_style_prefs[key]``.

    ``scale`` lets the prefs value differ from the slider's integer range
    (e.g. slider 0–60 with scale=0.1 stores 0.0–6.0). ``default_fmt`` is
    the format string for the side chip.
    """
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.sm)
    s = StyledSlider()
    s.setRange(lo, hi)
    s.setValue(default)
    val = QLabel(default_fmt.format(default * scale))
    val.setFixedWidth(48)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    val.setStyleSheet(
        f"color: {theme.Colors.text_primary}; "
        f"font-family: {theme.Typography.family_mono}; "
        f"font-size: {theme.Typography.small_size}px;"
    )
    s.valueChanged.connect(lambda v: val.setText(default_fmt.format(v * scale)))
    lay.addWidget(s, 1)
    lay.addWidget(val, 0)
    _bind_to_prefs(
        app, key,
        getter=lambda: s.value() * scale,
        setter=lambda v: s.setValue(int(round(float(v) / scale))),
        change_signal=s.valueChanged,
    )
    return host


def _toggle_pref(app, key: str, *, default: bool = False) -> ToggleSwitch:
    sw = ToggleSwitch(checked=default)
    _bind_to_prefs(
        app, key,
        getter=lambda: sw.isChecked(),
        setter=lambda v: sw.setChecked(bool(v)),
        change_signal=sw.toggled,
    )
    return sw


def _chips_pref(app, key: str, *labels: str, default: str | None = None,
                value_map: dict[str, object] | None = None) -> SegmentedControl:
    seg = SegmentedControl()
    fwd = value_map or {}
    inv = {v: k for k, v in fwd.items()} if value_map else {}
    for label in labels:
        seg.addSegment(label, data=fwd.get(label, label))
    if default is not None:
        seg.setCurrentByData(fwd.get(default, default))
    _bind_to_prefs(
        app, key,
        getter=lambda: seg.currentData(),
        setter=lambda v: seg.setCurrentByData(v),
        change_signal=seg.currentChanged,
    )
    return seg


def _stepper_pref(app, key: str, *, lo: float, hi: float, step: float,
                  default: float, decimals: int) -> Stepper:
    st = Stepper(minimum=lo, maximum=hi, single_step=step,
                 value=default, decimals=decimals)
    _bind_to_prefs(
        app, key,
        getter=lambda: st.value(),
        setter=lambda v: st.setValue(float(v)),
        change_signal=st.valueChanged,
    )
    return st


def _combo_pref(app, key: str, items: list[str], *,
                default: str | None = None) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    if default and default in items:
        cb.setCurrentText(default)
    _bind_to_prefs(
        app, key,
        getter=lambda: cb.currentText(),
        setter=lambda v: cb.setCurrentText(str(v)),
        change_signal=cb.currentTextChanged,
    )
    return cb


def _range_pair_pref(app, low_key: str, high_key: str, *,
                     separator: str = "–",
                     placeholder: tuple[str, str] = ("", "")) -> RangePair:
    rp = RangePair(separator=separator, placeholder=placeholder)
    # Two separate bindings — but RangePair emits one valueChanged for both
    # halves, so we route both writes from the same signal.
    from well_viewer.figure_export_editor import (
        _ensure_export_style_prefs, apply_export_style_to_current,
    )

    def _initial():
        prefs = _ensure_export_style_prefs(app)
        rp.setValue(str(prefs.get(low_key, "")), str(prefs.get(high_key, "")))

    _initial()

    def _on_changed(lo: str, hi: str):
        prefs = _ensure_export_style_prefs(app)
        prefs[low_key] = lo
        prefs[high_key] = hi
        for attr in ("_line_card", "_bar_card", "_scatter_card",
                     "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
            card = getattr(app, attr, None)
            if card is None or not card.isVisible():
                continue
            try:
                apply_export_style_to_current(app, card.figure, card.canvas)
            except Exception:
                pass
            break

    rp.valueChanged.connect(_on_changed)
    return rp


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


# Maps every plotting sub-tab to the names of its subplots (top → bottom).
# Single-subplot renderers list one entry; the scope row then collapses to
# just ``All`` (or hides entirely depending on how the caller wants it).
_PLOT_SUBPLOTS: dict[str, list[str]] = {
    "Line Graphs":  ["Mean", "Fraction", "CDF"],
    "Bar Plots":    ["Mean", "Fraction", "n above"],
    "Scatter Plot": ["Scatter"],
    "Distribution": ["Distribution"],
    "Heat Map":     ["Heat map"],
}


def set_properties_rail_scope(app, renderer: str) -> None:
    """Repopulate the Properties rail scope SegmentedControl for *renderer*.

    Drops the legacy fixed ``All / Plot 1 / Plot 2`` segments in favour of
    the actual subplot names for the active renderer (e.g. line graphs
    expose Mean / Fraction / CDF). Single-axes views collapse to a single
    ``All`` segment and the row stays present but compact.
    """
    seg = getattr(app, "_props_scope_seg", None)
    row = getattr(app, "_props_scope_row", None)
    if seg is None:
        return
    subplots = _PLOT_SUBPLOTS.get(renderer, [])
    blocked = seg.blockSignals(True)
    try:
        # Tear down the old segments by replacing the contained QButtonGroup
        # buttons. SegmentedControl doesn't expose a public clear() so we
        # iterate its internal _buttons list (created in __init__).
        for btn in list(getattr(seg, "_buttons", []) or []):
            seg._group.removeButton(btn)
            btn.setParent(None)
            btn.deleteLater()
        seg._buttons = []
        seg._data = []
        seg._current = -1
        if len(subplots) <= 1:
            seg.addSegment("All", data="all")
        else:
            seg.addSegment("All", data="all")
            for name in subplots:
                seg.addSegment(name, data=name)
        seg.setCurrentIndex(0)
    finally:
        seg.blockSignals(blocked)
    if row is not None:
        # Hide the entire scope row when there's nothing meaningful to
        # pick — single-axes renderers like Scatter / Distribution /
        # Heat Map shouldn't clutter the rail with a useless "All".
        row.setVisible(len(subplots) > 1)


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
    # Seed with a single "All" segment; ``set_properties_rail_scope`` (called
    # by centre_view._on_plotting_subtab) repopulates this with the active
    # renderer's actual subplot names — e.g. ``All / Mean / Fraction / CDF``
    # for the line tab, or just ``All`` for single-axes views like scatter.
    app._props_scope_seg.addSegment("All", data="all")
    sl.addWidget(app._props_scope_seg, 1)
    app._props_scope_row = scope_row
    app._props_scope_label = scope_lbl
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
    profile_cb = _combo_pref(app, "export_profile",
                             ["Custom", "Publication", "Slide", "Print A4"],
                             default="Custom")
    sec_profile.addWidget(_row("Profile", profile_cb))
    fmt_chips = _chips_pref(
        app, "format", "PNG", "SVG", "PDF", "TIFF", default="PNG",
        value_map={"PNG": "png", "SVG": "svg", "PDF": "pdf", "TIFF": "tiff"},
    )
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
    sec_axes.addWidget(_row("Axis size",  _slider_pref(app, "axis_label_size",
                                                       lo=6, hi=40, default=22)))
    sec_axes.addWidget(_row("Tick size",  _slider_pref(app, "tick_label_size",
                                                       lo=6, hi=40, default=22)))
    sec_axes.addWidget(_row("Title size", _slider_pref(app, "title_size",
                                                       lo=6, hi=40, default=22)))
    sec_axes.addWidget(_row("X rotation", _chips_pref(
        app, "x_tick_angle", "0°", "30°", "45°", "90°", default="0°",
        value_map={"0°": 0, "30°": 30, "45°": 45, "90°": 90},
    )))
    sec_axes.addWidget(_row("Tick dir", _chips_pref(
        app, "tick_direction", "In", "Out", "In/Out", default="Out",
        value_map={"In": "in", "Out": "out", "In/Out": "inout"},
    )))
    tick_len = _stepper_pref(app, "tick_length",
                             lo=0.0, hi=20.0, step=0.5, default=4.0, decimals=1)
    sec_axes.addWidget(_row("Tick len", tick_len))
    bl.addWidget(sec_axes)

    # ── 4. Legend ───────────────────────────────────────────────────────
    sec_legend = CollapsibleSection("Legend", expanded=False)
    sec_legend.setValueWidget(_preview_label("On · best · 12pt"))
    sec_legend.addWidget(_row("Show legend", _toggle_pref(app, "legend_show", default=True)))
    sec_legend.addWidget(_row("Size", _stepper_pref(
        app, "legend_font_size", lo=6, hi=24, step=1, default=12, decimals=0,
    )))
    sec_legend.addWidget(_row("Location", _combo_pref(
        app, "legend_loc",
        ["best", "upper right", "upper left", "lower right",
         "lower left", "center right"],
        default="best",
    )))
    bl.addWidget(sec_legend)

    # ── 5. Lines & Markers ──────────────────────────────────────────────
    sec_lm = CollapsibleSection("Lines & Markers", expanded=False)
    sec_lm.setValueWidget(_preview_label("· ■ ■"))
    preview = PreviewStrip()
    sec_lm.addWidget(preview)

    # Line width + Marker size + Marker edge — all bound to prefs and
    # live-mirroring into the inline PreviewStrip (B17).
    lw_row = _slider_pref(app, "line_width", lo=0, hi=60, default=18,
                          scale=0.1, default_fmt="{:.2f}")
    sec_lm.addWidget(_row("Line width", lw_row))
    ms_row = _slider_pref(app, "marker_size", lo=0, hi=28, default=10,
                          scale=0.5, default_fmt="{:.2f}")
    sec_lm.addWidget(_row("Marker size", ms_row))
    me_step = _stepper_pref(app, "marker_edge_width",
                            lo=0.0, hi=5.0, step=0.1, default=0.8, decimals=1)
    sec_lm.addWidget(_row("Marker edge", me_step))

    # Wire PreviewStrip live-update — read the current prefs after each
    # rail-driven write and reflect into the inline preview.
    from well_viewer.figure_export_editor import _ensure_export_style_prefs as _ensure
    def _refresh_preview(*_):
        prefs = _ensure(app)
        preview.setStyle(
            line_width=prefs.get("line_width", 1.8),
            marker_size=prefs.get("marker_size", 5.0),
            marker_edge=prefs.get("marker_edge_width", 0.8),
        )
    # Hook every interesting signal we already know about.
    for child in lw_row.findChildren(StyledSlider) + ms_row.findChildren(StyledSlider):
        child.valueChanged.connect(_refresh_preview)
    me_step.valueChanged.connect(_refresh_preview)
    _refresh_preview()

    bl.addWidget(sec_lm)
    app._props_preview_strip = preview

    # ── 6. Grid ─────────────────────────────────────────────────────────
    sec_grid = CollapsibleSection("Grid", expanded=False)
    sec_grid.setValueWidget(_preview_label("On · 0.25 · --"))
    sec_grid.addWidget(_row("Show grid", _toggle_pref(app, "grid_show", default=True)))
    sec_grid.addWidget(_row("Opacity",
                            _slider_pref(app, "grid_alpha",
                                         lo=0, hi=100, default=25,
                                         scale=0.01, default_fmt="{:.2f}")))
    sec_grid.addWidget(_row("Line style", _chips_pref(
        app, "grid_style", "—", "- -", "·", "-·", default="- -",
        value_map={"—": "-", "- -": "--", "·": ":", "-·": "-."},
    )))
    bl.addWidget(sec_grid)

    # ── 7. Limits & Scale ───────────────────────────────────────────────
    sec_lim = CollapsibleSection("Limits & Scale", expanded=False)
    sec_lim.setValueWidget(_preview_label("auto · auto"))
    sec_lim.addWidget(_row("X limits", _range_pair_pref(
        app, "x_lim_min", "x_lim_max", separator="–", placeholder=("auto", "auto"),
    )))
    sec_lim.addWidget(_row("Y limits", _range_pair_pref(
        app, "y_lim_min", "y_lim_max", separator="–", placeholder=("auto", "auto"),
    )))
    sec_lim.addWidget(_row("X log", _toggle_pref(app, "x_log")))
    sec_lim.addWidget(_row("Y log", _toggle_pref(app, "y_log")))
    bl.addWidget(sec_lim)

    # ── 8. Layout ───────────────────────────────────────────────────────
    sec_layout = CollapsibleSection("Layout", expanded=False)
    sec_layout.setValueWidget(_preview_label("Constrained"))
    # Spacing chips drive two booleans (tight / constrained) that the
    # existing apply_export_style_prefs reads.
    spacing = SegmentedControl()
    for label in ("Tight", "Constrained", "Manual"):
        spacing.addSegment(label, data=label.lower())
    spacing.setCurrentByData("constrained")

    def _on_spacing(_idx):
        from well_viewer.figure_export_editor import (
            _ensure_export_style_prefs, apply_export_style_to_current,
        )
        prefs = _ensure_export_style_prefs(app)
        which = spacing.currentData()
        prefs["layout_tight"] = (which == "tight")
        prefs["layout_constrained"] = (which == "constrained")
        for attr in ("_line_card", "_bar_card", "_scatter_card",
                     "_scatter_agg_card", "_distribution_card", "_heatmap_card"):
            card = getattr(app, attr, None)
            if card is None or not card.isVisible():
                continue
            try:
                apply_export_style_to_current(app, card.figure, card.canvas)
            except Exception:
                pass
            break

    spacing.currentChanged.connect(_on_spacing)
    sec_layout.addWidget(_row("Spacing", spacing))
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
