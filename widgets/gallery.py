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
    cust = ColorSwatchRow(allow_custom=True, recents=["#9B59B6", "#1ABC9C", "#E67E22"])
    cust.setCurrentColor("#9B59B6")
    v.addWidget(cust)
    out = QLabel("(curated · recents · Custom tile → picker)")
    out.setObjectName("Caption")
    v.addWidget(out)
    cust.colorPicked.connect(lambda c: out.setText(f"picked: {c.name().upper()}"))
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


def _build_gradient_strip():
    from PySide6.QtGui import QColor
    from widgets.gradient_strip import GradientStrip
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    g1 = GradientStrip([(0.0, theme.Colors.surface), (0.5, theme.Colors.accent),
                        (1.0, theme.Colors.accent_fg)])      # (pos, colour) stops
    g1.setMinimumHeight(16)
    g2 = GradientStrip(list(theme.Colors.trace))             # evenly-spaced flat list
    g2.setMinimumHeight(16)
    g3 = GradientStrip(reversed=False)                       # sampled from a callable
    g3.setMinimumHeight(16)
    g3.setSamples(lambda t: QColor.fromHsvF(max(0.0, min(0.999, 0.75 - 0.75 * t)),
                                            0.6, 0.35 + 0.55 * t))
    for w in (g1, g2, g3):
        v.addWidget(w)
    return host


def _build_window_resize_grips():
    from widgets.window_resize_grips import WindowResizeGrips
    from PySide6.QtWidgets import QMainWindow
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    lbl = QLabel("A frameless window helper — can't be embedded here. "
                 "Open a test window to drag its edges/corners:")
    lbl.setWordWrap(True)
    v.addWidget(lbl)
    btn = QPushButton("Open frameless test window")
    btn.setObjectName("Primary")
    v.addWidget(btn, 0, Qt.AlignLeft)
    holder = {"win": None}

    def _open():
        if holder["win"] is not None and holder["win"].isVisible():
            holder["win"].raise_(); holder["win"].activateWindow(); return
        w = QMainWindow()
        w.setWindowFlag(Qt.FramelessWindowHint, True)
        w.setMinimumSize(260, 160)
        c = QWidget()
        cv = QVBoxLayout(c)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setAttribute(Qt.WA_StyledBackground, True)
        bbl = QHBoxLayout(bar)
        bbl.setContentsMargins(theme.Spacing.md, theme.Spacing.sm, theme.Spacing.sm, theme.Spacing.sm)
        bbl.addWidget(QLabel("drag title to move · drag edges to resize"))
        bbl.addStretch(1)
        cb = QPushButton("✕")
        cb.clicked.connect(w.close)
        bbl.addWidget(cb)
        drag = {"o": None}
        bar.mousePressEvent = (lambda e: (w.windowHandle() and w.windowHandle().startSystemMove())
                               if e.button() == Qt.LeftButton else None)
        cv.addWidget(bar)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(theme.Spacing.lg, theme.Spacing.lg, theme.Spacing.lg, theme.Spacing.lg)
        iv.addWidget(QLabel("Hover the 4 edges / 4 corners → resize cursor; drag to resize."))
        iv.addStretch(1)
        cv.addWidget(inner, 1)
        w.setCentralWidget(c)
        w._grips = WindowResizeGrips(w, mode="auto", margin=8)   # keep a ref alive
        w.resize(420, 260)
        w.show()
        holder["win"] = w

    btn.clicked.connect(_open)
    return host


def _build_lut_selector():
    from widgets.lut_selector import LutSelector
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    sel = LutSelector(lut="viridis")
    v.addWidget(sel)
    out = QLabel("lut: viridis  (reversed=False)")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
    sel.lutChanged.connect(lambda name, rev: out.setText(f"lut: {name}  (reversed={rev})"))
    v.addStretch(1)
    return host


def _build_color_picker_popover():
    from PySide6.QtGui import QColor
    from widgets.color_picker_popover import ColorPickerPopover
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    btn = QPushButton("Pick a colour…")
    btn.setObjectName("Primary")
    v.addWidget(btn, 0, Qt.AlignLeft)
    swatch = QLabel()
    swatch.setFixedHeight(28)
    swatch.setAttribute(Qt.WA_StyledBackground, True)
    out = QLabel("#6B8AFD")
    out.setObjectName("Caption")

    def _paint(c: QColor):
        swatch.setStyleSheet(
            f"background-color: {c.name()}; border: 1px solid {theme.Colors.border}; "
            f"border-radius: {theme.Radii.xs}px;")
        out.setText(c.name().upper())

    _paint(QColor("#6B8AFD"))
    v.addWidget(swatch)
    v.addWidget(out)
    v.addStretch(1)
    pop = ColorPickerPopover(host, color="#6B8AFD")
    pop.colorPicked.connect(_paint)
    pop.colorCommitted.connect(_paint)
    btn.clicked.connect(lambda: pop.popup(btn, side="bottom", align="start"))
    return host


