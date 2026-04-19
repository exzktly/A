"""PySide6 application shell for All-Well (Phase 3 migration)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


class _ImportErrorWindow:
    """Fallback path when PySide6 is unavailable in the runtime environment."""

    def __init__(self, exc: Exception):
        self._exc = exc

    def run(self) -> int:
        sys.stderr.write(
            "PySide6 is required for the migrated All-Well shell. "
            f"Import failed: {self._exc}\n"
        )
        return 2


def main() -> int:
    ap = argparse.ArgumentParser(
        description="All-Well PySide6 shell",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--data_dir",
        type=Path,
        default=None,
        help="Optional dataset path for initial Review runtime context.",
    )
    args = ap.parse_args()

    try:
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:  # pragma: no cover - import/runtime environment dependent
        return _ImportErrorWindow(exc).run()

    app = QApplication(sys.argv)
    from ui.qt_theme import apply_theme, theme_names

    apply_theme(app, "Dark")

    win = QMainWindow()
    win.setWindowTitle("All-Well")
    win.resize(1280, 860)

    root = QWidget()
    root_layout = QVBoxLayout(root)
    root_layout.setContentsMargins(10, 10, 10, 10)
    root_layout.setSpacing(8)

    header = QHBoxLayout()
    title = QLabel("All-Well")
    title.setStyleSheet("font-size: 18px; font-weight: 600;")
    header.addWidget(title)
    header.addStretch(1)
    theme_picker = QComboBox()
    theme_picker.addItems(theme_names())
    theme_picker.setCurrentText("Dark")
    theme_picker.currentTextChanged.connect(lambda name: apply_theme(app, name))
    header.addWidget(QLabel("Theme:"))
    header.addWidget(theme_picker)
    root_layout.addLayout(header)

    tabs = QTabWidget()

    from well_viewer.runtime_app_qt import WellViewerRuntimeQt

    review_controller = WellViewerRuntimeQt()
    review_tab = review_controller.widget

    from analyze_tab_qt import AnalyzeTabQt

    analyze_controller = AnalyzeTabQt(
        on_pipeline_complete=lambda _out: status_log.append("Analyze pipeline completed.")
    )
    analyze_tab = analyze_controller.widget

    tabs.addTab(review_tab, "Review")
    tabs.addTab(analyze_tab, "Analyze")
    root_layout.addWidget(tabs, stretch=1)

    status_log = QTextEdit()
    status_log.setReadOnly(True)
    status_log.setMinimumHeight(120)
    status_log.setPlainText(
        "Phase 3 shell migrated to PySide6.\n"
        "Phase 4 Slice A complete: Analyze tab runs natively in Qt.\n"
        "Phase 4 Slice B/C/D complete: Review runtime shell, plot tabs, and tool dialogs are now Qt-hosted."
    )
    root_layout.addWidget(status_log)

    win.setCentralWidget(root)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
