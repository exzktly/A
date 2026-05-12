# Phase 8.0 — Saved-selections data-model migration plan

> **Status:** approved 2026-05-12 (Q1 migrate `bar_groups.json`; Q2 bake rank
> colour immediately; Q3 drop the legacy shadow at phase end; Q4 implement §3.5
> now). **Stage A is implemented** (see *Progress* at the bottom); Stages B–D
> not started. This doc promotes `SELECTIONS_MODEL_CONTRACT.md` §3–§5 (which
> only *sketched* the migration) into a complete, standalone plan: real legacy
> shapes, the algorithm with edge cases, the full 20-file touch-site inventory,
> schema versioning, backup/recovery, failure handling, a test plan, and a
> staged rollout.

**Honesty note (answering the question asked):** when I wrote contract §3–§5 I
**inferred** the `_rep_sets` / `_bar_groups` shapes from the *class definitions*
(`well_viewer/batch_models.py`) and the *(de)serialization* code
(`well_viewer/sample_definitions.py`, `well_viewer/barplot_controller.py`) — **not**
from a real saved `pipeline_info.json` or a test fixture, because the repo has
**no test fixtures and no sample data files** (`find` for `*pipeline_info*`,
`*fixture*`, `tests/` ⇒ nothing). The shapes below are therefore "what the code
constructs/reads", which is authoritative for *structure* but cannot show me what
*real user data* looks like (odd well tokens, very long names, empty rep-sets,
groups referencing deleted rep-sets, …). **Risk:** the migration must be defensive
about exactly those edge cases the contract may not have anticipated — §3's
"malformed records" handling is load-bearing, not a nicety. Before this lands,
running the migration against ≥1 real saved dataset (you have those) is part of
the test plan (T6 below).

---

## 1. Current data shapes (extracted from the codebase)

### 1.1 In-memory state (on `WellViewerApp` / `AllWellApp`)

From `well_viewer/runtime_app.py` (`__init__`, lines ~765–770) and `batch_models.py`:

```python
self._rep_sets:       List[ReplicateSet] = []     # all user-defined replicate sets
self._active_rep_idx: int                = -1     # index into _rep_sets of the "current" one (-1 = none)
self._rep_hidden:     set[int]           = set()  # indices into _rep_sets_loaded() (NOT _rep_sets!) that are hidden on plots
self._bar_groups:     List[BarGroup]     = []     # bar-plot groups
self._bar_active_grp: int                = -1     # index into _bar_groups of the "current" group (-1 = none)
```

`ReplicateSet` (`batch_models.py`): a plain object — `.name: str`, `.wells: list[str]` (well tokens like `"A01"`, zero-padded). No id, no colour, no hidden flag.

`BarGroup` (`batch_models.py`): `.name: str`, `.members: list[ReplicateSet]` (the *actual* ReplicateSet instances, often the same objects that are in `_rep_sets`), `.solo_wells: list[str]`, `.hidden: bool`. Derived: `.wells` (dedup'd union of members' wells then solo_wells, insertion order), `.replicate_sets() -> list[list[str]]` (`[m.wells for m in members if m.wells] + [[w] for w in solo_wells]`).

**Key invariant the code relies on, not obvious from the contract:**
`_rep_hidden` indexes into the **filtered, ordered** list `_rep_sets_loaded()`
(= `[r for r in _rep_sets if any(w in app._well_paths for w in r.wells)]`), *not*
into `_rep_sets`. `_rep_sets_active()` = `[r for i,r in enumerate(_rep_sets_loaded()) if i not in _rep_hidden]` — that's "what appears on plots". So a rep-set with **no currently-loaded wells** isn't in `_rep_sets_loaded()`, can't be hidden, and never plots. The migration's `hidden` flag must be computed against `_rep_sets_loaded()` order, and rep-sets with no loaded wells migrate with `hidden=False`.

### 1.2 Persisted shape (`pipeline_info.json` → key `"sample_definitions"`)

From `well_viewer/sample_definitions.py` (`build_sample_definitions`) and
`barplot_controller.bar_groups_to_dict` / `bar_groups_from_data`:

```jsonc
{
  "sample_definitions": {
    "well_labels": { "A01": "Treated 0nM", "B05": "Control", "...": "..." },
    "rep_sets": [
      { "name": "Rep 1", "wells": ["A01", "A02", "A03"] },
      { "name": "Rep 2", "wells": ["B01", "B02", "B03"] }
    ],
    "groups": [
      { "name": "Control", "hidden": false, "members": ["Rep 1"], "solo_wells": ["B05"] },
      { "name": "Drug A",  "hidden": true,  "members": ["Rep 2"], "solo_wells": [] }
    ],
    "notes": "free-form text"
  }
}
```

- `groups[*].members` is a list of **rep-set names** (string FKs into `rep_sets[*].name`), resolved on load by `bar_groups_from_data` (`rep_by_name = {r.name: r for r in rep_sets}`). Names not found are silently dropped.
- On load, well tokens are normalised (`^([A-H])(\d{1,2})$` → `A01`) and filtered to `tok_to_label` (loaded wells); unknown tokens are dropped.
- **No `schema_version` key exists today** anywhere in the file (the pipeline writes other keys — `schema`, `fov_index`, `fluor_tokens`, … — which the saver preserves verbatim; none is a version of *this* block).
- A second, standalone `bar_groups.json` file (`well_viewer/persistence/bar_groups.py`) uses the **same** `{"rep_sets": [...], "groups": [...]}` payload shape (`to_dict` / `bar_groups_from_data`). It has **no `well_labels`/`notes`**. The migration must handle this file too (or explicitly leave it legacy — see §5/§9-Q).
- `_rep_hidden` is **not persisted** at all today. So a reload always comes back with everything visible. (Implication: migrating `hidden` from `_rep_hidden` only matters for an *in-session* migration; a *from-disk* migration has no `_rep_hidden` to read and migrates `hidden=False` for all rep-set-derived entries.)
- Colours are **not persisted and not stored anywhere** — they're purely positional at render time: `WELL_COLORS[idx % len(WELL_COLORS)]` (`WELL_COLORS` from `well_viewer/plate_layout.py`). Bar-group colour = `WELL_COLORS[group_index % len]`; free rep-set colour = `WELL_COLORS[rep_index % len]`. **There is no concept of a per-selection colour today** — introducing one (and making the plate the legend, OPEN_DECISIONS #1) is part of this migration.

### 1.3 What I could NOT verify (no fixtures)

Real values of: well-token formatting variants users may have hand-edited; whether any real save has a group whose `members` references a non-existent rep-set name; whether `solo_wells` is ever non-empty in the wild; whether names ever collide in a real save; how large `notes` gets. **All handled defensively below; T6 closes the gap.**

---

## 2. Target shape

