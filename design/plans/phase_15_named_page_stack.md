# Phase 15 — Retire the legacy `app._notebook` QTabWidget

**Status:** 🚧 IN PROGRESS — commit 1 landed (outer `_notebook` swapped to `NamedPageStack`).
**Target branch:** `claude/analyze-repo-structure-2uEVQ`
**Owner doc:** referenced from `design/PROJECT_STATUS.md` phase table.

## Context

`design/PROJECT_STATUS.md` documents two pieces of v1 plumbing that survive
inside the v2 reconciliation:

1. **`app._notebook`** — the outer centre `QTabWidget` that hosts the 8
   section pages (Plotting / smFISH / Statistics / Image Table /
   Segmentation / Review CSV / Sample Definitions / Batch Export). Its tab
   bar is already hidden; the v2 `RailNav` on the left sidebar drives
   `setCurrentIndex(...)`.
2. **`app._plotting_notebook`** — the nested `QTabWidget` inside the
   Plotting page that hosts the 5 plot-type sub-pages. Same model: tab bar
   hidden, ctxbar `SegmentedControl` drives `currentIndex`.

Both `QTabWidget`s are page-host-only today — the rest of the v1 chrome
(`_GroupedTabBar` custom paint, wheel-to-scroll on the tab bar, the
`select_by_text` closure attached to the instance) is dead weight. This
phase replaces them with a small `NamedPageStack` (a `QStackedWidget`
subclass) that retains the call-site API every consumer already uses
(`tabText(i)`, `setCurrentIndex(i)`, `currentIndex()`, `count()`,
`currentChanged(int)`), plus a few v2 methods (`addPage`,
`setCurrentByName`, `currentName`, `pageNames`, `nameOf`).

**Outcome:** zero `QTabWidget` instances in
`well_viewer/views/centre_view.py`; `_GroupedTabBar` and `select_by_text`
deleted. The downstream call sites in `runtime_app.py`,
`selection_controller.py`, `sidebar_view.py`, `plot_orchestrator.py`, and
`review_image_controller.py` migrate to the v2 name-based API.

## Replacement API — `NamedPageStack`

A small `QStackedWidget` subclass added to
`well_viewer/views/centre_view.py` (single consumer pair — no need for a
separate module yet).

```python
class NamedPageStack(QStackedWidget):
    currentNameChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._names: list[str] = []
        self._by_name: dict[str, QWidget] = {}
        super().currentChanged.connect(self._emit_name)

    # ── v2 API ──────────────────────────────────────────────────
    def addPage(self, name: str, widget: QWidget) -> int: ...
    def setCurrentByName(self, name: str) -> bool: ...
    def currentName(self) -> str: ...
    def pageNames(self) -> list[str]: ...
    def nameOf(self, w: QWidget) -> str | None: ...

    # ── back-compat shims (QStackedWidget already provides
    #     currentIndex / setCurrentIndex / count / currentChanged) ─
    def tabText(self, i: int) -> str: ...
    def select_by_text(self, name: str) -> bool:
        return self.setCurrentByName(name)
```

No separate adapter wrapper is needed — `NamedPageStack` *is* the shim.
`app._notebook` and `app._plotting_notebook` keep their attribute names
and point at `NamedPageStack` instances. Every existing call site using
`tabText` / `setCurrentIndex` / `currentChanged` continues to work
unchanged on day one, so the migration can be staged across commits
without breaking the app between them.

## Five-commit migration plan

Each commit ends with `python -m py_compile` clean and the app launching
successfully.

### Commit 1 — Introduce `NamedPageStack`, swap outer `_notebook`

**File:** `well_viewer/views/centre_view.py`.

- Add `NamedPageStack` near the top of the file.
- In `build_centre` (lines 161–185), replace the `QTabWidget(parent)` +
  `_GroupedTabBar(parent)` construction with
  `app._notebook = NamedPageStack(parent)`. Drop `setTabBar`,
  `setUsesScrollButtons`, `setExpanding`, `setElideMode`,
  `tabBar().setVisible(False)`, `setDocumentMode` — none apply to
  `QStackedWidget` and none are needed.
- Delete the `_select_by_text` closure (lines 186–191); `NamedPageStack`
  provides the method natively.
- Replace each `app._notebook.addTab(frame, title)` (line 594 +
  group-starts in `tab_groups`) with
  `app._notebook.addPage(title, frame)`.
- Keep `setCurrentIndex(0)` (line 622) verbatim — `QStackedWidget`
  supports it.
- Leave the `_GroupedTabBar` class in place for now (unused) — deletion
  is commit 5.

**Verify:** app launches; RailNav clicks switch sections; sidebar
visibility updates per the existing `_on_tab_change` dispatcher;
`_on_notebook_current_changed(idx)` still fires with the correct int
payload (`QStackedWidget.currentChanged(int)` matches the signature).

### Commit 2 — Swap nested `_plotting_notebook`

**File:** `well_viewer/views/centre_view.py`.

- Inside `_build_plotting` (lines 403–411), swap the inner
  `QTabWidget(plotting_container)` for
  `NamedPageStack(plotting_container)`. Drop the
  `setObjectName("PlottingSubTabs")` / `tabBar().setVisible(False)` /
  `setDocumentMode(True)` lines — the stack has no tab bar.
- Replace the 5× `addTab(tab_frames[title], title)` with
  `addPage(title, tab_frames[title])`.
