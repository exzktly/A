"""Single source of truth for all visual theme definitions.

Contains:
  - Color tokens (backgrounds, text, accents, semantic colors, plot palette)
  - Font tuples (platform-aware)
  - Theme definitions (Dark and Light modes)
  - TTK style registration via apply_all_well_theme()
"""

from __future__ import annotations

import sys as _sys
from tkinter import ttk
from typing import Dict, Any

# ── Current theme (global state) ──────────────────────────────────────────────
_CURRENT_THEME = "Dark"

# ── Dark Mode Color Palette ───────────────────────────────────────────────────
_DARK_THEME = {
    # Backgrounds
    "BG_APP":   "#0F172A",
    "BG_SIDE":  "#1E293B",
    "BG_PANEL": "#111827",
    "BG_CELL":  "#334155",
    "BG_HOVER": "#475569",
    "BORDER":   "#64748B",

    # Tab chrome
    "TAB_BG":        "#1F2937",
    "TAB_BG_ACTIVE": "#374151",
    "TAB_FG":        "#CBD5E1",
    "TAB_FG_ACTIVE": "#FFFFFF",
    "TAB_BORDER":    "#475569",

    # Text
    "TXT_PRI": "#F8FAFC",
    "TXT_SEC": "#E2E8F0",
    "TXT_MUT": "#94A3B8",

    # Accents
    "ACCENT":      "#3B82F6",
    "ACCENT_DARK": "#2563EB",
    "WARN":        "#F59E0B",

    # Plot palette
    "PLOT_BG":  "#FFFFFF",
    "PLOT_GRD": "#B8CAE3",
    "PLOT_SPN": "#7F9FC9",
    "PLOT_TXT": "#2E4768",

    # Semantic colors
    "CLR_WHITE":            "#FFFFFF",
    "CLR_OFF_WHITE":        "#F0F4FF",
    "CLR_SUCCESS":          "#059669",
    "CLR_SUCCESS_DARK":     "#047857",
    "CLR_SUCCESS_BG_DARK":  "#064E3B",
    "CLR_SUCCESS_TEXT_SOFT":"#6EE7B7",
    "CLR_DANGER":           "#DC2626",
    "CLR_DANGER_DARK":      "#B91C1C",
    "CLR_DANGER_BG":        "#7F1D1D",
    "CLR_DANGER_HOVER":     "#991B1B",
    "CLR_ERROR_BG_DARK":    "#7F1D1D",
    "CLR_ERROR_TEXT_SOFT":  "#FCA5A5",
    "CLR_WARN_DARK":        "#D97706",
    "CLR_WARN_TEXT":        "#92400E",
    "CLR_WARN_BG":          "#78350F",
    "CLR_SLATE_BG":         "#0F172A",
    "CLR_SLATE_TEXT":       "#FCD34D",
    "CLR_MUTED_DISABLED":   "#A0AEC0",
    "CLR_MUTED_TEXT_SOFT":  "#CBD5E1",
    "CLR_PLACEHOLDER":      "#64748B",
    "CLR_ERR_BAR":          "#4A5568",
    "CLR_AVAIL_WELL":       "#1F2937",
    "CLR_AVAIL_HOVER":      "#374151",

    # Tooltip
    "TOOLTIP_BG": "#FFFFFF",
    "TOOLTIP_FG": "#1F2937",

    # Button base tokens
    "button_bg":            "#374151",
    "button_text":          "#F8FAFC",
    "button_text_disabled": "#64748B",
    "BTN_TEXT_BLACK":       "#000000",
}

