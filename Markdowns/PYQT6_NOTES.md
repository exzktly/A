# All-Well Redesign v2 — PyQt6 Implementation Notes

This document catalogs every component in `All-Well Redesign v2.html` that will **not** map cleanly to a standard PyQt6 widget. For each, you'll find:

- What it is in the mockup
- Why a stock widget won't do
- A recommended implementation path in PyQt6

Standard widgets that *do* map cleanly (`QPushButton`, `QLineEdit`, `QLabel`, `QCheckBox`, `QSpinBox`, `QComboBox`, `QSlider`, `QListWidget`) are not listed — style them via QSS using `DESIGN_TOKENS.md` constants.

Recommended base class for almost everything below: subclass `QWidget` and override `paintEvent`, `mousePressEvent`, `mouseMoveEvent`, `leaveEvent` as needed. Use `QStyle.PixelMetric` only when you want OS-native sizing; otherwise size in pixels from tokens.

---

## 1. Frameless window with custom titlebar

**Mockup.** 44-px tall titlebar containing: brand logo (4-color grid swatch), wordmark, breadcrumb (`Workspace · Project / File.awd`), live "Saved" status dot with halo, action buttons (Share, Export, …).

**Why custom.** Qt's native title bar is OS-controlled. To get this look you need a frameless window with a hand-built header strip that also handles window dragging and resizing.

**Implementation.**
- `QMainWindow` with `setWindowFlag(Qt.FramelessWindowHint)`.
- A `QWidget` header strip at the top, with its own `QHBoxLayout`. Override `mousePressEvent` + `mouseMoveEvent` to implement window dragging via `windowHandle().startSystemMove()`.
- Edge-resize: install a 6-px transparent border widget with `setCursor()` on the four edges + four corners, and call `windowHandle().startSystemResize(edge)`.
- The "Saved" status dot is a tiny custom `QWidget` that paints a filled circle + a translucent halo (`QColor("#4ADE80")` with alpha 30 at radius+3).
- The 4-color brand-logo tile is a fixed-size QWidget that paints four quadrant circles in `paintEvent`.

---

## 2. 96-Well Plate

**Mockup.** 8 × 12 grid of circular wells. Clickable row letters (A–H) and column numbers (1–12) act as headers — clicking one selects the whole row or column. Wells have multiple visual states: empty (flat fill), hovered, selected with a per-well *radial gradient + inset top-highlight + inset bottom-shadow* (the "lit chip" effect), and selected-as-trace-N (color keyed to series index).

**Why custom.** There is no Qt widget remotely like this. Even `QGraphicsView` would be overkill — you don't need full scene management, just a paint+hit-test grid.

**Implementation.**
- Subclass `QWidget`. Hold state as `selected: dict[(row, col), trace_index]` and `hover: tuple|None`.
- In `paintEvent`:
  - Draw 8 row letters and 12 column numbers in `TEXT_MUTED` 11 px Inter.
  - For each cell, compute its rect. If unselected: solid fill `BG_ELEVATED` + 1 px `BORDER` ring.
  - If selected: build a `QRadialGradient` centered at 35% / 30% of the cell, with the 3 stops listed in `DESIGN_TOKENS.md` §1.8 for that trace index. Fill with that gradient brush. Then overlay two 1-px lines for the inset: a top-edge `rgba(255,255,255,0.30)` line and a bottom-edge `rgba(0,0,0,0.30)` line. (Inset box-shadow has no Qt equivalent — paint it.)
- `mousePressEvent`:
  - Hit-test against the row-letter strip → emit `rowSelected(row_index)`.
  - Hit-test against the col-number strip → emit `columnSelected(col_index)`.
  - Hit-test against a well → emit `wellToggled(row, col)`.
- `mouseMoveEvent` updates hover with `setMouseTracking(True)` and calls `update()` only on the cell that changed.
- `leaveEvent` clears hover.
- Performance: at 96 cells this is cheap; no need to cache, no need for `QGraphicsScene`.

---

## 3. Matplotlib-style figure card with live coordinate readout

**Mockup.** A card containing one or more stacked subplots, with a *single* toolbar at the bottom. Toolbar layout, left → right: `home / back / forward` · `pan / zoom` · `configure / edit / save`, then push the live `x = … · y = …` coords readout to the right edge in JetBrains Mono.

