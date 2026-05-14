# Phase 4 Diagnosis — `theme.qss()` produces no visible chrome change

**Status:** root cause identified. No code changed yet.

## TL;DR

`app.setStyleSheet(theme.qss())` *is* called correctly in the entry point, but it
is immediately overwritten — twice — by the **legacy `ui/theme` stylesheet** while
the main window is being constructed. The new stylesheet never survives to paint.
There is nothing wrong with `theme.qss()` itself.

---

## 1. Where `setStyleSheet` is called in the entry point

`all_well.py` → `main()` (lines ~299–302):

```python
import theme

app = QApplication.instance() or QApplication(sys.argv)
app.setStyleSheet(theme.qss())          # ← line 302
win = AllWellApp(data_path=args.data_dir)
win.show()
sys.exit(app.exec())
```

- ✅ Called on the **`QApplication` instance**, not on a widget.
- ✅ Called **before** the main window is instantiated and shown.
- ✅ `theme.qss()` has parentheses — the string is invoked, not passed as a function reference.

So the entry-point wiring is correct. The problem is *after* this line.

---

## 2. Every other `setStyleSheet` / `setStyle` call in the codebase

`grep -rn "setStyleSheet\|setStyle(" --include='*.py'` (excluding `.git`):

### App-level (these REPLACE the global stylesheet — the actual bug)

| File:line | Call | Applied to | Notes |
|---|---|---|---|
| `well_viewer/runtime_app.py:2940` | `app.setStyleSheet(build_stylesheet(self._theme_name))` | **`QApplication`** | Inside `WellViewerApp._apply_theme()`. **Called from `WellViewerApp.__init__` at line 874.** Since `AllWellApp._build_ui()` constructs `WellViewerApp` *before* anything else, this runs during window construction and clobbers `theme.qss()`. **Override #1.** |
| `all_well.py:63` | `app.setStyleSheet(build_stylesheet(theme_name))` | **`QApplication`** | Inside `AllWellApp._apply_stylesheet()`. **Called from `AllWellApp.__init__` as `self._apply_stylesheet("Dark")`**, after `_build_ui()`. Clobbers whatever is left. **Override #2.** Also re-invoked on every theme-combo change. |
| `all_well.py:302` | `app.setStyleSheet(theme.qss())` | **`QApplication`** | The new Phase-4 call. Runs first, then gets overwritten by the two above. |

`build_stylesheet(...)` lives in `ui/theme/styles.py` and loads `ui/theme/<theme>.qss`
(~400-line token-substituted sheets, one per legacy theme: dark/light/amber/beige).

### Widget-scoped (harmless — they only style one widget, do not replace the global sheet)

| File:line | Applied to | What it sets |
|---|---|---|
| `well_viewer/runtime_app.py:2062` | a transient frameless `QWidget` (visibility rubber-band overlay) | `background-color` |
| `well_viewer/runtime_app.py:2797` | `th_lbl` (`QLabel`, threshold overlay text) | bg/color/padding |
| `well_viewer/runtime_app.py:3249` | `btn` (`QPushButton`, small pill button) | full `QPushButton{…}` block |
| `well_viewer/runtime_app.py:4235` | `btn` (`QPushButton`, review-image color swatch) | `background-color: rgb(...)`, `border: 1px solid #444` |
| `well_viewer/stats_controller.py:408` | `dot` (`QLabel`, status dot) | `color` |
| `well_viewer/views/image_table_grid_view.py:63` | `row_box` (`QGroupBox#ImageTableRowOptions`) | tinted bg/border/radius (uses `rgba(99,102,241,…)`) |
| `well_viewer/views/image_table_grid_view.py:78,88,98` | `well_lbl`/`chan_lbl`/`col_lbl` (`QLabel`) | `font-size: 10px` |
| `well_viewer/views/bar_group_panel_view.py:234` | `dot` (`QLabel`) | `color: #666` or trace color |
| `well_viewer/batch_export/well_grid_button.py:29` | `self` (`_WellGridButton(QPushButton)`) | `QPushButton{ background/color/border/padding }` |
| `well_viewer/batch_export/base_panel.py:534` | `card` (`QFrame`, selected bar-group card) | `border`, `background` |
| `well_viewer/batch_export/base_panel.py:542,567,580` | `dot`/`name_tag`/`s_lbl` (`QLabel`) | `color` |
| `well_viewer/batch_export/base_panel.py:571` | `chip` (`QLabel`) | `background`, `color`, `padding` |
| `well_viewer/batch_export/base_panel.py:859,864` | `self._prog_lbl` (`QLabel`) | `color` (danger / success) |
| `well_viewer/tabs/image_table_tab_view.py:211` | `lut_outer` (`QFrame#ImageTableLutRow`) | tinted bg/border/radius (uses `rgba(245,158,11,…)`) |

> The widget-scoped calls are not the cause of "no visible chrome change." They are
> worth tracking later as Phase-N cleanup (they hardcode hex/rgba and bypass the token
> system), but they do not block Phase 4.

### `QApplication.setStyle(...)`

- **None found.** The app does not force `"Fusion"` or any other `QStyle`. It uses
  the platform default style. (See §4.)

---

## 3. Inspecting the QSS string passed at runtime

`theme.qss()` was rendered and inspected (equivalent of adding a temporary
`print(theme.qss())` before the call):

- **Length:** ~9.4 KB, ~370 lines. Non-empty. ✅
- **Braces:** balanced — the f-string doubles every literal CSS `{ }` as `{{ }}`; the
  module compiles and `theme.qss()` executes without error. ✅
