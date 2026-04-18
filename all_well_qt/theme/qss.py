"""Build a full Qt Style Sheet string from a palette token dict."""

from __future__ import annotations


def build_qss(t: dict) -> str:
    """Return QSS stylesheet for the given palette token dict."""
    return f"""
/* ── Global ─────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {t['bg']};
    color: {t['ink']};
    font-family: "Geist", "SF Pro Text", "Segoe UI", system-ui, sans-serif;
    font-size: 12px;
}}

QMainWindow, QDialog {{
    background-color: {t['bg']};
}}

/* ── Frames / Cards ──────────────────────────────────────────────────── */
QFrame#card {{
    background-color: {t['panel']};
    border-radius: 14px;
    border: 1px solid {t['line']};
}}

QFrame#sunkFrame {{
    background-color: {t['sunk']};
    border-radius: 10px;
    border: 1px solid {t['line']};
}}

/* ── Buttons ─────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {t['sunk']};
    color: {t['ink_2']};
    border: 1px solid {t['line']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {t['line']};
    color: {t['ink']};
}}
QPushButton:pressed {{
    background-color: {t['sunk']};
}}
QPushButton:disabled {{
    color: {t['mut']};
    border-color: {t['line']};
}}

QPushButton#primary {{
    background-color: {t['accent']};
    color: {t['panel']};
    border: none;
    border-radius: 6px;
    padding: 5px 14px;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: {t['accent_ink']};
}}

QPushButton#pill {{
    border-radius: 999px;
    padding: 5px 14px;
}}

QPushButton#pillTab {{
    background-color: transparent;
    color: {t['mut']};
    border: none;
    border-radius: 999px;
    padding: 5px 14px;
    font-weight: 500;
    font-size: 12px;
}}
QPushButton#pillTab:hover {{
    color: {t['ink_2']};
    background-color: {t['sunk']};
}}
QPushButton#pillTab:checked {{
    background-color: {t['panel']};
    color: {t['ink']};
    font-weight: 600;
}}

QPushButton#chip {{
    background-color: transparent;
    color: {t['mut']};
    border: none;
    border-radius: 8px;
    padding: 5px 11px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#chip:hover {{
    color: {t['ink_2']};
}}
QPushButton#chip:checked {{
    background-color: {t['panel']};
    color: {t['ink']};
}}

QPushButton#ghost {{
    background-color: transparent;
    border: none;
    color: {t['mut']};
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 12px;
}}
QPushButton#ghost:hover {{
    background-color: {t['sunk']};
    color: {t['ink']};
}}

QPushButton#run {{
    background-color: {t['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 700;
}}
QPushButton#run:hover {{
    background-color: {t['accent_ink']};
}}

QPushButton#stop {{
    background-color: {t['danger']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 700;
}}

QPushButton#tweakToggle {{
    background-color: {t['sunk']};
    color: {t['ink']};
    border: 1px solid {t['line']};
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 13px;
}}
QPushButton#tweakToggle:hover {{
    background-color: {t['line']};
}}
QPushButton#tweakToggle:checked {{
    background-color: {t['accent']};
    color: {t['panel']};
    border-color: {t['accent']};
}}

/* ── Labels ──────────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {t['ink']};
}}
QLabel#muted {{
    color: {t['mut']};
    font-size: 11px;
}}
QLabel#section {{
    color: {t['mut']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QLabel#panelTitle {{
    color: {t['ink']};
    font-size: 13px;
    font-style: italic;
    font-family: "Instrument Serif", "Georgia", serif;
    font-weight: 400;
}}
QLabel#badge {{
    background-color: {t['accent_soft']};
    color: {t['accent_ink']};
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#popBadge {{
    background-color: {t['pop_soft']};
    color: {t['pop']};
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

/* ── Line Edits / Fields ─────────────────────────────────────────────── */
QLineEdit {{
    background-color: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['line']};
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 12px;
    selection-background-color: {t['accent_soft']};
}}
QLineEdit:focus {{
    border-color: {t['accent']};
}}

QLineEdit#fieldInput {{
    background: transparent;
    border: none;
    color: {t['ink']};
    font-family: "Geist Mono", "Menlo", "Consolas", monospace;
    font-size: 12px;
    font-weight: 500;
    padding: 0;
}}

/* ── Combo Box ───────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['line']};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}}
QComboBox:focus {{
    border-color: {t['accent']};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['line']};
    selection-background-color: {t['accent_soft']};
    selection-color: {t['accent_ink']};
}}

/* ── Scroll Areas ────────────────────────────────────────────────────── */
QScrollArea, QAbstractScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['line']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t['mut']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t['line']};
    border-radius: 3px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t['mut']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Splitter ────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {t['line']};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── Tab Widget ──────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {t['mut']};
    padding: 5px 12px;
    font-size: 12px;
    border: none;
}}
QTabBar::tab:selected {{
    color: {t['ink']};
    font-weight: 600;
    border-bottom: 2px solid {t['accent']};
}}
QTabBar::tab:hover {{
    color: {t['ink_2']};
}}

/* ── List Widget ─────────────────────────────────────────────────────── */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 2px 0;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {t['accent_soft']};
    color: {t['accent_ink']};
}}
QListWidget::item:hover {{
    background-color: {t['sunk']};
}}

/* ── Menu ────────────────────────────────────────────────────────────── */
QMenu {{
    background-color: {t['panel']};
    color: {t['ink']};
    border: 1px solid {t['line']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {t['sunk']};
}}
QMenu::separator {{
    height: 1px;
    background: {t['line']};
    margin: 4px 8px;
}}

/* ── Tooltip ─────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {t['ink']};
    color: {t['bg']};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Status Bar ──────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {t['panel']};
    color: {t['mut']};
    border-top: 1px solid {t['line']};
    font-size: 11px;
    padding: 0 10px;
}}

/* ── Top Bar ─────────────────────────────────────────────────────────── */
QWidget#topBar {{
    background-color: {t['panel']};
    border-bottom: 1px solid {t['line']};
}}

/* ── Pill Tab Rail ───────────────────────────────────────────────────── */
QWidget#pillRail {{
    background-color: {t['sunk']};
    border-radius: 999px;
    padding: 2px;
}}

/* ── Chip Group Rail ─────────────────────────────────────────────────── */
QWidget#chipRail {{
    background-color: {t['sunk']};
    border-radius: 10px;
    padding: 2px;
}}

/* ── Side Panel ──────────────────────────────────────────────────────── */
QWidget#sidePanel {{
    background-color: {t['bg']};
}}

/* ── Plate Card ──────────────────────────────────────────────────────── */
QFrame#plateCard {{
    background-color: {t['panel']};
    border-radius: 14px;
    border: 1px solid {t['line']};
}}

/* ── Sample Group Row ────────────────────────────────────────────────── */
QFrame#groupRow {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 4px;
}}
QFrame#groupRow:hover {{
    border-color: {t['ink_2']};
    background-color: {t['sunk']};
}}

/* ── Tweaks Popup ────────────────────────────────────────────────────── */
QFrame#tweaksPanel {{
    background-color: {t['panel']};
    border: 1px solid {t['line']};
    border-radius: 14px;
}}

/* ── Graphics View (plate map) ───────────────────────────────────────── */
QGraphicsView {{
    background: transparent;
    border: none;
    outline: none;
}}
"""
