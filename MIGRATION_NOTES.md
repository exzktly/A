# All-Well PySide6 Migration Notes

## Stack

```
PySide6 >= 6.7       Qt for Python (LGPL)
matplotlib >= 3.8    QtAgg backend via FigureCanvasQTAgg
numpy                chart demo data; tile rendering
```

## Font availability

`Geist` and `Instrument Serif` TTFs are **not bundled** in this repository.
At boot, `all_well_qt/theme/fonts.py` attempts to load them from
`all_well_qt/theme/fonts/`.  If the files are absent, a `WARNING` is logged
and the app falls back to:

| Intended font          | System fallback                         |
|------------------------|-----------------------------------------|
| Geist (sans)           | SF Pro Text / Segoe UI / system-ui      |
| Geist Mono             | Menlo / Consolas / SF Mono              |
| Instrument Serif italic| Georgia Italic                          |

Panel titles (`.panelTitle` QSS) will render in Georgia Italic rather than
Instrument Serif — visually close enough until TTFs are provided.

**To enable custom fonts:** place the following files in
`all_well_qt/theme/fonts/`:
- `Geist-Regular.ttf`, `Geist-Medium.ttf`, `Geist-SemiBold.ttf`, `Geist-Bold.ttf`
- `GeistMono-Regular.ttf`
- `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf`

Both families are available free from their respective GitHub repositories.

## Behavioral regressions vs Tk

| Area | Tk behavior | Qt status | Notes |
|------|-------------|-----------|-------|
| Well plate icon | `tk.PhotoImage` procedurally drawn at 64×64 | `_BrandMark` paints a 28×28 version in TopBar | Larger taskbar icon pending; add to `app.py` via `QApplication.setWindowIcon` |
| Scrollable canvas | `make_scrollable_canvas()` in runtime_app | `QScrollArea` used for SampleGroupList and Analyze controls | No regression |
| `ask_name_dialog()` | Custom modal Tk dialog | `QInputDialog.getText` | Functionally equivalent |
| `_GUILogHandler` logging widget | Text widget that streams log records | `QTextEdit.append()` in AnalyzeView; Python `logging.Handler` subclass to be wired | Handler not yet wired — deferred |
| Theme switching (Dark/Light) | `ui/theme/styles.py` `set_theme()` hot-swaps TTK styles | `ThemeManager.set_palette()` hot-swaps QSS | Three palettes replace two themes |
| Tk event loop | `tk.Tk.mainloop()` | `QApplication.exec()` | Not a regression |

## QSS hacks / workarounds

| CSS feature | QSS limitation | Workaround |
|-------------|---------------|------------|
| `box-shadow` | Not supported | `QGraphicsDropShadowEffect` on plate card and workspace card |
| `transform: scale(1.1)` on well hover | Not supported in QSS | `WellItem.setScale(1.1)` in `hoverEnterEvent` |
| `::after` pseudo-element for emboss arcs | Not supported | Overridden `WellItem.paint()` draws arcs directly |
| CSS `color-mix()` for group dot ring | Not supported | Inline `QColor.setAlpha()` in `_soften()` helper |
| Pulse dot CSS animation | Not supported | `QPropertyAnimation` on custom `opacity_prop` in `_PulseDot` |

## Unportable items

- **Tk `PhotoImage` for microscopy thumbnails** — replaced by `QLabel` +
  `QPixmap.fromImage(QImage(...))` in `MontageTile.set_image_array()`.
- **`NavigationToolbar2Tk`** — not used; save action provided by "Save figure…"
  button calling `figure.savefig()` directly. A `NavigationToolbar2QT` could
  be added if interactive pan/zoom is required.
- **StarDist / TensorFlow GPU stack** — not touched; runs in subprocess via
  `process_microscopy_v2.py`.  The `run_requested` signal in `AnalyzeView`
  carries the config dict; the adapter layer (`adapters/plot_renderer.py`) will
  spawn the subprocess.

## What is NOT yet wired (deferred for migration step 7–12)

1. `PlotWorkspace` chart reads demo data — not yet wired to real analysis CSVs.
2. `PreviewPanel` tiles show placeholders — not yet wired to `ImageLoader`.
3. `AnalyzeView` Run/Stop buttons fire signals but no subprocess is launched.
4. `_GUILogHandler` equivalent for streaming pipeline logs to `AnalyzeView._log`.
5. Old Tk code (`well_viewer/views/`, `well_viewer/ui_helpers.py`) is preserved
   per migration step 13 — do not delete until full parity confirmed.

## How to run the Qt UI

```bash
python all_well.py --qt
# or directly:
python -m all_well_qt.app
```
