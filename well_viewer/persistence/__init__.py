"""Persistence layer for WellViewerApp state.

Each module owns one save/load domain that previously lived as a method
cluster on ``WellViewerApp`` inside ``runtime_app.py``. Runtime methods now
delegate to these so the GUI class stops carrying disk-I/O implementations.

Modules:
    bar_groups         JSON file picker for the bar/replicate-group state.
    ratios             ``ratios.json`` in the data directory.
    heatmap_layouts    ``heatmap_layouts.json`` in the data directory.
    cell_overrides     ``cell_overrides.json`` (Segmentation tab patch).
    line_order         ``line_order.json`` for the Line Plot tab order.
    sample_definitions Combined save/load/clear orchestration.
    cell_gating        Cell gating thresholds inside ``pipeline_info.json``.
"""
