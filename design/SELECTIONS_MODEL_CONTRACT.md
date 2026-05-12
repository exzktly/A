# Selections-model contract (Phase 6.5.8a — gate)

The exact shape of the unified **`selections`** model that
`widgets.SavedSelectionsList` (Phase 6.5.8) reads and writes, and how the
Phase-8 migration of the legacy `_rep_sets` + `_bar_groups` + `_rep_hidden`
state maps onto it. The "stand-in model" the widget is built against in 6.5.8 **is
this contract** — not a throwaway — so the Phase-8 wiring drops in without
reshaping the widget.

**Status:** ✅ **approved** (user, 2026-05-12) — the five open questions below are
resolved (all per the recommendation). 6.5.8 (the editable `SavedSelectionsList`)
is built against this; the Phase-8 migration targets it.

References: `DESIGN_NOTES.md` §6.3 (the design intent), `well_viewer/batch_models.py`
(`ReplicateSet`, `BarGroup`), `well_viewer/sample_definitions.py` (the current
`pipeline_info.json::sample_definitions` schema), `well_viewer/selection_controller.py`
+ `runtime_app.py` (`app._rep_sets` / `app._rep_hidden` / `app._bar_groups` /
`app._bar_active_grp` / `app._well_labels` / `app._line_order_rsets` /
`app._line_order_wells`).

---

## 1. What it replaces

Today there are **two** panels backed by **two** structures:

- **Replicate sets** — `app._rep_sets: list[ReplicateSet]` where
  `ReplicateSet = {name: str, wells: [token, …]}` (no colour, no per-set hidden
  flag — visibility is `app._rep_hidden: set[int]`, a set of *indices* into the
  loaded rep-sets). One rep-set = "pool these wells as replicates of one
  condition".
