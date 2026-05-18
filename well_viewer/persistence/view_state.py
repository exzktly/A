"""Live UI view-state persistence — ``view_state`` section of ``persistence.json``.

Captures the user's *view* (active tab, selected wells, active channel /
metric, fold-change scopes, per-plot-tab combos) so reopening a dataset
lands them where they left off. Per-tab combo restore is deferred: the
state is stashed on ``app._view_state_pending`` at load time and popped
into the live widgets the first time each tab becomes active (some tabs
build lazily on first visit).

Save triggers: app close and dataset switch. No continuous autosave —
view changes happen interactively and a save-per-keystroke would burn I/O
for no user benefit.
"""

from __future__ import annotations

import logging
from typing import Any

from well_viewer.persistence import _doc

_logger = logging.getLogger("well_viewer")

# Plot sub-tab names that live inside the "Plotting" parent stack.
_PLOT_SUBTABS = (
    "Line Graphs", "Bar Plots", "Scatter Plot", "Distribution", "Heat Map",
)


# ── snapshot ───────────────────────────────────────────────────────────────

def snapshot(app) -> dict:
    """Build a JSON-serialisable view-state dict from current app state."""
    return {
        "schema_version": 1,
        "selected_wells": sorted(getattr(app, "_selected_wells", set()) or []),
        "active_centre_tab": _current_leaf_tab(app),
        "active_channel": str(getattr(app, "_active_channel", "") or ""),
        "active_metric": str(getattr(app, "_active_metric", "") or ""),
        "use_sem": bool(getattr(app, "_use_sem", True)),
        "fold_change": {
            "vs_control_on": bool(getattr(app, "_fc_vs_control_on", False)),
            "control_label": str(getattr(app, "_fc_control_label", "") or ""),
            "vs_t0_on": bool(getattr(app, "_fc_vs_t0_on", False)),
        },
        "export_style_prefs": dict(getattr(app, "_export_style_prefs", {}) or {}),
        "tabs": _snapshot_tabs(app),
    }


def _current_leaf_tab(app) -> str:
    fn = getattr(app, "_current_centre_tab", None)
    if callable(fn):
        try:
            return str(fn() or "")
        except Exception:
            return ""
    return ""


def _snapshot_tabs(app) -> dict[str, dict]:
    """Capture per-tab combo state for tabs we know how to round-trip.

    Tab files aren't modified — we read from the widget references the
    build functions already stash on ``app``. Missing widgets (tab not
    built yet) produce an empty dict for that tab.
    """
    tabs: dict[str, dict] = {}
    bar = _snapshot_bar(app)
    if bar:
        tabs["Bar Plots"] = bar
    dist = _snapshot_distribution(app)
    if dist:
        tabs["Distribution"] = dist
    scat = _snapshot_scatter(app)
    if scat:
        tabs["Scatter Plot"] = scat
    return tabs


def _combo_text(app, attr: str) -> str | None:
    w = getattr(app, attr, None)
    if w is None:
        return None
    try:
        return str(w.currentText())
    except Exception:
        return None


def _snapshot_bar(app) -> dict:
    out: dict[str, Any] = {}
    tp = _combo_text(app, "_bar_tp_cb")
    if tp is not None:
        out["timepoint"] = tp
    if hasattr(app, "_bar_swarm"):
        out["swarm"] = bool(app._bar_swarm)
    if hasattr(app, "_bar_violin"):
        out["violin"] = bool(app._bar_violin)
    slider = getattr(app, "_violin_slider", None)
    if slider is not None:
        try:
            out["violin_smooth"] = int(slider.value())
        except Exception:
            pass
    return out


def _snapshot_distribution(app) -> dict:
    out: dict[str, Any] = {}
    tp = _combo_text(app, "_distribution_tp_cb")
    if tp is not None:
        out["timepoint"] = tp
    mode = _combo_text(app, "_distribution_mode_cb")
    if mode is not None:
        out["mode"] = mode
    layout = _combo_text(app, "_distribution_layout_cb")
    if layout is not None:
        out["layout"] = layout
    if hasattr(app, "_distribution_bins"):
        out["bins"] = int(app._distribution_bins)
    if hasattr(app, "_distribution_log_x"):
        out["log_x"] = bool(app._distribution_log_x)
    return out


