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


def _card(title: str, builder, note: str | None = None) -> QFrame:
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
    if note:
        n = QLabel(note)
        n.setWordWrap(True)
        n.setStyleSheet(f"color: {theme.Colors.text_faint}; font-size: {theme.Typography.caption_size}px;")
        v.addWidget(n)
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


def _section(title: str) -> QWidget:
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, theme.Spacing.sm, 0, theme.Spacing.xs)
    v.setSpacing(theme.Spacing.xs)
    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        f"color: {theme.Colors.text_secondary}; font-size: {theme.Typography.caption_size}px; "
        f"font-weight: {theme.Typography.semibold}; letter-spacing: 1px;"
    )
    v.addWidget(lbl)
    rule = QFrame()
    rule.setFixedHeight(1)
    rule.setAttribute(Qt.WA_StyledBackground, True)
    rule.setStyleSheet(f"background-color: {theme.Colors.border_subtle};")
    v.addWidget(rule)
    return host


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
    lst.setEnabledWells([f"{r}{c:02d}" for r in "ABCDEFGH" for c in range(1, 13)])
    lst.setComposable(True)
    tr = theme.Colors.trace
    lst.setSelections([
        {"id": "aaaa1111", "name": "Control", "color": tr[0], "hidden": False,
         "wells": ["A01", "A02", "A03", "B01", "B02", "B03", "C03"],
         "replicates": [["A01", "A02", "A03"], ["B01", "B02", "B03"]], "source": "bar_group"},
        {"id": "bbbb2222", "name": "Drug A — 1µM", "color": tr[1], "hidden": False,
         "wells": ["C01", "C02", "C03"], "replicates": [["C01", "C02", "C03"]], "source": "rep_set"},
        {"id": "cccc3333", "name": "Drug A — 10µM", "color": tr[2], "hidden": False,
         "wells": ["D01", "D02", "D03"], "replicates": None, "source": "user"},
        {"id": "dddd4444", "name": "Untreated", "color": theme.Colors.text_muted, "hidden": True,
         "wells": ["E01", "E02"], "replicates": None, "source": "import"},
    ])
    lst.setCurrentId("bbbb2222")
    lst.setMinimumHeight(240)
    v.addWidget(lst, 1)
    row = QHBoxLayout()
    row.setSpacing(theme.Spacing.sm)
    from PySide6.QtWidgets import QCheckBox
    cb = QCheckBox("composable")
    cb.setChecked(True)
    cb.toggled.connect(lst.setComposable)
    row.addWidget(cb)
    row.addStretch(1)
    v.addLayout(row)
    out = QLabel("(composable: expand a row → edit chips / replicates / + wells…)")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
    lst.selectionsChanged.connect(
        lambda items: out.setText("order: " + " · ".join(i["name"] for i in items)))
    lst.wellsChanged.connect(lambda i, w: out.setText(f"wells[{i}] → {w}"))
    lst.replicatesChanged.connect(lambda i, r: out.setText(f"replicates[{i}] → {r}"))
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

    # per-card view-switcher (left header slot) + error-band controls row
    try:
        from widgets.plot_card import _make_segmented
        view_sc = _make_segmented([("Line", "line"), ("Bar", "bar"), ("Scatter", "scatter"),
                                   ("Dist", "dist"), ("Heat", "heat")], current="line")
        if view_sc is not None:
            card.setLeftHeaderWidget(view_sc)
        ctrls = QWidget()
        cl = QHBoxLayout(ctrls); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(theme.Spacing.sm)
        cl.addWidget(QLabel("Across:"))
        cl.addWidget(_make_segmented([("Replicates", "rep"), ("FOV", "fov")], current="rep"))
        cl.addWidget(QLabel("Error:"))
        cl.addWidget(_make_segmented([("SEM", "SEM"), ("SD", "SD"), ("None", "None")], current="SEM"))
        card.setControlsWidget(ctrls)
    except Exception:
        pass
    _plot()
    card.setMinimumHeight(240)
    v.addWidget(card, 1)
    out = QLabel("(view-switcher in the left header slot · controls row beneath · header Publication↔Screen toggle + 'preview only' chip · stats chip → popover)")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
    card.statsChanged.connect(lambda s, e: out.setText(f"stats → {s} · {e}"))
    card.plotThemeChanged.connect(lambda m: (_plot(), out.setText(f"plot theme → {m}")))
    return host