- The sub-tab-change handler at 417–440 keeps reading
  `tabText(currentIndex())` (serviced by the shim method) and calls
  `setCurrentIndex` from the ctxbar `SegmentedControl` — both work
  unchanged.

**Verify:** ctxbar segment clicks still drive plot pages; channel chip
refresh fires on switch; no `AttributeError` in the deferred builders for
the four non-active plot types.

### Commit 3 — Migrate read-side call sites to `currentName()` / `pageNames()`

**Files:**
- `well_viewer/runtime_app.py` (lines 1167, 1181–1199, 1211–1222,
  4800–4822).
- `well_viewer/selection_controller.py` (lines 19–24, 65–70).
- `well_viewer/views/sidebar_view.py` (lines 20–26).
- `well_viewer/plot_orchestrator.py` (lines 44–47).
- `well_viewer/review_image_controller.py` (the `_select_tab_by_text`
  helper).

Mechanical replacements:

- `nb.tabText(nb.currentIndex())` → `nb.currentName()`.
- `for i in range(nb.count()): t = nb.tabText(i); …` →
  `for t in nb.pageNames(): …`.
- `_current_centre_tab()` keeps its outer→nested drill-down logic; just
  swap the accessors.

### Commit 4 — Migrate write-side call sites to `setCurrentByName()`

**Files:**
- `well_viewer/runtime_app.py` (lines 1201–1209 `_on_section_nav_changed`;
  4751–4752, 5998–5999, 6008–6009, 6018–6019 — the four
  `_notebook.select_by_text("Batch Export")` call sites).

Replacements:

- `nb.select_by_text("Batch Export")` →
  `nb.setCurrentByName("Batch Export")`.
- `_on_section_nav_changed`: drop the
  `for i in range(nb.count()): if nb.tabText(i) == key: nb.setCurrentIndex(i)`
  loop in favour of a single `nb.setCurrentByName(key)`.

### Commit 5 — Dead-code cleanup

**File:** `well_viewer/views/centre_view.py`.

- Delete the `_GroupedTabBar` class entirely (custom paint,
  wheel-to-scroll, group-starts logic).
- Delete the `select_by_text` back-compat method on `NamedPageStack` *if*
  commit 4 migrated every caller (verify with
  `grep -rn select_by_text well_viewer/`). If any external touch point
  remains, leave the alias and document it.
- Delete the `tabText` back-compat method on `NamedPageStack` *if* commit
  3 migrated every caller (same verification).
- Remove the `QTabWidget` import line if no remaining uses in the file
  (`grep -n QTabWidget well_viewer/views/centre_view.py` should return
  zero).

## Risk callouts

- **`select_by_text` is a closure**, not a method. Grep for the string
  literal, not for `addTab`; the inventory found 5 call sites (commit 4
  migrates them).
- **`currentChanged(int)` signal** is natively emitted by
  `QStackedWidget` with the same `int` payload —
  `_on_notebook_current_changed(_idx)` works unchanged. Confirm in
  commit 1 by switching sections via RailNav and watching the RailNav-
  sync re-fire.
- **`addPage` order vs. `currentChanged` connection**: in commit 2,
  ensure `addPage(title, frame)` registers the name *before* the sub-tab
  handler connects to `currentChanged`, otherwise the first emit can see
  `currentName() == ""`.
- **External touch points** for `app._notebook` /
  `app._plotting_notebook` (if any plugin or scripted entry reads the
  attribute) keep working because `NamedPageStack` exposes the same shim
  methods that match `QTabWidget`'s API surface.
- **`_centre_pending_builders` / `_centre_lazy_only_titles`** are already
  title-keyed; the migration touches neither.

## Verification per commit

1. `python -m py_compile` clean on every file changed in that commit.
2. App launches; titlebar mode-seg works; titlebar dataset chip / OS
   window title still updates on Open.
3. RailNav click sweep — all 8 sections render correctly; sidebar
   visibility (Sample Definitions plate panel, Image Table picker, Stats
   sidebar) toggles correctly per `_on_tab_change`.
4. Plotting → ctxbar `SegmentedControl` click sweep — all 5 plot types
   render; channel chip mirrors active renderer's combo.
5. Batch Export entry points (those that previously called
   `select_by_text("Batch Export")`) still land on Batch Export.
6. smFISH single-well clamp (`selection_controller` line 65–70) —
   selecting smFISH, clicking row letter, only the last well stays
   selected.
7. Movie Montage gating (`plot_orchestrator` line 44–47) — switch to
   Plotting → Movie Montage (if accessible) and confirm preview refresh
   fires.

## Exit criteria

- Zero `QTabWidget` references in `well_viewer/views/centre_view.py`.
- `_GroupedTabBar` class deleted.
- Every downstream caller in `well_viewer/` routed through
  `currentName()` / `setCurrentByName()` / `pageNames()` (no remaining
  `tabText` or `select_by_text` uses outside the optional shims).

## Critical files

- `well_viewer/views/centre_view.py` — primary refactor surface.
- `well_viewer/runtime_app.py` — 4 read-side + 5 write-side call sites.
- `well_viewer/selection_controller.py` — 2 read-side call sites.
- `well_viewer/views/sidebar_view.py` — 1 read-side call site.
- `well_viewer/plot_orchestrator.py` — 1 read-side call site.
- `well_viewer/review_image_controller.py` — internal helper.
- `design/PROJECT_STATUS.md` — Phase 15 row + Outstanding-work section.
