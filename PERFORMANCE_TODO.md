# GUI Performance TODO Tracker

Last updated: 2026-04-11 (UTC)

Purpose: track performance remediation work so another AI can resume safely if interrupted.

## Scope
- Implement suggestions **1, 2, 3, and 5** from investigation.
- Explicitly out of scope: `process_microscopy_v2.py`.

## Tasks

- [x] **(1) Remove redundant redraw cascades from plate selection handlers**
  - Files:
    - `well_viewer/selection_controller.py`
    - `well_viewer/plot_orchestrator.py`
  - What changed:
    - Added `_active_tab()` and `_refresh_after_selection_change()` helpers.
    - `on_plate_sel_change`, `select_all`, `select_none` now refresh only active-tab views.
    - Removed tab-driven bar/scatter redraw fan-out from `plot_orchestrator.redraw()`.
  - Rationale:
    - Prevent duplicate heavy recomputes (`_redraw` + `_redraw_bars` + `_redraw_scatter`) on each selection event.

- [x] **(2) Cache scatter interaction points for hover/click**
  - Files:
    - `well_viewer/scatter_controller.py`
    - `well_viewer/runtime_app.py`
  - What changed:
    - `redraw_scatter()` now builds `app._scatter_interaction_cache["points"]` as flat `(x, y, metadata)` tuples.
    - `_on_scatter_click` and `_on_scatter_motion` now read from that cache (no per-event `_scatter_collect_data` rebuild).
    - Clears cache when no selection data is available.
  - Rationale:
    - Hover events can fire at high frequency; recomputing all scatter points each motion was O(total points) data rebuild + nearest-neighbor scan.

- [x] **(3) Debounce sidebar recolor and remove forced idle flush**
  - Files:
    - `well_viewer/runtime_app.py`
  - What changed:
    - Added `_sidebar_map_refresh_pending` state.
    - Converted `_refresh_sidebar_map()` into a debounced scheduler using `after(0, ...)`.
    - Moved original recolor body to `_refresh_sidebar_map_now()`.
    - Removed unconditional `update_idletasks()` from sidebar map refresh path.
  - Rationale:
    - Avoid synchronous GUI flush + repeated full button restyles during rapid selection operations.

- [x] **(5) Cache global timepoints for bar/scatter menu population**
  - Files:
    - `well_viewer/runtime_app.py`
    - `well_viewer/load_controller.py`
  - What changed:
    - Added `self._all_timepoints_cache`.
    - Added `_rebuild_all_timepoints_cache()` in `runtime_app.py`.
    - Called cache rebuild once after CSV load in `load_controller.load_directory()`.
    - `_update_bar_tp_menu()` and scatter menu timepoint setup now read from cache first.
  - Rationale:
    - Avoid scanning every row of every well on each menu refresh/redraw.

## Handoff notes for next AI
- If behavior regressions appear in tab-specific refreshes, inspect `selection_controller._refresh_after_selection_change()` first.
- If scatter hover/click looks stale, ensure `redraw_scatter()` runs after every input change (channel/timepoint/gates/selection).
- If new data-loading paths are added, ensure they call `_rebuild_all_timepoints_cache()`.
- Consider adding lightweight profiling counters around:
  - `_refresh_sidebar_map_now`
  - `_redraw_scatter`
  - `_update_bar_tp_menu`
