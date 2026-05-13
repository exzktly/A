# QA Issues — All-Well Well Viewer

_Last updated: 2026-05-13_

This file tracks known issues, regressions, and items that require manual QA verification.
Items are grouped by area. Fixed items are retained for traceability.

---

## Layout & UI

| # | Status | Area | Description |
|---|--------|------|-------------|
| L1 | ✅ Fixed | Heatmap sidebar | Layout configurator grid was cut off at the bottom because the trailing `addStretch(1)` in `build_sidebar` consumed all remaining height. Fixed: `heatmap_frame` now carries `stretch=1` and the trailing spacer was removed. |
| L2 | ✅ Fixed | Sample Definitions sidebar | Well-picker plate map was not aligned to the top — a 6 px default Qt spacing appeared above it because `setContentsMargins/setSpacing` were inside the `if layout is None` branch. Fixed: both calls moved outside the conditional. |
| L3 | ✅ Fixed | Main splitter | The divider between the left sidebar and centre panel was only 2 px wide and showed no resize cursor, making it very hard to drag. Fixed: `setHandleWidth(6)`, QSS updated to `width: 6px; cursor: col-resize`. |
| L4 | Open | Export dock | The right-side export-style dock (▸ panel) does not remember its width between sessions. |
| L5 | Open | Bar / Line scroll | When the scroll canvas is very tall and the user scrolls down, switching tabs and returning resets the scroll position to the top. |

---

## Data Loading & Review CSV

| # | Status | Area | Description |
|---|--------|------|-------------|
| D1 | ✅ Fixed | Review CSV tab | After "Make pandas DataFrame canonical" refactor, `_get_rows()` returned a `DataFrame`; the old code called `.items()` on it expecting a list-of-dicts, producing an empty table. Fixed: `df.to_dict("records")` conversion added. |
| D2 | ✅ Fixed | Review CSV tab | Signal race: `currentIndexChanged` fired `_refresh_review_csv_rows(rows=None)` mid-combo-update, re-deriving rows in an inconsistent filter state. Fixed: `blockSignals` wraps the entire combo update block; rows are cached in `_review_csv_rows_cache`. |
| D3 | Open | CSV loading | Files with non-ASCII paths on Windows produce a `UnicodeDecodeError` in `load_well_csv`; no user-facing error message surfaces. |
| D4 | Open | Review CSV | The "FOV" dropdown in the Review CSV tab shows raw numeric strings (e.g. `"1"`, `"2"`) instead of zero-padded values when FOV values come from different wells with mixed formats. |

---

## Plot Tabs

| # | Status | Area | Description |
|---|--------|------|-------------|
| P1 | ✅ Fixed | All plot tabs | No "Copy SVG" button; users had to use the matplotlib toolbar save dialog to get vector output. Added "Copy SVG" button next to "Export CSV" on Line Graphs, Bar Plots, Scatter Cells, Scatter Agg, Distribution, Heatmap, and smFISH tabs. |
| P2 | ✅ Fixed | smFISH tab | Export style panel (▸ button) was absent from the smFISH tab. Added to Row 2 of controls; `"smfish"` key wired into `_open_export_style_panel`. |
| P3 | Open | Line Graphs | The CDF subplot x-axis label overlaps the Fraction On subplot when the figure is short (< 700 px height). Needs `subplots_adjust` or `tight_layout` call after resize. |
| P4 | Open | Bar Plots | Beeswarm overlay renders on top of violin when both toggles are active, but the toggle buttons have no visual interlock; both can be simultaneously checked which produces a cluttered plot. |
| P5 | Open | Scatter Agg | Timepoint selector popup does not restore scroll position when the list is long (> ~15 timepoints). |
| P6 | Open | Heatmap | "Export CSV" exports the raw numeric matrix without row/column well labels, making it hard to interpret outside the app. |
| P7 | Open | Distribution | "Violin (per group)" mode crashes with `ValueError` when a group has fewer than 2 data points. |

---

## smFISH

| # | Status | Area | Description |
|---|--------|------|-------------|
| S1 | Open | smFISH tab | "Apply Global Threshold" blocks the UI thread for large datasets (many wells × FOVs). Should offload to `QThreadPool` or show a progress dialog. |
| S2 | Open | smFISH tab | After "Apply Global Threshold" finishes, the main cache is refreshed but the smFISH per-frame CDF popup (if open) is not updated to reflect new threshold values in the fresh data. |
| S3 | Open | smFISH tab | Scroll-to-zoom on the smFISH image does not clamp to image bounds; repeated scrolling can zoom out indefinitely to a blank canvas. |

---

## Export & Style Panel

| # | Status | Area | Description |
|---|--------|------|-------------|
| E1 | Open | Export style panel | Changing DPI in the export style panel does not redraw the canvas at the new DPI in real-time — only the saved PNG/SVG reflects the setting. |
| E2 | Open | Export style panel | "Reset to defaults" in the export style panel resets font sizes but not the figure background colour when a non-default theme colour was applied. |

---

## Theming

| # | Status | Area | Description |
|---|--------|------|-------------|
| T1 | Open | Light theme | Several `get_color("ACCENT")` calls in plot controllers return the dark-theme accent hex directly rather than resolving through the theme token, so accent colours do not update when switching from dark → light theme without restarting the app. |

---

## Known Won't-Fix / By Design

| # | Area | Description |
|---|------|-------------|
| W1 | smFISH CDF popup | The CDF popup is modal-less and can remain open while the user navigates to another tab. Closing and reopening is idempotent. |
| W2 | Review CSV | Columns are displayed in CSV file order, not alphabetical, to preserve semantic grouping (identifiers first, then measurements). |
