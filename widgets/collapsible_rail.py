"""CollapsibleRail — right-side rail overlay that floats above the host.

Anchored to a host widget's right edge (like ``widgets.Drawer``) but with
**no backdrop** and **no Esc dismissal**: it stays in whatever state the
caller picked until ``toggle()`` flips it. Used by the v2 app shell to
host the Properties rail without stealing canvas width — when collapsed
the rail slides off-screen to the right; when expanded it sits over the
canvas's right edge.

Visual target matches ``design/mockup-decoded.html``'s ``.main`` third
column (332 px) but the canvas underneath keeps its full width.

API
---
* ``CollapsibleRail(host, parent=None, *, width=332, collapsed=False, animation_ms=180)``
* ``setContentWidget(widget)`` / ``contentWidget() -> QWidget | None``
* ``setCollapsed(bool)`` / ``isCollapsed() -> bool`` / ``toggle()``
* ``setRailWidth(int)`` — change the expanded width (re-animates if visible).
* signal ``collapsedChanged(bool)`` — fires after the slide animation finishes.

Implementation notes:
* The widget is *not* a layout sibling of the canvas. It is reparented to
  ``host`` (the visual surface it floats over) and uses ``setGeometry``
  + ``QPropertyAnimation`` on ``geometry`` to slide in/out from the host's
  right edge.
* ``installEventFilter(host)`` keeps the rail glued to the host's right
  edge when the host resizes. Re-render and re-anchor are debounced
  through the standard Qt event loop.
* No backdrop / no Esc handler — the caller owns the toggle (typically a
  titlebar IconButton); the rail stays visible until the caller closes it.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import (  # noqa: E402
    QEasingCurve, QEvent, QPropertyAnimation, QRect, Qt, Signal,
)
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402


class CollapsibleRail(QFrame):
    collapsedChanged = Signal(bool)

    def __init__(self, host: QWidget, parent: QWidget | None = None, *,
                 width: int = 332, collapsed: bool = False,
                 animation_ms: int = 180) -> None:
        super().__init__(parent or host)
        self.setObjectName("CollapsibleRail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Overlay on top of host's other children; rely on raise_() at show
        # time and on z-order via parenting.
        self._host = host
        self._rail_width = max(0, int(width))
        self._collapsed = bool(collapsed)
        self._content: QWidget | None = None
        self._handle: QWidget | None = None  # built lazily by setEdgeHandle()

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(int(animation_ms))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        host.installEventFilter(self)
        self.setStyleSheet(self._build_qss())

        # Anchor without animating so the first paint sits at the right
        # position (off-screen if collapsed, flush against the host's right
        # edge otherwise).
        self._anchor(animate=False)
        self.setVisible(not self._collapsed)
        self.raise_()

    # ── content ──────────────────────────────────────────────────────────
    def setContentWidget(self, widget: QWidget) -> None:
        if self._content is widget:
            return
        if self._content is not None:
            self._lay.removeWidget(self._content)
            self._content.setParent(None)
        self._content = widget
        if widget is not None:
            widget.setParent(self)
            self._lay.addWidget(widget)

    def contentWidget(self) -> QWidget | None:
        return self._content

    # ── collapse state ───────────────────────────────────────────────────
    def isCollapsed(self) -> bool:
        return self._collapsed

    def setCollapsed(self, collapsed: bool) -> None:
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self._anchor(animate=True)

    def toggle(self) -> None:
        self.setCollapsed(not self._collapsed)

    # ── edge handle ──────────────────────────────────────────────────────
    def installEdgeHandle(self) -> QWidget:
        """Add a small clickable handle on the host's right edge that
        toggles the rail. Always visible regardless of rail state — when
        the rail is open the handle sits against its left edge; when
        collapsed it floats at the host's right edge. Discoverable
        affordance for "where did the rail go?".
        """
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QPushButton
        if self._handle is not None:
            return self._handle
        h = QPushButton(self._host)
        h.setObjectName("RailEdgeHandle")
        # ~1 char wide × 4 lines tall — was (14, 64) hardcoded.
        _fm = self.fontMetrics()
        h.setFixedSize(QSize(max(10, _fm.averageCharWidth() * 2),
                             max(40, _fm.height() * 4)))
        h.setCursor(QCursor(Qt.PointingHandCursor))
        h.setFocusPolicy(Qt.NoFocus)
        h.setToolTip("Show / hide the Properties rail")
        h.setText("▸")  # arrow points inward (toward the rail when collapsed)
        h.clicked.connect(self.toggle)
        h.setStyleSheet(self._handle_qss())
        self._handle = h
        self._reposition_handle()
        h.show()
        h.raise_()
        return h

    def _handle_qss(self) -> str:
        c = theme.Colors
        return f"""
        QPushButton#RailEdgeHandle {{
            background-color: {c.panel_elevated};
            border: 1px solid {c.border_subtle};
            border-right: 0;
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
            color: {c.text_secondary};
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton#RailEdgeHandle:hover {{
            background-color: {c.hover};
            color: {c.text_primary};
        }}
        """

    def _reposition_handle(self) -> None:
        if self._handle is None:
            return
        host_w = self._host.width()
        host_h = self._host.height()
        # When collapsed: handle sits at host's right edge. When expanded:
        # handle sits at the rail's left edge (= host.width - rail_width).
        if self._collapsed:
            x = host_w - self._handle.width()
            self._handle.setText("◂")
        else:
            x = max(0, host_w - self._rail_width - self._handle.width())
            self._handle.setText("▸")
        y = max(0, (host_h - self._handle.height()) // 2)
        self._handle.move(x, y)
        self._handle.raise_()

    def setRailWidth(self, width: int) -> None:
        width = max(0, int(width))
        if width == self._rail_width:
            return
        self._rail_width = width
        self._anchor(animate=not self._collapsed)

    def railWidth(self) -> int:
        return self._rail_width

    # ── geometry / event filtering ───────────────────────────────────────
    def _expanded_geom(self) -> QRect:
        h = max(0, self._host.height())
        x = max(0, self._host.width() - self._rail_width)
        return QRect(x, 0, self._rail_width, h)

    def _collapsed_geom(self) -> QRect:
        h = max(0, self._host.height())
        return QRect(self._host.width(), 0, self._rail_width, h)

    def _anchor(self, *, animate: bool) -> None:
        target = self._collapsed_geom() if self._collapsed else self._expanded_geom()
        if not animate:
            self._anim.stop()
            self.setGeometry(target)
            self.setVisible(not self._collapsed)
            return
        # When opening, become visible first so the slide is visible.
        if not self._collapsed:
            self.setVisible(True)
            self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._collapsed:
            self.setVisible(False)
        self._reposition_handle()
        self.collapsedChanged.emit(self._collapsed)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._host and event.type() == QEvent.Resize:
            # Keep the rail glued to the host's right edge regardless of
            # the host's new size.
            self._anchor(animate=False)
            if not self._collapsed:
                self.raise_()
            self._reposition_handle()
        return super().eventFilter(obj, event)

    def _build_qss(self) -> str:
        c = theme.Colors
        return f"""
        QFrame#CollapsibleRail {{
            background-color: {c.rail};
            border-left: 1px solid {c.border_subtle};
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QLabel, QPushButton, QVBoxLayout,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    # The host is the "main" widget the rail floats over.
    host = QWidget()
    host.setObjectName("Host")
    host.setStyleSheet(f"#Host {{ background-color: {theme.Colors.surface}; }}")
    host.setWindowTitle("CollapsibleRail — overlay demo")
    host.resize(960, 480)

    # Canvas fills the entire host; the rail does NOT take a layout slot.
    canvas = QFrame(host)
    canvas.setGeometry(0, 0, host.width(), host.height())
    canvas.setStyleSheet(
        f"background-color: {theme.Colors.panel}; "
        f"border: 1px solid {theme.Colors.border_subtle}; "
        f"border-radius: 8px;"
    )
    pl = QVBoxLayout(canvas)
    pl.setContentsMargins(16, 16, 16, 16)
    pl.addWidget(QLabel(
        "canvas — fills the whole host.  the rail floats above me when expanded,\n"
        "and slides off-screen when collapsed.  no layout shift, no width change."
    ))
    pl.addStretch(1)
    toggle_btn = QPushButton("Toggle rail")
    pl.addWidget(toggle_btn)

    rail = CollapsibleRail(host, width=332)
    body = QFrame(rail)
    bl = QVBoxLayout(body)
    bl.setContentsMargins(16, 16, 16, 16)
    bl.addWidget(QLabel("Properties (overlay)"))
    for s in ("Profile & Format", "Axes", "Legend", "Lines & Markers",
              "Grid", "Limits & Scale", "Layout"):
        lbl = QLabel(f"  · {s}")
        lbl.setStyleSheet(f"color: {theme.Colors.text_muted};")
        bl.addWidget(lbl)
    bl.addStretch(1)
    rail.setContentWidget(body)

    # Resize canvas to follow the host (no layout — manual geometry sync).
    def _sync_canvas(_ev=None):
        canvas.setGeometry(0, 0, host.width(), host.height())
    host.resizeEvent = lambda ev: (_sync_canvas(),
                                   QWidget.resizeEvent(host, ev))

    toggle_btn.clicked.connect(rail.toggle)
    rail.collapsedChanged.connect(
        lambda c: toggle_btn.setText("Show rail" if c else "Hide rail")
    )

    host.show()
    _sys.exit(app.exec())
