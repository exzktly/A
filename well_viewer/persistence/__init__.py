"""Persistence layer for WellViewerApp state.

Each module owns one save/load domain that previously lived as a method
cluster on ``WellViewerApp`` inside ``runtime_app.py``. Runtime methods now
delegate to these so the GUI class stops carrying disk-I/O implementations.

``ratios``, ``heatmap_layouts``, and ``line_order`` share a single
``persistence.json`` sidecar managed by ``_doc``; legacy per-domain JSON
files are migrated on first read. ``cell_overrides`` and the bar-group
file-picker stay separate.

Modules:
    _doc               Shared ``persistence.json`` reader/writer + migration.
    bar_groups         JSON file picker for the bar/replicate-group state.
    ratios             ``persistence.json["ratios"]``.
    heatmap_layouts    ``persistence.json["heatmap_layouts"]``.
    cell_overrides     ``cell_overrides.json`` (Segmentation tab patch).
    line_order         ``persistence.json["line_order"]``.
    sample_definitions Combined save/load/clear orchestration.
    cell_gating        Cell gating thresholds inside ``pipeline_info.json``.
"""
