import importlib

import pytest


@pytest.mark.skipif(importlib.util.find_spec("PySide6") is None, reason="PySide6 not installed")
def test_qt_tool_dialogs_construct() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from well_viewer.qt_tools import BatchExportDialogQt, FigureExportEditorDialog

    fed = FigureExportEditorDialog()
    bed = BatchExportDialogQt()

    assert fed.dialog is not None
    assert bed.dialog is not None
    _ = app
