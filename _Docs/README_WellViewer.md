# All-Well — Multi-Channel Fluorescence Microscopy Pipeline & Viewer

All-Well is a PySide6 (Qt) desktop application for fluorescence microscopy
quantification. It combines a StarDist-based nuclear segmentation pipeline
with an interactive multi-channel data viewer in a single window.

## Top-level layout

Two top-level tabs, composed by `all_well.py` (`AllWellApp`, a `QMainWindow`):

- **Review** — `WellViewerApp` from the `well_viewer/` package; load and
  explore per-well CSV output produced by the pipeline.
- **Analyze** — `AnalyzeTab` from `analyze_tab.py`; run the segmentation
  pipeline on a folder of microscopy images.

A header bar exposes a **Theme** selector (Dark / Light). Themes are applied
via `QApplication.setStyleSheet(build_stylesheet(name))` driven by
`ui/theme/`.

## Running from source

Prerequisites:
- Miniforge (Apple Silicon build for M-series Macs):
  - `curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh`
  - `bash Miniforge3-MacOSX-arm64.sh`
- Xcode Command Line Tools: `xcode-select --install`

Create the environment:

```
mamba create -n allwell python=3.10.14 setuptools=69.5.1 \
    "numpy>=1.24,<1.25" scipy scikit-image matplotlib pillow imageio h5py \
    -c conda-forge -y
mamba activate allwell
```

Verify `pkg_resources` works before proceeding:

```
python -c "import pkg_resources; print('OK')"
```

Install pip-only dependencies (always use `--no-build-isolation`):

```
pip install --no-build-isolation -r _Docs/requirements.txt
```

Verify TensorFlow sees the Metal GPU (Apple Silicon):

```
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
# Expected: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
```

Run the app:

```
mamba activate allwell
python all_well.py
python all_well.py --data_dir /path/to/results   # preload a dataset
```

## Pre-built macOS app

If you received `AllWell.app` (or `AllWell-mac.zip`), no Python installation
is needed — the bundle ships its own Python and dependencies.

1. Unzip and move `AllWell.app` to `/Applications` (optional).
2. First-launch Gatekeeper fix — macOS may report the app as "damaged"
   because it is not from the App Store:
   ```
   xattr -cr /Applications/AllWell.app
   codesign --force --deep --sign - /Applications/AllWell.app
   ```
3. Double-click `AllWell.app` to launch.

On Apple Silicon the pipeline uses Metal automatically via
`tensorflow-metal`. About 4 GB of free RAM is recommended for StarDist
inference.

## Building the app

The build must run on a Mac; PyInstaller produces a binary for the host
architecture. The `allwell` mamba environment must be active.

```
mamba activate allwell
chmod +x _Docs/_Installation/build_all_well.sh
_Docs/_Installation/build_all_well.sh
```

The finished bundle is written to `dist/AllWell.app`. To distribute:

```
cd dist && zip -r AllWell-mac.zip AllWell.app
```

Universal binary (Intel + Apple Silicon):

```
TARGET_ARCH=universal2 _Docs/_Installation/build_all_well.sh
```

This requires a universal2 Python from python.org; the Miniforge Python is
architecture-specific and cannot produce a universal binary.

## Project layout

Repository root:

