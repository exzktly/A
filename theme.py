"""
theme.py
--------
Design tokens for the All-Well v2 interface, translated from
``design/DESIGN_TOKENS.md``, plus a base Qt stylesheet builder.

This module is the single source of truth for colors, typography, spacing,
and radii. Widget code should read the constants here rather than hardcoding
values, and the application-wide chrome comes from :func:`qss`.

Names mirror ``DESIGN_TOKENS.md``; where the design doc's CSS custom-property
name differs from the name used in code, the original ``--token`` name is noted
in a trailing comment.
"""

from __future__ import annotations


class Colors:
    """Color tokens (DESIGN_TOKENS.md §1)."""

    # ── Surfaces (in increasing elevation) ───────────────────────────────
    titlebar        = "#0A0E15"   # --bg-titlebar  : top window chrome
    surface         = "#0B0F17"   # --bg-app       : app canvas / deepest backdrop
    rail            = "#0E131C"   # --bg-rail      : left rail + properties rail base
    panel           = "#131A24"   # --bg-panel     : cards / sub-panels
    panel_elevated  = "#1A2230"   # --bg-elevated  : default button/input fill
    hover           = "#212B3B"   # --bg-hover     : hover state for controls/rows
    active          = "#2A3548"   # --bg-active    : pressed / selected state

    # ── Borders / dividers ───────────────────────────────────────────────
    border_subtle   = "#1B2331"   # --border-subtle : hairlines within a panel
    border          = "#2A3343"   # --border        : default control border
    border_strong   = "#3B475C"   # --border-strong : hover/focus ring on inputs

    # ── Text ─────────────────────────────────────────────────────────────
    text_primary    = "#E6E9EF"   # --text-primary   : body, headings, primary labels
    text_secondary  = "#98A2B3"   # --text-secondary : labels-on-controls, metadata
    text_muted      = "#5F6B7C"   # --text-muted     : hints, inactive labels, ticks
    text_faint      = "#404B5C"   # --text-faint     : decorative separators

    # ── Accent (interactive / brand) ─────────────────────────────────────
    accent          = "#6B8AFD"   # --accent
    accent_hover    = "#84A0FF"   # --accent-hover
    accent_pressed  = "#5772E6"   # darkened --accent for :pressed (not a token)
    accent_dim      = "#2C3A66"   # --accent-dim : low-emphasis selected backgrounds
    accent_fg       = "#F0F4FF"   # --accent-fg  : text/icon on accent-filled buttons

    # ── Status ───────────────────────────────────────────────────────────
    success         = "#4ADE80"   # --success
    warn            = "#F59E0B"   # --warn
    danger          = "#F87171"   # --danger

    # ── Data-viz / trace colors (categorical, keyed to wells) ────────────
    trace           = ("#5B9BF8", "#F26B6B", "#4ADE80", "#F5A524")  # --trace-1..4
    threshold       = "#F5A524"   # --threshold  : dashed line + threshold chip
    plot_bg         = "#131A24"   # plot card fill (== panel)
    plot_grid       = "#1F2733"   # --plot-grid  : gridlines inside the figure
    plot_spine      = "#3A4658"   # --plot-spine : axis spines

    # ── Translucent overlays (rgba; kept as editable constants) ──────────
    inset_hilite    = "rgba(255, 255, 255, 0.30)"  # top inset on "lit" wells
    inset_shadow    = "rgba(0, 0, 0, 0.30)"        # bottom inset on "lit" wells
    focus_ring      = "rgba(107, 138, 253, 0.35)"  # --ring-focus
    drop_shadow_md  = "rgba(0, 0, 0, 0.35)"        # --sh-2 floating overlay shadow
    inner_line_dk   = "rgba(0, 0, 0, 0.40)"        # --sh-1 hairline drop
    success_glow    = "rgba(74, 222, 128, 0.12)"   # halo around the "saved" dot


class Typography:
    """Type tokens (DESIGN_TOKENS.md §2)."""

    family      = '"Inter", "SF Pro Text", "Segoe UI", system-ui, sans-serif'
    family_mono = '"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace'

    # font sizes (px) — §2.2
    caption_size = 11   # --fs-caption : section eyebrows, tick labels
    small_size   = 12   # --fs-small   : buttons, segmented text, status bar
    body_size    = 13   # --fs-body    : default body, list rows, property labels
    emph_size    = 14   # --fs-emph    : emphasized inline labels, control values
    h3_size      = 15   # --fs-h3      : panel sub-titles
    h2_size      = 17   # --fs-h2      : plot card titles, dialog titles

    # weights — §2.3 (CSS numeric values; map to QFont.Weight in widget code)
    regular  = 400
    medium   = 500
    semibold = 600
    bold     = 700

    # (size, weight) pairs per role
    title   = (h2_size,      semibold)   # plot card / dialog titles
    heading = (h3_size,      semibold)   # panel sub-titles ("Quick select")
    body    = (body_size,    regular)    # default body text, list rows
    label   = (small_size,   medium)     # labels-on-controls, button text
    caption = (caption_size, medium)     # uppercase eyebrow section labels, ticks
    mono    = (small_size,   regular)    # numeric readouts (use ``family_mono``)


