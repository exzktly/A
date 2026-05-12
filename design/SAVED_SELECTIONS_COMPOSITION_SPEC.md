# `SavedSelectionsList` composition extension — spec (Phase 6.5.12)

> **Status:** approved 2026-05-12 (incl. the §5 "widget stays permissive" call);
> **built** (code, not runtime-verified — `widgets/saved_selections_list.py` +
> the gallery card + `__main__`; `py_compile` clean). Pending: your runtime QA
> of the gallery card / `__main__`, then Phase 8.0 Stage C (view swap →
> mutation flip → Stage D). The text below is the as-built spec; minor
> as-built deviations are noted inline.
> The user reframed this as "the 6.5.10 widget round we missed"; numbered here
> **6.5.12** to avoid clashing with the already-completed 6.5.10 (`PlotCard`
> extension). It is the prerequisite that *unblocks* Phase 8.0 Stage C (swap the
> Sample-Definitions group/rep panels for `widgets.SavedSelectionsList`) and D
> (delete the legacy shadow). Build order: this spec → your approval → build →
> gallery QA → your runtime test → then Stage C/D.

## 0. Why

`widgets.SavedSelectionsList` (built in 6.5.8) renders a selection's well chips
**read-only** — by deliberate contract decision ("editing well membership from
the list is deferred", `SELECTIONS_MODEL_CONTRACT.md` §6). But the legacy
Sample-Definitions panels we want to replace (`views/grouping_view.py`,
`views/bar_group_panel_view.py`) *do* let you compose a selection — add/remove
wells, bundle wells into replicate sets, add/remove member rep-sets, add/remove
solo wells. A straight swap would lose that. So `SavedSelectionsList` needs an
optional composition mode before the swap can happen.

---

## 1. What the legacy "+ Set:" / "−" / plate-drag controls actually do

Exhaustive list, pulled from `well_viewer/grouping_controller.py`,
`well_viewer/views/grouping_view.py`, `well_viewer/views/bar_group_panel_view.py`,
`well_viewer/runtime_app.py` (rep dialogs), and `well_viewer/batch_export/base_panel.py`.

### 1.1 Replicate-set composition (legacy `ReplicateSet = {name, wells}`)

| Op | Where | Effect | Edge cases |
|---|---|---|---|
| **Create rep-set** | `_rep_add` (modal: name + multi-select well listbox) | new `ReplicateSet(name, sel)`; becomes the active rep-set | empty selection → blocked ("Select at least one well"); name blank → defaults `"Rep N"`; no uniqueness enforced on rep-set names (collisions allowed at the legacy level — the migration's `_v2` handles them on the way to the unified model) |
| **Rename rep-set** | `_rep_rename(idx)` (name dialog) | `rset.name = name` | blank → no change |
| **Delete rep-set** | `_rep_delete(idx)` | pop from `_rep_sets` **and** remove it from every `BarGroup.members` (cascade) | deleting the active one → active idx clamps; a group that loses its only member becomes empty (allowed) |
| **Add/remove a well to/from the *active* rep-set** | rep-map plate-**drag** (`grouping_controller.rep_map_press/drag/apply`) | adding `tok`: **removes `tok` from every other rep-set first** (a well belongs to ≤ 1 rep-set), then `rset.wells.append(tok)`; removing: `rset.wells.remove(tok)` | exclusivity across rep-sets is *enforced* here; drag-paint mode (add vs remove) is decided by the first cell touched |
| **Activate a rep-set** | `_rep_select(idx)` / clicking a rep card | makes the plate edit this rep-set; sets `_active_rep_idx`, clears `_bar_active_grp` (mutually exclusive edit target) | — |

### 1.2 Bar-group composition (legacy `BarGroup = {name, members:[ReplicateSet], solo_wells:[str], hidden}`)

| Op | Where | Effect | Edge cases |
|---|---|---|---|
| **Create group** | `grp_add` / `_bar_add_group` | new empty `BarGroup("Group N")`; becomes active | starts empty (`wells=[]`, `members=[]`, `solo_wells=[]`) — allowed |
| **Rename group** | `grp_rename(idx)` (dialog) / inline edit in the v2 card / `_bar_rename_group` | `grp.name = name` | blank → revert |
| **Delete group** | `grp_delete(idx)` / `_bar_remove_group` | pop from `_bar_groups`; **member rep-sets are NOT deleted** (shared, stay in `_rep_sets`); active idx clamps | — |
| **Toggle group visibility** | `grp_toggle_visibility(idx)` / `_bar_toggle_group_visibility` | `grp.hidden = not grp.hidden` | hidden groups still draw on plate (muted) but not on plots |
| **Clear all groups** | `grp_clear_all` / `_bar_clear_all_groups` | confirm dialog → `_bar_groups.clear()` | — |
| **Add a member rep-set to a group** | "+ Set: [rset buttons]" in `grp_panel_refresh` (only shows rep-sets *not already* in the group); `_bar_add_replicate_set(idx)` (picker) | `grp.members.append(rset)` if not present | a rep-set may be a member of **multiple** groups (no exclusivity, unlike well↔rep-set); the rep-set keeps its identity (the migration discards the *name* but keeps the *wells* as one `replicates` sub-list) |
| **Remove a member rep-set from a group** | "−" next to a member in the active group's card; `_bar_remove_replicate_set(idx, si)` | `grp.members.remove(rset)` | removing the last member → group may still have solo wells, or become empty; the rep-set survives (other groups / `_rep_sets`) |
| **Add a solo well to a group** | rep-map plate-**drag** when a *group* is active (`grouping_controller.rep_map_apply` → `grp.solo_wells.append(tok)`) | `grp.solo_wells.append(tok)` if not present | a solo well can coexist with the same well being inside a member's `wells` (`BarGroup.wells` dedups; `replicate_sets()` would list it twice → the migration de-overlaps) |
| **Remove a solo well from a group** | "−" next to a solo well; rep-map drag-remove | `grp.solo_wells.remove(tok)` | — |
| **Clear a group's replicates / clear a group** | `_bar_clear_replicates(idx)` / `_bar_clear_group(idx)` (bar-plot strip) | clear members (keep solo) / clear everything | — |

### 1.3 The plate-map is the keystone tool

The Sample-Definitions tab's rep-map plate (`_rep_map_btns`, 96 cells) is *the*
composition surface in the legacy UI: with a rep-set active, drag paints wells
into/out of that rep-set (exclusive); with a group active, drag paints **solo
wells** into/out of that group. The card lists ("+ Set:", "−") are secondary —
they exist for the rep-set↔group bundling that the plate can't express.

### 1.4 Mapping legacy ops → unified `Selection`

| Legacy | Unified |
|---|---|
| create rep-set from N wells | new `Selection(source="rep_set", wells=N, replicates=[[N]])` |
| create empty group | new `Selection(source="bar_group", wells=[], replicates=None)` |
| add member rep-set R to group G | append `list(R.wells)` as a new sub-list to `G.replicates`; union into `G.wells` |
| remove member rep-set R from G | remove the `G.replicates` sub-list equal to `R.wells` (first match); drop from `G.wells` the wells no longer covered |
| add solo well W to group G | union `W` into `G.wells`; if `G.replicates` is `None`, leave it; else append `[W]` |
| remove solo well W from G | drop `W` from `G.wells` and from any `G.replicates` sub-list |
| add well W to rep-set R (exclusive) | union `W` into `R.wells`; *(unified model does not enforce cross-selection exclusivity — see §5-Risk)* |
| remove well W from R | drop `W` from `R.wells` (and its single sub-list) |
| delete rep-set / group | remove the `Selection` |

**Net:** in the unified model there is no "member rep-set" object — a selection's
`replicates` is an *anonymous* partition of its `wells`. So "compose a group out
of rep-sets" becomes "edit this selection's wells, then bundle some of them into
replicates". The extension's UI is built around **editing one selection's
`wells` and `replicates`**, not around an inventory of named rep-sets.

---

## 2. Proposed UX in the extended `SavedSelectionsList`

Composition is **opt-in** (`setComposable(True)`); when off, the widget is
exactly today's read-only list. When on:

### 2.1 Where the controls live

The **expanded row** (already where well chips render) becomes the composition
surface — nothing new at the row-collapsed level (the kebab menu stays as-is).
Layout of an expanded, composable row, top-to-bottom:

```
▾ Control                       ● 6 wells          ⋯        <- row header (unchanged)
   ┌─────────────────────────────────────────────────────┐
   │ R1:  [A01 ×] [A02 ×] [A03 ×]                     ⊟  │  <- a replicate sub-list; ⊟ = "ungroup"
   │ R2:  [B01 ×] [B02 ×] [B03 ×]                     ⊟  │
   │ solo:[C03 ×]                                  [⊞ group] │  <- wells in no sub-list; ⊞ = "bundle all solo into a new replicate"
   │ [ + wells… ]                                        │  <- opens the plate popover
   └─────────────────────────────────────────────────────┘
```

When `replicates is None` (a flat selection), there are no `Rk:` rows — just
`[chip ×]…  [ + wells… ]` plus a `[⊞ make replicate]` button that wraps *all*
the selection's wells into a single sub-list (i.e. "treat these as one
condition's N replicates" — the common `rep_set` case).

### 2.2 The chips

- Each well chip renders in the chip style already used by the widget; in
  composable mode it shows a small **`×`** affordance on hover (and always when
  the row is keyboard-focused, for a11y). Clicking it removes the well from
  `wells` and from whatever `replicates` sub-list it was in (if that empties the
  sub-list, the sub-list is dropped). → emits `wellsChanged` (+ `replicatesChanged`
  if a sub-list changed).
- Chips wrap to multiple lines (a `FlowLayout`-ish wrap) so a large selection
  doesn't overflow horizontally. (If implementing a flow layout is too much,
  fall back to a horizontal `QScrollArea` strip per sub-list — `bar_group_panel_view`
  already does the single-line thing; acceptable.)
- A chip's menu offers **"✕ Remove"**, **"Move to new replicate"** (pull just
  this well into its own sub-list), **"Move to R1 / R2 / …"** (each other
  sub-list), and **"Make solo"** (if the well is currently in a sub-list). This
  covers arbitrary re-partitioning without needing chip drag-and-drop (the
  stretch goal, see §5). *(As built: rather than a hover-`×` plus a separate
  right-click menu, the chip is a `QToolButton` whose **click** opens this menu
  — one widget, one gesture, every action reachable; equivalent functionally,
  slightly fewer affordances on screen.)*