```
all_well.py                 Composition root — QMainWindow hosting Review + Analyze
all_well_launcher.py        PyInstaller entry point (sets QtAgg, _MEIPASS sys.path)
analyze_tab.py              Analyze tab (PySide6) — schema form, run controls, live log
process_microscopy_v2.py    StarDist segmentation + fluorescence quantification pipeline
WellPlateZipper.py          Groups loose TIFs into per-well zip archives from a schema
pipeline_config.py          Shared pipeline-config constants
theme.py                    Legacy shim; real theming lives under ui/theme/

services/                   Analyze-tab service layer
  input_resolution_service.py   Resolve input/output layout; invoke WellPlateZipper
  pipeline_service.py           Build CLI args, spawn pipeline, write pipeline_info.json

ui/theme/                   Qt theming
  __init__.py               Re-exports set_theme/get_color/build_stylesheet/THEMES
  styles.py                 Theme colours + QSS builder
  dark.qss / light.qss      Stylesheet fragments
  theme_manager.py          ThemeManager wrapper used by AllWellApp

well_viewer/                Review tab package (PySide6)
  __init__.py               Lazy-exposes WellViewerApp + debug_flags
  runtime_app.py            WellViewerApp (QMainWindow-contained QWidget root)
  ARCHITECTURE.md           tabs/ vs views/ split guidance

  tabs/                     Centre-notebook page builders (build_*_tab(app, parent))
    line_graphs_tab_view.py
    bar_plots_tab_view.py
    scatter_cells_tab_view.py
    scatter_agg_tab_view.py
    batch_export_tab_view.py
    review_csv_tab_view.py

  views/                    Reusable UI components and non-tab panels
    centre_view.py          Builds QTabWidget and wires every tab
    sidebar_view.py         Main well-picker sidebar
    preview_panel_view.py   Movie Montage preview controls + canvas
    preview_view.py         FOV picker
    image_panel_view.py     Image canvas + LUT controls (_label_to_rgb colormap)
    well_button.py          Plate-grid well buttons; 8×12 grid builder
    grouping_view.py        Replicate-set + group cards; group-def panel
    replicate_panel_view.py Sample Definitions sidebar
    bar_group_panel_view.py Bar-plot group panel + card builders
    label_editor_view.py    WELL LABELS editor
    stats_view.py           Statistics tab UI
    status_view.py          Status/log strip + logging handler

  cell_gating_tab.py        Cell Gating tab widget (FluorGating, per-channel settings)
  smfish_tab.py             smFISH tab widget (transcript detection / overlays)

  (controllers and services — see next section)

_Docs/
  README_WellViewer.md      This file
  requirements.txt          Pinned pip-only dependencies
  icons/                    App / tab iconography (SVG)
  _Installation/
    all_well.spec           PyInstaller spec
    build_all_well.sh       Automated macOS build script
    schema_config.py
    hooks/                  PyInstaller hooks for bundled packages
      hook-stardist.py
      hook-csbdeep.py
      hook-pkg_resources.py
      rthook-pkg_resources.py
```

## Review tab — controllers and services (`well_viewer/`)

`runtime_app.py` wires a thin `WellViewerApp` that delegates work to cohesive
helper modules:

| Module | Responsibility |
|--------|----------------|
| `data_loading.py` | CSV + `pipeline_info.json` ingestion, schema inference |
| `viewer_state.py` | Pure state/parsing helpers (no Qt) |
| `load_controller.py` | Load/path lifecycle (`_load_path`, `_load_directory`) and token-map rebuild |
| `selection_controller.py` | Well selection and cross-tab syncing |
| `grouping_controller.py` | Replicate-set and group drag / membership mutations |
| `barplot_controller.py` | Bar data-model serialization, ordering, rendering |
| `lineplot_controller.py` | Line / fraction / CDF redraw orchestration |
| `scatter_controller.py` | Scatter (cells + aggregate) state + drawing |
| `scatter_callbacks.py` | Scatter UI callbacks and interactions |
| `plot_orchestrator.py` | Shared `_redraw` / figure-save delegation |
| `stats_controller.py` | Pairwise stats (t-test, Wilcoxon, Mann-Whitney, KS) |
| `preview_controller.py` | Preview image/zip classification and I/O |
| `preview_callbacks.py` | Movie-montage interaction wiring |
| `montage_controller.py` | Montage popout generation |
| `review_image_controller.py` | Review-Image tab logic (per-FOV overlay / labels) |
| `image_resolver.py` | Finds per-well images (zip + loose) across layouts |
| `export_service.py` | CSV / figure export helpers |
| `figure_export_editor.py` | Figure-customization dialog |
| `batch_export_dialog.py` | Batch-export dialog and preflight |
| `batch_models.py` | `ReplicateSet`, `BarGroup` dataclasses |
| `ui_helpers.py` | Shared Qt helpers: plot toolbar, wheel scroll, tooltips |
| `debug_flags.py` | Tab-scoped debug toggles |

Optional/runtime-heavy imports (TIFF, numpy, skimage, matplotlib) are
guarded or lazy so lightweight imports remain cheap.

## Review tab — centre-notebook tabs

Built by `well_viewer/views/centre_view.py` in this order:

1. **Line Graphs** — mean intensity ± SD/SEM, fraction above threshold, CDF.
   Drag the threshold line on the CDF to adjust.
2. **Bar Plots** — bar / beeswarm / violin modes; drag bars to reorder;
   adjustable y-axis limits.
