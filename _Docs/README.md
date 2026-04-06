# All Well – Current Architecture

This repository is organized around package-owned runtime modules under `well_viewer/`.

## Top-level runtime surfaces

- `all_well.py`
  - Multi-tab desktop entry point for analysis + review workflows.
- `well_viewer/runtime_app.py`
  - Canonical runtime implementation of `WellViewerApp`.
- `well_viewer/app.py`
  - Package-facing app entry (`from well_viewer import WellViewerApp`).

## `well_viewer/` module ownership

- `well_viewer/state.py`
  - Pure state/parsing helpers (schema extraction, `pipeline_info.json` parsing).

- `well_viewer/ui_support.py`
  - Shared Tk utility UI helpers (dialogs, scrollable canvas helpers).

- `well_viewer/preview_controller.py`
  - Preview image/zip classification and I/O helpers.
  - Includes image decode helper (`open_imgref_as_array`) and zip-member scanners.

- `well_viewer/barplot_controller.py`
  - Bar-plot data-model serialization + rendering helpers.
  - Includes ordering (`ordered_bar_keys`), item collection, shared bar rendering (`render_bar_items`), and bar y-limit application.

- `well_viewer/lineplot_controller.py`
  - Line/fraction/CDF redraw orchestration (`redraw_line_plots`) extracted from legacy shell.

- `well_viewer/batch_models.py`
  - Batch export data classes (`ReplicateSet`, `BarGroup`).

- `well_viewer/batch_export.py`
  - Batch export utility helpers (naming, selected-list extraction, preflight group filtering).

- `well_viewer/grouping_controller.py`
  - Replicate/group drag + membership mutation handlers delegated from `WellViewerApp` (`_rep_*`, `_grp_*`, `_bg_*` families).

- `well_viewer/load_controller.py`
  - Load/path lifecycle orchestration (`_load_path`, `_load_directory`) and token-map rebuild ownership.

- `well_viewer/plot_orchestrator.py`
  - Plot redraw and figure save orchestration shared by line/bar tabs (`_redraw`, `_save_*` delegation).

## Runtime strategy (current state)

1. Keep runtime ownership in `well_viewer/*` modules.
2. Move cohesive responsibilities into dedicated controllers/views/services.
3. Preserve existing user-visible behavior and file/CLI conventions.

## Practical dependency boundaries

- Plotting: Matplotlib + Tk are used by viewer shell/controller orchestration.
- Image preview: optional TIFF/PIL/numpy paths are handled in preview helpers with runtime checks.
- Optional/runtime-heavy imports are isolated behind lazy/delegated paths where possible to keep lightweight import/CLI checks robust.

## Ongoing direction

The target architecture is package-only runtime ownership via `well_viewer/*`.

As of PR24, subsystem logic already lives in dedicated controller/orchestrator modules; next work focuses on extracting remaining UI-builder/callback families so app composition stays in package modules rather than the legacy monolith file.