- **Hex colors:** every color in the output is a valid `#RRGGBB` (interpolated from
  `theme.Colors.*`); there are **no** color values missing a `#`, and **no hardcoded
  hex literals in the f-string source** (all via `{c.…}`). ✅
- **Unsupported properties:** scanned — **no** `box-shadow`, **no** `transform`, **no**
  `transition`, **no** CSS `var(...)`. Only Qt-supported QSS properties are used
  (`background-color`, `color`, `border`, `border-radius`, `padding`, `margin`,
  `font-*`, `selection-*`, `subcontrol-*`, `min/max-width/height`, `::item`, `::tab`,
  `::handle`, `::indicator`, `::drop-down`, `::up/down-button`, `::chunk`, etc.). ✅

Conclusion: the stylesheet content is valid and *would* take effect — if it weren't
being replaced.

---

## 4. Is the app using a Qt style that ignores stylesheets?

- No `QApplication.setStyle(...)` call exists, so the style is the platform default
  (`"Fusion"` on Linux CI/headless; `"macos"` on macOS; `"windowsvista"` on Windows).
- App-level stylesheets are honored by all of these. The known macOS/Windows-native
  gotcha is *under-specified* QSS (sub-controls falling through to native rendering when
  the base selector lacks `background-color`/`border`) — `theme.qss()` already gives
  complete base selectors, so that is not the issue here.
- Even if a native style partially ignored a *widget* QSS rule, that would not explain
  "no chrome change at all" — an app-level sheet that survived would still recolor
  `QWidget`, `QPushButton`, `QLabel`, menus, etc. The total absence of effect points to
  the sheet being **replaced**, not **ignored**.

---

## 5. Is `qss()` actually called (vs. passed as a reference)?

Yes. `all_well.py:302` reads `app.setStyleSheet(theme.qss())` — with parentheses. If it
had been `app.setStyleSheet(theme.qss)` Qt would have raised a `TypeError`, which is not
happening. Verified independently: `import theme; theme.qss()` returns the rendered
string.

---

## Root cause (summary)

Startup order:

1. `main()`: `app.setStyleSheet(theme.qss())` — new sheet applied.
2. `AllWellApp.__init__()`:
   1. `_build_ui()` constructs `WellViewerApp(...)`; its `__init__` (runtime_app.py:874)
      calls `self._apply_theme()` → `app.setStyleSheet(build_stylesheet("Dark"))`
      — **legacy sheet replaces the new one (override #1)**.
   2. `_apply_stylesheet("Dark")` → `app.setStyleSheet(build_stylesheet("Dark"))`
      — **legacy sheet applied again (override #2)**.
3. `win.show()` — what paints is the legacy `ui/theme/dark.qss`, not `theme.qss()`.

`QApplication.setStyleSheet` is **not additive** — each call wholly replaces the
previous app-level sheet. So the last writer wins, and the last writer is the legacy
theme system.

---

## Recommended fix order (do not implement yet — for review)

1. **Decide the ownership model.** Phase 4's intent is that `theme.qss()` is the global
   chrome. Either:
   - **(A) Replace** — make the legacy `ui/theme` `build_stylesheet`/per-theme `.qss`
     path defer to `theme.qss()` (simplest: have `AllWellApp._apply_stylesheet` and
     `WellViewerApp._apply_theme` call `theme.qss()` instead of `build_stylesheet(...)`),
     and drop the four legacy `.qss` files, or
   - **(B) Compose** — keep `theme.qss()` as the base and append the legacy/per-widget
     overrides to it (one combined string per `setStyleSheet` call), retiring the legacy
     pieces incrementally.

   Recommend **(A)** — Phase 4 already committed to a single token source (`theme.py`);
   maintaining two parallel theming systems is the thing the redesign is trying to kill.
   The multi-theme (Light/Amber/Beige) feature is a separate decision (see open question
   #8 from the earlier design review) — if multi-theme must stay, parametrize
   `theme.Colors` instead of resurrecting `ui/theme`.

2. **Stop the constructor-time overrides.** Until step 1 lands, at minimum:
   - In `AllWellApp.__init__`, drop the `self._apply_stylesheet("Dark")` call (or make it
     a no-op / route it through `theme.qss()`).
   - In `WellViewerApp.__init__` (runtime_app.py:874), guard `self._apply_theme()` so it
     does **not** call `app.setStyleSheet(...)` when running embedded under `AllWellApp`
     (e.g. only when `parent is None` / standalone), or route it through `theme.qss()`.

3. **Re-test.** Run the app; confirm the new dark chrome (`#0B0F17` canvas, accent
   `#6B8AFD` primary buttons, hairline borders, Inter type) is visible. Add a temporary
   `print(repr(QApplication.instance().styleSheet()[:200]))` after `win.show()` to verify
   the live sheet is `theme.qss()` and not `dark.qss`.

4. **Migrate the widget-scoped `setStyleSheet` calls** (the table in §2) to read from
   `theme.Colors` instead of hardcoded hex/rgba and `ui.theme.get_color(...)`. Lowest
   priority; cosmetic consistency, not a blocker.

5. **Theme-switch path.** Re-point `AllWellApp._on_theme_change` /
   `WellViewerApp._on_theme_change` at whatever step 1 decides (single theme → remove the
   combo; parametrized `theme.py` → rebuild `theme.qss()` from the chosen palette).
