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

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QWidget,
)


_NONE_LABEL = "—"
_T0_LABEL = "t0 (first timepoint)"


# ── Scope registry ──────────────────────────────────────────────────────────
#
# A "scope" is a tab that owns its own fold-change combo widgets but
# shares state with every other scope via ``app._fc_*``. Each scope
# entry declares how to find that tab's widgets and which redraw
# method drives its plot. ``install_fold_change_controls(scope=…)``
# stashes the per-tab QComboBox refs on the app under the names the
# scope's descriptor specifies; ``_sync_widgets_to_state`` and
# ``set_fold_change_state`` iterate the registry instead of hard-
# coding scope-specific names.
#
# Adding a third tab (e.g. distribution / scatter) is a one-liner —
# register it with the dropdown attribute pattern and redraw method.


@dataclass(frozen=True)
class FoldChangeScope:
    """Per-tab description used by the cross-tab sync + redraw glue."""
    name: str
    ctrl_combo_attr: str
    baseline_combo_attr: str
    redraw_method: str  # method name on ``WellViewerApp``


_REGISTERED_SCOPES: "dict[str, FoldChangeScope]" = {}


def register_fold_change_scope(scope: FoldChangeScope) -> None:
    """Add a tab to the cross-tab fold-change sync set.

    Idempotent — registering the same scope twice replaces the prior
    entry. Call before any combo handler in the new tab fires.
    """
    _REGISTERED_SCOPES[scope.name] = scope


def registered_scopes() -> "tuple[FoldChangeScope, ...]":
    return tuple(_REGISTERED_SCOPES.values())


# Default registrations — the two scopes that exist today. Kept here
# (rather than at each tab's import site) so the registry is populated
# even when only one tab has been instantiated.
register_fold_change_scope(FoldChangeScope(
    name="bar",
    ctrl_combo_attr="_fc_ctrl_combo_bar",
    baseline_combo_attr="_fc_baseline_combo_bar",
    redraw_method="_redraw_bars",
))
register_fold_change_scope(FoldChangeScope(
    name="line",
    ctrl_combo_attr="_fc_ctrl_combo_line",
    baseline_combo_attr="_fc_baseline_combo_line",
    redraw_method="_redraw",
))

# Disambiguation suffix appended to a well-token combo entry when there is
# a replicate set with the same name. Without this, picking the entry
# would silently resolve to the replicate set (see resolve_control_wells)
# leaving the user no way to address the bare well. The suffix is stripped
# before the label is stored / dispatched, so existing saved selections
# without collisions are unaffected.
_WELL_DISAMBIG_SUFFIX = " (well)"


def _strip_well_suffix(label: str) -> str:
    """Remove the well-disambiguation suffix if present."""
    if label.endswith(_WELL_DISAMBIG_SUFFIX):
        return label[: -len(_WELL_DISAMBIG_SUFFIX)]
    return label


def _all_member_labels(app) -> list[str]:
    """Replicate-set names + selected well tokens currently plotted.

    When a well token collides with a rep-set name (e.g. someone named a
    rep-set "A01"), the well entry is suffixed with " (well)" so the
    user can pick either unambiguously.
    """
    names: list[str] = []
    repset_names: set[str] = set()
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
            repset_names.add(name)
    well_paths = getattr(app, "_well_paths", None) or {}
    for w in sorted(getattr(app, "_selected_wells", []) or [], key=lambda x: x):
        if w in well_paths and w not in seen:
            entry = w + _WELL_DISAMBIG_SUFFIX if w in repset_names else w
            names.append(entry)
            seen.add(w)
    return names


