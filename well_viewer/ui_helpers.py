"""Reusable Qt UI helpers (button factories, scroll area, name dialog, etc.)."""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


def _btn(parent: Optional[QWidget], text: str, command: Optional[Callable[[], Any]], variant: str) -> QPushButton:
    b = QPushButton(text, parent)
    b.setProperty("variant", variant)
    if command is not None:
        b.clicked.connect(lambda _=False: command())
    return b


def btn_primary(parent: QWidget, text: str, command, *, padx: int = 8, pady: int = 2, **_kw) -> QPushButton:
    return _btn(parent, text, command, "primary")


def btn_secondary(parent: QWidget, text: str, command, *, padx: int = 6, pady: int = 2, **_kw) -> QPushButton:
    return _btn(parent, text, command, "secondary")


def btn_card(parent: QWidget, text: str, command, *, padx: int = 4, **_kw) -> QPushButton:
    return _btn(parent, text, command, "card")


def btn_danger(parent: QWidget, text: str, command, *, padx: int = 4, **_kw) -> QPushButton:
    return _btn(parent, text, command, "danger")


def tok_at_event(event: Any, btn_dict: dict) -> Optional[str]:
    """Return the well-token whose QPushButton lies under the pointer, or None.

    Accepts either a QMouseEvent (preferred) or a tk-style event with
    ``.widget`` / ``.x`` / ``.y`` attributes so legacy callers keep working.
    """
    pos = None
    sender = None
    for attr in ("position", "globalPosition"):
        if hasattr(event, attr):
            try:
                pos = getattr(event, attr)().toPoint()
                break
            except Exception:
                pass
    if pos is None and hasattr(event, "pos"):
        try:
            pos = event.pos()
        except Exception:
            pass
    for tok, btn in btn_dict.items():
        try:
            if btn is not None and btn.isVisible() and btn.underMouse():
                return tok
        except Exception:
            continue
    return None


def make_scrollable_canvas(parent: QWidget, **_kw) -> Tuple[QScrollArea, QWidget]:
    """Return (scroll_area, inner_widget). Caller lays widgets inside inner."""
    sa = QScrollArea(parent)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    inner = QWidget(sa)
    sa.setWidget(inner)
    QVBoxLayout(inner)
    return sa, inner


def bind_mousewheel_scroll(_scroll_area) -> None:
    """No-op: QScrollArea handles wheel events natively."""
    return


def ask_name_dialog(parent: QWidget, *, title: str, prompt: str, default: str,
                    width: int = 30, **_kw) -> Optional[str]:
    text, ok = QInputDialog.getText(parent, title, prompt, QLineEdit.Normal, default)
    if not ok:
        return None
    text = text.strip()
    return text or None