3. **Scatter Plot: Cells** — per-cell scatter with gating.
4. **Scatter Plot: Aggregate** — per-well / per-replicate aggregate scatter.
5. **Movie Montage** — montage of top-hat filtered images per well / FOV /
   timepoint. Works with any quantified channel.
6. **Review Image** — single-FOV overlay + label viewer for spot-checking.
7. **Statistics** — pairwise tests across selected replicate sets.
8. **smFISH** — transcript detection / overlays (`smfish_tab.py`).
9. **Review CSV** — tabular view of the currently loaded CSVs.
10. **Cell Gating** — FluorGating and per-channel inclusion settings
    (`cell_gating_tab.py`).
11. **Batch Export** — preflight and export of plots / CSVs in bulk.
12. **Sample Definitions** — replicate-set and group editor (appears last).

The bottom controls bar includes a **Channel** dropdown that switches every
plot, axis label, threshold range, and export between all quantified
channels. The Movie Montage canvas reloads for the selected channel
automatically.

## Review tab — accepted input layouts

Open a results directory with the **Open…** button. The directory may be
any of:

- A flat directory of CSV files (`measurements_A01.csv`, …)
- A directory with an `out/` subfolder containing CSVs
- A directory with both `in/` (source zips) and `out/` (results) subfolders

Per-well image zips are discovered on demand for the Movie Montage and
Review Image tabs. The viewer reads `pipeline_info.json` (written by the
pipeline) to learn the filename schema and channel tokens — no manual
re-entry required.

## Analyze tab

`analyze_tab.py` wraps `process_microscopy_v2.py` with a Qt UI. The form is
scrollable; sections top-to-bottom:

1. **Filename Schema** — separator character (default `_`) and ordered
   field list. The "Schema string" text box shows the resulting schema and
   can be edited directly. Fields: `experiment`, `channel`, `well`, `fov`,
   `timepoint`, `ignore`. `channel` and `well` are required and must each
   appear exactly once. Schemas without `fov` (single-FOV acquisitions) are
   fully supported.
2. **Channel Tokens**
   - Nuclear (seg): token identifying the nuclear/segmentation channel
     (quantified and used for StarDist).
   - Fluorescent channels: one or more tokens to quantify; each produces
     its own intensity columns in the CSV.
3. **Folders** — input-folder resolution is handled by
   `services/input_resolution_service.py`:
   - Folder named `in/` → input = folder, output = `../out`
   - Folder contains `in/` subfolder → use it; output = `../out`
   - Folder contains loose TIFs (> 3) → `WellPlateZipper` is invoked to
     group them into per-well folders using the schema above
4. **Top-Hat Background Subtraction** — nuclear and fluorescent radii.
5. **Output Options / Compute Options / Run** — compression of input and
   output well folders, TF threads, worker count, CPU-only toggle, force
   re-run.

The log window displays the pipeline's streamed stdout, the number of
parallel workers used, and "Processing Complete" on success. When a run
finishes, `AllWellApp` automatically switches to the Review tab and loads
the output directory.

## Filename schema

The schema is a colon-separated list of field names applied left-to-right
to filename tokens (split on the separator).

```
experiment  — any experiment/project identifier (optional)
channel     — distinguishes imaging channels (required)
well        — 96-well plate position A01–H12 or A1–H12 (required)
fov         — field-of-view identifier (optional)
timepoint   — acquisition timepoint (optional)
ignore      — token present in filename but not used
```

Examples:

```
Exp01_NIR_B03_F001_02d04h30m.tif  →  experiment:channel:well:fov:timepoint   sep=_
A1_w1594_T01.tif                   →  well:channel:timepoint                  sep=_
Scan-A01-0001-GFP.tif              →  ignore:well:fov:channel                 sep=-
A01_DAPI.tif                       →  well:channel                            sep=_
```

The well token is normalised automatically: `A1` and `A01` are treated
identically.

Timepoint formats:

```
DDdHHhMMm     02d04h30m → 52.5 h
Standalone    48h, 2d, 30m, 90min
Pure number   24 or 1.5  (hours)
Prefixed      T01, day2, tp_3  (numeric suffix used as ordinal)
Any string    lexicographic sort order
```

## CSV output format

One CSV per well. Each row is one nucleus. Columns:

