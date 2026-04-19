# Context
All-Well is a scientific well-plate microscopy GUI (~21K LoC across 37 tkinter-importing files). The tkinter foundation carries real accidental complexity: a 598-line ui/theme/styles.py with recursive widget-tree color walks, a custom WellLabel(tk.Label) subclass that exists only to work around macOS Aqua ignoring tk.Button backgrounds, 131 tk.Variable instances, 146 .bind() calls, and dual-source-of-truth color constants.
Switching to PySide6 lets us keep Qt-native dark-mode integration, replace the recursive theme walk with a single QSS stylesheet, delete the WellLabel workaround, and drop most tk.Variable wiring in favor of direct widget reads. Strategy (per user): one-shot full port in a single PR, keep Dark/Light toggle via QSS, update PyInstaller spec in same PR.
Feature parity is required: both tabs, dark/light toggle, plate-map drag-select, matplotlib plots, image-panel LUT editor, batch export, figure-export editor, PyInstaller macOS bundle.

# Strategy
Big-bang rewrite in a single PR with 5 sequenced commits (only the last commit fully launches):

# Foundation + shell — port all_well.py to QMainWindow, rewrite ui/theme/styles.py as QSS producer, author dark.qss/light.qss.
Views & tabs — port well_viewer/views/*.py, well_viewer/tabs/*.py, analyze_tab.py, cell_gating_tab.py, smfish_tab.py, figure_export_editor.py.
runtime_app + controllers — port the 6941-line runtime_app.py in place (no class restructure) plus 10 *_controller.py files.
Theme polish — wire _on_theme_change to QApplication.setStyleSheet(build_stylesheet(name)); delete WellLabel, update_widget_colors, rebuild_widget_colors.
Packaging — rewrite _Installation/all_well.spec, flip matplotlib.use("TkAgg") → "QtAgg".

# Tests in tests/ target services (no GUI imports) and must stay green after every commit.

# File-by-file plan (37 files)

## Delete:

well_viewer/views/widgets.py — _Tooltip replaced by Qt built-in.
well_viewer/views/well_label_widget.py — Aqua workaround no longer needed; wells become QPushButton with an objectName/dynamic property.
well_viewer/app.py — facade existed to defer tk.Tk creation; unneeded in Qt. Re-export WellViewerApp from well_viewer/__init__.py.
scripts/ui_smoke_review_image_preserve_view.py — mocks-tk smoke script; delete (redundant with tests/).

## Rewrite:

ui/theme/styles.py — drop apply_all_well_theme, update_widget_colors, rebuild_widget_colors, duplicated module-level color constants, ttk.Style config, option_add for combobox listboxes. Keep: THEMES dict, _WELL_COLORS, set_theme(), get_color(), font tuples. Add: build_stylesheet(theme_name: str) -> str that reads a .qss template and string.Template.substitute()s the active palette. Target: ~150 LoC Python + two ~200-LoC .qss files.
ui/theme/__init__.py — re-export the surviving surface only.
all_well.py — AllWellApp(QMainWindow), header QWidget with title QLabel + theme QComboBox, QTabWidget with two tabs. Preserve the _install_app_icon algorithm by drawing into a QImage via setPixel(x, y, QColor(...).rgb()). _on_theme_change collapses to QApplication.instance().setStyleSheet(build_stylesheet(name)) + unpolish/polish on top-level children.
all_well_launcher.py — change matplotlib.use("TkAgg") → "QtAgg"; keep _MEIPASS handling.

## Port + simplify:

well_viewer/views/centre_view.py — CustomNotebook → QTabWidget (drop the hand-drawn tab chrome; QSS handles it).
well_viewer/views/image_panel_view.py — tk.Canvas → QLabel + QPixmap; LUT editor with QLineEdit+QPushButton; mouseover pixel tooltip via mouseMoveEvent + QToolTip.showText().
well_viewer/views/sidebar_view.py, grouping_view.py, bar_group_panel_view.py, replicate_panel_view.py, preview_panel_view.py, preview_view.py, stats_view.py, status_view.py, label_editor_view.py — mechanical port; drop StringVar/BooleanVar/DoubleVar in favor of direct widget reads.
well_viewer/tabs/bar_plots_tab_view.py, line_graphs_tab_view.py, scatter_cells_tab_view.py, scatter_agg_tab_view.py, batch_export_tab_view.py, review_csv_tab_view.py — swap matplotlib canvas/toolbar; ttk.Treeview → QTableWidget in review_csv_tab_view.py.
analyze_tab.py (1399 LoC), well_viewer/cell_gating_tab.py (537), well_viewer/smfish_tab.py (639), well_viewer/figure_export_editor.py (483) — mechanical port, same class structure.
Controllers: load_controller.py, stats_controller.py, grouping_controller.py, montage_controller.py, preview_controller.py, barplot_controller.py, lineplot_controller.py, scatter_controller.py, selection_controller.py, review_image_controller.py — drop tk.Event type hints; swap messagebox→QMessageBox, filedialog→QFileDialog, .after()→QTimer.singleShot.
well_viewer/preview_callbacks.py, scatter_callbacks.py, plot_orchestrator.py, export_service.py, ui_helpers.py — drop tk imports; map messagebox/filedialog/scrollable-canvas helpers to Qt equivalents.

## Port in place (no restructure this PR):

well_viewer/runtime_app.py (6941 LoC) — subclass QWidget; mechanical swap; keep all method names so the cross-module getattrs and plot_orchestrator bindings keep working. Expect ~20–30 % line reduction from tk.Variable removal and recursive-walk deletion.
well_viewer/batch_export_dialog.py (2030 LoC) — mechanical swap; call out as future refactor target in commit message.

# QSS stylesheet design
Two files ui/theme/dark.qss and ui/theme/light.qss with ${TOKEN} placeholders. build_stylesheet(name) loads the file and runs string.Template(text).substitute(THEMES[name] | _WELL_COLORS).
Button variants attach via setProperty("variant", "primary") and a selector QPushButton[variant="primary"]. Plate wells get objectName="WellButton" plus a state property ("empty", "selected", "group_a", ...) driving QSS:
QPushButton[variant="primary"]   { background: ${ACCENT}; color: ${CLR_WHITE}; }
QPushButton[variant="secondary"] { background: ${BG_CELL}; color: ${TXT_PRI}; }
QPushButton[variant="danger"]    { background: ${CLR_DANGER}; color: ${CLR_WHITE}; }
QPushButton:hover { background: ${BG_HOVER}; }
QPushButton[objectName="WellButton"][state="selected"] { background: ${ACCENT}; }
QTabBar::tab          { background: ${TAB_BG}; color: ${TAB_FG}; padding: 6px 14px; }
QTabBar::tab:selected { background: ${TAB_BG_ACTIVE}; color: ${TAB_FG_ACTIVE}; }
After a property change, call w.style().unpolish(w); w.style().polish(w) so QSS re-applies.

# Plate-map / WellLabel replacement
QGridLayout of WellButton(QPushButton) subclass (~30 LoC) with an objectName="WellButton" + dynamic state property. Drag-select reuses today's press/move/release state machine via mousePressEvent/mouseMoveEvent/mouseReleaseEvent on the grid container plus container.childAt(event.position().toPoint()) to find the well under the cursor. Colour transitions are QSS-only — no Python color rewiring on theme change.

# Matplotlib integration
Set matplotlib.use("QtAgg") once in all_well_launcher.py before any pyplot import. 
Every embed site:

```
pythonfrom matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
canvas = FigureCanvas(fig)
layout.addWidget(canvas)
toolbar = NavigationToolbar(canvas, parent_widget)
layout.addWidget(toolbar)
```
canvas.draw() / draw_idle() API is identical. Threaded figure updates (several controllers run a threading.Thread that mutates a Figure) must marshal back to the GUI thread via a QObject helper emitting a Signal connected to a slot that calls canvas.draw_idle() — never call draw() from a worker thread.

# PyInstaller (_Installation/all_well.spec)

hiddenimports: remove tkinter, tkinter.ttk, tkinter.filedialog, tkinter.messagebox, matplotlib.backends.backend_tkagg, matplotlib.backends._backend_tk, PIL.ImageTk. Add PySide6, PySide6.QtCore, PySide6.QtGui, PySide6.QtWidgets, shiboken6, matplotlib.backends.backend_qtagg, matplotlib.backends.backend_qt.
excludes: remove PySide6, PyQt5, PyQt6, PySide2. Add tkinter, _tkinter.
Rely on PyInstaller's built-in PySide6 hook; fall back to collect_data_files("PySide6", subdir="Qt/plugins/platforms") only if Qt plugins fail to load at runtime.
Also add PySide6 to requirements.txt.

# Critical files to modify

/home/user/A/all_well.py
/home/user/A/all_well_launcher.py
/home/user/A/ui/theme/styles.py (rewrite) + new ui/theme/dark.qss, ui/theme/light.qss
/home/user/A/well_viewer/runtime_app.py
/home/user/A/well_viewer/batch_export_dialog.py
/home/user/A/well_viewer/views/image_panel_view.py
/home/user/A/well_viewer/views/centre_view.py
/home/user/A/well_viewer/views/well_label_widget.py (delete) → new well_viewer/views/well_button.py
/home/user/A/well_viewer/views/widgets.py (delete)
/home/user/A/well_viewer/app.py (delete) + well_viewer/__init__.py (re-export)
/home/user/A/analyze_tab.py
All well_viewer/tabs/*.py, remaining well_viewer/views/*.py, remaining well_viewer/*.py controllers
/home/user/A/_Installation/all_well.spec
/home/user/A/scripts/ui_smoke_review_image_preserve_view.py (delete)

# Acceptance gate (grep sweep)
Before merging, these counts must be zero across the repo:

^import tkinter / ^from tkinter
customtkinter
FigureCanvasTkAgg, NavigationToolbar2Tk, backend_tkagg
tk.StringVar, tk.IntVar, tk.BooleanVar, tk.DoubleVar
messagebox., filedialog.
.after(, .bind("<
ttk.

# Verification

pytest tests/ — all 6 test files green (services untouched).
python all_well.py launches; both tabs populate; Dark↔Light toggle repaints every panel without artifacts.
python all_well.py --data_dir /path/to/results loads the dataset on startup.
Plate-map: click + drag selects wells; selected state persists across theme switch.
Each plot sub-tab (bar, line, scatter-cells, scatter-agg, review-csv, batch-export) renders its matplotlib figure; toolbar pan/zoom works.
Image panel: LUT min/max editor adjusts display; pixel tooltip on mouseover.
Save dialogs (figure export, batch export, CSV export) return valid paths via QFileDialog.
Invalid-path error path shows QMessageBox.
Run Analyze pipeline end-to-end — on completion the app switches to Review and loads the result.
cd _Installation && pyinstaller all_well.spec builds dist/AllWell.app; double-clicking launches it; smoke steps 2–9 repeat inside the bundle.

# Risks & open questions

Threaded mpl updates — audit every threading.Thread that touches a Figure; wire through Signal→slot→draw_idle().
Cross-tab state (_cell_threshold, theme) — replace tk.Variable sharing with a plain Python attribute on AllWellApp plus a Signal both tabs connect to.
High-DPI / Retina — call QApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough) before constructing QApplication; ensure image-panel QPixmap respects devicePixelRatio on Retina.
Bundle size — PySide6 + Qt adds ~150–200 MB. If needed, exclude unused Qt modules (PySide6.QtWebEngine*, PySide6.Qt3D*, etc.) via --exclude-module.
macOS menu bar — call QMainWindow.setMenuBar(None) to avoid an empty native menu bar, unless promoting existing actions into a real menu.

# PySide6 Migration — Port Progress (live)

Last updated: 2026-04-19 (UTC).

Strategy used so far: migrate runtime behavior into Qt tab/view builders and service/controller entry points while preserving public method names expected by cross-module callers.

## Completed

- [x] Foundation shell and theming migration (`all_well.py`, `ui/theme/*.qss`, launcher backend switch)
- [x] Qt port for core tab/view modules under `well_viewer/views/*` and `well_viewer/tabs/*`
- [x] `runtime_app.py` migration to Qt runtime shell:
  - [x] `WellViewerApp` now subclasses `QWidget`
  - [x] Qt tab composition wired through migrated tab builders
  - [x] Runtime export/review/batch handlers wired to existing service/controller functions
  - [x] Qt `main()` entrypoint

## Remaining before merge

- [ ] End-to-end runtime feature parity verification against checklist (plots, review image interactions, batch export flows, pipeline handoff)
- [x] Repository-wide acceptance grep sweep with all target patterns at zero
- [ ] Environment-stable green test run (`PYTHONPATH=. pytest -q tests`) in an environment with required runtime deps installed
- [ ] Packaging/bundle completion (`_Installation/all_well.spec`, PyInstaller app smoke run) — deferred with Phase 4

# Step-by-step execution checklist (completion path)

This section is the actionable sequence to finish the port and remove all legacy tkinter code.
Work top-to-bottom; do not skip acceptance checks between phases.

## Phase 0 — Baseline + guardrails

- [x] Confirm working tree is clean and capture current migration baseline:
  - [x] `git status --short`
  - [x] `rg -n "^import tkinter|^from tkinter|customtkinter|FigureCanvasTkAgg|NavigationToolbar2Tk|backend_tkagg|tk\\.StringVar|tk\\.IntVar|tk\\.BooleanVar|tk\\.DoubleVar|messagebox\\.|filedialog\\.|\\.after\\(|\\.bind\\(\"<|\\bttk\\." --glob '*.py'`
  - [x] `PYTHONPATH=. pytest -q tests` (record any environment-limited failures separately from code failures)
- [x] Create/update a migration tracking note with:
  - [x] Remaining Tk hit counts by pattern
  - [x] List of files containing each pattern
  - [x] Current blockers (missing deps, failing tests, etc.)

## Phase 1 — Restore testability boundaries (no GUI imports in service tests)

- [x] Identify tests that import Qt-dependent modules indirectly.
- [ ] Move pure helper logic used by tests into GUI-free modules (or add GUI-free helper wrappers).
- [ ] Update tests to import only GUI-free modules for non-UI behaviors.
- [ ] Ensure `tests/` collection succeeds without requiring app launch.
- [x] Re-run `PYTHONPATH=. pytest -q tests` and document exact remaining failures.

## Phase 2 — runtime_app.py core de-tkification (largest remaining surface)

- [x] Port `WellViewerApp.__init__` state to Qt/native runtime state holders.
- [x] Replace scheduling/event plumbing in runtime shell (`QTimer.singleShot` in startup load path).
- [x] Replace runtime dialog paths with `QMessageBox` / `QFileDialog`.
- [x] Remove direct `ttk` usage from `runtime_app.py`.
- [x] Remove Tk-named matplotlib aliases from runtime shell.
- [x] Preserve expected cross-module runtime method surface and wire key handlers to controller/service entry points.

## Phase 3 — Remaining module cleanup pass

- [x] Sweep controllers/callbacks/services for any residual Tk references:
  - [x] `load_controller.py`
  - [x] `stats_controller.py`
  - [x] `grouping_controller.py`
  - [x] `montage_controller.py`
  - [x] `preview_controller.py`
  - [x] `barplot_controller.py`
  - [x] `lineplot_controller.py`
  - [x] `scatter_controller.py`
  - [x] `selection_controller.py`
  - [x] `review_image_controller.py`
  - [x] `preview_callbacks.py`
  - [x] `scatter_callbacks.py`
  - [x] `plot_orchestrator.py`
  - [x] `export_service.py`
  - [x] `ui_helpers.py`
- [x] Remove any now-obsolete compatibility shims introduced solely for interim Tk parity.

## Phase 4 — Packaging + launcher completion

Status: deferred for now per user instruction (2026-04-19). Skip this phase temporarily and continue with later phases.

- [ ] Update `_Installation/all_well.spec`:
  - [ ] Remove tkinter and Tk backend hiddenimports
  - [ ] Add PySide6/Qt hiddenimports as specified
  - [ ] Update excludes to forbid tkinter/_tkinter, not PySide6
- [ ] Confirm `all_well_launcher.py` remains QtAgg-first before pyplot import.
- [ ] Validate bundle-time dependency resolution for Qt platform plugins.

## Phase 5 — Acceptance grep gate (must be zero)

- [x] Run acceptance sweep and require **0** matches for each:
  - [x] `^import tkinter` / `^from tkinter`
  - [x] `customtkinter`
  - [x] `FigureCanvasTkAgg`, `NavigationToolbar2Tk`, `backend_tkagg`
  - [x] `tk.StringVar`, `tk.IntVar`, `tk.BooleanVar`, `tk.DoubleVar`
  - [x] `messagebox.`, `filedialog.`
  - [x] `.after(`, `.bind("<`
  - [x] `ttk.`
- [x] If any match remains, block merge and return to relevant prior phase.

## Phase 6 — Functional verification (feature parity)

- [ ] `python all_well.py` launches and both tabs populate.
- [ ] Theme toggle (Dark/Light) repaints all panels cleanly.
- [ ] `python all_well.py --data_dir /path/to/results` loads dataset on startup.
- [ ] Plate-map click+drag select works and state survives theme switch.
- [ ] Plot tabs render (bar/line/scatter-cells/scatter-agg/review-csv/batch-export) with working toolbar pan/zoom.
- [ ] Image panel LUT min/max editor works; pixel tooltip works.
- [ ] Save/open dialogs return valid paths through `QFileDialog`.
- [ ] Invalid-path flows surface `QMessageBox`.
- [ ] Analyze end-to-end run switches to Review and loads output.

## Phase 7 — Build verification (PyInstaller/macOS bundle)

- [ ] `cd _Installation && pyinstaller all_well.spec` succeeds.
- [ ] Launch `dist/AllWell.app` and repeat core smoke checks from Phase 6.
- [ ] If bundle fails for Qt plugins, add targeted plugin collection fallback and re-test.

## Phase 8 — Final hardening + delivery

- [ ] Final `PYTHONPATH=. pytest -q tests` is green.
- [x] Re-run acceptance grep gate (all zeros) immediately before merge.
- [ ] Sanity-check docs/todos reflect final migrated state (remove stale Tk references).
- [ ] Prepare final PR summary with:
  - [ ] What was ported
  - [ ] What was deleted
  - [ ] Acceptance grep proof
  - [ ] Test/build evidence
