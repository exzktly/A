"""Theme tokens, fonts, and QSS stylesheet producer for the All-Well Qt app.

Three redesign palettes (Warm / Fluoro / Ivory) are the primary themes.
Legacy Dark / Light palettes are retained for backward compatibility.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from string import Template
from typing import Dict

_CURRENT_THEME = "Warm"

# ── Redesign palettes ──────────────────────────────────────────────────────────

_WARM_PALETTE: Dict[str, str] = {
    # Backgrounds
    "BG_APP":   "#F7F2EA", "BG_SIDE":  "#FFFDF8", "BG_PANEL": "#FFFDF8",
    "BG_CELL":  "#EEE5D4", "BG_HOVER": "#DED5C2", "BORDER":   "#DED5C2",
    # Tab chrome
    "TAB_BG": "#EEE5D4", "TAB_BG_ACTIVE": "#FFFDF8",
    "TAB_FG": "#7C786D", "TAB_FG_ACTIVE": "#1A1915", "TAB_BORDER": "#DED5C2",
    # Text
    "TXT_PRI": "#1A1915", "TXT_SEC": "#3D3B34", "TXT_MUT": "#7C786D",
    # Accent (emerald)
    "ACCENT": "#0E6B52", "ACCENT_DARK": "#08402F", "WARN": "#C08A2E",
    # Plot
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#E8DFC9",
    "PLOT_SPN": "#7C786D", "PLOT_TXT": "#1A1915",
    # Semantic
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#FFFDF8",
    "CLR_SUCCESS": "#0E6B52", "CLR_SUCCESS_DARK": "#08402F",
    "CLR_SUCCESS_BG_DARK": "#C9E4D6", "CLR_SUCCESS_TEXT_SOFT": "#08402F",
    "CLR_DANGER": "#B13A31", "CLR_DANGER_DARK": "#8B2D26",
    "CLR_DANGER_BG": "#FBD9CE", "CLR_DANGER_HOVER": "#8B2D26",
    "CLR_ERROR_BG_DARK": "#FBD9CE", "CLR_ERROR_TEXT_SOFT": "#B13A31",
    "CLR_WARN_DARK": "#C08A2E", "CLR_WARN_TEXT": "#8B6B22", "CLR_WARN_BG": "#F5DFA0",
    "CLR_SLATE_BG": "#F7F2EA", "CLR_SLATE_TEXT": "#1A1915",
    "CLR_MUTED_DISABLED": "#7C786D", "CLR_MUTED_TEXT_SOFT": "#7C786D",
    "CLR_PLACEHOLDER": "#7C786D", "CLR_ERR_BAR": "#DED5C2",
    "CLR_AVAIL_WELL": "#EEE5D4", "CLR_AVAIL_HOVER": "#DED5C2",
    "TOOLTIP_BG": "#FFFDF8", "TOOLTIP_FG": "#1A1915",
    "button_bg": "#EEE5D4", "button_text": "#1A1915",
    "button_text_disabled": "#7C786D", "BTN_TEXT_BLACK": "#000000",
    # New redesign tokens
    "SUNK": "#EEE5D4", "INK_2": "#3D3B34", "MUT": "#7C786D", "LINE": "#DED5C2",
    "POP": "#E25C3A", "POP_SOFT": "#FBD9CE",
    "ACCENT_SOFT": "#C9E4D6", "ACCENT_INK": "#08402F", "PANEL": "#FFFDF8",
    # Well group colors (palette-specific)
    "WELL_COLOR_1": "#0E6B52", "WELL_COLOR_2": "#E25C3A",
    "WELL_COLOR_3": "#C08A2E", "WELL_COLOR_4": "#7A4AB5",
    "WELL_COLOR_5": "#1F6FB8", "WELL_COLOR_6": "#B13A31",
    "WELL_COLOR_7": "#1F7A8C", "WELL_COLOR_8": "#7C6534",
    "WELL_COLOR_9": "#D4438A",
}

_FLUORO_PALETTE: Dict[str, str] = {
    "BG_APP":   "#0E0F0C", "BG_SIDE":  "#17181A", "BG_PANEL": "#17181A",
    "BG_CELL":  "#0A0B09", "BG_HOVER": "#2A2B27", "BORDER":   "#2A2B27",
    "TAB_BG": "#0A0B09", "TAB_BG_ACTIVE": "#17181A",
    "TAB_FG": "#8F8E86", "TAB_FG_ACTIVE": "#F2F0EA", "TAB_BORDER": "#2A2B27",
    "TXT_PRI": "#F2F0EA", "TXT_SEC": "#D4D2CA", "TXT_MUT": "#8F8E86",
    "ACCENT": "#C6F24E", "ACCENT_DARK": "#A8D43A", "WARN": "#F5B43A",
    "PLOT_BG": "#17181A", "PLOT_GRD": "#24251F",
    "PLOT_SPN": "#8F8E86", "PLOT_TXT": "#F2F0EA",
    "CLR_WHITE": "#F2F0EA", "CLR_OFF_WHITE": "#17181A",
    "CLR_SUCCESS": "#C6F24E", "CLR_SUCCESS_DARK": "#A8D43A",
    "CLR_SUCCESS_BG_DARK": "#2E3A15", "CLR_SUCCESS_TEXT_SOFT": "#0E0F0C",
    "CLR_DANGER": "#F05B5B", "CLR_DANGER_DARK": "#CC4444",
    "CLR_DANGER_BG": "#3A1A1A", "CLR_DANGER_HOVER": "#CC4444",
    "CLR_ERROR_BG_DARK": "#3A1A1A", "CLR_ERROR_TEXT_SOFT": "#F05B5B",
    "CLR_WARN_DARK": "#F5B43A", "CLR_WARN_TEXT": "#D49820", "CLR_WARN_BG": "#3A2E0A",
    "CLR_SLATE_BG": "#0E0F0C", "CLR_SLATE_TEXT": "#F2F0EA",
    "CLR_MUTED_DISABLED": "#8F8E86", "CLR_MUTED_TEXT_SOFT": "#8F8E86",
    "CLR_PLACEHOLDER": "#8F8E86", "CLR_ERR_BAR": "#2A2B27",
    "CLR_AVAIL_WELL": "#0A0B09", "CLR_AVAIL_HOVER": "#2A2B27",
    "TOOLTIP_BG": "#17181A", "TOOLTIP_FG": "#F2F0EA",
    "button_bg": "#0A0B09", "button_text": "#F2F0EA",
    "button_text_disabled": "#8F8E86", "BTN_TEXT_BLACK": "#0E0F0C",
    "SUNK": "#0A0B09", "INK_2": "#D4D2CA", "MUT": "#8F8E86", "LINE": "#2A2B27",
    "POP": "#F05BB5", "POP_SOFT": "#3A1A2C",
    "ACCENT_SOFT": "#2E3A15", "ACCENT_INK": "#0E0F0C", "PANEL": "#17181A",
    "WELL_COLOR_1": "#C6F24E", "WELL_COLOR_2": "#F05BB5",
    "WELL_COLOR_3": "#F5B43A", "WELL_COLOR_4": "#8A6AF0",
    "WELL_COLOR_5": "#4ED6F2", "WELL_COLOR_6": "#F05B5B",
    "WELL_COLOR_7": "#6BF09A", "WELL_COLOR_8": "#E6D84A",
    "WELL_COLOR_9": "#C49AF5",
}

_IVORY_PALETTE: Dict[str, str] = {
    "BG_APP":   "#F4F1EB", "BG_SIDE":  "#FFFFFF", "BG_PANEL": "#FFFFFF",
    "BG_CELL":  "#E9E4D8", "BG_HOVER": "#DED7C7", "BORDER":   "#DED7C7",
    "TAB_BG": "#E9E4D8", "TAB_BG_ACTIVE": "#FFFFFF",
    "TAB_FG": "#6F7874", "TAB_FG_ACTIVE": "#14201D", "TAB_BORDER": "#DED7C7",
    "TXT_PRI": "#14201D", "TXT_SEC": "#2D3936", "TXT_MUT": "#6F7874",
    "ACCENT": "#115E59", "ACCENT_DARK": "#0B403C", "WARN": "#B9862D",
    "PLOT_BG": "#FFFFFF", "PLOT_GRD": "#E5DDC6",
    "PLOT_SPN": "#6F7874", "PLOT_TXT": "#14201D",
    "CLR_WHITE": "#FFFFFF", "CLR_OFF_WHITE": "#F9FAFB",
    "CLR_SUCCESS": "#115E59", "CLR_SUCCESS_DARK": "#0B403C",
    "CLR_SUCCESS_BG_DARK": "#CDE4E0", "CLR_SUCCESS_TEXT_SOFT": "#0B403C",
    "CLR_DANGER": "#9F3A36", "CLR_DANGER_DARK": "#7E2D2A",
    "CLR_DANGER_BG": "#F9D9C2", "CLR_DANGER_HOVER": "#7E2D2A",
    "CLR_ERROR_BG_DARK": "#F9D9C2", "CLR_ERROR_TEXT_SOFT": "#9F3A36",
    "CLR_WARN_DARK": "#B9862D", "CLR_WARN_TEXT": "#8B6620", "CLR_WARN_BG": "#F0DCA8",
    "CLR_SLATE_BG": "#F4F1EB", "CLR_SLATE_TEXT": "#14201D",
    "CLR_MUTED_DISABLED": "#6F7874", "CLR_MUTED_TEXT_SOFT": "#6F7874",
    "CLR_PLACEHOLDER": "#6F7874", "CLR_ERR_BAR": "#DED7C7",
    "CLR_AVAIL_WELL": "#E9E4D8", "CLR_AVAIL_HOVER": "#DED7C7",
    "TOOLTIP_BG": "#FFFFFF", "TOOLTIP_FG": "#14201D",
    "button_bg": "#E9E4D8", "button_text": "#14201D",
    "button_text_disabled": "#6F7874", "BTN_TEXT_BLACK": "#000000",
    "SUNK": "#E9E4D8", "INK_2": "#2D3936", "MUT": "#6F7874", "LINE": "#DED7C7",
    "POP": "#F4A87A", "POP_SOFT": "#F9D9C2",
    "ACCENT_SOFT": "#CDE4E0", "ACCENT_INK": "#0B403C", "PANEL": "#FFFFFF",
    "WELL_COLOR_1": "#115E59", "WELL_COLOR_2": "#F4A87A",
    "WELL_COLOR_3": "#B9862D", "WELL_COLOR_4": "#6B4FA0",
    "WELL_COLOR_5": "#3C7BA5", "WELL_COLOR_6": "#9F3A36",
    "WELL_COLOR_7": "#277F6C", "WELL_COLOR_8": "#A68646",
    "WELL_COLOR_9": "#C463A0",
}

# ── Legacy palettes (kept for backward compat) ─────────────────────────────────

_DARK_THEME: Dict[str, str] = {
    "BG_APP": "#0F172A", "BG_SIDE": "#1E293B", "BG_PANEL": "#111827",
    "BG_CELL": "#334155", "BG_HOVER": "#475569", "BORDER": "#64748B",
    "TAB_BG": "#1F2937", "TAB_BG_ACTIVE": "#374151",
    "TAB_FG": "#CBD5E1", "TAB_FG_ACTIVE": "#FFFFFF", "TAB_BORDER": "#475569",
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
    # Redesign tokens (mapped to nearest dark equivalents)
    "SUNK": "#334155", "INK_2": "#E2E8F0", "MUT": "#94A3B8", "LINE": "#64748B",
    "POP": "#F59E0B", "POP_SOFT": "#78350F",
    "ACCENT_SOFT": "#1E3A5F", "ACCENT_INK": "#FFFFFF", "PANEL": "#111827",
    "WELL_COLOR_1": "#3B82F6", "WELL_COLOR_2": "#EF4444",
    "WELL_COLOR_3": "#F59E0B", "WELL_COLOR_4": "#8B5CF6",
    "WELL_COLOR_5": "#F97316", "WELL_COLOR_6": "#06B6D4",
    "WELL_COLOR_7": "#EC4899", "WELL_COLOR_8": "#84CC16",
    "WELL_COLOR_9": "#A855F7",
}

_LIGHT_THEME: Dict[str, str] = {
    "BG_APP": "#FFFFFF", "BG_SIDE": "#F3F4F6", "BG_PANEL": "#FFFFFF",
    "BG_CELL": "#E5E7EB", "BG_HOVER": "#D1D5DB", "BORDER": "#9CA3AF",
    "TAB_BG": "#E5E7EB", "TAB_BG_ACTIVE": "#D1D5DB",
    "TAB_FG": "#4B5563", "TAB_FG_ACTIVE": "#000000", "TAB_BORDER": "#D1D5DB",
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
    "SUNK": "#E5E7EB", "INK_2": "#374151", "MUT": "#6B7280", "LINE": "#9CA3AF",
    "POP": "#EA580C", "POP_SOFT": "#FEF3C7",
    "ACCENT_SOFT": "#DBEAFE", "ACCENT_INK": "#1F2937", "PANEL": "#FFFFFF",
    "WELL_COLOR_1": "#3B82F6", "WELL_COLOR_2": "#EF4444",
    "WELL_COLOR_3": "#F59E0B", "WELL_COLOR_4": "#8B5CF6",
    "WELL_COLOR_5": "#F97316", "WELL_COLOR_6": "#06B6D4",
    "WELL_COLOR_7": "#EC4899", "WELL_COLOR_8": "#84CC16",
    "WELL_COLOR_9": "#A855F7",
}

# ── Global well colors (legacy — per-palette WELL_COLOR_* above take precedence) ─
_WELL_COLORS: Dict[str, str] = {
    "WELL_COLOR_1": "#3B82F6", "WELL_COLOR_2": "#EF4444",
    "WELL_COLOR_3": "#F59E0B", "WELL_COLOR_4": "#8B5CF6",
    "WELL_COLOR_5": "#F97316", "WELL_COLOR_6": "#06B6D4",
    "WELL_COLOR_7": "#EC4899", "WELL_COLOR_8": "#84CC16",
    "WELL_COLOR_9": "#A855F7",
}

THEMES: Dict[str, Dict[str, str]] = {
    "Warm":   _WARM_PALETTE,
    "Fluoro": _FLUORO_PALETTE,
    "Ivory":  _IVORY_PALETTE,
    "Dark":   _DARK_THEME,
    "Light":  _LIGHT_THEME,
}


def set_theme(name: str) -> None:
    global _CURRENT_THEME
    if name in THEMES:
        _CURRENT_THEME = name


def get_theme_colors() -> Dict[str, str]:
    return dict(THEMES.get(_CURRENT_THEME, _WARM_PALETTE))


def get_color(name: str) -> str:
    return get_theme_colors().get(name, "#000000")


def build_stylesheet(theme_name: str | None = None) -> str:
    if theme_name is None:
        theme_name = _CURRENT_THEME
    set_theme(theme_name)
    tpl_dir = Path(__file__).parent
    # Prefer the unified redesign template; fall back to legacy per-theme files.
    base = tpl_dir / "base.qss"
    if base.exists():
        text = base.read_text(encoding="utf-8")
    else:
        fname = "dark.qss" if theme_name.lower() != "light" else "light.qss"
        text = (tpl_dir / fname).read_text(encoding="utf-8")
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


# ── Back-compat module-level color constants (dark defaults) ──────────────────
# Plot/controller code reads these at import time; frozen to the dark palette.
for _name, _value in _DARK_THEME.items():
    globals()[_name] = _value
for _name, _value in _WELL_COLORS.items():
    globals()[_name] = _value

BTN_FLAT_BG = _DARK_THEME["button_bg"]
BTN_FLAT_TEXT = _DARK_THEME["button_text"]
BTN_FLAT_TEXT_DISABLED = _DARK_THEME["button_text_disabled"]