# ── Light Mode Color Palette ──────────────────────────────────────────────────
_LIGHT_THEME = {
    # Backgrounds
    "BG_APP":   "#FFFFFF",
    "BG_SIDE":  "#F3F4F6",
    "BG_PANEL": "#FFFFFF",
    "BG_CELL":  "#E5E7EB",
    "BG_HOVER": "#D1D5DB",
    "BORDER":   "#9CA3AF",

    # Tab chrome
    "TAB_BG":        "#E5E7EB",
    "TAB_BG_ACTIVE": "#D1D5DB",
    "TAB_FG":        "#4B5563",
    "TAB_FG_ACTIVE": "#000000",
    "TAB_BORDER":    "#D1D5DB",

    # Text
    "TXT_PRI": "#1F2937",
    "TXT_SEC": "#374151",
    "TXT_MUT": "#6B7280",

    # Accents
    "ACCENT":      "#3B82F6",
    "ACCENT_DARK": "#1F2937",
    "WARN":        "#EA580C",

    # Plot palette
    "PLOT_BG":  "#FFFFFF",
    "PLOT_GRD": "#D0DCF0",
    "PLOT_SPN": "#5B8DCC",
    "PLOT_TXT": "#1F2937",

    # Semantic colors
    "CLR_WHITE":            "#FFFFFF",
    "CLR_OFF_WHITE":        "#F9FAFB",
    "CLR_SUCCESS":          "#059669",
    "CLR_SUCCESS_DARK":     "#047857",
    "CLR_SUCCESS_BG_DARK":  "#DBEAFE",
    "CLR_SUCCESS_TEXT_SOFT":"#065F46",
    "CLR_DANGER":           "#DC2626",
    "CLR_DANGER_DARK":      "#B91C1C",
    "CLR_DANGER_BG":        "#FEE2E2",
    "CLR_DANGER_HOVER":     "#991B1B",
    "CLR_ERROR_BG_DARK":    "#FEE2E2",
    "CLR_ERROR_TEXT_SOFT":  "#7F1D1D",
    "CLR_WARN_DARK":        "#D97706",
    "CLR_WARN_TEXT":        "#B45309",
    "CLR_WARN_BG":          "#FEF3C7",
    "CLR_SLATE_BG":         "#FFFFFF",
    "CLR_SLATE_TEXT":       "#1F2937",
    "CLR_MUTED_DISABLED":   "#9CA3AF",
    "CLR_MUTED_TEXT_SOFT":  "#6B7280",
    "CLR_PLACEHOLDER":      "#9CA3AF",
    "CLR_ERR_BAR":          "#D1D5DB",
    "CLR_AVAIL_WELL":       "#E5E7EB",
    "CLR_AVAIL_HOVER":      "#D1D5DB",

    # Tooltip
    "TOOLTIP_BG": "#FFFFFF",
    "TOOLTIP_FG": "#1F2937",

    # Button base tokens
    "button_bg":            "#E5E7EB",
    "button_text":          "#1F2937",
    "button_text_disabled": "#9CA3AF",
    "BTN_TEXT_BLACK":       "#000000",
}

# ── Well group colors (same for both themes) ──────────────────────────────────
_WELL_COLORS = {
    "WELL_COLOR_1": "#3B82F6",
    "WELL_COLOR_2": "#EF4444",
    "WELL_COLOR_3": "#F59E0B",
    "WELL_COLOR_4": "#8B5CF6",
    "WELL_COLOR_5": "#F97316",
    "WELL_COLOR_6": "#06B6D4",
    "WELL_COLOR_7": "#EC4899",
    "WELL_COLOR_8": "#84CC16",
    "WELL_COLOR_9": "#A855F7",
}

# ── Theme dictionary ─────────────────────────────────────────────────────────
THEMES = {
    "Dark": _DARK_THEME,
    "Light": _LIGHT_THEME,
}

def set_theme(theme_name: str) -> None:
    """Set the current theme to Dark or Light and update all color constants."""
    global _CURRENT_THEME
    if theme_name in THEMES:
        _CURRENT_THEME = theme_name
        _update_module_colors()

def _update_module_colors() -> None:
    """Update all module-level color constants to match current theme.

    This allows existing code that imports color constants to automatically
    use the new theme colors when the theme changes.
    """
    import sys
    colors = get_theme_colors()
    current_module = sys.modules[__name__]

    # Update all color constants
    for color_name, color_value in colors.items():
        setattr(current_module, color_name, color_value)

def update_widget_colors(widget, color_map: Dict[str, str]) -> None:
    """Recursively update all widget background/foreground colors based on color map.

    Args:
        widget: Root widget to start recursion from
        color_map: Dictionary mapping old colors to new colors
    """
    import tkinter as tk

    try:
        # Get current colors
        try:
            bg = widget.cget('bg')
            if bg in color_map:
                widget.config(bg=color_map[bg])
        except (tk.TclError, AttributeError):
            pass

        try:
            fg = widget.cget('fg')
            if fg in color_map:
                widget.config(fg=color_map[fg])
        except (tk.TclError, AttributeError):
            pass

        # Special handling for WellLabel to update cached hover colors
        if hasattr(widget, 'update_theme_colors'):
            try:
                widget.update_theme_colors(color_map)
            except Exception:
                pass
    except Exception:
        pass

    # Recursively update children
    try:
        for child in widget.winfo_children():
            update_widget_colors(child, color_map)
    except Exception:
        pass

