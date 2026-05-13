# All-Well — Project Status

**Last updated:** session of 2026-05-13
**Active reconciliation branch:** `claude/analyze-repo-structure-2uEVQ`
**Current canonical mockup:** `design/mockup-decoded.html` (decoded from the
`Redesign v2 _standalone_.html` bundle via `scripts/decode_mockup.py`)
**Reconciliation plan:** `design/RECONCILIATION_PLAN.md`
**Mockup audit:** `design/V2_MOCKUP_AUDIT.md`

This file is the single starting point for a fresh chat session. Read this
top-down, then dive into whichever phase or QA item is most pressing.
Everything below references files / commits that exist on the feature
branch `claude/analyze-repo-structure-2uEVQ`; `main` has not yet absorbed
the reconciliation work.

---

## TL;DR — where things stand

The v2 mockup re-anchoring has been executed in 6 phases (`Phase 9–14` in
`RECONCILIATION_PLAN.md`):

| Phase | What it ships | Status |
|---|---|---|
| **9** | Widget round — 7 new widgets + 3 extensions | ✅ shipped |
| **10** | App-shell restructure (titlebar v2, mode-seg, rail nav, statusbar v2, plate selection chip) | ✅ shipped |
| **11** | Plotting ctxbar over per-renderer pages + per-card chrome hidden | ✅ shipped |
| **11b** | Full A3/A4 canvas collapse — 5 renderers into one shared `PlotCanvas`, single global channel chip | ⏳ **DEFERRED** |
| **12** | Properties rail interior (scope segmented + ⌘K search + 8 sections) | ✅ shipped |
| **12b** | Rail controls bound to active figure via `_export_style_prefs` | ✅ shipped |
| **13** | Group B polish (Invert / ⌘ shortcuts / preview wire / cut-corner / compact sidebar Saved list) | ✅ shipped |
| **14** | Doc reconciliation — flip the contradicted decisions in `DECISIONS_NEEDED.md` / `OPEN_DECISIONS.md` / `PORT_PLAN.md` / `DESIGN_NOTES.md` (C1–C17) | ⏳ **PENDING** |

In addition to the planned phases, a number of **ad-hoc UX fixes** landed
during runtime QA: navigation re-layout, plate sizing, sample-definitions
restructure, etc. Those are documented inline below.

---

## Outstanding work

### Phase 11b — full canvas collapse (deferred, high-risk)

The five per-renderer pages (line / bar / scatter cells / scatter agg /
distribution / heatmap) each carry their own `PlotCard` with its own
`matplotlib.Figure`. The mockup spec (Q3 + Q5 from
`RECONCILIATION_PLAN.md` §8) wants ONE shared `PlotCanvas` with N stacked
subplots, one bottom toolbar, and a single global channel chip in the
ctxbar.

Phase 11 shipped the *ctxbar* (`well_viewer/views/centre_view.py`,
`_build_plotting`), so the user sees mockup-faithful chrome. Phase 11b
collapses the renderers themselves.

**Risk:** every controller (`line_graphs_controller`,
`bar_plots_controller`, `scatter_controller`, `distribution_controller`,
`heatmap_controller`) clears + redraws its own figure's axes. Collapsing
them into a shared canvas means re-shaping each renderer to accept a list
of axes from `PlotCanvas.axes()` and emit into them. Different renderers
have different natural axis counts (line wants 3 stacked: mean / fraction
/ CDF; heatmap wants 1 + a colorbar; bar wants 1; etc.).

**Concrete next steps if picked up:**
1. Build a per-renderer adapter that takes `(figure, axes_list)` and
   replaces today's `card.figure.add_subplot(...)` calls.
2. In `widgets/plot_canvas.py`, replace `_redraw_placeholder` with a
   dispatch to the active renderer's adapter.
3. Delete the per-card `PlotCard` mounts in the six plot-tab builders;
   they become thin renderer wrappers that register an adapter.
4. Channel selector hoists from each renderer's controls strip into a
   single `app._active_channel` driven by the ctxbar chip.

**Files to touch:**
- `widgets/plot_canvas.py` — already exists with placeholder renderer.
- `well_viewer/lineplot_controller.py`, `bar_controller.py`,
  `scatter_controller.py`, `distribution_controller.py`,
  `heatmap_controller.py` — per-renderer redraw functions.
- `well_viewer/tabs/{line_graphs,bar_plots,scatter_cells,scatter_agg,
  distribution,heatmap}_tab_view.py` — each one mounts a `PlotCard` today.

**Estimate:** 1–2 working days, plus heavy runtime QA across every renderer.

### Phase 14 — doc reconciliation (C1–C17)

Pure documentation work — no code touched. Flip the decisions that the
re-anchoring inverted so future readers don't run into contradictions
between docs and implementation.

Per `RECONCILIATION_PLAN.md` Section 6:

