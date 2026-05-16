# Rewiring log — Property panel port (reference area)

What was reconnected when porting the right-side **Properties** panel
(`well_viewer/views/export_style_sidebar_view.py`, class `ExportStyleSidebar`) to
the v2 chrome, and what — if anything — could not be carried over.

## Summary

**Nothing was dropped.** All 30 figure-style properties keep their original
state plumbing. The port re-skinned the *layout* only: the single `QGridLayout`
was replaced by a scrollable stack of `widgets.collapsible_section.CollapsibleSection`s,
and every `QCheckBox` became a `widgets.toggle_switch.ToggleSwitch`
(`ToggleSwitch` subclasses `QCheckBox`, so it is type-compatible with the
existing binding code). The binding layer
(`_bind_getter_setter` / `_getters` / `_setters` / `_persist` /
`_on_fields_changed` → `apply_export_style_to_current`) and every handler method
(`_on_profile_selected`, `_on_axis_target_changed`, `_reset_defaults`,
`_save_preset`, `_export`, `_copy_png`, `_copy_svg`, `_move_list_item`,
`_apply_line_order`, `_refresh_line_order_lists`, `_redraw_bound_figure`,
`_close_dock`) were left byte-for-byte unchanged.

## Property → state mapping (verified against the pre-port code)

Every row below is created in `_build_ui` and registered via
`_bind_getter_setter(key, widget)` (or, for `axis_target`, a hand-written
getter/setter pair), exactly as before. On any change, `_on_fields_changed`
→ `_persist()` writes the value into `app._export_style_prefs[...]` and calls
`apply_export_style_to_current(app, fig, canvas)`.

| Section (v2) | Property key(s) | Widget type | Change signal | Notes |
|---|---|---|---|---|
| Profile & Format | `export_profile` | `QComboBox` | `currentTextChanged` → `_on_profile_selected` (then `_on_fields_changed`) | profile presets unchanged |
| Profile & Format | `format` | `QComboBox` | `currentTextChanged` | png/svg/pdf/eps |
| Axes | `axis_target` | `QComboBox` | `currentTextChanged` → `_on_axis_target_changed` | **not** auto-applied — switching target swaps the per-axis bucket; identical to legacy behaviour |
| Axes | `axis_label_size`, `tick_label_size`, `title_size`, `x_tick_angle` | `QSpinBox` | `valueChanged` | |
| Axes | `tick_major`, `tick_minor` | `ToggleSwitch` (was `QCheckBox`) | `toggled` | wrapped in an `hrow(...)` for layout |
| Axes | `tick_length` | `QDoubleSpinBox` | `valueChanged` | |
| Axes | `tick_direction` | `QComboBox` | `currentTextChanged` | out/in/inout |
| Legend | `legend_show` | `ToggleSwitch` (was `QCheckBox`) | `toggled` | now carries its own "Show legend" label |
| Legend | `legend_font_size` | `QSpinBox` | `valueChanged` | |
| Legend | `legend_loc` | `QComboBox` | `currentTextChanged` | |
| Lines & Markers | `line_width`, `marker_size`, `marker_edge_width` | `QDoubleSpinBox` | `valueChanged` | |
| Grid | `grid_show` | `ToggleSwitch` (was `QCheckBox`) | `toggled` | |
| Grid | `grid_alpha` | `QDoubleSpinBox` | `valueChanged` | |
| Grid | `grid_style` | `QComboBox` | `currentTextChanged` | -, --, :, -. |
| Limits & Scale | `x_lim_min`, `x_lim_max`, `y_lim_min`, `y_lim_max` | `QLineEdit` | `textChanged` | per-axis bucketed via `_axis_keys` / `_axis_buckets` (unchanged) |
| Limits & Scale | `x_log`, `y_log` | `ToggleSwitch` (was `QCheckBox`) | `toggled` | also per-axis bucketed |
| Layout | `layout_tight`, `layout_constrained` | `ToggleSwitch` (was `QCheckBox`) | `toggled` | |
| Layout | (draw order) `app._line_order_rsets`, `app._line_order_wells` | `QListWidget` + ▲/▼/Apply `QPushButton`s | `clicked` → `_move_list_item` / `_apply_line_order` | only shown for line/bar/scatter figs (`_supports_well_order()`); `_refresh_line_order_lists()` still called once after building |
| (footer) | n/a — actions | `QPushButton` | `clicked` → `_copy_png` / `_copy_svg` / `_reset_defaults` / `_save_preset` / `_export` | unchanged |

