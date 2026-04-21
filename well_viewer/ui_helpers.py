"""Reusable Qt UI helpers (button factories, scroll area, name dialog, etc.)."""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


def build_section_header(
    parent: QWidget,
    title: str,
    *,
    hint: Optional[str] = None,
    buttons: tuple = (),
    margins: tuple = (8, 4, 8, 4),
) -> QWidget:
    """Return a "Sidebar"-styled header row with a section title.

    ``buttons`` is a sequence of already-constructed QWidgets that are added
    after a stretch. ``hint`` is an optional muted label shown right after
    the title.
    """
    hdr = QWidget(parent)
    hdr.setObjectName("Sidebar")
    hl = QHBoxLayout(hdr)
    hl.setContentsMargins(*margins)
    lbl = QLabel(title, hdr)
    lbl.setProperty("role", "section")
    hl.addWidget(lbl)
    if hint:
        hint_lbl = QLabel(hint, hdr)
        hint_lbl.setObjectName("Muted")
        hl.addWidget(hint_lbl)
    hl.addStretch(1)
    for btn in buttons:
        hl.addWidget(btn)
    return hdr


def build_hline_separator(parent: QWidget) -> QFrame:
    """Return the project's standard 1-px horizontal separator frame."""
    sep = QFrame(parent)
    sep.setObjectName("Separator")
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    return sep


def clear_layout(layout) -> None:
    """Remove every widget and sub-layout from *layout*, freeing them."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
            continue
        child = item.layout()
        if child is not None:
            clear_layout(child)


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


def install_canvas_wheel_scroll(canvas, scroll_area) -> None:
    """Forward wheel events from a matplotlib canvas to ``scroll_area``.

    FigureCanvasQTAgg accepts wheel events for its own toolbar zoom, so a
    QScrollArea wrapping it never sees them. This installs a wheelEvent
    override that forwards the vertical wheel delta to the scroll area's
    vertical scrollbar when no modifier key is held.
    """
    orig_wheel = getattr(canvas, "wheelEvent", None)

    def _wheel(event):
        if event.modifiers() == Qt.NoModifier:
            vbar = scroll_area.verticalScrollBar()
            if vbar is not None and (vbar.maximum() - vbar.minimum()) > 0:
                vbar.setValue(vbar.value() - event.angleDelta().y())
                event.accept()
                return
        if callable(orig_wheel):
            orig_wheel(event)

    canvas.wheelEvent = _wheel


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


_THEMED_NAV_CLS = None


def _themed_nav_toolbar_class():
    """Return a cached NavigationToolbar2QT subclass that recolors icons from theme tokens.

    The base class decides icon color from the QPalette background value, which
    QSS does not update — so in Light theme icons came out white on a styled
    light background. This subclass reads the current theme's ``TXT_PRI`` and
    repaints the icons directly.
    """
    global _THEMED_NAV_CLS
    if _THEMED_NAV_CLS is not None:
        return _THEMED_NAV_CLS

    from matplotlib import cbook
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

    class _ThemedNavToolbar(NavigationToolbar2QT):
        def _icon(self, name):
            path_regular = cbook._get_data_path("images", name)
            path_large = path_regular.with_name(
                path_regular.name.replace(".png", "_large.png")
            )
            filename = str(path_large if path_large.exists() else path_regular)
            pm = QPixmap(filename)
            pm.setDevicePixelRatio(self.devicePixelRatioF() or 1)
            try:
                from ui.theme import get_color
                icon_color = QColor(get_color("TXT_PRI"))
            except Exception:
                icon_color = self.palette().color(self.foregroundRole())
            mask = pm.createMaskFromColor(QColor("black"), Qt.MaskMode.MaskOutColor)
            pm.fill(icon_color)
            pm.setMask(mask)
            return QIcon(pm)

        def refresh_icons(self) -> None:
            """Rebuild action icons after a theme change."""
            for _text, _tip, image_file, callback in self.toolitems:
                if image_file is None:
                    continue
                action = self._actions.get(callback)
                if action is None:
                    continue
                action.setIcon(self._icon(image_file + ".png"))

    _THEMED_NAV_CLS = _ThemedNavToolbar
    return _ThemedNavToolbar


def attach_plot_toolbar(
    layout,
    canvas,
    parent: QWidget,
    app: Any = None,
    *,
    with_sem: bool = True,
) -> Any:
    """Create a themed matplotlib nav toolbar, append it to *layout* (at bottom),
    and optionally embed the shared SEM/SD toggle button.

    Returns the toolbar. When ``with_sem`` and ``app`` are provided, the toolbar
    hosts a SEM/SD button wired through ``app._toggle_sem``; ``app._sem_btns``
    collects every such button so ``_toggle_sem`` can update them all.
    """
    cls = _themed_nav_toolbar_class()
    toolbar = cls(canvas, parent)
    toolbar.setObjectName("PlotToolbar")

    if with_sem and app is not None:
        toolbar.addSeparator()
        eb_lbl = QLabel(" Error Band ", toolbar)
        eb_lbl.setObjectName("Muted")
        toolbar.addWidget(eb_lbl)
        initial = bool(getattr(app, "_use_sem", None) and app._use_sem.get())
        sem_btn = QPushButton("SEM" if initial else "SD", toolbar)
        sem_btn.setProperty("variant", "sem" if initial else "sem_warn")
        sem_btn.clicked.connect(lambda _=False: app._toggle_sem())
        toolbar.addWidget(sem_btn)
        if not hasattr(app, "_sem_btns") or app._sem_btns is None:
            app._sem_btns = []
        app._sem_btns.append(sem_btn)
        if not getattr(app, "_sem_btn", None):
            app._sem_btn = sem_btn

    layout.addWidget(toolbar)
    return toolbar


def refresh_plot_toolbar_icons(widget: QWidget) -> None:
    """Find every embedded ``PlotToolbar`` under *widget* and recolor its icons."""
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
    for tb in widget.findChildren(NavigationToolbar2QT):
        if tb.objectName() == "PlotToolbar" and hasattr(tb, "refresh_icons"):
            tb.refresh_icons()