**Why custom.** Use **matplotlib embedded in Qt** for the chart itself (not QtCharts — matplotlib has the right export semantics and the user is targeting matplotlib export parity). Then use matplotlib's own `NavigationToolbar2QT` *or* hide it and build a custom toolbar that drives the same backend signals — the mockup's toolbar is custom-styled and the default Qt toolbar will not match.

**Implementation.**
- `from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT`.
- Compose: `card = QFrame` containing `[ FigureCanvasQTAgg, CustomToolbarStrip ]` in a vertical layout.
- For the custom toolbar: each icon button is a `QToolButton` with `setCheckable(True)` for pan/zoom (mutually exclusive — wire them with `QButtonGroup.setExclusive(True)`).
- Wire the buttons to the canvas via the `NavigationToolbar2QT` API:
  ```python
  self._nav = NavigationToolbar2QT(self.canvas, self, coordinates=False)
  self._nav.hide()  # we replace its UI but keep its handlers
  home_btn.clicked.connect(self._nav.home)
  pan_btn.toggled.connect(lambda on: on and self._nav.pan())
  zoom_btn.toggled.connect(lambda on: on and self._nav.zoom())
  save_btn.clicked.connect(self._nav.save_figure)
  ```
- Live coords readout: connect to `canvas.mpl_connect('motion_notify_event', on_move)` and update a `QLabel` with `f"x = {e.xdata:.2f}  ·  y = {e.ydata:.2f}"` using `tabular-nums`-style mono font.

---

## 4. Segmented control

**Mockup.** Pill of 2–4 button-like options where exactly one is "on". The on-state gets `BG_ELEVATED` background + `--sh-1` drop. Three places: scope (`All / Plot 1 / Plot 2`), mode-rail (`Review / Analyze`), per-plot view-as (`Line / Bar / Scatter / Dist / Heat`).

**Why custom.** `QTabBar` looks like an OS tab bar and won't restyle into a pill without heavy QSS that's brittle across platforms. `QButtonGroup` works structurally but needs visual reskinning.

**Implementation.**
- Build as `SegmentedControl(QFrame)`. Constructor takes a list of `(label, icon)` items.
- Internally a `QHBoxLayout` of `QToolButton`s with `setCheckable(True)`, all in one `QButtonGroup(exclusive=True)`.
- QSS:
  ```css
  SegmentedControl { background: #131A24; border: 1px solid #1B2331; border-radius: 5px; padding: 2px; }
  SegmentedControl QToolButton { background: transparent; border: none; color: #98A2B3; padding: 4px 10px; border-radius: 3px; }
  SegmentedControl QToolButton:checked { background: #1A2230; color: #E6E9EF; }
  ```
- The `--sh-1` drop on the checked pill: paint manually in `paintEvent` of `SegmentedControl` using `QPainter` (a 1-px line at the bottom of the checked button rect, rgba(0,0,0,0.4)). QSS `border-bottom` would also work and is simpler.

---

## 5. Chip group (pill chips)

**Mockup.** Smaller cousin of the segmented control — a row of compact pills, often `single-select` (channel chip) or `multi-select` (trace toggles). Different sizing/padding from the segmented control above; they live inline with text labels.

**Implementation.** Same `QButtonGroup` of `QToolButton`s pattern; smaller padding (`4px 8px`) and `border-radius: 999px` (the `--r-pill` token). If multi-select, leave `setExclusive(False)`.

---

## 6. Collapsible section with live-preview value in header

**Mockup.** In the Properties panel, each section (`Appearance`, `Threshold`, `Annotations`, …) has a clickable header that toggles open/closed. When closed, the header shows a *live preview* of what's inside — a color swatch, a number, a short label — so you can read the panel without expanding everything.

**Why custom.** `QToolBox` and `QGroupBox` give you collapsing-or-grouping, but not a stylable header with a custom value chip on the right side. `QGroupBox::indicator` is too limited.

**Implementation.**
- `Section(QFrame)` with two children: a `SectionHeader(QWidget)` that paints the title + chevron + value chip, and a `QFrame body` containing the section's controls.
- `SectionHeader.mousePressEvent` toggles `body.setVisible(not body.isVisible())` and rotates the chevron icon.
- The "value chip" is a slot — pass in either a `QLabel` (for text), a small custom `ColorSwatch` widget, or a `QHBoxLayout` of swatches. Update it from the controls inside the body via signals.
- For smooth expand/collapse use `QPropertyAnimation` on the body's `maximumHeight`.

---

## 7. Stepper input (numeric input with up/down chevrons)

