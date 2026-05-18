"""MplToolbar — a styled matplotlib navigation toolbar.

A slim ``QWidget`` row of :class:`~widgets.icon_button.IconButton`s grouped the
matplotlib way (home · back/forward · pan/zoom · save) plus a right-aligned mono
``x = … · y = …`` coordinate readout. It drives a hidden ``NavigationToolbar2QT``
so we get matplotlib's real handlers behind our own UI.

Use it standalone over any ``FigureCanvasQTAgg`` (e.g. inside a hover overlay), or
let :class:`~widgets.plot_card.PlotCard` embed one for you.

API
---
* ``MplToolbar(canvas, parent=None, *, nav=None, owner=None)`` — ``canvas`` is the
  ``FigureCanvasQTAgg``; pass an existing ``NavigationToolbar2QT`` as ``nav`` (or
  one is created, hidden, parented to ``owner`` or ``parent``).
* ``nav`` — the underlying ``NavigationToolbar2QT`` (read-only).
* ``setCoordinatesVisible(bool)`` / ``coordinatesVisible()`` — the ``x = … · y = …`` label.
* ``home()`` / ``back()`` / ``forward()`` / ``save()`` — proxy the handlers (so the
  toolbar can be driven externally too).

matplotlib is an existing project dependency; if it's missing the module still
imports (``MplToolbar`` becomes ``None``) so ``import widgets.*`` doesn't explode.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QToolTip, QWidget,
)

import theme  # noqa: E402
from widgets.icon_button import IconButton  # noqa: E402

try:  # matplotlib is a project dependency; degrade gracefully if absent.
    import matplotlib  # noqa: E402
    matplotlib.use("QtAgg", force=False)
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as _NavToolbar  # noqa: E402
    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False


if _HAVE_MPL:

    class MplToolbar(QWidget):
        def __init__(self, canvas, parent=None, *, nav=None, owner=None) -> None:
            super().__init__(parent)
            self.setObjectName("MplToolbar")
            self.canvas = canvas
            self._nav = nav if nav is not None else _NavToolbar(
                canvas, owner or parent or self, coordinates=False)
            try:
                self._nav.hide()
            except Exception:
                pass

            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(theme.Spacing.xs)

            self._home = IconButton("home", tooltip="Reset view")
            self._back = IconButton("arrow-left", tooltip="Back")
            self._fwd = IconButton("arrow-right", tooltip="Forward")
            self._pan = IconButton("move", tooltip="Pan", checkable=True)
            self._zoom = IconButton("zoom-in", tooltip="Zoom to rectangle", checkable=True)
            self._save = IconButton("download", tooltip="Save figure…")

            grp = QButtonGroup(self)
            grp.setExclusive(False)   # allow toggling both modes off
            grp.addButton(self._pan)
            grp.addButton(self._zoom)

            self._home.clicked.connect(self.home)
            self._back.clicked.connect(self.back)
            self._fwd.clicked.connect(self.forward)
            self._save.clicked.connect(self.save)
            self._pan.toggled.connect(self._on_pan_toggled)
            self._zoom.toggled.connect(self._on_zoom_toggled)

            for w in (self._home, self._back, self._fwd):
                lay.addWidget(w)
            lay.addWidget(self._sep())
            lay.addWidget(self._pan)
            lay.addWidget(self._zoom)
            lay.addWidget(self._sep())
            lay.addWidget(self._save)
            lay.addStretch(1)

            self._coords = QLabel("x = —   ·   y = —", self)
            self._coords.setObjectName("MplToolbarCoords")
            lay.addWidget(self._coords)

            # Store the cids so we can mpl_disconnect on destroy — without
            # that the closures outlive the QLabel they update and emit
            # ``RuntimeError: wrapped C/C++ object … deleted`` in stderr
            # when the toolbar is destroyed but the canvas survives
            # (e.g. lazy tab rebuild).
            self._motion_cid = None
            self._leave_cid = None
            try:
                self._motion_cid = self.canvas.mpl_connect(
                    "motion_notify_event", self._on_mouse_move
                )
                self._leave_cid = self.canvas.mpl_connect(
                    "figure_leave_event", self._on_figure_leave
                )
            except Exception:
                pass
            self.setStyleSheet(self._qss())

        def closeEvent(self, event):  # noqa: N802 — Qt naming
            self._detach_canvas()
            try:
                super().closeEvent(event)
            except Exception:
                pass

        def deleteLater(self):  # noqa: N802 — Qt naming
            self._detach_canvas()
            super().deleteLater()

        def _detach_canvas(self) -> None:
            for attr in ("_motion_cid", "_leave_cid"):
                cid = getattr(self, attr, None)
                if cid is None:
                    continue
                setattr(self, attr, None)
                try:
                    self.canvas.mpl_disconnect(cid)
                except Exception:
                    pass

        # ── proxy the matplotlib handlers ───────────────────────────────────
        @property
        def nav(self):
            return self._nav

        def home(self) -> None:
            self._nav.home()

        def back(self) -> None:
            self._nav.back()

        def forward(self) -> None:
            self._nav.forward()

        def save(self) -> None:
            self._nav.save_figure()

        # ── pan / zoom (NavigationToolbar2QT toggles these internally) ───────
        def _on_pan_toggled(self, on: bool) -> None:
            if on and self._zoom.isChecked():
                self._zoom.setChecked(False)
            if on != (getattr(self._nav, "mode", "") == "pan"):
                self._nav.pan()

        def _on_zoom_toggled(self, on: bool) -> None:
            if on and self._pan.isChecked():
                self._pan.setChecked(False)
            if on != (getattr(self._nav, "mode", "") == "zoom rect"):
                self._nav.zoom()

        # ── coordinate readout ──────────────────────────────────────────────
        def setCoordinatesVisible(self, visible: bool) -> None:
            self._coords.setVisible(bool(visible))

        def coordinatesVisible(self) -> bool:
            return self._coords.isVisible()

        def _on_mouse_move(self, event) -> None:
            if event.inaxes and event.xdata is not None and event.ydata is not None:
                text = f"x = {event.xdata:.3g}   ·   y = {event.ydata:.3g}"
                self._coords.setText(text)
                # Mirror the read-out as a hover tooltip on the canvas
                # so the value is visible without scrolling the page
                # down to find the bottom-right read-out. matplotlib's
                # `event.x` / `event.y` are canvas pixel coords with
                # Y measured from the bottom; Qt's coords are from the
                # top, hence the height flip.
                try:
                    canvas_h = int(self.canvas.height())
                    cx = int(event.x)
                    cy = canvas_h - int(event.y)
                    # +14/+14 puts the tooltip near the cursor without
                    # sitting under it.
                    pt = self.canvas.mapToGlobal(QPoint(cx + 14, cy + 14))
                    QToolTip.showText(pt, text, self.canvas)
                except Exception:
                    pass
            else:
                self._coords.setText("x = —   ·   y = —")
                # Off-axes → hide the tooltip immediately.
                try:
                    QToolTip.hideText()
                except Exception:
                    pass

        def _on_figure_leave(self, _event) -> None:
            """Hide the hover tooltip when the cursor leaves the canvas."""
            self._coords.setText("x = —   ·   y = —")
            try:
                QToolTip.hideText()
            except Exception:
                pass

        # ── chrome ──────────────────────────────────────────────────────────
        def _sep(self) -> QFrame:
            f = QFrame(self)
            f.setObjectName("MplToolbarSep")
            f.setFrameShape(QFrame.VLine)
            f.setFixedWidth(1)
            return f

        def _qss(self) -> str:
            c, t = theme.Colors, theme.Typography
            return f"""
            QWidget#MplToolbar {{ background: transparent; }}
            QFrame#MplToolbarSep {{ background-color: {c.border_subtle}; border: none; }}
            QLabel#MplToolbarCoords {{
                color: {c.text_muted};
                font-family: {t.family_mono};
                font-size: {t.small_size}px;
                background: transparent;
            }}
            """

else:  # pragma: no cover - matplotlib unavailable
    MplToolbar = None  # type: ignore


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("MplToolbar — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)
    title = QLabel("MplToolbar")
    title.setObjectName("Title")
    lay.addWidget(title)

    if MplToolbar is None:
        lay.addWidget(QLabel("matplotlib is not installed — MplToolbar unavailable."))
    else:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FC
        from matplotlib.figure import Figure as _F
        fig = _F(figsize=(5, 3), layout="constrained")
        ax = fig.add_subplot(111)
        import math
        xs = [i * 0.1 for i in range(120)]
        ax.plot(xs, [math.sin(x) for x in xs], linewidth=1.6)
        ax.set_xlabel("x"); ax.set_ylabel("sin x")
        canvas = _FC(fig)
        lay.addWidget(canvas, 1)
        lay.addWidget(MplToolbar(canvas))

    root.resize(640, 460)
    root.show()
    _sys.exit(app.exec())
