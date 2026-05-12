# Porting patterns

How the All-Well v2 redesign is being assembled. Read this before porting
another screen area. The first worked example is the right-side **Properties**
panel — see `design/REWIRING.md` for its rewiring log.

---

## 1. Where files live

| Kind of code | Location | Examples |
|---|---|---|
| Design tokens + base stylesheet | `theme.py` (repo root) | `theme.Colors`, `theme.Typography`, `theme.Spacing`, `theme.Radii`, `theme.qss()` |
| Reusable custom widgets (no app knowledge) | `widgets/<snake_name>.py` | `widgets/collapsible_section.py` → `CollapsibleSection`, `widgets/toggle_switch.py` → `ToggleSwitch`, `widgets/well_plate_selector.py` → `WellPlateSelector` |
| Widget package helpers | `widgets/_support.py`, `widgets/icons.py` | `lerp_color`, `with_alpha`, `run_demo`, `make_icon` |
| Widget visual QA | `widgets/<name>.py` `__main__` block; `widgets/gallery.py` | `python widgets/toggle_switch.py`, `python widgets/gallery.py` |
| App-integration views (compose widgets + own app state) | `well_viewer/views/<name>_view.py` (existing convention) | `export_style_sidebar_view.py` (the Properties panel), `sidebar_view.py`, `centre_view.py` |
| App composition root / main window | `all_well.py` (`AllWellApp`), `well_viewer/runtime_app.py` (`WellViewerApp`) | |
| Design docs | `design/*.md` | `DESIGN_TOKENS.md`, `PORT_PLAN.md`, `PATTERNS.md`, `REWIRING.md` |

Naming: widget modules and files are `snake_case`; widget classes are
`PascalCase` and match the file name (`toggle_switch.py` → `ToggleSwitch`).
View modules keep the existing `*_view.py` suffix. One public widget class per
`widgets/` module (helpers may live alongside, prefixed `_`).

---

## 2. Composing widgets into a screen area

A "screen area" (a panel, a rail, a tab body) is an `app-integration view`: a
`QWidget`/`QFrame` subclass — or, for incremental ports, an existing view class
whose `_build_ui()` is rewritten — that:

1. **owns the app state** (or a reference to it) the area edits;
2. **builds a layout from custom widgets + theme-styled stock widgets**;
3. **connects widget signals to the state**, then leaves the state logic alone.

Patterns used in the Properties panel port:

- **Section stack.** A `QScrollArea` whose widget is a `QVBoxLayout` of
  `CollapsibleSection`s, one per mockup section, plus a trailing `addStretch(1)`.
  A fixed footer (action buttons) sits below the scroll area, outside it.
- **Rows inside a section.** Each `CollapsibleSection` gets one `QGridLayout`
  (`addLayout`) with a label column (0) and a control column (1, stretched). A
  tiny local `add_row(section, label, widget, key=None)` helper appends a row and
  — if `key` is given — registers the widget with the area's binding layer. A
  sibling `add_full(section, widget)` spans both columns (used for the draw-order
  sub-panels).
- **Compound controls** (two toggles side by side, a `min … max` pair) are
  wrapped in a throwaway `QWidget` + `QHBoxLayout` via a local `hrow(*widgets)`
  helper, then dropped into the control column.
- **Custom widgets are drop-ins where possible.** `ToggleSwitch` subclasses
  `QCheckBox`, so existing code that did `isinstance(w, QCheckBox)` /
  `w.isChecked()` / `w.toggled` keeps working unchanged — only the constructor
  call sites change (`QCheckBox("X", parent)` → `ToggleSwitch("X", parent)`;
  beware `QCheckBox(parent)` positional-parent → must become
  `ToggleSwitch(parent=parent)` since `ToggleSwitch`'s first positional arg is
  `text`).
- **Don't fight the binding layer.** If a screen area already has a generic
  "register a widget → state key" mechanism (here `_bind_getter_setter`), reuse
  it. Only introduce a new widget type into it when you're prepared to extend
  that mechanism (and document it in `REWIRING.md`).

---

## 3. QSS scoping — global vs object-name vs per-widget

Three tiers, in order of preference:

1. **Global (`theme.qss()`).** The application stylesheet, set once via
   `QApplication.setStyleSheet(theme.qss())` (in `all_well.main()`, and re-applied
   by `AllWellApp._apply_stylesheet` / `WellViewerApp._apply_theme`). It styles
   bare widget *classes* (`QWidget`, `QPushButton`, `QLineEdit`, `QComboBox`,
   `QCheckBox`, `QScrollBar`, `QTabBar`, `QMenu`, …) and a small set of
   well-known **object names** (`#Primary`, `#Danger`, `#Ghost` on buttons;
   `#Heading`, `#Caption`, `#Secondary`, `#Mono` on labels; `#Panel`, `#Rail`,
   `#Separator` on frames). Prefer this. To opt a widget into a variant, just
   `widget.setObjectName("Primary")` etc. — no extra stylesheet.