### 2.3 The `Rk:` sub-list rows

- Label `R1:`, `R2:`, … (1-based, in stored order). Drawn with the same muted
  caption style as the rest of the widget.
- `⊟` ("ungroup") at the end of the row: removes that sub-list — its wells stay
  in the selection's `wells` but become *solo* (no sub-list). → `replicatesChanged`.
- The `solo:` pseudo-row collects `wells` not in any sub-list; it has a `⊞`
  ("group solo") button that bundles all current solo wells into a *new*
  sub-list appended after the others. → `replicatesChanged`.
- If a selection has `replicates is None`, there are no sub-list rows; a single
  `[⊞ make replicate from all wells]` button is shown instead (sets
  `replicates = [list(wells)]`).

### 2.4 `[ + wells… ]` — the plate popover

- Opens a `widgets.Popover` anchored at the button, containing a
  `widgets.WellPlateSelector` in **multi-select** mode, with:
  - `setEnabledWells(...)` = the widget's `enabledWells` set (the host passes the
    loaded-dataset tokens; default = all 96, so it works standalone / in the
    gallery);
  - `setSelectedWellIds(...)` = this selection's current `wells`;
  - row/column header clicks select/deselect whole rows/columns (the
    `WellPlateSelector` already supports this);
  - dragging paint-toggles each cell the cursor crosses ("drag-paint", as the legacy rep-map plate does — not a rubber-band rectangle; already supported by `WellPlateSelector`).