def _snapshot_scatter(app) -> dict:
    out: dict[str, Any] = {}
    for key, attr in (
        ("ch_x", "_scatter_ch_x_cb"),
        ("metric_x", "_scatter_metric_x_cb"),
        ("ch_y", "_scatter_ch_y_cb"),
        ("metric_y", "_scatter_metric_y_cb"),
        ("timepoint", "_scatter_tp_cb"),
    ):
        v = _combo_text(app, attr)
        if v is not None:
            out[key] = v
    return out


# ── restore ────────────────────────────────────────────────────────────────

def restore(app, state: dict) -> None:
    """Apply *state* in two phases — cross-cutting now, per-tab deferred.

    Per-tab combo values are stashed on ``app._view_state_pending`` and
    flushed by ``apply_pending_tab_state`` when each tab becomes active.
    """
    if not isinstance(state, dict):
        return

    # Cross-cutting state — apply eagerly.

    wells = state.get("selected_wells") or []
    if isinstance(wells, list):
        valid = {str(w) for w in wells if isinstance(w, str)}
        valid &= set(getattr(app, "_well_paths", {}) or {})
        if valid and hasattr(app, "_set_selected_wells"):
            try:
                app._set_selected_wells(valid, commit=False)
            except Exception:
                _logger.debug("view_state: _set_selected_wells failed", exc_info=True)

    if "use_sem" in state:
        try:
            app._use_sem = bool(state["use_sem"])
        except Exception:
            pass

    fc = state.get("fold_change") or {}
    if isinstance(fc, dict):
        if "vs_control_on" in fc:
            app._fc_vs_control_on = bool(fc.get("vs_control_on"))
        if "control_label" in fc:
            app._fc_control_label = str(fc.get("control_label") or "")
        if "vs_t0_on" in fc:
            app._fc_vs_t0_on = bool(fc.get("vs_t0_on"))

    prefs_in = state.get("export_style_prefs")
    if isinstance(prefs_in, dict):
        existing = getattr(app, "_export_style_prefs", None)
        if isinstance(existing, dict):
            existing.update(prefs_in)
        else:
            app._export_style_prefs = dict(prefs_in)

    # Active channel — validated against the canonical list. Fall through
    # silently when the saved channel no longer exists in the new dataset.
    ch = state.get("active_channel")
    fluor = list(getattr(app, "_fluor_channels", []) or [])
    if (
        isinstance(ch, str) and ch
        and ch in fluor
        and hasattr(app, "_set_active_channel")
    ):
        try:
            app._set_active_channel(ch)
        except Exception:
            _logger.debug("view_state: _set_active_channel failed", exc_info=True)

    metric = state.get("active_metric")
    if isinstance(metric, str) and metric:
        app._active_metric = metric

    # Stash per-tab state for deferred apply on first tab visit.
    tabs = state.get("tabs") or {}
    if isinstance(tabs, dict) and tabs:
        app._view_state_pending = {str(k): dict(v) for k, v in tabs.items() if isinstance(v, dict)}

    # Active tab is restored last so its on-change hook triggers any
    # lazy build with cross-cutting state already in place. Drives the
    # nested plotting stack when a plot sub-tab is requested.
    target = state.get("active_centre_tab")
    if isinstance(target, str) and target:
        _activate_tab(app, target)


def _activate_tab(app, name: str) -> None:
    outer = getattr(app, "_notebook", None)
    if outer is None:
        return
    try:
        if name in _PLOT_SUBTABS:
            outer.setCurrentByName("Plotting")
            sub = getattr(app, "_plotting_notebook", None)
            if sub is not None:
                sub.setCurrentByName(name)
        else:
            outer.setCurrentByName(name)
    except Exception:
        _logger.debug("view_state: tab activation failed for %r", name, exc_info=True)