def _build_mpl_toolbar():
    from widgets.mpl_toolbar import MplToolbar
    if MplToolbar is None:
        lbl = QLabel("matplotlib not installed — MplToolbar unavailable")
        lbl.setWordWrap(True)
        return lbl
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FC
    from matplotlib.figure import Figure as _F
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    fig = _F(figsize=(4.6, 2.4), layout="constrained")
    ax = fig.add_subplot(111)
    import math
    xs = [i * 0.1 for i in range(110)]
    ax.plot(xs, [math.sin(x) for x in xs], color=theme.Colors.trace[0], linewidth=1.5)
    ax.set_xlabel("x"); ax.set_ylabel("sin x")
    canvas = _FC(fig)
    canvas.setMinimumHeight(180)
    v.addWidget(canvas, 1)
    v.addWidget(MplToolbar(canvas))
    out = QLabel("(home · back/fwd · pan/zoom · save — drives a hidden NavigationToolbar2QT; live x/y readout)")
    out.setObjectName("Caption")
    out.setWordWrap(True)
    v.addWidget(out)
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


# ── Phase 9 reconciliation widgets ───────────────────────────────────────
def _build_kbd_hint():
    from widgets.kbd_hint import KbdHint
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    row = QHBoxLayout()
    row.setSpacing(theme.Spacing.xs)
    for k in ("⌘O", "⌘K", "⌘E", "⌥⇧A"):
        row.addWidget(KbdHint(k))
    row.addStretch(1)
    v.addLayout(row)
    btn = QPushButton("Open")
    btn.setProperty("variant", "primary")
    v.addWidget(KbdHint.attach(btn, "⌘O"))
    from widgets.icon_button import IconButton
    ib = IconButton("folder-open")
    ib.setText("  Open")
    v.addWidget(ib.setKbdHint("⌘O"))
    v.addStretch(1)
    return host


def _build_selection_chip():
    from widgets.selection_chip import SelectionChip
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    r1 = QHBoxLayout(); r1.setSpacing(theme.Spacing.sm)
    r1.addWidget(SelectionChip("2 / 96", icon="check", variant="accent"))
    r1.addWidget(SelectionChip("12 / 96", icon="check", variant="accent"))
    r1.addWidget(SelectionChip("96 / 96", icon="check", variant="accent"))
    r1.addStretch(1)
    v.addLayout(r1)
    r2 = QHBoxLayout(); r2.setSpacing(theme.Spacing.sm)
    r2.addWidget(QLabel("Saved"))
    r2.addWidget(SelectionChip("3", variant="muted"))
    r2.addSpacing(20)
    r2.addWidget(QLabel("Recent"))
    r2.addWidget(SelectionChip("12", variant="muted"))
    r2.addStretch(1)
    v.addLayout(r2)
    return host


def _build_range_pair():
    from widgets.range_pair import RangePair
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    out = QLabel("(edit a field, press Enter or Tab)")
    out.setStyleSheet(f"color: {theme.Colors.text_muted};")
    rp1 = RangePair(separator="–", placeholder=("auto", "auto"))
    rp2 = RangePair(separator="–", value=("0", "1200"))
    rp3 = RangePair(separator="×", value=("1.618", "1.000"))
    for label, rp in (("X limits", rp1), ("Y limits", rp2), ("Aspect", rp3)):
        row = QHBoxLayout()
        lbl = QLabel(label); lbl.setFixedWidth(76)
        row.addWidget(lbl); row.addWidget(rp, 1)
        v.addLayout(row)
        rp.valueChanged.connect(
            lambda lo, hi, n=label: out.setText(f"{n} → ({lo!r}, {hi!r})")
        )
    v.addWidget(out)
    return host


def _build_rail_nav():
    from widgets.rail_nav import RailNav
    host = QWidget()
    host.setObjectName("RailNavDemoHost")
    host.setStyleSheet(
        f"#RailNavDemoHost {{ background-color: {theme.Colors.bg_rail}; "
        f"border-radius: {theme.Radii.sm}px; }}"
    )
    v = QVBoxLayout(host)
    v.setContentsMargins(8, 8, 8, 8)
    v.setSpacing(theme.Spacing.xs)
    head = QLabel("SECTION")
    head.setStyleSheet(
        f"color: {theme.Colors.text_muted}; font-size: 11px; "
        f"letter-spacing: 0.08em; font-weight: 600; padding-left: 9px;"
    )
    v.addWidget(head)
    nav = RailNav(host)
    nav.addItem("Plotting",           icon="line-chart")
    nav.addItem("smFISH",             icon="dna")
    nav.addItem("Statistics",         icon="sigma")
    nav.addItem("Image Table",        icon="layout-grid")
    nav.addItem("Segmentation",       icon="scan-line")
    nav.addItem("Review CSV",         icon="file-spreadsheet")
    nav.addItem("Sample Definitions", icon="tag")
    nav.addItem("Batch Export",       icon="boxes")
    v.addWidget(nav)
    out = QLabel(f"Active: {nav.currentKey()}")
    out.setStyleSheet(f"color: {theme.Colors.text_muted}; padding: 0 9px;")
    nav.currentChanged.connect(lambda k: out.setText(f"Active: {k}"))
    v.addWidget(out)
    return host


