# All-Well Developer/AI Readme

This guide is intended for future contributors (including AI coding sessions) who need to quickly understand:

1. **How to install dependencies and run the app/scripts**
2. **Where functionality lives now** (package-first architecture)
3. **Which files to edit for specific behavior changes**

---

## 1) Environment setup and dependency installation

## Prerequisites
- Python 3.10+ (3.11 works well in development)
- `pip` and virtualenv support
- On macOS, `python-tk`/Tk support for Tkinter UI

### Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

### Install runtime dependencies
```bash
pip install -r requirements.txt
```

### Important optional/analysis dependencies
The **Analyze** pipeline (`process_microscopy_v2.py`) requires scientific and ML packages, notably:
- `tifffile`
- `scipy`
- `scikit-image`
- `csbdeep`
- `stardist`
- TensorFlow runtime suitable for your platform (e.g. `tensorflow` and optionally `tensorflow-metal` on macOS)

If `csbdeep`/`stardist` are missing, the pipeline now fails fast with a clear runtime error before worker pool startup.

### Quick dependency smoke checks
```bash
python -c "import tkinter; print('tk ok')"
python -c "import tifffile, scipy, skimage; print('image stack ok')"
python -c "import csbdeep, stardist; print('stardist deps ok')"
```

---

## 2) How to run

### Main app (Review + Analyze tabs)
```bash
python all_well.py
```

### Review-only runtime
```bash
python -m well_viewer.runtime_app
```

### Analyze pipeline directly
```bash
python process_microscopy_v2.py --help
```

---

## 3) Current architecture (package-first)

The project no longer uses `well_viewer3.py` as a runtime shim. Runtime ownership is now package-first under `well_viewer/*`.

## Composition roots
- `all_well.py`
  - Desktop composition root. Builds notebook tabs and embeds:
    - `WellViewerApp` (Review)
    - `AnalyzeTab` (Analyze)
- `well_viewer/runtime_app.py`
  - Canonical Review runtime class (`WellViewerApp`) and most shared UI/runtime constants.
- `process_microscopy_v2.py`
  - Analyze pipeline CLI/engine for well image processing, segmentation, CSV outputs, and zip outputs.

## Well viewer package structure

**Root-level modules:**
- `well_viewer/app.py` — Package-facing wrapper for `WellViewerApp` construction.
- `well_viewer/__init__.py` — Re-exports package API (`WellViewerApp`).
- `well_viewer/runtime_app.py` — `WellViewerApp` main class, `CellGatingTab`, and shared design-token constants (`BG_*`, `TXT_*`, `ACCENT`, `PLOT_BG`, etc.).
- `well_viewer/batch_models.py` — `BarGroup`, `ReplicateSet` data models.
- `well_viewer/export_service.py` — CSV/figure/montage export helpers.
- `well_viewer/batch_export_dialog.py` — Batch export dialog UI classes.
- `well_viewer/ui_helpers.py` — Shared UI utilities (`btn_card`, `btn_primary`, `tok_at_event`, etc.).
- `well_viewer/viewer_state.py` — Shared state helpers (`extract_well_token`, `make_schema_extractor`, etc.).

**`well_viewer/views/` — UI builder modules (one `build_*(app, parent)` function each):**
- `centre_view.py` — Thin orchestrator; creates each notebook tab frame and delegates to `tabs/` builders or `app._build_*` methods.
- `preview_panel_view.py` — Preview panel controls, montage canvas, LUT/top-hat controls.
- `status_view.py` — Bottom status/log strip.
- `grouping_view.py` — Replicate/group card-list UI.
- `stats_view.py` — Statistics tab UI (results panel + group editor).
- `preview_view.py` — Preview picker UI (FOV selector panel).

**`well_viewer/tabs/` — One builder per plot/workflow tab:**

| File | Tab | Key attributes created |
|------|-----|----------------------|
| `line_graphs_tab_view.py` | Line Graphs | `_line_fig`, `_line_canvas`, `_line_ax_mean/frac/cdf` |
| `bar_plots_tab_view.py` | Bar Plots | `_bar_fig`, `_bar_canvas`, `_ax_bar_mean/frac` |
| `scatter_cells_tab_view.py` | Scatter Plot: Cells | `_scatter_fig`, `_scatter_canvas`, `_ax_scatter` |
| `scatter_agg_tab_view.py` | Scatter Plot: Aggregate | `_scatter_agg_fig`, `_scatter_agg_canvas`, `_ax_scatter_agg` |
| `batch_export_tab_view.py` | Batch Export | *(buttons only, no figure)* |

Each exposes `build_{name}_tab(app, parent: tk.Frame) -> None`.  
`tabs/__init__.py` provides shared helpers `_make_action_button` and `_make_secondary_button`.

