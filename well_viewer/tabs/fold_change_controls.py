"""Shared UI controls for the Fold-change normalization feature.

Used by the Bar Plots and Line Graphs tabs. Two parallel dropdowns:

* Control — divides each bar / curve by the picked well or replicate set's
  mean at the matching timepoint. ``—`` disables this axis.
* Baseline — divides each bar / curve by its own value at the chosen
  reference timepoint. Currently only ``t0`` (each member's first
  available timepoint) is offered; ``—`` disables this axis.

Both dropdowns are independent and may be combined. They mirror the
shared ``app._fc_*`` state so the same selection applies to both tabs.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QWidget,
)


_NONE_LABEL = "—"
_T0_LABEL = "t0 (first timepoint)"
_SCOPES = ("bar", "line")


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
    """Refresh the Control combo's item list from current selections."""
    members = _all_member_labels(app)
    saved = getattr(app, "_fc_control_label", "") or ""
    blocked = combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem(_NONE_LABEL)
        for m in members:
            combo.addItem(m)
        idx = combo.findText(saved) if saved else 0
        combo.setCurrentIndex(idx if idx >= 0 else 0)
    finally:
        combo.blockSignals(blocked)


def _repopulate_baseline_combo(app, combo: QComboBox) -> None:
    """Refresh the Baseline combo. Only ``t0`` is supported today."""
    on = bool(getattr(app, "_fc_vs_t0_on", False))
    blocked = combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem(_NONE_LABEL)
        combo.addItem(_T0_LABEL)
        combo.setCurrentIndex(1 if on else 0)
    finally:
        combo.blockSignals(blocked)


class _ControlCombo(QComboBox):
    """QComboBox that refreshes its item list from current selections on popup."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

    def showPopup(self) -> None:  # type: ignore[override]
        _repopulate_control_combo(self._app, self)
        super().showPopup()


def _sync_widgets_to_state(app, *, skip_scope: str = "") -> None:
    """Mirror ``app._fc_*`` state into every installed widget set.

    Called after a state mutation so the other tab's widgets reflect the
    new state — the per-tab combos are independent QWidget instances, so
    without this sync the inactive tab's UI would go stale.
    """
    for scope in _SCOPES:
        if scope == skip_scope:
            continue
        ctrl = getattr(app, f"_fc_ctrl_combo_{scope}", None)
        base = getattr(app, f"_fc_baseline_combo_{scope}", None)
        if ctrl is not None:
            _repopulate_control_combo(app, ctrl)
        if base is not None:
            _repopulate_baseline_combo(app, base)


def install_fold_change_controls(app, parent: QWidget, layout, *, scope: str) -> None:
    """Insert the Fold-change Control + Baseline dropdowns into *layout*.

    ``scope`` is "bar" or "line" — used to namespace the per-tab widget
    references stashed on ``app``. The dropdowns write through to the
    shared ``app._fc_*`` state so both tabs stay in lockstep.
    """
    title = QLabel("Fold change:", parent)
    f = title.font(); f.setBold(True); title.setFont(f)
    layout.addWidget(title)

    layout.addWidget(QLabel("Control", parent))
    ctrl_combo = _ControlCombo(app, parent)
    ctrl_combo.setMinimumWidth(140)
    ctrl_combo.setToolTip(
        "Divide each bar / curve by the picked well or replicate set's "
        "mean at the same timepoint. — disables this axis."
    )
    _repopulate_control_combo(app, ctrl_combo)
    layout.addWidget(ctrl_combo)

    layout.addWidget(QLabel("Baseline", parent))
    baseline_combo = QComboBox(parent)
    baseline_combo.setMinimumWidth(140)
    baseline_combo.setToolTip(
        "Divide each bar / curve by its own value at the reference "
        "timepoint. — disables this axis."
    )
    _repopulate_baseline_combo(app, baseline_combo)
    layout.addWidget(baseline_combo)

    def _redraw_all():
        # Both tabs share the state; redraw whichever is currently mounted.
        # Exceptions are surfaced via traceback so a failing redraw doesn't
        # silently look like the toggle did nothing.
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

    def _on_ctrl_changed(_idx: int) -> None:
        text = ctrl_combo.currentText()
        if text == _NONE_LABEL or not text:
            app._fc_vs_control_on = False
            app._fc_control_label = ""
        else:
            app._fc_vs_control_on = True
            app._fc_control_label = text
        _sync_widgets_to_state(app, skip_scope=scope)
        _redraw_all()

    def _on_baseline_changed(_idx: int) -> None:
        text = baseline_combo.currentText()
        app._fc_vs_t0_on = (text == _T0_LABEL)
        _sync_widgets_to_state(app, skip_scope=scope)
        _redraw_all()

    ctrl_combo.currentIndexChanged.connect(_on_ctrl_changed)
    baseline_combo.currentIndexChanged.connect(_on_baseline_changed)

    # Stash references so the cross-tab sync helper can reach them.
    setattr(app, f"_fc_ctrl_combo_{scope}", ctrl_combo)
    setattr(app, f"_fc_baseline_combo_{scope}", baseline_combo)
