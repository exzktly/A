# Well selector gap analysis

What the legacy `WellButton` plate grid does that `widgets.WellPlateSelector`
(as built in Phase 6) does not, and what it would take to close the gap.

**Scope note.** I audited the actual code, not the mockup. Several behaviours
people *expect* to find on a plate widget — right‑click context menus, hover
tooltips with sample/treatment/image‑count metadata, double‑click to open a
well's images, keyboard navigation, shift‑click ranges, per‑well badges — **do
not exist** in this app's `WellButton` today (no `contextMenuEvent`, no
`mouseDoubleClickEvent`, no key handling, the only tooltip is the bare well
token). So the gap is narrower than it might look, but the things that *are*
there are load‑bearing.

Reference files: `well_viewer/views/well_button.py` (the `WellButton` widget +
`build_plate_grid`), `well_viewer/views/sidebar_view.py` (`build_sidebar` —
wires the rail), `well_viewer/selection_controller.py` (drag/select handlers),
`well_viewer/runtime_app.py` (`_refresh_sidebar_map_now`, `_plate_apply_*`,
`_select_row/_select_col`, `_sb_press/_sb_drag/_sb_release`,
`_sidebar_btns`). Tokens are zero‑padded `"A01".."H12"` on both sides
(`PLATE_COLS = ["01".."12"]`), so the "token format mismatch" I worried about in
`REWIRING.md` is **not** actually a blocker — `app._well_paths` keys come from
`_extract_well_token` and match `"A01"` style.

---

## 1. Load‑bearing behaviours of the legacy grid

