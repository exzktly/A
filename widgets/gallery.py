"""widgets/gallery.py — one window showing every custom widget for visual QA.

Run::

    python widgets/gallery.py

Each widget gets a titled card; the whole grid is scrollable. Each card is built
inside a ``try/except`` so one broken widget can't take the gallery down — failed
cards show the traceback instead.
"""

from __future__ import annotations

import os as _os
import sys as _sys
import traceback as _traceback

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import theme  # noqa: E402


def _card(title: str, builder) -> QFrame:
    card = QFrame()
    card.setObjectName("Panel")
    card.setProperty("panel", True)
    card.setAttribute(Qt.WA_StyledBackground, True)
    card.setStyleSheet(
        f"QFrame#Panel {{ background-color: {theme.Colors.panel}; "
        f"border: 1px solid {theme.Colors.border_subtle}; "
        f"border-radius: {theme.Radii.md}px; }}"
    )
    v = QVBoxLayout(card)
    pad = theme.Spacing.md
    v.setContentsMargins(pad, pad, pad, pad)
    v.setSpacing(theme.Spacing.sm)
    cap = QLabel(title)
    cap.setObjectName("Caption")
    cap.setStyleSheet(
        f"color: {theme.Colors.text_muted}; "
        f"font-size: {theme.Typography.caption_size}px; font-weight: {theme.Typography.medium};"
    )
    v.addWidget(cap)
    try:
        body = builder()
    except Exception:  # pragma: no cover - keep the gallery alive
        body = QLabel("⚠ failed to build:\n" + _traceback.format_exc())
        body.setStyleSheet(f"color: {theme.Colors.danger}; font-family: {theme.Typography.family_mono};")
        body.setWordWrap(True)
    if isinstance(body, QWidget):
        v.addWidget(body)
    else:
        # builder may return a layout
        v.addLayout(body)
    v.addStretch(1)
    return card


def _row(*widgets) -> QWidget:
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.sm)
    for w in widgets:
        lay.addWidget(w)
    lay.addStretch(1)
    return host


# ── per-widget builders ─────────────────────────────────────────────────────
def _build_toggle():
    from widgets.toggle_switch import ToggleSwitch
    on = ToggleSwitch(checked=True)
    off = ToggleSwitch()
    dis = ToggleSwitch(checked=True)
    dis.setEnabled(False)
    return _row(QLabel("on"), on, QLabel("off"), off, QLabel("disabled"), dis)


def _build_collapsible():
    from widgets.collapsible_section import CollapsibleSection
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    s1 = CollapsibleSection("Appearance", expanded=True)
    s1.addWidget(QLabel("Trace width"))
    s1.addWidget(QLineEdit("1.6"))
    s2 = CollapsibleSection("Threshold", expanded=False)
    s2.addWidget(QLabel("Cutoff"))
    s2.addWidget(QLineEdit("0.50"))
    v.addWidget(s1)
    v.addWidget(s2)
    return host


def _build_segmented():
    from widgets.segmented_control import SegmentedControl
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    a = SegmentedControl()
    for n in ("All", "Plot 1", "Plot 2"):
        a.addSegment(n)
    b = SegmentedControl()
    for n in ("Line", "Bar", "Scatter", "Dist", "Heat"):
        b.addSegment(n)
    b.setCurrentIndex(2)
    v.addWidget(a)
    v.addWidget(b)
    return host


def _build_chips():
    from widgets.chip_group import ChipGroup
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    single = ChipGroup(exclusive=True)
    for n in ("DAPI", "GFP", "RFP", "Cy5"):
        single.addChip(n)
    single.setCurrentIndex(1)
    multi = ChipGroup(exclusive=False)
    for n in ("Grid", "Threshold", "Legend"):
        multi.addChip(n)
    multi.setChecked(0, True)
    v.addWidget(QLabel("single-select"))
    v.addWidget(single)
    v.addWidget(QLabel("multi-select"))
    v.addWidget(multi)
    return host


def _build_pilltabs():
    from widgets.pill_tab_bar import PillTabBar
    bar = PillTabBar()
    for n in ("Channel 1", "Channel 2"):
        bar.addTab(n)
    bar.addRequested.connect(lambda: bar.setCurrentIndex(bar.addTab(f"Channel {bar.count() + 1}")))
    return bar


def _build_plate():
    from widgets.well_plate_selector import WellPlateSelector
    plate = WellPlateSelector()
    plate.setSelectedWellIds(["A01", "A02", "B01", "C03", "C04", "D06", "H12"])
    return plate


def _build_stepper():
    from widgets.stepper import Stepper
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    si = Stepper(value=8, minimum=1, maximum=96, single_step=1, decimals=0)
    si.setSuffix(" px")
    sf = Stepper(value=0.5, minimum=0.0, maximum=1.0, single_step=0.05, decimals=2)
    v.addWidget(QLabel("integer"))
    v.addWidget(si)
    v.addWidget(QLabel("fraction"))
    v.addWidget(sf)
    return host


