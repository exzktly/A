# All-Well Architecture

This document is the starting map of the All-Well codebase. It explains how the
application is organised, why files are split the way they are, and how to
read, modify, and debug the code without having to spelunk for two hours
first. Read it linearly the first time; come back to specific sections when
you're chasing a bug or planning a feature.

The current code reflects an iterative port from a Tk prototype to a Qt
desktop app (PySide6). Some of the structural decisions only make sense once
you know that — they're called out where relevant.

---

## 1. What All-Well is

All-Well is a desktop application that does two things:

1. **Analyze.** Run a fluorescence microscopy pipeline against a folder of
   raw images: nuclear segmentation (StarDist), background subtraction,
   per-cell intensity quantification, smFISH spot counting, then export of
   per-well CSVs and per-well processed-image ZIPs.
2. **Review.** Load the CSVs the pipeline produced and explore them: plate
   maps, line / bar / scatter / distribution / heat-map plots, statistics,
   image preview, batch export, etc.

The same window hosts both modes — a segmented control in the title bar
switches between them — and a single dataset folder is the unit of work that
flows from Analyze (writes it) to Review (reads it).

```
   Raw images
      │
      ▼
  Analyze tab ──▶  process_microscopy.py  ──▶  <data>/{<well>_out.zip, *.csv, pipeline_info.json}
                                                        │
                                                        ▼
                                                  Review tab
```

---

## 2. The two-mode shell

The application root (`AllWellApp` in `all_well.py`) owns a title bar and a
central pane stack. The central stack has two pages:

| Pane | Mode | Implemented by | Source file |
|------|------|----------------|-------------|
| Page 0 | **Review** | `WellViewerApp(QWidget)` | `well_viewer/runtime_app.py` |
| Page 1 | **Analyze** | `AnalyzeTab(QWidget)` | `analyze_tab.py` |

The title bar's `SegmentedControl` (`Review` / `Analyze`) drives the stack.
Both panes are constructed eagerly at startup so switching back and forth is
instant; widget trees inside them build lazily on first use (see §5.4).

A handful of things live on the application root rather than per-pane because
they're shell-wide:

- **Stylesheet.** `theme.qss()` is set as the application-wide QSS string in
  `AllWellApp._apply_stylesheet`. All chrome reads from it.
- **Help drawer + keyboard shortcuts** (`Ctrl+O`, `Ctrl+E`, `Ctrl+←`/`→`).
- **Status bar** (bottom of the window) with a `StatusDot` and key-hint
  chips.
- **App icon, window geometry persistence.**

---

## 3. Top-level directory map

```
allwell/
├── all_well.py                  ← app entry point + title bar shell
├── all_well_launcher.py         ← PyInstaller entry point + --run-pipeline dispatch
├── analyze_tab.py               ← Analyze pane (form + run controls + live log)
├── process_microscopy.py        ← the actual analysis pipeline (CLI + library)
├── WellPlateZipper.py           ← input-folder packing utility (96-well .zip set)
├── auto_threshold_core.py       ← Otsu helpers shared by pipeline + GUI (stdlib + numpy only)
├── well_token.py                ← canonical 96-well token parser (stdlib only)
├── theme.py                     ← v2 design tokens (Colors / Typography / Spacing / Radii)
├── well_viewer/                 ← Review pane (the bulk of the app)
├── widgets/                     ← reusable Qt widgets (no app coupling)
├── ui/theme/                    ← QSS themes + Template-string driver (palette + plot tokens)
├── services/                    ← Analyze-side service modules
├── scripts/                     ← build_executable.sh, dev helpers
├── _Docs/                       ← installer / requirements / icon SVGs + this Planning.md
├── Markdowns/                   ← live docs (this file, README, model contract, icons readme)
├── tests/                       ← pytest scaffold (added in #248; pure-Python no Qt)
└── design/                      ← HTML mockups + screenshots — visual reference only
```

The two top-level helpers `auto_threshold_core.py` and `well_token.py` are
*deliberately at repo root* (not under `well_viewer/`): the pipeline contract
forbids `well_viewer` / `widgets` / Qt imports, so anything both the pipeline
and the GUI need to agree on has to live in a Qt-free module the pipeline can
import. See §6.2 for the contract.

A few rules of thumb so you know where to put something new:

- **It runs the pipeline →** put it in / next to `process_microscopy.py`. Keep
  the pipeline self-sufficient — it must run with no dependency on
  `well_viewer/` (see §6.2).
- **It's a Review-side tab body or sidebar →** `well_viewer/tabs/` or
  `well_viewer/views/`.
- **It's a Review-side stateful behaviour (data load, redraw, persistence)
  →** `well_viewer/<noun>_controller.py` or `well_viewer/persistence/`.
- **It's a reusable Qt widget with no All-Well-specific knowledge →**
  `widgets/`.
- **It's a design token / colour / size →** `theme.py` (for code) and
  `ui/theme/*.qss` (for QSS); never hardcode hex values in code.

---

## 4. Startup sequence

In one diagram, end-to-end:

```
all_well_launcher.main()                       (PyInstaller bundle only)
    │
    ▼ regular Python run jumps in here:
all_well.main()
    ├── QApplication(sys.argv)
    ├── theme_v2.Typography.family ← app.font().family()      ← collapse QSS family list
    ├── app.setStyleSheet(theme.qss())                        ← global QSS
    ├── AllWellApp().__init__
    │       ├── _build_ui()
    │       │    ├── title bar (mode seg, Open, Help, …)
    │       │    └── central stack:
    │       │         ├── page 0  ←  WellViewerApp() (Review)
    │       │         │       ├── _build_ui()
    │       │         │       │    ├── topbar
    │       │         │       │    ├── splitter:
    │       │         │       │    │   ├── sidebar  ← views.sidebar_view.build_sidebar
    │       │         │       │    │   └── centre stack
    │       │         │       │    │           ← views.centre_view.build_centre
    │       │         │       │    │           ├── pages dict {title → builder}
    │       │         │       │    │           ├── eager-builds the first page
    │       │         │       │    │           └── queues the rest in `pending`
    │       │         │       │    └── status bar
    │       │         │       └── (drain timer picks up `pending` builders)
    │       │         └── page 1  ←  AnalyzeTab()
    │       ├── _install_shortcuts()
    │       └── _restore_window_state()
    ├── window.show()
    └── app.exec()
```

Two important details:

1. **Lazy tab bodies.** `build_centre` returns immediately with most centre
   pages still un-built. A `QTimer.singleShot(0, …)` drain or a tab-change
   event triggers each builder on first need. This is what keeps the first
   paint fast even though the app has a lot of widget surface.
2. **Optional `--data_dir` argument** is queued with `QTimer.singleShot(150,
   …)` so the first paint completes before the dataset starts loading. This
   keeps the UI responsive while a few hundred CSVs stream in.

---

## 5. The Review side (`well_viewer/`)