def _build_preview_strip():
    from widgets.preview_strip import PreviewStrip
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    strip = PreviewStrip(host)
    v.addWidget(strip)

    from PySide6.QtWidgets import QSlider
    def _slider(lo, hi, val, fn):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val)
        s.valueChanged.connect(fn)
        return s

    grid = QGridLayout(); grid.setColumnStretch(1, 1)
    grid.addWidget(QLabel("Line width"), 0, 0)
    grid.addWidget(_slider(0, 60, 18, lambda v: strip.setStyle(line_width=v / 10.0)), 0, 1)
    grid.addWidget(QLabel("Marker size"), 1, 0)
    grid.addWidget(_slider(0, 28, 10, lambda v: strip.setStyle(marker_size=v / 2.0)), 1, 1)
    grid.addWidget(QLabel("Marker edge"), 2, 0)
    grid.addWidget(_slider(0, 30, 8, lambda v: strip.setStyle(marker_edge=v / 10.0)), 2, 1)
    v.addLayout(grid)

    colors = QHBoxLayout(); colors.setSpacing(theme.Spacing.xs)
    for token, label in (("trace_1", "Blue"), ("trace_2", "Red"),
                         ("trace_3", "Green"), ("trace_4", "Amber")):
        b = QPushButton(label)
        b.clicked.connect(
            lambda _=False, t=token: strip.setStyle(color=getattr(theme.Colors, t))
        )
        colors.addWidget(b)
    dashed = QPushButton("dashed"); dashed.setCheckable(True)
    dashed.toggled.connect(lambda on: strip.setStyle(dashed=on))
    colors.addWidget(dashed)
    v.addLayout(colors)
    return host


def _build_collapsible_rail():
    from widgets.collapsible_rail import CollapsibleRail
    host = QWidget()
    host.setMinimumHeight(280)
    outer = QHBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    plot = QFrame()
    plot.setStyleSheet(
        f"background-color: {theme.Colors.bg_panel}; "
        f"border: 1px solid {theme.Colors.border_subtle}; "
        f"border-radius: {theme.Radii.md}px;"
    )
    pl = QVBoxLayout(plot)
    pl.setContentsMargins(theme.Spacing.md, theme.Spacing.md,
                          theme.Spacing.md, theme.Spacing.md)
    pl.addWidget(QLabel("plot canvas (fills remaining)"))
    pl.addStretch(1)
    btn = QPushButton("Toggle rail")
    pl.addWidget(btn)
    outer.addWidget(plot, 1)
    rail = CollapsibleRail(host, width=240)
    inner = QFrame()
    iv = QVBoxLayout(inner)
    iv.setContentsMargins(theme.Spacing.md, theme.Spacing.md,
                          theme.Spacing.md, theme.Spacing.md)
    iv.addWidget(QLabel("Properties"))
    for s in ("Profile & Format", "Axes", "Legend", "Lines & Markers",
              "Grid", "Limits & Scale", "Layout"):
        lbl = QLabel(f"  · {s}")
        lbl.setStyleSheet(f"color: {theme.Colors.text_muted};")
        iv.addWidget(lbl)
    iv.addStretch(1)
    rail.setContentWidget(inner)
    outer.addWidget(rail, 0)
    btn.clicked.connect(rail.toggle)
    rail.collapsedChanged.connect(
        lambda c: btn.setText("Show rail" if c else "Hide rail")
    )
    return host


