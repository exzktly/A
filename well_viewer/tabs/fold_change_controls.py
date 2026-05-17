"""Shared UI controls for the Fold-change normalization feature.

Used by the Bar Plots and Line Graphs tabs. Two independent toggles that
mirror ``app._fc_vs_control_on`` / ``_fc_vs_t0_on`` plus the control
selector that drives ``app._fc_control_label``. Both tabs see the same
state so flipping the toggle on one tab takes effect on the other.

The control combo is populated lazily — at construction time the loaded
state may not yet be available — and refreshed whenever the user opens
the combo via the ``aboutToShowPopup``-style ``showPopup`` override.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QWidget,
)


_NONE_LABEL = "— none —"
_SCOPES = ("bar", "line")


def _sync_widgets_to_state(app, *, skip_scope: str = "") -> None:
    """Mirror ``app._fc_*`` state into every installed widget set.

    Called after a toggle / combo change so the OTHER tab's widgets reflect
    the new state — the per-tab widgets are independent instances but the
    underlying state is shared, so without this sync the user sees stale
    UI on whichever tab they didn't interact with last. Also called from
    each tab's ``showEvent``-equivalent hook.

    *skip_scope* is the tab that just initiated the change — its widgets
    already hold the new state (it's how they wrote it), so re-applying
    would be a no-op at best and a recursion hazard at worst. Passing the
    empty string syncs every installed scope.
    """
    vs_ctrl = bool(getattr(app, "_fc_vs_control_on", False))
    vs_t0 = bool(getattr(app, "_fc_vs_t0_on", False))
    for scope in _SCOPES:
        if scope == skip_scope:
            continue
        cb = getattr(app, f"_fc_ctrl_cb_{scope}", None)
        combo = getattr(app, f"_fc_ctrl_combo_{scope}", None)
        t0 = getattr(app, f"_fc_t0_cb_{scope}", None)
        if cb is not None:
            blocked = cb.blockSignals(True)
            try:
                cb.setChecked(vs_ctrl)
            finally:
                cb.blockSignals(blocked)
        if combo is not None:
            combo.setEnabled(vs_ctrl)
            _repopulate_control_combo(app, combo)
        if t0 is not None:
            blocked = t0.blockSignals(True)
            try:
                t0.setChecked(vs_t0)
            finally:
                t0.blockSignals(blocked)


class _ControlCombo(QComboBox):
    """QComboBox subclass that repopulates from current selections on popup."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._sync_pending = False

    def showPopup(self) -> None:  # type: ignore[override]
        self._sync_pending = True
        _repopulate_control_combo(self._app, self)
        super().showPopup()


def _all_member_labels(app) -> list[str]:
    """Replicate-set names + selected well tokens currently plotted."""
    names: list[str] = []
    seen: set[str] = set()
    for s in (getattr(app, "_selections", []) or []):
        if s.get("hidden"):
            continue
        name = s.get("name") or ""
        if not name or name in seen:
            continue
        wells = s.get("wells") or []
        if any(w in (getattr(app, "_well_paths", None) or {}) for w in wells):
            names.append(name)
            seen.add(name)
    well_paths = getattr(app, "_well_paths", None) or {}
    for w in sorted(getattr(app, "_selected_wells", []) or [], key=lambda x: x):
        if w in well_paths and w not in seen:
            names.append(w)
            seen.add(w)
    return names


def _repopulate_control_combo(app, combo: QComboBox) -> None:
    members = _all_member_labels(app)
    current = combo.currentText()
    saved = getattr(app, "_fc_control_label", "") or current
    blocked = combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem(_NONE_LABEL)
        for m in members:
            combo.addItem(m)
        # Prefer the persisted app-state selection, falling back to the user's
        # last in-combo choice — so the selection survives reloads even if the
        # member list temporarily emptied (e.g. between data-load events).
        idx = combo.findText(saved) if saved else 0
        combo.setCurrentIndex(idx if idx >= 0 else 0)
    finally:
        combo.blockSignals(blocked)


def install_fold_change_controls(app, parent: QWidget, layout, *, scope: str) -> None:
    """Insert the fold-change toggles into ``layout`` (a QHBoxLayout).

    ``scope`` is "bar" or "line" — used to namespace the per-tab widget
    references stored on ``app``. The toggles themselves write straight to
    the shared ``app._fc_*`` state so both tabs stay in lockstep.
    """
    fc_lbl = QLabel("Fold change:", parent)
    f = fc_lbl.font(); f.setBold(True); fc_lbl.setFont(f)
    layout.addWidget(fc_lbl)

    ctrl_cb = QCheckBox("vs control", parent)
    ctrl_cb.setChecked(bool(getattr(app, "_fc_vs_control_on", False)))
    layout.addWidget(ctrl_cb)

    ctrl_combo = _ControlCombo(app, parent)
    ctrl_combo.setMinimumWidth(140)
    _repopulate_control_combo(app, ctrl_combo)
    layout.addWidget(ctrl_combo)

    t0_cb = QCheckBox("vs t0", parent)
    t0_cb.setChecked(bool(getattr(app, "_fc_vs_t0_on", False)))
    t0_cb.setToolTip(
        "Normalize each curve / bar to its own value at the earliest "
        "available timepoint (the first point becomes 1.0)."
    )
    layout.addWidget(t0_cb)

    def _redraw_all():
        # Both tabs share the state; redraw whichever is currently mounted.
        # We log exceptions instead of swallowing them — if a redraw fails the
        # toggle appears to do nothing, and the user has no way to know why.
        import traceback
        if hasattr(app, "_redraw_bars"):
            try:
                app._redraw_bars()
            except Exception:
                traceback.print_exc()
        if hasattr(app, "_redraw"):
            try:
                app._redraw()
            except Exception:
                traceback.print_exc()

    def _on_ctrl_toggled(checked: bool) -> None:
        app._fc_vs_control_on = bool(checked)
        ctrl_combo.setEnabled(checked)
        _sync_widgets_to_state(app, skip_scope=scope)
        _redraw_all()

    def _on_ctrl_changed(_idx: int) -> None:
        text = ctrl_combo.currentText()
        app._fc_control_label = "" if text == _NONE_LABEL else text
        _sync_widgets_to_state(app, skip_scope=scope)
        if app._fc_vs_control_on:
            _redraw_all()

    def _on_t0_toggled(checked: bool) -> None:
        app._fc_vs_t0_on = bool(checked)
        _sync_widgets_to_state(app, skip_scope=scope)
        _redraw_all()

    ctrl_cb.toggled.connect(_on_ctrl_toggled)
    ctrl_combo.currentIndexChanged.connect(_on_ctrl_changed)
    t0_cb.toggled.connect(_on_t0_toggled)

    ctrl_combo.setEnabled(ctrl_cb.isChecked())

    # Stash references so other code can refresh / inspect.
    setattr(app, f"_fc_ctrl_cb_{scope}", ctrl_cb)
    setattr(app, f"_fc_ctrl_combo_{scope}", ctrl_combo)
    setattr(app, f"_fc_t0_cb_{scope}", t0_cb)