def rebuild_widget_colors(widget, old_theme: str, new_theme: str) -> None:
    """Recursively rebuild widget colors by semantic name, not hex value.

    This fixes the issue where multiple color names map to same hex value,
    causing dictionary collision in simple hex→hex mapping.

    Instead, we:
    1. Reverse-map current widget color (hex) → color name from old theme
    2. Look up that color name's new value in new theme
    3. Update widget with new theme's color

    Args:
        widget: Root widget to start recursion from
        old_theme: Name of theme being switched FROM (e.g., "Dark")
        new_theme: Name of theme being switched TO (e.g., "Light")
    """
    import tkinter as tk

    old_theme_dict = THEMES.get(old_theme, {})
    new_theme_dict = THEMES.get(new_theme, {})

    # Create reverse mapping: hex value → color name for old theme
    # (allows us to find which semantic color a widget currently uses)
    old_hex_to_name = {v: k for k, v in old_theme_dict.items()}

    try:
        # Update background color
        try:
            bg = widget.cget('bg')
            if bg in old_hex_to_name:
                color_name = old_hex_to_name[bg]
                new_color = new_theme_dict.get(color_name)
                if new_color:
                    widget.config(bg=new_color)
        except (tk.TclError, AttributeError):
            pass

        # Update foreground color
        try:
            fg = widget.cget('fg')
            if fg in old_hex_to_name:
                color_name = old_hex_to_name[fg]
                new_color = new_theme_dict.get(color_name)
                if new_color:
                    widget.config(fg=new_color)
        except (tk.TclError, AttributeError):
            pass

        # Special handling for WellLabel to update cached hover colors
        if hasattr(widget, 'update_theme_colors_rebuild'):
            try:
                widget.update_theme_colors_rebuild(old_theme, new_theme)
            except Exception:
                pass
    except Exception:
        pass

    # Recursively update children
    try:
        for child in widget.winfo_children():
            rebuild_widget_colors(child, old_theme, new_theme)
    except Exception:
        pass

def get_theme_colors() -> Dict[str, str]:
    """Get the current theme's color palette."""
    colors = THEMES[_CURRENT_THEME].copy()
    colors.update(_WELL_COLORS)
    return colors

def get_color(color_name: str) -> str:
    """Get a single color from the current theme."""
    colors = get_theme_colors()
    return colors.get(color_name, "#000000")

# ── Backward compatibility: Direct color constants from current theme ────────
# These will be replaced dynamically when theme changes
BG_APP   = "#0F172A"
BG_SIDE  = "#1E293B"
BG_PANEL = "#111827"
BG_CELL  = "#334155"
BG_HOVER = "#475569"
BORDER   = "#64748B"

# Tab chrome
TAB_BG        = "#1F2937"
TAB_BG_ACTIVE = "#374151"
TAB_FG        = "#CBD5E1"
TAB_FG_ACTIVE = "#FFFFFF"
TAB_BORDER    = "#475569"

# Text
TXT_PRI = "#F8FAFC"
TXT_SEC = "#E2E8F0"
TXT_MUT = "#94A3B8"

# Accents
ACCENT      = "#3B82F6"
ACCENT_DARK = "#2563EB"
WARN        = "#F59E0B"

# Plot palette
PLOT_BG  = "#FFFFFF"
PLOT_GRD = "#B8CAE3"
PLOT_SPN = "#7F9FC9"
PLOT_TXT = "#2E4768"