- Below the plate: an **OK / Cancel** pair (or live + a "Done"). On commit, the
  selection's `wells` is set to `picked ∩ enabledWells`, in plate-rank order;
  any `replicates` sub-list is pruned to wells still present (empty sub-lists
  dropped). → `wellsChanged` (+ `replicatesChanged` if pruning happened).
- The popover may optionally be host-overridable via `setWellPlateFactory(fn)`
  (the app can hand back its own themed plate); default is a fresh
  `WellPlateSelector`. (Keeps the widget self-contained for the gallery while
  letting the app reuse its plate later if it wants.)
- *Not* doing cross-selection exclusivity here (see §5-Risk).

### 2.5 Keyboard / a11y

- Expanded row: `Tab` cycles chips → `+ wells…` → sub-list `⊟`/`⊞` buttons.
- A focused chip: `Delete`/`Backspace` removes it; the context-menu items are
  also reachable via the application menu key.
- The plate popover: arrow keys move the focus cell, `Space`/`Enter` toggles it,
  `Esc` closes (cancel), the `WellPlateSelector` handles this if it already
  supports keyboard nav; otherwise this is a stretch goal for the popover.

### 2.6 What stays on the host (Stage C), not in the widget

- "**Add member rep-set R to group G**" has no direct analog (no rep-set
  inventory in the model). The Stage-C view-swap can offer an optional
  "**＋ from another selection…**" affordance (a small menu of other selections;
  picking one appends its `wells` as a new sub-list to this one) — but that's a
  Stage-C decision, not part of this widget extension. The widget just needs
  `wellsChanged`/`replicatesChanged` so the host can react.
