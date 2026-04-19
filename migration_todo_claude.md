# Tkinter → PySide6 Migration Status

Branch: `claude/migrate-pyside6-FvCyu`
Plan: `/root/.claude/plans/switch-from-tkinter-to-jolly-bachman.md`

## Done

### Foundation (commit `e564e8b`)
- [x] Created branch `claude/migrate-pyside6-FvCyu`
- [x] Rewrote `ui/theme/styles.py` as a QSS producer (~150 LoC, was 598 LoC)
- [x] Authored `ui/theme/dark.qss` and `ui/theme/light.qss` with `${TOKEN}` substitution
- [x] Ported `all_well.py` to `QMainWindow` + `QTabWidget` shell with theme `QComboBox`
- [x] Ported `all_well_launcher.py` (matplotlib `TkAgg` → `QtAgg`)
- [x] Created `well_viewer/views/well_button.py` (`WellButton(QPushButton)`)
- [x] Ported `well_viewer/ui_helpers.py` to Qt (button factories, scroll area, name dialog)
- [x] Made `well_viewer/__init__.py` lazy-load `WellViewerApp` so service tests don't pull GUI
- [x] Deleted obsolete files:
  - `well_viewer/views/widgets.py` (`_Tooltip` shim)
  - `well_viewer/views/well_label_widget.py` (Aqua workaround)
  - `well_viewer/app.py` (tk facade)
  - `scripts/ui_smoke_review_image_preserve_view.py`

### Views & tabs (commit `f9717ab` + uncommitted)
- [x] `well_viewer/views/centre_view.py` — `CustomNotebook` → `QTabWidget` (95 LoC, was 311)
- [x] `well_viewer/views/image_panel_view.py` — `tk.Canvas` → `QLabel` + `QPixmap`
- [x] `well_viewer/views/sidebar_view.py`
- [x] `well_viewer/views/grouping_view.py`
- [x] `well_viewer/views/bar_group_panel_view.py`
- [x] `well_viewer/views/replicate_panel_view.py`
- [x] `well_viewer/views/preview_panel_view.py`
- [x] `well_viewer/views/preview_view.py`
- [x] `well_viewer/views/stats_view.py`
- [x] `well_viewer/views/status_view.py`
- [x] `well_viewer/views/label_editor_view.py`
- [x] `well_viewer/tabs/__init__.py`
- [x] `well_viewer/tabs/bar_plots_tab_view.py`
- [x] `well_viewer/tabs/line_graphs_tab_view.py`
- [x] `well_viewer/tabs/scatter_cells_tab_view.py`
- [x] `well_viewer/tabs/scatter_agg_tab_view.py` — multi-select dropdown via `QMenu` + `QCheckBox` + `BoolHolder` shim
- [x] `well_viewer/tabs/batch_export_tab_view.py`
- [x] `well_viewer/tabs/review_csv_tab_view.py` — `ttk.Treeview` → `QTableWidget`
- [x] `well_viewer/cell_gating_tab.py` (537 LoC) — uncommitted
- [x] `well_viewer/smfish_tab.py` (639 LoC) — uncommitted; threaded mpl draws marshalled via `_WorkerBridge` `Signal`
- [x] `well_viewer/figure_export_editor.py` (483 LoC) — uncommitted; export-style sidebar uses `QSpinBox`/`QDoubleSpinBox`/`QCheckBox`/`QComboBox` with `_getters`/`_setters` registry replacing `tk.Variable.trace_add`

## To do

### Major modules
- [ ] `analyze_tab.py` (1399 LoC) — pipeline form + log panel; uses `tk.PanedWindow`, `tk.Text` log widget, `ttk.Progressbar`, `queue.Queue`, threading + `.after()` polling
- [ ] `well_viewer/runtime_app.py` (6941 LoC) — the monolith. Subclass `QWidget` instead of `tk.Frame`. Mechanical swap; keep all method names so cross-module `getattr`s and `plot_orchestrator` bindings still resolve. Expect ~20-30% line reduction from removing `tk.Variable` shims and recursive theme walks.
- [ ] `well_viewer/batch_export_dialog.py` (2030 LoC) — mechanical swap; complex form with multiple panel classes (`BatchExportPanel`, `BarBatchExportPanel`, `ScatterBatchExportPanel`)

