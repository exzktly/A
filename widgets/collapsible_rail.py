"""CollapsibleRail — right-side rail container with animated collapse.

Hosts a permanent column (default width 332 px to match the mockup's
Properties rail) that can collapse to a 0-px sliver via a smooth
``QPropertyAnimation`` on ``maximumWidth``. Used by the v2 app shell as
the third column of ``.main``; the titlebar's rail-toggle IconButton
calls ``toggle()`` to flip the state.

The container does **not** own the content widget's styling — it is a
neutral host. The content is supplied via the constructor or
``setContentWidget()`` and is laid out at its natural width inside the
rail's max-width clip.

API
---
* ``CollapsibleRail(parent=None, *, width=332, collapsed=False, animation_ms=180)``
* ``setContentWidget(widget)``
* ``contentWidget() -> QWidget | None``
* ``setCollapsed(bool)`` / ``isCollapsed() -> bool`` / ``toggle()``
* ``setRailWidth(int)`` — change the expanded width (re-animates if visible).
* signal ``collapsedChanged(bool)`` — fires after the animation completes,
  with the post-animation state.

Sizing model: when collapsed, ``maximumWidth`` is animated to 0; the rail
is still visible in the layout (as a zero-width gap) but `setVisible(False)`
is not used so the toggle in the titlebar remains discoverable.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import (  # noqa: E402
    QEasingCurve, QPropertyAnimation, Qt, Signal,
)
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402


class CollapsibleRail(QFrame):
    collapsedChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None, *,
                 width: int = 332, collapsed: bool = False,
                 animation_ms: int = 180) -> None:
        super().__init__(parent)
        self.setObjectName("CollapsibleRail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._rail_width = max(0, int(width))
        self._collapsed = bool(collapsed)
        self._content: QWidget | None = None

        # Initial geometry — apply the start state before the widget is shown
        # so the first paint is correct (no flash from full → animated).
        target = 0 if self._collapsed else self._rail_width
        self.setMinimumWidth(0)
        self.setMaximumWidth(target)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setDuration(int(animation_ms))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        self.setStyleSheet(self._build_qss())

    # ── content ──────────────────────────────────────────────────────────
    def setContentWidget(self, widget: QWidget) -> None:
        if self._content is widget:
            return
        # Drop the previous content (caller can hold a reference if they
        # need to re-mount it).
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
        self._start_anim()

    def toggle(self) -> None:
        self.setCollapsed(not self._collapsed)

    def setRailWidth(self, width: int) -> None:
        width = max(0, int(width))
        if width == self._rail_width:
            return
        self._rail_width = width
        if not self._collapsed:
            self._start_anim()

    def railWidth(self) -> int:
        return self._rail_width

    # ── internals ────────────────────────────────────────────────────────
    def _start_anim(self) -> None:
        end = 0 if self._collapsed else self._rail_width
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        # Pin the final size and emit the post-animation state.
        target = 0 if self._collapsed else self._rail_width
        self.setMaximumWidth(target)
        self.collapsedChanged.emit(self._collapsed)

    def _build_qss(self) -> str:
        c = theme.Colors
        return f"""
        QFrame#CollapsibleRail {{
            background-color: {c.bg_rail};
            border-left: 1px solid {c.border_subtle};
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    )

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    host = QWidget()
    host.setObjectName("Host")
    host.setStyleSheet(f"#Host {{ background-color: {theme.Colors.bg_app}; }}")
    host.setWindowTitle("CollapsibleRail — demo")
    host.resize(960, 480)

    outer = QHBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # Fake plot area on the left, fills available space.
    plot = QFrame(host)
    plot.setStyleSheet(
        f"background-color: {theme.Colors.bg_panel}; "
        f"border: 1px solid {theme.Colors.border_subtle}; border-radius: 8px;"
    )
    pl = QVBoxLayout(plot)
    pl.setContentsMargins(16, 16, 16, 16)
    pl.addWidget(QLabel("plot canvas (fills remaining space)"))
    pl.addStretch(1)
    toggle_btn = QPushButton("Toggle rail")
    pl.addWidget(toggle_btn)
    outer.addWidget(plot, 1)

    # The collapsible rail.
    rail = CollapsibleRail(host, width=332)
    body = QFrame(rail)
    bl = QVBoxLayout(body)
    bl.setContentsMargins(16, 16, 16, 16)
    bl.addWidget(QLabel("Properties"))
    for i in range(6):
        bl.addWidget(QLabel(f"  · section {i + 1}"))
    bl.addStretch(1)
    rail.setContentWidget(body)
    outer.addWidget(rail, 0)

    toggle_btn.clicked.connect(rail.toggle)
    rail.collapsedChanged.connect(
        lambda c: toggle_btn.setText("Show rail" if c else "Hide rail")
    )

    host.show()
    _sys.exit(app.exec())
