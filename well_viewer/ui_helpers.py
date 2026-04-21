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

    Accepts a pre-computed ``event.tok`` shim (fast path), a QMouseEvent, or
    a tk-style event with ``.widget`` / ``.x`` / ``.y`` attributes.
    """
    tok_attr = getattr(event, "tok", None)
    if tok_attr is not None and tok_attr in btn_dict:
        return tok_attr
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


def make_plot_with_right_dock(parent: QWidget) -> Tuple[QWidget, QVBoxLayout, QWidget]:
    """Build a ``plot | right-dock`` split container inside ``parent``.

    Returns ``(plot_area, plot_layout, right_dock)`` — callers lay their
    figure/toolbar into ``plot_layout`` and the export-style sidebar docks
    into ``right_dock``. The dock starts empty (hidden) so it occupies no
    space until the sidebar is shown.
    """
    root = parent.layout()
    if root is None:
        root = QVBoxLayout(parent)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

    split = QWidget(parent)
    hbox = QHBoxLayout(split)
    hbox.setContentsMargins(0, 0, 0, 0)
    hbox.setSpacing(0)

    plot_area = QWidget(split)
    plot_layout = QVBoxLayout(plot_area)
    plot_layout.setContentsMargins(0, 0, 0, 0)
    plot_layout.setSpacing(0)
    hbox.addWidget(plot_area, 1)

    right_dock = QWidget(split)
    right_dock_layout = QVBoxLayout(right_dock)
    right_dock_layout.setContentsMargins(0, 0, 0, 0)
    right_dock_layout.setSpacing(0)
    right_dock.setVisible(False)
    hbox.addWidget(right_dock, 0)

    root.addWidget(split, 1)
    return plot_area, plot_layout, right_dock


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


class ComboVar:
    """``tk.StringVar``-shaped shim over a ``QComboBox``.

    Legacy callers expect ``.get()``/``.set(value)`` semantics; this wraps the
    current text of a combo so those call sites keep working while tabs migrate
    to reading the widget directly.
    """
    __slots__ = ("_cb",)

    def __init__(self, cb) -> None:
        self._cb = cb

    def get(self) -> str:
        return self._cb.currentText()

    def set(self, value: str) -> None:
        self._cb.setCurrentText(str(value))


class LineEditVar:
    """tk.StringVar-shaped shim over a ``QLineEdit``."""
    __slots__ = ("_le",)

    def __init__(self, le) -> None:
        self._le = le

    def get(self) -> str:
        return self._le.text()

    def set(self, value: str) -> None:
        self._le.setText(str(value))


class CheckBoxVar:
    """tk.BooleanVar-shaped shim over a ``QCheckBox``."""
    __slots__ = ("_cb",)

    def __init__(self, cb) -> None:
        self._cb = cb

    def get(self) -> bool:
        return self._cb.isChecked()

    def set(self, value: bool) -> None:
        self._cb.setChecked(bool(value))


class BoolVar:
    """Plain boolean holder with tk.BooleanVar ``.get()``/``.set()`` semantics."""
    __slots__ = ("_v",)

    def __init__(self, initial: bool = False) -> None:
        self._v = bool(initial)

    def get(self) -> bool:
        return self._v

    def set(self, value: bool) -> None:
        self._v = bool(value)
