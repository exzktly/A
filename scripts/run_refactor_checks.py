#!/usr/bin/env python3
"""Run consolidated refactor guardrail checks (PR19)."""

from __future__ import annotations

import subprocess
import sys


COMMANDS: list[list[str]] = [
    ["python", "scripts/check_duplicate_methods.py"],
    ["python", "scripts/check_internal_imports.py"],
    [
        "python",
        "-m",
        "py_compile",
        "well_viewer/runtime_app.py",
        "well_viewer/app.py",
        "well_viewer/viewer_state.py",
        "well_viewer/preview_controller.py",
        "well_viewer/barplot_controller.py",
        "well_viewer/lineplot_controller.py",
        "well_viewer/ui_helpers.py",
        "well_viewer/batch_models.py",
        "well_viewer/batch_export_dialog.py",
        "well_viewer/grouping_controller.py",
        "well_viewer/load_controller.py",
        "well_viewer/plot_orchestrator.py",
        "well_viewer/views/status_view.py",
        "well_viewer/views/centre_view.py",
        "well_viewer/views/grouping_view.py",
        "well_viewer/views/stats_view.py",
        "well_viewer/views/preview_view.py",
        "well_viewer/selection_controller.py",
        "well_viewer/preview_callbacks.py",
        "well_viewer/export_service.py",
        "well_viewer/views/preview_panel_view.py",
    ],
    ["python", "-c", "from well_viewer import WellViewerApp; print(WellViewerApp.__name__)"],
]


def main() -> int:
    for cmd in COMMANDS:
        print(f"[RUN] {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"[FAIL] {' '.join(cmd)}")
            return result.returncode
    print("[OK] all refactor checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
