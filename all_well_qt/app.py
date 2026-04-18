"""QApplication boot: load fonts, create ThemeManager, launch MainWindow."""

from __future__ import annotations
import sys

import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtWidgets import QApplication

from .theme.fonts import register_fonts
from .theme.manager import ThemeManager
from .theme.tokens import DEFAULT_PALETTE
from .theme.qss import build_qss
from .theme.tokens import PALETTES


def run(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("All-Well")
    app.setOrganizationName("AllWell")

    register_fonts()

    # Bootstrap: apply initial QSS before any window is created
    app.setStyleSheet(build_qss(PALETTES[DEFAULT_PALETTE]))

    theme = ThemeManager(app)

    from .main_window import MainWindow
    win = MainWindow()
    win.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
