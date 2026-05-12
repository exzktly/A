# Phase 6.5 — widget-building round (before Phase 8 resumes)

A focused round to build the new widgets and extensions surfaced by the v3
additions + `OPEN_DECISIONS.md`, so that when Phase 8 (the per-area port)
resumes it has a complete, demonstrated widget library to draw on. **Phase 8
does not resume until all four deliverables below are met.**

## Deliverables (exit criteria)

1. **All new widgets built and demonstrated in `widgets/gallery.py`** — `Popover`,
   `GradientStrip`, `WindowResizeGrips`, `LutSelector` (+ a LUT registry),
   `ColorPickerPopover` (+ `SvSquare`, `HueStrip`).
2. **All extensions to existing widgets completed, with the extended
   functionality also demonstrated in `gallery.py`** — `ColorSwatchRow` ("Custom"
   tile + recents), `SavedSelectionsList` (editable / reorderable / per-row
   actions / expandable / footer), `TitleBar` (window controls + brand dropdown +
   theme-switcher popover + ghost Open + resize-grip integration + native-frame
   fallback), `PlotCard` (Screen/Publication theme swap + figure-header row +
   Stats popover), and `theme.py` (`CPub` + `TRACE_PUB`).
3. **The `_bind_getter_setter` extension applied** per `OPEN_DECISIONS.md` #2
   (option b — `bindingAdapter()` protocol on the custom widgets; one new
   `hasattr` branch in `well_viewer/views/export_style_sidebar_view.py`).
4. **Every custom widget that participates in binding-driven panels passes a
   binding test** — a minimal example binding the widget to a model property and
   showing changes propagate both ways, for `ToggleSwitch`, `SegmentedControl`,
   `ChipGroup`, `Stepper`, `StyledSlider`.

## Working rules (carried over)

- One new widget per commit; extensions one commit each (or split if large, e.g.
  `SavedSelectionsList`). Every widget keeps a `__main__` standalone demo. Every
  new/extended widget gets a card in `widgets/gallery.py`. `python -m py_compile`
  on every change; **runtime QA (run the demo / `gallery.py`, screenshot) is
  required before a sub-phase is "done" — this environment has no PySide6, so
  that step happens on your machine.**
- Styling stays from `theme.py` tokens (+ `theme.qss()` object names) — no new
  hardcoded hex. New custom widgets carry their own per-widget QSS built from
  tokens, scoped to their own `objectName`.
- No app-side wiring beyond the `_bind_getter_setter` branch (deliverable 3). The
  port itself (Phase 8) consumes these widgets later.

## Resolved clarifications

**C4 — `startSystemResize` on macOS, frameless PyQt6/PySide6.** It is *unreliable*
on macOS. `QWindow.startSystemResize(Qt.Edge)` works well on Windows and
Wayland; on the Cocoa (macOS) platform it has a long history of being a no-op or
inconsistent for `Qt.FramelessWindowHint` windows (whereas `startSystemMove`
works there). **Decision:** `WindowResizeGrips` (6.5.4) ships with a `mode`
argument — `"system"` (calls `startSystemResize`, the default on Windows/Linux)
or `"manual"` (the grip widgets compute the new `window().geometry()` from the
drag delta themselves — always works, just no OS snap/animation). On macOS the
default is `"manual"` until someone verifies `startSystemResize` works on the Qt
build in use. Both modes are exercisable from the widget's `__main__` demo (a
toggle), so the gallery / a frameless test window can demonstrate either.

