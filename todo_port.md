# PySide6 Migration — Port Progress

Strategy: break each large file into ≤200-line write chunks to avoid stream timeouts.

## analyze_tab.py (1399 → ~480 LoC) ✓ DONE

## Controllers (thin — one write each) ✓ DONE

## Callbacks + Services ✓ DONE

## Monoliths
- [x] batch_export_dialog.py (2030 LoC) — 4 parts
- [x] runtime_app.py (6941 LoC) — structural port (imports, widget constructors, dialogs, main)
    - [x] imports + module-level helpers (make_fluor_thumb, make_overlay_thumb, ask_name_dialog, _bind_drag, save/load_json)
    - [x] WellViewerApp.__init__ + tk.Variable attrs (23)
    - [x] WellViewerApp UI build methods (plate grid, tabs, sidebar, preview, montage, LUT editor)
    - [x] WellViewerApp controller/callback methods — widget constructors only
    - [x] main()

## Final
- [x] Acceptance grep sweep (0 hits for tkinter/ttk/messagebox/filedialog/after/bind/StringVar)
- [ ] pytest tests/ (blocked: libEGL.so.1 missing in sandbox; Qt import fails at test collection)
- [ ] Commit + push

---

## ⚠ Follow-up: legacy Tk-method call sites inside `runtime_app.py`

### Source of the problem

The previous acceptance sweep only covered **imports, constructors, and the
most obvious replacements** (`tk.Frame()`, `messagebox.*`, `filedialog.*`,
`self.after()`, `.bind("<...>")`, `tk.StringVar`). It did **not** touch any of
the Tk-era *widget method calls* or bare Tk constants that are sprinkled
throughout `runtime_app.py`. Because `tk` is no longer imported, every one of
these sites raises `NameError: name 'tk' is not defined` the first time the
code path is hit; the Qt widgets that replaced the old Tk widgets also don't
implement `.config()`, `.pack()`, `.winfo_*()`, `.destroy()`, etc., so the
call-sites would still fail with `AttributeError` even if `tk` were aliased.

### Survey (all counts are for `well_viewer/runtime_app.py` unless noted)

| Pattern | Count | What it is | Qt replacement |
|---|---|---|---|
| `.config(bg=, fg=, relief=, state=, cursor=, activebackground=, ...)` | 72 | Per-widget styling, mostly plate-map button refresh | Split: `setEnabled()`, `setCursor()`, `setText()`; drop colours in favour of `setProperty("state", ...)` + QSS + `style().unpolish/polish()` |
| `.configure(bg=..., fg=...)` | 18 | Stats panel theme hook | Delete — QSS handles theming (already wired in `_apply_theme`) |
| `.pack(fill=tk.BOTH, side=tk.LEFT, ...)` / `.pack_forget()` | 15 | Sidebar tab visibility, progress bar, log frame | `QLayout.addWidget()` at construction; for dynamic show/hide use `widget.show()` / `widget.hide()` |
| `.grid(...)` | 11 | Mostly `ax.grid()` (matplotlib, OK); a few layout calls | Layout calls already done via `QGridLayout.addWidget()`; leave mpl `ax.grid` alone |
| `.winfo_children()` | 3 | Re-render loops (montage rebuild, etc.) | Use existing `_clear_layout(layout)` helper |
| `.winfo_rootx()/rooty()` | 2 | Drag-handler screen-space anchor | `event.globalPosition().toPoint().x()/y()` (pattern already used in ported drag handlers) |
| `.winfo_width()/height()` | 6 | Canvas-size queries (montage, review-image) | `widget.width()` / `widget.height()` |
| `.winfo_manager()` | 4 | "is this frame currently packed?" check in sidebar switch | `widget.isVisible()` |
| `.winfo_exists()` | 1 | Guard on scatter-cell viewer window | Track the reference; test `is not None` (drop the Tk liveness check) |
| `.winfo_containing(x, y)` | 1 | Drag hit-test | `QApplication.widgetAt(x, y)` |
| `.destroy()` | 5 | Clear montage children; tear down embedded Tk root | Widget cleanup: `w.setParent(None); w.deleteLater()`. The two `self._tk_root` branches are dead code — delete. |
| `tk.END`, `tk.BOTH`, `tk.X`, `tk.LEFT`, `tk.RIGHT`, `tk.FLAT`, `tk.NORMAL`, `tk.DISABLED`, `tk.SUNKEN` | ~55 | Bare constants used as kwargs | Delete — the enclosing `.config/.pack/.insert` call goes away at the same time |
| `self._stats_result_text.delete("1.0", tk.END)` + `insert(tk.END, text)` + `config(state=tk.NORMAL/DISABLED)` | 5 lines | Stats results text area | `QTextEdit.clear()` / `QTextEdit.append(text)` / `setReadOnly(bool)` |
| `table.insert("", tk.END, values=...)` (Treeview) | 1 | Review-CSV row insert | `QTableWidget.insertRow(); setItem()` per column |
| `listbox.curselection()` (in `viewer_state.py`) | 1 | Helper `_selected_listbox_values` | `[lb.item(i).text() for i in range(lb.count()) if lb.item(i).isSelected()]` (already have `_selected_list_values` in runtime_app; consolidate) |

