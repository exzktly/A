# Post-port cleanup audit

> **Status:** catalogue only — **no deletions** in this PR. Each item below is a
> candidate for a follow-up cleanup PR.

## Why this exists

A major UI port just finished:

- **PR #206** merged the right-edge Properties rail into the floating Export
  Style sidebar, leaving a handful of no-op stubs behind.
- Earlier work replaced the v1 `WellButton` grid with the v2
  `WellPlateSelector`, completed Phase 6.5 (custom widgets round), and
  migrated saved selections to the v2 model.

What survives a refactor of that size:

1. **Dead callable code** — methods/functions/files with no callers.
2. **Compat shims** — aliases and back-compat constants kept for now-vanished
   call sites.
3. **Documentation & comment debt** — historical "Phase N" / "v2" / "(retired)"
   markers in docstrings, plus completed-migration docs in `design/`.

Each entry was verified with `grep` so the catalogue is reproducible. Risk
columns are conservative: `none` means no callers at all, `low` means tightly
scoped non-API changes, `medium` means user-visible or test-needed.

---

## 1. Dead methods & no-op stubs

| Location | What | Why safe | Risk |
|---|---|---|---|
| `all_well.py:304-308` | `_focus_props_search` — no-op after the Properties rail was deleted. | Body is `return`. Tied to a `Ctrl+K` shortcut and a help-text mention (`all_well.py:289`, `all_well.py:552-553`) that should go with it. | low |
| `all_well.py:612-615` | `_on_rail_toggle_clicked` — no-op stub kept "for legacy callers". | Zero references in the codebase. | none |
| `all_well.py:617-619` | `_on_rail_collapsed_changed` — no-op stub. | Zero callers. The two `getattr` guards at lines 165 & 218 are themselves stale comments referring to the removed rail. | none |
| `well_viewer/runtime_app.py:921` | `_apply_cell_gating_to_included` | Zero callers — never invoked anywhere in the app. | none |
| `well_viewer/runtime_app.py:2453` | `_bar_groups_prune` — body is `return`. | One caller in `well_viewer/load_controller.py:102`, invoking a deliberate no-op. Remove the caller and the method together. | low |
| `well_viewer/runtime_app.py:2980` | `_clear_montage_crop` | Zero callers. Thin wrapper around `_montage_crop_tool.clear()`. | none |
| `well_viewer/runtime_app.py:1142-1156` | `_refresh_sidebar_saved_list` | Guards against `None` attributes. Called once at `runtime_app.py:2229` with the comment _"Phase 13 B8: compact Saved mirror"_; the underlying placeholders live at `well_viewer/views/sidebar_view.py:148-149` (`_sidebar_saved_list = None`, `_sidebar_saved_count_chip = None`). Whole chain can come out together. | low |
| `well_viewer/_selftest_migration.py` | Phase 8.0 selections-migration self-test. | Not invoked by tests, CI, or any module. Run manually with `python well_viewer/_selftest_migration.py` according to its own docstring — and that migration is signed off (see Section 6). | low |

---

## 2. Unused widget files

| Location | What | Why safe | Risk |
|---|---|---|---|
| `widgets/gallery.py` (~1121 lines) | Visual gallery of every v2 widget. | Zero importers anywhere in the codebase; the file only runs as a `python widgets/gallery.py` demo harness. Phase 9 reconciliation widget. | none |
| `widgets/binding_check.py` (~183 lines) | Round-trip binding adapter checker. | Imported only inside `gallery.py`'s `__main__` block. If `gallery.py` goes, this goes with it. | none |

---

## 3. Widget `__main__` demo blocks (optional)

Twelve widget files ship 40–75 line `if __name__ == "__main__":` visual-test
harnesses. They're handy during development; treat this as a stylistic call
(remove vs. move to `widgets/_demos/`).

| Widget | Block start | Approx size |
|---|---|---|
| `widgets/plot_card.py` | 450 | 68 |
| `widgets/window_resize_grips.py` | 204 | 75 |
| `widgets/title_bar.py` | 463 | 59 |
| `widgets/collapsible_rail.py` | 246 | 59 |
| `widgets/popover.py` | 214 | 63 |
| `widgets/saved_selections_list.py` | 1092 | 64 |
| `widgets/gradient_strip.py` | 149 | 54 |
| `widgets/plot_canvas.py` | 273 | 54 |
| `widgets/preview_strip.py` | 145 | 53 |
| `widgets/icon_button.py` | 109 | 53 |
| `widgets/hover_toolbar_overlay.py` | 106 | 48 |
| `widgets/rail_nav.py` | 293 | 42 |

(`widgets/lut_selector.py`'s demo block is roughly the same size; it shipped
just before the port wrapped up.)

---

## 4. Compat shims & legacy constants