**Mockup.** Numeric input with a single right-edge column containing tiny `▲` / `▼` buttons. Focus state: `--accent` border + `--ring-focus` 2-px outer halo.

**Why custom.** `QSpinBox` does this *function* but its native style differs across platforms and the right-edge chevron stack is rendered by the OS style. To get pixel parity you reskin or replace.

**Implementation.**
- Path A (simpler): `QSpinBox` + heavy QSS. `QSpinBox::up-button`, `QSpinBox::down-button`, `QSpinBox::up-arrow`, `QSpinBox::down-arrow` are stylable. Ship the chevron as an SVG icon resource. Watch out for OS-specific drawing on macOS where some `QSpinBox` sub-controls fall through to native.
- Path B (pixel-perfect): build `Stepper(QFrame)` containing a `QLineEdit` (with `QIntValidator` or `QDoubleValidator`) and two `QToolButton`s stacked in a `QVBoxLayout`. Buttons emit `valueChanged(±1)`. This is the recommended path for design fidelity.
- Focus ring: install an `eventFilter` on the inner `QLineEdit` for `FocusIn` / `FocusOut`; on focus, set a 2-px translucent border on the wrapping frame.

---

## 8. Curated color-swatch picker

**Mockup.** Where the user picks a color, you don't get a free-form color picker — you get a curated row of ~4–6 tappable swatches. Selected swatch shows a 2-px accent ring around it.

**Why custom.** `QColorDialog` is a modal dialog. The mockup pattern is inline and constrained.

**Implementation.**
- `ColorSwatchRow(QWidget)` holds a list of `QColor` options.
- Each option is rendered as a 22-px square (`QPainter.fillRect` + 1-px border) in a horizontal layout.
- Hit-testing in `mousePressEvent` finds the swatch under the cursor and emits `colorPicked(QColor)`.
- The selected swatch gets a 2-px ring drawn in `paintEvent` outside its fill rect, using `ACCENT`.

---

## 9. Search input with leading icon

**Mockup.** `QLineEdit`-shaped, but with a search-glass icon inset on the left and a `⌘K` hint inset on the right.

**Why almost-standard.** `QLineEdit` supports `addAction(icon, QLineEdit.LeadingPosition)` — that handles the left icon out of the box.

**Implementation.**
- `QLineEdit` + `addAction(QIcon(search_svg), QLineEdit.ActionPosition.LeadingPosition)`.
- For the right `⌘K` hint: there is no built-in "trailing label". Use a `QLabel` child positioned in the lineedit's own layout, or call `setTextMargins(left=0, top=0, right=hint_width, bottom=0)` and place a `QLabel` over the right margin via absolute positioning in a wrapping `QFrame`.

---

## 10. Toast / inline notification

**Mockup.** Floating dismissible notification with a status dot and short copy.

**Why custom.** No built-in toast.

**Implementation.**
- `Toast(QWidget)` as a top-level `Qt.ToolTip | Qt.FramelessWindowHint` window, parented to the main window.
- Position with `move(parent.mapToGlobal(QPoint(x, y)))` near the bottom-right.
- Auto-dismiss with `QTimer.singleShot(4000, self.fade_out)` where fade is a `QPropertyAnimation` on `windowOpacity`.
- Drop shadow via `QGraphicsDropShadowEffect(blur=12, offset=(0,4), color=QColor(0,0,0,90))`.

---

## 11. Slide-in drawer (Analyze mode)

**Mockup.** Clicking the Analyze rail trigger slides a panel in from the right edge, overlaying part of the canvas. Dismissed by clicking outside or pressing `Esc`.

**Why custom.** Qt has no drawer primitive.

**Implementation.**
- `Drawer(QWidget)` child of the main window, initially positioned off-screen (`x = parent.width()`).
- Animate `pos.x()` with `QPropertyAnimation(self, b"pos")` over ~180 ms with `QEasingCurve.OutCubic`.
- Install an event filter on the main window to catch outside-clicks and `Esc` to dismiss.
- Optional: paint a translucent backdrop `QWidget` behind the drawer (full window, `rgba(0,0,0,0.35)`) so it dims the canvas.

---

## 12. Slider with focus ring and custom thumb

**Mockup.** `QSlider`-shaped, but the thumb is a 14-px circle with a 1-px accent border *outside* a 2-px transparent gap (the "ring on a stalk" look). Focus state adds a halo.