def _build_saved():
    from widgets.saved_selections_list import SavedSelectionsList
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    lst = SavedSelectionsList()
    tr = theme.Colors.trace
    lst.setSelections([
        {"id": "aaaa1111", "name": "Control", "color": tr[0], "hidden": False,
         "wells": ["A01", "A02", "A03", "B01", "B02", "B03"],
         "replicates": [["A01", "A02", "A03"], ["B01", "B02", "B03"]], "source": "bar_group"},
        {"id": "bbbb2222", "name": "Drug A — 1µM", "color": tr[1], "hidden": False,
         "wells": ["C01", "C02", "C03"], "replicates": [["C01", "C02", "C03"]], "source": "rep_set"},
        {"id": "cccc3333", "name": "Drug A — 10µM", "color": tr[2], "hidden": False,
         "wells": ["D01", "D02", "D03"], "replicates": None, "source": "user"},
        {"id": "dddd4444", "name": "Untreated", "color": theme.Colors.text_muted, "hidden": True,
         "wells": ["E01", "E02"], "replicates": None, "source": "import"},
    ])
    lst.setCurrentId("bbbb2222")
    lst.setMinimumHeight(220)
    v.addWidget(lst, 1)
    out = QLabel("(rename · recolour · reorder via handle/kebab · hide · expand)")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
    lst.selectionsChanged.connect(
        lambda items: out.setText("order: " + " · ".join(i["name"] for i in items)))
    return host


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
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    card = PlotCard(figsize=(4.6, 2.8))
    card.setFigureTitle("Signal")
    import math
    xs = [i * 0.1 for i in range(110)]

    def _plot():
        card.figure.clear()
        ax = card.add_subplot(111)
        for k, color in enumerate(card.traceColors()):
            ax.plot(xs, [math.sin(x + k * 0.6) for x in xs], color=color, linewidth=1.5)
        ax.axhline(0.0, color=theme.Colors.threshold, linestyle="--", linewidth=1.0)
        card.style_axes(ax)
        card.draw()

    _plot()
    card.setMinimumHeight(240)
    v.addWidget(card, 1)
    row = QHBoxLayout()
    row.setSpacing(theme.Spacing.sm)
    btn = QPushButton("Toggle screen / publication")
    btn.clicked.connect(lambda: (card.setPlotTheme(
        "publication" if card.plotTheme() == "screen" else "screen"), _plot()))
    row.addWidget(btn)
    row.addStretch(1)
    v.addLayout(row)
    out = QLabel("(stats chip → popover · screen/publication theme)")
    out.setObjectName("Caption")
    v.addWidget(out)
    card.statsChanged.connect(lambda s, e: out.setText(f"stats → {s} · {e}"))
    card.plotThemeChanged.connect(lambda m: out.setText(f"plot theme → {m}"))
    return host


def _build_titlebar():
    from widgets.title_bar import TitleBar
    from widgets import _window_chrome
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    tb = TitleBar(title="All-Well", frameless=True)
    tb.setBreadcrumb(["Workspace", "Plate 7"], file_chip="run_2026-05-12.awd")
    tb.setRecentFiles(["run_2026-05-12.awd", "plate6.awd", "screen-A.awd"])
    tb.addAction("search", "Search")
    tb.addAction("download", "Export", text="Export")
    v.addWidget(tb)
    out = QLabel(f"should_use_frameless() = {_window_chrome.should_use_frameless()}  "
                 f"(source: {_window_chrome.frameless_source()})  ·  brand → menu  ·  "
                 f"sun → theme popover  ·  ⌘O = Open")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
    row = QHBoxLayout()
    row.setSpacing(theme.Spacing.sm)
    tgl = QPushButton("Toggle frameless / native sub-strip")
    tgl.clicked.connect(lambda: (tb.setFramelessMode(not tb.isFramelessMode()),
                                 out.setText(f"frameless mode = {tb.isFramelessMode()}")))
    row.addWidget(tgl)
    row.addStretch(1)
    v.addLayout(row)
    for sig, name in ((tb.openRequested, "openRequested"),
                      (tb.preferencesRequested, "preferencesRequested"),
                      (tb.aboutRequested, "aboutRequested"),
                      (tb.quitRequested, "quitRequested")):
        sig.connect(lambda n=name: out.setText(f"signal: {n}"))
    tb.recentFileRequested.connect(lambda p: out.setText(f"recent: {p}"))
    tb.themeChangeRequested.connect(lambda k: out.setText(f"theme → {k}"))
    tb.highContrastToggled.connect(lambda on: out.setText(f"high-contrast → {on}"))
    return host


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
        ("GradientStrip", _build_gradient_strip),
        ("WindowResizeGrips", _build_window_resize_grips),
        ("LutSelector", _build_lut_selector),
        ("ColorPickerPopover", _build_color_picker_popover),
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