- **Bar groups** — `app._bar_groups: list[BarGroup]` where
  `BarGroup = {name: str, members: [ReplicateSet, …], solo_wells: [token, …], hidden: bool}`.
  A group has a `.wells` property (dedup'd union of members' wells + `solo_wells`,
  insertion order) and `.replicate_sets()` → `[member.wells, …] + [[w] for w in solo_wells]`
  (the per-condition replicate partition the bar plot uses for "error band across
  replicates"). Colour is *positional* (`WELL_COLORS[group_index % len]`).
  `app._bar_active_grp: int` is the "current" group.

Plus `app._well_labels: dict[token, str]` (per-well display labels — *global*,
orthogonal to both panels) and `app._line_order_rsets` / `app._line_order_wells`
(user-saved draw orders).

§6.3: the two panels collapse into one **Saved selections** list; on load both
legacy lists merge into one `selections` array; bar-group order wins for
ordering; name conflicts append `_v2`.

---

## 2. The model

### 2.1 Container

```python
SelectionsModel = list[Selection]   # the array IS the bar-plot order (drag = reorder)
```

`well_labels` is **not** folded in — it stays a separate global `dict[token, str]`
(the Sample Definitions tab still edits it; the `selections` model doesn't own
"what does well A01 mean"). Each `Selection` may optionally carry per-selection
label overrides (§2.2 `labels`), but that's a v2 nicety, not required for
migration.

### 2.2 `Selection` (one row)

A plain `dict` (JSON-friendly; persisted in `pipeline_info.json`):

| Key | Type | Required | Meaning |
|---|---|---|---|
| `id` | `str` | yes | Opaque, unique within the array, **stable across save/load**, **never reused** even after delete. Recommended: `uuid4().hex[:8]` (a counter `"sel-1"…` works too if you persist `_next_id` — uuid avoids that). The widget keys per-row UI state and the chart keys colour memory off this. |
| `name` | `str` | yes | Display name; **unique within the array** (post conflict-resolution — see §3). Inline-renamable. |
| `color` | `str` `"#RRGGBB"` | yes | The colour dot in the list *and* the trace colour the chart uses for this selection ("plate is the legend" — `OPEN_DECISIONS.md` #1). No alpha in the stored value (alpha is a render-time concern). |
| `hidden` | `bool` | yes | Visibility on the chart. Hidden rows fade + strike-through + sink to the bottom *in the widget's display* — but their **stored array position is preserved** (so unhide restores their place; the bar plot iterates non-hidden entries in stored order). |
| `wells` | `list[str]` | yes | The wells this selection refers to, in display/draw order; tokens like `"A01"` (zero-padded, matching `app._well_paths` keys). **Not guaranteed to all exist in the current dataset** — wells absent from `app._well_paths` render greyed/disabled in the widget (same as the plate) and are filtered by plot code. May be empty (a freshly-created, not-yet-populated row). |
| `replicates` | `list[list[str]]` \| `None` | yes (may be `None`) | Optional partition of `wells` into replicate sub-bundles — the bar plot's "error band across replicates" uses these (one sub-list = one condition's replicates). `None` ⇒ "no explicit replicate structure" (Phase-8 plot code decides: today's behaviour is each well its own replicate). Each sub-list ⊆ `wells`; for *migrated* entries the union of sub-lists equals `wells` (it does — see §3); the model does **not** enforce full coverage (a well may be in `wells` but in no replicate). |
| `labels` | `dict[str, str]` \| `None` | no (default `None`/absent) | Optional per-well display-label overrides scoped to this selection. **Deferred** — v1 of the widget ignores it; persistence round-trips it untouched if present. The global `well_labels` remains the source of truth. |
| `source` | `"rep_set"` \| `"bar_group"` \| `"user"` \| `"import"` | no (default `"user"`) | Provenance, informational only: `bar_group`/`rep_set` = migrated; `user` = created via "From selection"; `import` = from CSV import. The widget may show a tiny provenance hint; nothing branches on it. |

Unknown keys are preserved on round-trip (forward-compat).

### 2.3 Invariants

1. Every `id` is non-empty and unique within the array; never reused.
2. Every `name` is non-empty and unique within the array.
3. `color` parses as `#RRGGBB` (6 hex digits, leading `#`).
4. `replicates` (if not `None`): every sub-list is non-empty and a subset of
   `wells`; sub-lists may overlap is **not** allowed (a well belongs to at most
   one replicate within a selection — they're a partition, not arbitrary sets);
   the union may be a proper subset of `wells`.
5. Array order is significant (= bar-plot order). `hidden` does not change a
   row's stored index.
6. `wells` order is significant (= the order traces/bars draw within the
   selection).

The widget *should* keep these true as the user edits; the host *must* keep them
true when it mutates the model directly (e.g. the migration).

---

## 3. Migration: `_rep_sets` + `_rep_hidden` + `_bar_groups` → `selections`

> **Note:** the *full, standalone* migration plan — real legacy shapes, all edge
> cases, the 20-file touch-site inventory, schema versioning, backup/recovery,
> failure handling, test plan, staged rollout — now lives in
> **`design/SELECTIONS_MIGRATION.md`** (Phase 8.0). §3–§5 below remain the
> normative *contract* (the shape & the algorithm's intent); the migration doc
> implements them.

Run once when a dataset loads, **only if** the persisted `sample_definitions`
block has no `selections` key (i.e. it's a legacy v1 block — see §4).

Order of emission (**bar-group order wins**):

1. **For each `BarGroup` `g` in `app._bar_groups`** (in order, index `gi`):
   emit `Selection`:
   - `id` = a freshly minted opaque id
   - `name` = `g.name` (conflict-resolved per §3-conflicts below)
   - `color` = `WELL_COLORS[gi % len(WELL_COLORS)]` — the colour the legacy bar
     plot showed for it; the user may recolour afterward
   - `hidden` = `g.hidden`
   - `wells` = `list(g.wells)` (the dedup'd union, insertion order — i.e.
     `BarGroup.wells`)
   - `replicates` = `g.replicate_sets()` → `[m.wells for m in g.members if m.wells] + [[w] for w in g.solo_wells]`
   - `source` = `"bar_group"`
2. **For each `ReplicateSet` `r` in `app._rep_sets` that is *not* a member of
   any bar group** ("free" rep-sets — those bound into a group are already
   represented by that group's `replicates`), in order, with running index `j`:
   emit `Selection`:
   - `id` = freshly minted
   - `name` = `r.name` (conflict-resolved — and since groups were emitted first,
     a free rep-set whose name collides with a group's name gets `_v2`, exactly
     per §6.3)
   - `color` = `WELL_COLORS[(len(app._bar_groups) + j) % len(WELL_COLORS)]`
   - `hidden` = `(legacy_rep_index_of(r) in app._rep_hidden)` — i.e. it was
     hidden via the plate's rep-mode
   - `wells` = `list(r.wells)`
   - `replicates` = `[list(r.wells)]` (a free rep-set is one condition with N
     replicates)
   - `source` = `"rep_set"`

**Membership test for "free" rep-sets.** A `ReplicateSet` object is "a member of
a group" iff it's identity-present in some `g.members`. (Legacy `BarGroup.members`
holds the actual `ReplicateSet` instances, so `any(r is m for g in groups for m in g.members)`.)

**Name conflicts.** When an entry's `name` is already taken in the array being
built: append `"_v2"`; if `"<name>_v2"` is also taken, `"<name>_v2 2"`,
`"<name>_v2 3"`, … (per §6.3's "_v2", extended deterministically). Bar groups are
emitted first, so they keep their names; free rep-sets yield.

**Draw order.** The migrated array's order is bar-groups-then-free-rep-sets as
above. If `app._line_order_rsets` / `app._line_order_wells` are non-empty (a
user-saved line-graph order), the migration *may* additionally reorder the
migrated selections to honour them (best-effort: stable-sort the array so
selections appear in the saved order, unknowns last). This is a refinement, not
required for v1; the bar-group order is the canonical baseline.

**`well_labels`.** Copied through unchanged into the container; **not** moved
into any `Selection`.

**`app._bar_active_grp`.** Maps to "which selection is the *current* one" — the
widget's `currentId`. On migration, `currentId` = the id of the selection that
came from `app._bar_groups[app._bar_active_grp]` (or the first selection if that
group was filtered out / there were no groups).

**What the migration does *not* do:** it doesn't drop or merge selections with
identical well-sets, doesn't validate `wells` against the current dataset (stored
wells may not exist — see §2.2), and doesn't write colours that depend on the
loaded data. It's a pure structural transform; the result is persisted (§4) so
subsequent loads skip it.

---

## 4. Persistence

The unified block lives where `sample_definitions` already lives — under the
`sample_definitions` key in `pipeline_info.json` (and the standalone
`bar_groups.json` loader, if kept, reads/writes the same shape). New schema:

```jsonc
"sample_definitions": {
  "schema_version": 2,                      // NEW — absence ⇒ legacy v1 ⇒ migrate on load
  "well_labels":  { "A01": "Treated 0nM", "B05": "Control", ... },   // unchanged, global
  "selections": [
    {
      "id": "a1b2c3d4",
      "name": "Drug A — 10µM",
      "color": "#5B9BF8",
      "hidden": false,
      "wells": ["A01", "A02", "A03", "B05"],
      "replicates": [["A01", "A02", "A03"], ["B05"]],
      "source": "bar_group"
      // "labels": {...}   // optional, omitted when absent
    },
    ...
  ],
  "current_id": "a1b2c3d4",                  // optional — the widget's "current" selection
  "notes": ""                                // unchanged
}
```

Load logic:
- `schema_version == 2` (or `selections` key present) → load `selections` /
  `well_labels` / `current_id` directly; rebuild the in-memory `app` state from
  it (the inverse map — see §5).
- else (legacy: `rep_sets` / `groups` keys, no `schema_version`) → hydrate the
  legacy in-memory state as today **and then** run §3 to produce `selections`;
  set `schema_version = 2`; write back on next save.

`bar_groups.json` (the standalone loader) gets the same treatment. The legacy
`rep_sets` / `groups` keys are *removed* on the next save once a v2 block is
written (no dual-maintenance).

---

## 5. Phase-8 wiring (the inverse map — for reference, not built in 6.5)

When Phase 8 wires `SavedSelectionsList` into the app, it bridges the model
both ways:

- **Model → app state.** Maintain `app._selections: list[dict]` (this model) as
  the source of truth. Derive the legacy-shaped views the renderers still want
  *from* it: `_bar_groups`-equivalent iteration = non-hidden selections in array
  order, each yielding `replicates` (or `[[w] for w in wells]` if `replicates is
  None`); `_rep_hidden`/`_rep_sets` rep-mode on the plate = the selections, with
  `hidden` = the muted state and clicking a well toggling the owning selection's
  `hidden`; `_well_labels` stays separate. The line/CDF/scatter renderers'
  per-trace iteration = each selection's `wells` (pooled) coloured by the
  selection's `color`. The bar plot's per-condition error band = each
  selection's `replicates`.
- **App → model.** "From selection" → append a `Selection` with `wells` = the
  current plate selection, `replicates = None`, `source = "user"`, a minted id,
  the next colour in the cycle, a default name (`"Selection N"`), unhidden.
  "Import…" (CSV) → parse rows → one or more `Selection`s with `source = "import"`.
- The plate-map colour fix from `OPEN_DECISIONS.md` #1 reads the selection
  colours (and the per-well-rank palette for the *unstructured* selected-wells
  case) — same palette the chart uses, by construction.

(All of §5 is Phase-8 app work, listed here so the contract makes the
round-trip obligations explicit. None of it is built in Phase 6.5.)

---

## 6. What `widgets.SavedSelectionsList` does with this model (6.5.8)

- `setSelections(list[dict])` / `selections() -> list[dict]` — the widget holds a
  working list; `setSelections` replaces it and rebuilds the view.
- `setCurrentId(id)` / `currentId() -> str`.
- The widget mutates its working list in response to user actions and emits, per
  action: `entryActivated(id)`, `entryRenamed(id, name)`, `entryRecoloured(id, color)`,
  `entryVisibilityToggled(id, hidden)`, `entryDuplicated(new_id, src_id)`,
  `entryDeleted(id)`, `entryExportRequested(id)`, `orderChanged([id, …])`,
  `addFromSelectionRequested()`, `importRequested()` — **and** a coarse
  `selectionsChanged(list)` after any of the above (the host can use the granular
  signals to react to a specific action, or just take the whole list). The widget
  enforces §2.3 (unique id/name with `_v2` on collision, `#RRGGBB` colour, hidden
  sinks-in-display-only) for changes it originates.
- Rendering per row: drag handle · visibility eye (toggles `hidden`) · colour dot
  (opens recolour via `ColorSwatchRow` → `entryRecoloured`) · inline-renamable
  name · count chip (`len(wells)`) · kebab (`Popover`/`QMenu`: Rename / Recolour /
  Duplicate / Hide / Move up-down / Export / Delete). Expand a row → a `ChipGroup`
  of the selection's well chips (read-only in v1; editing well membership from
  here is deferred). Footer: `From selection` button (→ `addFromSelectionRequested`)
  and `Import…` button (→ `importRequested`). Hidden rows fade + strike-through and
  sort to the bottom of the *displayed* order.
- For the 6.5.8 gallery card, the widget is fed a hand-built `list[dict]`
  conforming to this contract (a few entries, some with `replicates`, one
  `hidden`); no app state is touched.

---

## Resolved (approved 2026-05-12)

1. **`id` scheme** → **`uuid4().hex[:8]`** (opaque, unique, stable; no persisted
   counter). On collision (vanishingly unlikely) re-mint.
2. **`replicates` for free rep-sets** → **`[wells]`** (one condition with N
   replicates — preserves the legacy "pooled-replicate condition" intent).
   `None` only for brand-new "From selection" / imported entries with no stated
   rep structure.
3. **`labels` (per-selection label overrides)** → **kept in the schema as a
   reserved, ignored-in-v1 field** (round-tripped untouched; the global
   `well_labels` stays the source of truth).
4. **Conflict suffix** → **`"_v2"`, then `"_v2 2"`, `"_v2 3"`, …** (per §6.3's
   literal `_v2`, extended deterministically).
5. **`current_id`** → **persisted** in the `sample_definitions` block (reopening
   a file restores the "current" selection; falls back to the first non-hidden
   entry if the stored id is absent).
