"""Qt-native tool dialogs used by runtime_app_qt migration slice."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExportStyleSettings:
    title_size: int = 14
    axis_label_size: int = 12
    tick_size: int = 10
    dpi: int = 300


class FigureExportEditorDialog:
    def __init__(self, parent=None, settings: ExportStyleSettings | None = None):
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QSpinBox,
            QVBoxLayout,
        )

        self._settings = settings or ExportStyleSettings()
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Figure Export Editor")

        layout = QVBoxLayout(self.dialog)
        form = QFormLayout()
        layout.addLayout(form)

        self._title = QSpinBox(); self._title.setRange(6, 64); self._title.setValue(self._settings.title_size)
        self._axis = QSpinBox(); self._axis.setRange(6, 64); self._axis.setValue(self._settings.axis_label_size)
        self._tick = QSpinBox(); self._tick.setRange(6, 64); self._tick.setValue(self._settings.tick_size)
        self._dpi = QSpinBox(); self._dpi.setRange(72, 1200); self._dpi.setValue(self._settings.dpi)

        form.addRow("Title size", self._title)
        form.addRow("Axis label size", self._axis)
        form.addRow("Tick size", self._tick)
        form.addRow("Export DPI", self._dpi)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.dialog.accept)
        btns.rejected.connect(self.dialog.reject)
        layout.addWidget(btns)

    def exec(self) -> ExportStyleSettings | None:
        accepted = self.dialog.exec()
        if not accepted:
            return None
        return ExportStyleSettings(
            title_size=int(self._title.value()),
            axis_label_size=int(self._axis.value()),
            tick_size=int(self._tick.value()),
            dpi=int(self._dpi.value()),
        )


class BatchExportDialogQt:
    def __init__(self, parent=None):
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QLineEdit,
            QVBoxLayout,
        )

        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Batch Export")

        layout = QVBoxLayout(self.dialog)
        form = QFormLayout()
        layout.addLayout(form)

        self._prefix = QLineEdit("export")
        self._include_plots = QCheckBox(); self._include_plots.setChecked(True)
        self._include_csv = QCheckBox(); self._include_csv.setChecked(True)

        form.addRow("Filename prefix", self._prefix)
        form.addRow("Include plots", self._include_plots)
        form.addRow("Include CSV", self._include_csv)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.dialog.accept)
        btns.rejected.connect(self.dialog.reject)
        layout.addWidget(btns)

    def exec(self) -> dict | None:
        accepted = self.dialog.exec()
        if not accepted:
            return None
        return {
            "prefix": self._prefix.text().strip() or "export",
            "include_plots": bool(self._include_plots.isChecked()),
            "include_csv": bool(self._include_csv.isChecked()),
        }