## Things deliberately *not* changed (and why)

- **The panel is still a per-figure dock, not a single persistent main-window
  rail.** The v2 mockup shows one global right-side Properties rail. The current
  app has no such thing — each plot tab gets its own export-style dock created
  lazily by `figure_export_editor` and keyed in `app._export_style_sidebars`.
  Restructuring to one shared rail is an architectural change tracked in
  `design/PORT_PLAN.md` (Table 1, "Properties panel" row); it was out of scope
  for re-skinning the reference area. Consequently the `ExportStyleSidebar`
  constructor signature is unchanged and `figure_export_editor.py` needed no
  edits — the panel is already "wired in" where it lives.
- **Numeric fields stayed `QSpinBox` / `QDoubleSpinBox`** instead of
  `widgets.stepper.Stepper`, and enum fields stayed `QComboBox` instead of
  `widgets.segmented_control.SegmentedControl`. `_bind_getter_setter` only knows
  `QSpinBox` / `QDoubleSpinBox` / `QComboBox` / `QCheckBox` / `QLineEdit`;
  swapping in `Stepper` would mean teaching the binding layer a new widget type,
  which would change the property plumbing. Kept as-is to honour "every property
  must still update the same underlying state". Both are styled by `theme.qss()`
  already. (Swapping them in later is a small, separate follow-up: add a
  `Stepper` branch to `_bind_getter_setter` and use `.value()` / `.setValue()` /
  `.valueChanged`.)
- **The header label changed** from "Export Style" to "Properties" and the close
  glyph from `◂` to `‹`; the close button still calls `_close_dock()`.
- **Section headers' "value preview" slot** (`CollapsibleSection.setValueWidget`)
  is not yet populated. Pure addition; can be filled in later (e.g. show the
  selected profile on the collapsed "Profile & Format" header).

## Verification status

⚠️ Not runtime-verified — this environment has no PySide6, so the port was
checked with `python -m py_compile` only. Before relying on it, open a plot tab,
toggle the right-side dock, and confirm: (1) every section expands/collapses,
(2) changing any field re-renders the figure (i.e. `apply_export_style_to_current`
fires), (3) Reset / Save Preset / Export / Copy PNG / Copy SVG still work,
(4) for line/bar/scatter figs the draw-order lists populate and Apply re-draws.

---

# Well plate selector area (left rail) — plate swap DEFERRED

Target: replace the 8×12 `WellButton` grid in the left rail with
`widgets.WellPlateSelector`, wiring its signals to the existing handlers.

## What was done

The rail **chrome** was moved onto the v2 theme (`well_viewer/views/sidebar_view.py`):

- "All" / "None" action buttons: dropped the dead legacy
  `setProperty("variant", "primary-dark")` (that selector no longer exists in
  `theme.qss()`); "All" now uses the default themed `QPushButton`, "None" uses
  `objectName("Danger")`, both get a pointing-hand cursor. They still call the
  unchanged handlers `app._select_all` / `app._select_none`
  (→ `selection_controller.select_all` / `select_none`).
- "N wells selected" status label: `objectName("Muted")` → `objectName("Caption")`
  so `theme.qss()`'s `QLabel#Caption` (muted, caption-size, medium) styles it.
  Its text is still produced unchanged by `WellViewerApp._refresh_sidebar_map`
  (`self._sel_count_lbl.setText(…)`).

## Why the plate-grid swap was NOT done

`widgets.WellPlateSelector` (as it exists today) models a flat set of selected
wells: click-to-toggle, row/col-header toggle, `selectedWells` property,
`selectionChanged(list)`, and All/Invert/Clear buttons — well IDs are
`"A01".."H12"`. The legacy `WellButton` grid that the rail uses
(`well_viewer/views/well_button.py` + `build_plate_grid`, wired in
`sidebar_view.build_sidebar`) carries a lot more, and the following could **not**
be straightforwardly reconnected — so per `design/PATTERNS.md` §4 they are
recorded here instead of being silently lost:

1. **Drag-to-select.** Press-and-drag across wells to add/remove a whole run in
   one gesture. Implemented by `_make_btn_handlers` overriding every WellButton's
   `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent` → `app._sb_press` /
   `_sb_drag` / `_sb_release` → `selection_controller.sb_press` / `sb_drag` /
   `sb_release` → `plate_drag_press` / `plate_drag_apply` / `plate_drag_release`
   driving the `app._sb_ds` state machine (`{"adding", "visited", "rep_toggled"}`).
   `WellPlateSelector` only does single-click toggles; it has no drag mode and no
   per-well child widgets to attach event overrides to.
2. **Replicate-set visual mode.** When `app._rep_sets` is active, the plate shows
   *replicate-set membership* and per-set hidden state (`btn.set_state("active"|
   "rep_hidden")`), and clicks toggle a set's visibility (`app._rep_hidden`)
   rather than individual wells. `WellPlateSelector` has no notion of rep-sets —
   only a flat selected-well set.
3. **Heat-map drag source.** On the Heat Map tab each well button becomes a
   `QDrag` source via `btn.set_drag_mime(...)` / `btn._drag_mime`, so wells can be
   dragged onto a heatmap layout. `WellPlateSelector` paints the grid itself —
   there are no per-well widgets to act as drag sources.
4. **`app._sidebar_btns: {token: WellButton}` + the `set_state` per-button API.**
   Consumed by `WellViewerApp._refresh_sidebar_map` / `_refresh_sidebar_map_now`
   (iterates the dict, calls `btn.set_state(...)` to repaint each well per
   selection / rep-colour / rep-hidden), `selection_controller.plate_drag_apply`,
   the heat-map controller, and the tab-change reset paths. `WellPlateSelector`
   exposes neither a per-well widget map nor a `set_state` hook.
5. **`app._select_row(row)` / `app._select_col(col)` rep-set branching.** The
   legacy header letters/numbers (built into `build_plate_grid` via `on_row_click`
   / `on_col_click`) call these, which — when rep-sets are active — toggle
   rep-set visibility, not wells. `WellPlateSelector` emits no row/col-header
   *signals*; its header clicks toggle its own internal selection set and emit
   `selectionChanged`, so the rep-set-aware variant would be bypassed.
6. **Per-tab selection gating.** `_row_col_select_disabled(app)` suppresses
   row/col clicks on the smFISH tab, and `on_plate_sel_change` forces single-well
   selection there. With `WellPlateSelector` these gates aren't enforced at the
   widget level (could only be re-applied after the fact by mutating its
   selection).
7. **Well-token format.** `app._well_paths` keys are extracted well tokens
   (`app._extract_well_token`), not guaranteed to be zero-padded `"A01"`.
   `WellPlateSelector` emits/accepts only `"A01".."H12"`, so a token↔ID
   translation layer would be needed at the boundary.

`selectionChanged(list)` → set `app._selected_wells` + call `app._on_plate_sel_change()`,
and `selectAll()` / `clearSelection()` → `app._select_all()` / `app._select_none()`
*would* reconnect cleanly — but only at the cost of regressions 1–6 above and the
~10 `_sidebar_btns` consumers in (4).

## Recommended next step (pick one)

- **Grow `widgets.WellPlateSelector`** to cover what's needed: an optional
  drag-select mode, an external "decoration" API (per-well state colours / a
  `set_well_state(id, state)` hook) so the app can drive rep-set rendering, a
  `tokenMap` so it speaks the app's well tokens, `rowHeaderClicked(str)` /
  `columnHeaderClicked(str)` *signals*, and an optional single-select mode — then
  do the swap and retire `_sidebar_btns` / `WellButton`. (Largest, but the only
  path that fully realises the v2 plate.)
- **Restyle the legacy `WellButton` grid in place** (token colours in
  `well_button.py` / `plate_layout.py`) and keep all the wiring. Lower risk, no
  feature loss, but doesn't use `widgets.WellPlateSelector`.

## Verification status

⚠️ Not runtime-verified (no PySide6 in this environment) — the chrome change was
checked with `python -m py_compile` only. Confirm the "All" / "None" buttons and
the count label still look/behave right; the plate grid itself is untouched.
