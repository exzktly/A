"""Theme tokens, fonts, and QSS stylesheet producer for the All-Well Qt app."""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from string import Template
from typing import Dict

_CURRENT_THEME = "Dark"


# ── Source of truth: the v2 dark palette ────────────────────────────────────
# H20 reconciliation: where this dict has a concept that also lives in
# ``theme.Colors`` (panel / accent / text-primary / borders / etc.) the value
# is sourced from there, so the two namespaces no longer hand out different
# hex codes for the same surface. Plot-specific tokens (PLOT_BG / PLOT_GRD /
# PLOT_SPN / PLOT_TXT) intentionally stay independent — those drive the
# Publication-mode plot canvas, which is white-on-dark on purpose.
from theme import Colors as _C  # noqa: E402

_DARK_THEME: Dict[str, str] = {
    # Surfaces — v2 design tokens
    "BG_APP": _C.surface,             # was "#0F172A"
    "BG_SIDE": _C.rail,               # was "#1E293B"
    "BG_PANEL": _C.panel,             # was "#111827"
    "BG_CELL": _C.panel_elevated,     # was "#334155"
    "BG_HOVER": _C.hover,             # was "#475569"
    "BORDER": _C.border,              # was "#64748B"
    # Tab chrome — kept independent (no v2 token covers tab states)
    "TAB_BG": "#1F2937", "TAB_BG_ACTIVE": "#374151",
    "TAB_FG": "#CBD5E1", "TAB_FG_ACTIVE": "#FFFFFF", "TAB_BORDER": "#475569",
    # Group banners — distinct semantic accents kept as-is
    "GRP_DATA": "#3B82F6", "GRP_CONFIG": "#84CC16",
    # Text hierarchy
    "TXT_PRI": _C.text_primary,       # was "#F8FAFC"
    "TXT_SEC": _C.text_secondary,     # was "#E2E8F0"
    "TXT_MUT": _C.text_muted,         # was "#94A3B8"
    # Interactive accent
    "ACCENT": _C.accent,              # was "#3B82F6"
    "ACCENT_DARK": _C.accent_pressed, # was "#2563EB"
    "WARN": _C.warn,                  # was "#F59E0B"
    # Publication-mode plot palette — independent of app chrome by design
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#B8CAE3",
    "PLOT_SPN": "#7F9FC9", "PLOT_TXT": "#2E4768",
    # Contrast inks
    "CLR_WHITE": _C.ink_light, "CLR_OFF_WHITE": _C.accent_fg,
    # Status / dialog palette — independent (no v2 equivalents)
    "CLR_SUCCESS": "#059669", "CLR_SUCCESS_DARK": "#047857",
    "CLR_SUCCESS_BG_DARK": "#064E3B", "CLR_SUCCESS_TEXT_SOFT": "#6EE7B7",
    "CLR_DANGER": "#DC2626", "CLR_DANGER_DARK": "#B91C1C",
    "CLR_DANGER_BG": "#7F1D1D", "CLR_DANGER_HOVER": "#991B1B",
    "CLR_ERROR_BG_DARK": "#7F1D1D", "CLR_ERROR_TEXT_SOFT": "#FCA5A5",
    "CLR_WARN_DARK": "#D97706", "CLR_WARN_TEXT": "#92400E", "CLR_WARN_BG": "#78350F",
    "CLR_SLATE_BG": _C.surface, "CLR_SLATE_TEXT": "#FCD34D",
    "CLR_MUTED_DISABLED": "#A0AEC0", "CLR_MUTED_TEXT_SOFT": "#CBD5E1",
    "CLR_PLACEHOLDER": "#64748B", "CLR_ERR_BAR": "#4A5568",
    "CLR_AVAIL_WELL": "#1F2937", "CLR_AVAIL_HOVER": "#374151",
    "TOOLTIP_BG": _C.ink_light, "TOOLTIP_FG": "#1F2937",
    "button_bg": _C.panel_elevated, "button_text": _C.text_primary,
    "button_text_disabled": _C.text_muted, "BTN_TEXT_BLACK": _C.ink_dark,
    "INSET_SHADOW": _C.surface, "INSET_HIGHLIGHT": _C.border,
}

