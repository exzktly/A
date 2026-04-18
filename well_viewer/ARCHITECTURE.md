# Well Viewer package layout

This package intentionally keeps `tabs/` and `views/` separate:

## `well_viewer/tabs`
- Owns builders for **centre notebook pages**.
- Each module exposes a `build_*_tab(app, parent)` function that populates the
  pre-created notebook frame.
- Examples: line graphs, bar plots, scatter plots, batch export.

## `well_viewer/views`
- Owns **reusable UI components** and **non-centre-notebook layout builders**.
- Includes sidebars, preview/image/status panels, shared widgets, and helpers
  composed by runtime and tab builders.

## Why both exist
The split prevents giant tab modules from accumulating shared widget logic and
keeps notebook-page assembly separate from reusable view primitives.