| # | Behaviour | What it does | Where implemented | Trigger | What breaks if shipped without it |
|---|---|---|---|---|---|
| G1 | **Per‑well click‑toggle selection** | Left‑click a well → add/remove it from `app._selected_wells`, refresh the active tab. | `sidebar_view._make_btn_handlers` overrides each `WellButton`'s mouse events → `app._sb_press` → `selection_controller.sb_press` → `plate_drag_press/_apply`; then `sb_release` → `app._on_plate_sel_change` → `_refresh_after_selection_change`. | User clicks a well. | Nothing fundamental — `WellPlateSelector.selectionChanged(list)` covers this if wired to `app._selected_wells` + `app._on_plate_sel_change()`. (This is the one piece that already maps.) |
| G2 | **Drag‑to‑select** | Press on a well and drag across others → toggles a whole run in one gesture; the "add vs remove" decision is locked at press time from the first well's state. | `sidebar_view._make_btn_handlers` (`_press/_move/_release` + `_tok_under_cursor`) → `app._sb_press/_sb_drag/_sb_release` → `selection_controller.plate_drag_press/_apply/_release` driving the `app._sb_ds` state machine (`{"adding","visited","rep_toggled"}`). | User press‑drags over the plate. | A primary multi‑well interaction is gone; users must click wells one at a time. `WellPlateSelector` has no drag mode and (being self‑painted) no per‑well child widgets to attach drag handlers to. |
| G3 | **Data‑state colour coding** | Every well is recoloured to reflect its state: selected → ACCENT (sunken), no data → disabled/transparent, in per‑well mode unselected → neutral. (Replicate‑set colouring is G4.) | `runtime_app._refresh_sidebar_map_now` → `_plate_apply_colored / _plate_apply_neutral / _plate_apply_disabled / _style_plate_button`, which mutate each `WellButton`'s `state` property + per‑widget QSS. | `_refresh_sidebar_map()` (debounced) — called after selection changes, dataset load, tab change, rep‑set edits, etc. | The plate stops being a status display. `WellPlateSelector` colours wells by *trace index of their position in the selection* (the "plate‑is‑legend" idea), not by "selected / no‑data / neutral" — semantically different. |
| G4 | **Replicate‑set visual mode** | When `app._rep_sets` is non‑empty the plate shows rep‑set *membership* (each set gets a colour) and *hidden* state (muted); clicks toggle a set's visibility (`app._rep_hidden`) rather than individual wells; the count label switches to "N/M set(s) visible". | Colouring: `_refresh_sidebar_map_now` (`tok_rep` map, `_style_plate_button` muted variant, `_plate_apply_colored`). Clicks: `selection_controller.plate_drag_apply` rep branch (`set_state("rep_hidden"|"active")`), `select_row/_select_col` rep branches, `sb_release` → `app._sb_on_rep_change`. | Rep‑sets defined on the Sample Definitions tab; then any plate click while rep‑sets exist. | Replicate‑set workflows lose their primary control surface. `WellPlateSelector` has no concept of rep‑sets — only a flat selected set. |
| G5 | **Disabled (no‑data) wells** | Wells with no loaded CSV are `setEnabled(False)` and rendered transparent‑bordered/greyed; they can't be selected or dragged onto. Enabled lazily as data loads. | `build_plate_grid` creates every button `setEnabled(False)`; `_plate_apply_*` enables/disables per `tok in app._well_paths`; `sb_press`/`plate_drag_apply` short‑circuit on `tok not in app._well_paths`. | Dataset load (`load_controller.load_directory` populates `_well_paths`). | Users could "select" wells that have no data; downstream code that assumes selected ⊆ `_well_paths` would get junk. `WellPlateSelector` has no per‑well enabled state. |
| G6 | **Heat‑map drag *source*** | On the Heat Map tab each well becomes a `QDrag` source carrying its token via a MIME type, so it can be dropped onto the heatmap‑layout table. | `WellButton.set_drag_mime(mime)` / `_drag_mime` + `mousePressEvent/mouseMoveEvent` start a `QDrag`; toggled by the heatmap controller. | Heat Map tab active → controller calls `set_drag_mime(...)` on each button; user drags a well. | Drag‑to‑build heatmap layouts breaks. `WellPlateSelector` paints the grid — there are no per‑well widgets to be drag sources, and a single widget can't easily originate per‑cell drags without bespoke `mouseMoveEvent` + hit‑testing. |
| G7 | **Drop *sink* (return a well)** | A well can *accept* a drop carrying a token (used to "return" a well that was dragged out elsewhere). | `WellButton.set_drop_handler(mime, handler)` / `_drop_mime` + `dragEnter/dragMove/dropEvent`. | A drag from the heatmap layout table over a plate well. | The "return well" gesture stops working (probably minor — only one direction of the heatmap DnD). |
| G8 | **Row/column header quick‑select** | The `A–H` letters and `1–12` numbers are themselves clickable: clicking one selects/deselects that whole row/column (rep‑set‑aware variant when rep‑sets are active; suppressed on smFISH). | `build_plate_grid` uses `_HeaderClickLabel` with `on_row_click/on_col_click`; `sidebar_view._on_row_click/_on_col_click` (gated by `_row_col_select_disabled`) → `app._select_row/_select_col` → `selection_controller.select_row/select_col` (each with a rep‑set branch). | User clicks a row letter / column number. | Whole‑row/col selection is gone. `WellPlateSelector` *has* clickable headers, but they only toggle its own internal selection and emit `selectionChanged` — so the rep‑set‑aware path and the smFISH suppression are bypassed; functionally OK for the plain case, wrong for rep‑sets. |
| G9 | **Per‑tab selection gating** | smFISH suppresses row/col header clicks and forces single‑well selection (`on_plate_sel_change` keeps only the last well when on smFISH). | `sidebar_view._row_col_select_disabled` (checks the notebook's current tab); `selection_controller.on_plate_sel_change` (smFISH single‑well clamp). | Switching to/being on the smFISH tab. | smFISH could end up with multi‑well selections it can't handle. Could be re‑applied on `WellPlateSelector` after the fact (clamp its selection), but only as a workaround. |
| G10 | **`app._sidebar_btns: {token: WellButton}` registry + `set_state`** | A dict of every plate well's widget, plus the `set_state(name)` per‑button API. Consumed by `_refresh_sidebar_map_now`, `selection_controller.plate_drag_apply`, the heatmap controller, `_on_tab_change`/reset paths, `_install_*` — ~10 sites. | `sidebar_view.build_sidebar` populates `app._sidebar_btns`; `WellButton.set_state` / `_plate_apply_*` consume it. | Constructed at sidebar build time; read whenever the plate needs repainting. | Direct `AttributeError`/crash at every consumer unless `WellPlateSelector` exposes an equivalent decoration API. This is the single biggest mechanical blocker. |
| G11 | **3D emboss cue** | A raised/depressed highlight‑and‑shadow arc painted just inside each well's border (raised = unselected, depressed = selected). | `WellButton.paintEvent` + `set_emboss`. | Selection state change. | Purely cosmetic; `WellPlateSelector` already has its own "lit chip" sheen, so this is the *least* important gap — it's a style choice, not a feature. |
| G12 | **Token tooltip** | Hovering a well shows its token (`"A07"`). | `WellButton.setToolTip(text)` in `__init__`. | Hover. | Minor accessibility loss; `WellPlateSelector` has no per‑cell tooltip. (Note: this is *not* the metadata‑rich tooltip people might expect — it's just the well ID.) |

---

## 2. How `widgets.WellPlateSelector` could be extended, per gap

`WellPlateSelector` is already a self‑painted `QWidget` with hover tracking, a
`_PlateGrid` child, and `selectionChanged`. The additions below build on that.

- **G1** — *no change needed.* Already covered by `selectionChanged(list)` +
  `selectedWells` / `setSelectedWellIds`.

- **G3, G5, G10 — external per‑well "decoration" API** (the keystone — most
  other gaps lean on this):
  - New: `setWellEnabled(ids: Iterable[str], enabled: bool)` / an
    `enabledWells` set — disabled wells render greyed/transparent‑bordered and
    are skipped by hit‑testing. (G5)
  - New: `setWellColors(mapping: dict[str, QColor|None])` — explicit per‑well
    fill override; `None` reverts to the default. `paintEvent` consults this
    map *before* the trace‑gradient logic. Lets the app paint "selected =
    accent", rep‑set colours, etc. (G3, G4 colouring)
  - New (optional, ergonomic): `setWellState(id, state)` accepting a small
    vocabulary (`"selected"`, `"neutral"`, `"disabled"`, `"rep:<colorhex>"`,
    `"rep_hidden:<colorhex>"`) mapped to the colour/enabled primitives — gives
    the app something close to today's `set_state`, easing the migration of the
    `_refresh_sidebar_map_now` consumer. (G10)
  - `paintEvent` changes: consult `enabledWells` + `setWellColors` per cell;
    add a "disabled" appearance branch.
  - Cost: medium rendering work, but it generalises cleanly.

- **G2 — drag‑to‑select mode:**
  - New: a `dragSelect` boolean (default on for the rail use). In `_PlateGrid`,
    `mousePressEvent` records the press cell and locks "add vs remove" from its
    current membership; `mouseMoveEvent` (already tracked) toggles every cell
    entered; `mouseReleaseEvent` finalises and emits `selectionChanged` once.
  - New signal `selectionDragFinished()` (so the app can do its
    once‑per‑gesture refresh instead of one per cell).
  - Cost: small‑to‑medium — the hit‑testing and hover machinery already exist;
    this is mostly a press→drag→release state variable.

- **G4 — replicate‑set mode:** mostly *not* the widget's job. The cleanest
  split: the app keeps owning rep‑set state and uses `setWellColors` (G3) to
  paint membership/hidden, and a new `mode` enum on the widget —
  `mode="select"` (current behaviour) vs `mode="passive"` (clicks/drags emit a
  `wellActivated(id)` / `rowActivated(str)` / `columnActivated(str)` signal but
  don't mutate the widget's own selection). In `"passive"` mode the app
  interprets clicks as rep‑set‑visibility toggles. Cost: small (a mode flag +
  routing clicks to a signal instead of the internal selected‑set), assuming G3
  lands.

- **G6 — heat‑map drag source:** add an optional `dragMime: str|None` property;
  when set and `mode != "select"`‑ish, a press‑then‑move past
  `QApplication.startDragDistance()` over a cell starts a `QDrag` carrying that
  cell's token (mirrors `WellButton`'s logic, but with one `mouseMoveEvent` on
  the parent + hit‑test). Cost: small‑to‑medium.

- **G7 — drop sink:** `setAcceptDrops(True)` + `dragEnter/dragMove/dropEvent`
  that hit‑test the drop point to a cell and emit `wellDropped(id, token)`.
  Cost: small.

- **G8 — row/column header signals:** expose
  `rowHeaderClicked(str)` / `columnHeaderClicked(str)` on `WellPlateSelector`
  (re‑emitting `_PlateGrid`'s internal `rowHeaderClicked/columnHeaderClicked`,
  and *not* mutating its own selection when `mode="passive"`). Cost: trivial —
  the signals already exist internally, just not surfaced.

- **G9 — per‑tab gating:** keep this in the app, not the widget. The rail
  view that hosts `WellPlateSelector` already knows the active tab; it can call
  `setRowColumnSelectable(False)` (a new small flag that makes header clicks
  no‑op) and clamp the selection to one well after `selectionChanged` on
  smFISH. Cost: trivial widget‑side (one flag), the clamp is app‑side.

- **G11 — emboss cue:** skip. `WellPlateSelector`'s radial‑gradient + sheen is
  the v2 look; the legacy emboss is the *old* look we're replacing.

- **G12 — token tooltip:** override `event()` for `QEvent.ToolTip` in
  `_PlateGrid`, hit‑test to a cell, `QToolTip.showText(id)`. Trivial. (If we
  ever want metadata‑rich tooltips, add a `wellTooltipProvider: Callable[[str],
  str]` hook — but that's net‑new, not a gap.)

---

## 3. Effort estimate

| Gap | Effort | Notes |
|---|---|---|
| G1 | **none** | already works |
| G8, G9, G12 | **trivial** | surface existing signals / add a flag / one event handler |
| G7 | **small** | standard drop handling + hit‑test |
| G2 (drag‑select), G6 (drag source) | **small–medium** | reuse existing hover/hit‑test; press→move→release state |
| G3 + G5 + G10 (decoration API: per‑well colours + enabled + a `setWellState` convenience) | **medium** | the keystone; new `paintEvent` branches + 2–3 new methods/props. Everything else leans on it. |
| G4 (rep‑set mode) | **small *given G3/G10*** | mostly a `mode` flag + routing clicks to a signal; the colouring is G3 |
| **Migrating the consumers** (rewrite `_refresh_sidebar_map_now`, `selection_controller` plate handlers, heatmap controller, tab‑change reset paths off `_sidebar_btns`/`set_state` onto the new API; delete `WellButton`/`build_plate_grid`) | **medium–large** | not a widget change at all — it's the app‑side rewire, and it touches ~10 sites and the smFISH/heatmap paths. This is where the real risk and test burden live. |

Nothing here individually "justifies keeping the legacy `WellButton` grid
permanently" — the widget‑side additions are all tractable and idiomatic. The
weight is in (a) the decoration API (G3/G5/G10) and (b) the app‑side migration,
which together are a focused 1–2‑session sub‑project that **must be runtime‑
tested** (rep‑set toggling, drag‑select, smFISH single‑well clamp, heatmap DnD).

---

## 4. Recommendation

**Option (b) now, Option (a) as the very next dedicated task.**

1. **Now — ship the rail‑chrome port with the legacy plate restyled.** The
   "All"/"None" buttons and the count label are already on `theme.qss()` (done
   in commit *Port well plate selector area*). Add a small follow‑up that
   restyles the *legacy `WellButton` grid* to match the mockup as closely as QSS
   + the existing `paintEvent` allow: pull the well fill/border/disabled colours
   in `runtime_app._plate_theme_colors` / `_plate_apply_*` /
   `well_button.py`'s QSS from `theme.Colors` (accent for selected, `panel_elevated`
   for empty‑with‑data, transparent for no‑data, the trace palette for rep‑sets),
   tweak `WELL_SIZE`/spacing toward the mockup's well size, and optionally swap
   the `_HeaderClickLabel` styling to `#Caption`. This is low‑risk (no behaviour
   change, ~one file of colour edits) and gets the rail looking right today.

2. **Next dedicated task — extend `WellPlateSelector` (G2, G3+G5+G10, G6, G7,
   G8, G9, G12), then do the swap.** Land the decoration API first (it unblocks
   everything), then drag‑select, then the heatmap DnD, then migrate
   `_refresh_sidebar_map_now` / `selection_controller` / the heatmap controller
   off `_sidebar_btns`, then delete `WellButton`/`build_plate_grid`. Gate on a
   manual QA pass covering: per‑well click + drag select, rep‑set membership
   colours + visibility toggle + the count‑label switch, no‑data wells
   un‑selectable, row/col quick‑select (incl. rep‑set variant), smFISH single‑
   well clamp, and heatmap‑layout drag‑and‑drop both directions.

Why not **(a) now**: it's a multi‑file, ~10‑consumer rewrite of interaction code
(drag‑select, rep‑set mode, heatmap DnD) that can't be verified in this
environment — exactly the kind of change that should be its own reviewed,
runtime‑tested commit, not bundled into "port the left rail". Why not "keep the
legacy grid forever": none of the gaps are intractable, and the v2 plate‑as‑
legend rendering is a real design goal, so a permanent fork would be the wrong
call.