**C5 — native-frame fallback activation (6.5.9).** The actual switch is the
`TitleBar.setFramelessMode(bool)` API (the host calls it; `True` = custom
frameless chrome, `False` = native OS frame + a 36-px sub-strip carrying the
breadcrumb + actions). *Which mode the app picks* is decided by a small
`widgets._window_chrome.should_use_frameless() -> bool` helper, resolved in this
order: (1) explicit env override `ALLWELL_FRAMELESS=0|1` → (2) a persisted user
preference (`settings.json` key `"frameless"` if present) → (3) an accessibility
probe — if `QAccessible.isActive()` is `True` (an assistive-tech client is
connected) it returns `False` (fall back to native), per `DESIGN_NOTES` §6.5 →
(4) platform default: `True` everywhere (on macOS, "frameless" still means the
native traffic-lights show at the left; the rest of the bar is custom). Testable
in `gallery.py`: the `TitleBar` card has a toggle that calls `setFramelessMode()`
directly so both layouts are visible, and a read-out of what `should_use_frameless()`
currently resolves to (with the env var honoured); the helper has its own
`__main__` that prints the resolution + each input.

---

## Sub-phases (in order)

| # | Sub-phase | Builds / changes | Depends on | Deliverable(s) |
|---|---|---|---|---|
| 6.5.1 | **Foundations & binding contract** | `theme.py`: add `CPub` class + `TRACE_PUB` list (DESIGN_TOKENS §9.2; rcParams-only, no QSS change). Add `bindingAdapter()` (returns `(getter, setter, change_signal)`) to `SegmentedControl`, `ChipGroup`, `Stepper`, `StyledSlider`; add `setCurrentByData(value)` to `SegmentedControl`/`ChipGroup`; confirm `ToggleSwitch` (already bindable as a `QCheckBox`) — give it a `bindingAdapter` too for uniformity. Extend `ExportStyleSidebar._bind_getter_setter` with the `if hasattr(w, "bindingAdapter")` branch. Add the **binding test harness** (`widgets/tests/test_binding.py` if pytest is available; else `widgets/binding_check.py` with a `__main__` that runs the round-trips and prints PASS/FAIL): a tiny model object (a property + a `<prop>Changed` signal, or a dict-backed pseudo-model) bound to each of the five widgets, asserting model→widget, widget→model, and no feedback loop. | — | 3, 4 |
| 6.5.1a | **🔒 GATE — binding-harness runtime QA (user)** | After 6.5.1 lands, *you* pull the branch and run the binding tests on your machine, confirming the harness is green against all five already-bindable widgets (`SegmentedControl`, `ChipGroup`, `Stepper`, `StyledSlider`, `ToggleSwitch`). **No 6.5.2 commit lands until you confirm.** Non-blocking on the implementation side — 6.5.2 work may be *staged* (drafted locally / on a scratch branch) in the meantime, but it is **not committed/pushed** to this branch until the gate clears. If the harness has issues, fixes go into 6.5.1 (not 6.5.2) and the gate is re-run. | 6.5.1 | gate on 3, 4 |
| 6.5.2 | **`Popover`** (core primitive) | New `widgets/popover.py` — an anchor-relative floating panel: positions next to an anchor widget (above/below/left/right with auto-flip), `setContentWidget(w)`, dismiss on outside-click / `Esc`, optional arrow, soft drop shadow (`QGraphicsDropShadowEffect`). `__main__` + gallery card. | 6.5.1a (gate clear) | 1 |
| 6.5.3 | **`GradientStrip`** | New `widgets/gradient_strip.py` — custom-painted horizontal colour ramp from a list of `(stop, color)` pairs (or a callable); `setReversed(bool)`; `setStops(...)`. Used by `LutSelector` (trigger + every list row). `__main__` + gallery card. | — | 1 |
| 6.5.4 | **`WindowResizeGrips`** | New `widgets/window_resize_grips.py` — installs 8 invisible ~6–8 px grip widgets (4 edges, 4 corners) on a top-level window, sets the right resize cursors. Two modes (see **C4**): `"system"` → `window().windowHandle().startSystemResize(edge)`; `"manual"` → compute the new `window().geometry()` from the drag delta. Default `"system"` on Windows/Linux, `"manual"` on macOS. API: `attach(window, mode="auto")` / `detach()`; `mode="auto"` picks per-platform. `__main__` demo = a small frameless test window with a mode toggle. (Gallery: documented + a stand-in card — a frameless window can't be embedded in the gallery; the `__main__` demo is the live test.) | — | 1 |
| 6.5.5 | **`LutSelector`** (+ LUT registry) | New `widgets/lut_selector.py` — a LUT registry grouping matplotlib colormaps into Perceptual / Diverging / Categorical / Cyclic; a trigger button = `GradientStrip` (current LUT) + name + a reverse-LUT toggle + a reset button; clicking it opens a `Popover` with a search field (`n / m` match count in the header) over a categorised list of rows, each row = a `GradientStrip` + monospace name. Signal: `lutChanged(name: str, reversed: bool)`. `setLut(name, reversed)`. `__main__` + gallery card. | 6.5.2, 6.5.3 | 1 |
| 6.5.6 | **`ColorPickerPopover`** (+ `SvSquare`, `HueStrip`) | New `widgets/color_picker_popover.py` — `SvSquare` (custom-painted saturation/value gradient for the current hue, drag-to-pick), `HueStrip` (custom-painted hue ramp, drag), `QLineEdit`s for Hex / HSL / Alpha (validated, two-way with the squares), a per-dataset "recents" row (≤8 swatches), all hosted in a `Popover`. Signals: `colorPicked(QColor)` (live) + `colorCommitted(QColor)` (on close/Enter). `setColor(QColor)`, `setRecents(list)`. `__main__` + gallery card. | 6.5.2 | 1 |
| 6.5.7 | **`ColorSwatchRow` extension** — Custom tile + recents | Extend `widgets/color_swatch_row.py` — add an optional conic-gradient "Custom" tile at the end of the swatch row that opens `ColorPickerPopover` (the picked colour becomes the current selection and prepends to recents); carry & display a recents list (≤8); keep the 2-px accent outline on the selected swatch; emit `colorPicked(QColor)` whether the colour came from a curated swatch, a recent, or the picker. Gallery: a row showing curated swatches + recents + the Custom tile + the picker opening. | 6.5.6 | 2 |
| 6.5.8a | **🔒 GATE — selections-model contract (user)** | **Before building 6.5.8:** produce `design/SELECTIONS_MODEL_CONTRACT.md` defining the exact shape of the `selections` model the widget reads/writes — fields, types, invariants, the per-entry id scheme, ordering semantics, and how the Phase-8 migration (`_rep_sets` + `_bar_groups` → this model) maps onto it — so the "stand-in model" *is* the target the Phase-8 migration will hit, not a throwaway. **No 6.5.8 commit lands until you approve the contract.** Revisions go into the doc, not the widget. | 6.5.6 | gate on 2 |
| 6.5.8 | **`SavedSelectionsList` extension** — editable / reorderable | Effectively a rebuild of `widgets/saved_selections_list.py` against the model defined by `SELECTIONS_MODEL_CONTRACT.md` (6.5.8a): per-row drag handle (drag-to-reorder), visibility eye, colour dot (recolour via `ColorSwatchRow`), inline-renamable name (delegate editor or a `QLineEdit` overlay), count chip, kebab → a `Popover`/`QMenu` (Rename / Recolour / Duplicate / Hide / Move up-down / Export / Delete); rows expand to a `ChipGroup` of well chips; footer with `From selection` + `Import…` buttons; hidden rows fade + strike-through + sink to the bottom. Signals: `entryActivated(id)`, `entryRenamed(id, name)`, `entryRecoloured(id, color)`, `entryVisibilityToggled(id, visible)`, `entryDuplicated(id)`, `entryDeleted(id)`, `entryExportRequested(id)`, `orderChanged([id,…])`, `addFromSelectionRequested()`, `importRequested()`. (The actual `_rep_sets` + `_bar_groups` → `selections` data-model migration is **Phase-8 app work**, *not* 6.5 — 6.5 delivers the widget + the contract.) Gallery: a populated, editable list. | 6.5.8a (contract approved), 6.5.2, 6.5.6 (recolour), existing `ChipGroup` | 2 |
| 6.5.9 | **`TitleBar` extension** | Extend `widgets/title_bar.py` — add: window-control buttons (min / max / close as `IconButton`s; close hovers to `--danger`; macOS-mode hides them, leaving room for native traffic lights); the brand-logo dropdown (a `Popover`/`QMenu`: Open / Recent / Preferences / About / Quit); the theme-switcher (sun/moon `IconButton` → `Popover` with Dark / Light / System tiles + a High-contrast toggle); the ghost `Open` button + a ⌘O shortcut; integrate `WindowResizeGrips` (enabled in frameless mode); a **native-frame fallback** mode — `setFramelessMode(bool)` (see **C5** for how the app *chooses*: `widgets._window_chrome.should_use_frameless()` = env `ALLWELL_FRAMELESS` → pref → accessibility probe → platform default); when off, the breadcrumb + actions render as a 36-px sub-strip beneath the OS bar. Gallery: the titlebar demo updated to show the window controls + dropdown + theme popover + a `setFramelessMode()` toggle + a read-out of `should_use_frameless()`. | 6.5.2, 6.5.4 | 2 |
| 6.5.10 | **`PlotCard` extension** — Screen/Publication theme + figure-header row | Extend `widgets/plot_card.py` — `setPlotTheme("screen"|"publication")` swaps the figure's rcParams between the dark token set and `theme.CPub`/`TRACE_PUB` (`figure.facecolor`, `axes.facecolor`, `axes.edgecolor`, `xtick/ytick.color`, `text.color`, `grid.color`, the trace prop-cycle) and redraws; `plotTheme()` exposes the state (the export dialog reads it later, in Phase 8). Add the figure-header row: a channel/trace label + a 2-segment `SegmentedControl` (`Screen` / `Publication`) + a "preview only" badge shown only in publication mode + a `Stats · SEM` chip whose click opens a `Popover` hosting the three Statistics controls (`Error bars` / `Across` / `Show` as `SegmentedControl`s — optionally wrapped in a `CollapsibleSection`). Signals: `plotThemeChanged(str)`, `statsChanged(dict)`. (The matplotlib `rcParams`-set-once-at-startup, the `plot_style.apply_ax_style` rework, and re-wiring every controller that styles axes are **Phase-8 plot-area work**, not 6.5.) Gallery: a `PlotCard` with the toggle doing a live light/dark swap + the Stats popover. | 6.5.1 (`CPub`/`TRACE_PUB`), 6.5.2 (`Popover`), existing `SegmentedControl`/`CollapsibleSection` | 2 |
| 6.5.11a | **🔒 GATE — gallery layout proposal (user)** | **Before reorganizing/QA:** produce `design/GALLERY_LAYOUT.md` proposing the final `widgets/gallery.py` organization — sections (e.g. "Inputs", "Pickers", "Containers / overlays", "Plot & figure", "Window chrome"), the order of widgets within each, the sectioning UI (collapsible section headers? a left index? tabs?), and how the host-dependent demos (`Popover`, `Toast`, `Drawer`, `WindowResizeGrips`, frameless `TitleBar`) are surfaced given a gallery card can't host a top-level window. **No gallery reorganization happens until you approve.** | 6.5.2–6.5.10 | gate on 1, 2 |
| 6.5.11b | **Gallery consolidation & sign-off** | Reorganize `widgets/gallery.py` per the approved `GALLERY_LAYOUT.md` so it shows a card for **every** new widget (6.5.2–6.5.6) and demonstrates **every** extension (6.5.7–6.5.10) — Custom tile, editable selections list, titlebar with controls/dropdown/theme/fallback, `PlotCard` theme toggle + Stats popover, `LutSelector`, `ColorPickerPopover`, `Popover`, `GradientStrip`, `WindowResizeGrips` (documented). Run `python widgets/gallery.py`, screenshot, fix any layout/visual issues. Confirm the binding test (6.5.1) still passes. Then Phase 6.5 is complete and Phase 8 resumes. | 6.5.11a (layout approved) | 1, 2 |

## Order rationale (dependency chain)

`6.5.1` (foundations + binding — small, unblocks #3/#4) → **`6.5.1a` 🔒 gate**
(your runtime QA of the binding harness) → `6.5.2 Popover` → `6.5.3 GradientStrip`
+ `6.5.4 WindowResizeGrips` (independent leaves, parallel-OK) → `6.5.5 LutSelector`
(needs 2+3) → `6.5.6 ColorPickerPopover` (needs 2) → `6.5.7 ColorSwatchRow ext`
(needs 6) → **`6.5.8a` 🔒 gate** (`SELECTIONS_MODEL_CONTRACT.md` + your approval)
→ `6.5.8 SavedSelectionsList ext` (needs 8a + 2 + 6) → `6.5.9 TitleBar ext`
(needs 2+4) → `6.5.10 PlotCard ext` (needs 1+2) → **`6.5.11a` 🔒 gate**
(`GALLERY_LAYOUT.md` + your approval) → `6.5.11b gallery consolidation` → Phase 8.

> Three hard hand-offs in the round, each blocking the *next* committed step
> until you confirm: **6.5.1a** (binding harness runs green), **6.5.8a**
> (selections-model contract approved), **6.5.11a** (gallery layout approved).
> Implementation may *stage* (draft locally, not push) the gated step's work in
> the interim, but the commit is held until the gate clears; revisions to a
> rejected gate go into the gate's doc/foundation, not the downstream widget.

## Explicitly NOT in Phase 6.5 (these stay Phase 8)

- The decision-#1 colour fix in `runtime_app._refresh_sidebar_map_now` (per-well
  branch → graph-palette colours by well-position rank instead of `ACCENT`) —
  it's an app-side change (~1 line + sourcing the graph's palette/ordering); it
  lands as part of the **left-rail finish** in Phase 8.
