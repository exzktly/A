# Tkinter → PySide6 Port: Phase 0/1 Architecture Note

This note captures the Phase 0 inventory/cutlines and tracks progress through later migration phases from `TODO_PORT.md`.

> Working agreement: every subsequent migration phase must read this document first and update it with scope, implementation, and remaining cutlines.

## 1) Tkinter dependency inventory (Phase 0)

### Direct usage map by area

#### Root app shell
- `all_well.py`
  - `tk.Tk` application shell + widget tree construction.
  - `ttk.Style` theme wiring.

#### Analysis tab
- `analyze_tab.py`
  - `tk.Frame` UI tree and widget variables.
  - **Dialogs/notifications now routed via `ui.ports`** (no direct `filedialog/messagebox` imports remain).

#### Theme package
- `ui/theme/styles.py`
  - `ttk.Style` theme definitions and tk option-database styling.

#### Well viewer runtime/tabs/controllers
- `well_viewer/runtime_app.py`
  - Main runtime shell and most widget construction.
  - Matplotlib Tk backend (`FigureCanvasTkAgg`, `NavigationToolbar2Tk`).
  - **Dialogs/notifications now routed via `ui.ports`**.
- `well_viewer/app.py`, `well_viewer/smfish_tab.py`, `well_viewer/cell_gating_tab.py`, `well_viewer/scatter_callbacks.py`, `well_viewer/preview_callbacks.py`, plus view/controller helpers continue using tk widgets and TkAgg.

#### Packaging
- `_Installation/all_well.spec`
  - Explicit `tkinter` hidden imports.
- `_Installation/build_all_well.sh`
  - tkinter availability/functional checks.

## 2) Module bucket classification (Phase 0)

### Bucket A — Pure logic (freeze/reuse during widget migration)
- `services/input_resolution_service.py`
- `services/pipeline_service.py`
- `process_microscopy_v2.py`
- `pipeline_config.py`
- Most non-UI data/analysis helpers under `well_viewer/*_controller.py` that do not construct widgets.

### Bucket B — Mixed logic + UI (migrate by seams)
- `analyze_tab.py`
- `well_viewer/runtime_app.py`
- `well_viewer/smfish_tab.py`
- `well_viewer/cell_gating_tab.py`
- `well_viewer/scatter_callbacks.py`

### Bucket C — UI-only
- `all_well.py`
- `ui/theme/styles.py`
- `well_viewer/views/*` (view builders/widgets)
- Tk-specific launch shells and tab container code.

## 3) Migration cutlines (Phase 0)

1. **Service cutline (frozen now):** keep pipeline/input/data-export behavior in `services/` and controller logic framework-agnostic.
2. **Adapter cutline (introduced in Phase 1):** dialogs/notifications/app services accessed via `ui.ports` interface.
3. **View cutline:** widget construction + style/theme backend isolated to tab/view modules and runtime shell.
4. **Backend cutline (future phase):** matplotlib host abstraction to swap TkAgg for Qt canvas without touching plotting logic.

## 4) Migration order

1. Continue routing remaining direct dialogs/notifications to `ui.ports` (started in Phase 1).
2. Replace `StringVar/BooleanVar/IntVar` clusters with typed state models by feature area.
3. Port app shell (`all_well.py` + runtime host) to PySide6 containers.
4. Port tabs in vertical slices with shared utilities pulled up.
5. Replace TkAgg backend host with Qt host helper.
6. Remove tkinter from packaging/runtime paths.

## 5) Phase 1 implementation summary

### Added temporary adapter package
- `ui/ports/base.py`
  - `UIPort` protocol (dialogs, notifications, timers, clipboard).
  - `FileFilter` helper type.
- `ui/ports/tk_port.py`
  - tkinter-backed implementation (`TkUIPort`).
- `ui/ports/__init__.py`
  - process-wide default port accessor (`get_ui_port`).

### Routed existing calls through adapter
- `analyze_tab.py`
  - Replaced direct `filedialog/messagebox` calls with `get_ui_port()` usage.
- `well_viewer/runtime_app.py`
  - Replaced direct dialog/messagebox imports and usage with `get_ui_port()` methods.
  - Updated JSON save/load helpers and bar-group import/export flows to use adapter abstractions.

## 6) Current simplification result

- Non-view modules in `services/` remain tkinter-free.
- Dialog/messagebox coupling is reduced and concentrated in one tkinter-specific adapter (`ui/ports/tk_port.py`), which is the planned swap point for a future PySide6 port implementation.

## 7) Phase 2 completion update — typed state models

- Added framework-agnostic state models in `services/ui_state_models.py`:
  - `AnalysisPipelineState`
  - `PlotViewState`
  - `GroupingState`
  - `ExportSettings`
- Added conversion/normalization logic in `AnalysisPipelineState.from_ui_values(...)`.
- Updated `analyze_tab.py` to convert Tk widget values into `AnalysisPipelineState` and then emit pipeline options through `to_pipeline_options()`.

### Phase-2 impact

- Parsing/defaulting logic previously embedded in ad-hoc widget reads is now centralized and testable without a Tk event loop.
- Domain-state ownership is explicit and grouped by analysis/plot/group/export concerns.