**Files with real residual legacy calls:** only `well_viewer/runtime_app.py` and
`well_viewer/viewer_state.py`. All other `well_viewer/` files are clean
(remaining "hits" are matplotlib `ax.grid()` or docstring mentions).

### Concentrations (where the damage lives)

1. **Plate-map refresh methods** — `_stats_refresh_map`, `_bar_refresh_map`,
   `_rep_refresh_map`, `_refresh_sidebar_map_now`, plus their per-button
   `config(...)` helpers. ~40 of the 72 `.config()` hits live here. Lines
   ~1855-1940, 2224-2330, 3900-3965.
2. **Stats panel theme hook** — `_stats_refresh_colors` calls `.configure(bg=)`
   on ~8 child widgets (lines 2085-2115). Now redundant — QSS handles colours.
3. **Sidebar tab switch** — `_on_tab_change` toggles 6 sub-frames with
   `pack_forget()` / `pack()` + `winfo_manager()` guards (lines 5159-5227).
4. **Montage rebuild** — three sites that call `winfo_children()` +
   `w.destroy()` to clear prior thumbnails (3379-3380, 3502-3503, 4411-4412).
5. **Stats results text area** — 5-line block at 2069-2073 using the Tk
   `Text` widget API.
6. **Review-image canvas size** — 6 `.winfo_width()/height()` calls on what is
   now a `QScrollArea` or `QLabel` (4952-4953, 5029-5030, 5091-5092).
7. **Review-CSV table insert** — one `tree.insert("", tk.END, values=...)` at
   5427 inside `_refresh_review_csv`.
8. **Progress bar + log frame show/hide** — lines 6795, 6810, 6816, 6819.
9. **Coordinate helpers `_sidebar_tok_at`, `_bar_map_tok_at`,
   `_rep_map_tok_at`** — three methods that still use
   `event.widget.winfo_rootx() + event.x` style lookups (lines ~2279, ~3263,
   ~3991). Need to switch to `event.globalPosition()` + `widgetAt()`.

### Strategy (the fix, to be executed in a follow-up PR)

**1. Consolidate the plate-map styling through a single `_style_well_button`
helper.** Today every refresh method repeats an 8-keyword `btn.config(bg=, fg=,
state=, relief=, cursor=, activebackground=, activeforeground=,
disabledforeground=)` incantation. Under Qt all of those kwargs collapse to
two operations:

```python
def _style_well_button(btn, *, state: str, enabled: bool = True):
    btn.setEnabled(enabled)
    btn.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
    btn.setProperty("state", state)   # "empty" / "selected" / "group_N" / "disabled"
    btn.style().unpolish(btn); btn.style().polish(btn)
```

All colour info lives in `ui/theme/dark.qss` / `light.qss` as
`QPushButton[state="group_1"] { background: ${WELL_COLOR_1}; }` — the
stylesheet already contains the token substitutions. After this single helper
lands, the ~40 `.config(...)` sites in the refresh methods collapse to one
function call each and all `tk.SUNKEN/FLAT/NORMAL/DISABLED` constants
disappear with them.

