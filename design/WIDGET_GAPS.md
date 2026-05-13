# Widget gap audit

Every custom widget in `widgets/` checked against the legacy widget it is meant
to replace (or, where there is no legacy counterpart, against the closest legacy
pattern). For each: what the legacy thing does, what the custom widget covers,
and the **load-bearing behaviours the custom replacement does not handle**.

Nothing fixed here — this is the list to triage from.

Scope notes:
- "Legacy" = what's in the current `well_viewer/` codebase today (after the
  Step-1 left-rail swap and the `WellButton` restyle).
- For widgets that are net-new in the v2 design (no legacy widget existed),
  the gap is "vs what the v2 mockup needs" or "vs the legacy ad-hoc pattern",
  noted as such.
- `WellPlateSelector` is audited in depth in `design/WELL_SELECTOR_GAP.md`
  (G1–G12 + the Step-1 status); only a one-line pointer is repeated here.

Severity tags: **[blocker]** = would break a current feature if swapped in as-is;
**[gap]** = missing capability, not currently exercised by the one place (if any)
the widget is wired; **[divergence]** = behaves differently on purpose, confirm
it's intended; **[n/a]** = no legacy behaviour to lose.

---

## 1. `ToggleSwitch` (widgets/toggle_switch.py) — legacy: plain `QCheckBox`

`ToggleSwitch` subclasses `QCheckBox`, so it inherits `isChecked()` /
`setChecked()` / `toggled(bool)` / `stateChanged(int)` / keyboard handling /
`text()` and is a genuine drop-in for the binding code that does
`isinstance(w, QCheckBox)` (e.g. `ExportStyleSidebar._bind_getter_setter`,
`distribution_tab_view` which uses `stateChanged`).

Gaps:
- **[gap] No tri-state.** `QCheckBox.setTristate(True)` / `PartiallyChecked` is
  not modelled — `ToggleSwitch` is strictly binary. (Not used anywhere today —
  the only `setTristate` hit is none — so currently moot.)
- **[divergence] The text label is custom-painted**, not laid out by the style.
  Side effects: no automatic eliding, no mnemonic underline from `&`, the hit
  area is the whole widget (we override `hitButton`), and `sizeHint` is computed
  from font metrics rather than the style. Visually fine; just not "a QCheckBox
  with a different indicator".
- **[gap] `setIcon()` on the checkbox is ignored** (the indicator is the
  painted switch). Not used today.
- **[gap] No focus-visible policy beyond a painted ring**; QSS `:focus` rules on
  `QCheckBox` won't affect it (it's fully `paintEvent`-drawn).

Verdict: safe drop-in for current usage; the only "real" gap (tri-state) is
unused.

---

## 2. `CollapsibleSection` (widgets/collapsible_section.py) — legacy: `QGroupBox`

No true legacy "collapsible section with header preview" exists. The closest
legacy thing is `QGroupBox` (e.g. `QGroupBox#ImageTableRowOptions` in
`views/image_table_grid_view.py`, the `QGroupBox` in `export_style_sidebar_view`
before the port). `CollapsibleSection` adds collapse/expand + the value-preview
slot, which `QGroupBox` never had.

Gaps (vs `QGroupBox`):
- **[gap] No checkable group-box semantics.** `QGroupBox.setCheckable(True)`
  (a checkbox in the title that enables/disables the contents) isn't modelled.
  Not used today.
- **[gap] No title alignment / flat options** (`QGroupBox.setAlignment`,
  `setFlat`). Minor.
- **[gap] The body's `maximumHeight` is animated**, so a child that wants to
  be taller than its `sizeHint` *after* the section is first shown won't grow
  until the next expand toggle (the animation target is recomputed on toggle,
  not on child resize). Containers with dynamic content (e.g. the reorder lists
  added in the ported Properties panel) work because they're added before first
  show, but a section whose content changes height while expanded would clip.
  → would need a `relayout()` / size-change hook.
- **[gap] No nesting story tested** — a `CollapsibleSection` inside another
  works structurally but the inner one's animated `maximumHeight` and the
  outer's `sizeHint` recompute aren't coordinated.

Verdict: net-new capability; the height-recompute gap is the one that could
bite if a section's content changes size while open.

---

## 3. `SegmentedControl` (widgets/segmented_control.py) — legacy: ad-hoc button rows

