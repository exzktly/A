# Decisions needed

Distilled from `design/WIDGET_GAPS.md` — only the **[blocker]** and
**[divergence]** items, i.e. the things that need an actual call from you before
the corresponding port work can proceed (or before it ships compromised).
`[gap]` items for unexercised legacy behaviour and `[n/a]` items are omitted.

> **Status:** all of #1–#11 are now **resolved** (rows kept for the record, with
> the chosen option + rationale). #1 (per-plot cards), #2 (white-screen + dark
> "presentation" toggle), #3 (extend `PlotCard` first), #4 (keep native frame,
> restyle the header) were decided 2026-05; #5/#6/#7 were resolved & done earlier
> (WellSelector migration / `bindingAdapter` protocol / `PillTabBar`=channel-tabs);
> #8–#11 were the low-stakes "use the new widget here?" calls. **Next:** the
> per-area v2 ports proper — the plot/figure area (now unblocked: per-card `PlotCard`
> + `MplToolbar` + `PillTabBar` channel strip + the `PlotCard` SEM/FOV extension +
> the `plot_style`/export-pipeline rework), the app-shell header restyle, then the
> per-tab property panels. See `PORT_PLAN.md` Table 2 + `all-well-porting-plan.md`.

Sorted by blast radius: rows that block/compromise multiple downstream port
prompts come first. "Phase 8 prompts" below = the per-area port prompts (plot
area, centre/tabs, main-window/titlebar, the per-tab sidebar swaps), plus the
`simplify`/regression passes that follow them.

