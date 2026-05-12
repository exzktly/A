"""TitleBar — the frameless-window chrome strip from the v2 mockup.

Brand tile + wordmark, a breadcrumb (``Workspace · Project / file.awd`` with a
mono "file chip"), a live "Saved" :class:`~widgets.status_dot.StatusDot`, then
right-aligned action :class:`~widgets.icon_button.IconButton`s. Dragging the bar
moves the window; double-click toggles maximize. Designed to sit at the top of a
``Qt.FramelessWindowHint`` ``QMainWindow``/``QWidget`` (it works fine inside a
normal window too — dragging is just inert there).

API
---
* ``TitleBar(parent=None, *, title="All-Well")``
* ``setBreadcrumb(parts, file_chip=None)`` — ``parts`` is a list of strings
  joined by "·"; ``file_chip`` (if given) is appended after a "/" in a mono chip.
* ``setSaved(bool)`` / ``setSavedText(text)``
* ``addAction(icon_name, tooltip="") -> IconButton`` — append a right-side button.
* ``windowButtonsVisible`` — set via ``setShowWindowButtons(bool)`` to add
  minimize / maximize / close buttons (off by default — many platforms keep the
  native ones even when frameless via the compositor).

Sizes are font-relative (DPI-aware); colours from ``theme`` tokens.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QHBoxLayout, QLabel, QSizePolicy, QWidget,
)

import theme  # noqa: E402
from widgets.brand_tile import BrandTile  # noqa: E402
from widgets.icon_button import IconButton  # noqa: E402
from widgets.status_dot import StatusDot  # noqa: E402


class TitleBar(QWidget):
    closeRequested = Signal()
    minimizeRequested = Signal()
    maximizeToggleRequested = Signal()

    def __init__(self, parent: QWidget | None = None, *, title: str = "All-Well") -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._press_offset = None

        h = theme.Spacing.sm
        lay = QHBoxLayout(self)
        lay.setContentsMargins(theme.Spacing.md, h, theme.Spacing.sm, h)
        lay.setSpacing(theme.Spacing.sm)

        self._brand = BrandTile(self)
        self._wordmark = QLabel(title, self)
        self._wordmark.setObjectName("TitleBarWordmark")
        lay.addWidget(self._brand)
        lay.addWidget(self._wordmark)

        # Breadcrumb area.
        self._sep1 = self._dot_sep()
        self._crumbs = QLabel("", self)
        self._crumbs.setObjectName("TitleBarCrumbs")
        self._slash = QLabel("/", self)
        self._slash.setObjectName("TitleBarFaint")
        self._slash.setVisible(False)
        self._file_chip = QLabel("", self)
        self._file_chip.setObjectName("TitleBarFileChip")
        self._file_chip.setVisible(False)
        lay.addWidget(self._sep1)
        lay.addWidget(self._crumbs)
        lay.addWidget(self._slash)
        lay.addWidget(self._file_chip)
        self._sep1.setVisible(False)

        # Saved indicator.
        self._saved_dot = StatusDot("success", self,
                                    diameter=max(8, round(self.fontMetrics().height() * 0.5)))
        self._saved_dot.setLabel("Saved")
        lay.addWidget(self._saved_dot)

        lay.addStretch(1)

        # Action buttons row.
        self._actions = QHBoxLayout()
        self._actions.setContentsMargins(0, 0, 0, 0)
        self._actions.setSpacing(theme.Spacing.xs)
        lay.addLayout(self._actions)

        # Optional window buttons.
        self._winbtns = QHBoxLayout()
        self._winbtns.setContentsMargins(0, 0, 0, 0)
        self._winbtns.setSpacing(theme.Spacing.xs)
        self._btn_min = IconButton("more-horizontal", tooltip="Minimize")  # placeholder glyph
        self._btn_min.setIconName("chevron-down")
        self._btn_max = IconButton("grid", tooltip="Maximize / restore")
        self._btn_close = IconButton("x", tooltip="Close")
        self._btn_min.clicked.connect(self.minimizeRequested)
        self._btn_max.clicked.connect(self.maximizeToggleRequested)
        self._btn_close.clicked.connect(self.closeRequested)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            self._winbtns.addWidget(b)
        self._winbtns_host = QWidget(self)
        self._winbtns_host.setLayout(self._winbtns)
        self._winbtns_host.setVisible(False)
        lay.addWidget(self._winbtns_host)

        # Wire window-control signals to the actual top-level window if any.
        self.closeRequested.connect(self._do_close)
        self.minimizeRequested.connect(self._do_minimize)
        self.maximizeToggleRequested.connect(self._do_toggle_max)

        self.setStyleSheet(self._build_qss())

    # ── API ──────────────────────────────────────────────────────────────
    def setTitle(self, text: str) -> None:
        self._wordmark.setText(text)

    def setBreadcrumb(self, parts, file_chip: str | None = None) -> None:
        parts = [str(p) for p in (parts or []) if str(p)]
        has_any = bool(parts) or bool(file_chip)
        self._sep1.setVisible(has_any)
        self._crumbs.setText("  ·  ".join(parts))
        self._crumbs.setVisible(bool(parts))
        if file_chip:
            self._file_chip.setText(str(file_chip))
            self._file_chip.setVisible(True)
            self._slash.setVisible(bool(parts))
        else:
            self._file_chip.setVisible(False)
            self._slash.setVisible(False)

    def setSaved(self, saved: bool) -> None:
        self._saved_dot.setStatus("success" if saved else "warn")
        self._saved_dot.setLabel("Saved" if saved else "Unsaved")

    def setSavedText(self, text: str) -> None:
        self._saved_dot.setLabel(text)

    def addAction(self, icon_name: str, tooltip: str = "", *, text: str = "") -> IconButton:  # type: ignore[override]
        btn = IconButton(icon_name, self, tooltip=tooltip, text=text)
        self._actions.addWidget(btn)
        return btn

    def setShowWindowButtons(self, show: bool) -> None:
        self._winbtns_host.setVisible(bool(show))

    # ── window drag ──────────────────────────────────────────────────────
    def _window(self):
        w = self.window()
        return w if w is not None and w is not self else None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            win = self._window()
            handle = win.windowHandle() if win is not None else None
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
            else:
                self._press_offset = event.globalPosition().toPoint() - (
                    win.frameGeometry().topLeft() if win else self.pos()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_offset is not None and (event.buttons() & Qt.LeftButton):
            win = self._window()
            if win is not None:
                win.move(event.globalPosition().toPoint() - self._press_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.maximizeToggleRequested.emit()
        super().mouseDoubleClickEvent(event)

    # ── window control fallbacks ─────────────────────────────────────────
    def _do_close(self) -> None:
        win = self._window()
        if win is not None:
            win.close()

    def _do_minimize(self) -> None:
        win = self._window()
        if win is not None:
            win.showMinimized()

    def _do_toggle_max(self) -> None:
        win = self._window()
        if win is None:
            return
        win.showNormal() if win.isMaximized() else win.showMaximized()

    # ── helpers ──────────────────────────────────────────────────────────
    def _dot_sep(self) -> QLabel:
        lbl = QLabel("·", self)
        lbl.setObjectName("TitleBarFaint")
        return lbl

    def _build_qss(self) -> str:
        c, t, r = theme.Colors, theme.Typography, theme.Radii
        return f"""
        #TitleBar {{
            background-color: {c.titlebar};
            border-bottom: 1px solid {c.border_subtle};
        }}
        QLabel#TitleBarWordmark {{
            color: {c.text_primary};
            font-size: {t.emph_size}px;
            font-weight: {t.semibold};
            background: transparent;
        }}
        QLabel#TitleBarCrumbs {{
            color: {c.text_secondary};
            font-size: {t.small_size}px;
            background: transparent;
        }}
        QLabel#TitleBarFaint {{ color: {c.text_faint}; background: transparent; }}
        QLabel#TitleBarFileChip {{
            color: {c.text_secondary};
            background-color: {c.panel};
            border: 1px solid {c.border_subtle};
            border-radius: {r.xs}px;
            padding: 2px 6px;
            font-family: {t.family_mono};
            font-size: {t.small_size}px;
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget as _QW,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    win = QMainWindow()
    win.setWindowTitle("TitleBar — demo")
    win.setWindowFlag(Qt.FramelessWindowHint, True)

    central = _QW()
    v = QVBoxLayout(central)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)

    tb = TitleBar(central, title="All-Well")
    tb.setBreadcrumb(["Workspace", "Plate 7"], file_chip="run_2026-05-12.awd")
    tb.setShowWindowButtons(True)
    tb.addAction("search", "Search (⌘K)")
    share = tb.addAction("download", "Export", text="Export")
    v.addWidget(tb)

    body = QLabel("(frameless window — drag the title bar, double-click to maximize)")
    body.setObjectName("Secondary")
    body.setAlignment(Qt.AlignCenter)
    body.setMinimumHeight(220)
    v.addWidget(body, 1)
    win.setCentralWidget(central)

    win.resize(820, 360)
    win.show()
    _sys.exit(app.exec())