def _build_plot_canvas():
    from widgets.plot_canvas import PlotCanvas
    host = QWidget()
    host.setMinimumHeight(420)
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    # ctxbar fake: plot-type buttons + add/remove
    bar = QHBoxLayout()
    bar.setSpacing(theme.Spacing.xs)
    type_btns: dict[str, QPushButton] = {}
    for label, key in (("Line", "line"), ("Bar", "bar"), ("Scatter", "scatter"),
                       ("Dist", "distribution"), ("Heat", "heatmap")):
        b = QPushButton(label); b.setCheckable(True)
        type_btns[key] = b
        bar.addWidget(b)
    type_btns["line"].setChecked(True)
    bar.addStretch(1)
    add_btn = QPushButton("+ Add panel")
    rm_btn = QPushButton("− Remove last")
    count_lbl = QLabel("subplots: 2")
    for w in (add_btn, rm_btn, count_lbl):
        bar.addWidget(w)
    v.addLayout(bar)

    canvas = PlotCanvas(host, subplots=2, max_subplots=4)
    v.addWidget(canvas, 1)

    def _on_type(key):
        for k, b in type_btns.items():
            b.setChecked(k == key)
        canvas.setPlotType(key)
    for key, b in type_btns.items():
        b.clicked.connect(lambda _=False, k=key: _on_type(k))
    canvas.subplotCountChanged.connect(lambda n: count_lbl.setText(f"subplots: {n}"))
    add_btn.clicked.connect(canvas.addPanel)
    rm_btn.clicked.connect(lambda: canvas.removePanel(canvas.subplotCount() - 1))
    return host


def _build_saved_compact():
    from widgets.saved_selections_list import SavedSelectionsList
    from well_viewer.selections_model import make_selection
    host = QWidget()
    host.setObjectName("SavedCompactHost")
    host.setStyleSheet(
        f"#SavedCompactHost {{ background-color: {theme.Colors.bg_rail}; "
        f"border-radius: {theme.Radii.sm}px; padding: 8px; }}"
    )
    v = QVBoxLayout(host)
    v.setContentsMargins(8, 8, 8, 8)
    v.setSpacing(theme.Spacing.xs)
    head = QLabel("SAVED")
    head.setStyleSheet(
        f"color: {theme.Colors.text_muted}; font-size: 11px; "
        f"letter-spacing: 0.08em; font-weight: 600;"
    )
    v.addWidget(head)
    lst = SavedSelectionsList()
    used: set = set()
    sels = []
    for i, (name, wells) in enumerate((
        ("Control", ["A01", "A02", "A03", "A04"]),
        ("High MOI", [f"B{c:02d}" for c in range(1, 13)]),
        ("Replicate set 2", [f"C{c:02d}" for c in range(1, 13)]),
    )):
        s = make_selection(name=name, wells=wells, used_names=used,
                           used_ids=set(), fallback_color_idx=i)
        used.add(s["name"])
        sels.append(s)
    lst.setSelections(sels)
    lst.setCompact(True)
    v.addWidget(lst)
    return host


# ── per-widget builders end ─────────────────────────────────────────────────