No legacy "segmented control" widget. The legacy equivalents are loose
`QPushButton` rows: the **SEM/SD** toggle (`app._sem_btns`, `_toggle_sem`), the
**Error Band / FOV / Spread** buttons (`attach_plot_toolbar` with `with_fov`),
the export-profile picker (`QComboBox`), etc.

Gaps (vs replacing those patterns):
- **[gap] No "registry" pattern.** The legacy SEM button lives in *every* plot
  toolbar and `_toggle_sem` updates them all via `app._sem_btns`. A
  `SegmentedControl` is a single widget; if the same logical control appears in
  N places you'd need N controls kept in sync by the app (not the widget's job,
  but worth knowing it doesn't help).
- **[gap] No disabled-with-tooltip-explaining-why** beyond `setSegmentEnabled` +
  whatever tooltip you set; the legacy FOV button auto-disables when replicate
  sets are active with state managed by `_refresh_fov_btn_state` — that logic
  would have to be reimplemented on the app side.
- **[gap] No keyboard navigation between segments** (arrow keys), no per-segment
  tooltips API (you'd `segmentText(i)` and set them yourself), no icons-only
  vs text-only modes beyond what `addSegment(text, icon)` gives.
- **[divergence] Exclusive only** — no "all off" state (use a `ChipGroup` with
  `exclusive=False` for that).

Verdict: net-new; mostly fine. The "one logical control in many toolbars"
pattern (SEM/FOV) doesn't map to a single `SegmentedControl`.

---

## 4. `ChipGroup` (widgets/chip_group.py) — legacy: `QComboBox` / button rows

No legacy chip widget. Single-select chips overlap a `QComboBox` (the channel
picker `app._*_channel_cb`), multi-select chips overlap loose `QCheckBox` rows.

Gaps:
- **[gap] No dropdown / popup** — a `QComboBox` with 12+ channels is compact;
  a `ChipGroup` of 12 chips wraps/overflows. The mockup's channel chip is
  single-select with few options, so fine there; not a `QComboBox` replacement
  for long lists.
- **[gap] No model/`QAbstractItemModel` backing, no editable entry, no
  `currentIndexChanged(QString)` / `activated` distinction** — `ChipGroup` only
  has `currentChanged(int)` / `chipToggled(int, bool)`.
- **[gap] No "clear all" / "select all" affordance** for the multi-select mode.

Verdict: net-new; fine for the mockup's use; not a `QComboBox` swap-in.

---

## 5. `PillTabBar` (widgets/pill_tab_bar.py) — legacy: `QTabWidget` + `_GroupedTabBar(QTabBar)`

The legacy tab system is real `QTabWidget`s (the Review notebook + a nested
"Plotting" notebook) with a `_GroupedTabBar(QTabBar)` subclass (group separators
+ painted group labels), plus overflow-scroll-arrow handling and a keyboard
override in `views/centre_view.py`. `PillTabBar` is a flat row of toggle
buttons + a "+ Add" button — it's the mockup's *channel-tabs* widget, not a
`QTabWidget` replacement.

Gaps:
- **[blocker if used to replace `QTabWidget`] No page stacking.** `PillTabBar`
  is a tab *bar*, not a `QTabWidget` — there's no content area, no `addTab(widget,
  text)`, no `currentWidget()`. Replacing the Review/Plotting notebooks with it
  means building the page-switching yourself.
- **[gap] No group separators / group labels** (`_GroupedTabBar.set_group_starts`
  / `set_first_group_label`).
- **[gap] No overflow scrolling.** With more tabs than fit, `QTabBar` shows
  scroll arrows; `PillTabBar`'s `QHBoxLayout` just overflows / squashes.
- **[gap] No per-tab tooltips, no tab icons, no close buttons** (the `removeTab`
  API exists but there's no per-tab "×"), no drag-to-reorder. (Legacy
  `setMovable(False)`, so reorder isn't used.)
- **[gap] No keyboard tab navigation** (Ctrl+Tab etc.) — the legacy
  `centre_view` overrides arrow-key behaviour on the bar.

Verdict: a different widget for a different job (channel tabs). Not a drop-in for
the main notebooks.

---

## 6. `WellPlateSelector` (widgets/well_plate_selector.py) — legacy: `WellButton` grid + `build_plate_grid`

See `design/WELL_SELECTOR_GAP.md` (G1–G12) for the full audit and the §7/§8
migration plan + status. Summary of what the custom widget now covers vs. still
doesn't, for the **other six** plate-maps still on `WellButton` (Statistics /
Image Table / Segmentation / Sample Definitions / Bar Plots; the line rail is
already swapped):

- Covered: click-toggle, drag-to-select, per-well enabled/colour decoration,
  passive mode + activation signals, single-select mode, row/col header signals,
  drag source / drop sink, tooltips.
- **[blocker for the swap]** the app-side migration off `app._sidebar_btns` /
  `WellButton.set_state` / `_plate_apply_*` / the `_plate_drag_*` engine for
  those six maps (Steps 2–8) — none done yet. So those maps still use the legacy
  grid (now v2-*styled*, but still the legacy widget).
- **[gap]** `WellButton`'s `set_drop_handler` is per-button with an arbitrary
  callback; `WellPlateSelector` exposes one `wellDropped(id, token)` signal —
  fine for "return to palette" but not arbitrary per-well drop targets.

---

## 7. `Stepper` (widgets/stepper.py) — legacy: `QSpinBox` / `QDoubleSpinBox`

`Stepper` covers `value()` / `setValue()` / `valueChanged(float)` / `setRange` /
`setMinimum` / `setMaximum` / `setSingleStep` / `setDecimals` / `setPrefix` /
`setSuffix`, plus wheel + arrow-key stepping and an accent focus ring. `QSpinBox`
is used in `ExportStyleSidebar` (now via `_bind_getter_setter`, which only knows
`QSpinBox`/`QDoubleSpinBox` — *not* `Stepper`), `image_table_controller`
(`setSuffix(" in")`), `views/ratio_panel_view`, `views/heatmap_layout_sidebar_view`,
`tabs/{image_table,distribution}_tab_view`, `runtime_app`.

Gaps (vs `QSpinBox`/`QDoubleSpinBox`):
- **[blocker if swapped into `ExportStyleSidebar`]** `_bind_getter_setter`
  branches on `isinstance(QSpinBox)` / `isinstance(QDoubleSpinBox)` — a `Stepper`
  falls through to no binding. Swapping needs a `Stepper` branch added there
  (`.value()` / `.setValue()` / `.valueChanged`) — noted in `REWIRING.md`.
- **[gap] `valueChanged` carries a `float`**, always. `QSpinBox.valueChanged`
  carries an `int`; code connecting an int slot would still work (PySide coerces)
  but `_prefs[...]` would store `8.0` instead of `8` — could matter for code that
  does identity/`is` checks or JSON round-trips.
- **[gap] No `setSpecialValueText`** (e.g. "Auto" at minimum), no `setWrapping`,
  no `setStepType` (adaptive decimal steps), no `setGroupSeparatorShown`, no
  `setButtonSymbols(NoButtons/PlusMinus)`, no `setAccelerated`, no
  `setKeyboardTracking(False)`, no `valueFromText` / `textFromValue` overrides,
  no `lineEdit()` accessor, no `selectAll()`/`setReadOnly()`/`setAlignment()`,
  no `setCorrectionMode`. None of these are used by the codebase today (only
  `setSuffix` is), so currently moot — but `Stepper` is *not* a feature-complete
  `QSpinBox`.
- **[gap] Validator is `QDoubleValidator` even in `decimals=0` mode** (we round on
  commit) — typing intermediate non-integers is allowed and then snapped, vs
  `QSpinBox`'s stricter `QIntValidator`.

Verdict: covers the cases the codebase actually uses; not a full `QSpinBox`.
Real blocker is the `_bind_getter_setter` branch if it's ever swapped in.

---

## 8. `StyledSlider` (widgets/styled_slider.py) — legacy: `QSlider`

`StyledSlider` subclasses `QSlider`, paints groove/fill/handle itself
(horizontal), drives the value from the pointer x, and adds a focus halo. No
`QSlider` in the codebase uses tick marks or special features.

Gaps (vs `QSlider`):
- **[gap] Tick marks ignored.** `setTickPosition` / `setTickInterval` have no
  visual effect — the custom `paintEvent` doesn't draw ticks. (Not used today.)
- **[gap] `sliderMoved` / `sliderPressed` / `sliderReleased` may not fire** the
  way they do on a stock `QSlider` — the custom `mousePress`/`Move`/`Release`
  call `setSliderDown()` and `setValue()` (which emits `valueChanged`), but the
  fine-grained `sliderMoved`/`sliderPressed`/`sliderReleased` sequence isn't
  guaranteed. Code that relies on those (vs `valueChanged`) would break. (Not
  used today.)
- **[divergence] Vertical orientation falls back to the default Qt rendering** —
  a vertical `StyledSlider` won't look v2. (Not used today; all sliders are
  horizontal.)
- **[gap] Clicking the groove jumps the handle to the click point** (we compute
  value from x), which differs from `QStyle.SH_Slider_AbsoluteSetButtons` /
  page-step-on-trough behaviour some platforms default to. Arguably nicer; just
  different.

Verdict: fine for current usage; not tick-aware, not vertical-styled.

---

## 9. `IconButton` + `icons.py` (widgets/) — legacy: `_ThemedNavToolbar._icon` + `refresh_plot_toolbar_icons` + ad-hoc styled `QPushButton`s

Legacy icon handling: matplotlib's bundled toolbar PNGs recoloured by mask in
`ui_helpers._ThemedNavToolbar._icon`, re-applied on theme change via
`refresh_plot_toolbar_icons(widget)` → `toolbar.refresh_icons()`. Plus many
`QPushButton`s with inline `setStyleSheet(...)` for colour swatches / dots / pills
(those aren't really "icon buttons").

Gaps:
- **[gap] Small curated SVG set (~18 glyphs).** `icons.py` ships a fixed Lucide-ish
  set (chevrons, x, plus, search, sliders, home, arrows, move, zoom-in, save,
  download, more-horizontal, check, alert-triangle, info, image, grid). Anything
  else (e.g. the *actual* matplotlib toolbar icons, "configure subplots", a copy
  icon, an eye/eye-off, a lock) doesn't exist — you'd add a path string. The
  legacy `_ThemedNavToolbar` uses matplotlib's full icon set verbatim.
- **[gap] No theme-change re-render hook for embedded uses other than `showEvent`.**
  `IconButton.showEvent` re-renders at the current DPR, and the pixmap cache is
  keyed by `(name, hex, size, dpr)` — but if multi-theme returns, an `IconButton`
  already shown won't recolour on a live theme switch (it'd need an explicit
  `setIconName`/`_refresh_icon` call, the analogue of `refresh_plot_toolbar_icons`).
- **[gap] No QSS-stylable icon** (it's a baked `QPixmap` per state) — fine, but
  means colour comes only from the `make_icon` state args, not from a `:hover`
  QSS rule.
- **[n/a]** It's not trying to replace the colour-swatch / dot `QPushButton`s —
  those map to `ColorSwatchRow` / `StatusDot`.

Verdict: fine for v2 toolbars; not a drop-in for the matplotlib toolbar's icon
set, and no live-theme-switch recolour hook.

---

## 10. `StatusDot` (widgets/status_dot.py) — legacy: `QLabel("●")` + `setStyleSheet(f"color: {c}")`

Legacy: tiny `●` labels coloured via inline stylesheet — in `stats_controller.py`,
`views/bar_group_panel_view.py` (`dot.setStyleSheet(f"color: {'#666' if hidden else color}")`),
`batch_export/base_panel.py` (group/legend dots). No halo, no status semantics.

Gaps:
- **[gap] Different sizing model.** The legacy `●`-label's size is the glyph's
  font size; `StatusDot` computes diameter from `fontMetrics().height() * 0.45`
  (or an explicit `diameter`). Dropping `StatusDot` into a tight existing layout
  (e.g. a bar-group card row) may need size tuning.
- **[gap] No arbitrary text glyph** — the legacy uses a `QLabel` so you can put
  any character; `StatusDot` always paints a filled circle. (Fine for dots.)
- **[n/a]** It's strictly better for the "saved" indicator (halo + status names);
  the legacy never had that.

Verdict: net-new; only watch sizing when retrofitting it where `●`-labels are.

---

## 11. `BrandTile` (widgets/brand_tile.py) — legacy: `all_well._install_app_icon()` painter

Legacy: a `QPainter`-rendered 96-well-plate icon used as the *window* icon
(`setWindowIcon`), not shown in the UI. `BrandTile` is the mockup's in-titlebar
four-quadrant mark.

Gaps:
- **[n/a]** No legacy in-UI brand widget existed; nothing to lose.
- **[gap] Doesn't render the existing app icon.** `_install_app_icon` paints a
  detailed plate-with-lit-wells icon; `BrandTile` is a generic 4-dot tile. If
  the brand should *be* the plate icon, `BrandTile` doesn't do that (and the
  window icon painter still does its own thing — two separate marks now).

Verdict: net-new; only "gap" is that it's a different mark than the window icon.

---

## 12. `ColorSwatchRow` (widgets/color_swatch_row.py) — legacy: `QColorDialog` + LUT `QComboBox` + colour `QPushButton`s

Legacy free-form colour picking: `QColorDialog.getColor(...)` in
`runtime_app.py:4316-4319` for review-image channel colours; a `QComboBox` of
named LUT colours in `image_table_controller`; `QPushButton`s with
`setStyleSheet("background-color: rgb(...)")` as colour swatches.

Gaps:
- **[blocker if it replaces `QColorDialog`] No free-form colour selection.**
  `ColorSwatchRow` is a *curated* set — it can't replace the review-image
  `QColorDialog` unless that feature is willing to drop arbitrary-colour choice
  (the mockup's curated-swatch pattern implies it is, but that's a product
  decision, not a widget fact).
- **[gap] No "more…" escape hatch** to open a full picker for a colour not in the
  curated set, and no alpha channel.
- **[gap] Not a `QComboBox`** — for the long LUT-name list, `ColorSwatchRow`'s
  inline row would overflow; the `QComboBox` should stay there.
- **[gap] No labels on swatches** — the LUT combo shows names ("Viridis",
  "Gray"); `ColorSwatchRow` shows only colour squares.

Verdict: net-new curated picker; explicitly *not* a `QColorDialog`/`QComboBox`
replacement for free-form or long-list cases.

---

## 13. `SearchInput` (widgets/search_input.py) — legacy: none

No search field exists in the app today.

Gaps:
- **[n/a]** Nothing to lose.
- **[gap vs the mockup] The `⌘K` hint is decorative** — `SearchInput` doesn't
  register a global `⌘K` shortcut; the host must do that. And it doesn't
  implement any actual filtering — it's just `QLineEdit` + icon + hint chip.

Verdict: net-new; just a styled input. Wiring the shortcut + the search logic is
on the host.

---

## 14. `EmptyState` (widgets/empty_state.py) — legacy: a centered `QLabel` (e.g. `NO_SELECTION_MSG`)

Legacy: `runtime_app.NO_SELECTION_MSG` (a two-line string) shown as a plain
centered `QLabel` in the plot area (and similar "nothing selected" labels in the
line/bar tab builders), plus matplotlib axes showing nothing.

Gaps:
- **[gap] It's a `QWidget`, not text on the canvas.** The legacy "no wells
  selected" message is often drawn *on the matplotlib axes* (so it sits inside
  the figure and exports with it, or is just `ax.text(...)`); `EmptyState` is a
  separate Qt widget that would have to be shown/hidden over or instead of the
  canvas. Swapping it in means managing that visibility toggle.
- **[gap] No retry/action button slot** (the mockup's empty states are static;
  fine).

Verdict: net-new presentation; the integration cost is the canvas-vs-widget
toggle.

---

## 15. `SavedSelectionsList` (widgets/saved_selections_list.py) — legacy: replicate-set / bar-group list cards + `_LayoutTable(QTableWidget)`

Legacy "list of named things with a colour dot": the replicate-set list in
`views/replicate_panel_view.py` + `sample_definitions.py`, the bar-group cards in
`views/bar_group_panel_view.py` (`_build_group_card` — a `QFrame` per group with
a dot, name, chips, hidden-toggle), and `_LayoutTable(QTableWidget)` in
`views/heatmap_layout_sidebar_view.py`. These support **rename, delete, reorder,
show/hide toggle, "solo wells" chips, double-click-to-edit, context menus**, etc.

Gaps:
- **[blocker if it replaces those panels] No per-row actions.** `SavedSelectionsList`
  is read-mostly: `addEntry` / `setEntries` / `clear` / `currentName` /
  `entryActivated(name)`. It has **no** rename, delete, reorder (drag or ▲/▼),
  show/hide toggle, sub-item chips, context menu, double-click-to-edit — all of
  which the legacy replicate-set / bar-group panels have and the app relies on.
- **[gap] No editable model** — it's a `QStandardItemModel` populated by the
  widget; the legacy panels are backed by the real `sample_definitions` /
  `bar_groups` state and write back to it.
- **[gap] No multi-select** (`SingleSelection` only); no checkboxes per row.
- **[n/a]** For the *new* "saved well selections" list in the mockup (which is
  read + click-to-apply), it's adequate; for the existing replicate/bar-group
  panels it is not a replacement.

Verdict: covers the mockup's read-only "saved selections" list; **does not** cover
the legacy replicate-set / bar-group editing panels.

---

## 16. `Drawer` (widgets/drawer.py) — legacy: the Analyze *tab* (`analyze_tab.py`)

Legacy: Analyze is a full top-level `QTabWidget` tab hosting `AnalyzeTab(QWidget)`
— always present, switched to like any tab. The mockup demotes it to a slide-in
drawer.

Gaps:
- **[gap] No persistence of state across open/close beyond the content widget**
  — fine, since the content widget is kept; but the drawer doesn't remember its
  width if the user resized it (no resize grip — it's a fixed fraction/width).
- **[gap] No resize handle.** `QDockWidget` (another candidate) lets the user
  drag the splitter; `Drawer` is a fixed width.
- **[gap] OpenGL z-order caveat (from `PYQT6_NOTES.md` §21)** — if the canvas
  behind it uses an OpenGL surface, the drawer (a child widget) may not paint
  above it; would need a top-level `Qt.Popup`. Not handled.
- **[gap] No "push content aside" mode** — it always overlays (with a dim
  backdrop); some drawers slide the main content over instead. (Overlay matches
  the mockup.)
- **[n/a]** Replacing the Analyze *tab* with the drawer is a structural change;
  the drawer widget itself is fine, but the host has to host `AnalyzeTab`'s
  contents inside it and remove the tab.

Verdict: net-new; the only real "missing" things are a resize grip and the
OpenGL-overlay edge case.

---

## 17. `Toast` (widgets/toast.py) — legacy: `QMessageBox` + `app._set_status` / status label

Legacy transient/notification messaging: `QMessageBox.information/warning/critical/
question` (modal, blocking, with buttons; ~18 uses in `runtime_app` alone, plus
`load_controller`, `export_service`, `batch_export`, `figure_export_editor`,
`grouping_controller`, `persistence/sample_definitions`, …) and `app._set_status(msg)`
(persistent status-bar text).

Gaps:
- **[blocker — it's not a `QMessageBox` replacement] No buttons, no return
  value, not modal.** `Toast` is fire-and-forget. It cannot replace any
  `QMessageBox.question` (needs a yes/no answer), `QMessageBox.critical` that
  must be acknowledged before continuing, or anything where the code waits for
  the user. It's only a replacement for "fire-and-forget success/info" — which
  in the legacy is `_set_status`, not `QMessageBox`.
- **[gap] No queue / stacking** — two `Toast.show_message` calls in quick
  succession overlap at the same position; there's no toast stack manager.
- **[gap] No "undo" action slot** (some toasts have an inline action).
- **[gap] Doesn't replace `_set_status`** either — `_set_status` text is
  *persistent* (stays in the status bar); `Toast` auto-dismisses. They're
  complementary.

Verdict: net-new for fire-and-forget notices; **not** a `QMessageBox` (or
`_set_status`) replacement.

---

## 18. `HoverToolbarOverlay` (widgets/hover_toolbar_overlay.py) — legacy: `ui_helpers.attach_plot_toolbar` (always-on)

Legacy: plot toolbars are *always visible* (`attach_plot_toolbar` adds a
`NavigationToolbar2QT` at the bottom of each tab). The mockup hides them until
hover. `HoverToolbarOverlay` is a behaviour wrapper (fades a `QGraphicsOpacityEffect`
on Enter/Leave).

Gaps:
- **[gap] Keeps layout space but is invisible** — which means the area below the
  plot is "dead" when not hovered. The mockup's hover toolbar overlays the
  bottom of the figure rather than reserving space; `HoverToolbarOverlay` (per
  `PYQT6_NOTES.md`'s own recommendation) keeps the space to avoid layout jump.
  Acceptable, but it's a layout-vs-overlay tradeoff, not a true "appears on top".
- **[gap] Touch / no-mouse devices** — a hover-only control is unreachable
  without a pointer; no keyboard or focus fallback.
- **[gap] Pointer-tracking is approximate** — `_pointer_inside` uses `QCursor.pos()`
  geometry checks; rapid host↔toolbar moves could flicker (mitigated, not
  eliminated).
- **[n/a]** The legacy always-on toolbar loses nothing functionally — this just
  hides it. If the single-shared-canvas model wins (per `DESIGN_NOTES.md` §2.8),
  this widget isn't used at all.

Verdict: behaviour wrapper, not a widget swap; the main caveat is the dead-space
tradeoff and no non-pointer fallback.

---

## 19. `PlotCard` (widgets/plot_card.py) — legacy: `FigureCanvasQTAgg` + `ui_helpers.attach_plot_toolbar` (`_ThemedNavToolbar`) + `plot_style.apply_ax_style`

Legacy: every plot tab builds `Figure()` + `FigureCanvasQTAgg` directly, then
`attach_plot_toolbar(layout, canvas, parent, app, with_sem=…, with_fov=…)` adds
a themed `NavigationToolbar2QT` (full mpl toolbar) **plus** the SEM/SD toggle
**plus** optionally the FOV/Spread toggle, registered in `app._sem_btns` /
`app._fov_btns`. Axes are styled per-redraw by `plot_style.apply_ax_style(ax,
title, ylabel)`.

Gaps:
- **[divergence — significant] White vs dark plot background.** `plot_style.apply_ax_style`
  sets `ax.set_facecolor(PLOT_BG)` where `PLOT_BG = "#FFFFFF"` in *every* legacy
  theme (white plots, for publication export). `PlotCard.apply_axes_style` sets
  `ax.set_facecolor(theme.Colors.plot_bg)` = `#131A24` (dark). This is the
  open design question from `DESIGN_NOTES.md` / `PORT_PLAN.md` — `PlotCard`
  picked "dark", the codebase is "white". Swapping `PlotCard` in flips every
  plot to a dark background and changes export semantics.
