"""PlotCanvas — single shared matplotlib figure with 1–4 stacked subplots.

Mockup target: the centre column's ``.canvas > .figure``. One ``Figure``
holding N vertically stacked subplots (each its own ``Axes`` with
independent X/Y — Q10), one persistent bottom ``MplToolbar``, one mono
coords readout. The ctxbar above (built by the Plotting section in
Phase 11) drives a single plot-TYPE switch that applies to all subplots.

Phase 9 scope: ship the canvas widget with a **placeholder renderer**
(simple ``ax.plot([1, 2, 3, …])`` per subplot) so it can be runtime-QA'd in
isolation. Phase 11 swaps the placeholder for the real controllers
(line / bar / scatter / distribution / heatmap).

API
---
* ``PlotCanvas(parent=None, *, subplots=2, max_subplots=4, figsize=(8, 6))``
* ``setPlotType(name)`` — ``"line" | "bar" | "scatter" | "distribution" | "heatmap"``;
  re-renders every subplot.
* ``plotType() -> str``
* ``addPanel() -> bool`` — adds one subplot, returns ``True`` on success,
  ``False`` if already at ``max_subplots``.
* ``removePanel(idx) -> bool`` — removes the subplot at ``idx`` (0-based);
  no-op if only one subplot remains.
* ``subplotCount() -> int``
* ``axes() -> list[Axes]`` — read-only snapshot for Phase-11 renderer wiring.
* ``setSubplotTitle(idx, title)`` — convenience for the per-subplot title.
* signals
  * ``plotTypeChanged(name)``
  * ``subplotCountChanged(n)``

Notes:
* All subplots share a single matplotlib ``Figure`` but **not** a shared
  axis (Q10): each ``Axes`` is created independently and gets its own
  X/Y limits.
* The canvas owns its `MplToolbar`; toolbar-driven pan/zoom/save apply
  to whichever subplot the user interacted with last (matplotlib default).
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402

try:
    from matplotlib.figure import Figure as _Figure
    from matplotlib.backends.backend_qtagg import (
        FigureCanvasQTAgg as _FigureCanvas, NavigationToolbar2QT as _NavToolbar,
    )
    _HAVE_MPL = True
except ImportError:  # pragma: no cover
    _HAVE_MPL = False

from widgets.mpl_toolbar import MplToolbar  # noqa: E402

_PLOT_TYPES = ("line", "bar", "scatter", "distribution", "heatmap")


if _HAVE_MPL:

    class PlotCanvas(QFrame):
        plotTypeChanged = Signal(str)
        subplotCountChanged = Signal(int)

        def __init__(self, parent: QWidget | None = None, *,
                     subplots: int = 2, max_subplots: int = 4,
                     figsize=(8.0, 6.0)) -> None:
            super().__init__(parent)
            self.setObjectName("PlotCanvas")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setFrameShape(QFrame.NoFrame)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            self._max_subplots = max(1, int(max_subplots))
            initial = max(1, min(int(subplots), self._max_subplots))
            self._plot_type = "line"
            self._subplot_titles: list[str] = []

            self.figure = _Figure(figsize=figsize, layout="constrained")
            self.figure.set_facecolor(theme.Colors.bg_panel)
            # Back-reference so v2 plot_style / apply_ax_style can find us.
            self.figure._plot_canvas = self  # type: ignore[attr-defined]

            self.canvas = _FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Hidden mpl nav we re-export via MplToolbar.
            self._nav = _NavToolbar(self.canvas, self, coordinates=False)
            self._nav.hide()
            self.toolbar = MplToolbar(self.canvas, self, nav=self._nav, owner=self)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)
            root.addWidget(self.canvas, 1)
            root.addWidget(self.toolbar, 0)

            # Build the initial subplots and render the placeholder.
            self._axes: list = []
            for _ in range(initial):
                self._append_axes(repaint=False)
            self._redraw_placeholder()

            self.setStyleSheet(self._build_qss())

        # ── API ──────────────────────────────────────────────────────────
        def setPlotType(self, name: str) -> None:
            if name not in _PLOT_TYPES:
                return
            if name == self._plot_type:
                return
            self._plot_type = name
            self._redraw_placeholder()
            self.plotTypeChanged.emit(name)

        def plotType(self) -> str:
            return self._plot_type

        def addPanel(self) -> bool:
            if len(self._axes) >= self._max_subplots:
                return False
            self._append_axes(repaint=False)
            self._redraw_placeholder()
            self.subplotCountChanged.emit(len(self._axes))
            return True

        def removePanel(self, idx: int) -> bool:
            if len(self._axes) <= 1:
                return False
            if not (0 <= idx < len(self._axes)):
                return False
            ax = self._axes.pop(idx)
            self.figure.delaxes(ax)
            if idx < len(self._subplot_titles):
                self._subplot_titles.pop(idx)
            self._reflow_axes()
            self._redraw_placeholder()
            self.subplotCountChanged.emit(len(self._axes))
            return True

        def subplotCount(self) -> int:
            return len(self._axes)

        def axes(self) -> list:
            return list(self._axes)

        def setSubplotTitle(self, idx: int, title: str) -> None:
            while len(self._subplot_titles) <= idx:
                self._subplot_titles.append("")
            self._subplot_titles[idx] = title or ""
            if 0 <= idx < len(self._axes):
                self._axes[idx].set_title(title or "", loc="left", fontsize=10,
                                          color=theme.Colors.text_primary)
                self.canvas.draw_idle()

        # ── internals ────────────────────────────────────────────────────
        def _append_axes(self, *, repaint: bool) -> None:
            self._axes.append(self.figure.add_subplot(1, 1, 1))
            self._reflow_axes()
            if repaint:
                self._redraw_placeholder()

        def _reflow_axes(self) -> None:
            n = len(self._axes)
            if n == 0:
                return
            # Re-position every axes onto an Nx1 grid. We can't use ``add_gridspec``
            # after the fact without re-creating, so use set_position with
            # explicit fractions; constrained_layout still tidies labels.
            top_pad = 0.04
            bot_pad = 0.08
            gap = 0.04
            usable = 1.0 - top_pad - bot_pad - (n - 1) * gap
            h = usable / n
            for i, ax in enumerate(self._axes):
                y = 1.0 - top_pad - (i + 1) * h - i * gap
                ax.set_position([0.10, y, 0.85, h])
            self.canvas.draw_idle()

        def _redraw_placeholder(self) -> None:
            """Phase-9 placeholder render. Phase 11 replaces this with the real
            controllers."""
            for i, ax in enumerate(self._axes):
                ax.clear()
                ax.set_facecolor(theme.Colors.bg_panel)
                for spine in ax.spines.values():
                    spine.set_color(theme.Colors.border)
                ax.tick_params(colors=theme.Colors.text_muted, labelsize=9)
                ax.grid(True, color=theme.Colors.border_subtle, linewidth=0.7)
                ax.set_axisbelow(True)
                title = (self._subplot_titles[i]
                         if i < len(self._subplot_titles) else "")
                if not title:
                    title = f"Subplot {i + 1} · {self._plot_type}"
                ax.set_title(title, loc="left", fontsize=10,
                             color=theme.Colors.text_primary)

                x = list(range(1, 9))
                ys_a = [1.0 + i * 0.5 + j * 0.1 for j in x]
                ys_b = [0.7 + i * 0.3 - j * 0.05 for j in x]
                c_a = theme.Colors.trace_1
                c_b = theme.Colors.trace_2

                t = self._plot_type
                if t == "line":
                    ax.plot(x, ys_a, color=c_a, linewidth=1.8, marker="o", markersize=4)
                    ax.plot(x, ys_b, color=c_b, linewidth=1.8, marker="o", markersize=4)
                elif t == "bar":
                    width = 0.4
                    ax.bar([v - width / 2 for v in x], ys_a, width=width, color=c_a)
                    ax.bar([v + width / 2 for v in x], ys_b, width=width, color=c_b)
                elif t == "scatter":
                    ax.scatter(x, ys_a, c=c_a, s=30)
                    ax.scatter(x, ys_b, c=c_b, s=30)
                elif t == "distribution":
                    # Two stacked histograms.
                    import random
                    random.seed(42 + i)
                    a = [random.gauss(0, 1) for _ in range(200)]
                    b = [random.gauss(0.7, 1.2) for _ in range(200)]
                    ax.hist(a, bins=20, color=c_a, alpha=0.6)
                    ax.hist(b, bins=20, color=c_b, alpha=0.6)
                elif t == "heatmap":
                    import numpy as np
                    rng = np.random.default_rng(0 + i)
                    ax.imshow(rng.random((8, 12)), aspect="auto",
                              cmap="viridis")
            self.canvas.draw_idle()

        def _build_qss(self) -> str:
            c, r = theme.Colors, theme.Radii
            return f"""
            QFrame#PlotCanvas {{
                background-color: {c.bg_panel};
                border: 1px solid {c.border_subtle};
                border-radius: {r.md}px;
            }}
            """

else:
    # Matplotlib missing — provide a stub so imports succeed in headless envs.
    class PlotCanvas(QFrame):  # type: ignore[no-redef]
        plotTypeChanged = Signal(str)
        subplotCountChanged = Signal(int)

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(kwargs.get("parent"))
            self.setObjectName("PlotCanvas")
            lay = QVBoxLayout(self)
            from PySide6.QtWidgets import QLabel
            lay.addWidget(QLabel("matplotlib not available", self))

        def setPlotType(self, _name: str) -> None: ...
        def plotType(self) -> str: return "line"
        def addPanel(self) -> bool: return False
        def removePanel(self, _idx: int) -> bool: return False
        def subplotCount(self) -> int: return 0
        def axes(self) -> list: return []
        def setSubplotTitle(self, _idx: int, _title: str) -> None: ...


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    host = QWidget()
    host.setWindowTitle("PlotCanvas — demo")
    host.resize(960, 640)
    outer = QVBoxLayout(host)
    outer.setContentsMargins(16, 16, 16, 16)
    outer.setSpacing(8)

    # ctxbar (mockup-shaped fake controls row)
    bar = QHBoxLayout()
    bar.addWidget(QLabel("Plot type:"))
    type_btns = {}
    for label, key in (("Line", "line"), ("Bar", "bar"),
                       ("Scatter", "scatter"), ("Distribution", "distribution"),
                       ("Heat Map", "heatmap")):
        b = QPushButton(label); b.setCheckable(True)
        type_btns[key] = b
        bar.addWidget(b)
    type_btns["line"].setChecked(True)
    bar.addStretch(1)

    add_btn = QPushButton("+ Add panel"); add_btn.setProperty("variant", "secondary")
    rm_btn = QPushButton("− Remove last")
    count_lbl = QLabel("subplots: 2")
    for w in (add_btn, rm_btn, count_lbl):
        bar.addWidget(w)
    outer.addLayout(bar)

    canvas = PlotCanvas(host, subplots=2, max_subplots=4)
    outer.addWidget(canvas, 1)

    def _on_type(key, btn):
        for k, b in type_btns.items():
            b.setChecked(k == key)
        canvas.setPlotType(key)
    for key, b in type_btns.items():
        b.clicked.connect(lambda _=False, k=key, _b=b: _on_type(k, _b))

    def _refresh_count():
        count_lbl.setText(f"subplots: {canvas.subplotCount()}")
    canvas.subplotCountChanged.connect(lambda _n: _refresh_count())

    add_btn.clicked.connect(canvas.addPanel)
    rm_btn.clicked.connect(lambda: canvas.removePanel(canvas.subplotCount() - 1))

    host.show()
    _sys.exit(app.exec())