| Location | What | Why safe (or not) | Risk |
|---|---|---|---|
| `ui/theme/styles.py:209-211` | `BTN_FLAT_BG` / `BTN_FLAT_TEXT` / `BTN_FLAT_TEXT_DISABLED` | Zero importers in the codebase. Aliases for the dark-only flat-button styling that's been replaced. | none |
| `well_viewer/views/export_style_sidebar_view.py:1055` | `_ExportStyleSidebar = ExportStyleSidebar` | Leading-underscore alias for "callers that imported the leading-underscore name". `grep` finds zero external importers (only the module docstring at line 3 references it). | none |
| `ui/theme/styles.py:177-180` | `globals()[_name] = _value` loop that re-exposes `_DARK_THEME` keys as module-level constants. | **Keep — load-bearing.** Used by `well_viewer/runtime_app.py` for `PLOT_BG`, `PLOT_SPN`, `WARN`, `CLR_*` and friends. Only the comment ("Back-compat module-level color constants") is stale wording; the constants themselves are part of the live API. | n/a |

---

## 5. Stale historical comments

These are cosmetic — collapsing them is a single-PR docstring pass. None of
the underlying code is affected.

- `widgets/__init__.py:1` — _"Custom widgets for the All-Well v2 UI."_
- `theme.py:5` — _"Design tokens for the All-Well v2 interface."_
- `theme.py:299-301` — _"Plate-map well buttons (legacy WellButton grid)."_
  The QSS rules below are still consumed; keep the rules, retire the framing.
- Eight `widgets/*.py` docstrings tagged **Phase 6.5.x**: `popover.py`,
  `gradient_strip.py`, `color_picker_popover.py`, `lut_selector.py`,
  `well_plate_selector.py`, `title_bar.py`, `window_resize_grips.py`,
  `saved_selections_list.py`.
- `widgets/plot_canvas.py:10-20`, `widgets/plot_card.py:1, 236, 415` —
  "Phase 9 / Phase 11 / v2 token look" markers.
- `widgets/gallery.py:31, 50, 79` — "Phase 9 reconciliation widgets"
  (moot once Section 2 lands).
- Tab views with Phase 11b markers: `heatmap_tab_view.py:183`,
  `distribution_tab_view.py:105`, `scatter_agg_tab_view.py:78`,
  `scatter_cells_tab_view.py:72`, `line_graphs_tab_view.py:38, 83`,
  `bar_plots_tab_view.py:42, 122`.

---

## 6. Completed migration / phase docs

Self-described as done at the top of each file:

| File | Header verdict |
|---|---|
| `design/PHASE_6_5_PLAN.md` | _"Status: ✅ DONE."_ All deliverables met; gallery + binding harness QA signed off 2026-05-12. |
| `design/SELECTIONS_MIGRATION.md` | _"Status: ✅ DONE — runtime-QA'd & signed off."_ Approved 2026-05-12. |
| `design/WELL_SELECTOR_GAP.md` | _"Status: ✅ DONE — `WellButton` is gone."_ Body marked historical. |
| `design/PHASE_4_DIAGNOSIS.md` | _"Status: root cause identified. No code changed yet."_ Diagnostic-only artifact for a long-resolved theme.qss() chrome bug. |

**Keep** `design/PORT_PLAN.md` and `design/PROJECT_STATUS.md` — they still
describe live state and reference scripts (e.g. `decode_mockup.py`).

---

## 7. Active "legacy"-tagged code that must STAY

Listed so future cleanup passes don't mistake the label for permission:

- `well_viewer/runtime_app.py:1850` `_rep_set_id_at` — legacy bridge but still
  called twice from rep-set selection paths.
- `well_viewer/runtime_app.py:5869-5883` `_rep_sets_loaded` /
  `_groups_from_rep_sets` / `_rep_sets_active` — used across scatter, line,
  heatmap, and batch_export modules.
- `services/input_resolution_service.py`, `services/pipeline_runner.py`,
  `services/pipeline_service.py` — all three are live consumers of the
  Analyze tab (`analyze_tab.py:30, 31, 36`).
- All four QSS theme files (`dark.qss` / `light.qss` / `amber.qss` /
  `beige.qss`) — wired via `ui/theme/theme_manager.py:70` and `styles.py`.
- `process_microscopy_v2.py` — no v1 file exists in the repo; "v2" is purely
  historical naming. Live consumer in `all_well_launcher.py:45` and
  `analyze_tab.py:31`.
- `widgets/_support.py` — `lerp_color` / `with_alpha` / `run_demo` consumed
  by multiple widgets.
- `widgets/_window_chrome.py` — `should_use_frameless()` consumed by
  `title_bar.py`.

---

## Suggested follow-up sequence

When the team is ready, ship the deletions in roughly this order so each PR
stays reviewable:

1. **Dead method sweep** (Section 1) — single PR, no behaviour change.
2. **Demo file removal** (Section 2: gallery + binding_check).
3. **Compat shim removal** (Section 4 first two rows).
4. **Docstring / comment de-historicising** (Section 5).
5. **Archive done phase docs** (Section 6) — move to `design/_archive/`
   rather than deleting, so the design history stays browsable.

Each follow-up should re-run the relevant `grep` to confirm nothing crept in
between this audit and the deletion PR.