- **[blocker] No SEM/SD toggle, no FOV/Spread toggle, no `_sem_btns`/`_fov_btns`
  registry.** Those live in the legacy toolbar; `PlotCard`'s toolbar has only
  home/back/forward/pan/zoom/save. Swapping `PlotCard` in means re-adding those
  controls (and their cross-toolbar sync) elsewhere.
- **[gap] No "configure subplots" tool** (`NavigationToolbar2QT` has it;
  `PlotCard` omits it).
- **[gap] No matplotlib message area** — `NavigationToolbar2QT` shows transient
  text ("Pan mode", "Zoom rect"); `PlotCard` shows only the `x=… y=…` coords.
- **[gap] No theme-change icon refresh hook** — `refresh_plot_toolbar_icons`
  re-tints the legacy toolbar's mpl icons on theme switch; `PlotCard`'s
  `IconButton`s only re-render on `showEvent` (and the pixmap cache is hex-keyed).
- **[gap] No integration with the export pipeline** — `figure_export_editor` /
  `ExportStyleSidebar` operate on the figures the controllers create directly;
  `PlotCard` owns its own `Figure`, so wiring the per-figure export dock to a
  `PlotCard` would need plumbing.
- **[gap] `apply_axes_style` signature differs** — legacy `apply_ax_style(ax,
  title, ylabel)` sets the title/ylabel for you; `PlotCard.style_axes(ax)`
  styles only what's there, so callers must set title/ylabel themselves.
