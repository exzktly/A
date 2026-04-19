"""Qt theming utilities for the PySide6 migration (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    bg_app: str
    bg_panel: str
    bg_side: str
    border: str
    text_primary: str
    text_muted: str
    accent: str
    accent_hover: str


THEMES: dict[str, ThemeTokens] = {
    "Dark": ThemeTokens(
        bg_app="#111827",
        bg_panel="#1f2937",
        bg_side="#0f172a",
        border="#334155",
        text_primary="#e5e7eb",
        text_muted="#94a3b8",
        accent="#2563eb",
        accent_hover="#1d4ed8",
    ),
    "Light": ThemeTokens(
        bg_app="#f8fafc",
        bg_panel="#ffffff",
        bg_side="#e2e8f0",
        border="#cbd5e1",
        text_primary="#0f172a",
        text_muted="#475569",
        accent="#2563eb",
        accent_hover="#1d4ed8",
    ),
}


def theme_names() -> list[str]:
    return list(THEMES.keys())


def build_stylesheet(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES["Dark"])
    return f"""
    QWidget {{
        background: {t.bg_app};
        color: {t.text_primary};
    }}
    QGroupBox {{
        border: 1px solid {t.border};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 8px;
        background: {t.bg_panel};
    }}
    QGroupBox::title {{
        color: {t.text_muted};
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QTabWidget::pane {{
        border: 1px solid {t.border};
        background: {t.bg_panel};
    }}
    QTabBar::tab {{
        background: {t.bg_side};
        border: 1px solid {t.border};
        padding: 6px 12px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {t.bg_panel};
    }}
    QPushButton {{
        background: {t.accent};
        border: 1px solid {t.accent_hover};
        border-radius: 4px;
        color: #ffffff;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background: {t.accent_hover};
    }}
    QLineEdit, QListWidget, QTextEdit, QPlainTextEdit {{
        background: {t.bg_panel};
        border: 1px solid {t.border};
        color: {t.text_primary};
    }}
    QLabel {{
        color: {t.text_primary};
    }}
    """


def apply_theme(app, theme_name: str) -> None:
    app.setStyleSheet(build_stylesheet(theme_name))