class Spacing:
    """4-px linear spacing scale (DESIGN_TOKENS.md §3)."""

    xs  = 4    # --s-1 : icon ↔ label gap, tightest gutter
    sm  = 8    # --s-2 : default control gap
    md  = 12   # --s-3 : field-row gap, padding inside cards
    lg  = 16   # --s-4 : padding inside panels, gap between blocks
    xl  = 24   # --s-6 : outer gutter between major panels
    xxl = 32   # --s-8 : rare large empty-state padding


class Radii:
    """Border-radius tokens (DESIGN_TOKENS.md §4)."""

    xs   = 3     # --r-xs   : file chip, logo tile, tiny inline indicators
    sm   = 5     # --r-sm   : buttons, inputs, chips — dominant radius
    md   = 8     # --r-md   : cards (plot card, plate card, panel sections)
    lg   = 12    # --r-lg   : floating overlays (toasts, drawers, dialogs)
    pill = 999   # --r-pill : status dot rings, count badges


def qss() -> str:
    """Return the application-wide base stylesheet.

    All color values are interpolated from :class:`Colors` / :class:`Typography`
    / :class:`Radii` / :class:`Spacing`; there are no hardcoded hex literals in
    the returned string.
    """
    c, t, r, s = Colors, Typography, Radii, Spacing
    return f"""
* {{
    font-family: {t.family};
    font-size: {t.body_size}px;
    color: {c.text_primary};
    selection-background-color: {c.accent};
    selection-color: {c.accent_fg};
    outline: 0;
}}

QWidget {{
    background-color: {c.surface};
    color: {c.text_primary};
}}
QMainWindow, QDialog {{
    background-color: {c.surface};
}}
QScrollArea {{
    background-color: {c.surface};
    border: 0;
}}

/* ── Structural frames (opt-in via objectName / dynamic property) ─────── */
QFrame#Panel, QFrame[panel="true"] {{
    background-color: {c.panel};
    border: 1px solid {c.border_subtle};
    border-radius: {r.md}px;
}}
QFrame#Rail, QFrame[rail="true"] {{
    background-color: {c.rail};
    border: none;
}}
QFrame#Titlebar {{
    background-color: {c.titlebar};
    border-bottom: 1px solid {c.border_subtle};
}}
QFrame[hline="true"], QFrame[vline="true"], QFrame#Separator {{
    background-color: {c.border_subtle};
    border: none;
}}

/* ── Labels ──────────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {c.text_primary};
}}
QLabel#Title {{
    font-size: {t.h2_size}px;
    font-weight: {t.semibold};
}}
QLabel#Heading {{
    font-size: {t.h3_size}px;
    font-weight: {t.semibold};
}}
QLabel#Caption, QLabel[caption="true"] {{
    font-size: {t.caption_size}px;
    font-weight: {t.medium};
    color: {c.text_muted};
}}
QLabel#Secondary, QLabel[secondary="true"] {{
    color: {c.text_secondary};
}}
QLabel#Mono, QLabel[mono="true"] {{
    font-family: {t.family_mono};
    font-size: {t.small_size}px;
}}
QLabel#Danger  {{ color: {c.danger}; }}
QLabel#Success {{ color: {c.success}; }}
QLabel#Warn    {{ color: {c.warn}; }}

/* ── Buttons ─────────────────────────────────────────────────────────── */
QPushButton, QToolButton {{
    background-color: {c.panel_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border_subtle};
    border-radius: {r.sm}px;
    padding: 6px 10px;
    font-size: {t.small_size}px;
    font-weight: {t.medium};
}}
QToolButton {{
    padding: 4px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {c.hover};
    border-color: {c.border};
}}
QPushButton:pressed, QToolButton:pressed,
QPushButton:checked, QToolButton:checked {{
    background-color: {c.active};
}}
QPushButton:disabled, QToolButton:disabled {{
    color: {c.text_muted};
    background-color: {c.panel};
    border-color: {c.border_subtle};
}}

QPushButton#Primary {{
    background-color: {c.accent};
    border-color: {c.accent};
    color: {c.accent_fg};
    font-weight: {t.semibold};
}}
QPushButton#Primary:hover {{
    background-color: {c.accent_hover};
    border-color: {c.accent_hover};
}}
QPushButton#Primary:pressed {{
    background-color: {c.accent_pressed};
    border-color: {c.accent_pressed};
}}
QPushButton#Primary:disabled {{
    background-color: {c.accent_dim};
    border-color: {c.accent_dim};
    color: {c.text_muted};
}}

QPushButton#Danger {{
    background-color: transparent;
    border-color: {c.border_subtle};
    color: {c.danger};
}}
QPushButton#Danger:hover {{
    background-color: {c.panel};
}}

QPushButton#Ghost, QToolButton#Ghost {{
    background-color: transparent;
    border-color: transparent;
}}
QPushButton#Ghost:hover, QToolButton#Ghost:hover {{
    background-color: {c.panel};
}}

/* ── Text inputs / steppers ──────────────────────────────────────────── */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c.panel_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.sm}px;
    padding: 5px 8px;
    selection-background-color: {c.accent};
    selection-color: {c.accent_fg};
}}
QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {c.border_strong};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {c.accent};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {c.text_muted};
    background-color: {c.panel};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {c.panel_elevated};
    border: none;
    width: 14px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {c.hover};
}}

/* ── Combo box ───────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {c.panel_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.sm}px;
    padding: 5px 8px;
}}
QComboBox:hover {{
    border-color: {c.border_strong};
}}
QComboBox:focus, QComboBox:on {{
    border-color: {c.accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background-color: {c.panel};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.sm}px;
    selection-background-color: {c.accent_dim};
    selection-color: {c.text_primary};
    outline: 0;
}}

/* ── Check / radio ───────────────────────────────────────────────────── */
QCheckBox, QRadioButton {{
    background: transparent;
    color: {c.text_primary};
    spacing: {s.sm}px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    background-color: {c.panel_elevated};
    border: 1px solid {c.border};
}}
QCheckBox::indicator {{
    border-radius: {r.xs}px;
}}
QRadioButton::indicator {{
    border-radius: 7px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {c.border_strong};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c.accent};
    border-color: {c.accent};
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: {c.text_muted};
}}

/* ── Slider ──────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {c.border_subtle};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background-color: {c.accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: {c.panel_elevated};
    border: 2px solid {c.rail};
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {c.hover};
}}

/* ── Tabs ────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {c.surface};
    border: 1px solid {c.border_subtle};
    border-radius: {r.md}px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {c.text_secondary};
    border: none;
    padding: 8px 14px;
    font-size: {t.small_size}px;
    font-weight: {t.medium};
}}
QTabBar::tab:hover {{
    color: {c.text_primary};
}}
QTabBar::tab:selected {{
    color: {c.text_primary};
    border-bottom: 2px solid {c.accent};
}}

/* ── Menus ───────────────────────────────────────────────────────────── */
QMenu {{
    background-color: {c.panel};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.sm}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 18px;
    border-radius: {r.xs}px;
}}
QMenu::item:selected {{
    background-color: {c.accent_dim};
}}
QMenu::separator {{
    height: 1px;
    background-color: {c.border_subtle};
    margin: 4px 6px;
}}

/* ── Tooltip ─────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {c.panel};
    color: {c.text_primary};
    border: 1px solid {c.border};
    border-radius: {r.xs}px;
    padding: 4px 6px;
}}

/* ── Group box ───────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {c.panel};
    border: 1px solid {c.border_subtle};
    border-radius: {r.md}px;
    margin-top: {s.md}px;
    padding: {s.md}px;
    font-weight: {t.semibold};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: {s.md}px;
    padding: 0 4px;
    color: {c.text_secondary};
}}

/* ── Lists / trees / tables ──────────────────────────────────────────── */
QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{
    background-color: {c.panel};
    color: {c.text_primary};
    border: 1px solid {c.border_subtle};
    border-radius: {r.sm}px;
    outline: 0;
    selection-background-color: {c.accent_dim};
    selection-color: {c.text_primary};
}}
QListView::item, QListWidget::item, QTreeView::item, QTreeWidget::item {{
    padding: 4px 6px;
    border-radius: {r.xs}px;
}}
QListView::item:hover, QListWidget::item:hover,
QTreeView::item:hover, QTreeWidget::item:hover {{
    background-color: {c.hover};
}}
QListView::item:selected, QListWidget::item:selected,
QTreeView::item:selected, QTreeWidget::item:selected {{
    background-color: {c.accent_dim};
}}
QHeaderView::section {{
    background-color: {c.panel_elevated};
    color: {c.text_secondary};
    border: none;
    border-bottom: 1px solid {c.border_subtle};
    padding: 5px 8px;
    font-weight: {t.medium};
}}

/* ── Splitter ────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {c.border_subtle};
}}
QSplitter::handle:hover {{
    background-color: {c.border_strong};
}}

/* ── Scrollbars ──────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: {c.border};
    border-radius: 5px;
    min-height: 24px;
    min-width: 24px;
}}
QScrollBar::handle:hover {{
    background-color: {c.border_strong};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
    background: transparent;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ── Progress bar ────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {c.panel_elevated};
    border: 1px solid {c.border_subtle};
    border-radius: {r.sm}px;
    text-align: center;
    color: {c.text_primary};
}}
QProgressBar::chunk {{
    background-color: {c.accent};
    border-radius: {r.sm}px;
}}
"""
