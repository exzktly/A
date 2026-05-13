"""Round-trip binding check for the bindable custom widgets (Phase 6.5.1).

Run::

    python widgets/binding_check.py        # exits 0 iff every widget passes

For each widget that exposes ``bindingAdapter() -> (getter, setter,
change_signal)`` — `ToggleSwitch`, `SegmentedControl`, `ChipGroup` (exclusive
and multi-select), `Stepper`, `StyledSlider` — this:

  1. wires the widget two-way to a one-property in-memory model using the *same*
     ``(getter, setter, change_signal)`` contract that
     ``ExportStyleSidebar._bind_getter_setter`` uses (with a re-entrancy guard);
  2. checks model → widget propagation (set the model, the widget reflects it);
  3. checks widget → model propagation (drive the widget, the model reflects it);
  4. checks there's no feedback loop (a bounded number of cross-updates).

Prints ``[PASS]`` / ``[FAIL]`` per widget and ``ALL PASS`` / ``SOME FAILED``.
Needs PySide6; no Qt event loop is required (all updates are synchronous).

This is the harness for Phase 6.5.1a (user runtime QA). If pytest is available
it can also be wrapped — ``def test_binding(): assert run()`` — but the script
form works anywhere PySide6 does.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import theme  # noqa: E402,F401  (ensures repo-root import path is wired)
from widgets.chip_group import ChipGroup  # noqa: E402
from widgets.segmented_control import SegmentedControl  # noqa: E402
from widgets.stepper import Stepper  # noqa: E402
from widgets.styled_slider import StyledSlider  # noqa: E402
from widgets.toggle_switch import ToggleSwitch  # noqa: E402

_LOOP_LIMIT = 20  # a real feedback loop is unbounded; this catches it


class _Model(QObject):
    """A single-property model: ``.value`` (any) emits ``valueChanged`` on set."""

    valueChanged = Signal(object)

    def __init__(self, initial) -> None:
        super().__init__()
        self._v = initial

    @property
    def value(self):
        return self._v

    @value.setter
    def value(self, v) -> None:
        if v == self._v:
            return
        self._v = v
        self.valueChanged.emit(v)


def _bind(model: _Model, widget):
    """Two-way bind ``model.value`` <-> *widget* via ``bindingAdapter()``,
    re-entrancy-guarded. Returns ``(getter, state)`` where *state* counts the
    cross-updates (for the loop check)."""
    getter, setter, change_sig = widget.bindingAdapter()
    state = {"updating": False, "m2w": 0, "w2m": 0}

    def on_model_changed(v):
        if state["updating"]:
            return
        state["updating"] = True
        try:
            setter(v)
        finally:
            state["updating"] = False
        state["m2w"] += 1

    def on_widget_changed(*_a):
        if state["updating"]:
            return
        state["updating"] = True
        try:
            model.value = getter()
        finally:
            state["updating"] = False
        state["w2m"] += 1

    model.valueChanged.connect(on_model_changed)
    change_sig.connect(on_widget_changed)

    # initial sync: widget ← model
    state["updating"] = True
    try:
        setter(model.value)
    finally:
        state["updating"] = False
    return getter, state


def _check(name, widget, *, initial, model_new, widget_new, widget_action) -> bool:
    """*initial*: model's starting value (and the widget's after ``_bind``).
    *model_new*: a different value pushed from the model side.
    *widget_action(widget)*: a user-style change on the widget.
    *widget_new*: the value the widget should report after *widget_action*."""
    model = _Model(initial)
    getter, state = _bind(model, widget)
    msgs = []

    # (0) initial sync took
    if getter() != initial:
        msgs.append(f"initial sync: widget reports {getter()!r}, expected {initial!r}")

    # (1) model -> widget
    model.value = model_new
    if getter() != model_new:
        msgs.append(f"model→widget: set {model_new!r}, widget reports {getter()!r}")

    # (2) widget -> model
    widget_action(widget)
    if getter() != widget_new:
        msgs.append(f"widget set didn't take: widget reports {getter()!r}, expected {widget_new!r}")
    if model.value != widget_new:
        msgs.append(f"widget→model: widget {widget_new!r}, model {model.value!r}")

    # (3) no feedback loop
    if state["m2w"] > _LOOP_LIMIT or state["w2m"] > _LOOP_LIMIT:
        msgs.append(f"feedback loop suspected: m2w={state['m2w']} w2m={state['w2m']}")

    ok = not msgs
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else "  — " + "; ".join(msgs)))
    return ok


def run() -> bool:
    QApplication.instance() or QApplication([])
    print("Binding round-trip checks:")
    ok = True

    ts = ToggleSwitch()
    ok &= _check("ToggleSwitch", ts, initial=False, model_new=True,
                 widget_action=lambda w: w.setChecked(False), widget_new=False)

    sc = SegmentedControl()
    for txt, d in (("A", "a"), ("B", "b"), ("C", "c")):
        sc.addSegment(txt, data=d)
    ok &= _check("SegmentedControl", sc, initial="a", model_new="c",
                 widget_action=lambda w: w.setCurrentIndex(1), widget_new="b")

    cg = ChipGroup(exclusive=True)
    for txt, d in (("X", "x"), ("Y", "y"), ("Z", "z")):
        cg.addChip(txt, data=d)
    ok &= _check("ChipGroup (exclusive)", cg, initial="x", model_new="z",
                 widget_action=lambda w: w.setCurrentIndex(1), widget_new="y")

    cgm = ChipGroup(exclusive=False)
    for txt, d in (("Grid", "grid"), ("Legend", "legend"), ("Bars", "bars")):
        cgm.addChip(txt, data=d)
    ok &= _check("ChipGroup (multi)", cgm, initial=[], model_new=["grid", "bars"],
                 widget_action=lambda w: w.setCheckedData(["legend"]), widget_new=["legend"])

    st = Stepper(value=0.0, minimum=0.0, maximum=10.0, single_step=0.5, decimals=1)
    ok &= _check("Stepper", st, initial=0.0, model_new=3.5,
                 widget_action=lambda w: w.setValue(2.0), widget_new=2.0)

    sl = StyledSlider()
    sl.setRange(0, 100)
    ok &= _check("StyledSlider", sl, initial=0, model_new=70,
                 widget_action=lambda w: w.setValue(40), widget_new=40)

    print("ALL PASS" if ok else "SOME FAILED")
    return bool(ok)


if __name__ == "__main__":
    _sys.exit(0 if run() else 1)