The Review pane is the bulk of the codebase. Treat the package as four
layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  views/   ← Qt widget trees / layouts (no business logic)       │
│           ── centre_view (the page stack)                       │
│           ── sidebar_view (the left rail body)                  │
│           ── …other panel-shaped pieces (preview, stats, etc.)  │
├─────────────────────────────────────────────────────────────────┤
│  tabs/    ← builders for each centre page's body                │
│           ── line_graphs_tab_view, bar_plots_tab_view, …        │
│           ── one module per top- or sub-tab                     │
├─────────────────────────────────────────────────────────────────┤
│  controllers (top-level *.py)  ← all stateful behaviour          │
│           ── load_controller, selection_controller,             │
│              lineplot_controller, barplot_controller,           │
│              scatter_controller, heatmap_controller,            │
│              stats_controller, distribution_controller,         │
│              image_table_controller, montage_controller,        │
│              smfish_controller, review_image_controller,        │
│              plot_orchestrator, …                                │
├─────────────────────────────────────────────────────────────────┤
│  data + persistence                                              │
│  data_loading, image_discovery, image_resolver,                  │
│  selections_model, viewer_state, plate_layout,                   │
│  sample_definitions, gating_state, auto_threshold,               │
│  batch_models, heatmap_models, ratio_models                      │
│  persistence/  ← JSON file I/O (one module per file)            │
└─────────────────────────────────────────────────────────────────┘