def _build_binding_harness():
    import contextlib
    import io
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(theme.Spacing.sm)
    out = QLabel("(not run yet)")
    out.setStyleSheet(f"font-family: {theme.Typography.family_mono}; "
                      f"font-size: {theme.Typography.caption_size}px;")
    out.setWordWrap(True)

    def _run():
        buf = io.StringIO()
        ok = False
        try:
            from widgets.binding_check import run as _bc_run
            with contextlib.redirect_stdout(buf):
                ok = bool(_bc_run())
        except Exception as exc:  # pragma: no cover
            out.setText(f"⚠ harness error: {exc}")
            out.setStyleSheet(f"color: {theme.Colors.danger}; font-family: {theme.Typography.family_mono};")
            return
        text = buf.getvalue().strip() or ("ALL PASS" if ok else "SOME FAILED")
        colour = theme.Colors.success if ok else theme.Colors.danger
        out.setText(text)
        out.setStyleSheet(f"color: {colour}; font-family: {theme.Typography.family_mono}; "
                          f"font-size: {theme.Typography.caption_size}px;")

    btn = QPushButton("Run binding round-trip")
    btn.setObjectName("Primary")
    btn.clicked.connect(_run)
    v.addWidget(btn, 0, Qt.AlignLeft)
    v.addWidget(out)
    _run()
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
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    cols = 2

    # (entry forms): ("title", builder, note) for a normal card,
    # ("§", "Section name") for a section header (always starts a new row),
    # ("title", builder, note, "wide") for a card spanning both columns.
    layout = [
        ("§", "Form controls & inputs"),
        ("ToggleSwitch", _build_toggle, "on/off paint · bindingAdapter()"),
        ("StyledSlider", _build_slider, "custom groove/handle · bindingAdapter()"),
        ("Stepper", _build_stepper, "± buttons + field · bindingAdapter()"),
        ("SegmentedControl", _build_segmented, "options · setCurrentByData · bindingAdapter()"),
        ("ChipGroup", _build_chips, "exclusive & multi · checkedData/setCheckedData · bindingAdapter()"),
        ("SearchInput", _build_search, "placeholder + hint count"),

        ("§", "Navigation & disclosure"),
        ("PillTabBar", _build_pilltabs, "tab switching"),
        ("CollapsibleSection", _build_collapsible, "expand/collapse, nested content"),

        ("§", "Buttons, icons & status"),
        ("IconButton", _build_iconbar, "icon set · checkable · with-text"),
        ("StatusDot", _build_statusdots, "status palette + labels"),
        ("BrandTile", _build_brand, "the four-quadrant mark"),
        ("EmptyState", _build_empty, "icon + message + action"),

        ("§", "Colour"),
        ("GradientStrip", _build_gradient_strip, "(pos,colour) stops · flat list · callable · reversed"),
        ("LutSelector", _build_lut_selector, "trigger + reverse/reset · popover w/ search n / m · lutChanged"),
        ("ColorSwatchRow", _build_swatches, "curated + recents + Custom tile → ColorPickerPopover"),
        ("ColorPickerPopover", _build_color_picker_popover, "SV square + hue strip + hex/alpha + recents"),

        ("§", "Overlays & transient surfaces"),
        ("Popover", _build_popover, "side × align · auto-flip · Esc/outside dismiss"),
        ("HoverToolbarOverlay", _build_hover_overlay, "hover-to-reveal toolbar over a host"),

        ("§", "Plate & plot"),
        ("WellPlateSelector", _build_plate, "select/passive modes · colours · header clicks"),
        ("SavedSelectionsList", _build_saved, "v2 editable + composable: rename · recolour · reorder · hide · expand → edit wells/replicates · + wells popover"),
        ("MplToolbar", _build_mpl_toolbar, "v2 matplotlib nav toolbar — home · back/fwd · pan/zoom · save + live x/y readout (drives a hidden NavigationToolbar2QT)"),
        ("PlotCard", _build_plotcard, "MplToolbar + figure header + Stat·Error stats popover · screen/publication theme", "wide"),

        ("§", "Window chrome"),
        ("TitleBar", _build_titlebar, "window controls · brand→menu · theme popover · ⌘O · setFramelessMode · should_use_frameless()", "wide"),
        ("WindowResizeGrips", _build_window_resize_grips, "opens a frameless test window with draggable edges/corners"),

        ("§", "Phase 9 — reconciliation widgets"),
        ("KbdHint", _build_kbd_hint, "standalone ⌘ keycaps · attach() composes with any button or IconButton"),
        ("SelectionChip", _build_selection_chip, "accent variant (plate-head 2/96) · muted variant (rail count [3])"),
        ("RangePair", _build_range_pair, "two QLineEdits + glyph · valueChanged(low, high) on Enter or Tab · bindingAdapter"),
        ("RailNav", _build_rail_nav, "vertical accent-bar nav · one-of-N · currentChanged(key) · drives the QStackedWidget in Phase 10"),
        ("PreviewStrip", _build_preview_strip, "custom-painted polyline + markers · live setStyle()"),
        ("CollapsibleRail", _build_collapsible_rail, "right-side animated rail · setCollapsed / toggle · collapsedChanged"),
        ("PlotCanvas", _build_plot_canvas, "single Figure · 1–4 stacked subplots · independent axes · placeholder renderer (real controllers in Phase 11)", "wide"),
        ("SavedSelectionsList — compact", _build_saved_compact, "rail-side compact mode: drag/eye/kebab hidden, recolour disabled, read-only"),

        ("§", "Binding harness"),
        ("Binding round-trip", _build_binding_harness, "runs widgets/binding_check.run() in-process — every binding-driven widget round-trips model↔widget", "wide"),
    ]

    r = 0
    next_col = 0
    for entry in layout:
        if entry[0] == "§":
            if next_col != 0:
                r += 1
                next_col = 0
            grid.addWidget(_section(entry[1]), r, 0, 1, cols)
            r += 1
            continue
        title, builder = entry[0], entry[1]
        note = entry[2] if len(entry) > 2 else None
        wide = len(entry) > 3 and entry[3] == "wide"
        card = _card(title, builder, note)
        if wide:
            if next_col != 0:
                r += 1
                next_col = 0
            grid.addWidget(card, r, 0, 1, cols)
            r += 1
        else:
            grid.addWidget(card, r, next_col)
            next_col += 1
            if next_col >= cols:
                next_col = 0
                r += 1
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
