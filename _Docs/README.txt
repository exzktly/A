All-Well — Multi-Channel Fluorescence Microscopy Pipeline & Viewer
==================================================================

All-Well is an all-in-one macOS application for fluorescence microscopy
quantification.  It combines a StarDist-based nuclear segmentation pipeline
with an interactive multi-channel data viewer in a single double-clickable app.

Two top-level tabs:

  Review   — load and explore per-well fluorescence measurement results:
               line graphs, bar/violin/beeswarm plots, CDF, statistics,
               replicate set management, and image preview.  Channel selector
               in the bottom bar switches between all quantified channels.

  Analyze  — run the segmentation pipeline on a folder of microscopy images
               with a live log and per-well progress bar.  Supports arbitrary
               filename conventions via the Filename Schema form.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION A — PRE-BUILT APP (recommended for end users)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you have received AllWell.app (or AllWell-mac.zip), no Python installation
is needed.

  1. If you received a zip file, double-click it to extract AllWell.app.

  2. Move AllWell.app to your Applications folder (optional but recommended).

  3. First-launch Gatekeeper fix — macOS may show "damaged and can't be
     opened" because the app is not from the App Store.  Run these two
     commands in Terminal once:

         xattr -cr /Applications/AllWell.app
         codesign --force --deep --sign - /Applications/AllWell.app

     (Adjust the path if you did not move it to Applications.)

  4. Double-click AllWell.app to launch.

Note: the app bundles its own Python and all dependencies — nothing else
needs to be installed on the machine running it.  The Analyze pipeline does
require enough RAM and CPU to run StarDist inference (~4 GB RAM recommended).