- **[gap] Constructed-vs-attached.** Legacy `attach_plot_toolbar` slots into an
  existing layout next to a caller-owned canvas; `PlotCard` is a self-contained
  `QFrame` that owns the `Figure` + canvas + toolbar — swapping it in restructures
  the tab layout.
- **[gap] Degrades to `PlotCard = None` if matplotlib is missing** — callers
  must handle `None` (the legacy code would `ImportError` loudly instead).

Verdict: the dark-vs-white background is a real divergence to resolve before
this replaces the legacy plot setup; and the SEM/FOV toggles + export-pipeline
hooks are missing.

---

## 20. `TitleBar` (widgets/title_bar.py) — legacy: the top bar in `runtime_app._build_ui` + the `all_well` header

Legacy: `runtime_app._build_ui` has a top bar with `_dir_label` ("No data loaded"
→ the dataset path) + an "Open…" `QPushButton(variant="primary")` that calls
`_browse`; `all_well.py` has a header (`QWidget#Sidebar` with a `Title` label +
a Theme `QComboBox` + `_install_app_icon` for the window icon). The window is
**native-framed**. The mockup wants a frameless window with a custom titlebar.

Gaps:
- **[blocker] Frameless = you lose the native title bar's everything.** `TitleBar`
  paints a drag strip and supports `startSystemMove` + double-click-maximize, but
  going frameless means re-implementing: edge/corner resize grips (the mockup
  notes a 6px transparent border — `TitleBar` doesn't add those), window snapping
  (Win/macOS), the native traffic-lights / min-max-close (TitleBar has optional
  painted ones, off by default), restore-from-maximized geometry, multi-monitor
  edge cases, and the OS "shake to minimize others" / Aero-snap behaviours.
  This is the big one — `TitleBar` is a strip, not a window manager.
- **[gap] No "Open dataset" affordance built in** — the legacy `_dir_label` +
  "Open…" button live in the top bar; `TitleBar` has `setBreadcrumb(...)` (a
  display-only file chip) and `addAction(icon, tooltip)` for right-side buttons,
  but the host has to add the "Open…" action and wire it.
- **[gap] No theme switcher** — the legacy `all_well` header has a Theme
  `QComboBox`; `TitleBar` has no slot for it (would be an `addAction` or a custom
  child). (Moot if multi-theme is dropped.)
- **[gap] `setSaved(bool)` only flips success/warn** — no "saving…" intermediate
  state, no dirty-since-last-save tracking (the host must drive it).
- **[gap] Window-control fallbacks are best-effort** — `_do_minimize` /
  `_do_toggle_max` / `_do_close` call `self.window()` methods; if `TitleBar` is
  used inside something that isn't the top-level window, those are no-ops.
- **[gap] Doesn't render the existing app icon** — see `BrandTile` §11.

Verdict: the strip is fine; the **frameless-window** decision it implies is a
large surface area (resize, snap, native controls) that `TitleBar` does not
cover. Worth deciding whether to stay native-framed and just restyle the in-window
header instead.

---

## Cross-cutting notes

- **Binding-layer awareness.** `ExportStyleSidebar._bind_getter_setter` only
  knows `QSpinBox` / `QDoubleSpinBox` / `QComboBox` / `QCheckBox` / `QLineEdit`.
  `ToggleSwitch` works (it *is* a `QCheckBox`); `Stepper`, `SegmentedControl`,
  `ChipGroup`, `StyledSlider` do **not** — swapping any of those into a
  binding-driven panel needs that registry extended (per `REWIRING.md`).
- **Theme-switch redraw.** Several custom widgets build a per-widget stylesheet
  from `theme.Colors` *once* in `__init__` (`CollapsibleSection`,
  `SegmentedControl`, `ChipGroup`, `Stepper`, `StyledSlider`, `SearchInput`,
  `WellPlateSelector`, `IconButton` icons). If multi-theme returns and a live
  theme switch happens, those won't restyle themselves — they'd each need a
  `re-apply` hook (analogous to `refresh_plot_toolbar_icons`). Currently moot
  (one theme).
- **macOS / native-style sub-control fallthrough.** `Stepper` and the
  `WellPlateSelector` action buttons rely on QSS for stock sub-widgets; per
  `PYQT6_NOTES.md` §21 these can fall through to native rendering on macOS if
  under-specified. (`StyledSlider` already side-steps this by painting itself.)
- **`QGraphicsEffect` interactions.** `Drawer` / `Toast` use
  `QGraphicsDropShadowEffect` / `QGraphicsOpacityEffect`; stacking these with a
  matplotlib canvas (raster) is fine, but with an OpenGL canvas (Agg is fine,
  Cairo/GL is not) z-order/compositing can misbehave (`PYQT6_NOTES.md` §21).
