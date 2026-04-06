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
- `well_viewer/app.py`
  - Package-facing wrapper for `WellViewerApp` construction.
- `well_viewer/__init__.py`
  - Re-exports package API (`WellViewerApp`).
- `well_viewer/views/centre_view.py`
  - Builds center notebook tabs and plot canvases (Line, Bar, Preview, Stats, Sample Definitions).
- `well_viewer/views/preview_panel_view.py`
  - Builds Preview panel controls, montage canvas, LUT controls, top-hat controls.
- `well_viewer/views/status_view.py`
  - Builds bottom/status/log strip.
- `well_viewer/preview_callbacks.py`
  - Preview/montage refresh and draw callbacks.
- `well_viewer/preview_controller.py`
  - Preview file discovery/classification and zip/image read helpers.
- `well_viewer/montage_controller.py`
  - Montage zoom/resize/tophat-done interaction helpers.
- `well_viewer/plot_orchestrator.py`
  - Line/bar redraw orchestration and save helper dispatch.
- `well_viewer/barplot_controller.py`
  - Bar plotting data prep/order/serialization/rendering helpers.
- `well_viewer/lineplot_controller.py`
  - Line/CDF/fraction redraw helpers.
- `well_viewer/grouping_controller.py`, `well_viewer/grouping_view.py`
  - Group/replicate assignment logic and group UI builders.
- `well_viewer/selection_controller.py`
  - Well selection + drag behavior.
- `well_viewer/load_controller.py`
  - Data loading orchestration and token map rebuild.
- `well_viewer/export_service.py`
  - Export/saving helpers (CSV/figures/montage export).
- `well_viewer/stats_controller.py`, `well_viewer/stats_view.py`
  - Statistics compute and statistics-tab UI.
- `well_viewer/batch_export*.py`, `well_viewer/batch_models.py`
  - Batch export dialogs/models/helpers.

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
- Centre tab wiring in `well_viewer/views/centre_view.py`

### D) "Well/group selection and sample definitions"
- Sidebar and map interactions:
  - `well_viewer/selection_controller.py`
  - `well_viewer/grouping_controller.py`
- Group UI rendering:
  - `well_viewer/grouping_view.py`
  - relevant sections of `well_viewer/views/centre_view.py`

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
   python -m py_compile well_viewer/runtime_app.py well_viewer/views/centre_view.py well_viewer/views/preview_panel_view.py well_viewer/preview_callbacks.py process_microscopy_v2.py
   python scripts/run_refactor_checks.py
   ```
5. If UI changed, manually validate affected tabs/controls in-app.

---

## 6) Known architectural constraints

- Tkinter/Matplotlib UI code is stateful and event-driven; many callbacks mutate app instance fields.
- Some logic remains intentionally duplicated between `runtime_app.py` methods and extracted callback modules for compatibility while migration stabilizes.
- Analyze runtime depends on heavyweight scientific stack; environment mismatch is a common failure mode.

