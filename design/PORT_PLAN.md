# All-Well v2 — Port Plan

Maps the approved v2 mockup (`design/All-Well Redesign v2 _standalone_.html` — a
self-unpacking bundle that isn't statically readable; this plan is built from
`design/PYQT6_NOTES.md`, `design/DESIGN_TOKENS.md`, `design/DESIGN_NOTES.md`, and
the current-app screenshot) onto the existing PySide6 codebase.

Conventions:
- "current code location" is the most specific file/class/function that owns the
  thing today; many of these are *builder functions* that populate a plain
  `QWidget`/`QFrame` rather than subclasses.
- Framework is **PySide6** (the PYQT6_NOTES doc says PyQt6 — APIs are equivalent;
  use `Signal`/`Slot`, PySide6 enum scoping).
- Styling for everything is sourced from `theme.py` (`theme.Colors / Typography /
  Spacing / Radii`) and the base sheet from `theme.qss()`. No new hardcoded hex.
- "No code yet" — this is the inventory for Step 2 of `all-well-porting-plan.md`.

---

## Table 1 — Existing widgets to port

| Mockup component | Current code location | Port strategy |
|---|---|---|
| Frameless window + custom titlebar (brand tile, wordmark, breadcrumb, Saved dot, action buttons) | `all_well.py` `AllWellApp(QMainWindow)` (native frame) + header strip built in `AllWellApp._build_ui()` (`QWidget#Sidebar` with `QLabel#Title`, Theme `QComboBox`) | rebuild from scratch (new `TitleBar` widget; `AllWellApp` gets `FramelessWindowHint` + drag/resize wiring) |
| Top-of-canvas tab bar (`Channel 1 · Channel 2 · + Add`, accent underline) | `well_viewer/views/centre_view.py` `_GroupedTabBar(QTabBar)`; `all_well.py` outer `QTabWidget` (Review/Analyze) | subclass and extend (`_GroupedTabBar` already subclasses `QTabBar`; restyle + add `+`/underline). Outer Review/Analyze `QTabWidget` → see "Mode demoted" row |
| Secondary tab strip (`Plotting · smFISH · Statistics · Image Table · Segmentation · Review CSV · Sample Definitions · Batch Export`) | `well_viewer/views/centre_view.py` (centre notebook) + `well_viewer/tabs/__init__.py` registry | restyle via QSS only (keep `QTabWidget`/`QTabBar`, apply v2 tab QSS) |
| Per-plot view switcher (`Line / Bar / Scatter / Dist / Heat`) — *was* a global subnav (`Line Graphs · Bar Plots · Scatter Plot · Distribution · Heat Map` in screenshot) | global plot-type tabs in `well_viewer/views/centre_view.py`; per-type builders in `well_viewer/tabs/{line_graphs,bar_plots,scatter_tab,scatter_agg,distribution,heatmap}_tab_view.py` | rebuild from scratch (replace the global tab row with a `SegmentedControl` in each plot card header — see Table 2). **Decided: per-plot cards** (DECISIONS #1) — each subplot is its own `PlotCard` with its own view-switcher. |
| Channel selector (`Channel: GFP` chip, per panel) | global `QComboBox` near the figure; attrs `self._*_channel_cb` assigned in `well_viewer/tabs/*_tab_view.py`; state `WellViewerApp._active_channel` (`runtime_app.py:712`) | rebuild from scratch (becomes a `ChipGroup`/dropdown chip inside each plot card header — Table 2) |
| Well-plate selector (8×12 circles + clickable row/col headers, lit-chip selected state) | `well_viewer/views/well_button.py` `WellButton(QPushButton)` + `_HeaderClickLabel(QLabel)`; layout in `well_viewer/plate_layout.py`; assembled in `well_viewer/views/sidebar_view.py` / `runtime_app.py` | rebuild from scratch (single custom-painted `WellPlate(QWidget)` — see Table 2; replaces the 96 `QPushButton`s + header `QLabel`s) |
| Quick-select row (`All 96 / Invert / Clear`) — currently `All / None` | bottom-of-plate buttons in `well_viewer/views/sidebar_view.py` (the `All` / `None` `QPushButton`s in the screenshot) | rebuild from scratch (3 ghost `QPushButton`s w/ tooltips; row/col select moves onto `WellPlate`) |
| Saved-selections list (colored condition dots, name, count chip, hover menu) | `well_viewer/sample_definitions.py` + `well_viewer/views/replicate_panel_view.py` + `well_viewer/persistence/sample_definitions.py`; ratio/replicate panels `views/ratio_panel_view.py` | subclass and extend (`QListView` + custom `QStyledItemDelegate` — see Table 2; reuse the existing sample-definition model) |
| Properties panel (`All / Plot 1 / Plot 2` scope segmented, `⌘K` search, collapsible sections with live-preview value) | **no unified panel today** — controls are spread across tab views, `well_viewer/views/export_style_sidebar_view.py` `ExportStyleSidebar(QWidget)`, `views/heatmap_layout_sidebar_view.py`, `views/stats_view.py`, per-tab option rows | rebuild from scratch (new `PropertiesPanel` composing `SegmentedControl` + `SearchInput` + N× `CollapsibleSection` — Table 2; migrate existing controls into sections) |
| Collapsible section / group box (current "Row N" option boxes etc.) | `QGroupBox` usages, e.g. `well_viewer/views/image_table_grid_view.py:60` `QGroupBox#ImageTableRowOptions`; `runtime_app.py` option groups | subclass and extend → actually rebuild: replace `QGroupBox` with `CollapsibleSection` (Table 2) where the header-preview/collapse behavior is wanted; plain `QGroupBox` elsewhere → restyle via QSS only |
| Matplotlib figure card + bottom toolbar (home/back/fwd · pan/zoom · configure/edit/save · `x=… y=…` mono readout) | `well_viewer/ui_helpers.py` `_ThemedNavToolbar(NavigationToolbar2QT)` + `attach_plot_toolbar()` + `_PlotDockHost(QWidget)`; canvases created in `well_viewer/tabs/*_tab_view.py` (`FigureCanvasQTAgg`), also `cell_gating_tab.py`, `smfish_tab.py`, `views/stats_view.py`, `batch_export/base_panel.py`, `export_service.py` | rebuild from scratch (new `PlotCard(QFrame)` wrapper = `FigureCanvasQTAgg` + custom `MplToolbar` driving a hidden `NavigationToolbar2QT`; route every existing canvas through it). `_ThemedNavToolbar` icon-recolor logic → fold into `MplToolbar` |
| Matplotlib axis styling (dark-on-white today; mockup wants dark-on-chrome) | `well_viewer/plot_style.py` `apply_ax_style()`; per-figure `set_facecolor` calls in `runtime_app.py`, `cell_gating_tab.py`, `smfish_tab.py`, `image_table_controller.py` | rebuild: `plot_style.apply_ax_style` rewritten to read the active `PlotCard` theme (`"publication"` = white `CPub`/`TRACE_PUB`, the default + what's exported; `"screen"` = dark token set, a per-card live-preview toggle). **Decided** (DECISIONS #2): white on screen by default, per-card dark "presentation" toggle. |
| Plot toolbar (always-on) → hover-revealed | `well_viewer/ui_helpers.py` `attach_plot_toolbar()` (permanent toolbar row) | rebuild from scratch (event-filter Enter/Leave + `QGraphicsOpacityEffect`) — *only if* per-card plots survive; with the single-shared-canvas reversion this becomes one persistent bottom toolbar instead |
| Error-band controls (`Error Band / SEM / Spread / FOV` segmented buttons, screenshot bottom-right) | `WellViewerApp._use_sem` / `_sem_btns` / `_sem_btn` (`runtime_app.py:736-743`); buttons created in `well_viewer/views/status_view.py` `build_bottom` + line/bar tab toolbars | subclass and extend → rebuild as a `SegmentedControl` (Table 2) bound to `_use_sem` |
| Status bar (`● Connected · 96 wells loaded · 2 plots`, tray button) | `well_viewer/views/status_view.py` `build_bottom(app)` | subclass and extend (keep the builder, restyle to v2; add a `StatusDot` widget — Table 2) |
| "Open…" / data-load button + `No data loaded` label (→ breadcrumb file chip) | `well_viewer/load_controller.py` + the `Open...` `QPushButton` and `No data loaded` `QLabel` built in `runtime_app.py` / `views/centre_view.py` | rebuild from scratch (becomes the breadcrumb `Workspace · Project / file.awd ●` in the titlebar; "Open…" stays as a `QPushButton#Primary` — restyle via QSS only) |
| `Export CSV` / `Export` buttons | per-tab export buttons; `well_viewer/export_service.py`; `views/export_style_sidebar_view.py` | restyle via QSS only (apply `#Primary` / default button styling) |
| Theme combo (`Theme: Dark`) in header | `all_well.py` `_theme_combo` (`QComboBox`) + `AllWellApp._on_theme_change`; `ui/theme/theme_manager.py` `ThemeManager` | delete (mockup ships one dark theme). **Open question — keep multi-theme by parametrizing `theme.Colors`, or remove entirely.** If kept: rebuild as a small menu/`ChipGroup`, not a `QComboBox` |
| Stepper inputs (numeric + ▲/▼) | plain `QSpinBox`/`QDoubleSpinBox` in `views/ratio_panel_view.py`, `views/export_style_sidebar_view.py`, `views/heatmap_layout_sidebar_view.py`, `image_table_controller.py`, `tabs/{image_table,distribution}_tab_view.py`, `runtime_app.py` | restyle via QSS only for the common case (style `::up-button/::down-button/::up-arrow/::down-arrow`); rebuild as `Stepper` (Table 2) only where pixel-perfect parity is required |
| Sliders (threshold etc.) | plain `QSlider` in `runtime_app.py`, `tabs/heatmap_tab_view.py`, `tabs/bar_plots_tab_view.py` | restyle via QSS only (groove/sub-page/handle QSS); subclass and extend only if the crisp outer accent ring is needed (`StyledSlider`, Table 2) |
| Curated color picker / LUT color choice | `runtime_app.py` review-image color swatch `QPushButton`s (`setStyleSheet(f"background-color: rgb(...)")`, `:4235`); LUT-color `QComboBox` in `tabs/image_table_tab_view.py` / `image_table_controller.py`; trace-color dots in `batch_export/base_panel.py` | rebuild from scratch (`ColorSwatchRow`, Table 2) where it's a small curated set; keep `QComboBox` where it's a long LUT list (restyle via QSS only) |
| Checkboxes / radios | `QCheckBox` across `views/export_style_sidebar_view.py`, `tabs/*`, `batch_export/*`, `views/preview_panel_view.py` | restyle via QSS only; where the mockup shows an on/off **toggle switch** rather than a checkmark, rebuild as `ToggleSwitch` (Table 2) |
| Plain buttons / tool buttons | `QPushButton` everywhere; `well_viewer/batch_export/well_grid_button.py` `_WellGridButton(QPushButton)` | restyle via QSS only (object names `#Primary`/`#Danger`/`#Ghost`); `_WellGridButton` keeps its subclass, drop its inline `setStyleSheet` in favor of QSS + dynamic property |
| Lucide icon set | none — matplotlib toolbar icons + `well_viewer/ui_helpers.py` `refresh_plot_toolbar_icons()` (recolors mpl icons) | rebuild from scratch (bundle SVGs under `ui/icons/`, add an `IconButton`/icon-loader helper with runtime recolor + cache — Table 2) |
| Analyze mode (full co-equal tab) → dashed-rail trigger + slide-in drawer | `all_well.py` second `QTabWidget` tab hosting `analyze_tab.py` `AnalyzeTab(QWidget)` | rebuild from scratch (new `Drawer` host + rail trigger; `AnalyzeTab`'s *contents* are reused inside the drawer — restyle via QSS only for the inner controls) |
| Toast / inline notification | none (errors via status label / `QMessageBox`) | rebuild from scratch (`Toast` top-level — Table 2) |
| Empty-state placeholder ("No wells or well groups selected…") | the centered `QLabel`s in the figure area, built in `well_viewer/tabs/line_graphs_tab_view.py` / `centre_view.py` | restyle via QSS only (wrap in an `EmptyState` `QFrame` with icon + tip; trivial) |
| Brand-logo tile (4-color quadrant grid) | window icon painted in `all_well.py._install_app_icon()` (not shown in-UI) | rebuild from scratch (small custom-painted `BrandTile(QWidget)` for the titlebar; the window-icon painter can stay) |
| Pop-out plot host | `well_viewer/ui_helpers.py` `_PlotDockHost(QWidget)`; `well_viewer/figure_export_editor.py` | subclass and extend (keep, restyle, host the new `PlotCard`) |
| Scatter cell viewer dialog | `well_viewer/scatter_callbacks.py` `ScatterCellViewer(QDialog)` | restyle via QSS only (inherits `QDialog` v2 styling; embedded canvas → `PlotCard`) |

---

## Table 2 — New custom widgets to build

| Component | Composed from | Custom `paintEvent`? | Used where in the new app |
|---|---|---|---|
| **`ToggleSwitch`** (on/off pill switch) | `QAbstractButton` (checkable) | **Yes** — paint the track + knob (animate knob x via `QVariantAnimation`); no native QSS equivalent for an iOS-style toggle | Properties panel boolean rows (replacing checkmarks where the mockup shows a switch), plot-card quick toggles, anywhere a binary state reads better as a switch (e.g. grid on/off, log-scale, error-band on/off) |
| **`CollapsibleSection`** (header with chevron + live-preview value chip + animated body) | `QFrame` container → `SectionHeader(QWidget)` (title `QLabel` + chevron `QLabel`/icon + a "value" slot: `QLabel` / `ColorSwatchRow` / mini layout) + body `QFrame`; `QPropertyAnimation` on body `maximumHeight` | **Partly** — `SectionHeader` paints its hover background + bottom hairline (or via QSS); chevron is an icon; body is plain layout. Mostly QSS-able, light `paintEvent` for the hairline | Every section of the new Properties panel (Appearance, Threshold, Axes, Legend, Annotations…); also replaces `QGroupBox#ImageTableRowOptions`-style boxes in Image Table |
| **`SegmentedControl`** (2–4 mutually-exclusive pills, "on" pill has `bg-elevated` + 1-px drop) | `QFrame` track + `QHBoxLayout` of checkable `QToolButton`s in one exclusive `QButtonGroup` | **Optional** — track + checked-pill via QSS (`:checked` bg + `border-bottom`); a 1-px `paintEvent` line only if the `--sh-1` drop must be exact | Properties-panel scope (`All / Plot 1 / Plot 2`); per-plot view-as (`Line/Bar/Scatter/Dist/Heat`); error-band mode (`Error Band/SEM/Spread/FOV`); any 2–3-way option that's currently a row of buttons |
| **`PillTabBar`** / channel tab bar (`Channel 1 · Channel 2 · + Add`, accent underline, inline add) | `QTabBar` subclass (or `QHBoxLayout` of `QToolButton`s) + a `+` `QToolButton` corner widget | **Optional** — underline via `QTabBar::tab:selected { border-bottom }`; custom paint only for the add-button hit area if not using `setCornerWidget` | Top-of-canvas channel tabs; potentially the secondary tab strip if `QTabWidget` styling proves too brittle on macOS |
| **`ChipGroup`** (compact pills, single- or multi-select; `--r-pill` radius) | `QHBoxLayout` of checkable `QToolButton`s; `QButtonGroup` (exclusive or not) | No — pure QSS | Per-plot channel chip (single-select); trace-toggle chips; small filter rows; possibly the theme switcher if multi-theme is kept |
| **`WellPlate`** (8×12 well grid + clickable A–H row letters + 1–12 column numbers; states: empty / hover / selected-as-trace-N with radial gradient + inset highlight/shadow) | bare `QWidget` (no children); state dict `selected: {(row,col): trace_idx}`, `hover`; emits `wellToggled(row,col)`, `rowSelected(r)`, `columnSelected(c)` | **Yes** — the whole widget is custom-drawn: row/col labels, well circles, `QRadialGradient` fills per trace index, 1-px inset top-highlight + bottom-shadow lines; `mousePressEvent`/`mouseMoveEvent`/`leaveEvent` for hit-test + hover; `update(QRect)` per changed cell | The left plate panel (replaces the 96 `WellButton`s + `_HeaderClickLabel`s); the plate *is* the legend (selected wells carry their trace color) |
| **`Stepper`** (numeric field + stacked ▲/▼, accent focus ring) | `QFrame` wrapper → `QLineEdit` (`QIntValidator`/`QDoubleValidator`) + `QVBoxLayout` of two `QToolButton`s; `eventFilter` on the line edit for focus | **Optional** — focus ring via `:focus` border in QSS, or a small `paintEvent` outline for a true 2-px translucent halo | Properties panel numeric fields; export DPI/size; heatmap layout dims; image-table indices; anywhere a `QSpinBox` is too platform-variant for the design |
| **`StyledSlider`** (groove + accent sub-page + ring-on-stalk handle + focus halo) | `QSlider` (+ QSS) or `QSlider` subclass | **Optional** — QSS handles groove/sub-page/handle; subclass + `paintEvent` only if the 1-px outer accent ring around the handle must be crisp | Threshold sliders, heatmap range, bar-plot scaling — wherever a `QSlider` is exposed in the v2 chrome |
| **`IconButton`** (Lucide-icon `QToolButton`, 13/14/16 px, 1.75 stroke, hover recolor) | `QToolButton` + an SVG icon loader that does `currentColor → hex` substitution and caches per `(name, hex)` | No (QSS for bg/border; icon swap on hover via event filter or `QIcon` states) | Plot card toolbar; titlebar action buttons; section/list hover-action menus; quick-select row; everywhere a small icon-only button appears |
| **`PlotCard`** (matplotlib canvas + redesigned bottom toolbar + live `x=… y=…` mono readout; applies canonical axis styling on every draw) | `QFrame` → `FigureCanvasQTAgg` + `MplToolbar(QWidget)` (row of `IconButton`s in matplotlib groups, pan/zoom in an exclusive `QButtonGroup`) wired to a hidden `NavigationToolbar2QT`; a mono `QLabel` for coords (`mpl_connect('motion_notify_event')`) | No (matplotlib paints the figure; chrome is QSS + `IconButton`s) | Every plot surface: line/bar/scatter/distribution/heatmap tabs, smFISH, statistics, cell-gating, batch-export previews, the pop-out dock, and the figure-export editor |
| **`TitleBar`** (frameless window chrome: `BrandTile` + wordmark + breadcrumb + `StatusDot` + action `IconButton`s; window drag + edge/corner resize) | `QWidget` + `QHBoxLayout`; child `BrandTile`, `StatusDot`, breadcrumb `QLabel`s + file-chip `QLabel`; `mousePressEvent`/`mouseMoveEvent` → `windowHandle().startSystemMove()`; 6-px transparent edge/corner grips → `startSystemResize()` | **Yes** for `BrandTile` (4 quadrant circles) and `StatusDot` (filled circle + translucent halo); the bar itself is QSS + layout | Top of `AllWellApp` (replaces the current `QWidget#Sidebar` header strip and the native title bar) |
| **`StatusDot`** (filled circle + translucent halo; success/warn/danger) | `QWidget` (fixed ~10–12 px) | **Yes** — paint inner disc + outer alpha ring | "Saved" indicator in `TitleBar`; `● Connected` in the status bar; condition dots could reuse it at small size |
| **`ColorSwatchRow`** (curated 4–6 swatches, 2-px accent ring on the selected one) | `QWidget` + `QHBoxLayout` (or a single custom-painted widget); emits `colorPicked(QColor)` | **Yes** — fill rects + 1-px borders + accent ring on selection (or per-swatch `QToolButton`s with QSS, paint only the ring) | Trace/series color choice; review-image channel colors; LUT color (short lists); the "value" slot inside `CollapsibleSection` headers |
| **`SavedSelectionsList`** (rows = condition dot + name + count chip + hover-action menu) | `QListView` + `QStyledItemDelegate` (custom `paint`/`sizeHint`); backed by the existing sample-definition model | **Yes** — in the delegate's `paint()` (background by selection state, dot, name text, count chip) | Left panel under the plate; the Sample Definitions tab; replicate/ratio panels |
| **`SearchInput`** (line edit + leading search icon + trailing `⌘K` hint) | `QLineEdit` + `addAction(icon, LeadingPosition)` + a trailing `QLabel` (via `setTextMargins` + absolute placement, or a wrapping `QFrame`) | No | Properties panel header; potentially a global command search |
| **`Drawer`** (right-edge slide-in overlay; dismiss on outside-click / `Esc`; optional dim backdrop) | `QWidget` child of `AllWellApp` (or top-level `Qt.Popup` if it must sit above an OpenGL canvas); `QPropertyAnimation` on `pos`; backdrop `QWidget` at `rgba(0,0,0,0.35)`; event filter for outside-click/`Esc` | No | Hosts the Analyze workflow (the reused `AnalyzeTab` contents); reusable for any future side panel |
| **`Toast`** (floating dismissible notification: `StatusDot` + short copy; auto-fade) | top-level `QWidget` (`Qt.ToolTip | FramelessWindowHint`) parented to the main window; `QGraphicsDropShadowEffect`; `QTimer` + `QPropertyAnimation` on `windowOpacity` | No | Save confirmations, export-done, non-fatal errors (replacing some `QMessageBox` / status-label uses) |
| **`HoverToolbarOverlay`** (opacity-0-until-hover toolbar strip) | wraps a toolbar `QWidget` in a `QGraphicsOpacityEffect`; event filter on the parent card for Enter/Leave + `QPropertyAnimation` on the effect's `opacity` | No | Per-plot toolbar reveal — **only if** per-card plots survive the single-shared-canvas reversion (DESIGN_NOTES §2.8); otherwise dropped in favor of one persistent `MplToolbar` |
| **`EmptyState`** (centered icon + 1-line tip) | `QFrame` + `QVBoxLayout` (`QLabel` w/ 48-px `QPixmap` + `QLabel` tip) | No | Figure area when no wells/groups selected; any tab with a "nothing loaded" state |

---

## Build order recommendation (for Step 3+ of the porting plan)

1. **Resolve the two open questions first** — (a) single shared figure canvas vs.
   per-plot cards (changes whether `HoverToolbarOverlay` and a per-card `SegmentedControl`/
   `ChipGroup` get built, and how `PlotCard` is laid out); (b) keep multi-theme (parametrize
   `theme.Colors`) vs. single dark theme (delete theme combo + `ThemeManager`).
2. **Reference component:** `WellPlate` — riskiest, most distinctive, fully custom-painted;
   port it end-to-end (with its sidebar integration and the `wellToggled/rowSelected/
   columnSelected` signals feeding the existing selection model) and write down the pattern.
3. Then, roughly in dependency order: `IconButton` + icon loader → `SegmentedControl` /
   `ChipGroup` / `ToggleSwitch` → `CollapsibleSection` → `Stepper` / `StyledSlider` /
   `ColorSwatchRow` → `PropertiesPanel` (composes the above) → `PlotCard` + `MplToolbar` +
   matplotlib `rcParams` (the "own beast" Step 5) → `TitleBar` (+ `BrandTile`, `StatusDot`)
   + frameless window → status bar restyle → `SavedSelectionsList` → `Drawer` (+ Analyze
   move) → `Toast` → `SearchInput` / `EmptyState` polish.
4. Commit + run the app after each component (porting-plan meta-tips).

> Caveat: PySide6 isn't installed in this environment, so component work will need to be
> verified by running the app locally (screenshots), per the porting plan's "run between
> every step" rule.

---

# v3 additions — expanded scope (round 2)

`design/All-Well Additions v3.html` + `DESIGN_NOTES.md` §6 + `DESIGN_TOKENS.md`
§9 added five mid-port supplements, in response to `design/DECISIONS_NEEDED.md`.
This section folds them into the plan; Tables 1–2 and the build order above are
amended by what follows.

## A. How the additions resolve `DECISIONS_NEEDED.md`

> **⚠ This table is superseded for #1 and #4 — see `DECISIONS_NEEDED.md`.** The
> user's final calls (2026-05): **#1 = per-plot cards** (not the single-canvas
> reversion §A originally recorded — so `HoverToolbarOverlay`, per-card
> `SegmentedControl`/`ChipGroup`, and `PillTabBar` channel tabs *are* in scope);
> **#4 = keep the native window frame, restyle the in-window header** (not the
> frameless titlebar — `TitleBar`'s frameless features stay available but unused).
> #2/#3 stand as below.

| # (DECISIONS) | Status | What the v3 additions say |
|---|---|---|
| 1 — plot layout model (per-card vs single shared canvas) | ✅ **RESOLVED → per-plot cards** (user, 2026-05; overrides the §A-original "single shared canvas" reading). Each subplot = a `PlotCard` with a hover-revealed toolbar (`HoverToolbarOverlay`), a per-card view-switcher (`SegmentedControl`: Line/Bar/Scatter/Dist/Heat), and a channel chip (`ChipGroup`/`PillTabBar`); export is per-card. | (v3 had hinted at a single-canvas reversion in DESIGN_NOTES §2.4/§2.8; the v2-port decision goes per-card.) |
| 2 — dark vs white plot background | ✅ **RESOLVED → white on screen, dark "presentation" toggle** (user, 2026-05). Default plot theme = `"publication"` (white bg, `CPub`/`TRACE_PUB`) so rendered == exported; each `PlotCard` has a per-card `setPlotTheme("screen"\|"publication")` toggle in its header — `"screen"` (dark token set) is a *live preview*, not the canonical/exported state (file open lands on Publication). A "preview only" chip shows whenever Screen is active. The export dialog reads the preview state to pre-select the theme; "Transparent" is an export-only extra. |
| 3 — `PlotCard` SEM/FOV toggles + export hooks | ✅ **RESOLVED → extend `PlotCard` first** (implied by #1 — `PlotCard` is adopted for *all* plot tabs, so it must carry what Line/Bar need). The SEM/SD + FOV/Spread controls become a `SegmentedControl` (bound to `app._use_sem` / the FOV state, replacing `app._sem_btns`/`_fov_btns`) — either in the `PlotCard` header chip's popover (per §6.2's "Statistics" section idea) or a small inline strip; keep a "configure subplots" affordance; hook the per-card export dock. Build this extension *before* swapping the Line/Bar/Scatter tabs onto `PlotCard`. |
| 4 — `TitleBar` ⇒ frameless window | ✅ **RESOLVED → keep the native window frame; restyle the in-window header** (user, 2026-05; overrides the §A-original "keep custom frameless" reading and DESIGN_NOTES §6.5's frameless spec). `runtime_app`'s top bar + `all_well`'s header get the v2 colours/layout; the `TitleBar` widget's frameless mode (resize grips, window-control buttons, brand dropdown, theme switcher, drag-anywhere) is *available but unused* in v1 — a frameless mode can be revisited later. |
| 5 / 9 — selected wells: accent vs trace colours | ✅ **RESOLVED → trace colours** (= `OPEN_DECISIONS.md` #1; implemented in Phase 8.0): the left rail's selected/rep-set wells use the graph palette colour by well-position rank (`runtime_app._refresh_sidebar_map_now` / `_rank_color_well` / `_rank_color_wells`), so the plate doubles as the legend. The picker plate-maps (GROUPS rep-map, Stats) likewise show each selection/group in its rank colour. |
| 6 — `_bind_getter_setter` doesn't know `Stepper`/`SegmentedControl`/`ChipGroup`/`StyledSlider` | ✅ **RESOLVED → `bindingAdapter` protocol** (= `OPEN_DECISIONS.md` #2; implemented in Phase 6.5.1): the custom widgets expose `bindingAdapter()`, `_bind_getter_setter` gained the `hasattr` branch, `SegmentedControl`/`ChipGroup` grew `setCurrentByData`. |
| 7 — `PillTabBar` ≠ `QTabWidget` | ✅ **RESOLVED → (a)** (= `OPEN_DECISIONS.md` #3): `QTabWidget` (+ `_GroupedTabBar`) stays for the Review notebook / Plotting sub-notebook / secondary tab strip (restyled via `theme.qss()`); `PillTabBar` is reserved for the figure/plot-area channel-tabs strip only (built in the plot-area port — now in scope per #1). |
| 8 — `SavedSelectionsList` read-only | **Resolved → must become a full editable panel** | §6.3: one unified **Saved selections** panel *replaces both* the replicate-sets and bar-groups panels. Each row: drag handle · visibility eye · colour dot · inline-renamable name · count chip · kebab; rows expand to show sub-item well chips; drag-reorder == bar-plot order; right-click → Rename/Recolour/Duplicate/Hide/Move/Export/Delete; footer `From selection` + `Import…`; hidden rows fade + strike + sink. Migration: on file load both legacy lists merge into one `selections` array, bar-group order wins, name conflicts get `_v2`. So `SavedSelectionsList` is **not** sufficient as built — it's effectively a new editable widget (the current read-mostly one is at most a starting delegate). |
| 10 — `ColorSwatchRow` curated-only | **Resolved → curated + Custom escape hatch, plus a separate LUT selector** | §6.4: (i) trace-colour picker = curated 6-swatch row + a conic-gradient **Custom** tile that opens a free-form picker (SV square + hue strip + Hex/HSL/Alpha fields + per-dataset recents, capped at 8); selected swatch has a 2-px accent outline. (ii) **LUT selector** (review-image LUTs) = a trigger button showing the current LUT's gradient strip + name, opening a searchable popover with four categories (Perceptual / Diverging / Categorical / Cyclic), each row a 60-px live gradient strip + monospace name, plus reverse-LUT + reset buttons next to the trigger and a `n / m` match count in the search header. |
| 11 — `Toast` ≠ `QMessageBox` | **Still open (unchanged)** | v3 adds no notification design. `Toast` stays additive; `QMessageBox` stays for blocking/answer-bearing dialogs. |

### New gaps the additions introduce

- **`Popover` primitive** — needed in ≥3 new places (the Stats `SEM` chip popover, the LUT-selector popover, the titlebar theme-switcher popover) and arguably the row kebab menu. No such widget exists; `Drawer` is edge-anchored, not anchor-relative.
- **Free-form colour picker** (SV square + hue strip + Hex/HSL/Alpha) — net-new custom-painted widgets.
- **Gradient strip / LUT preview** — net-new custom-painted widget (used in the LUT trigger and every LUT list row).
- **Publication rcParams + `CPub`/`TRACE_PUB`** — `theme.py` needs the second token set; `PlotCard` (or whatever the figure widget becomes) needs a `mode="screen"|"publication"` axes-style path; the existing `plot_style.apply_ax_style` (and every controller that calls it) has to learn both modes.
- **"Saved selections" data-model migration** — a one-time on-load merge of `app._rep_sets` + `app._bar_groups` into a single `selections` array, with the bar-group-order-wins / `_v2`-conflict rules. Touches `well_viewer/sample_definitions.py`, `bar_models.py`, persistence (`persistence/sample_definitions.py`, `persistence/bar_groups.py`, `persistence/line_order.py`), and every consumer of `_rep_sets`/`_bar_groups`/`_rep_hidden` (the line/bar/scatter renderers, `selection_controller`, `runtime_app._refresh_sidebar_map_now`, the rep-set-mode plate behaviour, the heatmap layout flow…). This is large and orthogonal to the widget work.
- **`TitleBar` native-frame fallback mode** — a second layout (36-px sub-strip under the native bar) the widget must support, gated on an accessibility audit.

## B. New custom widgets to build in `widgets/` before Phase 8 proceeds cleanly

In rough dependency order:

1. **`Popover`** — anchor-relative floating panel (positions next to an anchor widget; dismiss on outside-click / `Esc`; optional arrow). Core primitive; used by Stats chip, LUT selector, theme switcher, kebab menus. (Distinct from `Drawer`, which is edge-docked.)
2. **`GradientStrip`** — custom-painted horizontal colour-ramp swatch (paints a `QLinearGradient` from a list of stops; reversible). Used in the LUT trigger and every LUT list row.
3. **`LutSelector`** — composes a trigger (`GradientStrip` + name + reverse + reset) with a `Popover` holding a searchable, categorised list of `GradientStrip` rows + a `n / m` match count. Backed by a LUT registry (matplotlib colormaps grouped into Perceptual/Diverging/Categorical/Cyclic).
4. **`ColorPickerPopover`** (+ sub-components `SvSquare`, `HueStrip`) — the free-form picker: an SV square (custom-painted, drag-to-pick), a hue strip, Hex/HSL/Alpha line edits, and a "recents" row (≤8). Opened from the **Custom** tile.
5. **`WindowResizeGrips`** (a.k.a. frameless-window helper) — the invisible 4–8-px edge + corner grip widgets that call `windowHandle().startSystemResize(edge)`; installs cursors. Needed by `TitleBar`'s frameless mode.
6. *(possibly)* **`PreviewBadge`** — the small "preview only" pill in the figure header when Publication mode is active. Trivial — could just be a styled `QLabel`; not strictly a new widget.

The `Screen`/`Publication` figure-header control is just a 2-segment `SegmentedControl`; the Statistics section is a `CollapsibleSection` of three `SegmentedControl`s — no new widget for those.

## C. Existing `widgets/` widgets that need extension

- **`SavedSelectionsList` → effectively rebuilt** as an editable, reorderable list: editable model with write-back to the `selections` array; drag-to-reorder; inline rename; per-row eye / colour-dot (→ recolour via `ColorSwatchRow`) / count chip / kebab (→ `Popover`/`QMenu`); expandable rows showing a `ChipGroup` of well chips; footer `From selection` / `Import…`; hidden-row styling (fade + strike + sink to bottom). Big.
- **`ColorSwatchRow` → add a "Custom" tile** that opens `ColorPickerPopover`; carry & display a per-dataset recents list; keep the 2-px accent outline on the selected swatch.
- **`TitleBar` → add**: window-control buttons (min/max/close — uses `IconButton`); the brand-logo dropdown menu (uses `Popover`/`QMenu`); the theme-switcher popover (Dark · Light · System + High-contrast); the ghost `Open` button + ⌘O; the `WindowResizeGrips`; a **native-frame fallback** layout (36-px sub-strip under the OS bar). Substantial.
- **`PlotCard` → add**: `setPlotTheme("screen"|"publication")` driving an rcParams swap between the dark token set and `CPub`/`--pub-*`; expose that state so the export dialog can read it; the figure-header row (channel/trace label + the `Screen`/`Publication` `SegmentedControl` + a `Stats · SEM` chip whose click opens a `Popover` hosting the Statistics controls). Also still owes the [gap]s from `WIDGET_GAPS.md` (configure-subplots tool, export-pipeline integration).
- **`StatusDot`** — unchanged, but now also used for the titlebar "Saved" dot + `● Connected` exactly as planned; no change needed.

## D. Which Phase 8 prompts to re-issue or modify

> I don't have the verbatim 8.1–8.5 prompt list, so this maps by *area* — please
> confirm the numbering. Nothing here should be built before you've reviewed it.

| Area / prompt | Status | What changes |
|---|---|---|
| **Left rail / well-plate selector** (≈ 8.1) | ✅ **Done** | Step 1 done; DECISIONS #5/#9 done — the rail's selected wells now use **trace colours by well-position rank** (plate ↔ plot match; "the plate is the legend"). All other plate-maps (GROUPS rep-map, Statistics, image-table picker, preview picker) migrated to `WellPlateSelector` too — `WellButton` / `build_plate_grid` / `_plate_apply_*` are deleted. |
| **Right-side property panel** (≈ 8.2) | "Reference area" port done | **Re-issue / extend:** add the new **Statistics** section (§6.2) between Data and Appearance (`Error bars` / `Across` / `Show`), populate `CollapsibleSection.setValueWidget` header previews (the port currently populates none — §2.5 wants them, §6.2 wants `SEM · spread`), and decide the binding question (DECISIONS #6) since the new section needs it. Also still open: is the Properties panel the per-figure export dock (current) or a future global rail (§2.5)? |
| **Plot / figure area — matplotlib** (≈ 8.3) | ✅ **Done** (per-card model — DECISIONS #1; per-card live `Publication ↔ Screen` toggle — DECISIONS #2/#3) | Every plot tab (Line / Bar / Scatter cells & agg / Distribution / Heat Map) is now a `widgets.PlotCard` (card chrome + new `widgets.MplToolbar` — home / back-fwd / pan-zoom / save + `x/y` readout). Header carries the per-card view-switcher (`Line · Bar · Scatter · Dist · Heat`, switches the Plotting sub-notebook tab), the `Publication ↔ Screen` `SegmentedControl` (with the "preview only" chip in Screen mode), and the stats chip (currently hidden — error band lives on the controls row below). Controls row beneath the header hosts the shared SEM/SD + FOV/Spread toggles via the new `ui_helpers.make_band_controls`. `plot_style.tokens_for(ax)` + the `ax.figure._plot_card` back-ref drive theme-aware colours through `apply_ax_style`, the line renderer's legend / placeholder text, the bar renderer's titles + scipy placeholder, and `figure_export_editor.apply_export_style_to_current` (was the hardcoded-"black"s that overrode everything). Dead orchestrator args (`plot_bg`/`plot_spn`/`txt_pri`/`txt_mut`/`well_colors`) dropped. **Not yet:** trace-palette swap (`TRACE_PUB` in publication; needs a coordinated `WELL_COLORS` rework — kept rank-based for now); stats-chip wiring; multi-card / "Plot 1 + Plot 2" comparison scope; export dialog reading the preview state. |
| **Main window / titlebar / app shell** (≈ 8.4, if not yet issued) | Not started | **Scope (DECISIONS #4 = keep native frame):** restyle the in-window header strip (`runtime_app` top bar + `all_well` header) to v2 colours/layout — breadcrumb / file chip / `StatusDot` / action `IconButton`s sit *beneath* the native title bar; no frameless mode, no resize grips, no window-control buttons. The `TitleBar` widget's frameless features remain available for a future revisit. Smaller/lower-risk than the §6.5 frameless spec. |
| **Sample Definitions / Bar Plots tabs** (≈ 8.5 or wherever those land) | Not started | **Re-issue with the unified design:** the two legacy panels (replicate-sets, bar-groups) collapse into one **Saved selections** panel (§6.3) backed by the merged `selections` model + the on-load migration. The plate-maps in those tabs become "pick wells for the active saved-selection row". This is the largest non-widget data change in the round-2 scope. |
| **Image-table / Segmentation tabs** | Not started | The review-image LUT picker (`QComboBox` today) becomes the §6.4 **`LutSelector`**; trace-colour pickers anywhere become `ColorSwatchRow` + the **Custom** escape hatch (§6.4). |

## E. Recommended order, revised

0. **You decide:** DECISIONS #5/#9 (accent vs trace), #6 (binding-layer policy), and confirm the 8.1–8.5 mapping above.
1. Build the new primitives: `Popover` → `GradientStrip` → `WindowResizeGrips`; then `LutSelector` (needs `Popover`+`GradientStrip`) and `ColorPickerPopover`/`SvSquare`/`HueStrip` (+ extend `ColorSwatchRow` with the Custom tile). Gallery entries + `__main__` demos as usual.
2. Extend `PlotCard` for the screen/publication theme + figure-header row; add `theme.CPub`/`TRACE_PUB`; rework `plot_style.apply_ax_style` for both modes (no controllers touched yet).
3. Re-issue & do the **plot/figure-area port** (≈8.3) with the above in hand.
4. Re-issue & extend the **Properties-panel port** (≈8.2): add the Statistics section (decide binding first), populate header previews.
5. Build the editable **`SavedSelectionsList`** + the `selections` data-model migration, then re-issue the **Sample Definitions / Bar Plots port** (≈8.5).
6. Extend **`TitleBar`** (+ `WindowResizeGrips`, the dropdown/theme popovers, the native-frame fallback) and re-issue the **app-shell port** (≈8.4).
7. The remaining `WellPlateSelector` migration (Steps 2–8 of `WELL_SELECTOR_GAP.md`) for the other six plate-maps slots in alongside step 5 (Sample Definitions / Bar Plots) and step 6 (image-table / segmentation), since those are where the legacy grids live.

> Same caveat: no PySide6 in this environment — every widget/port step needs a
> local run + screenshots before it's trusted.
