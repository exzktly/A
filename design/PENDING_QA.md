# Pending QA

Items shipped on `claude/analyze-repo-structure-2uEVQ` that have **not yet
been runtime-QA'd** by the user. Each row gets a one-line description,
its commit SHA, and what to look for. Mark `✅` when you sign off in
this session; rows that pass move out of this list at the next push.

## Awaiting QA

| Commit | Area | What to look for |
|---|---|---|
| `ab78c7d` | Sample Definitions plate height | Resize the window vertically — the plate keeps its 8×12 aspect; the GROUPS list takes the squeeze instead of crushing the wells. |
| `9693d74` | Well Labels 96-well grid | Sample Definitions → Well Labels: 8×12 editable grid replaces the long text-row list. Type into a cell, click row "C" header or column "3" header to select that row/column, Shift-click a cell to toggle it. Add Prefix / Add Suffix act on the grid's selection (fallback: sidebar plate selection). |
| `db13a7f` | GROUPS hoisted to centre + grid lock to loaded wells | Sample Definitions sidebar shows only the plate (with a usage hint below). First centre sub-tab is "Groups" with the SavedSelectionsList + Quick Replicates moved out of the sidebar. Well Labels grid: cells/headers stay disabled until a dataset loads, then only loaded wells become editable. |
| `f1ed2d6` | Plotting ctxbar split into two rows | Plotting section: plot-type SegmentedControl (Line/Bar/Scatter/Dist/Heat) fills its own row; Channel chip + hint + Add panel / Configure subplots / Edit axes-curve / Export figure live in a second row immediately above the canvas. |
| `f05cce4` + `b26b7ff` | Rail UX + Phase 12b bindings | Rail hidden on launch; edge-handle button on the canvas's right edge always visible (arrow `◂` to open, `▸` to close). Titlebar IconButton mirrors. **Phase 12b**: changing Line width / Marker size / Grid opacity / Y log / X-Y limits / etc. in the Properties rail live-updates the active plot. |
| `ca6e21a` | Phase 13 polish | Quick-select row reads "All 96 / Invert / Clear"; tip line below. ⌘O / ⌘K / ⌘E global shortcuts work. PreviewStrip in Lines & Markers live-updates. Plate top-left has a tiny cut-corner notch in rail colour. Selected wells render with the radial gradient. |
| `8bb85f6` | Phase 12 rail content | Right rail interior: scope segmented + ⌘K search + 8 collapsible sections (Profile & Format / **Statistics** / Axes / Legend / Lines & Markers / Grid / Limits & Scale / Layout). |
| `cf90561` | Mode-seg in titlebar / OS window title carries dataset name | Titlebar's redundant dataset chip + stats labels are gone; mode-seg (Review · Analyze) sits where they used to. OS window title now reads `All-Well — <dataset> · N wells · N timepoints`. Sidebar starts with SECTION nav directly (no mode-seg). |
| _NEXT_ | Phase 13 final: compact Saved list in sidebar | Sidebar bottom shows a "SAVED [N]" caption + a compact `SavedSelectionsList` mirror of `app._selections` (dot + name + meta only — no kebab/eye/drag). Clicking a row activates that selection. Refreshes with every group edit. |

## Recently-cleared QA (most recent first)

- `c1d2096` — Phase 10 app-shell (titlebar v2, mode-seg, statusbar, rail).
- `8c2fe7d` — Phase 11 ctxbar over Plotting renderers.
- `5c3218b` — mode-seg hoisted into sidebar; Analyze in WellViewerApp's central stack.
- `c09bc1f` — Review/Analyze label centring + Properties rail scoped to Review centre.
- `7dff6e6` — Phase 11b chrome cleanup: per-card headers hidden.

Add a new row whenever a commit is pushed with visible behaviour for the
user to verify; remove or strike through after sign-off.
