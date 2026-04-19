"""Compatibility shim for legacy theme imports.

Legacy ttk styling has been removed. Use `ui.qt_theme` for runtime theming.
"""

from __future__ import annotations

from ui.qt_theme import THEMES as QT_THEMES

_CURRENT_THEME = "Dark"
THEMES = {name: {
    "BG_APP": t.bg_app,
    "BG_PANEL": t.bg_panel,
    "BG_SIDE": t.bg_side,
    "BORDER": t.border,
    "TXT_PRI": t.text_primary,
    "TXT_MUT": t.text_muted,
    "ACCENT": t.accent,
    "ACCENT_DARK": t.accent_hover,
    "TXT_SEC": t.text_primary,
    "WARN": "#f59e0b",
    "CLR_WHITE": "#ffffff",
} for name, t in QT_THEMES.items()}

# Legacy font token compatibility
FM_TINY = ("Segoe UI", 9)
FM_MED = ("Segoe UI", 10)
FM_BOLD = ("Segoe UI", 10, "bold")
FM_SECTION = ("Segoe UI", 11, "bold")
FM_H2 = ("Segoe UI", 12, "bold")


def set_theme(theme_name: str) -> None:
    global _CURRENT_THEME
    if theme_name in THEMES:
        _CURRENT_THEME = theme_name


def get_theme_colors() -> dict[str, str]:
    colors = THEMES.get(_CURRENT_THEME, THEMES["Dark"]).copy()
    # legacy aliases
    colors.setdefault("TOOLTIP_BG", colors["BG_PANEL"])
    colors.setdefault("TOOLTIP_FG", colors["TXT_PRI"])
    colors.setdefault("BG_CELL", colors["BG_SIDE"])
    colors.setdefault("BG_HOVER", colors["ACCENT_DARK"])
    return colors


def get_color(name: str, default: str = "#000000") -> str:
    return get_theme_colors().get(name, default)


def apply_all_well_theme(style, theme_name: str | None = None) -> None:
    if theme_name:
        set_theme(theme_name)


def update_widget_colors(widget, color_map: dict[str, str]) -> None:
    return None


def rebuild_widget_colors(widget, old_theme: str, new_theme: str) -> None:
    set_theme(new_theme)


for _k, _v in get_theme_colors().items():
    globals()[_k] = _v
