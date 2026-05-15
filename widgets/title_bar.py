"""TitleBar — the frameless-window chrome strip.

Brand tile + wordmark (the brand opens a **brand menu**: Open / Recent /
Preferences / About / Quit), a breadcrumb (``Workspace · Project / file.awd``
with a mono "file chip"), a live "Saved" :class:`~widgets.status_dot.StatusDot`,
then right-aligned widgets: a ghost **Open** button (⌘O), a **theme switcher**
(sun/moon → a `Popover` of Dark / Light / System tiles + a High-contrast
toggle), arbitrary action :class:`~widgets.icon_button.IconButton`s, and
optional **window-control** buttons (min / max / close — close hovers to
``--danger``; hidden on macOS / in native-frame mode).

Frameless vs. native frame
--------------------------
``setFramelessMode(bool)`` flips between:

* **frameless** (default on Win/Linux) — the bar drags the window (system move),
  double-click maximizes, window-control buttons show, and a
  :class:`~widgets.window_resize_grips.WindowResizeGrips` is attached to the
  top-level window for edge/corner resizing.
* **native** (default on macOS) — the OS draws the frame; the bar shrinks to a
  ~36 px sub-strip beneath it (breadcrumb + actions only), drag is inert,
  window-control buttons hide, resize grips detach.

The initial mode is chosen by ``widgets._window_chrome.should_use_frameless()``
(env ``ALLWELL_FRAMELESS`` → Preferences override → accessibility probe →
platform default) unless an explicit ``frameless=`` is passed.

API
---
* ``TitleBar(parent=None, *, title="All-Well", frameless=None)``
* ``setBreadcrumb(parts, file_chip=None)`` / ``setSaved(bool)`` / ``setSavedText(text)``
* ``addAction(icon_name, tooltip="", *, text="") -> IconButton``
* ``setShowWindowButtons(bool)`` (auto-managed by ``setFramelessMode``)
* ``setFramelessMode(bool)`` / ``isFramelessMode() -> bool``
* ``setRecentFiles(list[str])``
* signals: ``closeRequested``/``minimizeRequested``/``maximizeToggleRequested``,
  ``openRequested``, ``recentFileRequested(str)``, ``preferencesRequested``,
  ``aboutRequested``, ``quitRequested``, ``themeChangeRequested(str)``
  (``"dark"``/``"light"``/``"system"``), ``highContrastToggled(bool)``
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import Qt, Signal  # noqa: E402
from PySide6.QtGui import QKeySequence, QShortcut  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

import theme  # noqa: E402
from widgets._window_chrome import should_use_frameless  # noqa: E402
from widgets.brand_tile import BrandTile  # noqa: E402
from widgets.icon_button import IconButton  # noqa: E402
from widgets.status_dot import StatusDot  # noqa: E402


class TitleBar(QWidget):
    closeRequested = Signal()
    minimizeRequested = Signal()
    maximizeToggleRequested = Signal()
    openRequested = Signal()
    recentFileRequested = Signal(str)
    preferencesRequested = Signal()
    aboutRequested = Signal()
    quitRequested = Signal()
    themeChangeRequested = Signal(str)      # "dark" | "light" | "system"
    highContrastToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None, *, title: str = "All-Well",
                 frameless: bool | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._press_offset = None
        self._recent: list[str] = []
        self._grips = None
        self._frameless = bool(should_use_frameless() if frameless is None else frameless)
        self._theme_pop = None

        h = theme.Spacing.sm
        lay = QHBoxLayout(self)
        lay.setContentsMargins(theme.Spacing.md, h, theme.Spacing.sm, h)
        lay.setSpacing(theme.Spacing.sm)
        self._lay = lay

        # ── brand (clickable → brand menu) ───────────────────────────────
        self._brand = BrandTile(self)
        self._brand.setCursor(Qt.PointingHandCursor)
        self._brand.setToolTip("Menu")
        self._brand.mousePressEvent = self._brand_clicked  # type: ignore[assignment]
        self._wordmark = QLabel(title, self)
        self._wordmark.setObjectName("TitleBarWordmark")
        self._caret = QLabel("▾", self)
        self._caret.setObjectName("TitleBarFaint")
        self._version_pill = QLabel("", self)
        self._version_pill.setObjectName("TitleBarVersionPill")
        self._version_pill.setVisible(False)
        lay.addWidget(self._brand)
        lay.addWidget(self._wordmark)
        lay.addWidget(self._caret)
        lay.addWidget(self._version_pill)

        # ── breadcrumb ───────────────────────────────────────────────────
        self._sep1 = self._dot_sep()
        self._crumbs = QLabel("", self)
        self._crumbs.setObjectName("TitleBarCrumbs")
        self._slash = QLabel("/", self)
        self._slash.setObjectName("TitleBarFaint")
        self._slash.setVisible(False)
        self._file_chip = QLabel("", self)
        self._file_chip.setObjectName("TitleBarFileChip")
        self._file_chip.setVisible(False)
        self._dataset_stats = QLabel("", self)
        self._dataset_stats.setObjectName("TitleBarDatasetStats")
        self._dataset_stats.setVisible(False)
        for w in (self._sep1, self._crumbs, self._slash, self._file_chip,
                  self._dataset_stats):
            lay.addWidget(w)
        self._sep1.setVisible(False)

        # ── saved indicator ──────────────────────────────────────────────
        self._saved_dot = StatusDot("success", self,
                                    diameter=max(8, round(self.fontMetrics().height() * 0.5)))
        self._saved_dot.setLabel("Saved")
        lay.addWidget(self._saved_dot)

        lay.addStretch(1)

        # ── ghost Open + ⌘O ──────────────────────────────────────────────
        self._open_btn = QPushButton("Open", self)
        self._open_btn.setObjectName("Ghost")
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.clicked.connect(self.openRequested)
        lay.addWidget(self._open_btn)
        self._open_sc = QShortcut(QKeySequence(QKeySequence.Open), self)
        self._open_sc.activated.connect(self.openRequested)

        # ── theme switcher ───────────────────────────────────────────────
        self._theme_btn = IconButton("sun", self, tooltip="Theme")
        self._theme_btn.clicked.connect(self._open_theme_popover)
        lay.addWidget(self._theme_btn)

        # ── action buttons row ───────────────────────────────────────────
        self._actions = QHBoxLayout()
        self._actions.setContentsMargins(0, 0, 0, 0)
        self._actions.setSpacing(theme.Spacing.xs)
        lay.addLayout(self._actions)

        # ── window buttons (min / max / close) ───────────────────────────
        self._winbtns = QHBoxLayout()
        self._winbtns.setContentsMargins(0, 0, 0, 0)
        self._winbtns.setSpacing(theme.Spacing.xs)
        self._btn_min = IconButton("chevron-down", tooltip="Minimize")
        self._btn_max = IconButton("grid", tooltip="Maximize / restore")
        self._btn_close = IconButton("x", tooltip="Close")
        self._btn_close.setObjectName("TitleClose")
        self._btn_min.clicked.connect(self.minimizeRequested)
        self._btn_max.clicked.connect(self.maximizeToggleRequested)
        self._btn_close.clicked.connect(self.closeRequested)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            self._winbtns.addWidget(b)
        self._winbtns_host = QWidget(self)
        self._winbtns_host.setLayout(self._winbtns)
        lay.addWidget(self._winbtns_host)

        self.closeRequested.connect(self._do_close)
        self.minimizeRequested.connect(self._do_minimize)
        self.maximizeToggleRequested.connect(self._do_toggle_max)

        self.setStyleSheet(self._build_qss())
        self._apply_mode()

    # ── API ──────────────────────────────────────────────────────────────
    def setTitle(self, text: str) -> None:
        self._wordmark.setText(text)

    def setBreadcrumb(self, parts, file_chip: str | None = None) -> None:
        parts = [str(p) for p in (parts or []) if str(p)]
        self._sep1.setVisible(bool(parts) or bool(file_chip))
        self._crumbs.setText("  ·  ".join(parts))
        self._crumbs.setVisible(bool(parts))
        if file_chip:
            self._file_chip.setText(str(file_chip))
            self._file_chip.setVisible(True)
            self._slash.setVisible(bool(parts))
        else:
            self._file_chip.setVisible(False)
            self._slash.setVisible(False)

    def setVersionPill(self, text: str) -> None:
        """Small mono pill next to the wordmark (e.g. ``v2.4.1``).

        Pass an empty string to hide it.
        """
        text = (text or "").strip()
        self._version_pill.setText(text)
        self._version_pill.setVisible(bool(text))

    def setDatasetStats(self, text: str) -> None:
        """Faint trailing summary after the file chip (e.g. ``· 96 wells · 8 timepoints``)."""
        text = (text or "").strip()
        self._dataset_stats.setText(text)
        self._dataset_stats.setVisible(bool(text))

    def setFromPath(self, path, *, max_parents: int = 2,
                    dataset_stats: str | None = None) -> None:
        """Synthesise the breadcrumb + file chip from a single filesystem path
        (Q7's "split from the dataset path" answer).

        Picks the last ``max_parents`` parent directories as breadcrumb parts
        and the final segment as the file chip. ``dataset_stats`` is forwarded
        to :meth:`setDatasetStats`. Pass ``path=None`` to clear everything.
        """
        if path is None:
            self.setBreadcrumb([], None)
            self.setDatasetStats("")
            return
        try:
            from pathlib import Path as _Path
            p = _Path(path)
            parts = list(p.parents)
            # parts[0] is the immediate parent; we want the closest N upward
            # in display order [grandparent, parent].
            upward = []
            for i in range(min(max_parents, len(parts))):
                upward.append(parts[i].name)
            upward = [s for s in reversed(upward) if s]
            self.setBreadcrumb(upward, file_chip=p.name)
        except Exception:
            self.setBreadcrumb([], None)
        self.setDatasetStats(dataset_stats or "")

    def setSaved(self, saved: bool) -> None:
        self._saved_dot.setStatus("success" if saved else "warn")
        self._saved_dot.setLabel("Saved" if saved else "Unsaved")

    def setSavedText(self, text: str) -> None:
        self._saved_dot.setLabel(text)

    def addAction(self, icon_name: str, tooltip: str = "", *, text: str = "") -> IconButton:  # type: ignore[override]
        btn = IconButton(icon_name, self, tooltip=tooltip, text=text)
        self._actions.addWidget(btn)
        return btn

    def setShowWindowButtons(self, show: bool) -> None:
        self._winbtns_host.setVisible(bool(show) and self._frameless and _sys.platform != "darwin")

    def setRecentFiles(self, files) -> None:
        self._recent = [str(f) for f in (files or []) if str(f)]

    def isFramelessMode(self) -> bool:
        return self._frameless

    def setFramelessMode(self, frameless: bool) -> None:
        frameless = bool(frameless)
        if frameless == self._frameless:
            return
        self._frameless = frameless
        self._apply_mode()

    # ── mode application ─────────────────────────────────────────────────
    def _apply_mode(self) -> None:
        native = not self._frameless
        # window-control buttons: only in frameless mode and not macOS
        self._winbtns_host.setVisible(self._frameless and _sys.platform != "darwin")
        # in native mode the bar is a slim sub-strip; in frameless it's the full bar
        fm = self.fontMetrics().height()
        if native:
            self.setFixedHeight(max(30, round(fm * 1.9)))
        else:
            self.setMinimumHeight(max(36, round(fm * 2.4)))
            self.setMaximumHeight(16777215)
        # resize grips follow the mode
        self._update_grips()

    def _update_grips(self) -> None:
        win = self._window()
        if self._frameless and win is not None:
            try:
                from widgets.window_resize_grips import WindowResizeGrips
                if self._grips is None:
                    self._grips = WindowResizeGrips(mode="auto", margin=8)
                self._grips.attach(win)
            except Exception:
                self._grips = None
        elif self._grips is not None:
            self._grips.detach()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # The top-level window exists by show time — (re)attach grips now.
        self._update_grips()

    # ── brand menu ───────────────────────────────────────────────────────
    def _brand_clicked(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        m = QMenu(self)
        m.addAction("Open…").triggered.connect(self.openRequested)
        rec = m.addMenu("Open recent")
        if self._recent:
            for path in self._recent:
                rec.addAction(path).triggered.connect(
                    lambda _checked=False, p=path: self.recentFileRequested.emit(p))
        else:
            a = rec.addAction("(no recent files)")
            a.setEnabled(False)
        m.addSeparator()
        m.addAction("Preferences…").triggered.connect(self.preferencesRequested)
        m.addAction("About All-Well").triggered.connect(self.aboutRequested)
        m.addSeparator()
        m.addAction("Quit").triggered.connect(self.quitRequested)
        m.exec(self._brand.mapToGlobal(self._brand.rect().bottomLeft()))

    # ── theme popover ────────────────────────────────────────────────────
    def _open_theme_popover(self) -> None:
        from widgets.popover import Popover
        try:
            from widgets.toggle_switch import ToggleSwitch
        except Exception:
            ToggleSwitch = None  # type: ignore[assignment]
        pop = Popover(self)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(theme.Spacing.sm, theme.Spacing.sm, theme.Spacing.sm, theme.Spacing.sm)
        v.setSpacing(theme.Spacing.xs)
        v.addWidget(QLabel("Appearance"))
        tiles = QHBoxLayout()
        tiles.setSpacing(theme.Spacing.xs)
        for label, key in (("Dark", "dark"), ("Light", "light"), ("System", "system")):
            b = QPushButton(label)
            b.setObjectName("Ghost")
            b.clicked.connect(lambda _c=False, k=key: (self.themeChangeRequested.emit(k), pop.close()))
            tiles.addWidget(b)
        v.addLayout(tiles)
        hc_row = QHBoxLayout()
        hc_row.setSpacing(theme.Spacing.sm)
        hc_row.addWidget(QLabel("High contrast"))
        hc_row.addStretch(1)
        if ToggleSwitch is not None:
            ts = ToggleSwitch()
            ts.toggled.connect(self.highContrastToggled)
            hc_row.addWidget(ts)
        v.addLayout(hc_row)
        pop.setContentWidget(content)
        self._theme_pop = pop
        pop.popup(self._theme_btn, side="bottom", align="end")

    # ── window drag ──────────────────────────────────────────────────────
    def _window(self):
        w = self.window()
        return w if w is not None and w is not self else None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._frameless:
            win = self._window()
            handle = win.windowHandle() if win is not None else None
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
            else:
                self._press_offset = event.globalPosition().toPoint() - (
                    win.frameGeometry().topLeft() if win else self.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_offset is not None and (event.buttons() & Qt.LeftButton):
            win = self._window()
            if win is not None:
                win.move(event.globalPosition().toPoint() - self._press_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._frameless:
            self.maximizeToggleRequested.emit()
        super().mouseDoubleClickEvent(event)

    # ── window control fallbacks ─────────────────────────────────────────
    def _do_close(self) -> None:
        win = self._window()
        if win is not None:
            win.close()

    def _do_minimize(self) -> None:
        win = self._window()
        if win is not None:
            win.showMinimized()

    def _do_toggle_max(self) -> None:
        win = self._window()
        if win is None:
            return
        win.showNormal() if win.isMaximized() else win.showMaximized()

    # ── helpers ──────────────────────────────────────────────────────────
    def _dot_sep(self) -> QLabel:
        lbl = QLabel("·", self)
        lbl.setObjectName("TitleBarFaint")
        return lbl

    def _build_qss(self) -> str:
        c, t, r = theme.Colors, theme.Typography, theme.Radii
        return f"""
        #TitleBar {{
            background-color: {c.titlebar};
            border-bottom: 1px solid {c.border_subtle};
        }}
        QLabel#TitleBarWordmark {{
            color: {c.text_primary};
            font-size: {t.emph_size}px;
            font-weight: {t.semibold};
            background: transparent;
        }}
        QLabel#TitleBarCrumbs {{
            color: {c.text_secondary};
            font-size: {t.small_size}px;
            background: transparent;
        }}
        QLabel#TitleBarFaint {{ color: {c.text_faint}; background: transparent; }}
        QLabel#TitleBarFileChip {{
            color: {c.text_secondary};
            background-color: {c.panel};
            border: 1px solid {c.border_subtle};
            border-radius: {r.xs}px;
            padding: 2px 6px;
            font-family: {t.family_mono};
            font-size: {t.small_size}px;
        }}
        QLabel#TitleBarVersionPill {{
            color: {c.text_faint};
            font-family: {t.family_mono};
            font-size: {t.caption_size}px;
            font-weight: 500;
            padding: 0 2px;
            margin-left: 4px;
            background: transparent;
        }}
        QLabel#TitleBarDatasetStats {{
            color: {c.text_faint};
            font-size: {t.caption_size}px;
            margin-left: 4px;
            background: transparent;
        }}
        QToolButton#TitleClose:hover {{
            background-color: {c.danger};
            border-radius: {r.xs}px;
        }}
        """


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import (
        QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget as _QW,
    )
    from widgets import _window_chrome

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    win = QMainWindow()
    win.setWindowTitle("TitleBar — demo")
    win.setWindowFlag(Qt.FramelessWindowHint, True)

    central = _QW()
    v = QVBoxLayout(central)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)

    tb = TitleBar(central, title="All-Well", frameless=True)
    tb.setVersionPill("v2.4.1")
    # Demonstrate Q7-style path-synthesised breadcrumb + dataset stats.
    tb.setFromPath("/data/Experiments/2019/20190325 SE c2 turq then cit hi moi 30/out",
                   dataset_stats="· 96 wells · 8 timepoints")
    tb.setRecentFiles(["run_2026-05-12.awd", "plate6.awd", "screen-A.awd"])
    tb.addAction("refresh-cw", "Refresh")
    tb.addAction("search", "Search (⌘K)")
    tb.addAction("panel-right-close", "Collapse properties rail")
    tb.addAction("download", "Export", text="Export")
    v.addWidget(tb)

    body = QLabel(f"frameless={tb.isFramelessMode()}  ·  "
                  f"should_use_frameless()={_window_chrome.should_use_frameless()}  "
                  f"(source: {_window_chrome.frameless_source()})\n\n"
                  "drag the title bar · double-click to maximize · brand → menu · "
                  "sun → theme popover · ⌘O = Open")
    body.setObjectName("Secondary")
    body.setAlignment(Qt.AlignCenter)
    body.setWordWrap(True)
    body.setMinimumHeight(220)
    v.addWidget(body, 1)

    toggle = QPushButton("Toggle frameless / native sub-strip")
    toggle.clicked.connect(lambda: (tb.setFramelessMode(not tb.isFramelessMode()),
                                    body.setText(f"frameless={tb.isFramelessMode()}")))
    v.addWidget(toggle)

    for sig, name in ((tb.openRequested, "openRequested"),
                      (tb.preferencesRequested, "preferencesRequested"),
                      (tb.aboutRequested, "aboutRequested"),
                      (tb.quitRequested, "quitRequested")):
        sig.connect(lambda n=name: body.setText(f"signal: {n}"))
    tb.recentFileRequested.connect(lambda p: body.setText(f"recent: {p}"))
    tb.themeChangeRequested.connect(lambda k: body.setText(f"theme → {k}"))
    tb.highContrastToggled.connect(lambda on: body.setText(f"high-contrast → {on}"))

    win.setCentralWidget(central)
    win.resize(860, 380)
    win.show()
    _sys.exit(app.exec())