**Implementation.**
- `QSlider` + QSS:
  ```css
  QSlider::groove:horizontal { height: 4px; background: #1B2331; border-radius: 2px; }
  QSlider::sub-page:horizontal { background: #6B8AFD; border-radius: 2px; }
  QSlider::handle:horizontal {
    width: 14px; height: 14px; margin: -5px 0;
    background: #1A2230; border-radius: 7px;
    border: 2px solid #0E131C; /* the "gap" effect via a ring of the rail color */
  }
  QSlider::handle:horizontal:focus {
    border: 2px solid rgba(107,138,253,0.35);
  }
  ```
- The 1-px outer accent ring is fiddly via QSS alone. If you need it crisp, subclass `QSlider`, override `paintEvent`, draw the groove/sub-page/handle yourself with `QPainter`.

---

## 13. Hover-revealed plot toolbar

**Mockup.** A row of icon buttons that is `opacity: 0` until you hover the plot card, then fades in to `opacity: 1`.

**Why custom.** Qt has no `:hover`-driven visibility on a child widget. QSS `:hover` only restyles, it can't show/hide.

**Implementation.**
- Install an `eventFilter` on the plot card that listens for `QEvent.Enter` / `QEvent.Leave`.
- On enter: animate the toolbar's `windowOpacity` (if it's a separate window) or a `QGraphicsOpacityEffect` to 1.0 over 120 ms.
- On leave: animate to 0.0 over 200 ms with `QEasingCurve.OutCubic`.
- Use `QGraphicsOpacityEffect`, not `setVisible(False)`, so the row keeps its space and the layout doesn't jump.

---

## 14. Saved-selections list with colored condition dots

**Mockup.** A list of saved well selections. Each row has a colored dot (mapping to a condition), a name, a count chip, and a hover action menu.

**Why custom.** `QListWidget` rows show text + icon. Multiple inline columns with custom layout per row need a delegate.