- The legacy *rep-map plate on the Sample-Definitions tab* can stay alive after
  the swap and be wired to drive the **currently-selected** selection's `wells`
  (drag-paint) — i.e. the keystone tool keeps working, just retargeted. That's a
  Stage-C wiring task; this widget extension provides the API (`wellsChanged`)
  for the host to push plate-driven changes *into* the widget too
  (`setSelectionWells(id, wells)` — see §3).

---

## 3. API additions

All additive; the existing `SavedSelectionsList` API is unchanged when
`composable` is off (the default).

**State / config:**
- `setComposable(bool)` / `isComposable() -> bool` — turns the expanded-row
  composition affordances on/off.
- `setEnabledWells(iterable[str])` / `enabledWells() -> list[str]` — the wells
  offered in the `+ wells…` popover (default: all 96; host passes loaded tokens).
- `setWellPlateFactory(callable | None)` — optional; `fn() -> a WellPlateSelector-
  like widget` for the popover (default: a fresh `widgets.WellPlateSelector`).

**Mutators (host → widget — keep the widget in sync when the app changes a
selection's membership from elsewhere, e.g. the rep-map plate):**
- `setSelectionWells(id, wells)` — replace one selection's `wells` (prunes its
  `replicates` to surviving wells); re-renders that row. *Does not* emit
  `wellsChanged` (host-originated).
- `setSelectionReplicates(id, replicates | None)` — replace one selection's
  `replicates` (validated/de-overlapped ⊆ `wells`); re-renders. No signal.
  *(Both are conveniences over `setSelections(...)`; they avoid a full rebuild.)*

**Signals (widget → host — user-originated edits):**
- `wellsChanged(str, list)` — `(id, new_wells)` after a chip removal or a
  popover commit.
- `replicatesChanged(str, list)` — `(id, new_replicates)` where `new_replicates`
  is `list[list[str]]` (never `None` in the signal — an empty partition is `[]`;
  the widget stores `None` internally for "no replicate structure" but the
  signal sends `[]` so the slot signature is stable).
- `selectionsChanged(list)` — still fires after any composition edit (coarse
  catch-all, as today).
  *(Granular `entry*` signals from 6.5.8 are unchanged. No `memberAdded`/
  `memberRemoved` — there's no "member" concept in the unified model; `wells`/
  `replicates` deltas cover everything.)*

**Internal state:** `_SelectionRow` already holds the row's `wells`; it gains the
selection's `replicates` and a `composable` flag, and rebuilds its expanded body
accordingly. The widget keeps its working `self._selections` list authoritative
(composition edits mutate it then emit, exactly like the existing edit ops). The
`_v2`/uuid/`#RRGGBB` invariants are unaffected (composition doesn't touch
id/name/colour).

---

## 4. Gallery demo plan

In `widgets/gallery.py`, the existing **`SavedSelectionsList`** card is upgraded:

- `lst.setComposable(True)`; `lst.setEnabledWells([f"{r}{c:02d}" for r in "ABCDEFGH" for c in range(1,13)])`.
- The seed data already has one selection with two `replicates` sub-lists
  (`"Control"`), one with one sub-list (`"Drug A — 1µM"`), one flat
  (`replicates=None`, `"Drug A — 10µM"`), and one `hidden` — exercising every
  layout branch.
- A reviewer can:
  1. expand a row → see `R1:/R2:/solo:` chip rows (or flat chips + `⊞ make
     replicate` for the `replicates=None` one);
  2. hover/focus a chip → click `×` → it disappears, the count chip and a
     read-out update;
  3. click `⊟` on a sub-list → its chips drop to `solo:`;
  4. click `⊞ group solo` → solo chips become a new `R3:`;
  5. right-click a chip → "Move to new replicate" / "Move to R1" → chip hops
     rows;
  6. click `+ wells…` → a `Popover` with a `WellPlateSelector` opens; click
     cells / a column header / drag-paint a run of cells → OK → those wells appear as
     chips;
  7. watch a `QLabel` read-out wired to `wellsChanged` / `replicatesChanged` /
     `selectionsChanged`.
