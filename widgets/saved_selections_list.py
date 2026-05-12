"""SavedSelectionsList — an editable, reorderable list of saved well selections.

Built against the model defined in ``design/SELECTIONS_MODEL_CONTRACT.md``: the
widget holds a working ``list[dict]`` (each dict = one ``Selection``: ``id``,
``name``, ``color``, ``hidden``, ``wells``, ``replicates``, optional ``labels``/
``source``) and emits granular signals plus a coarse ``selectionsChanged(list)``
as the user edits.

Per row: drag handle (drag-to-reorder) · visibility eye · colour dot (opens a
``ColorSwatchRow`` recolour popover) · inline-renamable name · count chip
(``len(wells)``) · kebab → ``QMenu`` (Rename / Recolour / Duplicate / Hide /
Move up / Move down / Export / Delete). Clicking the row body activates it;
clicking the chevron expands it to a read-only ``ChipGroup`` of well chips.
Hidden rows fade + strike-through and sink to the bottom of the *displayed*
order (their stored position is preserved). Footer: *From selection* + *Import…*.

API
---
* ``setSelections(list[dict])`` / ``selections() -> list[dict]``
* ``setCurrentId(str)`` / ``currentId() -> str``
* signals: ``entryActivated(str)``, ``entryRenamed(str, str)``,
  ``entryRecoloured(str, str)``, ``entryVisibilityToggled(str, bool)``,
  ``entryDuplicated(str, str)``, ``entryDeleted(str)``,
  ``entryExportRequested(str)``, ``orderChanged(list)``,
  ``addFromSelectionRequested()``, ``importRequested()``, ``selectionsChanged(list)``
"""

from __future__ import annotations

import os as _os
import sys as _sys
import uuid as _uuid

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QPoint, QTimer, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

import theme  # noqa: E402

_HANDLE = "⠇"   # ⠇-ish drag dots
_EYE_ON = "◉"   # ◉
_EYE_OFF = "○"  # ○
_KEBAB = "⋯"    # ⋯
_CHEV_C = "▸"   # ▸
_CHEV_O = "▾"   # ▾


def _hex6(c) -> str:
    qc = QColor(c)
    return qc.name(QColor.HexRgb).upper() if qc.isValid() else "#888888"