def _repopulate_control_combo(app, combo: QComboBox) -> None:
    """Refresh the Control combo's item list from current selections.

    Skips the clear-and-repopulate if (a) the combo's popup is currently
    visible (don't yank the dropdown out from under the user) or (b) the
    candidate list is identical to what the combo already shows. The
    selected index is still re-synced from app state.
    """
    members = _all_member_labels(app)
    saved = getattr(app, "_fc_control_label", "") or ""
    # If the saved label matches a bare well token AND there's a
    # collision-suffixed entry in the candidate list, prefer the suffixed
    # form so the user-visible state is unambiguous.
    if saved and saved in members:
        saved_display = saved
    elif saved + _WELL_DISAMBIG_SUFFIX in members:
        saved_display = saved + _WELL_DISAMBIG_SUFFIX
    else:
        saved_display = saved

    candidate_items = [_NONE_LABEL, *members]
    current_items = [combo.itemText(i) for i in range(combo.count())]
    popup_visible = False
    try:
        view = combo.view()
        popup_visible = bool(view is not None and view.isVisible())
    except Exception:
        pass

    blocked = combo.blockSignals(True)
    try:
        if current_items != candidate_items and not popup_visible:
            combo.clear()
            for m in candidate_items:
                combo.addItem(m)
        idx = combo.findText(saved_display) if saved_display else 0
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
    without this sync the inactive tab's UI would go stale. Iterates the
    scope registry, so adding a third tab only requires registering it.
    """
    for scope in registered_scopes():
        if scope.name == skip_scope:
            continue
        ctrl = getattr(app, scope.ctrl_combo_attr, None)
        base = getattr(app, scope.baseline_combo_attr, None)
        if ctrl is not None:
            _repopulate_control_combo(app, ctrl)
        if base is not None:
            _repopulate_baseline_combo(app, base)


def set_fold_change_state(
    app, *,
    vs_control_on: "bool | None" = None,
    control_label: "str | None" = None,
    vs_t0_on: "bool | None" = None,
    initiating_scope: str = "",
) -> None:
    """Single entry point for fold-change state mutations.

    Mirrors the shape of ``runtime_app._set_active_channel`` — every
    combo handler funnels through here so state mutation, widget sync,
    and redraw fire in a fixed order regardless of which tab initiated
    the change. ``None`` arguments leave the corresponding field
    unchanged. ``initiating_scope`` lets the caller skip syncing back
    into the widget that just wrote the value (it already holds it,
    and re-applying could yank an open popup).
    """
    import traceback

    if vs_control_on is not None:
        app._fc_vs_control_on = bool(vs_control_on)
    if control_label is not None:
        # Normalize: drop the disambiguation suffix in storage so the
        # underlying state stays a bare well token / rep-set name.
        # ``resolve_control_wells`` would handle the suffix too, but
        # we'd rather not push the UI artefact down the stack.
        label = control_label
        if label.endswith(_WELL_DISAMBIG_SUFFIX):
            label = label[: -len(_WELL_DISAMBIG_SUFFIX)]
        app._fc_control_label = label
    if vs_t0_on is not None:
        app._fc_vs_t0_on = bool(vs_t0_on)

    _sync_widgets_to_state(app, skip_scope=initiating_scope)

    # Redraw every registered scope's plot. Exceptions are surfaced via
    # traceback so a failing redraw doesn't silently look like the
    # toggle did nothing.
    for scope in registered_scopes():
        method = getattr(app, scope.redraw_method, None)
        if method is None:
            continue
        try:
            method()
        except Exception:
            traceback.print_exc()


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

    def _on_ctrl_changed(_idx: int) -> None:
        text = ctrl_combo.currentText()
        if text == _NONE_LABEL or not text:
            set_fold_change_state(
                app, vs_control_on=False, control_label="",
                initiating_scope=scope,
            )
        else:
            set_fold_change_state(
                app, vs_control_on=True, control_label=text,
                initiating_scope=scope,
            )

    def _on_baseline_changed(_idx: int) -> None:
        text = baseline_combo.currentText()
        set_fold_change_state(
            app, vs_t0_on=(text == _T0_LABEL),
            initiating_scope=scope,
        )

    ctrl_combo.currentIndexChanged.connect(_on_ctrl_changed)
    baseline_combo.currentIndexChanged.connect(_on_baseline_changed)

    # Stash references using the scope descriptor's attribute names so
    # the cross-tab sync helper picks them up via the registry. Falls
    # back to the standard naming pattern when the scope isn't
    # registered (e.g. a test stub).
    descriptor = _REGISTERED_SCOPES.get(scope)
    ctrl_attr = (descriptor.ctrl_combo_attr if descriptor
                 else f"_fc_ctrl_combo_{scope}")
    baseline_attr = (descriptor.baseline_combo_attr if descriptor
                     else f"_fc_baseline_combo_{scope}")
    setattr(app, ctrl_attr, ctrl_combo)
    setattr(app, baseline_attr, baseline_combo)