# Semantic colors
CLR_WHITE            = "#FFFFFF"
CLR_OFF_WHITE        = "#F0F4FF"
CLR_SUCCESS          = "#059669"
CLR_SUCCESS_DARK     = "#047857"
CLR_SUCCESS_BG_DARK  = "#064E3B"
CLR_SUCCESS_TEXT_SOFT= "#6EE7B7"
CLR_DANGER           = "#DC2626"
CLR_DANGER_DARK      = "#B91C1C"
CLR_DANGER_BG        = "#7F1D1D"
CLR_DANGER_HOVER     = "#991B1B"
CLR_ERROR_BG_DARK    = "#7F1D1D"
CLR_ERROR_TEXT_SOFT  = "#FCA5A5"
CLR_WARN_DARK        = "#D97706"
CLR_WARN_TEXT        = "#92400E"
CLR_WARN_BG          = "#78350F"
CLR_SLATE_BG         = "#0F172A"
CLR_SLATE_TEXT       = "#FCD34D"
CLR_MUTED_DISABLED   = "#A0AEC0"
CLR_MUTED_TEXT_SOFT  = "#CBD5E1"
CLR_PLACEHOLDER      = "#64748B"
CLR_ERR_BAR          = "#4A5568"
CLR_AVAIL_WELL       = "#1F2937"
CLR_AVAIL_HOVER      = "#374151"

# Tooltip
TOOLTIP_BG = "#FFFFFF"
TOOLTIP_FG = "#1F2937"

# Well group colors
WELL_COLOR_1 = "#3B82F6"
WELL_COLOR_2 = "#EF4444"
WELL_COLOR_3 = "#F59E0B"
WELL_COLOR_4 = "#8B5CF6"
WELL_COLOR_5 = "#F97316"
WELL_COLOR_6 = "#06B6D4"
WELL_COLOR_7 = "#EC4899"
WELL_COLOR_8 = "#84CC16"
WELL_COLOR_9 = "#A855F7"

# Button base tokens
button_bg            = "#374151"
button_text          = "#F8FAFC"
button_text_disabled = "#64748B"
BTN_TEXT_BLACK           = "#000000"
BTN_FLAT_BG              = button_bg
BTN_FLAT_TEXT            = button_text
BTN_FLAT_TEXT_DISABLED   = button_text_disabled

# ── Fonts (platform-aware) ────────────────────────────────────────────────────
SANS            = "Segoe UI"
_MONO           = "Menlo"        if _sys.platform == "darwin" else "Consolas"
_SANS_PLATFORM  = "SF Pro Text"  if _sys.platform == "darwin" else SANS
FM_MONO    = (_MONO,          9)
FM_UI      = (_SANS_PLATFORM, 9)
FM_BOLD    = (_SANS_PLATFORM, 9,  "bold")
FM_H2      = (_SANS_PLATFORM, 11, "bold")
FM_TITLE   = (_SANS_PLATFORM, 13, "bold")
FM_TINY    = (_MONO,          8)
FM_SECTION = (_SANS_PLATFORM, 10)

# ── TTK style registration ────────────────────────────────────────────────────

# Legacy action-button styles (flat dark bg, used by QuickSelect / Action bars)
_TBUTTON_PADDING = {
    "QuickSelect.TButton":     (4,  1),
    "ActionIndigo.TButton":    (10, 4),
    "ActionSuccess.TButton":   (10, 4),
    "ActionSecondary.TButton": (10, 4),
}

# Named button variants: (background, foreground, active_background, font)
_TBUTTON_VARIANTS = {
    "Primary.TButton":      (ACCENT,        CLR_WHITE,  ACCENT,           FM_TINY),
    "PrimaryDark.TButton":  (ACCENT_DARK,   CLR_WHITE,  ACCENT,           FM_BOLD),
    "Secondary.TButton":    (BG_CELL,       TXT_SEC,    BG_HOVER,         FM_TINY),
    "Card.TButton":         (BG_CELL,       TXT_SEC,    BG_HOVER,         FM_TINY),
    "Danger.TButton":       (CLR_DANGER_BG, CLR_DANGER, CLR_DANGER_HOVER, FM_TINY),
    "SEM.TButton":          (ACCENT,        CLR_WHITE,  ACCENT_DARK,      FM_BOLD),
    "SEMWarn.TButton":      (WARN,          CLR_WHITE,  CLR_WARN_DARK,    FM_BOLD),
    "Toggle.TButton":       (BG_CELL,       TXT_SEC,    BG_HOVER,         FM_TINY),
    "ToggleActive.TButton": (ACCENT,        CLR_WHITE,  ACCENT_DARK,      FM_TINY),
    "ToggleWarn.TButton":   (WARN,          CLR_WHITE,  CLR_WARN_DARK,    FM_TINY),
    "ToggleMuted.TButton":  (BG_CELL,       TXT_MUT,    BG_HOVER,         FM_TINY),
    "ToggleAccent.TButton": (BG_CELL,       ACCENT,     BG_HOVER,         FM_TINY),
    "SideAccent.TButton":   (BG_SIDE,       ACCENT,     BG_HOVER,         FM_TINY),
    "SideMuted.TButton":    (BG_SIDE,       TXT_MUT,    BG_HOVER,         FM_TINY),
    "Run.TButton":          (CLR_SUCCESS,   CLR_WHITE,  CLR_SUCCESS_DARK, FM_BOLD),
    "Stop.TButton":         (CLR_DANGER,    CLR_WHITE,  CLR_DANGER_DARK,  FM_BOLD),
}