def _build_slider():
    from widgets.styled_slider import StyledSlider
    s = StyledSlider()
    s.setRange(0, 100)
    s.setValue(40)
    return s


def _build_iconbar():
    from widgets.icon_button import IconButton
    from PySide6.QtWidgets import QButtonGroup as _BG
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.xs)
    home = IconButton("home", tooltip="Reset")
    pan = IconButton("move", tooltip="Pan", checkable=True)
    zoom = IconButton("zoom-in", tooltip="Zoom", checkable=True)
    save = IconButton("download", tooltip="Export")
    grp = _BG(host)
    grp.setExclusive(True)
    grp.addButton(pan)
    grp.addButton(zoom)
    for b in (home, pan, zoom, save):
        lay.addWidget(b)
    lay.addWidget(IconButton("search", text="Search"))
    lay.addStretch(1)
    return host


def _build_statusdots():
    from widgets.status_dot import StatusDot
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.lg)
    for st in ("success", "warn", "danger", "accent", "neutral"):
        d = StatusDot(st)
        d.setLabel(st)
        lay.addWidget(d)
    lay.addStretch(1)
    return host


def _build_brand():
    from widgets.brand_tile import BrandTile
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.lg)
    for s in (18, 24, 36, 56):
        lay.addWidget(BrandTile(side=s))
    lay.addStretch(1)
    return host


def _build_swatches():
    from widgets.color_swatch_row import ColorSwatchRow
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    v.addWidget(ColorSwatchRow())
    luts = ColorSwatchRow(["#FFFFFF", "#5B9BF8", "#4ADE80", "#F26B6B", "#F5A524"])
    luts.setCurrentIndex(2)
    v.addWidget(luts)
    return host


def _build_search():
    from widgets.search_input import SearchInput
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    v.addWidget(SearchInput(placeholder="Search properties…"))
    v.addWidget(SearchInput(placeholder="Filter wells…", hint=""))
    return host


def _build_empty():
    from widgets.empty_state import EmptyState
    es = EmptyState("No wells selected", icon="grid",
                    hint="Pick wells on the plate to plot.")
    es.setMinimumHeight(180)
    return es


def _build_popover():
    from widgets.popover import Popover
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.Spacing.sm)

    def _content(text):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(theme.Spacing.sm)
        h = QLabel(text)
        h.setObjectName("Heading")
        v.addWidget(h)
        v.addWidget(QLabel("Click outside or press Esc to dismiss."))
        v.addWidget(QPushButton("An action"))
        return w

    for label, side in (("below", "bottom"), ("above", "top"), ("right", "right")):
        b = QPushButton(f"open {label}")
        b.setCursor(Qt.PointingHandCursor)
        pop = Popover(host)
        pop.setContentWidget(_content(f"Popover (side={side})"))
        b.clicked.connect(lambda _=False, _b=b, _p=pop, _s=side: _p.popup(_b, side=_s))
        lay.addWidget(b)
    lay.addStretch(1)
    return host


def _build_saved():
    from widgets.saved_selections_list import SavedSelectionsList
    lst = SavedSelectionsList()
    tr = theme.Colors.trace
    lst.setEntries([
        ("Control", tr[0], 6),
        ("Drug A — 1µM", tr[1], 6),
        ("Drug A — 10µM", tr[2], 6),
        ("Untreated", theme.Colors.text_muted, 3),
    ])
    lst.setCurrentIndex(0)
    lst.setMinimumHeight(150)
    return lst


def _build_hover_overlay():
    from widgets.hover_toolbar_overlay import HoverToolbarOverlay
    card = QFrame()
    card.setObjectName("Panel")
    card.setAttribute(Qt.WA_StyledBackground, True)
    card.setStyleSheet(
        f"QFrame#Panel {{ background-color: {theme.Colors.panel_elevated}; "
        f"border: 1px solid {theme.Colors.border}; border-radius: {theme.Radii.sm}px; }}"
    )
    v = QVBoxLayout(card)
    v.setContentsMargins(theme.Spacing.md, theme.Spacing.md, theme.Spacing.md, theme.Spacing.md)
    body = QLabel("hover me — toolbar reveals")
    body.setAlignment(Qt.AlignCenter)
    body.setMinimumHeight(110)
    v.addWidget(body, 1)
    tb = QWidget()
    tbl = QHBoxLayout(tb)
    tbl.setContentsMargins(0, 0, 0, 0)
    for n in ("Home", "Pan", "Zoom", "Save"):
        tbl.addWidget(QPushButton(n))
    tbl.addStretch(1)
    v.addWidget(tb)
    HoverToolbarOverlay(tb, host=card)
    return card


