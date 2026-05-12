"""PlotCard — an embedded matplotlib figure in a v2 card with a custom toolbar.

A ``QFrame`` (``#Panel`` chrome) containing a ``FigureCanvasQTAgg`` above a
slim toolbar row of :class:`~widgets.icon_button.IconButton`s grouped the
matplotlib way (home / back–forward / pan–zoom / save) plus a right-aligned
mono ``x = … · y = …`` readout. The toolbar drives a hidden
``NavigationToolbar2QT`` so we get matplotlib's real handlers with our own UI.

The figure / axes are styled from ``theme`` tokens (dark panel facecolor,
token grid + spines + tick/label colours) every time you ask for an axes via
:meth:`add_subplot`; call :meth:`style_axes` after drawing your own axes.

API
---
* ``PlotCard(parent=None, *, figsize=(4, 3))``
* ``figure`` — the ``matplotlib.figure.Figure``.
* ``add_subplot(*args, **kwargs)`` — like ``Figure.add_subplot`` but pre-styled.
* ``style_axes(ax)`` — apply the token look to an existing Axes.
* ``draw()`` — redraw the canvas.

matplotlib is an existing dependency of this project; if it's somehow missing
the module still imports (``PlotCard`` becomes ``None``) so ``import widgets.*``
elsewhere doesn't explode.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout,
)

import theme  # noqa: E402
from widgets.icon_button import IconButton  # noqa: E402

try:  # matplotlib is a project dependency; degrade gracefully if absent.
    import matplotlib  # noqa: E402
    matplotlib.use("QtAgg", force=False)
    from matplotlib.backends.backend_qtagg import (  # noqa: E402
        FigureCanvasQTAgg as _FigureCanvas, NavigationToolbar2QT as _NavToolbar,
    )
    from matplotlib.figure import Figure as _Figure  # noqa: E402
    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False


def apply_axes_style(ax) -> None:
    """Apply the v2 token look to a matplotlib Axes (module-level helper)."""
    c = theme.Colors
    ax.set_facecolor(c.plot_bg)
    fig = ax.figure
    if fig is not None:
        fig.set_facecolor(c.plot_bg)
    for side, spine in ax.spines.items():
        if side in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(c.plot_spine)
            spine.set_linewidth(0.8)
    ax.tick_params(colors=c.text_muted, labelsize=theme.Typography.caption_size)
    ax.xaxis.label.set_color(c.text_secondary)
    ax.yaxis.label.set_color(c.text_secondary)
    if ax.get_title():
        ax.title.set_color(c.text_primary)
    ax.grid(True, color=c.plot_grid, linewidth=0.7, linestyle="-")
    ax.set_axisbelow(True)


if _HAVE_MPL:

    class PlotCard(QFrame):
        def __init__(self, parent=None, *, figsize=(4.0, 3.0)) -> None:
            super().__init__(parent)
            self.setObjectName("Panel")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setFrameShape(QFrame.NoFrame)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            self.figure = _Figure(figsize=figsize, layout="constrained")
            self.figure.set_facecolor(theme.Colors.plot_bg)
            self.canvas = _FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Hidden real toolbar — we reuse its handlers, not its UI.
            self._nav = _NavToolbar(self.canvas, self, coordinates=False)
            self._nav.hide()

            root = QVBoxLayout(self)
            m = theme.Spacing.md
            root.setContentsMargins(m, m, m, theme.Spacing.sm)
            root.setSpacing(theme.Spacing.sm)
            root.addWidget(self.canvas, 1)
            root.addWidget(self._build_toolbar())

            self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
            self.setStyleSheet(self._build_qss())

        # ── public API ───────────────────────────────────────────────────
        def add_subplot(self, *args, **kwargs):
            ax = self.figure.add_subplot(*(args or (111,)), **kwargs)
            self.style_axes(ax)
            return ax

        @staticmethod
        def style_axes(ax) -> None:
            apply_axes_style(ax)

        def draw(self) -> None:
            self.canvas.draw_idle()

        def clear(self) -> None:
            self.figure.clear()
            self.figure.set_facecolor(theme.Colors.plot_bg)
            self.draw()

        # ── toolbar ──────────────────────────────────────────────────────
        def _build_toolbar(self) -> QFrame:
            bar = QFrame(self)
            bar.setObjectName("PlotCardToolbar")
            bar.setAttribute(Qt.WA_StyledBackground, True)
            lay = QHBoxLayout(bar)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(theme.Spacing.xs)

            home = IconButton("home", tooltip="Reset view")
            back = IconButton("arrow-left", tooltip="Back")
            fwd = IconButton("arrow-right", tooltip="Forward")
            pan = IconButton("move", tooltip="Pan", checkable=True)
            zoom = IconButton("zoom-in", tooltip="Zoom to rectangle", checkable=True)
            save = IconButton("download", tooltip="Save figure…")

            grp = QButtonGroup(bar)
            grp.setExclusive(False)  # allow toggling both off
            grp.addButton(pan)
            grp.addButton(zoom)

            home.clicked.connect(self._nav.home)
            back.clicked.connect(self._nav.back)
            fwd.clicked.connect(self._nav.forward)
            save.clicked.connect(self._nav.save_figure)

            def _toggle_pan(on: bool):
                if on and zoom.isChecked():
                    zoom.setChecked(False)
                # NavigationToolbar2QT.pan() toggles internally; only call to enter.
                if on != (getattr(self._nav, "mode", "") == "pan"):
                    self._nav.pan()

            def _toggle_zoom(on: bool):
                if on and pan.isChecked():
                    pan.setChecked(False)
                if on != (getattr(self._nav, "mode", "") == "zoom rect"):
                    self._nav.zoom()

            pan.toggled.connect(_toggle_pan)
            zoom.toggled.connect(_toggle_zoom)

            for w in (home, back, fwd):
                lay.addWidget(w)
            lay.addWidget(self._sep())
            lay.addWidget(pan)
            lay.addWidget(zoom)
            lay.addWidget(self._sep())
            lay.addWidget(save)
            lay.addStretch(1)
            self._coords = QLabel("x = —   ·   y = —", bar)
            self._coords.setObjectName("PlotCardCoords")
            lay.addWidget(self._coords)
            return bar

        def _sep(self) -> QFrame:
            f = QFrame(self)
            f.setObjectName("PlotCardSep")
            f.setFrameShape(QFrame.VLine)
            f.setFixedWidth(1)
            return f

        def _on_mouse_move(self, event) -> None:
            if event.inaxes and event.xdata is not None and event.ydata is not None:
                self._coords.setText(f"x = {event.xdata:.3g}   ·   y = {event.ydata:.3g}")
            else:
                self._coords.setText("x = —   ·   y = —")

        def _build_qss(self) -> str:
            c, t, r = theme.Colors, theme.Typography, theme.Radii
            return f"""
            QFrame#Panel {{
                background-color: {c.panel};
                border: 1px solid {c.border_subtle};
                border-radius: {r.md}px;
            }}
            QFrame#PlotCardToolbar {{ background: transparent; }}
            QFrame#PlotCardSep {{ background-color: {c.border_subtle}; border: none; }}
            QLabel#PlotCardCoords {{
                color: {c.text_muted};
                font-family: {t.family_mono};
                font-size: {t.small_size}px;
                background: transparent;
            }}
            """

else:  # pragma: no cover - matplotlib unavailable
    PlotCard = None  # type: ignore


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("PlotCard — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)
    title = QLabel("PlotCard")
    title.setObjectName("Title")
    lay.addWidget(title)

    if PlotCard is None:
        lay.addWidget(QLabel("matplotlib is not installed — PlotCard unavailable."))
    else:
        card = PlotCard(figsize=(5, 3.2))
        ax = card.add_subplot(111)
        import math
        xs = [i * 0.1 for i in range(120)]
        for k, color in enumerate(theme.Colors.trace):
            ax.plot(xs, [math.sin(x + k * 0.6) * (1.0 - 0.12 * k) for x in xs],
                    color=color, linewidth=1.6, label=f"Well {chr(65 + k)}01")
        ax.axhline(0.0, color=theme.Colors.threshold, linestyle="--", linewidth=1.0)
        ax.set_xlabel("Time (h)")
        ax.set_ylabel("Signal")
        ax.set_title("Mean fluorescence")
        leg = ax.legend(facecolor=theme.Colors.panel, edgecolor=theme.Colors.border_subtle,
                        labelcolor=theme.Colors.text_secondary, fontsize=theme.Typography.caption_size)
        card.style_axes(ax)
        card.draw()
        lay.addWidget(card, 1)

    root.resize(640, 460)
    root.show()
    _sys.exit(app.exec())