The target is **exactly** `SELECTIONS_MODEL_CONTRACT.md` §2 — `selections: list[dict]`, each
`{ id, name, color, hidden, wells, replicates, labels?, source? }`, plus a separate
global `well_labels: dict[token,str]`. See the contract for field semantics and
the §2.3 invariants. Not re-specified here.

### 2.1 Drift check — contract vs. what `widgets.SavedSelectionsList` actually consumes

I diffed the 6.5.8 widget (`widgets/saved_selections_list.py`) against contract §2/§6:

| Aspect | Contract | Widget (as built) | Verdict |
|---|---|---|---|
| Per-row dict keys read | `id, name, color, hidden, wells, replicates, labels?, source?` | reads `id, name, color, hidden, wells` (count chip = `len(wells)`); `replicates`/`labels`/`source` round-tripped untouched (`source` only used for a not-yet-shown provenance hint) | ✅ consistent — widget reads a subset, preserves the rest |
| `color` format | `"#RRGGBB"`, no alpha | `_hex6()` normalises anything to `#RRGGBB` on `setSelections` | ✅ |
| id scheme | `uuid4().hex[:8]`, unique, re-mint on collision | `_ensure_unique` re-mints empty/dup ids with `uuid4().hex[:8]` | ✅ |
| name uniqueness | unique, `_v2` then `_v2 2`, … on collision | `_unique_name` does exactly that | ✅ |
| ordering | array order = bar-plot order; hidden keeps stored index, only sinks in *display* | widget keeps `self._selections` in stored order; `_display_order()` floats hidden to the bottom for rendering only; `orderChanged` emits stored-order ids | ✅ |
| current selection | `currentId` (opaque id) | `setCurrentId`/`currentId` | ✅ |
| signals | the §6 list | all present (`entryActivated/Renamed/Recoloured/VisibilityToggled/Duplicated/Deleted/ExportRequested/orderChanged/addFromSelectionRequested/importRequested` + coarse `selectionsChanged`) | ✅ |
| `replicates` for migrated free rep-set | `[wells]` (one condition, N reps) | widget doesn't care (round-trips) — the *migration* must produce this | n/a to widget; **migration responsibility** |

**Conclusion: no drift.** The widget is a faithful, slightly-narrower consumer of
the contract shape. One thing the widget does *not* yet surface: per-well `labels`
overrides (deferred, contract §2.2) and a visible `source` hint — both fine.