| ID | Doc | Change |
|---|---|---|
| C1 | `DECISIONS_NEEDED.md` #1 | "per-plot cards … HoverToolbarOverlay in scope" → single shared figure canvas (still pending Phase 11b actually landing). |
| C2 | `DECISIONS_NEEDED.md` #4 | Annotate the mockup divergence — Light theme is parked (Q2 locked Dark only). |
| C3 | `DECISIONS_NEEDED.md` #7 | "secondary tab strip stays QTabWidget" → vertical rail nav. |
| C4 | `OPEN_DECISIONS.md` #3 | Matches C3. |
| C5 | `PORT_PLAN.md` row 26 | "restyle via QSS only" → "rebuild as vertical rail nav". |
| C6 | `PORT_PLAN.md` row 32 | Confirm permanent third column + hideable. |
| C7 | `PORT_PLAN.md` row 36 | Always-on toolbar; HoverToolbarOverlay dropped. |
| C8 | `PORT_PLAN.md` row 41 | Theme combo: deferred, no change. |
| C9 | `PORT_PLAN.md` row 48 | Analyze: top-of-titlebar SegmentedControl peer; no drawer. |
| C10 | `PORT_PLAN.md` §D | Re-issue 8.x phase mapping; reference Phases 9–14. |
| C11 | `DESIGN_NOTES.md` §2.2 | Single canvas + ctxbar.subnav governs whole canvas. |
| C12 | `DESIGN_NOTES.md` §2.3 | Channel chip is global in ctxbar.right. |
| C13 | `DESIGN_NOTES.md` §2.4 / §2.8 | Keep the reversion as the spec; drop the v2-port counter-revert. |
| C14 | `DESIGN_NOTES.md` §2.7 | Analyze is a titlebar SegmentedControl peer. |
| C15 | `DESIGN_NOTES.md` §2.8 | Same as C7. |
| C16 | `DESIGN_NOTES.md` §6.5 | Theme switcher parked. |
| C17 | `mockup-decoded.html` | Append a top-comment banner explaining which DESIGN_NOTES sections it supersedes. |

**Estimate:** half a day.

---

## Outstanding QA (pending sign-off)

These are commits shipped on `claude/analyze-repo-structure-2uEVQ` that
the user has not yet runtime-QA'd. Mark `✅` and move down once verified.

| Commit | Area | What to look for |
|---|---|---|
| `ab78c7d` | Sample Definitions plate height | Resize the window vertically — the plate keeps its 8×12 aspect; the GROUPS list takes the squeeze instead of crushing the wells. |
| `9693d74` | Well Labels 96-well grid | Sample Definitions → Well Labels: 8×12 editable grid replaces the long text-row list. Type into a cell, click row "C" header or column "3" header to select that row/column, Shift-click a cell to toggle it. Add Prefix / Add Suffix act on the grid's selection (fallback: sidebar plate selection). |
| `db13a7f` | GROUPS hoisted to centre + grid lock to loaded wells | Sample Definitions sidebar shows only the plate (with a usage hint below). First centre sub-tab is "Groups" with the SavedSelectionsList + Quick Replicates moved out of the sidebar. Well Labels grid: cells/headers stay disabled until a dataset loads, then only loaded wells become editable. |
| `f1ed2d6` | Plotting ctxbar split into two rows | Plotting section: plot-type SegmentedControl (Line/Bar/Scatter/Dist/Heat) fills its own row; Channel chip + hint + Add panel / Configure subplots / Edit axes-curve / Export figure live in a second row immediately above the canvas. |
| `f05cce4` + `b26b7ff` | Rail UX + Phase 12b bindings | Rail hidden on launch; edge-handle button on the canvas's right edge always visible (arrow `◂` to open, `▸` to close). Titlebar IconButton mirrors. **Phase 12b**: changing Line width / Marker size / Grid opacity / Y log / X-Y limits / etc. in the Properties rail live-updates the active plot. |
| `ca6e21a` | Phase 13 polish | Quick-select row reads "All 96 / Invert / Clear"; tip line below (later removed in 9990bcc). ⌘O / ⌘K / ⌘E global shortcuts work. PreviewStrip in Lines & Markers live-updates. Plate top-left has a tiny cut-corner notch in rail colour. Selected wells render with the radial gradient. |
| `8bb85f6` | Phase 12 rail content | Right rail interior: scope segmented + ⌘K search + 8 collapsible sections (Profile & Format / **Statistics** / Axes / Legend / Lines & Markers / Grid / Limits & Scale / Layout). |
| `cf90561` | Mode-seg in titlebar / OS window title carries dataset name | Titlebar's redundant dataset chip + stats labels are gone; mode-seg (Review · Analyze) sits where they used to. OS window title now reads `All-Well — <dataset> · N wells · N timepoints`. Sidebar starts with SECTION nav directly (no mode-seg). |
| `c3e937b` | Phase 13 final: compact Saved list in sidebar | Sidebar bottom shows a "SAVED [N]" caption + a compact `SavedSelectionsList` mirror of `app._selections` (dot + name + meta only — no kebab/eye/drag). Clicking a row activates that selection. Refreshes with every group edit. |
| `9990bcc` | Sidebar simplification + Analyze hides rail | All 96 / Invert / Clear buttons + "Tip: click a row letter…" line gone from the main sidebar; ditto the Sample Definitions sidebar tip. Plate widget now uses identical `setMinimumHeight(280)` + `Preferred / MinimumExpanding` size policy on both sidebars, so its size + placement stay fixed across every section. Switching to Analyze mode hides the whole left rail (sidebar); switching back to Review restores it. |
| `dce3a62` | Export Style sidebar width | The floating Export Style sidebar (sliders IconButton) shrinks to 440 px and tightens its internal column widths so all controls fit without cutoff. |