**Controllers (flat under `well_viewer/`):**
- `lineplot_controller.py` — Line/CDF/fraction redraw helpers.
- `barplot_controller.py` — Bar plotting data prep/order/rendering helpers.
- `scatter_controller.py` — Scatter plot rendering helpers.
- `montage_controller.py` — Montage zoom/resize/tophat-done helpers.
- `preview_controller.py` — Preview file discovery/classification and zip/image read helpers.
- `grouping_controller.py` — Group/replicate assignment logic.
- `selection_controller.py` — Well selection + drag behavior.
- `load_controller.py` — Data loading orchestration and token map rebuild.
- `stats_controller.py` — Statistics compute helpers.
- `plot_orchestrator.py` — Redraw orchestration and save helper dispatch.

**Callbacks:**
- `preview_callbacks.py` — Preview/montage refresh and draw callbacks.
- `scatter_callbacks.py` — Scatter plot event handlers.

---

## 4) Where to edit for common feature requests

### A) "Change app colors/theme/fonts"
- Start in `well_viewer/runtime_app.py` design tokens near the top:
  - `BG_*`, `TXT_*`, `ACCENT`, `BORDER`, `WELL_COLORS`, semantic aliases.
- Most extracted views import these constants, so token edits propagate globally.
- **Do not modify well picker colors unless explicitly requested** (`WELL_COLORS`, `CLR_AVAIL_WELL`, `CLR_AVAIL_HOVER`).

### B) "Preview tab loads wrong images / top-hat behavior"
- `well_viewer/runtime_app.py` and `well_viewer/preview_callbacks.py`
  - `_refresh_preview_montage` / `refresh_preview_montage`:
    - choose raw vs pre-filtered top-hat refs
    - build display arrays
- `well_viewer/preview_controller.py`
  - member classification logic (`fluor`, `tophat_fluor`, `overlay`, `mask`)
  - zip scanning and image reference extraction
- `well_viewer/views/preview_panel_view.py`
  - default UI control states (checkboxes, LUT entries, top-hat controls)

### C) "Plot rendering issues (line/bar/cdf)"
- High-level orchestration in `well_viewer/plot_orchestrator.py`
- Line plots in `well_viewer/lineplot_controller.py`
- Bar plots in `well_viewer/barplot_controller.py`
- Tab control-bar layout in `well_viewer/tabs/` (see G below)

### D) "Well/group selection and sample definitions"
- Sidebar and map interactions:
  - `well_viewer/selection_controller.py`
  - `well_viewer/grouping_controller.py`
- Group UI rendering:
  - `well_viewer/views/grouping_view.py`
  - relevant sections of `well_viewer/views/centre_view.py`

### G) "Tab layout / UI controls (selectors, buttons, toggles)"
- Each plot tab has its own builder in `well_viewer/tabs/`:
  - Line Graphs → `line_graphs_tab_view.py`
  - Bar Plots → `bar_plots_tab_view.py`
  - Scatter Plot: Cells → `scatter_cells_tab_view.py`
  - Scatter Plot: Aggregate → `scatter_agg_tab_view.py`
  - Batch Export → `batch_export_tab_view.py`
- All tab builders follow the same layout pattern:
  `ctrl_bar` (controls) → `figure + canvas + toolbar` → optional `axis_controls`
- Shared button helpers (`_make_action_button`, `_make_secondary_button`) live in `well_viewer/tabs/__init__.py`.

### E) "Analyze pipeline crashes / worker pool failures"
- Start in `process_microscopy_v2.py`:
  - dependency preflight (`_ensure_stardist_runtime_deps`)
  - worker initializer (`_worker_init`)
  - pool dispatchers (`run_pipeline_on_wells`, `process_well_zips`)
- If failures mention missing modules in workers, ensure the dependency preflight and env setup are aligned.

### F) "Packaging/build app bundle"
- `all_well.spec`
  - PyInstaller sibling scripts, data inclusion, hiddenimports
- `build_all_well.sh`
  - build preflight checks and execution
- `all_well_launcher.py`
  - bundled app entry/bootstrap behavior

---

## 5) Suggested workflow for future edits

1. Reproduce with smallest command (`python all_well.py` or target script).
2. Locate owner module via section 4 above.
3. Apply minimal change in owner module first (avoid duplicating logic).
4. Run checks:
   ```bash
   python -m py_compile \
     well_viewer/runtime_app.py \
     well_viewer/views/centre_view.py \
     well_viewer/views/preview_panel_view.py \
     well_viewer/preview_callbacks.py \
     process_microscopy_v2.py
   python scripts/run_refactor_checks.py
   ```
5. If UI changed, manually validate affected tabs/controls in-app.

---

## 6) Known architectural constraints

- Tkinter/Matplotlib UI code is stateful and event-driven; many callbacks mutate app instance fields.
- Some logic remains intentionally duplicated between `runtime_app.py` methods and extracted callback modules for compatibility while migration stabilizes.
- Analyze runtime depends on heavyweight scientific stack; environment mismatch is a common failure mode.

