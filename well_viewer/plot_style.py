"""Shared matplotlib axis styling.

Extracted from ``well_viewer.runtime_app`` so plot controllers and export
panels can apply the canonical dark-on-light look without importing the GUI
monolith.
"""

from __future__ import annotations

from ui.theme import PLOT_BG, PLOT_GRD, PLOT_SPN, PLOT_TXT, TXT_PRI


def apply_ax_style(ax, title: str, ylabel: str) -> None:
    """Apply the standard plot style to *ax*."""
    ax.set_facecolor(PLOT_BG)
    for sp in ax.spines.values():
        sp.set_color(PLOT_SPN)
        sp.set_linewidth(0.8)
    ax.tick_params(colors=PLOT_TXT, labelsize=8)
    ax.xaxis.label.set_color(PLOT_TXT)
    ax.yaxis.label.set_color(PLOT_TXT)
    ax.set_title(title, color=TXT_PRI, fontsize=9, fontweight="bold", pad=6)
    ax.set_ylabel(ylabel, fontsize=8, labelpad=5, color=PLOT_TXT)
    ax.grid(True, color=PLOT_GRD, linewidth=0.7, linestyle="-")