```
filename, experiment, channel, well, fov, timepoint, timepoint_hours
nucleus_id, area_px
<token>_total_intensity       — one set per quantified channel
<token>_mean_intensity
<token>_max_intensity
<token>_min_intensity
<token>_std_intensity
```

`<token>` is the lowercase channel token (e.g. `gfp`, `mcherry`, `w2turq`).
The nuclear/segmentation token is also quantified, so it appears as
standard `<token>_*_intensity` columns and is available in viewer selectors.

`pipeline_info.json` is written to the output directory alongside the CSVs
and records the schema, channel tokens, segmentation method, available
FOVs/timepoints, and execution options. The Review tab reads this file to
parse image filenames without requiring the user to re-enter the schema.

## Parallelism and GPU usage

The pipeline spawns one worker per well up to a configured maximum. Each
worker loads StarDist once and reuses it across every FOV in that well.

- **macOS with Metal GPU (default):** workers default to 2. Metal
  serialises GPU calls across processes, so additional workers do not
  improve GPU throughput — they only add RAM pressure. Two workers overlap
  I/O and CPU preprocessing with GPU inference.
- **CPU-only (`--cpu_only` or non-macOS):** workers =
  `floor((cpu_count − 1) / tf_threads)`, with `tf_threads` defaulting to 4.
  For example, 16 cores → 3 workers × 4 threads = 12 cores, with 1 reserved
  for the main process. Adjust with the **TF threads** field in Compute
  Options.

Temporary directories (`_tmp_extract_*`, `_tmp_images_*`) are always
removed when each well completes, even after an error. Any stragglers from
a previously crashed run are cleaned up at the start of the next run.

## Dependencies

Installed via mamba (do not touch with pip):

```
python          3.10.14
setuptools      69.5.1      must stay <70 — pkg_resources
numpy           1.24.x      must stay <1.25 for TF 2.13
scipy           1.11.x
scikit-image    0.21.x
matplotlib      3.8.x
pillow          10.0.x
imageio         2.28.x
h5py            3.9.x
```

Installed via pip (`--no-build-isolation`) — see `_Docs/requirements.txt`:

```
tensorflow-macos   2.13.0
tensorflow-metal   1.1.0
keras              2.13.1
protobuf           3.20.3
csbdeep            0.8.0
stardist           0.9.1
numba              0.57.1
llvmlite           0.40.1
tifffile           2023.9.26
imagecodecs        2023.9.18
pyinstaller        6.1.0    (build only)
PySide6                      GUI toolkit (Qt 6)
```

## Troubleshooting

**"AllWell.app is damaged and can't be opened":**

```
xattr -cr /Applications/AllWell.app
codesign --force --deep --sign - /Applications/AllWell.app
```

**App opens then immediately closes:**

```
dist/AllWell.app/Contents/MacOS/AllWell 2>&1 | head -100
```

**No module named 'pkg_resources':** `setuptools` was upgraded past v70.
Recreate the environment from scratch (never `pip install setuptools`,
never `mamba update --all`).

**No Metal GPU detected:**

```
pip install tensorflow-metal==1.1.0
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

**Movie Montage / Review Image shows "No images found":** ensure the
results directory has both `in/` and `out/` subfolders and that `out/`
contains `<well>_out.zip`. The viewer looks for top-hat filtered images
(`_tophat.tif`; legacy `_tophat_<channel>.tif`), overlays (`_overlay.png`),
and masks (`_labels.tif`) inside those zips. If the channel tokens differ
from what the viewer expects, re-open the directory — `pipeline_info.json`
is re-read on every open.

**Bar-plot timepoint dropdown is empty:** either no wells are selected or
the CSVs do not contain a `timepoint_hours` column. Check that the schema
used during analysis included a `timepoint` field. Single-timepoint
experiments show one entry (e.g. `0`).

**WellPlateZipper produces no zip files:** schema or separator does not
match the filenames. Check that `well` points to the correct token, the
separator matches, and the token is a valid plate position (A01–H12 or
A1–H12). The schema used is logged at the start of every run.

**StarDist model download fails (SSL error):** pre-download the model on
an unrestricted machine and copy `~/.keras/models/` across.

**`No module named 'stardist'` in the built app:** the build must include
`_Docs/_Installation/hooks/` — notably `hook-stardist.py`.

**Built app >900 MB:** normal. TensorFlow + numba + llvmlite + scipy +
matplotlib account for most of it.
