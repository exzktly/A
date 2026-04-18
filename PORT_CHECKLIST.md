# All-Well — PySide6 Port Checklist

Track each item as `[x]` when complete, `[-]` when deferred with a note.

## Boot & Theme
- [x] App launches, theme applies, fonts load (fallback if TTFs missing)
- [x] Three palettes defined: warm, fluoro, ivory in `all_well_qt/theme/tokens.py`
- [x] `build_qss()` produces a valid QSS stylesheet from any palette
- [x] `ThemeManager` singleton with `palette_changed` signal
- [x] Palette switcher in Tweaks panel swaps QSS live without restart
- [x] Font TTFs (Geist, Instrument Serif) placed in `all_well_qt/theme/fonts/`

## Top Bar
- [x] Top-bar brand mark painted in `_BrandMark` (2×2 wells + sparkline)
- [x] Brand name label with Instrument Serif italic style
- [x] Pill tabs (Review / Analyze / Pipelines) switch views via QStackedWidget
- [x] Crumb label (dataset path)
- [x] ⌘K command palette button (stub — opens QInputDialog)
- [x] ✦ Tweaks toggle opens floating TweaksPanel popup
- [x] Avatar badge

## Plate Map
- [x] PlateMapWidget renders 96 wells in 8×12 grid
- [x] Row A–H and Col 1–12 labels drawn as QGraphicsTextItems
- [x] Dotted corner micro-illustration drawn in drawBackground
- [x] Click toggles selection (depressed emboss)
- [x] Unselected wells show raised emboss (top highlight + bottom shadow)
- [x] Click-and-drag paints selection
- [x] Shift-click extends selection row-major rectangle
- [x] Hover scales well to 1.1× with no jitter
- [x] Group-assigned wells show group color fill
- [x] Row A–H selector buttons toggle whole row
- [x] Col 1–12 selector buttons toggle whole column
- [x] "Clear" button empties selection; count label updates
- [x] `selection_changed` signal fires on every change
- [x] `hovered_well_changed` signal fires on hover enter/leave
- [x] `set_groups()` API wires GroupSpec → per-well color fills
- [x] `apply_palette()` updates emboss colors on theme switch

## Sidebar
- [x] "Plate" panel title (Instrument Serif italic)
- [x] Row / col selector chip rows
- [x] Plate card with QGraphicsDropShadowEffect (blur 20, offset 0,4)
- [x] Selection count footer
- [x] "Sample groups" header + "+ New" button
- [x] SampleGroupRow cards: colored dot, name, well count, ··· menu
- [x] ··· menu: Rename… / Delete
- [x] "+ New" prompts for name, creates from current selection
- [x] Demo groups seeded on launch
- [x] Sample group row rename commits to PlateMapWidget group mapping

## Plot Workspace
- [x] Sub-tabs: Kinetics / Bar plots / Scatter / Stats / CSV
- [x] Workspace card with shadow + radius
- [x] Panel title updates on tab switch
- [x] ChipGroup metric chips: Mean / Median / Sum / CDF
- [x] Normalize toggle chip
- [x] Channel field
- [x] matplotlib demo kinetics chart embedded via FigureCanvasQTAgg
- [x] Chart has annotated "drug added · t=6h" dashed callout
- [x] Legend list with colored dots + group names
- [x] "Save figure…" writes PNG/SVG via matplotlib
- [x] Live chart wired to real analysis CSV data via `PlotRenderer` + `set_data_dir` / `set_live_groups`
- [x] Metric chip changes re-render chart (demo data; switches Mean/Median/Sum/CDF reduction)
- [x] Normalize toggle re-renders chart (divides by t=0 baseline)

## Preview Panel
- [x] Well tag updates on plate-map hover
- [x] Well badge label
- [x] Channel chips: GFP / DAPI / Merge
- [x] FOV, LUT min/max fields
- [x] 2×2 montage tile grid with placeholder state
- [x] Tiles load real FOV thumbnails from `ImageLoader` (wired via `ReviewView._on_data_dir_changed`)
- [x] Channel chip switches displayed channel (channel-tinted placeholder; real tiles load via ImageLoader when data dir set)

## Analyze View
- [x] Data directory input + Browse… button
- [x] Stardist controls: radius, prob_thresh fields
- [x] Cell gating controls: min/max area
- [x] smFISH threshold field
- [x] Run button fires `run_requested` signal with config dict
- [x] Stop button fires `stop_requested`
- [x] Log output panel with Clear button
- [x] `run_requested` wired to `process_microscopy_v2.py` via `_PipelineWorker(QThread)` + `services.pipeline_service`
- [x] `stop_requested` calls `proc.terminate()` via worker

## Status Bar
- [x] Pulsing dot animates (QPropertyAnimation, 2s loop)
- [x] Status text label
- [x] Dot color updates on palette switch

## Persistence (QSettings)
- [x] Window geometry saved/restored
- [x] Palette choice saved/restored
- [x] ReviewView QSplitter state saved/restored

## Misc
- [x] Qt launches by default (`python all_well.py`); pass `--tk` for legacy Tk UI
- [x] Old Tk view/tab files deleted (`well_viewer/views/`, `well_viewer/tabs/`); all bare tkinter imports guarded with try/except so domain helpers remain importable
- [-] Screenshots of each palette → `_Docs/screenshots/qt_port_*.png` — _requires desktop display server; deferred_
