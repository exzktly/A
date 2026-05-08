"""Backwards-compatible re-export shim.

Implementation now lives under ``well_viewer.batch_export`` (one module per
panel class). Existing callers that import from this path continue to work.
"""

from __future__ import annotations

from well_viewer.batch_export import (
    BarBatchExportPanel,
    BatchExportPanel,
    ScatterBatchExportPanel,
    _WellGridButton,
)

# Legacy aliases retained from the original ``batch_export_dialog`` module.
BatchExportDialog = BatchExportPanel
BarBatchExportDialog = BarBatchExportPanel

__all__ = [
    "BatchExportPanel",
    "BarBatchExportPanel",
    "ScatterBatchExportPanel",
    "BatchExportDialog",
    "BarBatchExportDialog",
    "_WellGridButton",
]