**2. Delete the stats-panel `configure(bg=...)` chain wholesale.** The
theme repaint path for Qt is `QApplication.setStyleSheet(build_stylesheet(
theme_name))` inside `_apply_theme`, which we already wired. The
`_stats_refresh_colors` method becomes a no-op (or is deleted entirely
along with its call-sites in `_on_theme_change`).

**3. Replace `pack/pack_forget` with `show/hide`.** Every call site stores the
widget as `self._sidebar_X_frame`; the frame is already in its parent's layout
from the `_build_ui` phase. The sidebar tab-switch becomes:

```python
self._sidebar_preview_frame.setVisible(tab == "Preview")
self._sidebar_sample_frame.setVisible(tab in {"Bar Plots", "Sample Definitions"})
# ...etc
```

This removes 26 layout calls and all `winfo_manager()` guards in one sweep.

**4. Replace `winfo_children() + destroy()` with the existing `_clear_layout`
helper.** All three montage-rebuild sites already have a `QLayout` reference
(or one can be obtained via `widget.layout()`); just call
`_clear_layout(layout)`. The helper already does
`takeAt(0); w.setParent(None); w.deleteLater()` correctly.

**5. Port the stats results `Text` block to `QTextEdit`.** Replace the five
lines at 2069-2073 with:

```python
self._stats_result_text.setReadOnly(False)
self._stats_result_text.clear()
for text in ...:
    self._stats_result_text.append(text)
self._stats_result_text.setReadOnly(True)
```

**6. Port the review-CSV table.** `ttk.Treeview` → `QTableWidget`. For each
row: `row = table.rowCount(); table.insertRow(row); for ci, v in
enumerate(values): table.setItem(row, ci, QTableWidgetItem(str(v)))`.

**7. Fix the three plate-map hit-test helpers.** Replace:

```python
sx = event.widget.winfo_rootx() + event.x
sy = event.widget.winfo_rooty() + event.y
w  = event.widget.winfo_containing(sx, sy)
```

with:

```python
gp = event.globalPosition().toPoint()
w  = QApplication.widgetAt(gp)
```

**8. Delete `self._tk_root` branches and the orphan `self.destroy()` call.**
`_tk_root` is set to `None` in `__init__`; the two sites that dereference it
are unreachable and can be removed.

**9. Swap `.winfo_width()` → `.width()` and `.winfo_height()` → `.height()`
across the review-image block.** Mechanical; no semantics change.

**10. Consolidate the viewer_state helper.** `selected_listbox_values` in
`well_viewer/viewer_state.py` still does `listbox.curselection()` on a Tk
Listbox. Rewrite to use `QListWidget` API. The local
`_selected_list_values` in runtime_app.py should be deleted in favour of the
consolidated helper.

### Execution plan

Implement in this order so every commit leaves the module importable and
leaves `pytest tests/` green:

1. Add the `_style_well_button` helper and the QSS `state=` selectors; migrate
   all four `_*_refresh_map` methods. (~60 call sites, 1 commit)
2. Port the Text/Treeview widgets (stats results + review CSV). (1 commit)
3. Sidebar-tab `pack_forget`/`pack` → `setVisible`. (1 commit)
4. Montage rebuild `winfo_children/destroy` → `_clear_layout`. (1 commit)
5. Plate-map hit-test `winfo_rootx/winfo_containing` → `QApplication.widgetAt`.
   (1 commit)
6. Dead code cleanup (`_tk_root`, `_stats_refresh_colors`, orphan `destroy`,
   `winfo_width/height` renames). (1 commit)
7. `viewer_state.selected_listbox_values` → QListWidget. (1 commit)

After step 7 the repo should launch cleanly under PySide6 and
`grep -nE '\.config\(|\.configure\(|\.pack\(|winfo_|tk\.(END|BOTH|X|LEFT|RIGHT|FLAT|NORMAL|DISABLED|SUNKEN)|\.destroy\(\)' well_viewer/` should return 0 hits for real widget methods (matplotlib `ax.grid()` remains).