_LIGHT_THEME: Dict[str, str] = {
    "BG_APP": "#FFFFFF", "BG_SIDE": "#F3F4F6", "BG_PANEL": "#FFFFFF",
    "BG_CELL": "#E5E7EB", "BG_HOVER": "#D1D5DB", "BORDER": "#9CA3AF",
    "TAB_BG": "#E5E7EB", "TAB_BG_ACTIVE": "#D1D5DB",
    "TAB_FG": "#4B5563", "TAB_FG_ACTIVE": "#000000", "TAB_BORDER": "#D1D5DB",
    "GRP_DATA": "#3B82F6", "GRP_CONFIG": "#84CC16",
    "TXT_PRI": "#1F2937", "TXT_SEC": "#374151", "TXT_MUT": "#6B7280",
    "ACCENT": "#3B82F6", "ACCENT_DARK": "#1F2937", "WARN": "#EA580C",
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#D0DCF0",
    "PLOT_SPN": "#5B8DCC", "PLOT_TXT": "#1F2937",
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#F9FAFB",
    "CLR_SUCCESS": "#059669", "CLR_SUCCESS_DARK": "#047857",
    "CLR_SUCCESS_BG_DARK": "#DBEAFE", "CLR_SUCCESS_TEXT_SOFT": "#065F46",
    "CLR_DANGER": "#DC2626", "CLR_DANGER_DARK": "#B91C1C",
    "CLR_DANGER_BG": "#FEE2E2", "CLR_DANGER_HOVER": "#991B1B",
    "CLR_ERROR_BG_DARK": "#FEE2E2", "CLR_ERROR_TEXT_SOFT": "#7F1D1D",
    "CLR_WARN_DARK": "#D97706", "CLR_WARN_TEXT": "#B45309", "CLR_WARN_BG": "#FEF3C7",
    "CLR_SLATE_BG": "#FFFFFF", "CLR_SLATE_TEXT": "#1F2937",
    "CLR_MUTED_DISABLED": "#9CA3AF", "CLR_MUTED_TEXT_SOFT": "#6B7280",
    "CLR_PLACEHOLDER": "#9CA3AF", "CLR_ERR_BAR": "#D1D5DB",
    "CLR_AVAIL_WELL": "#E5E7EB", "CLR_AVAIL_HOVER": "#D1D5DB",
    "TOOLTIP_BG": "#FFFFFF", "TOOLTIP_FG": "#1F2937",
    "button_bg": "#E5E7EB", "button_text": "#1F2937",
    "button_text_disabled": "#9CA3AF", "BTN_TEXT_BLACK": "#000000",
    "INSET_SHADOW": "#6B7280", "INSET_HIGHLIGHT": "#FFFFFF",
}

# Well palette — derived from the canonical tuple in the repo-root ``theme``
# module so every consumer (matplotlib's ``axes.prop_cycle`` via
# ``widgets/plot_card.plot_palette``, the QSS template substitution below,
# and ``well_viewer.plate_layout.WELL_COLORS``) reads the same 48 entries
# in the same order. Adjusting the palette only requires editing the
# source tuple in ``theme.py``.
from theme import WELL_COLORS_TUPLE as _WELL_COLORS_TUPLE  # noqa: E402

_WELL_COLORS: Dict[str, str] = {
    f"WELL_COLOR_{_i}": _hex
    for _i, _hex in enumerate(_WELL_COLORS_TUPLE, start=1)
}

_BEIGE_THEME: Dict[str, str] = {
    "BG_APP": "#F5F0E8", "BG_SIDE": "#EDE8DC", "BG_PANEL": "#F5F0E8",
    "BG_CELL": "#E0D8CA", "BG_HOVER": "#D4C9B5", "BORDER": "#B8A98C",
    "TAB_BG": "#EDE8DC", "TAB_BG_ACTIVE": "#E0D8CA",
    "TAB_FG": "#5C3D28", "TAB_FG_ACTIVE": "#2C1E14", "TAB_BORDER": "#D4C9B5",
    "GRP_DATA": "#C85A2C", "GRP_CONFIG": "#5A8A1E",
    "TXT_PRI": "#2C1E14", "TXT_SEC": "#5C3D28", "TXT_MUT": "#8B6A52",
    "ACCENT": "#C85A2C", "ACCENT_DARK": "#963E1C", "WARN": "#D97706",
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#E8DFD0",
    "PLOT_SPN": "#B8A98C", "PLOT_TXT": "#2C1E14",
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#FDF8F0",
    "CLR_SUCCESS": "#2D7D46", "CLR_SUCCESS_DARK": "#1F5C33",
    "CLR_SUCCESS_BG_DARK": "#D1E8D8", "CLR_SUCCESS_TEXT_SOFT": "#1F5C33",
    "CLR_DANGER": "#C0392B", "CLR_DANGER_DARK": "#922B21",
    "CLR_DANGER_BG": "#F5C6C2", "CLR_DANGER_HOVER": "#922B21",
    "CLR_ERROR_BG_DARK": "#F5C6C2", "CLR_ERROR_TEXT_SOFT": "#7F1D1D",
    "CLR_WARN_DARK": "#B45309", "CLR_WARN_TEXT": "#92400E", "CLR_WARN_BG": "#FDE8C4",
    "CLR_SLATE_BG": "#F5F0E8", "CLR_SLATE_TEXT": "#2C1E14",
    "CLR_MUTED_DISABLED": "#B8A98C", "CLR_MUTED_TEXT_SOFT": "#8B6A52",
    "CLR_PLACEHOLDER": "#B8A98C", "CLR_ERR_BAR": "#D4C9B5",
    "CLR_AVAIL_WELL": "#E0D8CA", "CLR_AVAIL_HOVER": "#D4C9B5",
    "TOOLTIP_BG": "#FDF8F0", "TOOLTIP_FG": "#2C1E14",
    "button_bg": "#E0D8CA", "button_text": "#2C1E14",
    "button_text_disabled": "#B8A98C", "BTN_TEXT_BLACK": "#000000",
    "INSET_SHADOW": "#B8A98C", "INSET_HIGHLIGHT": "#FFFFFF",
}

