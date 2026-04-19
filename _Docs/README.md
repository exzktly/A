# All Well – Current Architecture

This repository is organized around package-owned runtime modules under `well_viewer/`.

## Top-level runtime surfaces

- `all_well.py`
  - Multi-tab desktop entry point for analysis + review workflows.
- `well_viewer/runtime_app.py`
  - Canonical runtime implementation of `WellViewerApp`.
- `well_viewer/runtime_app_qt.py`
  - Qt-native review/runtime slice host used by the PySide6 shell.
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

## Views and tabs (UI builder modules)

All widget-construction code has been extracted from `runtime_app.py` into dedicated files.

### `well_viewer/views/`

Each file exposes one or more `build_*(app, parent)` / `*_refresh(app)` functions:

| File | Contents |
|------|----------|
| `centre_view.py` | Notebook orchestrator — creates tab frames, delegates to `tabs/` |
| `preview_panel_view.py` | Preview panel controls, montage canvas, LUT/top-hat controls |
| `status_view.py` | Bottom status/log strip; `_GUILogHandler` logging handler |
| `grouping_view.py` | Replicate-set cards (`rep_panel_refresh`), group cards (`grp_panel_refresh`), group-def panel (`build_group_def_panel`) |
| `stats_view.py` | Statistics tab UI |
| `preview_view.py` | Preview picker (FOV selector panel) |
| `widgets.py` | `_Tooltip` floating hover label |
| `image_panel_view.py` | `_ImagePanel` canvas + LUT; `_label_to_rgb` colormap |
| `well_label_widget.py` | `WellLabel` cross-platform button-label; `build_plate_grid` 8×12 grid |
| `sidebar_view.py` | Main well-picker sidebar (`build_sidebar`) |
| `bar_group_panel_view.py` | Bar-plot group panel + all card-builder helpers |
| `replicate_panel_view.py` | Sample Definitions left panel (`build_replicate_panel`) |
| `label_editor_view.py` | WELL LABELS editor (`build_label_editor`, `label_panel_refresh`) |

### `well_viewer/tabs/`

| File | Tab |
|------|-----|
| `line_graphs_tab_view.py` | Line Graphs |
| `bar_plots_tab_view.py` | Bar Plots |
| `scatter_cells_tab_view.py` | Scatter Plot: Cells |
| `scatter_agg_tab_view.py` | Scatter Plot: Aggregate |
| `batch_export_tab_view.py` | Batch Export |
| `review_csv_tab_view.py` | Review CSV |

## Ongoing direction

The target architecture is package-only runtime ownership via `well_viewer/*`.

UI-builder/callback extraction from `runtime_app.py` is complete: every panel builder, card-list refresher, and tab constructor now lives in a dedicated `views/` or `tabs/` file. `WellViewerApp` methods are thin one-line delegators. Runtime logic (data loading, plot redraw, group mutations) continues to live in the controller/orchestrator modules.
