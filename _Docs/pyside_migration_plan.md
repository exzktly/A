# PySide Migration Remediation Plan

## Scope
- Codebase: `well_viewer/`
- Inputs: `_Docs/attribute_call_audit.csv` + `_Docs/attribute_call_audit.md`
- Goal: eliminate remaining legacy tkinter call patterns and unsafe late-init attribute accesses.

## Workstreams
1. **Legacy API Elimination**
   - Replace all `config/configure/pack/pack_forget/winfo_*` flagged calls with compatibility helper methods.
   - Owner: UI migration
   - Exit criteria: 0 flagged legacy method calls in audit.

2. **Variable Access Hardening**
   - Replace direct `*_var.get/set` with `_get_var_value/_set_var_value` in runtime callbacks where initialization order is non-deterministic.
   - Reduce dependency on `__getattr__` fallback over time.
   - Exit criteria: direct `*_var.get/set` retained only in safe post-init view construction paths.

3. **Lifecycle Guard Coverage**
   - Ensure redraw/save/event handlers check non-None readiness for widgets/axes/canvases before use.
   - Exit criteria: no AttributeError crashes in smoke tests under early tab-switch timing.

4. **Verification & Regression Gates**
   - Add CI step that regenerates audit and fails if legacy-call count increases.
   - Add smoke tests for startup + tab switch + redraw + export in partially initialized states.
   - Exit criteria: stable CI over 7 consecutive runs.

## Risk Matrix
- High: event handlers firing pre-init (`None` widget refs)
- Medium: mixed tk/qt helper behavior differences
- Low: static style/theme regressions

## Milestones
- M1: Baseline audit committed (done)
- M2: 100% legacy API call elimination
- M3: lifecycle guards complete
- M4: CI gate + board sign-off

## Board-Ready Deliverables
- Attribute call inventory table (full)
- Before/after counts by category
- Residual risk register and mitigation owners