GPU acceleration on Apple Silicon:
  The pipeline uses Apple's Metal GPU automatically on M-series Macs if
  tensorflow-metal is bundled (it is in the pre-built app).  No configuration
  needed.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION B — RUN FROM SOURCE (developers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prerequisites:
  • Miniforge — https://github.com/conda-forge/miniforge/releases/latest
      macOS Apple Silicon:
          curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
          bash Miniforge3-MacOSX-arm64.sh
  • Xcode Command Line Tools (for Tk and compiler):
          xcode-select --install

Create the environment:

    mamba create -n allwell python=3.10.14 setuptools=69.5.1 "numpy>=1.24,<1.25" scipy scikit-image matplotlib pillow imageio h5py -c conda-forge -y
    mamba activate allwell

IMPORTANT — verify pkg_resources works before proceeding:

    python -c "import pkg_resources; print('OK')"

If that fails, do not continue.  See Troubleshooting below.

Install pip-only dependencies:

    pip install --no-build-isolation -r _Docs/requirements.txt

Always use --no-build-isolation with pip in this environment.  Without it,
pip may use the system Python to build wheels, which will fail.

Verify TensorFlow sees the Metal GPU (Apple Silicon only):

    python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
    # Expected: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]

Run the app:

    mamba activate allwell
    python all_well.py

You can also run the components individually:

    python -m well_viewer.runtime_app  # Review tab only
    python analyze_tab.py           # Analyze tab only (standalone test)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION C — BUILD THE APP FROM SOURCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The build must run on a Mac — PyInstaller produces binaries for the platform
it runs on.  The allwell mamba environment must be active before building.

PROJECT STRUCTURE:

The build script must find files in the repository root and _Installation/
subdirectory:

  Repository Root:
    all_well.py                  main application
    all_well_launcher.py         PyInstaller entry point
    analyze_tab.py               Analyze tab widget
    process_microscopy_v2.py     segmentation pipeline
    WellPlateZipper.py           well-image zip utility
    well_viewer/                 Review tab package (modularized viewer)
    ui/                          Theme and shared UI components
    services/                    Business logic modules

  _Installation/ subdirectory:
    all_well.spec                PyInstaller build configuration
    build_all_well.sh            automated build script
    hooks/                       PyInstaller hooks for special packages
        hook-stardist.py         — bundles stardist with data files
        hook-csbdeep.py          — bundles csbdeep with data files
        hook-pkg_resources.py    — provides pkg_resources from conda
        rthook-pkg_resources.py  — runtime hook for pkg_resources

  _Docs/ subdirectory:
    requirements.txt             pinned pip dependencies

Steps:

  1. Complete Option B setup first.

  2. Activate the environment:

         mamba activate allwell

  3. Run the build script (from either the repository root or _Installation/):

         chmod +x _Installation/build_all_well.sh
         _Installation/build_all_well.sh

     The script automatically locates the repository root and verifies that
     all required files exist in the correct locations (repository root,
     _Installation/, and _Docs/) before proceeding with the PyInstaller build.

  4. The finished app will be at:

         dist/AllWell.app

  5. To distribute, zip it:

         cd dist && zip -r AllWell-mac.zip AllWell.app

Universal binary (runs on both Intel and Apple Silicon):

    TARGET_ARCH=universal2 _Installation/build_all_well.sh

    (Requires a universal2 Python from https://python.org — the Miniforge
    Python is architecture-specific and cannot produce a universal binary.)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USING THE APP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REVIEW TAB

  Open a results directory with the Open… button (top right).  The directory
  should contain per-well CSV files produced by the pipeline, and optionally
  per-well output zip files for image preview.

  Accepted input layouts:
    • A flat directory of CSV files (measurements_A01.csv, …)
    • A directory with an out/ subfolder containing CSVs
    • A directory with both in/ (source zips) and out/ (results) subfolders

  Channel selector:
    A "Channel" dropdown in the bottom controls bar lets you switch between
    all fluorescent channels that were quantified.  All plots, axis labels,
    threshold range, and CSV exports update automatically.  The Preview tab
    reloads images for the selected channel automatically when you switch.

  Tabs within Review:
    Line Graphs      — mean intensity ± SD/SEM, fraction above threshold, CDF.
                       Drag the threshold line on the CDF to adjust.
    Bar Plots        — bar, beeswarm, or violin mode; drag bars to reorder;
                       adjustable y-axis limits at the bottom.
    Preview          — montage of top-hat filtered images per well/FOV.
                       Works with any channel — not limited to GFP.
    Statistics       — pairwise tests (t-test, Wilcoxon, Mann-Whitney, KS).
    Sample Defs      — define replicate sets; plate-map colour coding.

ANALYZE TAB

  The form is scrollable — use two-finger trackpad scroll to reach all
  options including the Run button at the bottom.

  When a run completes, "Processing Complete" is displayed prominently in
  the log window in green.  The number of parallel worker processes used
  is also reported in the log before inference begins.

  Form sections (top to bottom):

  1. Filename Schema
       Define how your image filenames are structured.  Set the separator
       character (default: underscore) and use the five position dropdowns
       to assign a field to each token in your filename.

       The "Schema string" text box shows the resulting schema and can be
       edited directly — type the schema (e.g. well:channel:timepoint) and
       press Return.  This is the most reliable way to set the schema.

       Field names: experiment, channel, well, fov, timepoint, ignore
       "channel" and "well" must each appear exactly once.
       Unused positions should be set to "ignore".

       Schemas without a "fov" field (single-FOV acquisitions) are fully
       supported — the Preview tab will show images correctly.

       The input folder selector is locked until the schema is valid.

  2. Channel Tokens
       Nuclear (seg):        token identifying the nuclear/segmentation channel
                             (used for StarDist only, not quantified)
       Fluorescent channels: one or more tokens identifying channels to quantify.
                             Use "+ Add channel" to add additional channels.
                             Each produces its own intensity columns in the CSV.

  3. Folders
       Browse to your input folder.  Accepted layouts:
         • A folder named "in" containing per-well zip files (A01.zip, …)
         • A folder containing an "in" subfolder with zip files
         • A folder containing TIF files — WellPlateZipper runs automatically
           to group them into per-well zips using the filename schema above

       The output folder is set automatically and shown in the form.
       The progress bar reflects the actual number of wells found, not a
       fixed plate size.

  4. Top-Hat Background Subtraction
       Nuclear radius:  top-hat filter radius for the segmentation channel
       Fluor radius:    top-hat filter radius applied to all fluorescent channels

  5. Output Options / Compute Options / Run


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILENAME SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Any underscore-separated (or custom separator) naming scheme can be described
using the Filename Schema form.  The schema is a colon-separated ordered list
of field names:

    experiment  — any experiment/project identifier (optional)
    channel     — the token distinguishing imaging channels (required)
    well        — 96-well plate position A01–H12 or A1–H12 (required)
    fov         — field-of-view identifier (optional; omit for single-FOV data)
    timepoint   — acquisition timepoint (optional)
    ignore      — field present in filename but not used

Examples:

  Filename: Exp01_NIR_B03_F001_02d04h30m.tif
  Schema:   experiment:channel:well:fov:timepoint   separator: _

  Filename: A1_w1594_T01.tif
  Schema:   well:channel:timepoint   separator: _

  Filename: Scan-A01-0001-GFP.tif
  Schema:   ignore:well:fov:channel  separator: -

  Filename: A01_DAPI.tif  (single FOV, no timepoint)
  Schema:   well:channel             separator: _

The well token is normalised automatically: A1 and A01 are treated identically.

TIMEPOINT FORMATS

  DDdHHhMMm    02d04h30m = 2 days 4 hours 30 min → 52.5 h
  Standalone   48h, 2d, 30m, 90min
  Pure number  24 or 1.5  (treated as hours)
  Prefixed     T01, day2, tp_3  (numeric suffix used as ordinal)
  Any string   plotted in lexicographic sort order if nothing else matches


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CSV OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

One CSV per well.  Each row is one nucleus.  Columns:

  filename, experiment, channel, well, fov, timepoint, timepoint_hours
  nucleus_id, area_px
  <token>_total_intensity    — one set of five columns per fluorescent channel
  <token>_mean_intensity
  <token>_max_intensity
  <token>_min_intensity
  <token>_std_intensity

Where <token> is the lowercase channel token, e.g. gfp, mcherry, w2turq.

The pipeline_info.json sidecar (written to the output directory alongside
the CSVs) records the filename schema and channel tokens used during the run.
The viewer reads this file to correctly parse image filenames for the Preview
tab without requiring the user to re-enter the schema.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARALLELISM AND GPU USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The pipeline spawns one worker process per well, up to a configured maximum.
Each worker loads StarDist once and reuses it across all FOVs in that well.

On macOS with Metal GPU (default, no --cpu_only flag):
  Workers default to 2.  Metal serialises GPU calls across processes, so
  running more workers does not increase GPU throughput — it only adds RAM
  pressure.  The two workers overlap I/O and CPU preprocessing with GPU
  inference, which is the practical benefit.

On CPU-only mode (--cpu_only, or non-macOS):
  Workers = floor((cpu_count − 1) / tf_threads), where tf_threads defaults
  to 4.  Example: 16 cores → 3 workers × 4 threads = 12 cores, with 1
  reserved for the main process.  Adjust tf_threads with the "TF threads"
  field in the Compute Options section if your images are unusually large
  or small.

The number of workers actually used is printed to the log window before
inference starts, e.g. "Workers: 2 parallel well(s) will be processed
simultaneously."

Temporary directories (_tmp_extract_* and _tmp_images_*) created during
processing are always removed when each well completes, even if an error
occurs.  Any directories left over from a previously crashed run are cleaned
up automatically at the start of the next run.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPENDENCY SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Installed via mamba (do not touch with pip):
  python          3.10.14
  setuptools      69.5.1    pkg_resources — must stay <70, never upgrade
  numpy           1.24.x    must stay <1.25 for TF 2.13 compatibility
  scipy           1.11.x
  scikit-image    0.21.x
  matplotlib      3.8.x
  pillow          10.0.x
  imageio         2.28.x
  h5py            3.9.x

Installed via pip (--no-build-isolation):
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


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"AllWell.app is damaged and can't be opened":

    xattr -cr /Applications/AllWell.app
    codesign --force --deep --sign - /Applications/AllWell.app

App opens then immediately closes:

    dist/AllWell.app/Contents/MacOS/AllWell 2>&1 | head -100

No module named 'pkg_resources':
  setuptools was upgraded past v70, which removed pkg_resources.
  The only reliable fix is to recreate the environment from scratch:

    mamba deactivate
    mamba env remove -n allwell -y
    mamba create -n allwell python=3.10.14 setuptools=69.5.1 "numpy>=1.24,<1.25" scipy scikit-image matplotlib pillow imageio h5py -c conda-forge -y
    mamba activate allwell
    python -c "import pkg_resources; print('OK')"
    pip install --no-build-isolation -r requirements.txt

  Never run "pip install setuptools" — it will upgrade past v70 and break things.
  Never run "mamba update --all" — it may upgrade setuptools.

No Metal GPU detected:

    pip install tensorflow-metal==1.1.0
    python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

Preview tab shows "No images found" for a well:
  Ensure the results directory has both in/ and out/ subfolders, and that
  the out/ folder contains a <well>_out.zip file.  The viewer looks for
  top-hat filtered images (_tophat_<channel>.tif), overlays (_overlay.png),
  and masks (_labels.tif) inside those zips.  If the channel token used
  during analysis differs from what the viewer expects, re-open the directory
  — the viewer reads pipeline_info.json to detect the correct tokens
  automatically.

Bar plot timepoint dropdown is empty:
  This can happen if no wells are selected or if the CSV files do not
  contain a timepoint_hours column.  Check that the Filename Schema used
  during analysis included a "timepoint" field.  For single-timepoint
  experiments the dropdown will show one entry (e.g. "0").

WellPlateZipper produces no zip files:
  The filename schema or separator does not match your filenames.  Check:
    • The "well" position points to the correct token
    • The separator character matches (underscore by default)
    • The well token is a valid plate position (A01–H12 or A1–H12)
  The schema used is logged at the start of every run.
  If a previous failed run left an empty in/ folder, delete it and retry.

Temporary directories not cleaned up after a crash:
  Any _tmp_extract_* or _tmp_images_* directories left in the output folder
  by a previously crashed run are removed automatically at the start of the
  next run.  You can also delete them manually — they contain only
  intermediate files and are safe to remove at any time.

StarDist model download fails (SSL error):
  Pre-download the model on an unrestricted machine and copy
  ~/.keras/models/ to the target machine.

Pipeline fails with "No module named 'stardist'":
  Ensure the app was built with the _Installation/hooks/ directory present.
  The hooks/ subdirectory must contain hook-stardist.py and other
  PyInstaller hooks required for proper bundling of special packages.

Build produces app >900 MB:
  Normal — TensorFlow + numba + llvmlite + scipy + matplotlib together
  account for most of this.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT STRUCTURE & KEY FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPOSITORY ROOT — Application & Pipeline:

  all_well.py                      Outer application frame; embeds both
                                   Review and Analyze tabs
  all_well_launcher.py             PyInstaller entry point; configures
                                   sys.path for bundled environment
  analyze_tab.py                   Analyze tab — workflow UI, schema form,
                                   channel selectors, progress tracking
  process_microscopy_v2.py         StarDist segmentation + fluorescence
                                   quantification pipeline
  WellPlateZipper.py               Groups TIF files into per-well zip
                                   archives using filename schema

  well_viewer/                     Review tab — modularized viewer package:
    runtime_app.py                 — Main Review tab GUI
    controllers/                   — Event handlers and business logic
    views/                         — UI component builders
    models/                        — Data management and state
    services/                      — Data loading and utilities

  ui/                              Shared UI components and theming:
    theme/                         — Theme definitions and styles
    components/                    — Reusable widget builders

  services/                        Business logic and data handling:
    (modularized utilities for pipeline and viewer)

_INSTALLATION/ DIRECTORY — Build Configuration:

  all_well.spec                    PyInstaller build specification
  build_all_well.sh                Automated macOS build script
  all_well_launcher.py             (copy) Entry point for PyInstaller
  hooks/                           PyInstaller hooks for special packages:
    hook-stardist.py               — Bundles stardist weights & configs
    hook-csbdeep.py                — Bundles csbdeep data files
    hook-pkg_resources.py          — Provides pkg_resources in bundle
    rthook-pkg_resources.py        — Runtime hook for pkg_resources

_DOCS/ DIRECTORY — Documentation & Dependencies:

  README.txt                       This file (installation & usage guide)
  requirements.txt                 Pinned pip-only dependencies
  README.md, README_AI.md         Additional documentation