## 8) Phase 3 completion update — PySide6 shell

- Migrated the root desktop shell to PySide6 in `all_well.py`:
  - `QApplication`
  - `QMainWindow`
  - `QTabWidget`
  - simple bottom status/log panel (`QTextEdit`)
- Kept one canonical launcher path (`all_well_launcher.py` -> `all_well.main`) and removed explicit TkAgg bootstrap from launcher.
- During early migration, legacy Tk fallback paths were retained temporarily while Qt slices were brought up.

### Remaining cutline after Phase 3

- The shell is now Qt-based, while tab internals remain Tk-based until Phase 4 vertical-slice ports are finished.

## 9) Phase 4 completion update — Slices A/B/C/D

- Implemented `analyze_tab_qt.py` with a runnable Qt Analyze workflow:
  - input directory picker
  - core run/stop controls
  - progress/status UI
  - live log panel
- Added `well_viewer/runtime_app_qt.py` with Qt-native runtime shell composition:
  - left well sidebar
  - centre plot tab host (Line/Bar/Scatter/CDF)
  - right tool panel for specialized dialogs
- Added shared Qt helper utilities for repeated section/field and dialog composition (now consolidated in `ui/qt_ui.py`).
- Wired `all_well.py` to host both Qt Analyze and Qt Review runtime slices directly.

### Phase-4 slice mapping

- Slice A → `analyze_tab_qt.py`
- Slice B/C/D → `well_viewer/runtime_app_qt.py`

## 10) Phase 5 completion update — Qt matplotlib host

- Added `ui/qt_plot_host.py` as the canonical Qt matplotlib host utility:
  - creates `FigureCanvasQTAgg` + `NavigationToolbar2QT`
  - returns a small host bundle (`figure`, `axis`, `canvas`, `toolbar`, `widget`)
  - includes `draw_message(...)` helper for consistent placeholder/empty-state rendering
- Updated `well_viewer/runtime_app_qt.py` plot tabs to use the shared host utility for Line/Bar/Scatter/CDF tabs.
- Verified basic interaction availability by using Qt-native toolbar widgets attached to each host.

## 11) Phase 6 completion update — Qt theming simplification

- Added `ui/qt_theme.py` as the centralized Qt theme token + stylesheet module.
- Reduced theme variants to two supported modes: `Dark` and `Light`.
- Added shell-level theme selector in `all_well.py` (`QComboBox`) that applies the selected stylesheet via `apply_theme(...)`.
- Removed dependency on ttk-style specific workarounds for Qt-hosted runtime paths.

## 12) Phase 7 completion update — packaging/build/runtime docs

- Updated `_Installation/build_all_well.sh` dependency checks to validate `PySide6` instead of `tkinter`.
- Updated `_Installation/all_well.spec`:
  - removed tkinter hidden imports
  - switched matplotlib hidden backend from TkAgg to QtAgg
  - added explicit PySide6 hidden imports
  - removed `PySide6` from excluded package list
- Updated docs (`_Docs/README.md`, `_Docs/README.txt`, `_Docs/README_AI.md`) to reflect PySide6 prerequisites and runtime instructions.

## 13) Phase 8 progress update — deletion/consolidation pass

- Removed legacy Tk fallback from packaging-required paths:
  - `_Installation/all_well.spec` no longer bundles `all_well_tk_legacy.py` as a sibling script.
  - `_Installation/build_all_well.sh` no longer requires `all_well_tk_legacy.py`.
- Removed legacy shell source file `all_well_tk_legacy.py` from the active repository runtime path.
- Removed Tk-specific ImageTk packaging check from build preflight.
- Updated user-facing runtime description in `all_well.py` argument help and docs to point to Qt-first paths.
- Added guard tests to enforce that `services/*.py` remains UI-framework-agnostic (no tkinter/PySide6 imports), now consolidated under `tests/test_migration_guards.py`.
- Consolidated Qt helpers to reduce file sprawl:
  - `ui/qt_helpers.py` + `ui/qt_dialogs.py` merged into `ui/qt_ui.py`.
  - `well_viewer/qt_runtime_io.py` + `well_viewer/qt_runtime_plots.py` folded into `well_viewer/runtime_app_qt.py`.
- Added smoke/contract tests:
  - `tests/test_qt_smoke.py`
  - `tests/test_migration_guards.py` (consolidates import-boundary, dialog-wrapper, runtime-path, and UI-port contract checks)

## 14) Completion status

- Migration checklist items are now marked complete in `TODO_PORT.md`.
- Qt-first runtime path is in place with Qt-native shell/slices, shared Qt theming, plot hosts, and tool dialogs.
- Verification checklist (tests + smoke coverage + manual QA tracking) has been completed per the TODO plan.

## 15) Ongoing slice-D progress

- Added `well_viewer/qt_tools.py` with Qt-native dialog implementations for:
  - figure export editor
  - batch export options
- Wired `well_viewer/runtime_app_qt.py` tool buttons to these dialogs for active Qt-side configuration flows.