**Implementation.**
- `QListView` (or `QListWidget` if you don't need a model) with a custom `QStyledItemDelegate.paint`:
  ```python
  def paint(self, painter, option, index):
      row = index.data(Qt.UserRole)
      # Paint background based on option.state & QStyle.State_Selected
      # Paint dot circle in row.color
      # Paint name in TEXT_PRIMARY
      # Paint count chip on right edge
  ```
- `sizeHint` returns `QSize(option.rect.width(), 28)`.

---

## 15. Lucide icons

**Mockup.** All icons use [Lucide](https://lucide.dev). Stroke width 1.75. Sizes: 13 / 14 / 16 px.

**Why custom.** Qt has no built-in Lucide icon set. `QStyle.standardIcon` gives you OS icons which are wrong.

**Implementation.**
- Bundle the SVGs you need (download from lucide.dev or `npm i lucide` and copy from `lucide/icons/`).
- Load via `QIcon(":/icons/check.svg")` after registering with `QResource` (or just load from disk with `QIcon("icons/check.svg")` during development).
- For runtime color tinting (e.g. icon flips between `TEXT_SECONDARY` and `TEXT_PRIMARY` on hover), the simplest path is to load the SVG as text, `replace('currentColor', desired_hex)`, then `QIcon(QPixmap.fromImage(QImage.fromData(svg_bytes)))`. Or subclass `QIconEngine`.
- Cache colored variants per `(icon_name, hex)` tuple.

---

## 16. Breadcrumb with file chip

**Mockup.** `Workspace · Project / file.awd ●` where the file chip has its own monospace box-ish background and the `●` is the saved-status dot.

**Implementation.** A `QHBoxLayout` of `QLabel`s. The file chip is a `QLabel` with QSS:
```css
QLabel#FileChip {
  background: #131A24; border: 1px solid #1B2331;
  font-family: 'JetBrains Mono'; font-size: 12px;
  padding: 3px 8px; border-radius: 3px;
}
```
The status dot is the same custom widget as in §1.

---

## 17. Status bar

**Mockup.** 28-px tall strip across the bottom with live indicators (`● Connected`, `· 96 wells loaded`, `· 2 plots`) and a right-aligned "tray" button.

**Why almost-standard.** `QMainWindow.statusBar()` exists but renders system-default. You'll want a custom `QWidget` for full styling control.

**Implementation.** Custom `StatusBar(QWidget)` with a `QHBoxLayout` of small `QLabel`s separated by a `·` `QLabel`. Use `QMainWindow.setStatusBar(custom_status_bar)` to install — `QMainWindow` will accept any `QWidget` subclass via `setMenuWidget`-style hosting, but easier is to add it manually to the central layout's bottom row.

---

## 18. Tab bar (top-of-canvas tabs)

**Mockup.** Tabs like `Channel 1 · Channel 2 · + Add` with the active tab carrying an `inset 0 -2px 0 var(--accent)` underline.

**Why custom.** `QTabBar`/`QTabWidget` can be styled but the underline detail and the inline `+ Add` action require either subclassing or building from scratch.

**Implementation.** `QTabBar` with QSS:
```css
QTabBar::tab { padding: 8px 14px; background: transparent; color: #98A2B3; border: none; }
QTabBar::tab:selected { color: #E6E9EF; border-bottom: 2px solid #6B8AFD; }
```
Then `tabBar.setExpanding(False)` and add a `+` `QToolButton` via `setCornerWidget`.

---

## 19. Empty-state placeholder

**Mockup.** When the figure has no data, a centered iconographic placeholder with a 1-line tip.

**Implementation.** A `QFrame` with a vertical `QHBoxLayout`, containing a `QLabel` carrying an `QIcon` rendered to `QPixmap` at 48 px and a `QLabel` with the tip text. Toggle visibility based on the canvas state.

---

## 20. Putting it together — recommended structure

```
MainWindow (QMainWindow, frameless)
├── TitleBar (QWidget)              ── §1
├── Body (QWidget, QHBoxLayout)
│   ├── LeftRail (QFrame)
│   │   ├── ModeButton (Analyze)    ── §11
│   │   └── (tool icons)
│   ├── CenterPanel (QFrame, QVBoxLayout)
│   │   ├── ContextBar (QFrame)
│   │   │   ├── TabBar              ── §18
│   │   │   └── PlateActions
│   │   ├── SplitPane (QSplitter horizontal)
│   │   │   ├── PlatePanel (QFrame)
│   │   │   │   ├── WellPlate (QWidget custom)  ── §2
│   │   │   │   └── QuickSelectRow
│   │   │   └── FigureCard (QFrame)             ── §3
│   │   └── (empty state slot)                  ── §19
│   └── PropertyPanel (QFrame, QVBoxLayout)
│       ├── ScopeSegmented           ── §4
│       ├── SearchInput              ── §9
│       └── (Sections...)            ── §6
│           ├── inputs / steppers    ── §7
│           ├── color row            ── §8
│           └── slider               ── §12
├── StatusBar                        ── §17
└── (overlays)
    ├── Toast                        ── §10
    └── Drawer                       ── §11
```

---

## 21. Things to be careful about

- **macOS QSS gotchas.** Several controls (`QSpinBox`, `QComboBox` drop-arrow, `QSlider::groove`) fall through to native rendering on macOS unless you give them a *complete* QSS specification including a `background-color` on the base selector. If a control suddenly looks native on Mac, you've under-specified the QSS — add `background-color` and `border` to the base selector.
- **High-DPI.** Render all icons from SVG, not bitmap. Set `QApplication.setHighDpiScaleFactorRoundingPolicy(...)` and `Qt.AA_EnableHighDpiScaling` early in startup.
- **Cursor changes.** Pan/zoom modes should change `QApplication.setOverrideCursor(Qt.OpenHandCursor / Qt.CrossCursor)`. Matplotlib's `NavigationToolbar2QT.pan()` does this for you — verify when wiring.
- **Z-order for the drawer overlay.** Drawer must be `raise_()`d above the canvas every time it's shown. If you parent it to `MainWindow` and the canvas embeds an OpenGL widget (e.g. matplotlib with Agg/cairo backend), OpenGL surfaces don't respect Qt's z-order — you may need to use a separate top-level window with `Qt.Popup` flag.
- **Repaint cost of the well plate.** Don't `update()` the whole widget on every mouse move — `update(QRect)` only the cell that changed hover state. At 96 cells it doesn't matter, but it's a good habit before someone makes a 384-well variant.

---

## 22. Reference

| File                              | Purpose                                                              |
|-----------------------------------|----------------------------------------------------------------------|
| `All-Well Redesign v2.html`       | Editable source mockup.                                              |
| `DESIGN_TOKENS.md`                | Token reference — colors, type, spacing, radii, shadows.             |
| `DESIGN_NOTES.md`                 | Redesign intent and rationale.                                       |
| `PYQT6_NOTES.md`                  | (this file) Custom Qt widget catalog.                                |
