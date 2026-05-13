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

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402
from widgets.mpl_toolbar import MplToolbar  # noqa: E402

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


def _plot_palette(mode: str):
    """Trace-colour cycle for ``"screen"`` (dark) or ``"publication"`` (light)."""
    if mode == "publication":
        return list(getattr(theme, "TRACE_PUB", theme.Colors.trace))
    return list(theme.Colors.trace)


def _plot_tokens(mode: str):
    """(bg, fg, muted, grid, spine) colours for the given plot theme."""
    if mode == "publication" and hasattr(theme, "CPub"):
        p = theme.CPub
        return (p.bg, p.text, getattr(p, "text_muted", p.text), p.grid, p.spine)
    c = theme.Colors
    return (c.plot_bg, c.text_primary, c.text_muted, c.plot_grid, c.plot_spine)


def _make_segmented(items, parent=None, *, current=None):
    """Build a :class:`~widgets.segmented_control.SegmentedControl` from a list of
    ``(text, data)`` pairs (it has no list constructor — segments are added one at
    a time) and optionally select *current* by data. Returns ``None`` if the
    widget isn't importable."""
    try:
        from widgets.segmented_control import SegmentedControl
    except Exception:  # pragma: no cover
        return None
    sc = SegmentedControl(parent)
    for text, data in items:
        sc.addSegment(text, data=data)
    if current is not None:
        sc.setCurrentByData(current)
    return sc


def apply_axes_style(ax, mode: str = "screen") -> None:
    """Apply the v2 token look (``"screen"``) or the publication look
    (``"publication"`` — white bg, ``theme.CPub`` ink) to a matplotlib Axes."""
    bg, fg, muted, grid, spine = _plot_tokens(mode)
    sec = fg if mode == "publication" else theme.Colors.text_secondary
    ax.set_facecolor(bg)
    fig = ax.figure
    if fig is not None:
        fig.set_facecolor(bg)
    for side, sp in ax.spines.items():
        if side in ("top", "right"):
            sp.set_visible(False)
        else:
            sp.set_color(spine)
            sp.set_linewidth(0.8)
    ax.tick_params(colors=muted, labelsize=theme.Typography.caption_size)
    ax.xaxis.label.set_color(sec)
    ax.yaxis.label.set_color(sec)
    if ax.get_title():
        ax.title.set_color(fg)
    ax.grid(True, color=grid, linewidth=0.7, linestyle="-")
    ax.set_axisbelow(True)


