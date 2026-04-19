# TODO: Port GUI from tkinter to PySide6 (with simplification-first approach)

## Goals
- Replace all tkinter/ttk dependencies with PySide6.
- Reduce architectural complexity while porting (fewer hidden cross-module side effects, clearer ownership, smaller interfaces).
- Preserve user-visible behavior where it matters (core analysis flow, plot interactions, export paths), but avoid 1:1 widget translation when a simpler design is better.

> Maintenance rule for all future phases: always read `_Docs/tkinter_port_phase0_phase1.md` before starting work, and update it at the end of each phase with new cutlines, ownership, and migration decisions.

## Guiding simplification rules
1. **Prefer composition over global mutable app state**: stop attaching dozens of ad-hoc attributes to a single root app object.
2. **Use explicit data models** for state shared across views/controllers.
3. **Collapse thin pass-through layers** and duplicate controller/view helpers while porting.
4. **Minimize framework leakage**: keep PySide6 code at the UI boundary; keep business logic framework-agnostic.
5. **Feature freeze during migration**: no new features until parity and cleanup are complete.

---

## Phase 0 — Inventory & cutlines
- [x] Build a dependency map of tkinter usage (imports + widget factories + dialog calls) across:
  - `all_well.py`
  - `analyze_tab.py`
  - `ui/theme/`
  - `well_viewer/` (runtime app, tabs, views, controllers, export helpers)
  - `_Installation/` packaging scripts/spec
- [x] Mark modules into three buckets:
  1) pure logic (no UI framework),
  2) mixed logic/UI,
  3) UI-only.
- [x] Define migration cutlines so pure logic is frozen and reused without rewrite.

Deliverable: architecture note in `_Docs/` showing module ownership and migration order.

---

## Phase 1 — Introduce a minimal UI abstraction layer (temporary)
- [x] Create a temporary adapter package (e.g., `ui/ports/`) to isolate framework-coupled operations:
  - dialogs (open/save directory/file)
  - notifications (info/warn/error/confirm)
  - timers/invoke-later
  - clipboard/basic app services
- [x] Route existing dialog/messagebox calls through the adapter first, before full widget porting.
- [x] Ensure core services (pipeline, data loading, export logic) depend on adapter interfaces, not tkinter modules.

Simplification target: remove scattered direct imports such as `from tkinter import messagebox, filedialog` from non-view modules.

---

## Phase 2 — State model cleanup before widget swap
- [x] Replace large sets of `StringVar/BooleanVar/IntVar` with typed state objects (dataclasses or lightweight models).
- [x] Group state by feature domain:
  - analysis pipeline inputs/options
  - plotting/view options
  - grouping/replicate selections
  - export settings
- [x] Add explicit conversion/validation functions between UI widgets and state models.
- [x] Remove duplicated state definitions (same concept represented in multiple vars across files).

Simplification target: make state testable without a running GUI event loop.

---

## Phase 3 — Application shell migration
- [x] Replace root app bootstrap (`tk.Tk`, notebook shell, theme bootstrap) with PySide6 equivalents:
  - `QApplication`
  - `QMainWindow` (or a single top-level `QWidget` with clear layout)
  - `QTabWidget` / splitters / dock areas as needed
- [x] Rebuild top-level navigation and status/log area with simpler container layout.
- [x] Keep only one canonical entrypoint for desktop launch (avoid duplicate launch scripts where possible).

Simplification target: reduce custom notebook/shim code unless it is truly required.

---

## Phase 4 — Incremental tab/view ports (high-value first)
Port in vertical slices so each slice is runnable end-to-end:

- [x] Slice A: Analysis tab (`analyze_tab.py`) + run/stop/progress/log wiring.
- [x] Slice B: Core well viewer runtime shell (`well_viewer/runtime_app.py`) + key sidebars.
- [x] Slice C: Plot tabs and controls (`well_viewer/tabs/`, `well_viewer/views/`).
- [x] Slice D: Specialized editors/dialogs (`figure_export_editor.py`, `batch_export_dialog.py`, `smfish_tab.py`, `cell_gating_tab.py`).

For each slice:
- [x] Replace widget construction with Qt widgets.
- [x] Replace variable traces/binds with Qt signals/slots.
- [x] Move per-slice repeated helper code into shared, minimal utility modules.
- [x] Delete legacy compatibility shims immediately after parity for that slice.

---

## Phase 5 — Matplotlib backend + interaction parity
- [x] Switch from TkAgg toolbars/canvas to Qt backend (`FigureCanvasQTAgg`, `NavigationToolbar2QT`).
- [x] Normalize plot wiring behind a small plot-host helper to avoid duplicated canvas/toolbar setup across tabs.
- [x] Verify zoom/pan/save interactions and callback lifecycles.

Simplification target: one standard way to host matplotlib figures in the app.

---

## Phase 6 — Theming and styling simplification
- [x] Replace ttk style system in `ui/theme/styles.py` with Qt stylesheet + palette approach.
- [x] Prune style variants to a small supported set (e.g., dark/light + semantic button roles).
- [x] Remove style workarounds that existed only because of ttk limitations.

Simplification target: fewer style names, fewer per-widget special cases, centralized theme tokens.

---

## Phase 7 — Packaging/build/runtime updates
- [x] Update `_Installation/all_well.spec` and `_Installation/build_all_well.sh`:
  - remove tkinter checks/hidden imports
  - add PySide6 runtime packaging requirements
- [x] Confirm launcher expectations in `all_well_launcher.py` no longer mention TkAgg/tkinter constraints.
- [x] Update developer docs (`_Docs/README*.md`, root docs) for PySide6 prerequisites and run instructions.

---

## Phase 8 — Deletion and consolidation pass (required)
- [x] Remove dead tkinter codepaths and compatibility stubs.
- [x] Consolidate duplicated UI helper modules (button factories, repeated combobox boilerplate, repeated dialog wrappers).
- [x] Split oversized modules only where it reduces cognitive load; otherwise keep fewer, clearer files.
- [x] Enforce import boundaries (UI package cannot leak into core services).

Success criterion: no `tkinter` imports remain in runtime paths.

---

## Testing/verification plan (static + manual)
- [x] Add/adjust unit tests around migrated state models and adapter interfaces.
- [x] Add lightweight smoke checks for app startup and tab construction without full pipeline execution.
- [x] Manual QA checklist:
  - startup + theme toggle
  - folder/file dialogs
  - run/stop pipeline UX
  - all plotting tabs and exports
  - replicate/group editing flows
  - batch export flows

---

## Suggested execution order (pragmatic)
1. Adapter layer + dialog/message cleanup
2. State model cleanup
3. App shell port
4. Analysis tab
5. Core viewer and plot host standardization
6. Remaining specialized tabs/dialogs
7. Theme + packaging + docs
8. Dead code deletion/consolidation

---

## Finish plan from current state
Completed.

---

## Definition of done
- [x] PySide6 is the only GUI framework dependency.
- [x] No tkinter imports in application code or packaging scripts.
- [x] Main user workflows work with equivalent or simpler UX.
- [x] Module boundaries are clearer than before migration.
- [x] Net complexity reduced (fewer global mutable fields, fewer duplicated helpers, fewer special-case codepaths).
