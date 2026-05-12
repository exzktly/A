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