runtime_app.WellViewerApp  ← composes all four layers together
```

### 5.1 `runtime_app.WellViewerApp`

The `WellViewerApp(QWidget)` class is the central god-object. It is large
(roughly 6.7 k lines, ~400 methods) **on purpose** — every centre tab and
sidebar panel writes attributes onto it (e.g. `app._line_fig`,
`app._chan_cb_bar`, `app._selected_wells`) so that controllers can reach
state from anywhere without circular imports. Think of it as a typed
namespace.

What lives directly on `WellViewerApp`:

- **State:** loaded wells (`_well_paths`), the per-well row cache
  (`_cache`), the current selection (`_selected_wells`), the active
  channel / metric / threshold, the saved-selections list (`_selections`).
- **Widget handles:** every centre figure / canvas / dock the tab views
  produce gets stashed here (e.g. `_line_fig`, `_bar_canvas`,
  `_heatmap_export_dock`).
- **One-shot helpers:** legacy or back-compat wrappers, dialog launchers,
  small UI utilities (`make_fluor_thumb`, `ask_name_dialog`, …).
- **Method aliases:** a long list of `def _foo(self, …): return
  controller.foo(self, …)` shims. These are deliberate — they let
  controllers stay GUI-free pure functions while the rest of the app
  continues to call `self._foo(…)`. When you see `self._redraw_bars()`
  on `WellViewerApp`, follow it into `well_viewer/barplot_controller.py`.

When you add behaviour, prefer to write a new free function in a
`*_controller.py` module and add a one-line wrapper on `WellViewerApp`
rather than putting logic directly on the class.

### 5.2 The page stack: `views/centre_view.py`

`build_centre(app, parent)` returns nothing; it mutates `app._notebook`
(a `NamedPageStack` — a `QStackedWidget` subclass with name-keyed pages)
and registers every centre page. The current page-list:

| Section | Tab | Sub-pages |
|---------|-----|-----------|
| Analysis | **Plotting** | Line Graphs / Bar Plots / Scatter Plot / Distribution / Heat Map |
| Analysis | **Statistics** | — |
| Images | **Image Table** | — |
| Images | **Segmentation** | Segmentation / smFISH |
| Data | **Review CSV** | — |
| Data | **Sample Definitions** | (includes Cell Gating as a sub-section) |
| Data | **Batch Export** | — |

Two of the top-level entries (Plotting, Segmentation) are *parent* tabs
whose body is a nested `NamedPageStack`. `WellViewerApp._current_centre_tab()`
descends through that one level of indirection so the rest of the app can
always pattern-match on a leaf name (e.g. `"Line Graphs"`, `"smFISH"`).

The left **rail navigation** (`RailNav` from `widgets/rail_nav.py`) is the
single visible selector for the top-level pages. It mirrors the notebook —
clicking a rail item drives `_notebook.setCurrentByName(name)`; programmatic
changes to the notebook drive the rail back via
`WellViewerApp._on_notebook_current_changed`. The QTabWidget tab bar from
the v1 UI is gone; the page stack is purely name-keyed.

### 5.3 Centre tab builders: `tabs/<x>_tab_view.py`

Each module exposes a single `build_<name>_tab(app, parent)` function. The
function:

1. Creates a `make_plot_with_right_dock(parent)` host (returns
   `(plot_area, layout, right_dock)`) — the right-side dock is reserved for
   the Properties / Export Style sidebar.
2. Adds the per-tab controls row (channel ctxbar, metric combo, timepoint
   combo, action buttons — Export CSV, Copy SVG, Save figure, **Properties**).
3. Mounts a `PlotCard` from `widgets/plot_card.py` (matplotlib figure +
   custom toolbar inside a styled panel).
4. Stashes the figure / canvas on `app` so controllers can reach them
   later (`app._line_fig`, `app._bar_canvas`, …).
5. Wires signals to the corresponding controller's redraw entry point
   (e.g. `_redraw_bars` → `barplot_controller.redraw_bar_plots`).

The split between `tabs/` and `views/` is deliberate:

| | `tabs/` | `views/` |
|--|---------|----------|
| Granularity | One module per *centre page* | Many panel-shaped builders |
| Couples to | The runtime app's per-tab attributes | Smaller surfaces (sidebar, preview, stats list) |
| Typical caller | `centre_view._build_<tab>()` | A `tabs/` module *or* `runtime_app._build_sidebar` |

In one sentence: if it's the body of a centre page, it's a `tabs/` module;
if it's any other panel-shaped composition, it's a `views/` module.

One `tabs/` module is a shared widget helper rather than a centre-page
builder: `tabs/fold_change_controls.py` exposes
`install_fold_change_controls(app, parent, layout, scope=…)` — the
Control + Baseline dropdown pair installed on both the Bar Plots and
Line Graphs control rows. It owns the cross-tab widget sync
(`_sync_widgets_to_state`) that mirrors each state change into the
other tab's widget instances, so the shared `app._fc_*` state stays
visually in lockstep across tab switches.

### 5.4 The left sidebar

`views/sidebar_view.build_sidebar(app, parent)` builds the well picker
(`widgets/well_plate_selector.WellPlateSelector`) plus the **Select all /
Select none** buttons, the selection-count chip, and the group hint label.
Selection signals route through `WellViewerApp._on_sidebar_plate_*` methods,
which delegate into `well_viewer/selection_controller.py`.

Other sidebar bodies (preview picker, image-table picker, sample-definitions
group editor, stats group editor) live in `views/*_view.py`. They're stacked
inside the same sidebar QWidget and shown/hidden by `_on_tab_change` based
on the active tab.

### 5.5 Controllers

Every non-trivial behaviour lives in a `*_controller.py` module at the
top of `well_viewer/`. The convention is:

- Pure functions (`def foo(app, …)`) that take the `WellViewerApp` and any
  extra args.
- No `WellViewerApp` import in the controller — that would be circular —
  use the dynamic attributes on the object.
- One module per *behaviour domain*: `lineplot_controller.py`, not
  `line_tab_controller.py`. The behaviour outlives the tab name.

The current list (with a one-line role each):

| Module | Role |
|--------|------|
| `load_controller.py` | Open a dataset folder, scan CSVs, populate caches, schedule first redraw. |
| `selection_controller.py` | Plate-selection events; commits a selection change into the redraw pipeline. |
| `lineplot_controller.py` | Line Graphs: redraw the 3-stacked-subplot figure. |
| `barplot_controller.py` + `barplot_renderer.py` | Bar Plots: redraw + bar-draw math (split from controller because it's used by batch export too). |
| `scatter_controller.py` + `scatter_callbacks.py` | Scatter Plot (cells + aggregate). |
| `heatmap_controller.py` + `heatmap_models.py` | Heat Map: layout + redraw. |
| `distribution_controller.py` | Distribution tab: histogram / KDE / violin. |
| `stats_controller.py` | Statistics tab: groupwise tests, KS CDF. |
| `image_table_controller.py` | Image Table grid: per-cell config, distribute, export. |
| `montage_controller.py` | (legacy) Movie Montage popout — folded into Image Table; retained for image-LUT helpers. |
| `smfish_controller.py` + `smfish_worker.py` | smFISH spot detection + the background worker. |
| `review_image_controller.py` + `review_image_renderer.py` | Segmentation tab review-image + Review-CSV jump-to-image. |
| `preview_controller.py` | Image-preview helpers (zip member classification, byte reading). |
| `plot_orchestrator.py` | Default-scope fan-out (line + distribution + heat map). Per-tab scopes (bar / scatter / scatter-agg) have their own entry points that consume scope-specific state. PR #249 unified the dist/heatmap dispatch here so a new default-scope tab is wired in one place. |
| `plot_style.py` | `apply_ax_style` — token-aware axes styling for matplotlib. |
| `figure_export_editor.py` | The floating Export Style sidebar's prefs + apply pipeline + `launch_export_editor`. |
| `grouping_controller.py` | Sample-Definitions group editor logic. |
| `auto_threshold.py` | Otsu-based per-channel default threshold estimator. Delegates the shared helpers (`parse_tp_hours`, `pick_endpoint_timepoints`, `sample_cell_and_bg`) to the top-level `auto_threshold_core.py` so the pipeline and the GUI agree exactly. |
| `fold_change.py` | Fold-change normalization helpers (vs control well/rep-set, vs each member's first timepoint). Consumed by the line / bar plot controllers, their renderers, the batch-export panels, and `export_service.py`. |
| `channel_state_controller.py` | Channel-state machinery extracted from the runtime god-object (PR #249): `recalculate_threshold`, `set_active_channel`, `update_channel_selector`, `refresh_metric_combo_for_channel`. Owns the per-channel `(min, max)` cache on `app._threshold_range_cache` that turns repeat channel toggles from an O(total cells) scan into an O(1) lookup. |
| `zipfile_cache.py` | Process-wide LRU of open `ZipFile` handles, lock-guarded per handle so `read_member_bytes` / `scan_zip_members` share one open file across the thousands of per-member reads the Image Table / heatmap / smFISH-worker paths issue. Invalidated on dataset swap. |

### 5.6 The data layer

The Review pane reads two things off disk:

1. **Per-well CSV files** produced by `process_microscopy.py`. One CSV per
   well, one row per (cell × FOV × timepoint).
2. **Per-well image ZIPs** (`<well>_out.zip`) — masks, top-hat-corrected
   fluorescence, overlays, smFISH-processed channels. Used by Image Table,
   Segmentation, smFISH, and the heatmap.

Plus the sidecar:

3. **`pipeline_info.json`** — schema fields, channel tokens, available
   timepoints, saved selections, persisted gating thresholds, etc.

The relevant modules:

| Module | Job |
|--------|-----|
| `data_loading.py` | CSV parsing, channel detection, threshold-aware aggregation, per-well array helpers. |
| `image_discovery.py` | Scans zips / loose directories for masks, overlays, tophat images. Classifies by suffix + schema. |
| `image_resolver.py` | Filename → kind classifier (`mask` / `overlay` / `fluor_processed` / `smfish`). |
| `viewer_state.py` | `read_pipeline_info` + the `make_schema_extractor(sep, fov_idx, tp_idx)` factory used everywhere the app needs a `(fov, tp)` from a filename. |
| `plate_layout.py` | `PLATE_ROWS`, `PLATE_COLS`, the 48-colour well palette. |
| `selections_model.py` | Saved-selections schema v2: shape, validators, the v1→v2 migration. The on-disk contract lives in `Markdowns/SELECTIONS_MODEL_CONTRACT.md`. |
| `sample_definitions.py` | Read / write the `sample_definitions` block inside `pipeline_info.json`. |
| `batch_models.py` | `BarGroup` + `ReplicateSet` — plain dataclasses used by every plot tab + batch export. |
| `ratio_models.py` | Channel-ratio definitions (`gfp/mcherry`-style virtual channels). |

### 5.7 Persistence

Every "save state into the dataset folder" path lives under
`well_viewer/persistence/`. One module per JSON file:

| File on disk | Module | What it holds |
|--------------|--------|---------------|
| `pipeline_info.json::cell_gating` | `cell_gating.py` | Cell-area + per-channel `fluor_gates` + `thresh_frac_on`. |
| `pipeline_info.json::sample_definitions` | `sample_definitions.py` (top level) | Saved selections (`_selections`). |
| `persistence.json::ratios` | `ratios.py` | User-defined ratio channels. |
| `persistence.json::heatmap_layouts` | `heatmap_layouts.py` | Saved heatmap layouts + cmap/scale state. |
| `persistence.json::line_order` | `line_order.py` | Line plot replicate-set / well draw order. |
| `persistence.json::view_state` | `view_state.py` | Active tab, selected wells, channel/metric, fold-change scopes, per-tab combos, export-style prefs. Saved on dataset switch + app close. |
| `cell_overrides.json` | `cell_overrides.py` | Per-cell `Included` overrides set on the Segmentation tab (kept separate — large + write-heavy). |
| `bar_groups.json` | `bar_groups.py` | User-picked file for bar-plot group state (no auto-save). |

`persistence.json` is a single consolidated viewer-state document managed by
`_doc.py`. On first load it migrates any legacy `ratios.json`,
`heatmap_layouts.json`, or `line_order.json` sidecars into the unified file
and deletes them.

Persistence modules expose `load_from_data_dir(app)` / `save_to_data_dir(app)`
function pairs. `WellViewerApp` delegates to them via thin shims.

**Atomic writes.** Every save goes through
`well_viewer/persistence/_io.atomic_write_json` (or `atomic_write_text` for
the smFISH worker's per-well CSV writer): tmp file + fsync + `os.replace`.
A crash, signal, or full-disk mid-write can no longer leave a truncated
sidecar that the next viewer load reads as empty state and silently
clobbers. Two persistence paths share a debounce flag
(`_<name>_save_pending` on the app) so signal storms (ratio-panel field
edits, heatmap layout drag-and-drop) coalesce into one disk write per
500 ms burst. `cell_overrides.json` v2 stamps each row with the well's
`<well>_out.zip` mtime so a pipeline re-run drops the now-stale overrides
on load instead of re-binding them to unrelated cells.

### 5.8 The Export Style sidebar

Each plot tab pre-allocates a right-side dock via
`make_plot_with_right_dock(parent)`. The dock is hidden by default and a
**Properties** button on the tab's controls row toggles it. When opened, the
dock hosts an `ExportStyleSidebar` (from `views/export_style_sidebar_view.py`)
backed by a single per-app dict (`app._export_style_prefs`). The widget
binds to that dict via `_bind_getter_setter`, so changes flow:

```
Properties widget → app._export_style_prefs
                        ↓
                  apply_export_style_prefs(fig, prefs)
                        ↓
                  canvas.draw_idle()
```

`figure_export_editor.py` owns the prefs dict + the apply pipeline. Every
redraw path ends with a call to
`figure_export_editor.apply_export_style_to_current(app, fig, canvas)` so the
sidebar's toggles (grid on/off, axis label size, log-scale, …) survive a
re-render.

---

## 6. The Analyze side

### 6.1 `analyze_tab.py`

A single-file Qt form that builds the input panel (folder pickers, channel
tokens, top-hat radii, segmentation method, smFISH options, worker count)
plus a live-streaming log panel and a Run / Stop button. The Run path:

1. Validate the form.
2. Call `services.pipeline_service.find_pipeline_script()` to locate
   `process_microscopy.py` (or the frozen-bundle launcher).
3. Call `services.pipeline_service.build_pipeline_args(pipeline, input_dir,
   output_dir, opts)` to assemble argv.
4. `services.pipeline_service.spawn_pipeline(args)` returns a
   `subprocess.Popen` running the pipeline in its own process group / session
   so Stop can signal the entire tree.
5. The Analyze tab streams stdout/stderr into its log view (`tail -f`-style).
6. On completion, the dataset folder is offered to the Review tab.

### 6.2 `process_microscopy.py`

The pipeline. **Self-sufficient by design** — no import from `well_viewer/`,
`widgets/`, or the Qt UI. The pipeline must run in environments that don't
have the GUI installed (CI workers, headless boxes).

That is also why the auto-threshold estimator was inlined into
`process_microscopy.py` (`_estimate_thresholds_standalone`,
`_apply_thresholds_to_pipeline_info`, `_sample_cell_and_bg`,
`_pick_endpoint_timepoints`) — earlier versions imported the equivalent from
`well_viewer.auto_threshold`, which crashed the pass on hosts without the
viewer. The viewer's copy is still used by the GUI's "Auto-threshold"
button on the Cell Gating tab; the pipeline's copy is now the standalone
fallback.

Inputs / outputs / contract:

```
Input dir (one of)
├── A01.zip / A02.zip / … H12.zip          ← per-well zip mode (preferred)
└── flat directory of TIFs                  ← legacy mode

Output dir
├── <well>_out.zip                          ← masks + tophat + overlays per well
├── <prefix>_<well>.csv                     ← per-well measurement CSV
├── pipeline_info.json                      ← schema / channels / timepoints / cell_gating
└── (transient tmp_<well>/ directories deleted on success)
```

### 6.3 `all_well_launcher.py`

PyInstaller entry point. Two responsibilities:

1. Set the matplotlib backend to `QtAgg` before any `pyplot` import.
2. Re-dispatch to `process_microscopy.main()` when invoked with
   `--run-pipeline` as the first argument. The Analyze tab uses that path
   when running inside a frozen `.app` bundle — there's no Python
   interpreter on `sys.executable`, so re-exec'ing the launcher with the
   sentinel argv routes the same Python process into the pipeline.

### 6.4 `services/`

Small dependency-light service modules used by `analyze_tab.py`:

| Module | What |
|--------|------|
| `pipeline_service.py` | `find_pipeline_script` / `build_pipeline_args` / `spawn_pipeline`. |
| `pipeline_runner.py` | Asynchronous subprocess + stdout-streaming wrapper used by Analyze. |
| `input_resolution_service.py` | Validates the input folder shape (zip set vs flat). |

These modules deliberately have no Qt imports beyond what the Analyze tab
itself uses — keeping them potentially reusable for a CLI driver.

---

## 7. The widget library (`widgets/`)

Every widget under `widgets/` is:

- **Standalone.** It only imports from `theme` and Qt (plus `widgets._support`
  for tiny RGB helpers). It does *not* know anything about
  `WellViewerApp` or any tab.
- **Token-styled.** Sizes derive from font metrics; colours come from
  `theme.Colors` / QSS object names. No hardcoded device pixels.
- **DPI-aware.** Geometry is computed from `fontMetrics()`, so the widgets
  scale correctly at 1×, 1.5×, 2×.
- **Singly responsible.** One widget per file. The file may contain a
  helper class or two but never another reusable widget.

Notable members worth knowing about by name:

| Widget | What it is |
|--------|-----------|
| `PlotCard` | The `QFrame` chrome around every matplotlib figure. Provides a custom toolbar (`MplToolbar`), Screen↔Publication mode toggle, and stats chip slot. |
| `WellPlateSelector` | The 8×12 plate selector used by the sidebar and the sample-definitions editor. Supports per-well colour overrides, drag-to-select, drag mime types for the heatmap layout. |
| `NamedPageStack` (in `views/centre_view.py`, not `widgets/` — but morally a widget) | A `QStackedWidget` keyed by page name. The replacement for the legacy `QTabWidget` + custom tab bar. |
| `RailNav` | The left-rail section navigator. |
| `SegmentedControl`, `ChipGroup`, `Stepper`, `StyledSlider`, `ToggleSwitch` | Form controls; each exposes `bindingAdapter()` returning `(getter, setter, change_signal)` for the Export Style sidebar's binding loop. |
| `SavedSelectionsList` | The rich saved-selection list with composition (drag-to-reorder, replicate sub-lists, recolour popovers). |
| `LutSelector`, `GradientStrip`, `ColorPickerPopover` | The colour-map picker + its preview strip + the freeform colour-picker popover. |
| `Popover`, `Drawer`, `Toast`, `EmptyState` | Generic overlay primitives. |
| `TitleBar`, `WindowResizeGrips`, `_window_chrome` | Frameless-window chrome (currently disabled by default — see `_window_chrome.should_use_frameless`). |
| `MplToolbar` | The slim toolbar shown under every matplotlib figure (home / pan / zoom / save + coords readout). |
| `BrandTile`, `IconButton`, `StatusDot`, `KbdHint`, `SelectionChip`, `PillTabBar` | Misc small bits. |

If you find yourself building something that isn't All-Well-specific, write
it as a new `widgets/<x>.py` module. Each widget gets a `__main__` block
that opens a small demo window so you can iterate visually with
`python widgets/foo.py`.

---

## 8. Theming

The app has two complementary theme surfaces. The previous version of this
doc claimed `ui/theme/` was "dormant scaffolding"; that was wrong — both
systems are load-bearing, and they cover different concerns:

1. **`theme.py`** (repo root) — Python-side design tokens for the v2
   redesign. `Colors`, `Typography`, `Spacing`, `Radii`, plus a `qss()`
   builder that produces the full application stylesheet by
   string-templating the tokens into `theme.qss`'s inline template. The
   `widgets/` package and most of the app shell read from
   `theme.Colors.*`; the v2 dark palette is hardcoded here.
2. **`ui/theme/`** — a separate palette + QSS-template system used by
   matplotlib-side plot styling, the Analyze tab, a handful of
   batch-export panels, and the per-theme `.qss` files for an
   in-progress theme switcher (`dark.qss` / `light.qss` / `amber.qss` /
   `beige.qss`). Plot tokens live here (`PLOT_BG`, `TXT_PRI`, `TXT_MUT`,
   `FM_UI`, `WELL_COLOR_1..48`); call `get_color("ACCENT")` for the
   active theme's value. The well palette is sourced from
   `theme.WELL_COLORS_TUPLE` so both systems hand out identical
   per-well colours.

**Why two:** the v2 design (theme.py) was added on top of an existing
palette system (ui/theme). The two stabilised side-by-side rather than
being merged — overlapping conceptual tokens (panel / text-primary /
accent) have *different* hex values in each system, picked
independently for each palette's aesthetic. They are not currently
reconciled.

When you add a colour or size:

- For widgets in `widgets/`, the app shell, or the v2-styled chrome:
  add to `theme.Colors` / `theme.Spacing` / etc.
- For plot styling, the Analyze tab, or anything reading via
  `get_color()`: add to `ui/theme/styles._DARK_THEME` (and the other
  palettes when relevant) and reference it from QSS via
  `${TOKEN_NAME}` in the `.qss` template.
- **Do not** hardcode hex / px values inline.

The publication-export plot surface uses `theme.CPub` and feeds the
target figure's axes (`figure.facecolor`, `axes.facecolor`, etc.) when
a `PlotCard` flips into Publication mode. (PR #249 changed this from a
global `matplotlib.rcParams.update` to per-figure styling so toggling
one PlotCard no longer changes the rcParams seen by later figures.)

**Widgets with per-instance QSS.** Many widgets in `widgets/` set their
own stylesheet at construction (`self.setStyleSheet(self._build_qss())`
or `self.setStyleSheet(self._qss())`) — that's load-bearing for
per-widget object-name scoping, but it freezes the colour tokens at
construction time. Today the global QSS is static and this is fine; if
a runtime theme switcher ever ships (the `ui/theme/theme_manager.py`
scaffold is there for exactly that), widgets need to rebuild their
inline QSS when Qt fires `QEvent.StyleChange`.

`widgets/_support.install_qss_refresh(widget, qss_factory)` is the
opt-in helper: it installs a single event filter that catches
`StyleChange` and calls `widget.setStyleSheet(qss_factory())`. Idempotent.
PlotCard uses it as the canonical example; other widgets should adopt it
when their inline QSS depends on `theme.Colors` values.

---

## 9. Key data flows

### 9.1 Opening a dataset

```
User clicks Open…  or  Ctrl+O  or  --data_dir argv
        │
        ▼
WellViewerApp._load_path(path)        ← runtime_app.py
        │
        ▼
load_controller.load_path(app, path)  ← well_viewer/load_controller.py
        ├── detect in/out layout
        ├── app._read_pipeline_info(out_dir)  ← schema, fluor tokens, smFISH tokens
        ├── app._fov_tp_extractor ← make_schema_extractor(sep, fov_idx, tp_idx)
        └── load_directory(app, dir)
              ├── glob *.csv, validate header, load each into pandas
              ├── populate app._well_paths, app._cache
              ├── _build_tok_to_label, _rebuild_all_timepoints_cache, …
              ├── hydrate persisted state (sample_definitions, ratios,
              │   heatmap_layouts, cell_overrides, line_order, cell_gating)
              ├── _refresh_sidebar_map           ← view side
              ├── _recalculate_threshold        ← invokes _update_channel_selector
              └── app._redraw()                  ← plot_orchestrator.redraw
```

### 9.2 Selecting wells

```
User clicks/drags on the plate widget
        │
        ▼
WellPlateSelector.selectionChanged       ← widget signal
        │
        ▼
WellViewerApp._on_sidebar_plate_selection_changed(ids)
        ├── updates app._selected_wells
        └── app._refresh_sidebar_map()   ← updates colours; no plot redraw yet

User releases mouse / clicks "Select all" / "Select none"
        │
        ▼
selectionDragFinished → WellViewerApp._on_sidebar_plate_drag_finished
                                or
              click handler → app._on_plate_sel_change()
        │
        ▼
selection_controller.on_plate_sel_change(app)
        ├── snapshots prev_sel / last_sel
        └── _refresh_after_selection_change(app)
              ├── dispatches by active tab name:
              │     Bar Plots      → app._redraw_bars()
              │     Scatter Plot   → scatter_redraw_active(app)
              │     Review CSV     → app._refresh_review_csv()
              │     smFISH         → smfish_sync_from_app(app)
              │     Sample Defs    → cell_gating CDF refresh (no plot redraw)
              │     anything else  → app._redraw()
```

That **two-step "selection-changed (paint) → drag-finished (commit)"** split
is important. Drag-paint events fire many times per second; they should not
trigger a redraw on every cell. Click handlers (`Select all`, `Select none`,
row/column header) must explicitly call `_on_plate_sel_change()` to commit.

### 9.3 Switching channels

```
Global ctxbar QComboBox.currentIndexChanged
        │
        ▼
WellViewerApp._on_plot_channel_selected(source=ctxbar)
        └── _set_active_channel(channel)
              ├── update app._active_channel + app._active_val_col
              ├── sync every per-renderer combo
              │     (each tab keeps a hidden _chan_cb_<x> for back-compat)
              ├── app._recalculate_threshold()
              └── app._redraw()        + _redraw_bars() if Bar tab exists

WellViewerApp._update_channel_selector() (called from _recalculate_threshold)
        ├── populates every channel combo from app._fluor_channels + ratios
        ├── picks a sensible default if the current channel disappeared
        └── snaps the global combo's currentIndex to the active label
            (this last step is what prevents the "drop-down doesn't match
            the plot on first draw" bug)
```

### 9.4 Redrawing a plot

```
app._redraw()              ← runtime_app.py
   └── plot_orchestrator.redraw(app, …)
         ├── lineplot_redraw(app, …)              ← always
         ├── if Distribution tab built: redraw_distribution(app)
         ├── if Heat Map tab built:     redraw_heatmap(app)
         └── for each open ExportStyleSidebar: refresh order list

Each per-tab redraw ends with:
   apply_export_style_to_current(app, fig, canvas)
       ↳ figure_export_editor.apply_export_style_prefs(fig, prefs)
       ↳ canvas.draw_idle()

Bar Plots, Scatter Plot, and Scatter Aggregate redraws are *not* invoked
from `plot_orchestrator.redraw` — they have their own entry points
(`app._redraw_bars()`, `scatter_redraw_active(app)`) called from the
selection / channel / tab-change paths.
```

### 9.5 Applying fold-change normalization

Two independent axes, both optional, both stacking. State lives on the
`WellViewerApp` so the Bar Plots and Line Graphs tabs share it; the
batch-export panels keep their own panel-local mirror so a batch job
isn't tied to whatever the plot tab has set.

The math has one important invariant: the **numerator** (each bar's /
curve's value) and the **denominator** (control mean and t0 baseline)
use the **same statistic**. For a rep-set member that's
"mean-of-per-well-means" (`_compute_rep_stats`), or per-FOV pool when
Aggregate-FOVs is on (`_compute_rep_per_fov_stats`); for a single-well
member it's `_aggregate_well`. Mixing statistics gave biased ratios in
the original implementation. The helpers in `fold_change.py` enforce
this — see `member_mean_series` for the dispatch.

Stacking when both axes are active is **ΔΔCt-style**:
```
   Y(t) = (X(t) / C(t)) / (X(0) / C(0))
```
because `vs t0` is applied to the post-control values. This is not the
same as `(X(t)/X(0)) / (C(t)/C(0))` in general. Documented on
`normalize_pts`.

Error propagation: each fold-change denominator (control mean, t0
baseline) is divided through with its own spread, and the resulting
relative error combines in quadrature:

```
   (σ_Y / Y)² = (σ_X / X)² + (σ_C / C)² + (σ_B / B)²
```

`scale_bar_value` and `normalize_pts` accept the denominator spreads
via `control_spread` / `t0_spread` / `control_stats`. Callers that
don't have a meaningful denominator uncertainty can omit them; that
recovers the legacy "treat denominator as exact" `spread / factor`
behaviour and is the backwards-compatible default.

```
                            app._fc_vs_control_on   ─┐
User → Control combo  ─→    app._fc_control_label   ─┼─→ fold_change.fold_change_state(app)
                            app._fc_vs_t0_on        ─┘
User → Baseline combo ─→ (sets _fc_vs_t0_on)

tabs/fold_change_controls.set_fold_change_state(app, *, …, initiating_scope)
        │   mirrors the shape of runtime_app._set_active_channel:
        │   updates state → _sync_widgets_to_state → _redraw_bars + _redraw
        ▼
Line tab — lineplot_controller.redraw_line_plots(…) →
            collect_line_series(app, …) → list[LineSeries]
   1. Single source of truth, mirrors the bar plot's
      ``collect_bar_items``. Each member becomes a ``LineSeries``
      with a list of ``LinePoint``s (full AggPoint shape so the
      renderer and CSV writers consume the same record).
   2. fold_change.member_stats_series(app, fc_ctrl_lbl, …) →
      {t: (control_mean, control_spread)} — mean-of-per-well-means
      for rep-set controls (per-FOV pool when Aggregate-FOVs is on),
      single-well agg for well controls. Spreads thread through
      normalize_pts via quadrature for proper error propagation.
   3. normalize_pts(pts, control_stats=…, use_t0=…,
      miss_sink=fc_misses) is called inside collect_line_series.
      Drag-order from ``_line_order_rsets`` / ``_line_order_wells``
      is applied before the per-trace work.
   4. The renderer just iterates the resulting LineSeries and calls
      ax.plot. The batch line CSV / figure go through
      ``batch_export._line_series_runner.collect_line_series_for_group``
      — same data shape, pool-of-cells stat for the batch
      numerator (matches the prior batch behaviour).
   5. After redraw, app._set_status(…) surfaces a one-line warning
      naming any timepoints where the control had no sample.

Bar tab — barplot_controller.collect_bar_items(app, target_t,
                                                miss_sink=fc_misses)
          → list[BarItem]  (single source of truth)
   1. fold_change.control_mean_at_for_bar(app, label, target_t, …)
      → single float (or None). Uses the same stat as the bar's
      numerator (mean-of-per-well-means for rep-set, per-FOV pool
      when Aggregate-FOVs is on).
   2. For each bar's (mean, spread): scale_bar_value(…).
   3. t0 baseline = member_first_tp_value(app, member_label, …) for
      rep-sets (same stat) or first_tp_value(pts) for per-well bars.
   4. If vs-control was requested but the resolver returned None,
      every bar is forced to NaN (no silent fall-back to raw values)
      and the target_t is recorded in miss_sink for the status
      warning surfaced by barplot_renderer.draw_grouped_bar_mode.

Bar tab violin / beeswarm — runtime_app._draw_per_cell_bar_mode →
fold_change.build_cell_scaling(…) → {well: factor}, where each cell
value is divided by factor before plotting. factor = control_mean ×
t0_mean (per-well). NaN factor → that well's column rendered as a
placeholder. Title gains the suffix when scaling is active.

Both renderers append a "(fold change vs <ctrl>, vs t0)" suffix to the
mean axis title / ylabel via fold_change.fold_change_suffix.

Float-tolerance: _match_control_mean uses relative tolerance
abs(a-b) < 1e-3 · max(1, |a|, |b|) — the bar tp combo formats with
:.4g so a fractional tp like 2/3 ≈ 0.6667 parses back ~3e-5 off the
original float, which the prior absolute 1e-6 tolerance missed.

CSV output (additive in both line and bar paths):
   On-tab:
     export_service.export_plot_data        (line)
     export_service.export_bar_plot_data    (bar)
   Batch:
     batch_export/base_panel._run_group     (line)
     batch_export/bar_panel._run_batch      (bar)

   The mean_<ch>_<metric> / err_<band>_<ch>_<metric> columns always
   carry the RAW values. When fold-change is active, four columns are
   appended:
       fold_change_mean             — normalized mean
       fold_change_<sd|sem>         — normalized spread
       fold_change_mode             — "control" | "t0" | "control+t0"
       fold_change_control          — the chosen well / rep-set name

   The bar CSV is implemented via two calls to collect_bar_items
   (or collect_bar_items_for_group): one with FC_STATE_OFF for the
   raw columns and one with the active state for the fold-change
   columns. The aggregation helpers are cached so the second call
   is cheap. Pre-refactor the bar CSV used to overwrite the raw mean
   column with the normalized value when fold-change was active —
   that was inconsistent with the line CSV's additive schema and
   has been corrected.

Cross-tab widget sync:
   Each tab installs its own QComboBox instances via
   tabs/fold_change_controls.install_fold_change_controls(scope=…).
   The combo handlers funnel every state mutation through
   set_fold_change_state, which calls _sync_widgets_to_state to
   mirror the new state into the other tab's widget set (with
   signals blocked). The smart-repopulation check skips the
   clear-and-readd cycle when the combo's popup is currently
   visible, so user interaction is never yanked out of focus.

   Scope registry. Each tab that owns a fold-change combo set
   declares itself via a FoldChangeScope (name, ctrl combo attr,
   baseline combo attr, redraw method, tab name). The two scopes
   today are bar and line; adding a third (e.g. distribution /
   scatter) is a single register_fold_change_scope call —
   _sync_widgets_to_state and set_fold_change_state iterate the
   registry rather than hard-coding scope names. The registry lives
   in the pure-logic ``well_viewer.fold_change_scopes`` module so
   the helpers can be unit-tested without Qt.

   Redraw deferral. State mutations route through
   ``redraw_scopes_or_defer(app)``: the currently-visible scope's
   redraw method runs immediately, every other scope is marked
   dirty. ``_on_notebook_current_changed`` calls
   ``flush_dirty_scopes(app)``, which redraws any dirty scope whose
   tab just became visible. ``WellViewerApp._set_active_channel``
   uses the same chokepoint, so the two former 'redraw both
   eagerly' paths now share one consistent visibility-aware
   policy. The dirty set is stored on the app under
   ``_fc_dirty_scopes`` (auto-created on first use).

When a rep-set name collides with a loaded well token, the well's
combo entry is suffixed with " (well)"; resolve_control_wells
accepts both bare and suffixed forms, and set_fold_change_state
strips the suffix before storage so the underlying state stays a
bare token. This is the only collision-resolution mechanism — the
Sample Definitions UI does not currently prevent the collision at
input time.

### 9.6 Running the pipeline

```
Analyze tab Run button
        │
        ▼
services.pipeline_service.find_pipeline_script()
services.pipeline_service.build_pipeline_args(…)
services.pipeline_service.spawn_pipeline(args) → subprocess.Popen
        │
        ▼ stdout stream → Analyze tab log view
process_microscopy.main()
        ├── per-well loop (ProcessPoolExecutor)
        │     ├── extract zip → tmp dir
        │     ├── segment + quantify
        │     ├── write per-well CSV + image outputs
        │     └── compress to <well>_out.zip
        ├── write pipeline_info.json
        └── _estimate_thresholds_standalone(output_dir, …)
              └── _apply_thresholds_to_pipeline_info(output_dir, thresholds, log)
                    ↳ pipeline_info.json["cell_gating"]["thresh_frac_on"]
        │
        ▼
Process exits. Analyze tab offers the dataset to Review.
```

---

## 10. Cross-cutting concerns

### 10.1 Logging

- Every module uses
  `logging.getLogger("well_viewer")` (the viewer) or
  `logging.getLogger("well_viewer.auto_threshold")` (per-domain children).
- `all_well._attach_log_ring_buffer` captures every record into a ring
  buffer that the Help drawer's log tab and the Analyze tab's live log
  view both read from.

### 10.2 Status signal

`well_viewer/status_signal.py` is a tiny pub-sub for the bottom status bar's
`StatusDot`. Long-running operations call
`with status_signal.warn_scope(): …` so the dot turns amber while they run,
and call `status_signal.signal_failed()` on exceptions so it turns red and
auto-clears after `DANGER_HOLD_SECS`.

### 10.3 Debug flags

`well_viewer/debug_flags.py` exposes module-level booleans
(`REVIEW_TAB_DEBUG`, `REVIEW_BAR_DEBUG`, `REVIEW_SCATTER_DEBUG`,
`ANALYZE_TAB_DEBUG`, `MOVIE_MONTAGE_DEBUG`, `REVIEW_IMAGE_CHSW_DEBUG`).
`all_well.main()` wires the top-of-file constants in `all_well.py` into
these flags so toggling them is a one-line edit. Each flag gates `logger.debug`
calls inside its domain; off by default.

### 10.4 Build / packaging

- **Source run:** `python all_well.py [--data_dir …]`.
- **macOS .app:** `_Docs/_Installation/build_all_well.sh` (mamba env +
  PyInstaller), spec at `_Docs/_Installation/all_well.spec`.
- **Pipeline-only run:** `python process_microscopy.py --input_dir … --output_dir …`.
  No GUI deps required.

---

## 11. Recipes

### 11.1 Add a new plotting tab

1. Create `well_viewer/tabs/<name>_tab_view.py` with a
   `build_<name>_tab(app, parent)` function. Model it on
   `line_graphs_tab_view.py`. The minimum:
   - `make_plot_with_right_dock(parent)` for the export dock.
   - A controls row with `btn_secondary("Properties", …,
     icon="sliders-horizontal")` as the rightmost widget.
   - A `PlotCard` that hosts your figure(s).
   - Stash `app._<name>_fig`, `app._<name>_canvas`,
     `app._<name>_export_dock`, `app._<name>_card` for the rest of the
     code to find.
2. Add a controller `well_viewer/<name>_controller.py` with a `redraw(app)`
   pure function. Don't import `WellViewerApp`; read state off the `app`
   argument.
3. Wire the controller's `redraw` into the redraw pipeline. Either:
   - Add a branch to `plot_orchestrator.redraw` (if it should redraw on every
     selection change); or
   - Add an `app._redraw_<name>()` shim on `WellViewerApp` and call it from
     the relevant tab-change / selection-change paths in
     `selection_controller._refresh_after_selection_change`.
4. Register the tab in `views/centre_view.py`'s `groups` list (it sits
   under "Analysis" / "Images" / "Data" sections) and create a
   `_build_<name>()` closure that calls your `build_<name>_tab`.
5. Add an icon to `_SECTION_ICONS` in `runtime_app.py` if you want it to
   appear in the rail nav.
6. End your redraw with `apply_export_style_to_current(app, fig, canvas)`
   so the Properties sidebar's toggles apply.

### 11.2 Add a sidebar widget for a specific tab

1. Create `well_viewer/views/<name>_view.py` with a
   `build_<name>(app, parent)` function.
2. In `runtime_app._build_ui`, allocate a `QWidget` for it and hide it by
   default:
   ```python
   self._sidebar_<name>_frame = QWidget()
   QVBoxLayout(self._sidebar_<name>_frame).setContentsMargins(0, 0, 0, 0)
   sidebar_layout.addWidget(self._sidebar_<name>_frame, 1)
   self._sidebar_<name>_frame.hide()
   ```
3. In `_on_tab_change`, show your frame on the relevant tab and hide every
   other sibling frame.
4. Build the frame body lazily — usually called from the tab's
   `_build_<tab>()` closure in `centre_view.py`.

### 11.3 Persist some state to disk

1. Create `well_viewer/persistence/<name>.py` with a `load_from_data_dir(app)`
   and `save_to_data_dir(app)` pair.
2. The file lives at `<data_dir>/<name>.json` (or as a key under
   `pipeline_info.json` if it's pipeline-coupled).
3. Add `app._<name>_load_from_data_dir = <name>.load_from_data_dir`-style
   bindings in `WellViewerApp.__init__` if you want the shim style, or
   call the module functions directly.
4. Hydrate at load time (`load_controller.load_directory` already calls
   each persistence module's loader at the end). Persist on user-driven
   edits, never on every signal — debounce with a `QTimer.singleShot(0, …)`
   if many small edits arrive together.

### 11.4 Add a new channel-ratio metric or aggregation

1. The ratio model is in `ratio_models.py` (`RatioMetric` dataclass) and
   the persistence layer in `persistence/ratios.py`.
2. Aggregations are configured in `data_loading.aggregate_with_threshold_df`
   and `_aggregate_arrays`. Add the new metric as a column or in the
   AggPoint tuple, then teach `bar_metric_row` / `line_metric_row` in
   `export_service.py` how to format it for CSV export.

### 11.5 Hook a new keyboard shortcut

Add a `QShortcut(QKeySequence("Ctrl+X"), self, activated=self._handler)`
line in `AllWellApp._install_shortcuts` (`all_well.py`). The help drawer's
shortcut list is in `_toggle_help_drawer` in the same file — keep it
in sync.

---

## 12. Debugging recipes

### 12.1 "Where is this widget defined?"

The Review pane is built bottom-up; every widget is stored on
`WellViewerApp` as `_<noun>`. Grep first for the attribute name:

```bash
grep -rn '_line_fig\b' well_viewer/ widgets/
```

That returns both the producer (a `tabs/*_tab_view.py`) and every consumer.
For widgets in the rail nav, search `centre_view.py`. For controls in the
title bar, search `all_well.py`.

### 12.2 "The plot is showing the wrong data"

In order of probability:

1. **Stale `_active_channel`.** Check `_update_channel_selector` ran with
   the current dataset's channel list and that the global ctxbar combo's
   current text matches `_active_channel.upper()`.
2. **A controller didn't get the redraw entry-point call.** Check the
   tab-name branches in
   `selection_controller._refresh_after_selection_change`.
3. **The selection was painted but not committed.** Make sure the path that
   changed `_selected_wells` also called `app._on_plate_sel_change()` (the
   Select all / Select none buttons used to skip this).

### 12.3 "The pipeline ran but Review can't see the channels"

`process_microscopy.py` writes `pipeline_info.json` with `fluor_tokens`,
`schema`, `separator`, and `available_timepoints`. The viewer reads those
in `viewer_state.read_pipeline_info`. If the file is missing, the viewer
falls back to detecting channels from a sample CSV's column names
(`data_loading.detect_fluor_channels`). Check both:

```bash
cat <data>/pipeline_info.json | python -m json.tool | grep -A1 fluor_tokens
head -1 <data>/<one>_measurements.csv
```

### 12.4 "Auto-threshold reports 'timepoint unknown'"

`well_viewer/preview_controller.classify_member` parses `(fov, tp)` from
each image filename. It prefers the schema-derived fields from
`pipeline_info.json` (`pipeline_fields_extractor`) and only falls back to
the legacy 5-field regex when those are absent. If you see "unknown", the
pipeline_info schema is either missing or doesn't include `fov` / `tp`
fields. Make sure `--filename_schema` was correct at pipeline-run time.

### 12.5 "Tab body doesn't appear when I click the rail"

Centre pages build lazily. The first time you click a page, its builder
runs from `centre_view._on_tab_change`. If the builder raises an exception,
the log captures it — open the help drawer's log tab or run
`python all_well.py` from a terminal and watch stderr. The most common
failure is a missing widget attribute on `WellViewerApp` because two
builders touch a shared attribute in the wrong order. Use the
`_centre_lazy_only_titles` set in `centre_view.py` to control which
builders never run from the background drain.

### 12.6 "The figure's Properties panel doesn't stick"

Every figure-styling toggle writes into the shared dict
`app._export_style_prefs` (see `figure_export_editor.py`). Every controller
ends its redraw with `apply_export_style_to_current(app, fig, canvas)`.
If a new redraw entry point you added is "losing" the user's toggles, it's
missing that call at the end.

### 12.7 "PyInstaller .app launches but freezes / can't find a module"

Three places to check:

1. The spec file `_Docs/_Installation/all_well.spec` has explicit
   `hiddenimports` for every non-trivial dependency (numpy internals,
   skimage submodules, stardist, csbdeep, …). Add yours there.
2. The launcher `all_well_launcher.py` sets `matplotlib.use("QtAgg")`
   before `pyplot` import — if matplotlib isn't picking up Qt, this is
   why.
3. The build script `_Docs/_Installation/build_all_well.sh` enumerates
   every required file. Missing inputs fail loudly.

---

## 13. The `Markdowns/` library

The `Markdowns/` folder is intentionally small — the long tail of port-time
plans, status updates, phase write-ups, gap analyses, and migration plans
was retired once the port finished and is preserved in git history rather
than as live files. What remains:

| File | What it's for |
|------|---------------|
| `ARCHITECTURE.md` | This document — the developer-oriented architectural overview. |
| `README_WellViewer.md` | User-facing README — install, run, troubleshoot. |

The on-disk shape of `pipeline_info.json::sample_definitions` (the saved
selections schema) is described in the `well_viewer/selections_model.py`
module docstring; that module is the live source of truth for the
contract.

`design/` (sibling of `Markdowns/`) holds the **non-Markdown** design
artifacts — the HTML mockups (`mockup-decoded.html`,
`All-Well Redesign v2 _standalone_.html`), screenshots, and decoded mockup
assets — for visual reference only.

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| **Pane** | One of the two top-level pages: Review or Analyze. |
| **Tab** | A centre-stack page inside the Review pane (Plotting, Statistics, …). |
| **Sub-tab** | A leaf page inside a parent tab (e.g. Plotting → Line Graphs). |
| **Sidebar** | The left rail in the Review pane. Hosts the rail nav + the well picker + per-tab control panels. |
| **Ctxbar** | The horizontal contextual control row above each plot card. Hosts channel / metric / timepoint combos + action buttons. |
| **PlotCard** | The framed container around each matplotlib figure. Provides the screen↔publication toggle, the custom toolbar, and the stats chip slot. |
| **Properties sidebar / Export Style sidebar** | The right-side dock that slides out when the user clicks the Properties button on a plot card. Backed by `app._export_style_prefs`. |
| **Selection** | A named, persisted subset of wells. Lives in `app._selections` (schema v2). Aliased as "Sample Definition" in the UI. |
| **Replicate set** | A group of wells treated as replicates for a single condition. Members of a `BarGroup`. |
| **`pipeline_info.json`** | The sidecar file written by `process_microscopy.py` next to the per-well CSVs. Holds schema, channel tokens, available timepoints, persisted selections, gating thresholds. |
| **Well token** | Two-letter / two-digit well identifier (`A01` … `H12`). Always uppercase, always zero-padded. |
| **fov, tp** | Field-of-view and timepoint extracted from a filename via the schema-aware extractor in `viewer_state.make_schema_extractor`. |

---

## 15. Conventions and gotchas

- **Never hardcode colours.** Use `theme.Colors.*` or QSS object names.
- **Never block the UI thread.** Heavy operations spawn workers (see
  `well_viewer/smfish_worker.py` and the `services.pipeline_runner`
  pattern). Streaming progress messages route through `logging` →
  `status_signal` → the bottom `StatusDot`.
- **Plate selections are well IDs (strings), not (row, col) tuples.**
  `_selected_wells: set[str]`. Convert to / from tuples at the
  edge with `data_loading.parse_well_token`.
- **Selections survive a tab switch.** Whenever you read or write
  `_selected_wells`, you're touching app-wide state — clobbering it in a
  tab-local handler will leak across tabs.
- **Don't call controllers' `redraw` directly from a widget signal.**
  Route through the shim on `WellViewerApp`. The shim knows how to
  defer / batch / no-op when the relevant tab hasn't been built yet.
- **Lazy tab builds are real.** Don't assume `app._heatmap_fig` exists; do
  `if hasattr(app, "_heatmap_canvas"): …`.
- **Pipeline runs in a separate process.** Don't try to share Python
  objects between Analyze and the running pipeline; everything passes
  through argv → stdout text streaming → the dataset folder.
- **`Markdowns/` is documentation, not code.** It is kept intentionally
  small post-port (this file, the user README, the selections-model
  contract, and the icons readme). The port-time plans and status updates
  were removed once the port shipped; they remain in git history if
  you ever need them.

If you read all the way to here and the structure still doesn't make sense,
the right next move is to open `well_viewer/runtime_app.py` and scroll
through `_build_ui` (around line 934) — that's where every widget tree
hanging off `WellViewerApp` gets stitched together, and every name you'll
need to grep for is in plain sight.