| # | Widget(s) | The gap (one sentence) | Decision required (pick one) | Downstream impact if deferred |
|---|---|---|---|---|
| 1 | `PlotCard`, `HoverToolbarOverlay`, per-card `SegmentedControl`/`ChipGroup` | ✅ **RESOLVED — went with (a): per-plot cards** (user, 2026-05). Each subplot becomes a `widgets.PlotCard` with a hover-revealed toolbar (`HoverToolbarOverlay`) and per-card view-switcher (`SegmentedControl`) + channel chip (`ChipGroup`). Diverges from "one PNG == one figure" — export becomes per-card (each card exports its own figure). Gates #2/#3 (now also resolved). | ~~**(a)** per-plot cards; **(b)** single shared canvas + 1 toolbar; **(c)** hybrid.~~ Chose (a). | — (resolved) |
| 2 | `PlotCard` (+ `well_viewer/plot_style.py`) | ✅ **RESOLVED — went with (c): white on screen, dark "presentation" toggle** (user, 2026-05). Default plot theme stays `"publication"` (white bg, `theme.CPub`/`TRACE_PUB`) so the rendered figure == the exported figure; each `PlotCard` gets a per-card `setPlotTheme("screen"|"publication")` toggle in its header (`PlotCard` already has this) — `"screen"` = the dark token set, for on-screen / presentation use, not exported by default. `plot_style.apply_ax_style` is reworked to read the active theme. | ~~**(a)** dark everywhere; **(b)** keep white only; **(c)** white + dark "presentation" toggle.~~ Chose (c). | — (resolved) |
| 3 | `PlotCard` (vs `ui_helpers.attach_plot_toolbar` / `_ThemedNavToolbar`) | ✅ **RESOLVED — went with (a)** (implied by #1: we're adopting `PlotCard` for *all* plot tabs, so it must host what Line/Bar need). Extend `PlotCard`'s toolbar/header to carry the SEM/SD + FOV/Spread toggles (a `SegmentedControl` bound to `app._use_sem` / the FOV state — replacing `app._sem_btns`/`_fov_btns`), keep a "configure subplots" affordance, and hook the per-figure export dock (now per-card). Build the extension *before* swapping the Line/Bar/Scatter tabs onto it. | ~~**(a)** extend `PlotCard` first; **(b)** adopt only for simple tabs; **(c)** no `PlotCard`, restyle only.~~ Chose (a). | — (resolved) |
| 4 | `TitleBar` (+ `widgets.brand_tile.BrandTile`) | ✅ **RESOLVED — went with (b): keep the native window frame, restyle the in-window header** (user, 2026-05). No frameless mode in v1 — `runtime_app`'s top bar + `all_well`'s header get the v2 colours/layout; the `TitleBar` widget's frameless features (resize grips, window-control buttons, brand dropdown, theme switcher) are *available* but unused for now (a frameless mode can be revisited later). | ~~**(a)** go frameless; **(b)** keep native frame + restyle header; **(c)** frameless on one platform.~~ Chose (b). | — (resolved) |
| 5 | `WellPlateSelector` (vs `WellButton` / `build_plate_grid`) | ✅ **RESOLVED — went with (a); done** (`WELL_SELECTOR_GAP.md`): the left rail, the GROUPS-panel rep-map, the Statistics plate, the image-table picker and the preview picker are all `widgets.WellPlateSelector` now; `WellButton` / `build_plate_grid` / `runtime_app._style_plate_button` / `_plate_apply_*` / `_plate_theme_colors` / `grouping_controller.rep_map_*` are deleted. (The Bar-Plots sidebar panel is itself gone, deleted in Phase 8.0. The batch-export panels keep their own `_WellGridButton` grid — separate widget, still out of scope.) Code-complete + runtime-QA'd by the user. | ~~**(a)** do Steps 2–8 — migrate all maps to `WellPlateSelector` and delete `WellButton`/`build_plate_grid`; **(b)** permanent fork; **(c)** migrate only the simple ones.~~ Chose (a). | — (resolved) |
| 6 | `Stepper`, `SegmentedControl`, `ChipGroup`, `StyledSlider` | ✅ **RESOLVED — went with (a); done** (= `OPEN_DECISIONS.md` #2, implemented in Phase 6.5.1): the custom widgets expose `bindingAdapter() -> (getter, setter, change_signal)` and `ExportStyleSidebar._bind_getter_setter` gained an `if hasattr(w, "bindingAdapter")` branch; `SegmentedControl`/`ChipGroup` also grew `setCurrentByData`. (`widgets/binding_check.py` harness — user-confirmed green.) | ~~**(a)** extend `_bind_getter_setter` with branches; **(b)** keep stock inputs in binding-driven panels.~~ Chose (a) (via the `bindingAdapter` protocol). | — (resolved) |
| 7 | `PillTabBar` (vs `QTabWidget` + `_GroupedTabBar`) | ✅ **RESOLVED — went with (a)** (= `OPEN_DECISIONS.md` #3): `QTabWidget` (+ `_GroupedTabBar`) stays for the Review notebook / the Plotting sub-notebook / the secondary tab strip, restyled via `theme.qss()` (already done); `PillTabBar` is reserved for the figure/plot-area channel-tabs strip only (built in the plot-area port). No notebook rebuild. | ~~**(a)** keep `QTabWidget`, restyle, `PillTabBar` for channel tabs only; **(b)** rebuild the notebooks on `PillTabBar` + `QStackedWidget`.~~ Chose (a). | — (resolved) |
| 8 | `SavedSelectionsList` (vs the replicate-set / bar-group panels) | `SavedSelectionsList` is read-mostly (`addEntry` / `entryActivated`) — it has no rename / delete / reorder / show-hide toggle / sub-item chips / context menu / double-click-edit, all of which the legacy `replicate_panel_view` / `bar_group_panel_view` panels have and the app depends on. | **(a)** use `SavedSelectionsList` only for the mockup's *new* read-only "saved well selections" list and leave the replicate-set / bar-group editing panels as they are (just restyle them); **(b)** extend `SavedSelectionsList` into an editable list-with-row-actions and migrate those panels onto it; **(c)** don't add the "saved selections" feature at all for now. | If deferred: the **Sample Definitions sidebar port** and the **Bar Plots sidebar port** can't "use `SavedSelectionsList`" for those panels; and the mockup's saved-selections list either ships read-only (a) or not at all (c). |
| 9 | `WellPlateSelector` | Selected wells on the left rail render in the **accent colour** (driven by `_refresh_sidebar_map_now` overriding with `theme.Colors.accent`) rather than each well in its **trace colour** — the mockup's "plate is the legend" idea (`DESIGN_NOTES.md` §2.1). | **(a)** keep accent-for-selected (matches the legacy look, one colour, simplest, no colour-blind concern on the plate); **(b)** switch to per-trace colours so the plate doubles as the legend (the v2 intent — drop the accent override and let the widget's trace-gradient show, keep the well-ID labels as the non-colour fallback). | Low / reversible — affects the **left rail's appearance** (already shipped) and whether the mockup's "plate = legend" claim holds. One-line change either direction; no downstream prompt is *blocked*, but the standalone legend-row removal (also part of §2.1) is moot without (b). |
| 10 | `ColorSwatchRow` | It's a *curated* swatch picker — it can't replace the free-form `QColorDialog` used for review-image channel colours, nor the long-list LUT-name `QComboBox` in Image Table. | **(a)** keep `QColorDialog` for review-image colours and `QComboBox` for the LUT list, and use `ColorSwatchRow` only where the mockup shows a small curated set (trace colours, the section-header value chips); **(b)** replace review-image colours with a curated `ColorSwatchRow` (drops arbitrary-colour choice — a product decision) and add a "more…" escape hatch; **(c)** same as (b) but no escape hatch (fully constrained palette). | If deferred: the **review-image colour-picker** and **Image Table LUT** ports either keep their legacy widgets (a — fine) or wait on this call. Small surface. |
| 11 | `Toast` | `Toast` is fire-and-forget (no buttons, no return value, not modal) — it cannot replace `QMessageBox.question/.critical/.warning` (which the app uses ~40× for confirmations / blocking errors), and it doesn't replace `app._set_status` (persistent text) either. | **(a)** use `Toast` only for fire-and-forget success/info ("Saved layout.awd", "Figure copied") and leave all `QMessageBox` uses + `_set_status` exactly as they are; **(b)** additionally route some current `_set_status` notices through `Toast` and reserve the status bar for persistent state. | Lowest — purely "where do we use the new toast". Nothing is blocked; it's additive. Only matters when a port prompt touches a notification site. |

## Notes

- **Rows 1–3 are one cluster** — the plot-area model. #1 (per-card vs shared
  canvas) must be answered first; #2 (dark vs white) and #3 (SEM/FOV + export)
  follow from it.
- **Rows 5 and 9 both touch `WellPlateSelector`** but are independent: #5 is "do
  we migrate the other six plate-maps and delete the legacy grid"; #9 is "what
  colour are selected wells". #9 can be decided now in isolation; #5 is a
  multi-commit programme.
- **Row 4** has a clearly low-risk option (b — stay native-framed, restyle the
  header). If you pick it, the app-shell port is unblocked immediately and
  `TitleBar` becomes "the in-window header strip" rather than "the OS chrome".
- Everything not in this table from `WIDGET_GAPS.md` is either a `[gap]` for
  behaviour nothing currently uses (e.g. `QSpinBox` special-value text, `QSlider`
  tick marks, `QCheckBox` tri-state) or `[n/a]` (net-new widgets with no legacy
  to lose) — no decision needed; addressable opportunistically.