**One small contract clarification this plan adds:** the contract says the
container "also keeps a separate global `well_labels`". Today `well_labels` lives
on `app._well_labels` and is persisted under `sample_definitions.well_labels`. The
migration **does not move it** — it stays exactly where it is; `selections` is a
*sibling* key. (Stated in the contract; making it explicit here so the touch-site
inventory doesn't accidentally touch `_well_labels`.)

---

## 3. Migration algorithm

Input: a legacy `sample_definitions` block (or the in-memory `_rep_sets` /
`_bar_groups` / `_rep_hidden` / `_bar_active_grp`). Output: `(selections: list[dict],
current_id: str | None, well_labels: dict, notes: str)`.

**Pure structural transform** — no dependency on the loaded dataset, no colour
that depends on data, no merging/dedup of identical well-sets, no validation of
wells against `_well_paths` (stored wells may legitimately not exist; consumers
already filter).

### 3.1 Steps (bar-group order wins)

```
WELL_COLORS = well_viewer.plate_layout.WELL_COLORS   # the existing positional palette
selections = []
used_names = set()                                   # for _v2 conflict resolution
rep_set_objs_in_groups = set of id(r) for every r that is .members of any group   # identity, not name

# (1) bar groups, in order
for gi, g in enumerate(bar_groups):
    sel = {
      "id":         mint_id(),                                   # uuid4().hex[:8], unique
      "name":       unique_name(g.name or f"Group {gi+1}", used_names),
      "color":      WELL_COLORS[gi % len(WELL_COLORS)],          # what the legacy bar plot showed
      "hidden":     bool(g.hidden),
      "wells":      list(g.wells),                                # the dedup'd union (BarGroup.wells)
      "replicates": g.replicate_sets() or None,                   # [m.wells for m in members if m.wells] + [[w] for w in solo_wells]; None if empty
      "source":     "bar_group",
    }
    used_names.add(sel["name"]); selections.append(sel)

# (2) "free" rep-sets — those NOT bound into any group (identity test against rep_set_objs_in_groups)
loaded_order = rep_sets_loaded()      # = [r for r in rep_sets if any(w in well_paths for w in r.wells)]  — only meaningful for an in-session migration
free = [r for r in rep_sets if id(r) not in rep_set_objs_in_groups]
for j, r in enumerate(free):
    # hidden: only knowable in-session; from disk there's no _rep_hidden ⇒ False
    hidden = (in_session and (index_of(r) in rep_hidden_translated_to_loaded_order))
    sel = {
      "id":         mint_id(),
      "name":       unique_name(r.name or f"Rep {j+1}", used_names),   # groups emitted first ⇒ a colliding free rep-set yields, gets _v2
      "color":      WELL_COLORS[(len(bar_groups) + j) % len(WELL_COLORS)],
      "hidden":     bool(hidden),
      "wells":      list(r.wells),
      "replicates": [list(r.wells)] if r.wells else None,         # one condition with N replicates (contract §6.2)
      "source":     "rep_set",
    }
    used_names.add(sel["name"]); selections.append(sel)

# (3) current
current_id = (selections[bar_active_grp]["id"] if 0 <= bar_active_grp < len(bar_groups)
              else (selections[0]["id"] if selections else None))

# (4) decision-#1 colour (OPEN_DECISIONS #1) — see 3.4
# (5) optional: honour a saved line-graph order — see 3.5
```

`unique_name(name, used)`: `name.strip() or "Selection"`; if free, return it; else
`f"{name}_v2"`; if that's taken, `f"{name}_v2 2"`, `"_v2 3"`, … — the exact
algorithm `SavedSelectionsList._unique_name` uses, so the widget never has to
re-resolve a name the migration produced.

`mint_id()`: `uuid4().hex[:8]`; re-mint while it collides with an already-emitted id.

### 3.2 Edge cases

| Case | Handling |
|---|---|
| `bar_groups == []` **and** `rep_sets == []` | `selections = []`, `current_id = None`. Valid empty model. Persist it (so the file gets `schema_version: 2` and won't re-migrate). |
| `rep_sets == []` but `bar_groups != []` | groups migrate normally; no free rep-sets. (A group with empty `members` *and* empty `solo_wells` ⇒ `wells=[]`, `replicates=None` — kept, not dropped.) |
| group's `members` references a rep-set name that doesn't exist | already dropped at *load* time by `bar_groups_from_data`; by migration time `g.members` only holds resolved objects, so nothing extra to do. **But** if migrating directly from a raw JSON block (not via the loader), resolve names the same way the loader does and drop unresolved ones (log a warning per dropped name). |
| same rep-set object in **two** groups | each group's `replicates` includes it (matches legacy behaviour); the rep-set is "in a group" (identity test) ⇒ it is **not** also emitted as a free selection. |
| two groups (or two free rep-sets, or a group and a rep-set) with the **same name** | groups emitted first keep their names; later collisions get `_v2` (then `_v2 2`, …). Order within "groups" is the `bar_groups` order; within "free rep-sets" the `rep_sets` order. |
| empty `name` | `f"Group {gi+1}"` / `f"Rep {j+1}"`, then run through `unique_name`. |
| `wells` contains an un-normalised / unknown token | the loader already normalises+filters on read; migration keeps whatever is in `r.wells` verbatim (it's already been through the loader). For a raw-JSON migration path, normalise (`^([A-H])(\d{1,2})$` → `A01`) but **do not** filter against `_well_paths` (stored ≠ loaded is allowed). |
| `solo_wells` non-empty | folded into `g.wells` (already, via `BarGroup.wells`) and each becomes its own `[w]` sub-list in `replicates` (already, via `replicate_sets()`). |
| partial overlap: a well in `wells` but in no `replicates` sub-list | allowed by contract §2.3 inv. 4 (union may be a proper subset of `wells`); migration does nothing special. (This *can* happen for a group: `BarGroup.wells` includes `solo_wells`, and `replicate_sets()` also includes them as `[w]`, so for migrated groups the union actually equals `wells` — but the model doesn't require it.) |
| overlapping `replicates` sub-lists (a well in two sub-lists) | contract §2.3 inv. 4 forbids it. Legacy `replicate_sets()` *can* produce this if two `members` share a well. Migration: **de-overlap** — for each well, keep it only in its first sub-list (stable); drop now-empty sub-lists. Log a warning when it happens. |
| `bar_active_grp` out of range / `-1` | `current_id` = first selection's id, or `None` if empty. |
| `notes` missing / non-string | `""`. |
| `well_labels` missing / not a dict / values blank | filtered to `{tok: str(v).strip() for tok,v in ... if str(v).strip()}` (the existing `parse_well_labels` behaviour, minus the loaded-token filter — at migration time keep all non-blank labels; the *display* code already filters to loaded tokens). |
| the file already has `sample_definitions.selections` / `schema_version >= 2` | **do not migrate** — read it as-is (after a light validate/repair pass: re-mint empty/dup ids, re-resolve name collisions, coerce `color` to `#RRGGBB`, default missing `hidden`/`wells`/`replicates`/`source`). |
| the file has `sample_definitions` but it's not a dict / is `null` | treat as "no block" — `selections = []`. |
| no `pipeline_info.json` at all | nothing to migrate; in-session migration only (or no-op). |
| standalone `bar_groups.json` present | see §5 / §9-Q — decision needed; default plan: migrate it on load the same way (it has no `well_labels`/`notes`). |

### 3.3 Determinism

Given the same inputs, the output `selections` list (and the name-resolution) is
identical every run **except** for `id`s (uuid4). For testing, the migration takes
an optional `id_factory` (default `lambda: uuid4().hex[:8]`) so tests can inject a
deterministic counter.

### 3.4 Decision-#1 colour (OPEN_DECISIONS #1, "the plate is the legend")

Separate, small follow-on (the contract calls it Phase-8, ~1 line in
`_refresh_sidebar_map_now`): once `selections` exists, **colour by well-position
rank** — i.e. the sidebar plate colours each well by the rank of its
(row,col) position, and a selection's `color` is derived from its first well's
rank (so a selection and its replicate-set members all render in the same
colour everywhere). The *migration* writes the **positional `WELL_COLORS`** value
as a starting point (so nothing changes visually on first load); the colour-by-rank
rule is applied at render time and can also be "baked" into `selections[*].color`
by a one-time pass after migration (and re-baked whenever the user reorders).
**This plan does not implement the render-time rule** — it just makes sure the
migration leaves `color` populated and the contract's invariant (`#RRGGBB`) holds.
Implementing colour-by-rank is the first item of the *post-migration* Phase-8 work,
not Phase 8.0.

### 3.5 Optional: honour a saved line-graph order

If `app._line_order_rsets` / `app._line_order_wells` are non-empty (a user-saved
order, persisted separately), stable-sort the migrated `selections` so they appear
in that order, unknowns last. **Best-effort, off by default** in v1 (bar-group
order is canonical); a flag `respect_line_order=False` on the migration fn.

---

## 4. Schema versioning

- Add `"schema_version": 2` **inside** the `sample_definitions` block (not at the
  top level of `pipeline_info.json` — that file's top level is pipeline-owned).
  v1 = "no `schema_version` key, has `rep_sets`/`groups`" (today's shape). v2 =
  "`schema_version: 2`, has `selections`" (no `rep_sets`/`groups` keys — they're
  dropped on write).
- **On-load trigger:** migrate iff `block.get("schema_version", 1) < 2` (covers
  both "absent" and a future bump). When migrating, also handle the degenerate
  "v1 block that already happens to have a `selections` key" (shouldn't exist —
  treat `selections` as authoritative if present and well-formed, else migrate
  from `rep_sets`/`groups`).
- **On write:** always write `schema_version: 2` and `selections`; never write
  `rep_sets`/`groups` (a v2 writer drops them). Preserve all other
  `sample_definitions` keys (`well_labels`, `notes`, `labels` if any) and all
  other `pipeline_info.json` keys verbatim, exactly as `save_to_pipeline_info`
  does today.
- **Forward-compat:** unknown keys inside a `Selection` and inside the block are
  preserved on round-trip. A future v3 reader sees `schema_version: 2` and knows
  the shape.
- The standalone `bar_groups.json` gets the same treatment **iff** we decide to
  keep supporting it (§9-Q): a `schema_version`/`selections` payload, migrated on
  load. Default plan: yes, mirror it.

---

## 5. Backup mechanism & recovery

Before the **first** write that drops the legacy keys (i.e. the first save after a
migrated load, *or* an explicit "migrate now"), copy the pre-migration file:

- `pipeline_info.json` → `pipeline_info.json.pre-v2-backup` (in the same dir).
  If that name exists, **don't overwrite it** (the first backup is the precious
  one) — fall back to `pipeline_info.json.pre-v2-backup.<UTC-timestamp>`.
- Same for `bar_groups.json` → `bar_groups.json.pre-v2-backup` if we migrate it.
- The backup is the *raw bytes* of the old file (a straight copy), not a
  re-serialization — so it's byte-for-byte restorable.
- Log at INFO: `"sample_definitions: migrated v1→v2; backup written to <path>"`.

**Recovery procedure (documented in this file + a one-line hint in the app log):**
1. Close All-Well.
2. `mv pipeline_info.json.pre-v2-backup pipeline_info.json` (overwriting the
   migrated one). If you used a timestamped backup, pick the oldest.
3. Re-open the data folder. You're back on the v1 shape. *(Note: a v1-shaped file
   re-opened by a v2-aware build will migrate again on load — but it won't
   *persist* the migration until you Save, so you can keep working v1-ish and just
   not Save, or stay on the pre-migration build.)*
4. If you also have a `bar_groups.json.pre-v2-backup`, restore it the same way.

---

## 6. Failure handling

Migration runs inside a `try/except` that **never** crashes the app:

- **Read error / malformed block** → log a WARNING, treat as "no block" (empty
  `selections`); the app continues with whatever state it had. Do **not** write
  anything (so the bad file is left untouched for the user to inspect).
- **Migration raises mid-transform** (a truly unexpected input) → log the
  exception with the offending block (truncated), keep the **legacy** in-memory
  state (`_rep_sets`/`_bar_groups` unchanged — see rollout §7: legacy state is
  still populated in parallel during the staged phases), show a non-modal warning
  (status-bar message or a small banner): *"Couldn't upgrade saved sample
  definitions — using them in compatibility mode. See log; a backup was not
  written."* — and **disable v2 writes for this session** (so a half-baked model
  never gets persisted).
- **Backup write fails** (disk full, permissions) → **abort the v2 write**, keep
  the file on v1, log an ERROR, status message: *"Can't save: unable to write a
  pre-upgrade backup of pipeline_info.json."* Better to refuse to save than to
  destroy the only copy of the old data.
- **Post-migration validate/repair** of an already-v2 file that's slightly off
  (dup id, bad colour) → repair in memory, log INFO; the repaired version is what
  gets written on the next Save.
- Partial in-memory state is never exposed: the migration builds the new
  `selections` list fully *then* assigns it (no incremental mutation of live
  state).

---

## 7. Rollout strategy — **staged** (recommended)

A single mega-commit that flips 20 files at once is high-risk and unreviewable.
Staged, each step independently shippable & testable:

**Stage A — model + migration + persistence, no consumers switched.**
- Add `well_viewer/selections_model.py`: the `Selection` shape helpers,
  `migrate_legacy(block_or_appstate, *, id_factory=...) -> (selections, current_id, well_labels, notes)`,
  `validate_repair(selections) -> selections`, and `to_block(selections, well_labels, notes) -> dict` / `from_block(block) -> (...)` (the v2 (de)serializer with `schema_version: 2`).
- Wire it into `well_viewer/persistence/sample_definitions.py` **read path only**:
  on load, build `app._selections` / `app._current_selection_id` *in parallel*
  with the existing `_rep_sets`/`_bar_groups` (which are then derived from
  `_selections` via an inverse map — contract §5 — so both representations are
  consistent and every existing consumer keeps working untouched). Backup +
  `schema_version: 2` write happen on the next Save.
- Add `bar_groups.json` handling (or defer per §9-Q).
- Ship. **Nothing visible changes**; the model now exists and round-trips.
- Tests T1–T6 (below) all run against Stage A.

**Stage B — switch consumers, one cluster per commit**, each keeping the
`_rep_sets`/`_bar_groups` shadow in sync (so a half-migrated tree still works):
1. `runtime_app.py` helpers (`_rep_sets_active/_loaded`, `_groups_from_rep_sets`,
   `_replicate_display_label`, `_bar_groups_prune`) → derive from `_selections`.
2. `barplot_*` (`barplot_controller.collect_bar_items`, `barplot_renderer`) — the
   biggest behavioural risk; do alone, screenshot bar plots before/after.
3. `lineplot_controller`, `heatmap_controller`, `scatter_controller`,
   `stats_controller`, `export_service`, `cell_gating_tab`, `data_loading` —
   read-only consumers, mostly mechanical.
4. `selection_controller` + `grouping_controller` — these *write* the legacy state
   (plate drags, group create/rename/hide/delete); switch them to mutate
   `_selections` and emit the same UI refreshes.
5. `batch_export/base_panel.py` + `batch_export/scatter_panel.py` — they
   temporarily swap `self._app._rep_sets` to render per-group; rework to pass a
   selection subset instead.

**Stage C — views → `SavedSelectionsList` integration.**
- `views/grouping_view.py` + `views/bar_group_panel_view.py`: replace the
  hand-rolled rep-set / group list widgets with `widgets.SavedSelectionsList` bound
  to `app._selections` (wire its `entry*` / `orderChanged` / `selectionsChanged`
  signals to the same handlers). `views/export_style_sidebar_view.py` only reads
  `_rep_sets_active()` — switch to the derived accessor; no widget swap.
- Decision-#1 colour-by-rank in `_refresh_sidebar_map_now` lands here.

**Stage D — remove the shadow.** Once every consumer reads `_selections`, delete
`_rep_sets`/`_bar_groups`/`_rep_hidden`/`_active_rep_idx`/`_bar_active_grp` and the
inverse-map sync. Final cleanup commit.

Each stage: `py_compile` here + your runtime QA (and for Stage B-2 / Stage C, a
screenshot diff). The plan, the contract, and `WELL_SELECTOR_GAP.md` get progress
notes as stages land.

---

## 8. Touch-site inventory (the 20 files)

Classification: **P** = persistence (migration code lives here / nearby) · **C** =
consumer/controller (gets an adapter or rewrite) · **V** = view (replaced by /
integrated with `SavedSelectionsList`) · **O** = other/data/service. "Shadow-OK"
means: during Stages A–C this file keeps working unchanged because `_rep_sets`/
`_bar_groups` are kept in sync from `_selections`; it only *needs* changes when we
get to it in Stage B/C.

| # | File | Class | Refs / functions that touch the legacy state | What changes |
|---|---|---|---|---|
| 1 | `well_viewer/runtime_app.py` | C (core) | `__init__` (declares `_rep_sets/_active_rep_idx/_rep_hidden/_bar_groups/_bar_active_grp`, ~765–770); `_rep_sets_loaded` (~5755), `_rep_sets_active` (~5776), `_groups_from_rep_sets` (~5760), `_replicate_display_label` (~5727), `_bar_groups_prune` (~2346); rep-set create/rename/delete/clear dialogs (~1609–1690), group create/clear (~1897, ~2024, ~2032), `_refresh_sidebar_map_now` (~1546–1559: positional `WELL_COLORS`), draw helpers (~3154, ~3186, ~3236), KS-CDF (~1267), `_redraw_line_plots`/exports (~5779); `_bar_active_grp` reads throughout | Add `_selections`/`_current_selection_id`; rewrite the helper accessors to derive from `_selections`; the create/rename/delete/clear paths mutate `_selections`; `_refresh_sidebar_map_now` gets the colour-by-rank rule (decision #1). Stage B-1 + B-4 + C. |
| 2 | `well_viewer/selection_controller.py` | C | `sb_press/sb_drag/sb_release` & row/col handlers & "select all/none reps" (~66–223): every `app._rep_hidden.add/discard/clear`, `app._rep_sets_loaded()`, `if app._rep_sets:` branch | The plate's rep-mode show/hide toggling now flips `selections[i]["hidden"]` (translating loaded-order ↔ stored-order); the "is there a rep-set layer" check becomes "are there `source in {rep_set,bar_group}` selections". Stage B-4. |
| 3 | `well_viewer/barplot_controller.py` | C | `collect_bar_items` (~77) & the dist variant (~148): `app._rep_sets_active()` | Switch to the derived `_rep_sets_active()` accessor (no signature change). Trivial once #1's helper is rewritten. Stage B-1/B-2. |
| 4 | `well_viewer/barplot_renderer.py` | C (high-risk) | `~249–301`: `getattr(app, "_rep_sets", [])`, the name→index→`WELL_COLORS` colour map, `well_colors=WELL_COLORS`; `_rep_sets_active()` (~350) | Colour now comes from `selection["color"]` (which after decision #1 is the rank colour) instead of `WELL_COLORS[name_index % len]`. **Do this commit alone**, screenshot bar plots. Stage B-2. |
| 5 | `well_viewer/grouping_controller.py` | C | `_has_active_group`/`_has_active_rep` (~17–21), group/rep mutators: create/rename/delete/hide/move/clear (~31–164), `_rep_sets = new_sets` rebuild (~249–262), `_bar_groups.clear()` (~290) | All group/rep CRUD now operates on `_selections` (a group's "members" become the selection's `replicates`; "hidden" the `hidden` flag; "active" the `current_id`). Stage B-4. |
| 6 | `well_viewer/lineplot_controller.py` | C | `~72,79`: `app._rep_sets_active()`; `~92`: `getattr(app, "_rep_sets", [])` for the CDF "all rep sets" path | Use the derived accessor + iterate `_selections` for the all-sets case. Stage B-3. |
| 7 | `well_viewer/heatmap_controller.py` | C | `~83,111`: `list(getattr(app, "_rep_sets", []))` | Iterate `_selections` (filter to `source in {rep_set,bar_group}` or just use all). Stage B-3. |
| 8 | `well_viewer/scatter_controller.py` | C | `~107,187,337,454`: `app._rep_sets_active()` (4×) | Derived accessor; mechanical. Stage B-3. |
| 9 | `well_viewer/stats_controller.py` | C | `~344`: `next((r for r in app._rep_sets if tok in r.wells), …)`; `~367,400`: `WELL_COLORS[gi % len]`; `~476`: `app._groups_from_rep_sets()` | "which rep-set owns this token" → "which selection owns this token"; colour from `selection["color"]`; `_groups_from_rep_sets` becomes a `_selections`-derived helper. Stage B-3. |
| 10 | `well_viewer/load_controller.py` | C (thin) | `~102`: `app._bar_groups_prune()` | No change beyond #1's `_bar_groups_prune` rewrite. Shadow-OK. |
| 11 | `well_viewer/data_loading.py` | O/C | `~567–568`: `list(getattr(app, "_rep_sets", []))`, `set(getattr(app, "_rep_hidden", set()))` (used to compute something during load) | Read `_selections` instead (translate hidden). Stage B-3. |
| 12 | `well_viewer/export_service.py` | C | `~226`: `app._rep_sets_active() or []` | Derived accessor. Stage B-3. |
| 13 | `well_viewer/cell_gating_tab.py` | C | `~342–343`: `if hasattr(self._app, "_rep_sets_active"): active_rsets = self._app._rep_sets_active()` | Derived accessor; the `hasattr` guard can stay. Stage B-3. |
| 14 | `well_viewer/persistence/sample_definitions.py` | **P** | `save_to_pipeline_info` (~40–60: `build_sample_definitions(app._well_labels, app._rep_sets, app._bar_groups, …)`), `load_from_pipeline_info` (~82–90: `parse_groups_block` → `app._rep_sets = …; app._bar_groups = …; app._bar_active_grp = …`), `clear_all` (~186–190) | **The migration's home.** Load: call `selections_model.from_block` (which migrates v1→v2 internally) → set `app._selections`/`_current_selection_id` (+ keep the legacy shadow during Stages A–C). Save: `selections_model.to_block(app._selections, app._well_labels, app._notes_text)` with `schema_version: 2`, write a backup first. `clear_all`: `app._selections = []`. Stage A. |
| 15 | `well_viewer/persistence/bar_groups.py` | **P** | `~29–38`: clears + `bar_groups_from_data` → `app._rep_sets/_bar_groups/_bar_active_grp`; `~61`: `json.dump(to_dict(app._rep_sets, app._bar_groups), …)`; `~89–101`: confirm/replace dialog | The standalone `bar_groups.json` import/export. **Decision needed (§9-Q):** (a) migrate it the same way on load + write v2 payload (recommended — keep parity), or (b) keep it strictly v1 (legacy import only) and never write v2 to it. Stage A (or skip if (b)). |
| 16 | `well_viewer/views/export_style_sidebar_view.py` | V (read-only) | `~680`: `list(app._rep_sets_active() or [])` | Just the derived accessor — **no widget swap** (this is the export-style dock, not the selections list). Stage B/C. |
| 17 | `well_viewer/views/bar_group_panel_view.py` | **V** | `~179–259`: iterates `app._bar_groups`, reads `g.hidden`, `app._bar_active_grp`, sets `app._bar_active_grp = i`; uses `ui.theme.styles._WELL_COLORS` for the dots | **Replaced by** `widgets.SavedSelectionsList` bound to `app._selections` (the kebab/recolour/reorder/hide all come for free). Stage C. |
| 18 | `well_viewer/views/grouping_view.py` | **V** | `~26–213`: iterates `app._rep_sets` (rep list) & `app._bar_groups` (group list), `_active_rep_idx`/`_bar_active_grp`, inline rename writing `app._bar_groups[i].name` | **Replaced by** `SavedSelectionsList` (one unified list now — rep-sets and groups are both `selections`). Stage C. The "rep set" vs "group" distinction collapses into `source` + `replicates`. |
| 19 | `well_viewer/batch_export/scatter_panel.py` | C | `~272–483`: 4× `old = self._app._rep_sets; self._app._rep_sets = list(grp.members); … ; self._app._rep_sets = old` (temporary swap to render per-group); `WELL_COLORS` import | Rework to pass a *subset of `_selections`* to the renderer instead of mutating `app._rep_sets` (the swap hack is fragile). Stage B-5. |
| 20 | `well_viewer/batch_export/base_panel.py` | C | `_groups_from_rep_sets` (~94, ~698–712: `copy.deepcopy(self._app._bar_groups)`), per-token owner lookup (~451, ~735, ~776), row/col rep-set filters (~666–684), colour by `WELL_COLORS[gi % len]` (~475–530, ~1101), `getattr(self._app, "_rep_sets"/"_bar_groups", [])` (~1050–1051), sidebar-groups deepcopy (~922) | Same as #19 + the owner/colour lookups switch to `_selections`. Stage B-5. |

**`WELL_COLORS`**: defined in `well_viewer/plate_layout.py`; imported by
`runtime_app.py`, `barplot_renderer.py`, `stats_controller.py`,
`batch_export/scatter_panel.py`, `batch_export/base_panel.py` (and there's a
parallel `ui.theme.styles._WELL_COLORS` used by `bar_group_panel_view.py`). The
migration uses `WELL_COLORS` to seed `selection["color"]`; after decision #1 the
*render-time* rule replaces positional indexing with rank-based colour, but
`WELL_COLORS` (or `theme.Colors.trace`) stays as the underlying palette.

**Today there is no per-selection colour** — colour is purely positional at render
time. This migration introduces a stored `color` on every selection; the contract
(decision #1) then says "derive it from well-position rank so the plate is the
legend". Both are new.

---

## 9. Test plan

No test harness exists in the repo today; add a `tests/` (or a
`well_viewer/_selftest_migration.py` in the same spirit as `widgets/binding_check.py`)
that runs without a display.

- **T1 — clean migration.** A v1 block with 2 groups (one hidden) + 2 free
  rep-sets → assert: 4 selections, bar-group order first, colours =
  `WELL_COLORS[0..3]`, `hidden` matches, `replicates` shapes (`group.replicate_sets()`
  vs `[wells]` for free), `current_id` = the active group's id, `well_labels`/`notes`
  carried through, ids unique 8-hex. Round-trip `to_block` → `from_block` → identical.
- **T2 — naming conflicts.** Two groups named `"Control"`, a free rep-set named
  `"Control"` and another named `"Control_v2"` → assert names `"Control"`,
  `"Control_v2 2"` (wait: groups first ⇒ first group `"Control"`, second group
  `"Control_v2"`; then the free rep-set `"Control"` → `"Control_v2 2"`; the free
  rep-set already literally named `"Control_v2"` → `"Control_v2 3"`) — i.e. assert
  the exact deterministic sequence, and that it matches `SavedSelectionsList._unique_name`.
- **T3 — malformed legacy data.** `members` referencing a missing rep-set name;
  `solo_wells` with un-normalised tokens (`"a1"`); a group with empty `members`
  and empty `solo_wells`; `hidden` as the string `"true"`; `wells` not a list →
  assert: no crash, sane output, warnings logged, the empty group survives with
  `wells=[]`/`replicates=None`.
- **T4 — missing fields.** Block with only `well_labels`; block `{}`; block with
  `rep_sets` but no `groups`; block `null`; no `sample_definitions` key at all →
  assert empty/partial `selections`, `current_id=None`, no exception.
- **T5 — already-v2 (backward-compat read).** A v2 block (`schema_version: 2`,
  `selections: [...]`) → `from_block` returns it (after validate/repair); a v2
  block with a dup id / a bad `color` / a missing `hidden` → repaired; assert it's
  **not** re-migrated and the legacy keys aren't required.
- **T6 — real data (manual, you run it).** Point the migration at ≥1 real saved
  `pipeline_info.json` from an actual run, open it in the app, eyeball: bar plot
  unchanged, group/rep lists unchanged, Save → reopen → still fine, the
  `.pre-v2-backup` exists and restores cleanly. This is the only test that can
  surface edge cases the inferred shape missed (see the honesty note at the top).
- **T7 — backup/recovery.** Migrate + Save → assert `pipeline_info.json.pre-v2-backup`
  is byte-identical to the pre-Save file; a second Save doesn't clobber it; restore
  the backup → app reads v1 again. Backup-write failure (simulate read-only dir) →
  Save aborts, file stays v1.
- **T8 — failure handling.** Feed the migration something that makes it throw
  (monkeypatch an internal) → assert: legacy state retained, warning surfaced, v2
  writes disabled for the session, original file untouched.

---

## 10. Open questions for you (answer before/with approval)

- **Q1 — `bar_groups.json`.** Migrate it on load + write v2 to it (parity,
  recommended), or freeze it as a v1-only legacy import (never write v2)? *(Plan
  assumes the former.)*
- **Q2 — colour seed vs. immediate rank-recolour.** On migration, seed
  `color = WELL_COLORS[pos % len]` (visually unchanged on first load), and apply
  the colour-by-rank rule only at render time — *or* bake the rank colour straight
  into `selections[*].color` during migration (visual change immediately, but the
  stored model and the plate agree from minute one)? *(Plan assumes seed-then-render;
  Q2-bake is a one-line change.)*
- **Q3 — Stage D timing.** Remove the `_rep_sets`/`_bar_groups` shadow as soon as
  the last consumer is switched (Stage D, this phase), or leave the shadow in for a
  release as a safety net? *(Plan assumes remove in Stage D.)*
- **Q4 — `_line_order` honouring.** Implement §3.5 (reorder migrated selections to
  a saved line-graph order) now, or leave it for later? *(Plan assumes later;
  bar-group order is canonical.)*

---

## 11. Progress

### Stage A — model + migration + persistence (with a legacy shadow) — **done** (code, not runtime-verified)

- **`well_viewer/selections_model.py`** (new, GUI-free) — the v2 `Selection`
  shape + helpers: `normalize_token` / `well_rank` / `rank_color` (decision-#1:
  colour = palette entry of the selection's *lowest* well's row-major rank;
  **baked at migration time** per Q2), `make_selection` (normalises, de-overlaps
  `replicates` ⊆ `wells`, mints `uuid4().hex[:8]` ids, `_v2`-resolves names),
  `validate_repair`, `migrate_v1` (bar-groups-first → free rep-sets; drops
  members referencing unknown rep-sets with a warning; in-session variant takes
  `rep_hidden`/`loaded_tokens`/`bar_active_grp`), `reorder_by_line_order` (§3.5,
  per Q4), `from_block` / `to_block` (v2 `{schema_version: 2, selections,
  current_id, well_labels, notes}`; drops `rep_sets`/`groups`), `to_bar_groups_payload`,
  `selections_to_legacy` (the inverse map — `source=="rep_set"` → a free
  `ReplicateSet`; everything else → a `BarGroup` with one member per `replicates`
  sub-list named `"<name> #k"`; `rep_hidden` always empty since it was never
  persisted), `from_legacy_appstate`. Borrows `WELL_COLORS` from
  `plate_layout` with a pure-Python fallback so the module (and its self-test)
  import without Qt.
- **`well_viewer/sample_definitions.py`** — added `build_sample_definitions_v2`
  (→ `to_block`) and `_backup_pre_v2` (raw-bytes copy to
  `pipeline_info.json.pre-v2-backup`, no-clobber + timestamped fallback);
  `save_to_pipeline_info` now writes a backup *before* a v1→v2 overwrite and
  **aborts the save** (`OSError`) if the backup can't be written; preserves all
  other `pipeline_info.json` keys verbatim. (The legacy `build_sample_definitions`
  / `parse_groups_block` are kept, unused, for now.)
- **`well_viewer/persistence/sample_definitions.py`** — `load_from_pipeline_info`
  now builds `app._selections` / `app._current_selection_id` from the block; the
  legacy `_rep_sets`/`_bar_groups`/… shadow is hydrated **by the original parser
  for a v1 block** (byte-perfect — zero regression on opening an existing
  dataset) and **by the inverse map for a v2 block**; a malformed block /
  migration failure logs, leaves state alone, sets `_selections_v2_writes_disabled`,
  surfaces a status message, and does **not** write. `save_to_pipeline_info`
  writes the v2 block from `_selections` (refuses if writes are disabled).
  `clear_all` resets `_selections`/`_current_selection_id` too.
- **`well_viewer/persistence/bar_groups.py`** — `bar_groups.json` now round-trips
  the same model (Q1): `save_via_dialog` writes a v2 payload; `from_dict` reads
  v1 (via the original parser → byte-perfect shadow) or v2 (via the inverse map),
  always setting `_selections`.
- **`well_viewer/persistence/line_order.py`** — after loading `line_order.json`
  (which loads *after* sample-defs), `_reorder_selections_by_line_order` re-sorts
  `app._selections` per §3.5 (the legacy shadow is left alone — the legacy
  renderers already re-order at draw time via `_line_order_*`).
- **`well_viewer/runtime_app.py`** — `__init__` declares `_selections: list = []`,
  `_current_selection_id: Optional[str] = None`, `_selections_v2_writes_disabled:
  bool = False` (2-line addition; everything else still works off the shadow).
- **`well_viewer/_selftest_migration.py`** (new, runnable like `binding_check.py`)
  — covers T1 (clean migration: order/sources/names/wells/replicates/hidden/rank
  colours/ids/current/round-trip + inverse-map sanity), T2 (the exact `_v2` /
  `<base> N` conflict sequence, matching `SavedSelectionsList._unique_name`), T3
  (malformed: missing-member groups, non-dict items, junk/dup tokens, `"true"`
  string, non-list `wells`, surviving-empty groups), T4 (missing fields / `null`
  / no-block), T5 (already-v2: dup ids, dup names, bad colours, unknown-key
  preservation, idempotent round-trip), T7 (disk: `.pre-v2-backup` byte-identical
  & no-clobber, other pipeline keys preserved, recovery), T8 (hostile inputs
  don't crash; a throwing `id_factory` falls back to uuid). **`ALL PASS`** here;
  `python -m py_compile` clean on every changed file.

**Documented Stage-A simplifications** (faithful enough; cleaned up in B/C):
1. The legacy shadow is byte-perfect for a freshly-loaded **v1** dataset; once
   you Save (→ the file becomes v2) a reload reconstructs the shadow via the
   inverse map, so a bar group's member rep-sets come back named `"<group> #k"`
   and a solo well becomes its own 1-well member. The *bar plot* may therefore
   draw a group with multiple members / solo wells slightly differently after a
   v2 save until Stage B-2 rewrites the bar renderer to read `_selections`.
2. Decision-#1 colour is baked at migration (Q2), so colours **do** change on
   the first load of a v1 dataset (intended).
3. `_rep_hidden` doesn't round-trip into `_selections.hidden` for free-rep-set
   selections (it was never persisted; a from-disk load has always come back
   fully visible). Group/user/import `hidden` round-trips fine.
4. `app._bar_groups_prune()` (run after a dataset load) still prunes the legacy
   shadow but no longer affects `_selections` — consistent with the contract
   (stored wells may legitimately not be in the current dataset).

### Decision-#1 colour ("the plate is the legend") — **done early** (code, not runtime-verified)

Landed ahead of Stages B/C because it's low-risk (presentational) and the
headline user-visible change. `runtime_app.py` gained `_rank_color_well(tok)` /
`_rank_color_rset(rset_or_group)` (rank = row-major plate position; a rep-set /
group takes its lowest well's rank colour, so all its wells + its line/bar
trace share one colour). Every `WELL_COLORS[index % len]` colour assignment in
the **main viewer** now goes through them: the replicate-panel plate map
(`_rep_refresh_map`), the left-rail sidebar plate (`_refresh_sidebar_map_now`,
incl. per-well mode — selected wells now show their rank colour, not flat
accent), the per-cell violin/beeswarm + per-well `n`-bars (`runtime_app`), the
bar plot (`barplot_renderer._render_canonical` group bars **and** per-well
bars; `barplot_controller.collect_bar_items`), the line/CDF plots
(`lineplot_controller`, both rep-set and per-well paths), and the Statistics
tab's plate map + group cards (`stats_controller`). `_rep_color_for` is now
rank-based too. **Not yet converted:** `scatter_controller` colours and the
`batch_export/*` panels — next cluster (Stage B-3 / B-5). `py_compile` clean;
the migration self-test still `ALL PASS`.

### Stage B foundation — `_selections` is now a live mirror — **done** (code, not runtime-verified)

`from_legacy_appstate` gained a `prior_selections=` argument and `_reuse_ids`
(match new entries to prior ones by name, then by well-set, so ids stay stable
across a legacy→model re-derive — needed once `SavedSelectionsList` keys
per-row state off id; `current_id` is re-pointed accordingly).
`WellViewerApp._sync_selections_from_legacy()` re-derives `self._selections`
from the live `_rep_sets`/`_bar_groups`/`_rep_hidden`/`_bar_active_grp` with id
reuse; it's invoked at the top of `_groups_centre_refresh` (every Sample-Definitions
mutation/refresh) and `_sb_on_rep_change` (rep-set visibility toggles), so the
unified model now tracks the legacy "shadow" between edits — not just at save
time (the save path still re-syncs as a backstop). The legacy edit code still
mutates the shadow directly; **Stage C** will flip that (mutations write
`_selections`; the shadow is derived) and wire `widgets.SavedSelectionsList`
into the rep-set/group views; **Stage D** removes the shadow. `py_compile`
clean; self-test `ALL PASS` (incl. an id-reuse round-trip smoke).

### Stage C — sub-cluster 1: the "GROUPS" panel → `SavedSelectionsList` — **done** (code, not runtime-verified)

*(Two earlier attempts hit dead code — `grouping_view.build_group_def_panel`
(no caller, a638943, reverted) and `bar_group_panel_view.build_bar_group_panel`
(→ `app._sidebar_groups_frame`, which is never made visible — 818c3cc, reverted).
The user confirmed: the live panel is `well_viewer/views/replicate_panel_view.py::
build_replicate_panel` → `app._sidebar_sample_frame`, the only sidebar frame shown
on the Sample Definitions tab; its card list is `grouping_view.rep_panel_refresh`
→ `app._rep_inner`.)*

`replicate_panel_view.build_replicate_panel`: the rep-card scrollable canvas
(`app._rep_canvas`/`app._rep_inner`) is replaced by a composable
`widgets.SavedSelectionsList` (`app._rep_list`); the header "REPLICATE SETS" →
"**GROUPS**" (per the user — groups apply to all plots); the plate map, `+ Add`
(→ `app._rep_add`), `Clear All`, quick-replicates dropdowns, and the rep-map
drag handlers are unchanged; the hint text updated.
`grouping_view.rep_panel_refresh` is rewritten: `_sync_selections_from_legacy()`
then `lst.updateSelections(app._selections)` (in-place when ids unchanged so an
expanded row survives) + `lst.setCurrentId(app._current_selection_id)` + honours
the `_grp_inline_edit_idx` rename request + `_rep_refresh_map()`.
`grouping_view.wire_selections_list(app, lst)` bridges the widget's signals to
the legacy mutators via `_sel_legacy_target(sel_id) → ("grp", bar_group_idx) |
("rep", rep_set_idx)` (the unified `_selections` array is `[bar_groups…, free
rep_sets…]`): `entryActivated→_rep_select / _bar_select_group`,
`entryRenamed→set .name + _rebuild_all`, `entryVisibilityToggled→_bar_groups[i].hidden`
(group) or the `_rep_hidden` set translated to `_rep_sets_loaded()` order + `_sb_on_rep_change`
(rep-set), `entryDeleted→_rep_delete / _bar_remove_group`,
`entryDuplicated→deepcopy a ReplicateSet/BarGroup`, `orderChanged→reorder _rep_sets`
(handled only when there are no bar groups — the common case), `wellsChanged→_rep_rebuild_from`
(rep-set: set `.wells`, replicate sub-list edits flatten back on round-trip; group:
one fresh `ReplicateSet "<group> #k"` per sub-list + the rest as `solo_wells`,
prune/extend `_rep_sets`), `addFromSelectionRequested→_rep_add`,
`importRequested→_bar_load_groups`. `migrate_v1` / `from_legacy_appstate` gained
an `active_rep_idx` arg so a clicked rep-set becomes `current_id` (else the
highlight would jump). `_rep_canvas`/`_rep_inner` removed. `py_compile` clean;
self-test `ALL PASS`.

**Known interim limits** (gone after Stage D): (a) editing a rep-set selection's
*replicate sub-lists* flattens back to one sub-list on the next refresh (a legacy
`ReplicateSet` only holds `{name, wells}` — true multi-sub-list editing only works
for the (rare) `bar_group`-source selections, which become `solo_wells`/`"#k"`
member rep-sets); (b) drag-reorder of the list is only applied when there are no
bar groups; (c) the same `solo → [[w]]` round-trip quirk as before.

Next: sub-cluster 2 — the mutation flip (mutations write `_selections` directly;
the legacy shadow becomes *derived from* it; `sync_selections_from_legacy` →
no-op); sub-cluster 3 = Stage D (delete the shadow + the round-trip helpers).

### Still to do
- **T6 (yours):** open ≥1 real saved `pipeline_info.json` in the app — eyeball
  the bar/line/stats/scatter plots & plate maps (colours **will** look different
  now — by plate position, decision #1; verify they're *consistent* across
  plate ↔ line ↔ bar ↔ stats ↔ scatter), the group/rep lists, **edit a
  group/rep then Save → reopen** (the Stage-A save fix must persist the edit),
  confirm `pipeline_info.json.pre-v2-backup` exists and restores cleanly;
  `python well_viewer/_selftest_migration.py` → `ALL PASS`.
- ~~`batch_export/*` colours~~ — **done**: `base_panel.py`'s plate map, single-well
  refresh, group cards, and per-member overlay traces now use
  `self._app._rank_color_rset` / `_rank_color_well` (last-group-wins for shared
  wells); `scatter_panel.py` needs no change (it forwards through the now
  rank-aware scatter collectors). `WELL_COLORS` is left imported-but-unused in
  `base_panel.py`.
- **Statistics-tab *widget* styling** — the Statistics tab still uses the
  *legacy* `_stats_map_btns` QPushButton plate (themed to match `#WellButton`
  in `theme.qss()`), **not** the v2 `widgets.WellPlateSelector` that the left
  rail uses — so it looks a bit different (cell sizing, headers, hover, drag
  visuals). Migrating the stats / image-table / segmentation / sample-defs
  plates to `WellPlateSelector` is the deferred WellSelector migration
  (`WELL_SELECTOR_GAP.md` Steps 2–8) — its own cluster, not part of the
  colour work.
- **Phase 6.5.12 (`SavedSelectionsList` composition extension)** — **done** (code,
  not runtime-verified): `setComposable(True)` + editable replicate sub-lists +
  per-chip move-menu + `+ wells…` `WellPlateSelector` popover + `setEnabledWells`
  / `setWellPlateFactory` / `setSelectionWells` / `setSelectionReplicates` +
  `wellsChanged` / `replicatesChanged` signals. See
  `design/SAVED_SELECTIONS_COMPOSITION_SPEC.md`. **This unblocks Stage C** — the
  view swap no longer loses group/rep composition.
- **Stage B (rest)** — switch the remaining read-only consumers (`batch_export/*`,
  the `runtime_app` rep-set helpers) to the unified model; **Stage C** (now
  unblocked by 6.5.12) — flip the mutation paths (`grouping_controller`,
  `selection_controller`, the `runtime_app` rep/group dialogs) to mutate
  `_selections` directly (so `sync_selections_from_legacy` becomes a no-op), and
  swap the Sample-Definitions rep-set/group view widgets for
  `widgets.SavedSelectionsList` in composable mode (wiring `wellsChanged` /
  `replicatesChanged` / `entry*` / `orderChanged` to the mutators, with an
  optional "＋ from another selection…" affordance replacing legacy "add member
  rep-set", and the legacy rep-map plate retargeted to drive the
  currently-selected selection's `wells`); **Stage D** — delete the legacy
  `_rep_sets`/`_bar_groups`/`_rep_hidden`/`_active_rep_idx`/`_bar_active_grp`
  shadow + `from_legacy_appstate` + `sync_selections_from_legacy`. Each as its
  own commit, with your runtime QA between.
