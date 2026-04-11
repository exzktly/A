# Runtime Slimming

Tracking the incremental extraction of GUI/viewer code from `well_viewer/runtime_app.py`
into dedicated view files under `well_viewer/views/` and `well_viewer/tabs/`.

Each task moves inline widget-construction code out of `runtime_app.py` and into a
standalone function/class in the appropriate view file.  The `WellViewerApp` method
becomes a thin one-line delegator (matching the pattern already established for
`_build_centre`, `_build_right_panel`, `_build_bottom`, `_build_stats_*`, etc.).

---

## Tasks

- [x] **1. `_Tooltip` class → `views/widgets.py`** (new file)
  Lines 1374–1407 (~33 lines). Small hover-tooltip widget imported by `preview_panel_view.py`.

- [x] **2. `_ImagePanel` class → `views/image_panel_view.py`** (new file)
  Lines 1413–1635 (~220 lines). Self-contained canvas image panel with LUT controls and pixel tooltip. Already imported from `runtime_app` by `preview_panel_view.py`.

- [x] **3. `_GUILogHandler` class → extend `views/status_view.py`**
  Lines 1634–1657 (~24 lines). `logging.Handler` subclass that writes to a `tk.Text` widget. Referenced as `rt._GUILogHandler` in `status_view.py`; moving it breaks the `rt.*` coupling.

- [x] **4. `WellLabel` class + `build_plate_grid` → `views/well_label_widget.py`** (new file)
  Lines 294–517 (~225 lines). Cross-platform `tk.Label` subclass that emulates `tk.Button`; `build_plate_grid` builds the 8×12 grid from it. Tightly coupled; move together.

- [x] **5. `_build_sidebar` → `views/sidebar_view.py`** (new file)
  Lines 1923–2004 (~80 lines). Builds the main well-picker: "WELLS" header, row/col quick-select buttons, 8×12 plate-map, All/None buttons, count/hint labels.

- [x] **6. `_build_bar_group_panel` + bar card builders → `views/bar_group_panel_view.py`** (new file)
  Lines 2406–2470 + 3164–3437 (~315 lines total). The sidebar plate-map/card panel and all six nested card-builder helpers: `_build_bar_perwell_strip`, `_bar_rebuild_groups_ui_now`, `_update_bar_group_count_label`, `_build_bar_group_row`, `_build_bar_group_header`, `_build_bar_group_chip_rows`, `_build_bar_group_action_row`.

- [x] **7. `_build_replicate_panel` → `views/replicate_panel_view.py`** (new file)
  Lines 2480–2542 (~62 lines). Left panel of the Sample Definitions tab: header, quick-replicate dropdowns, plate-map with drag bindings, scrollable card list.

- [x] **8. `_build_group_def_panel` + `_grp_panel_refresh` → extend `views/grouping_view.py`**
  Lines 2838–2893 + 2895–3022 (~183 lines). Right panel builder and card-list refresh for the Sample Definitions tab. `_rep_panel_refresh` already delegates to `grouping_view.py`; this makes `_grp_panel_refresh` consistent.

- [x] **9. `_build_label_editor` + `_label_panel_refresh` → `views/label_editor_view.py`** (new file)
  Lines 3061–3135 (~75 lines). "WELL LABELS" editor in the Sample Definitions centre panel.

- [x] **10. `_build_review_csv_tab` → `tabs/review_csv_tab_view.py`** (new file)
  Lines 5189–5224 (~35 lines). Completes the tab-builder extraction; every other tab already has its own file.

- [x] **11. Update README** with the new architecture overview.
