import importlib

import pytest


@pytest.mark.skipif(importlib.util.find_spec("PySide6") is None, reason="PySide6 not installed")
def test_qt_shell_slices_construct() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from analyze_tab_qt import AnalyzeTabQt
    from well_viewer.runtime_app_qt import WellViewerRuntimeQt

    analyze = AnalyzeTabQt()
    review = WellViewerRuntimeQt()

    assert analyze.widget is not None
    assert review.widget is not None

    # Keep app alive for this scope only.
    _ = app
