"""Standardized matplotlib Qt host used by Qt migration slices (Phase 5)."""

from __future__ import annotations


def make_plot_host(parent=None, *, title: str = ""):
    import matplotlib

    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
    from matplotlib.figure import Figure
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    fig = Figure(figsize=(5, 3), tight_layout=True)
    ax = fig.add_subplot(111)
    if title:
        ax.set_title(title)
    canvas = FigureCanvasQTAgg(fig)
    toolbar = NavigationToolbar2QT(canvas, container)

    layout.addWidget(toolbar)
    layout.addWidget(canvas, stretch=1)

    return {
        "widget": container,
        "figure": fig,
        "axis": ax,
        "canvas": canvas,
        "toolbar": toolbar,
    }


def draw_message(host: dict, message: str) -> None:
    ax = host["axis"]
    ax.clear()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_xticks([])
    ax.set_yticks([])
    host["canvas"].draw_idle()