2. **Object-name / dynamic-property selectors** for app-specific structure that
   the global sheet shouldn't bake in: give the area a unique `objectName`
   (`PropertyPanel`, `PlotCardToolbar`, …) and add a *small* rule for just that
   selector. The Properties panel sets `objectName("PropertyPanel")` +
   `WA_StyledBackground` and a one-line widget stylesheet
   `#PropertyPanel { background-color: <rail>; }`.
3. **Per-widget stylesheets** (`widget.setStyleSheet(...)`) only for *self-contained
   custom widgets* in `widgets/` whose look isn't expressible via the global
   sheet (`CollapsibleSection`, `SegmentedControl`, `Stepper`, `IconButton`, …).
   These build their stylesheet from `theme.Colors`/`Typography`/`Radii` tokens
   (never hardcoded hex) and scope every rule to their own `objectName` so they
   don't leak into children. They are self-contained: dropping one into any
   layout "just works" because the app already runs `theme.qss()` globally and
   the widget carries its own extra rules.

Rules of thumb:
- A per-widget `setStyleSheet` on a *container* cascades to descendants' QSS
  resolution — keep such rules limited to a single `#ObjectName { … }` selector
  so they can't accidentally restyle children.
- Plain `QWidget`/`QFrame` need `setAttribute(Qt.WA_StyledBackground, True)` for
  a QSS `background-color` to actually paint.
- macOS/Windows native styles fall back to native rendering on under-specified
  QSS sub-controls — that's why `widgets.styled_slider.StyledSlider` paints its
  groove/handle itself instead of relying on `QSlider::handle` QSS.
- Never reach back into the legacy `ui/theme` system (`build_stylesheet`,
  `get_color`, `ui/theme/*.qss`, `setProperty("variant", …)`,
  `setProperty("role", "section")`). It is no longer the app stylesheet (see
  `design/PHASE_4_DIAGNOSIS.md`); those selectors are dead. `ui/theme` survives
  only as a bag of frozen colour constants used by not-yet-ported code.

---

## 4. Reconnecting signals during a port

Goal: the ported area drives **exactly the same underlying state** as before.

1. **Trace first.** Find every `.connect(...)` and every read/write of app/pref
   state in the area being ported. For `ExportStyleSidebar` that was
   `_bind_getter_setter` (which `.connect`s a change signal per widget type),
   the manual `axis_target` getter/setter, the profile/axis-target handlers, and
   the button `clicked` connections.
2. **Keep the state side intact.** Don't touch the slot methods, the prefs dict,
   the apply/persist functions, or the redraw entry points. Re-skinning is a
   *layout* change, not a logic change.
3. **Recreate the same connections on the new widgets.** Reuse the existing
   registration mechanism if there is one; recreate the explicit
   `widget.signal.connect(self._handler)` lines if not. Where a widget type
   changed but stays signal-compatible (`QCheckBox` → `ToggleSwitch`), nothing
   on the connection side changes.
4. **If a connection can't be recreated straightforwardly** — a different signal
   shape, a control that no longer exists, a behaviour that doesn't fit the new
   layout — **do not silently drop it**. Record it (what it did, why it's hard,
   the proposed resolution) in `design/REWIRING.md` before moving on.
5. **Write the rewiring log either way.** Even a clean port gets a
   `REWIRING.md` entry: the property→state table, plus what you deliberately
   left unchanged and why. It's the audit trail for "did we lose anything?".
6. **Verify at runtime.** Type-checking / `py_compile` proves syntax, not
   feature parity. Open the area, exercise every control, confirm the same
   state changes / redraws happen. (When the porting environment can't run the
   GUI, say so explicitly in `REWIRING.md` and flag it for a manual pass.)

---

## 5. Checklist for the next screen-area port

- [ ] Identify the area's owning class and its app-state surface.
- [ ] List every signal/slot + state read/write (the rewiring trace).
- [ ] Rebuild the layout from `widgets/` + theme-styled stock widgets, grouped
      per the mockup; reuse `CollapsibleSection` / `SegmentedControl` /
      `ToggleSwitch` / `IconButton` / `Stepper` / `WellPlateSelector` etc.
- [ ] Reconnect every signal to the same state; extend any binding mechanism
      only if you must, and note it.
- [ ] Style via `theme.qss()` + object names first; per-widget QSS only for
      self-contained custom widgets, always from tokens.
- [ ] Add/append `design/REWIRING.md` (property→state table + "not changed" list
      + verification status).
- [ ] Run it; exercise every control; fix; screenshot.
- [ ] Commit the area as its own commit.
