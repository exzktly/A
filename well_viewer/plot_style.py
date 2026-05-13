"""Shared matplotlib axis styling.

Extracted from ``well_viewer.runtime_app`` so plot controllers and export
panels can apply the canonical axis look without importing the GUI monolith.

When the axes belongs to a figure inside a ``widgets.PlotCard``, the styling
honours the card's active ``plotTheme()`` — ``"publication"`` (white bg,
``theme.CPub`` ink — the canonical / exported state) or ``"screen"`` (the dark
token set, a per-card live preview). When the axes is on a bare figure (no
card), falls back to the legacy ``ui.theme`` constants (publication-style).
"""

from __future__ import annotations

from ui.theme import PLOT_BG, PLOT_GRD, PLOT_SPN, PLOT_TXT, TXT_PRI


def _tokens_for(ax) -> tuple:
    """Return ``(bg, title_fg, muted_fg, grid, spine)`` for *ax*'s figure: the
    active ``PlotCard`` theme tokens if the figure is hosted in a card, else the
    legacy ``ui.theme`` constants."""
    fig = getattr(ax, "figure", None)
    card = getattr(fig, "_plot_card", None) if fig is not None else None
    if card is not None:
        try:
            from widgets.plot_card import plot_tokens
            bg, fg, muted, grid, spine = plot_tokens(card.plotTheme())
            return bg, fg, muted, grid, spine
        except Exception:
            pass
    return PLOT_BG, TXT_PRI, PLOT_TXT, PLOT_GRD, PLOT_SPN


def apply_ax_style(ax, title: str, ylabel: str) -> None:
    """Apply the standard plot style to *ax*."""
    bg, title_fg, muted_fg, grid, spine = _tokens_for(ax)
    ax.set_facecolor(bg)
    fig = getattr(ax, "figure", None)
    if fig is not None:
        fig.set_facecolor(bg)
    for sp in ax.spines.values():
        sp.set_color(spine)
        sp.set_linewidth(0.8)
    ax.tick_params(colors=muted_fg, labelsize=8)
    ax.xaxis.label.set_color(muted_fg)
    ax.yaxis.label.set_color(muted_fg)
    ax.set_title(title, color=title_fg, fontsize=9, fontweight="bold", pad=6)
    ax.set_ylabel(ylabel, fontsize=8, labelpad=5, color=muted_fg)
    ax.grid(True, color=grid, linewidth=0.7, linestyle="-")