_AMBER_THEME: Dict[str, str] = {
    "BG_APP": "#0C0A06", "BG_SIDE": "#1A1108", "BG_PANEL": "#110D07",
    "BG_CELL": "#2A1C0E", "BG_HOVER": "#3A2610", "BORDER": "#6B4A24",
    "TAB_BG": "#0C0A06", "TAB_BG_ACTIVE": "#2A1C0E",
    "TAB_FG": "#8C6A3E", "TAB_FG_ACTIVE": "#F5E6C8", "TAB_BORDER": "#3D2810",
    "GRP_DATA": "#D97706", "GRP_CONFIG": "#84CC16",
    "TXT_PRI": "#F5E6C8", "TXT_SEC": "#D4A853", "TXT_MUT": "#8C6A3E",
    "ACCENT": "#D97706", "ACCENT_DARK": "#B45309", "WARN": "#EAB308",
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#D4B896",
    "PLOT_SPN": "#A07840", "PLOT_TXT": "#4A2E08",
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#FEF3C7",
    "CLR_SUCCESS": "#059669", "CLR_SUCCESS_DARK": "#047857",
    "CLR_SUCCESS_BG_DARK": "#064E3B", "CLR_SUCCESS_TEXT_SOFT": "#6EE7B7",
    "CLR_DANGER": "#DC2626", "CLR_DANGER_DARK": "#B91C1C",
    "CLR_DANGER_BG": "#7F1D1D", "CLR_DANGER_HOVER": "#991B1B",
    "CLR_ERROR_BG_DARK": "#7F1D1D", "CLR_ERROR_TEXT_SOFT": "#FCA5A5",
    "CLR_WARN_DARK": "#B45309", "CLR_WARN_TEXT": "#92400E", "CLR_WARN_BG": "#78350F",
    "CLR_SLATE_BG": "#0C0A06", "CLR_SLATE_TEXT": "#F59E0B",
    "CLR_MUTED_DISABLED": "#6B4A24", "CLR_MUTED_TEXT_SOFT": "#D4A853",
    "CLR_PLACEHOLDER": "#6B4A24", "CLR_ERR_BAR": "#3D2810",
    "CLR_AVAIL_WELL": "#2A1C0E", "CLR_AVAIL_HOVER": "#3A2610",
    "TOOLTIP_BG": "#1A1108", "TOOLTIP_FG": "#F5E6C8",
    "button_bg": "#2A1C0E", "button_text": "#F5E6C8",
    "button_text_disabled": "#6B4A24", "BTN_TEXT_BLACK": "#000000",
    "INSET_SHADOW": "#0C0A06", "INSET_HIGHLIGHT": "#6B4A24",
}

THEMES: Dict[str, Dict[str, str]] = {
    "Dark": _DARK_THEME,
    "Light": _LIGHT_THEME,
    "Amber": _AMBER_THEME,
    "Beige": _BEIGE_THEME,
}


def set_theme(name: str) -> None:
    global _CURRENT_THEME
    if name in THEMES:
        _CURRENT_THEME = name


def get_theme_colors() -> Dict[str, str]:
    d = dict(THEMES[_CURRENT_THEME])
    d.update(_WELL_COLORS)
    return d


def get_color(name: str) -> str:
    return get_theme_colors().get(name, "#000000")


def build_stylesheet(theme_name: str | None = None) -> str:
    if theme_name is None:
        theme_name = _CURRENT_THEME
    set_theme(theme_name)
    tpl_path = Path(__file__).parent / f"{theme_name.lower()}.qss"
    text = tpl_path.read_text(encoding="utf-8")
    return Template(text).substitute(get_theme_colors())


# ── Fonts (platform-aware) ────────────────────────────────────────────────────
SANS = "Segoe UI"
_MONO = "Menlo" if _sys.platform == "darwin" else "Consolas"
_SANS_PLATFORM = "SF Pro Text" if _sys.platform == "darwin" else SANS
FM_MONO    = (_MONO,          9)
FM_UI      = (_SANS_PLATFORM, 9)
FM_BOLD    = (_SANS_PLATFORM, 9,  "bold")
FM_H2      = (_SANS_PLATFORM, 11, "bold")
FM_TITLE   = (_SANS_PLATFORM, 13, "bold")
FM_TINY    = (_MONO,          8)
FM_SECTION = (_SANS_PLATFORM, 10)


# ── Back-compat module-level color constants (dark defaults) ─────────────────
# Plot/controller code reads these at import time; they are frozen to the
# dark palette. Code paths that need live values must call get_color().
for _name, _value in _DARK_THEME.items():
    globals()[_name] = _value
for _name, _value in _WELL_COLORS.items():
    globals()[_name] = _value