_TBUTTON_VARIANT_PADDING = {
    "Primary.TButton":      (10, 4),
    "PrimaryDark.TButton":  (14, 5),
    "Secondary.TButton":    (8,  3),
    "Card.TButton":         (6,  2),
    "Danger.TButton":       (6,  2),
    "SEM.TButton":          (12, 4),
    "SEMWarn.TButton":      (12, 4),
    "Toggle.TButton":       (8,  3),
    "ToggleActive.TButton": (8,  3),
    "ToggleWarn.TButton":   (8,  3),
    "ToggleMuted.TButton":  (8,  3),
    "ToggleAccent.TButton": (8,  3),
    "SideAccent.TButton":   (6,  2),
    "SideMuted.TButton":    (6,  2),
    "Run.TButton":          (14, 6),
    "Stop.TButton":         (14, 6),
}


def apply_all_well_theme(style: ttk.Style, theme_name: str = None) -> None:
    """Apply the AllWell theme to *style*.

    Uses the "clam" TTK theme engine — macOS "aqua" ignores most colour
    customisations, while clam respects them on all platforms.

    Args:
        style: ttk.Style object to configure
        theme_name: "Dark" or "Light" (default: current theme)
    """
    if theme_name is None:
        theme_name = _CURRENT_THEME
    set_theme(theme_name)
    colors = get_theme_colors()

    style.theme_use("clam")

    # Extract colors for this theme
    bg_app = colors["BG_APP"]
    bg_side = colors["BG_SIDE"]
    bg_panel = colors["BG_PANEL"]
    bg_cell = colors["BG_CELL"]
    bg_hover = colors["BG_HOVER"]
    txt_pri = colors["TXT_PRI"]
    txt_sec = colors["TXT_SEC"]
    txt_mut = colors["TXT_MUT"]
    accent = colors["ACCENT"]
    clr_white = colors["CLR_WHITE"]
    btn_flat_bg = colors["button_bg"]
    btn_flat_text = colors["button_text"]
    btn_flat_text_disabled = colors["button_text_disabled"]
    clr_danger_bg = colors["CLR_DANGER_BG"]
    clr_danger = colors["CLR_DANGER"]
    clr_danger_hover = colors["CLR_DANGER_HOVER"]
    clr_danger_dark = colors["CLR_DANGER_DARK"]
    clr_success = colors["CLR_SUCCESS"]
    clr_success_dark = colors["CLR_SUCCESS_DARK"]
    warn = colors["WARN"]
    clr_warn_dark = colors["CLR_WARN_DARK"]

    # Notebook
    style.configure("AllWell.TNotebook", background=bg_app, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("AllWell.TNotebook.Tab", font=(*FM_UI[:1], 11, "bold"), padding=[20, 8], background=bg_side, foreground=txt_mut)
    style.map(
        "AllWell.TNotebook.Tab",
        background=[("selected", bg_panel), ("active", bg_side)],
        foreground=[("selected", accent),   ("active", txt_pri)],
        expand=[("selected", [0, 0, 0, 2])],
    )
    style.configure("TNotebook", background=bg_app, borderwidth=0)
    style.configure("TNotebook.Tab", font=FM_UI, padding=[12, 5], background=bg_side, foreground=txt_sec)
    style.map("TNotebook.Tab",
              background=[("selected", bg_panel), ("active", bg_side)],
              foreground=[("selected", txt_pri)])

    # Treeview / table widgets
    style.configure(
        "Treeview",
        background=bg_panel,
        fieldbackground=bg_panel,
        foreground=txt_pri,
        bordercolor=colors["BORDER"],
        lightcolor=colors["BORDER"],
        darkcolor=colors["BORDER"],
        rowheight=22,
    )
    style.map(
        "Treeview",
        background=[("selected", accent)],
        foreground=[("selected", clr_white)],
    )
    style.configure(
        "Treeview.Heading",
        background=bg_side,
        foreground=txt_pri,
        bordercolor=colors["BORDER"],
        lightcolor=colors["BORDER"],
        darkcolor=colors["BORDER"],
        font=FM_TINY,
    )
    style.map(
        "Treeview.Heading",
        background=[("active", bg_hover)],
        foreground=[("active", txt_pri)],
    )

    # Combobox
    style.configure("TCombobox", fieldbackground=bg_panel, background=bg_panel,
                    foreground=txt_pri, selectbackground=accent, selectforeground=clr_white,
                    arrowcolor=txt_sec)
    style.map("TCombobox",
              fieldbackground=[("readonly", bg_panel)],
              foreground=[("readonly", txt_pri)])

    # Combobox popdown (the dropdown list is a plain tk.Listbox, not a ttk widget,
    # so it must be styled via the option database rather than ttk styles)
    try:
        import tkinter as _tk
        _root = _tk._default_root
        if _root is not None:
            _root.option_add("*TCombobox*Listbox.background", bg_panel, "interactive")
            _root.option_add("*TCombobox*Listbox.foreground", txt_pri, "interactive")
            _root.option_add("*TCombobox*Listbox.selectBackground", accent, "interactive")
            _root.option_add("*TCombobox*Listbox.selectForeground", clr_white, "interactive")
    except Exception:
        pass

    # Legacy flat-dark action buttons
    for _name, _pad in _TBUTTON_PADDING.items():
        style.configure(_name, background=btn_flat_bg, foreground=btn_flat_text,
                        font=FM_TINY, borderwidth=0, focusthickness=0, padding=_pad)
        style.map(_name,
                  background=[("active",   btn_flat_bg), ("pressed", btn_flat_bg), ("disabled", btn_flat_bg)],
                  foreground=[("active",   btn_flat_text), ("pressed", btn_flat_text), ("disabled", btn_flat_text_disabled)])

    # Named button variants - dynamically construct based on theme colors
    _DYNAMIC_BUTTON_VARIANTS = {
        "Primary.TButton":      (accent,        clr_white,  accent,           FM_TINY),
        "PrimaryDark.TButton":  (colors["ACCENT_DARK"],   clr_white,  accent,           FM_BOLD),
        "Secondary.TButton":    (bg_cell,       txt_sec,    bg_hover,         FM_TINY),
        "Card.TButton":         (bg_cell,       txt_sec,    bg_hover,         FM_TINY),
        "Danger.TButton":       (clr_danger_bg, clr_danger, clr_danger_hover, FM_TINY),
        "SEM.TButton":          (accent,        clr_white,  colors["ACCENT_DARK"],      FM_BOLD),
        "SEMWarn.TButton":      (warn,          clr_white,  clr_warn_dark,    FM_BOLD),
        "Toggle.TButton":       (bg_cell,       txt_sec,    bg_hover,         FM_TINY),
        "ToggleActive.TButton": (accent,        clr_white,  colors["ACCENT_DARK"],      FM_TINY),
        "ToggleWarn.TButton":   (warn,          clr_white,  clr_warn_dark,    FM_TINY),
        "ToggleMuted.TButton":  (bg_cell,       txt_mut,    bg_hover,         FM_TINY),
        "ToggleAccent.TButton": (bg_cell,       accent,     bg_hover,         FM_TINY),
        "SideAccent.TButton":   (bg_side,       accent,     bg_hover,         FM_TINY),
        "SideMuted.TButton":    (bg_side,       txt_mut,    bg_hover,         FM_TINY),
        "Run.TButton":          (clr_success,   clr_white,  clr_success_dark, FM_BOLD),
        "Stop.TButton":         (clr_danger,    clr_white,  clr_danger_dark,  FM_BOLD),
    }

    # Named button variants
    for _name, (_bg, _fg, _abg, _font) in _DYNAMIC_BUTTON_VARIANTS.items():
        _pad = _TBUTTON_VARIANT_PADDING.get(_name, (8, 2))
        style.configure(_name, background=_bg, foreground=_fg, font=_font,
                        borderwidth=0, focusthickness=0, padding=_pad)
        style.map(_name,
                  background=[("active", _abg), ("pressed", _abg), ("disabled", _bg)],
                  foreground=[("active", _fg),  ("pressed", _fg),  ("disabled", btn_flat_text_disabled)])