- The card's caption note is updated to mention "composable: expand a row, edit
  chips / replicates / + wells…".
- (The non-composable behaviour is still shown implicitly — `setComposable` could
  even be toggled with a checkbox in the card if cheap.)

`__main__` of `widgets/saved_selections_list.py` gets the same `setComposable(True)`
treatment so it can be QA'd standalone.

---

## 5. Risk / hard-to-express ops

| Concern | Assessment |
|---|---|
| **Cross-selection well exclusivity** | **RESOLVED 2026-05-12 — exclusive.** A well belongs to **at most one group** (it caused an edge-case bug in the line-graph plate's rep-mode visibility toggle — `_rep_idx_for_label` returns the *first* owning set, so a well in two groups toggled the wrong one). The *app side* enforces it: every well-add point (the `+ Add` dialog, the rep-map plate drag, and `_rep_rebuild_from` for the `SavedSelectionsList` `+ wells…` popover) strips the well out of every other group first (the group being edited / created wins); a duplicate starts empty; `runtime_app._enforce_well_exclusivity()` runs at the top of `_groups_centre_refresh()` as a safety net + to clean up pre-existing overlaps in old saved data. The widget itself is still permissive (the round-trip via `_rebuild_all → _sync_selections_from_legacy → updateSelections` re-renders it with the exclusive state); a widget-level `setExclusiveWells` is unnecessary. |
| **"Add member rep-set R to group G"** (pick from an inventory of named rep-sets) | No analog in the model (rep-sets aren't objects anymore). Handled as a Stage-C host affordance ("＋ from another selection…") *or* not at all (you compose by editing wells directly). The widget extension doesn't try to express it. |
| **Arbitrary re-partitioning via chip drag-and-drop between sub-lists** | The hardest UI piece. **Deferred to a stretch goal.** The MVP covers it with per-chip menu items ("Move to new replicate", "Move to R1/R2/…") + `⊟ ungroup` + `⊞ group solo` — functionally complete, just less slick. If drag turns out to be easy on top of the existing chip layout, add it. |
| **Wrapping a large selection's chips** | Need a wrapping layout (or a per-row horizontal scroll strip). Low risk — `bar_group_panel_view` already does the single-line version; a `QScrollArea` strip is a safe fallback if a flow layout is fiddly. |
| **The plate popover reusing `WellPlateSelector`** | `WellPlateSelector` has no "compact" mode; the popover will be a decent-sized panel (~96 cells). Acceptable. If it's too big, the `setWellPlateFactory` hook lets the app substitute something smaller later. No blocker. |
| **Keyboard nav in the plate popover** | Stretch goal (depends on whether `WellPlateSelector` already does cell keyboard nav). MVP relies on mouse + the existing chip-level `×`/menu for a11y. |
| **Interaction with Phase-8.0's `_selections` live-mirror** | None — the widget mutates its own working list and emits; the *host* (Stage C) decides whether those edits go to the legacy shadow or to `_selections`. The widget extension is independent of where the app currently keeps state. |

**Nothing in §1 is *impossible* in the new design** — the only genuine loss is
the "named rep-set inventory" affordance, which is an artifact of the legacy
two-tier model and is replaced by direct `wells`/`replicates` editing (+ an
optional Stage-C "copy from another selection" shortcut). The exclusivity
behaviour change is the one item that needs an explicit decision.

---

## 6. Out of scope (for 6.5.12)

- Chip drag-and-drop (stretch).
- Plate-popover keyboard nav (stretch, depends on `WellPlateSelector`).
- Any host/app wiring (`views/grouping_view.py` swap, the rep-map-plate
  retargeting, the "copy from another selection" affordance) — that's Stage C.
- Renaming/recolouring/reordering — already covered by 6.5.8; unchanged.
- Touching `WellPlateSelector` itself (we use it as-is; if it lacks something we
  need, that's a separate note, not part of this build).

---

**Decision needed:** approve §2's UX, §3's API, and the §5 *exclusivity* call
(widget stays permissive — wells may live in multiple selections). On approval I
build it, demo it in the gallery, you runtime-test, then we proceed to Stage C.