if _HAVE_MPL:

    class PlotCard(QFrame):
        statsChanged = Signal(str, str)   # (statistic, error-band)
        plotThemeChanged = Signal(str)    # "screen" | "publication"

        def __init__(self, parent=None, *, figsize=(4.0, 3.0), constrained=True) -> None:
            super().__init__(parent)
            self.setObjectName("Panel")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setFrameShape(QFrame.NoFrame)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Decision #2: the canonical/exported state is "publication" (white,
            # CPub/TRACE_PUB); "screen" (dark token set) is a per-card live
            # preview only — a "preview only" chip shows whenever it's active.
            self._plot_theme = "publication"
            self._stat = "Mean"
            self._error = "SEM"
            self._stats_pop = None

            self.figure = _Figure(figsize=figsize,
                                  layout=("constrained" if constrained else None))
            self.figure.set_facecolor(_plot_tokens(self._plot_theme)[0])
            self.canvas = _FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Hidden real toolbar — we reuse its handlers, not its UI.
            self._nav = _NavToolbar(self.canvas, self, coordinates=False)
            self._nav.hide()
            self.toolbar = MplToolbar(self.canvas, self, nav=self._nav, owner=self)

            root = QVBoxLayout(self)
            m = theme.Spacing.md
            root.setContentsMargins(m, m, m, theme.Spacing.sm)
            root.setSpacing(theme.Spacing.sm)
            root.addWidget(self._build_header())
            root.addWidget(self._build_controls_row())
            root.addWidget(self.canvas, 1)
            root.addWidget(self.toolbar)

            self.setStyleSheet(self._build_qss())
            self._sync_theme_ui()

        # ── public API ───────────────────────────────────────────────────
        def add_subplot(self, *args, **kwargs):
            ax = self.figure.add_subplot(*(args or (111,)), **kwargs)
            self.style_axes(ax)
            return ax

        def style_axes(self, ax) -> None:
            apply_axes_style(ax, self._plot_theme)

        def draw(self) -> None:
            self.canvas.draw_idle()

        def clear(self) -> None:
            self.figure.clear()
            self.figure.set_facecolor(_plot_tokens(self._plot_theme)[0])
            self.draw()

        # ── figure header ────────────────────────────────────────────────
        def setFigureTitle(self, text: str) -> None:
            self._title_lbl.setText(str(text))
            self._title_lbl.setVisible(bool(text))

        def setStatsChipVisible(self, visible: bool) -> None:
            """Hide the ``Mean · SEM`` chip (e.g. on a tab whose stats UI lives
            elsewhere). The popover/stat/error API still works programmatically."""
            self._stats_chip.setVisible(bool(visible))

        def setThemeToggleVisible(self, visible: bool) -> None:
            """Hide the in-header ``Publication ↔ Screen`` toggle (and the
            'preview only' chip). ``setPlotTheme`` still works programmatically."""
            if getattr(self, "_theme_sc", None) is not None:
                self._theme_sc.setVisible(bool(visible))
            if not visible:
                self._preview_chip.setVisible(False)
            else:
                self._sync_theme_ui()

        def headerWidget(self) -> QWidget:
            return self._header

        def setLeftHeaderWidget(self, widget) -> None:
            """Mount *widget* at the far left of the header (e.g. a per-card
            view-switcher ``SegmentedControl``). Pass ``None`` to clear."""
            lay = self._left_holder.layout()
            while lay.count():
                it = lay.takeAt(0)
                w = it.widget()
                if w is not None:
                    w.setParent(None)
            if widget is not None:
                lay.addWidget(widget)
            self._left_holder.setVisible(widget is not None)

        def leftHeaderWidget(self) -> QWidget:
            return self._left_holder

        def setControlsWidget(self, widget) -> None:
            """Mount *widget* in the controls row beneath the header (e.g. the
            error-band / replicates-vs-FOV ``SegmentedControl``s). ``None`` clears."""
            lay = self._controls_row.layout()
            while lay.count():
                it = lay.takeAt(0)
                w = it.widget()
                if w is not None:
                    w.setParent(None)
            if widget is not None:
                lay.addWidget(widget)
                lay.addStretch(1)
            self._controls_row.setVisible(widget is not None)

        def controlsWidget(self) -> QWidget:
            return self._controls_row

        def _build_controls_row(self) -> QWidget:
            self._controls_row = QWidget(self)
            self._controls_row.setObjectName("PlotCardControls")
            self._controls_row.setAttribute(Qt.WA_StyledBackground, True)
            cl = QHBoxLayout(self._controls_row)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(theme.Spacing.sm)
            self._controls_row.setVisible(False)
            return self._controls_row

        def _build_header(self) -> QWidget:
            self._header = QWidget(self)
            self._header.setObjectName("PlotCardHeader")
            self._header.setAttribute(Qt.WA_StyledBackground, True)
            lay = QHBoxLayout(self._header)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(theme.Spacing.sm)

            self._left_holder = QWidget(self._header)
            self._left_holder.setObjectName("PlotCardLeftSlot")
            self._left_holder.setAttribute(Qt.WA_StyledBackground, True)
            _ll = QHBoxLayout(self._left_holder)
            _ll.setContentsMargins(0, 0, 0, 0)
            _ll.setSpacing(theme.Spacing.xs)
            self._left_holder.setVisible(False)
            lay.addWidget(self._left_holder)

            self._title_lbl = QLabel("", self._header)
            self._title_lbl.setObjectName("PlotCardTitle")
            self._title_lbl.setVisible(False)
            lay.addWidget(self._title_lbl)
            lay.addStretch(1)

            # "preview only" chip — shown when the (non-canonical) "screen"
            # theme is active, so it's clear the on-screen look isn't exported.
            self._preview_chip = QLabel("preview only", self._header)
            self._preview_chip.setObjectName("PlotCardPreviewChip")
            self._preview_chip.setVisible(False)
            lay.addWidget(self._preview_chip)

            # Screen ↔ Publication toggle.
            self._theme_sc = _make_segmented(
                [("Publication", "publication"), ("Screen", "screen")],
                self._header, current=self._plot_theme)
            if self._theme_sc is not None:
                self._theme_sc.setObjectName("PlotCardThemeToggle")
                self._theme_sc.currentChanged.connect(
                    lambda *_a: self.setPlotTheme(self._theme_sc.currentData() or "publication"))
                lay.addWidget(self._theme_sc)

            self._stats_chip = QPushButton(self._chip_text(), self._header)
            self._stats_chip.setObjectName("PlotCardStatsChip")
            self._stats_chip.setCursor(Qt.PointingHandCursor)
            self._stats_chip.clicked.connect(self._open_stats_popover)
            lay.addWidget(self._stats_chip)
            return self._header

        def _sync_theme_ui(self) -> None:
            self._preview_chip.setVisible(self._plot_theme == "screen")
            if getattr(self, "_theme_sc", None) is not None:
                try:
                    self._theme_sc.blockSignals(True)
                    self._theme_sc.setCurrentByData(self._plot_theme)
                finally:
                    self._theme_sc.blockSignals(False)

        def _chip_text(self) -> str:
            return f"{self._stat} · {self._error}"

        def _open_stats_popover(self) -> None:
            from widgets.popover import Popover
            pop = Popover(self)
            content = QWidget()
            v = QVBoxLayout(content)
            v.setContentsMargins(theme.Spacing.sm, theme.Spacing.sm,
                                 theme.Spacing.sm, theme.Spacing.sm)
            v.setSpacing(theme.Spacing.sm)
            v.addWidget(QLabel("Statistic"))
            stat_sc = _make_segmented([("Mean", "Mean"), ("Median", "Median")], current=self._stat)
            if stat_sc is not None:
                stat_sc.currentChanged.connect(lambda *_a: self._set_stat(stat_sc.currentData()))
                v.addWidget(stat_sc)
            v.addWidget(QLabel("Error band"))
            err_sc = _make_segmented([("SEM", "SEM"), ("SD", "SD"),
                                      ("95% CI", "95% CI"), ("None", "None")], current=self._error)
            if err_sc is not None:
                err_sc.currentChanged.connect(lambda *_a: self._set_error(err_sc.currentData()))
                v.addWidget(err_sc)
            pop.setContentWidget(content)
            self._stats_pop = pop
            pop.popup(self._stats_chip, side="bottom", align="end")

        def _set_stat(self, value) -> None:
            if value and value != self._stat:
                self._stat = str(value)
                self._stats_chip.setText(self._chip_text())
                self.statsChanged.emit(self._stat, self._error)

        def _set_error(self, value) -> None:
            if value and value != self._error:
                self._error = str(value)
                self._stats_chip.setText(self._chip_text())
                self.statsChanged.emit(self._stat, self._error)

        def statistic(self) -> str:
            return self._stat

        def errorBand(self) -> str:
            return self._error

        # ── plot theme ───────────────────────────────────────────────────
        def plotTheme(self) -> str:
            return self._plot_theme

        def traceColors(self) -> list:
            return _plot_palette(self._plot_theme)

        def setPlotTheme(self, mode: str) -> None:
            mode = "publication" if str(mode).lower().startswith("pub") else "screen"
            if mode == self._plot_theme:
                return
            self._plot_theme = mode
            self._apply_rcparams()
            palette = _plot_palette(mode)
            bg = _plot_tokens(mode)[0]
            self.figure.set_facecolor(bg)
            for ax in self.figure.axes:
                apply_axes_style(ax, mode)
                # best-effort: recolour the visible traces with the new cycle
                idx = 0
                for line in ax.get_lines():
                    lbl = line.get_label() or ""
                    if isinstance(lbl, str) and lbl.startswith("_"):
                        continue
                    line.set_color(palette[idx % len(palette)])
                    idx += 1
                leg = ax.get_legend()
                if leg is not None:
                    fg = _plot_tokens(mode)[1]
                    leg.get_frame().set_facecolor(bg)
                    for txt in leg.get_texts():
                        txt.set_color(fg)
            self.setStyleSheet(self._build_qss())
            self._sync_theme_ui()
            self.draw()
            self.plotThemeChanged.emit(mode)

        def _apply_rcparams(self) -> None:
            bg, fg, muted, grid, spine = _plot_tokens(self._plot_theme)
            try:
                from cycler import cycler
                matplotlib.rcParams.update({
                    "figure.facecolor": bg, "axes.facecolor": bg,
                    "axes.edgecolor": spine, "axes.labelcolor": fg,
                    "text.color": fg, "xtick.color": muted, "ytick.color": muted,
                    "grid.color": grid,
                    "axes.prop_cycle": cycler(color=_plot_palette(self._plot_theme)),
                })
            except Exception:
                pass

        def _build_qss(self) -> str:
            c, t, r = theme.Colors, theme.Typography, theme.Radii
            return f"""
            QFrame#Panel {{
                background-color: {c.panel};
                border: 1px solid {c.border_subtle};
                border-radius: {r.md}px;
            }}
            QWidget#PlotCardHeader, QWidget#PlotCardControls,
            QWidget#PlotCardLeftSlot {{ background: transparent; }}
            QLabel#PlotCardTitle {{
                color: {c.text_primary};
                font-size: {t.emph_size}px;
                font-weight: {t.semibold};
                background: transparent;
            }}
            QLabel#PlotCardPreviewChip {{
                color: {c.text_muted};
                background-color: {c.panel_elevated};
                border: 1px solid {c.border_subtle};
                border-radius: {r.pill}px;
                padding: 1px 8px;
                font-size: {t.small_size}px;
            }}
            QPushButton#PlotCardStatsChip {{
                color: {c.text_secondary};
                background-color: {c.panel_elevated};
                border: 1px solid {c.border_subtle};
                border-radius: {r.pill}px;
                padding: 2px 10px;
                font-size: {t.small_size}px;
            }}
            QPushButton#PlotCardStatsChip:hover {{
                color: {c.text_primary};
                border-color: {c.border};
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
        from PySide6.QtWidgets import QPushButton as _QPB
        card = PlotCard(figsize=(5, 3.2))
        card.setFigureTitle("Mean fluorescence")

        def _plot():
            card.figure.clear()
            ax = card.add_subplot(111)
            import math
            xs = [i * 0.1 for i in range(120)]
            for k, color in enumerate(card.traceColors()):
                ax.plot(xs, [math.sin(x + k * 0.6) * (1.0 - 0.12 * k) for x in xs],
                        color=color, linewidth=1.6, label=f"Well {chr(65 + k)}01")
            ax.axhline(0.0, color=theme.Colors.threshold, linestyle="--", linewidth=1.0)
            ax.set_xlabel("Time (h)")
            ax.set_ylabel("Signal")
            ax.legend(fontsize=theme.Typography.caption_size)
            card.style_axes(ax)
            card.draw()

        _plot()
        # left-header view-switcher + a controls row beneath the header
        vsw = _make_segmented([("Line", "line"), ("Bar", "bar"), ("Scatter", "scatter"),
                               ("Dist", "dist"), ("Heat", "heat")], current="line")
        if vsw is not None:
            card.setLeftHeaderWidget(vsw)
        from PySide6.QtWidgets import QHBoxLayout as _QHB
        ctrls = _QW()
        _cl = _QHB(ctrls); _cl.setContentsMargins(0, 0, 0, 0); _cl.setSpacing(theme.Spacing.sm)
        _cl.addWidget(QLabel("Across:"))
        _cl.addWidget(_make_segmented([("Replicates", "rep"), ("FOV", "fov")], current="rep"))
        _cl.addWidget(QLabel("Error:"))
        _cl.addWidget(_make_segmented([("SEM", "SEM"), ("SD", "SD"), ("None", "None")], current="SEM"))
        card.setControlsWidget(ctrls)
        lay.addWidget(card, 1)

        btn = _QPB("Toggle screen / publication (also in the header)")
        btn.clicked.connect(lambda: (card.setPlotTheme(
            "publication" if card.plotTheme() == "screen" else "screen"), _plot()))
        lay.addWidget(btn)
        echo = QLabel("(left header: view-switcher · header: Publication↔Screen toggle + 'preview only' chip + stats chip → popover · controls row beneath the header)")
        echo.setObjectName("Secondary")
        echo.setWordWrap(True)
        lay.addWidget(echo)
        card.statsChanged.connect(lambda s, e: echo.setText(f"stats → {s} · {e}"))
        card.plotThemeChanged.connect(lambda m: (_plot(), echo.setText(f"plot theme → {m}")))

    root.resize(640, 500)
    root.show()
    _sys.exit(app.exec())