class _SelectionRow(QFrame):
    activated = Signal(str)
    visibilityToggled = Signal(str, bool)   # (id, hidden)
    recolourRequested = Signal(str, QWidget)
    renameCommitted = Signal(str, str)
    kebabRequested = Signal(str, QWidget)
    expandToggled = Signal(str, bool)
    dragMoveBy = Signal(str, int)            # (id, net ± rows) — emitted on release

    def __init__(self, sel: dict, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SelectionRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._id = sel["id"]
        self._expanded = False
        c = theme.Colors

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QWidget(self)
        row = QHBoxLayout(top)
        row.setContentsMargins(theme.Spacing.sm, theme.Spacing.xs,
                               theme.Spacing.sm, theme.Spacing.xs)
        row.setSpacing(theme.Spacing.sm)

        self._chev = QToolButton(top)
        self._chev.setObjectName("RowGhost")
        self._chev.setText(_CHEV_C)
        self._chev.setCursor(Qt.PointingHandCursor)
        self._chev.clicked.connect(self._toggle_expand)
        row.addWidget(self._chev)

        self._handle = QLabel(_HANDLE, top)
        self._handle.setObjectName("RowHandle")
        self._handle.setCursor(Qt.OpenHandCursor)
        self._handle.setToolTip("Drag to reorder")
        self._drag_y0: float | None = None
        self._drag_steps = 0
        self._handle.mousePressEvent = self._handle_press     # type: ignore[assignment]
        self._handle.mouseMoveEvent = self._handle_move       # type: ignore[assignment]
        self._handle.mouseReleaseEvent = self._handle_release  # type: ignore[assignment]
        row.addWidget(self._handle)

        self._eye = QToolButton(top)
        self._eye.setObjectName("RowGhost")
        self._eye.setCheckable(True)
        self._eye.setCursor(Qt.PointingHandCursor)
        self._eye.clicked.connect(
            lambda: self.visibilityToggled.emit(self._id, self._eye.isChecked()))
        row.addWidget(self._eye)

        self._dot = QToolButton(top)
        self._dot.setObjectName("RowDot")
        self._dot.setCursor(Qt.PointingHandCursor)
        self._dot.setToolTip("Recolour")
        self._dot.clicked.connect(
            lambda: self.recolourRequested.emit(self._id, self._dot))
        row.addWidget(self._dot)

        self._name = QLabel(top)
        self._name.setObjectName("RowName")
        self._name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self._name, 1)

        self._editor: QLineEdit | None = None

        self._chip = QLabel(top)
        self._chip.setObjectName("RowCount")
        self._chip.setAlignment(Qt.AlignCenter)
        row.addWidget(self._chip)

        self._kebab = QToolButton(top)
        self._kebab.setObjectName("RowGhost")
        self._kebab.setText(_KEBAB)
        self._kebab.setCursor(Qt.PointingHandCursor)
        self._kebab.clicked.connect(
            lambda: self.kebabRequested.emit(self._id, self._kebab))
        row.addWidget(self._kebab)

        outer.addWidget(top)

        self._chips_host = QWidget(self)
        ch = QHBoxLayout(self._chips_host)
        ch.setContentsMargins(theme.Spacing.xl + theme.Spacing.sm, 0,
                              theme.Spacing.sm, theme.Spacing.sm)
        self._chips_inner = ch
        self._chips_host.setVisible(False)
        outer.addWidget(self._chips_host)

        self._top = top
        self.setStyleSheet(self._qss())
        top.mouseDoubleClickEvent = self._begin_rename  # type: ignore[assignment]
        top.mousePressEvent = self._on_body_press        # type: ignore[assignment]

    # ── styling ──────────────────────────────────────────────────────────
    def _qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        return f"""
        QFrame#SelectionRow {{ background: transparent; border-radius: {r.sm}px; }}
        QFrame#SelectionRow[current="true"] {{ background-color: {c.accent_dim}; }}
        QFrame#SelectionRow[hiddenRow="true"] {{ }}
        QToolButton#RowGhost {{ border: none; background: transparent; color: {c.text_secondary};
            padding: 0 2px; }}
        QToolButton#RowGhost:hover {{ color: {c.text_primary}; }}
        QToolButton#RowDot {{ border: 1px solid {c.border}; border-radius: 7px;
            min-width: 14px; max-width: 14px; min-height: 14px; max-height: 14px; }}
        QLabel#RowHandle {{ color: {c.text_faint}; }}
        QLabel#RowName {{ color: {c.text_primary}; }}
        QLabel#RowName[hiddenRow="true"] {{ color: {c.text_muted}; }}
        QLabel#RowCount {{ color: {c.text_secondary}; background-color: {c.panel_elevated};
            border: 1px solid {c.border_subtle}; border-radius: {r.xs}px; padding: 0 6px; }}
        """

    # ── populate / refresh ───────────────────────────────────────────────
    def update_from(self, sel: dict, *, current: bool) -> None:
        self._id = sel["id"]
        hidden = bool(sel.get("hidden"))
        self._name.setText(str(sel.get("name", "")))
        if hidden:
            f = self._name.font(); f.setStrikeOut(True); self._name.setFont(f)
        else:
            f = self._name.font(); f.setStrikeOut(False); self._name.setFont(f)
        self._chip.setText(str(len(sel.get("wells") or [])))
        col = _hex6(sel.get("color"))
        self._dot.setStyleSheet(
            f"QToolButton#RowDot {{ background-color: {col}; border: 1px solid {theme.Colors.border};"
            f" border-radius: 7px; min-width:14px; max-width:14px; min-height:14px; max-height:14px; }}")
        self._eye.blockSignals(True)
        self._eye.setChecked(hidden)
        self._eye.setText(_EYE_OFF if hidden else _EYE_ON)
        self._eye.setToolTip("Hidden — click to show" if hidden else "Visible — click to hide")
        self._eye.blockSignals(False)
        self.setProperty("current", "true" if current else "false")
        self.setProperty("hiddenRow", "true" if hidden else "false")
        self._name.setProperty("hiddenRow", "true" if hidden else "false")
        op = 0.55 if hidden else 1.0
        self.setStyleSheet(self._qss())
        self.setWindowOpacity(1.0)
        for w in (self._name, self._chip, self._handle, self._chev):
            w.setStyleSheet(f"opacity: {op};")
        # rebuild well chips (only matters while expanded)
        self._wells = list(sel.get("wells") or [])
        if self._expanded:
            self._fill_chips()
        self.style().unpolish(self); self.style().polish(self)

    def _fill_chips(self) -> None:
        while self._chips_inner.count():
            it = self._chips_inner.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        try:
            from widgets.chip_group import ChipGroup
            cg = ChipGroup(exclusive=False)
            for w in self._wells:
                cg.addChip(w, data=w)
            cg.setEnabled(False)
            self._chips_inner.addWidget(cg)
        except Exception:
            lbl = QLabel(", ".join(self._wells) or "(no wells)")
            lbl.setObjectName("Caption")
            lbl.setWordWrap(True)
            self._chips_inner.addWidget(lbl)
        self._chips_inner.addStretch(1)

    # ── interactions ─────────────────────────────────────────────────────
    def _on_body_press(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.activated.emit(self._id)

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._chev.setText(_CHEV_O if self._expanded else _CHEV_C)
        if self._expanded and self._chips_inner.count() == 0:
            self._fill_chips()
        self._chips_host.setVisible(self._expanded)
        self.expandToggled.emit(self._id, self._expanded)

    def _begin_rename(self, _event=None) -> None:
        if self._editor is not None:
            return
        self._editor = QLineEdit(self._name.text(), self._top)
        self._editor.setObjectName("RowEditor")
        self._editor.selectAll()
        # swap the label out for the editor in the layout
        lay = self._top.layout()
        idx = lay.indexOf(self._name)
        self._name.setVisible(False)
        lay.insertWidget(idx, self._editor, 1)
        self._editor.setFocus()
        self._editor.editingFinished.connect(self._finish_rename)

    def _finish_rename(self) -> None:
        if self._editor is None:
            return
        new = self._editor.text().strip()
        ed = self._editor
        self._editor = None
        ed.deleteLater()
        self._name.setVisible(True)
        if new and new != self._name.text():
            self.renameCommitted.emit(self._id, new)

    def trigger_rename(self) -> None:
        self._begin_rename()

    # ── drag-handle reorder ──────────────────────────────────────────────
    def _handle_press(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_y0 = event.globalPosition().y()
            self._drag_steps = 0
            self._handle.setCursor(Qt.ClosedHandCursor)

    def _handle_move(self, event) -> None:
        if self._drag_y0 is None:
            return
        h = max(1.0, float(self.height()))
        self._drag_steps = int(round((event.globalPosition().y() - self._drag_y0) / h))

    def _handle_release(self, _event) -> None:
        steps = self._drag_steps
        self._drag_y0 = None
        self._drag_steps = 0
        self._handle.setCursor(Qt.OpenHandCursor)
        if steps:
            self.dragMoveBy.emit(self._id, steps)


class SavedSelectionsList(QWidget):
    entryActivated = Signal(str)
    entryRenamed = Signal(str, str)
    entryRecoloured = Signal(str, str)
    entryVisibilityToggled = Signal(str, bool)     # (id, hidden)
    entryDuplicated = Signal(str, str)             # (new_id, src_id)
    entryDeleted = Signal(str)
    entryExportRequested = Signal(str)
    orderChanged = Signal(list)                    # [id, …] in stored order
    addFromSelectionRequested = Signal()
    importRequested = Signal()
    selectionsChanged = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SavedSelectionsList")
        self._selections: list[dict] = []
        self._current_id: str = ""
        self._rows: dict[str, _SelectionRow] = {}
        self._recolour_pop = None

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(theme.Spacing.sm)

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("SavedSelScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._body = QWidget()
        self._body.setObjectName("SavedSelBody")
        self._body.setAttribute(Qt.WA_StyledBackground, True)
        self._vbox = QVBoxLayout(self._body)
        self._vbox.setContentsMargins(theme.Spacing.xs, theme.Spacing.xs,
                                      theme.Spacing.xs, theme.Spacing.xs)
        self._vbox.setSpacing(2)
        self._vbox.addStretch(1)
        self._scroll.setWidget(self._body)
        v.addWidget(self._scroll, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(theme.Spacing.sm)
        self._from_btn = QPushButton("From selection")
        self._from_btn.clicked.connect(self.addFromSelectionRequested.emit)
        self._import_btn = QPushButton("Import…")
        self._import_btn.clicked.connect(self.importRequested.emit)
        footer.addWidget(self._from_btn)
        footer.addWidget(self._import_btn)
        footer.addStretch(1)
        v.addLayout(footer)

        self.setStyleSheet(self._qss())

    def _qss(self) -> str:
        c, r = theme.Colors, theme.Radii
        return f"""
        QScrollArea#SavedSelScroll {{ background: transparent; }}
        QWidget#SavedSelBody {{ background-color: {c.panel}; border: 1px solid {c.border_subtle};
            border-radius: {r.sm}px; }}
        """

    # ── model API ────────────────────────────────────────────────────────
    def setSelections(self, selections) -> None:
        self._selections = [self._sanitise(dict(s)) for s in selections]
        self._ensure_unique()
        if self._current_id not in {s["id"] for s in self._selections}:
            self._current_id = self._selections[0]["id"] if self._selections else ""
        self._rebuild()

    def selections(self) -> list[dict]:
        return [dict(s) for s in self._selections]

    def setCurrentId(self, sel_id: str) -> None:
        if sel_id in {s["id"] for s in self._selections} and sel_id != self._current_id:
            self._current_id = sel_id
            self._refresh_current()

    def currentId(self) -> str:
        return self._current_id

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _sanitise(s: dict) -> dict:
        s.setdefault("id", "")
        s.setdefault("name", "Selection")
        s["color"] = _hex6(s.get("color", "#5B9BF8"))
        s["hidden"] = bool(s.get("hidden"))
        s["wells"] = list(s.get("wells") or [])
        if "replicates" not in s:
            s["replicates"] = None
        s.setdefault("source", "user")
        return s

    def _mint_id(self) -> str:
        taken = {s["id"] for s in self._selections}
        while True:
            i = _uuid.uuid4().hex[:8]
            if i not in taken:
                return i

    def _ensure_unique(self) -> None:
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        for s in self._selections:
            if not s["id"] or s["id"] in seen_ids:
                s["id"] = self._mint_id_excluding(seen_ids)
            seen_ids.add(s["id"])
            s["name"] = self._unique_name(s["name"], taken=seen_names)
            seen_names.add(s["name"])

    def _mint_id_excluding(self, taken: set[str]) -> str:
        while True:
            i = _uuid.uuid4().hex[:8]
            if i not in taken and all(x["id"] != i for x in self._selections):
                return i

    def _unique_name(self, name: str, *, exclude_id: str | None = None,
                     taken: set[str] | None = None) -> str:
        name = name.strip() or "Selection"
        if taken is None:
            taken = {s["name"] for s in self._selections if s["id"] != exclude_id}
        if name not in taken:
            return name
        base = f"{name}_v2"
        if base not in taken:
            return base
        i = 2
        while f"{base} {i}" in taken:
            i += 1
        return f"{base} {i}"

    def _by_id(self, sel_id: str) -> dict | None:
        for s in self._selections:
            if s["id"] == sel_id:
                return s
        return None

    def _index_of(self, sel_id: str) -> int:
        for i, s in enumerate(self._selections):
            if s["id"] == sel_id:
                return i
        return -1

    def _display_order(self) -> list[dict]:
        return ([s for s in self._selections if not s["hidden"]]
                + [s for s in self._selections if s["hidden"]])

    # ── view build ───────────────────────────────────────────────────────
    def _rebuild(self) -> None:
        # remove existing row widgets (keep the trailing stretch)
        while self._vbox.count() > 1:
            it = self._vbox.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._rows = {}
        for s in self._display_order():
            row = _SelectionRow(s, self._body)
            row.activated.connect(self._on_activated)
            row.visibilityToggled.connect(self._on_visibility)
            row.recolourRequested.connect(self._on_recolour_requested)
            row.renameCommitted.connect(self._on_renamed)
            row.kebabRequested.connect(self._on_kebab)
            row.dragMoveBy.connect(self._on_drag_move)
            row.update_from(s, current=(s["id"] == self._current_id))
            self._vbox.insertWidget(self._vbox.count() - 1, row)
            self._rows[s["id"]] = row

    def _refresh_rows(self) -> None:
        for s in self._selections:
            row = self._rows.get(s["id"])
            if row is not None:
                row.update_from(s, current=(s["id"] == self._current_id))

    def _refresh_current(self) -> None:
        for sid, row in self._rows.items():
            s = self._by_id(sid)
            if s is not None:
                row.update_from(s, current=(sid == self._current_id))

    def _emit_changed(self) -> None:
        self.selectionsChanged.emit(self.selections())

    # ── row callbacks ────────────────────────────────────────────────────
    def _on_activated(self, sel_id: str) -> None:
        if sel_id != self._current_id:
            self._current_id = sel_id
            self._refresh_current()
        self.entryActivated.emit(sel_id)

    def _on_visibility(self, sel_id: str, hidden: bool) -> None:
        s = self._by_id(sel_id)
        if s is None:
            return
        s["hidden"] = bool(hidden)
        self._rebuild()                       # display order changes
        self.entryVisibilityToggled.emit(sel_id, s["hidden"])
        self._emit_changed()

    def _on_renamed(self, sel_id: str, new_name: str) -> None:
        s = self._by_id(sel_id)
        if s is None:
            return
        final = self._unique_name(new_name, exclude_id=sel_id)
        if final == s["name"]:
            return
        s["name"] = final
        self._refresh_rows()
        self.entryRenamed.emit(sel_id, final)
        self._emit_changed()

    def _on_recolour_requested(self, sel_id: str, anchor: QWidget) -> None:
        s = self._by_id(sel_id)
        if s is None:
            return
        from widgets.popover import Popover
        from widgets.color_swatch_row import ColorSwatchRow
        pop = Popover(self)
        recents = [x["color"] for x in self._selections if x["id"] != sel_id][:8]
        sw = ColorSwatchRow(allow_custom=True, recents=recents)
        sw.setCurrentColor(s["color"])
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(theme.Spacing.sm, theme.Spacing.sm,
                              theme.Spacing.sm, theme.Spacing.sm)
        cl.addWidget(QLabel("Recolour"))
        cl.addWidget(sw)
        pop.setContentWidget(content)

        def _picked(c: QColor):
            s["color"] = _hex6(c)
            self._refresh_rows()
            self.entryRecoloured.emit(sel_id, s["color"])
            self._emit_changed()
        sw.colorPicked.connect(_picked)
        self._recolour_pop = pop
        pop.popup(anchor, side="bottom", align="start")

    def _on_kebab(self, sel_id: str, anchor: QWidget) -> None:
        s = self._by_id(sel_id)
        if s is None:
            return
        m = QMenu(self)
        a_rename = m.addAction("Rename")
        a_recolour = m.addAction("Recolour…")
        a_dup = m.addAction("Duplicate")
        a_hide = m.addAction("Show" if s["hidden"] else "Hide")
        m.addSeparator()
        idx = self._index_of(sel_id)
        a_up = m.addAction("Move up")
        a_down = m.addAction("Move down")
        a_up.setEnabled(idx > 0)
        a_down.setEnabled(0 <= idx < len(self._selections) - 1)
        m.addSeparator()
        a_export = m.addAction("Export…")
        a_delete = m.addAction("Delete")
        chosen = m.exec(anchor.mapToGlobal(QPoint(0, anchor.height())))
        if chosen is None:
            return
        if chosen is a_rename:
            row = self._rows.get(sel_id)
            if row is not None:
                row.trigger_rename()
        elif chosen is a_recolour:
            self._on_recolour_requested(sel_id, anchor)
        elif chosen is a_dup:
            self._duplicate(sel_id)
        elif chosen is a_hide:
            self._on_visibility(sel_id, not s["hidden"])
        elif chosen is a_up:
            self._move(sel_id, -1)
        elif chosen is a_down:
            self._move(sel_id, +1)
        elif chosen is a_export:
            self.entryExportRequested.emit(sel_id)
        elif chosen is a_delete:
            self._delete(sel_id)

    # ── mutations ────────────────────────────────────────────────────────
    def _duplicate(self, sel_id: str) -> None:
        s = self._by_id(sel_id)
        if s is None:
            return
        new = dict(s)
        new["id"] = self._mint_id()
        new["name"] = self._unique_name(f"{s['name']} copy")
        new["source"] = "user"
        idx = self._index_of(sel_id)
        self._selections.insert(idx + 1, new)
        self._rebuild()
        self.entryDuplicated.emit(new["id"], sel_id)
        self.orderChanged.emit([x["id"] for x in self._selections])
        self._emit_changed()

    def _delete(self, sel_id: str) -> None:
        idx = self._index_of(sel_id)
        if idx < 0:
            return
        self._selections.pop(idx)
        if self._current_id == sel_id:
            self._current_id = self._selections[min(idx, len(self._selections) - 1)]["id"] if self._selections else ""
        self._rebuild()
        self.entryDeleted.emit(sel_id)
        self.orderChanged.emit([x["id"] for x in self._selections])
        self._emit_changed()

    def _move(self, sel_id: str, step: int) -> None:
        idx = self._index_of(sel_id)
        if idx < 0:
            return
        new_idx = max(0, min(len(self._selections) - 1, idx + step))
        if new_idx == idx:
            return
        self._selections.insert(new_idx, self._selections.pop(idx))
        self._rebuild()
        self.orderChanged.emit([x["id"] for x in self._selections])
        self._emit_changed()

    def _on_drag_move(self, sel_id: str, steps: int) -> None:
        # Deferred: the originating row widget is destroyed inside _rebuild().
        QTimer.singleShot(0, lambda: self._move(sel_id, steps))


# ── standalone visual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget as _QW

    app = QApplication.instance() or QApplication(_sys.argv)
    app.setStyleSheet(theme.qss())

    root = _QW()
    root.setWindowTitle("SavedSelectionsList — demo")
    pad = theme.Spacing.lg
    lay = QVBoxLayout(root)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(theme.Spacing.md)

    title = QLabel("SavedSelectionsList (editable)")
    title.setObjectName("Title")
    lay.addWidget(title)

    lst = SavedSelectionsList()
    tr = theme.Colors.trace
    lst.setSelections([
        {"id": "aaaa1111", "name": "Control", "color": tr[0], "hidden": False,
         "wells": ["A01", "A02", "A03", "B01", "B02", "B03"],
         "replicates": [["A01", "A02", "A03"], ["B01", "B02", "B03"]], "source": "bar_group"},
        {"id": "bbbb2222", "name": "Drug A — 1µM", "color": tr[1], "hidden": False,
         "wells": ["C01", "C02", "C03"], "replicates": [["C01", "C02", "C03"]], "source": "rep_set"},
        {"id": "cccc3333", "name": "Drug A — 10µM", "color": tr[2], "hidden": False,
         "wells": ["D01", "D02", "D03"], "replicates": None, "source": "user"},
        {"id": "dddd4444", "name": "Untreated", "color": theme.Colors.text_muted, "hidden": True,
         "wells": ["E01", "E02"], "replicates": None, "source": "import"},
    ])
    lst.setCurrentId("bbbb2222")
    lst.setMinimumHeight(260)
    lay.addWidget(lst, 1)

    echo = QLabel("(interact — rename / recolour / reorder / hide / delete)")
    echo.setObjectName("Secondary")
    echo.setWordWrap(True)
    lay.addWidget(echo)
    lst.entryActivated.connect(lambda i: echo.setText(f"activated → {i}"))
    lst.entryRenamed.connect(lambda i, n: echo.setText(f"renamed {i} → {n}"))
    lst.entryRecoloured.connect(lambda i, c: echo.setText(f"recoloured {i} → {c}"))
    lst.entryVisibilityToggled.connect(lambda i, h: echo.setText(f"{i} hidden={h}"))
    lst.orderChanged.connect(lambda ids: echo.setText("order → " + ", ".join(ids)))
    lst.entryDeleted.connect(lambda i: echo.setText(f"deleted → {i}"))
    lst.addFromSelectionRequested.connect(lambda: echo.setText("from-selection requested"))
    lst.importRequested.connect(lambda: echo.setText("import requested"))

    root.resize(440, 420)
    root.show()
    _sys.exit(app.exec())