def _build_plotcard():
    from widgets.plot_card import PlotCard
    if PlotCard is None:
        lbl = QLabel("matplotlib not installed — PlotCard unavailable")
        lbl.setWordWrap(True)
        return lbl
    card = PlotCard(figsize=(4.6, 2.8))
    ax = card.add_subplot(111)
    import math
    xs = [i * 0.1 for i in range(110)]
    for k, color in enumerate(theme.Colors.trace):
        ax.plot(xs, [math.sin(x + k * 0.6) for x in xs], color=color, linewidth=1.5)
    ax.axhline(0.0, color=theme.Colors.threshold, linestyle="--", linewidth=1.0)
    ax.set_title("Signal")
    card.style_axes(ax)
    card.draw()
    card.setMinimumHeight(260)
    return card


def _build_titlebar():
    from widgets.title_bar import TitleBar
    tb = TitleBar(title="All-Well")
    tb.setBreadcrumb(["Workspace", "Plate 7"], file_chip="run_2026-05-12.awd")
    tb.addAction("search", "Search")
    tb.addAction("download", "Export", text="Export")
    return tb


# ── window ──────────────────────────────────────────────────────────────────
def build_gallery() -> QWidget:
    root = QWidget()
    root.setObjectName("AppRoot")
    root.setWindowTitle("All-Well — widget gallery")

    outer = QVBoxLayout(root)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    header = QWidget()
    header.setObjectName("Sidebar")
    header.setAttribute(Qt.WA_StyledBackground, True)
    hl = QHBoxLayout(header)
    hl.setContentsMargins(theme.Spacing.lg, theme.Spacing.md, theme.Spacing.lg, theme.Spacing.md)
    htitle = QLabel("Widget gallery")
    htitle.setObjectName("Title")
    hl.addWidget(htitle)
    hl.addStretch(1)
    # Live demos that need a window host:
    from widgets.toast import Toast
    from widgets.drawer import Drawer
    btn_toast = QPushButton("Toast")
    btn_toast.setObjectName("Primary")
    btn_drawer = QPushButton("Open drawer")
    hl.addWidget(btn_toast)
    hl.addWidget(btn_drawer)
    outer.addWidget(header)

    sep = QFrame()
    sep.setObjectName("Separator")
    sep.setAttribute(Qt.WA_StyledBackground, True)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {theme.Colors.border_subtle};")
    outer.addWidget(sep)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    inner = QWidget()
    grid = QGridLayout(inner)
    pad = theme.Spacing.lg
    grid.setContentsMargins(pad, pad, pad, pad)
    grid.setHorizontalSpacing(theme.Spacing.lg)
    grid.setVerticalSpacing(theme.Spacing.lg)

    cards = [
        ("ToggleSwitch", _build_toggle),
        ("CollapsibleSection", _build_collapsible),
        ("SegmentedControl", _build_segmented),
        ("ChipGroup", _build_chips),
        ("PillTabBar", _build_pilltabs),
        ("Stepper", _build_stepper),
        ("StyledSlider", _build_slider),
        ("IconButton", _build_iconbar),
        ("StatusDot", _build_statusdots),
        ("BrandTile", _build_brand),
        ("ColorSwatchRow", _build_swatches),
        ("SearchInput", _build_search),
        ("EmptyState", _build_empty),
        ("Popover", _build_popover),
        ("HoverToolbarOverlay", _build_hover_overlay),
        ("SavedSelectionsList", _build_saved),
        ("WellPlateSelector", _build_plate),
        ("PlotCard", _build_plotcard),
        ("TitleBar", _build_titlebar),
    ]
    cols = 2
    for i, (title, builder) in enumerate(cards):
        grid.addWidget(_card(title, builder), i // cols, i % cols)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)

    scroll.setWidget(inner)
    outer.addWidget(scroll, 1)

    # Wire the live host-dependent demos.
    btn_toast.clicked.connect(
        lambda: Toast.show_message(root, "Saved layout.awd", kind="success")
    )
    drawer = Drawer(root, width_fraction=0.36)
    drawer_content = QWidget()
    dv = QVBoxLayout(drawer_content)
    dv.setContentsMargins(0, 0, 0, 0)
    dv.setSpacing(theme.Spacing.md)
    h2 = QLabel("Analyze")
    h2.setObjectName("Title")
    dv.addWidget(h2)
    dv.addWidget(QLabel("Input directory:"))
    dv.addWidget(QLineEdit())
    dv.addWidget(QPushButton("Run pipeline"))
    dv.addStretch(1)
    drawer.setContentWidget(drawer_content)
    btn_drawer.clicked.connect(drawer.open)

    return root


def main() -> None:
    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())
    win = build_gallery()
    win.resize(1080, 860)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