### Controllers + callbacks + services (~2500 LoC)
For each: drop `tk.Event` type hints; swap `messagebox`→`QMessageBox`, `filedialog`→`QFileDialog`, `.after()`→`QTimer.singleShot`. Most are thin orchestration layers and should port quickly.

- [ ] `well_viewer/load_controller.py` (114 LoC)
- [ ] `well_viewer/stats_controller.py` (147 LoC)
- [ ] `well_viewer/grouping_controller.py` (168 LoC)
- [ ] `well_viewer/montage_controller.py` (169 LoC)
- [ ] `well_viewer/preview_controller.py` (251 LoC)
- [ ] `well_viewer/barplot_controller.py` (251 LoC)
- [ ] `well_viewer/lineplot_controller.py` (163 LoC)
- [ ] `well_viewer/scatter_controller.py` (556 LoC)
- [ ] `well_viewer/selection_controller.py` (222 LoC)
- [ ] `well_viewer/review_image_controller.py` (114 LoC)
- [ ] `well_viewer/preview_callbacks.py` (319 LoC)
- [ ] `well_viewer/scatter_callbacks.py` (720 LoC)
- [ ] `well_viewer/plot_orchestrator.py` (137 LoC)
- [ ] `well_viewer/export_service.py` (403 LoC)

### Packaging
- [ ] `_Installation/all_well.spec` — drop `tkinter`, `tkinter.ttk`, `tkinter.filedialog`, `tkinter.messagebox`, `matplotlib.backends.backend_tkagg`, `matplotlib.backends._backend_tk`, `PIL.ImageTk` from `hiddenimports`. Add `PySide6`, `PySide6.QtCore`, `PySide6.QtGui`, `PySide6.QtWidgets`, `shiboken6`, `matplotlib.backends.backend_qtagg`, `matplotlib.backends.backend_qt`. Remove `PySide6/PyQt5/PyQt6/PySide2` from `excludes`; add `tkinter`, `_tkinter`.
- [ ] `requirements.txt` — add `PySide6`

### Acceptance gate (must all be 0 hits)
- [ ] `^import tkinter` / `^from tkinter`
- [ ] `customtkinter`
- [ ] `FigureCanvasTkAgg`, `NavigationToolbar2Tk`, `backend_tkagg`
- [ ] `tk.StringVar`, `tk.IntVar`, `tk.BooleanVar`, `tk.DoubleVar`
- [ ] `messagebox.`, `filedialog.`
- [ ] `.after(`, `.bind("<`
- [ ] `ttk.`

### Verification
- [ ] `pytest tests/` — must stay green (services have no GUI imports)
- [ ] `python all_well.py` launches; both tabs populate; dark↔light toggle repaints
- [ ] Plate-map drag-select works; selection persists across theme switch
- [ ] Each plot sub-tab renders matplotlib figure; toolbar pan/zoom works
- [ ] Image panel LUT editor + pixel-value tooltip
- [ ] `QFileDialog` save flows return valid paths
- [ ] `QMessageBox` shown on invalid-path error
- [ ] Analyze pipeline end-to-end → switches to Review on completion
- [ ] `cd _Installation && pyinstaller all_well.spec` builds and bundle launches

### Final
- [ ] Commit cell_gating + smfish + figure_export_editor + remaining ports
- [ ] Push to `claude/migrate-pyside6-FvCyu`

## Notes & risks

- **Threaded mpl draws** — every `threading.Thread` that touches a `Figure` must marshal back to the GUI thread. `smfish_tab.py` uses a `_WorkerBridge(QObject)` with `Signal` slots; `analyze_tab.py` and `runtime_app.py` need the same treatment.
- **Cross-tab state** — `_cell_threshold` and theme were `tk.Variable`-shared; need to become plain attrs on `AllWellApp` plus a `Signal` both tabs connect to.
- **`StringHolder` / `BoolHolder` shims** — `cell_gating_tab.py` and `tabs/scatter_agg_tab_view.py` define small shims with `.get()`/`.set()` so the not-yet-ported `runtime_app.py` and `export_service.py` keep working until those files land.
- **Bundle size** — PySide6 + Qt adds ~150-200 MB. May need `--exclude-module PySide6.QtWebEngine*`, `PySide6.Qt3D*` etc. once the spec is built.
- **High-DPI / Retina** — call `QApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)` before `QApplication()` if scaling is wrong; verify image-panel `QPixmap.devicePixelRatio` on Retina.
