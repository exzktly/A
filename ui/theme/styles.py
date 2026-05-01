"""Theme tokens, fonts, and QSS stylesheet producer for the All-Well Qt app."""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from string import Template
from typing import Dict

_CURRENT_THEME = "Dark"

_DARK_THEME: Dict[str, str] = {
    "BG_APP": "#0F172A", "BG_SIDE": "#1E293B", "BG_PANEL": "#111827",
    "BG_CELL": "#334155", "BG_HOVER": "#475569", "BORDER": "#64748B",
    "TAB_BG": "#1F2937", "TAB_BG_ACTIVE": "#374151",
    "TAB_FG": "#CBD5E1", "TAB_FG_ACTIVE": "#FFFFFF", "TAB_BORDER": "#475569",
    "GRP_DATA": "#3B82F6", "GRP_CONFIG": "#84CC16",
    "TXT_PRI": "#F8FAFC", "TXT_SEC": "#E2E8F0", "TXT_MUT": "#94A3B8",
    "ACCENT": "#3B82F6", "ACCENT_DARK": "#2563EB", "WARN": "#F59E0B",
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#B8CAE3",
    "PLOT_SPN": "#7F9FC9", "PLOT_TXT": "#2E4768",
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#F0F4FF",
    "CLR_SUCCESS": "#059669", "CLR_SUCCESS_DARK": "#047857",
    "CLR_SUCCESS_BG_DARK": "#064E3B", "CLR_SUCCESS_TEXT_SOFT": "#6EE7B7",
    "CLR_DANGER": "#DC2626", "CLR_DANGER_DARK": "#B91C1C",
    "CLR_DANGER_BG": "#7F1D1D", "CLR_DANGER_HOVER": "#991B1B",
    "CLR_ERROR_BG_DARK": "#7F1D1D", "CLR_ERROR_TEXT_SOFT": "#FCA5A5",
    "CLR_WARN_DARK": "#D97706", "CLR_WARN_TEXT": "#92400E", "CLR_WARN_BG": "#78350F",
    "CLR_SLATE_BG": "#0F172A", "CLR_SLATE_TEXT": "#FCD34D",
    "CLR_MUTED_DISABLED": "#A0AEC0", "CLR_MUTED_TEXT_SOFT": "#CBD5E1",
    "CLR_PLACEHOLDER": "#64748B", "CLR_ERR_BAR": "#4A5568",
    "CLR_AVAIL_WELL": "#1F2937", "CLR_AVAIL_HOVER": "#374151",
    "TOOLTIP_BG": "#FFFFFF", "TOOLTIP_FG": "#1F2937",
    "button_bg": "#374151", "button_text": "#F8FAFC",
    "button_text_disabled": "#64748B", "BTN_TEXT_BLACK": "#000000",
    "INSET_SHADOW": "#0F172A", "INSET_HIGHLIGHT": "#64748B",
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

_WELL_COLORS: Dict[str, str] = {
    "WELL_COLOR_1": "#3B82F6", "WELL_COLOR_2": "#EF4444",
    "WELL_COLOR_3": "#F59E0B", "WELL_COLOR_4": "#8B5CF6",
    "WELL_COLOR_5": "#F97316", "WELL_COLOR_6": "#06B6D4",
    "WELL_COLOR_7": "#EC4899", "WELL_COLOR_8": "#84CC16",
    "WELL_COLOR_9": "#A855F7",
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

BTN_FLAT_BG = _DARK_THEME["button_bg"]
BTN_FLAT_TEXT = _DARK_THEME["button_text"]
BTN_FLAT_TEXT_DISABLED = _DARK_THEME["button_text_disabled"]