def apply_pending_tab_state(app, tab_name: str) -> None:
    """Pop *tab_name*'s pending state (if any) into live widgets.

    Called from ``_on_tab_change`` so a tab that built lazily still receives
    its restored combo values the first time the user lands on it.
    """
    pending = getattr(app, "_view_state_pending", None)
    if not pending:
        return
    state = pending.pop(tab_name, None)
    if not state:
        return
    try:
        if tab_name == "Bar Plots":
            _apply_bar(app, state)
        elif tab_name == "Distribution":
            _apply_distribution(app, state)
        elif tab_name == "Scatter Plot":
            _apply_scatter(app, state)
    except Exception:
        _logger.debug("view_state: apply_pending_tab_state(%r) failed", tab_name, exc_info=True)


def _set_combo_if_valid(app, attr: str, value: str) -> None:
    w = getattr(app, attr, None)
    if w is None:
        return
    try:
        items = [w.itemText(i) for i in range(w.count())]
        if value in items:
            w.setCurrentText(value)
    except Exception:
        pass


def _apply_bar(app, state: dict) -> None:
    if "timepoint" in state:
        _set_combo_if_valid(app, "_bar_tp_cb", str(state["timepoint"]))
    if "swarm" in state:
        app._bar_swarm = bool(state["swarm"])
    if "violin" in state:
        app._bar_violin = bool(state["violin"])
    slider = getattr(app, "_violin_slider", None)
    if slider is not None and "violin_smooth" in state:
        try:
            slider.setValue(int(state["violin_smooth"]))
        except Exception:
            pass


def _apply_distribution(app, state: dict) -> None:
    if "timepoint" in state:
        _set_combo_if_valid(app, "_distribution_tp_cb", str(state["timepoint"]))
    if "mode" in state:
        _set_combo_if_valid(app, "_distribution_mode_cb", str(state["mode"]))
    if "layout" in state:
        _set_combo_if_valid(app, "_distribution_layout_cb", str(state["layout"]))
    if "bins" in state:
        try:
            bins = int(state["bins"])
        except (TypeError, ValueError):
            return
        spin = getattr(app, "_distribution_bins_spin", None)
        if spin is not None:
            try:
                spin.setValue(bins)
            except Exception:
                pass
        app._distribution_bins = bins
    if "log_x" in state:
        app._distribution_log_x = bool(state["log_x"])
        cb = getattr(app, "_distribution_log_x_cb", None)
        if cb is not None:
            try:
                cb.setChecked(bool(state["log_x"]))
            except Exception:
                pass


def _apply_scatter(app, state: dict) -> None:
    for key, attr in (
        ("ch_x", "_scatter_ch_x_cb"),
        ("metric_x", "_scatter_metric_x_cb"),
        ("ch_y", "_scatter_ch_y_cb"),
        ("metric_y", "_scatter_metric_y_cb"),
        ("timepoint", "_scatter_tp_cb"),
    ):
        if key in state:
            _set_combo_if_valid(app, attr, str(state[key]))


# ── save / load entry points ───────────────────────────────────────────────

def save_to_data_dir(app) -> None:
    if not getattr(app, "_data_dir", None):
        return
    try:
        state = snapshot(app)
    except Exception:
        _logger.exception("view_state: snapshot failed; not saving")
        return
    _doc.set_section(app, "view_state", state)


def load_from_data_dir(app) -> None:
    if not getattr(app, "_data_dir", None):
        return
    state = _doc.get_section(app, "view_state")
    if not isinstance(state, dict):
        return
    sv = state.get("schema_version")
    if sv is not None and sv != 1:
        _logger.warning("view_state schema_version=%r; ignoring saved state.", sv)
        return
    try:
        restore(app, state)
    except Exception:
        _logger.exception("view_state: restore failed; continuing with defaults")