- The `_rep_sets` + `_bar_groups` → unified `selections` data-model migration
  (the on-load merge, bar-group-order-wins, `_v2` conflict rule, and updating
  every consumer) — **Sample-Definitions / Bar-Plots Phase-8 port**.
- The matplotlib `rcParams`-at-startup + `plot_style.apply_ax_style` rework +
  routing every controller through it; the export-dialog↔preview-state wiring —
  **plot/figure-area Phase-8 port**.
- Wiring the new Statistics section into the actual Properties panel, populating
  `CollapsibleSection.setValueWidget` previews — **properties-panel Phase-8 port**.
- Making `AllWellApp` a frameless window and hosting the extended `TitleBar` in it
  — **app-shell Phase-8 port**.
- Migrating the other six plate-maps off the legacy `WellButton` grid
  (`WELL_SELECTOR_GAP.md` Steps 2–8) — **Phase-8**, alongside the relevant tabs.
- Confirming the 8.1–8.5 prompt numbering — your call, before Phase 8 resumes.

## Progress log

Updated as each sub-phase lands. `done` = committed + (where it applies) the
working-rules `py_compile` check passed; **runtime QA still happens on your
machine** unless noted.

| Sub-phase | Status | Commit / note |
|---|---|---|
| 6.5.1 — foundations & binding contract | **done** (code, not runtime-verified) | `theme.CPub` + `TRACE_PUB`; `bindingAdapter()` on `ToggleSwitch` / `SegmentedControl` / `ChipGroup` / `Stepper` / `StyledSlider`; `setCurrentByData` on `SegmentedControl` / `ChipGroup` (+ `checkedData`/`setCheckedData` on `ChipGroup`); `_bind_getter_setter` gained the `bindingAdapter` branch; `widgets/binding_check.py` harness added. `py_compile` clean. |
| 6.5.1a — binding-harness runtime QA (user) | **✅ confirmed PASS** (user, 2026-05-12) | `python widgets/binding_check.py` — all green. Gate clear; 6.5.2 onward unblocked. |
| 6.5.2 — `Popover` | **done** (code, not runtime-verified) | `widgets/popover.py` — `Qt.Popup` frameless anchor-relative panel: `setContentWidget` / `popup(anchor, side, align, gap)` with auto-flip + screen-clamp, dismiss on outside-click / Esc, soft drop shadow on a `#PopoverFrame` card, `opened`/`closed` signals; `__main__` demo (6 side/align buttons) + a `Popover` card in `gallery.py`. `py_compile` clean. |
| 6.5.3 — `GradientStrip` | **done** (code, not runtime-verified) | `widgets/gradient_strip.py` — custom-painted left→right colour ramp from `(pos, colour)` stops / a flat colour list / a `t→colour` callable; `setStops` / `setSamples` / `setReversed` / `colorAt`; font-relative size; `__main__` demo + `GradientStrip` card in `gallery.py`. `py_compile` clean. |
| 6.5.4 — `WindowResizeGrips` | **done** (code, not runtime-verified) | `widgets/window_resize_grips.py` — `QObject` helper that installs 8 invisible edge/corner grip widgets on a top-level frameless window with the right resize cursors; modes `system` (`startSystemResize`) / `manual` (geometry-delta) / `auto` (manual on darwin else system); repositions on resize, stays on top; `attach`/`detach`/`setMode`/`mode`. `__main__` demo = a frameless test window with a mode toggle; `WindowResizeGrips` card in `gallery.py` opens that test window (can't embed a frameless window in a card). `py_compile` clean. |
| 6.5.5 — `LutSelector` | **done** (code, not runtime-verified) | `widgets/lut_selector.py` — matplotlib-colormap LUT registry (Perceptual / Diverging / Categorical / Cyclic; fallback stops when matplotlib is absent); trigger button = `GradientStrip` + name + a reverse-LUT `QToolButton#LutReverse` (⇄) + a reset `QToolButton#LutReset`; clicking opens a `Popover` with a `SearchInput` (`n / m` match count in the hint) over categorised `_LutRow`s (`GradientStrip` + monospace name), filter hides empty category headers; `setLut(name, reversed)` / `lut()` / `isReversed()` / `availableLuts()`; `lutChanged(name, reversed)` signal. `__main__` demo + `LutSelector` card in `gallery.py`. `py_compile` clean. |
| 6.5.6 — `ColorPickerPopover` | **done** (code, not runtime-verified) | `widgets/color_picker_popover.py` — `SvSquare` (custom-painted hue→white horizontal × transparent→black vertical, drag-to-pick ring), `HueStrip` (12-stop vertical hue ramp, drag), validated Hex (`QRegularExpressionValidator`) + Alpha (`QIntValidator`) `QLineEdit`s, a `ColorSwatchRow` recents row (≤8), all hosted in a `Popover`; `setColor` / `color()` / `setRecents` / `recents()`; `colorPicked(QColor)` live + `colorCommitted(QColor)` on Return / recent-click / dismiss (prepends to recents). Docstring notes the `Qt.Popup` keyboard-forwarding caveat for the line edits. `__main__` demo + `ColorPickerPopover` card in `gallery.py`. `py_compile` clean. |
| 6.5.7 — `ColorSwatchRow` ext | **done** (code, not runtime-verified) | `widgets/color_swatch_row.py` — added an opt-in conic-gradient **"Custom"** tile at the end of the row (opens `ColorPickerPopover` anchored at the tile; the committed colour becomes current + prepends to recents) and a recents group (≤`max_recents`); `setAllowCustom` / `allowCustom` / `setRecents` / `recents` / `addRecent`; selection now tracked by colour (not index) so the 2-px accent ring follows curated **and** recent tiles; `colorPicked(QColor)` fires for curated / recent / picker (live + commit); curated-index API (`currentIndex` / `setCurrentIndex`) kept. `__main__` demo + the `ColorSwatchRow` gallery card now shows curated + recents + Custom tile + a read-out. `py_compile` clean. |
| 6.5.8a — selections-model contract (user gate) | **✅ approved** (user, 2026-05-12) | `design/SELECTIONS_MODEL_CONTRACT.md` — unified `selections` list shape, invariants, the `_rep_sets`+`_rep_hidden`+`_bar_groups` → `selections` migration (bar-group order wins, `_v2` on name clash), persistence (`pipeline_info.json::sample_definitions` `schema_version: 2`), Phase-8 inverse map. 5 open questions resolved per recommendation (uuid id; `[wells]` for free rep-sets; keep `labels` reserved; `_v2` suffix; persist `current_id`). 6.5.8 unblocked (still needs 6.5.2 + 6.5.6 built). |
| 6.5.8 — `SavedSelectionsList` ext | **done** (code, not runtime-verified) | `widgets/saved_selections_list.py` — rebuilt against `SELECTIONS_MODEL_CONTRACT.md`: holds a working `list[dict]` (`setSelections`/`selections`/`setCurrentId`/`currentId`); a `QScrollArea` of `_SelectionRow`s — each = chevron-expand · drag handle (drag-to-reorder, deferred-`_move` on release so the row can be safely rebuilt) · visibility eye (toggles `hidden`) · colour dot (→ `Popover` of `ColorSwatchRow` recolour) · inline-renamable name (`QLineEdit` swap, `_v2` on collision) · count chip (`len(wells)`) · kebab `QMenu` (Rename / Recolour / Duplicate / Hide / Move up / Move down / Export / Delete); expanded row shows a read-only `ChipGroup` of well chips; hidden rows fade + strike-through and sink to the bottom of the *displayed* order (stored index preserved); footer = *From selection* + *Import…* buttons. Granular signals (`entryActivated`/`entryRenamed`/`entryRecoloured`/`entryVisibilityToggled`/`entryDuplicated`/`entryDeleted`/`entryExportRequested`/`orderChanged`/`addFromSelectionRequested`/`importRequested`) + coarse `selectionsChanged(list)`; enforces unique id (`uuid4().hex[:8]`) / unique name / `#RRGGBB`. `__main__` demo + the `SavedSelectionsList` gallery card now feeds a contract-shaped `list[dict]` (one `hidden`, some with `replicates`). `py_compile` clean. (The actual `_rep_sets`+`_bar_groups` → `selections` data migration is Phase-8 app work, not 6.5.) |
| 6.5.9 — `TitleBar` ext | **done** (code, not runtime-verified) | `widgets/title_bar.py` — added: window-control buttons (min / max / close `IconButton`s; `#TitleClose:hover` → `--danger`; hidden on macOS / native mode); a clickable brand → `QMenu` (Open… / Open recent ▸ / Preferences… / About / Quit) with `setRecentFiles`; a ghost **Open** button + a ⌘O `QShortcut` (`QKeySequence.Open`); a theme-switcher `IconButton` (sun) → `Popover` with Dark / Light / System tiles + a High-contrast `ToggleSwitch`; `WindowResizeGrips` auto-attached to the top-level window in frameless mode (re-attached on `showEvent`, detached in native mode); `setFramelessMode(bool)` / `isFramelessMode()` — native mode shrinks the bar to a ~36 px sub-strip, makes drag inert, hides window buttons, detaches grips; the **initial** mode comes from new `widgets/_window_chrome.py` `should_use_frameless()` (env `ALLWELL_FRAMELESS` → `set_frameless_preference()` → accessibility probe [`QT_ACCESSIBILITY` / Win `SPI_GETHIGHCONTRAST`] → platform default) with `frameless_source()` for a read-out. New signals: `openRequested` / `recentFileRequested(str)` / `preferencesRequested` / `aboutRequested` / `quitRequested` / `themeChangeRequested(str)` / `highContrastToggled(bool)`; existing API (`setBreadcrumb` / `setSaved` / `addAction` / `setShowWindowButtons`) preserved. `__main__` demo updated (frameless↔native toggle, signal read-out, `should_use_frameless()` line); the `TitleBar` gallery card now shows the controls / brand menu / theme popover / `setFramelessMode` toggle / a `should_use_frameless()` + `frameless_source()` read-out. `py_compile` clean. |
| 6.5.10 — `PlotCard` ext | not started | |
| 6.5.11a — gallery layout proposal (user gate) | not started | |
| 6.5.11b — gallery consolidation & sign-off | not started | |