### Known bugs reported in this session, not yet fixed

These were called out by the user during the last QA cycle but no fix
has been pushed yet. Carry forward into the next session.

| Bug | Detail |
|---|---|
| **Sample Definitions plate alignment** | Well picker is not aligned to the top of the sidebar. Likely cause: `_sidebar_sample_frame` had a `QVBoxLayout` pre-created in `runtime_app._build_ui` with default ~9 px margins, and `build_replicate_panel`'s `if layout is None` guard skips its `setContentsMargins(0,0,0,0)` call. Fix: clear margins on the pre-created layout, OR have `build_replicate_panel` always reset them. |
| **Review CSV tab does not load data** | The Review CSV tab's content doesn't populate. Investigate `well_viewer/tabs/review_csv_tab_view.py` and the QTableView model wiring; check whether `app._notebook.currentChanged` reaches the deferred builder when the rail nav drives index changes. |

---

## What lives where — quick map

| Area | Files |
|---|---|
| **Reconciliation plan** | `design/RECONCILIATION_PLAN.md` |
| **Mockup audit** | `design/V2_MOCKUP_AUDIT.md` |
| **Canonical mockup** | `design/mockup-decoded.html` + `design/mockup-decoded-assets/` |
| **Mockup decoder** | `scripts/decode_mockup.py` |
| **Pending QA tracker** | `design/PENDING_QA.md` (on feature branch) |
| **App shell** | `all_well.py` |
| **Review widget** | `well_viewer/runtime_app.py` (the WellViewerApp class) |
| **Sidebar (left rail)** | `well_viewer/views/sidebar_view.py` |
| **Properties rail content** | `well_viewer/views/properties_rail_view.py` |
| **Plotting section + ctxbar** | `well_viewer/views/centre_view.py` (`_build_plotting`) |
| **Sample Definitions tab build** | `well_viewer/runtime_app.py` (`_build_sample_definitions_tab`) |
| **Sample Definitions sidebar (plate)** | `well_viewer/views/replicate_panel_view.py` → `build_replicate_panel` |
| **Sample Definitions GROUPS centre** | same file → `build_replicate_groups_centre` |
| **Well Labels grid** | `well_viewer/views/label_grid_view.py` |
| **Phase 9 widgets** | `widgets/{rail_nav,selection_chip,range_pair,kbd_hint,collapsible_rail,preview_strip,plot_canvas}.py` |
| **Theme tokens** | `theme.py` |
| **Selections model (Phase 8.0)** | `well_viewer/selections_model.py`, `well_viewer/persistence/sample_definitions.py` |

---

## Decision lookup table (from RECONCILIATION_PLAN.md §8)

Locked answers that govern Phase 11b and the doc reconciliation:

| Q | Locked | Note |
|---|---|---|
| Q1 | Titlebar icon button only | Rail collapse toggle placement. |
| Q2 | Dark only | Light theme parked. |
| Q3 | Configurable 1–4 subplots | `PlotCanvas.addPanel` / `removePanel`. |
| Q4 | Statistics own section in Properties | Implemented Phase 12. |
| Q5 | ctxbar.subnav governs whole canvas | All subplots switch plot type together. |
| Q6 | Build all three (Add panel, Configure subplots, Edit axes/curve) | Phase 11 chrome shipped; Configure / Edit wrap mpl built-ins. |
| Q7 | Synthesise breadcrumb from dataset path | Now lives in OS window title (`cf90561`). |
| Q8 | Drop count aside on rail nav rows | Implemented. |
| Q9 | Rail width = 400 px | Mockup's 260 widened for plate ergonomics. |
| Q10 | Per-subplot axes independent | `PlotCanvas` no `sharex`/`sharey`. |
| Q11 | Drawer with recent log entries | Statusbar Log tray opens a Drawer. |
| Q12 | Fixed subplot order | Insertion order; no drag-reorder. |

---

## How a new session should bootstrap

1. **Read this file first.** It points at every other doc.
2. **Then `design/RECONCILIATION_PLAN.md`.** Has every phase's deliverables, dependency graph, and risk register.
3. **Then `design/PENDING_QA.md`** on the feature branch (`claude/analyze-repo-structure-2uEVQ`) for the live list of commits awaiting sign-off.
4. **For Phase 11b:** survey the per-renderer controllers and `widgets/plot_canvas.py`'s placeholder; the adapter contract is the key design question.
5. **For Phase 14:** the C1–C17 table above is exhaustive — every edit is mechanical, no fresh decisions needed.
6. **For new ad-hoc UX work:** confirm against `design/mockup-decoded.html` (the canonical source) and update `design/PENDING_QA.md` after every push.
