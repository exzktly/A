# Open decisions — needed before resuming the port

The four decisions left open after the v3 additions (see `DECISIONS_NEEDED.md`
#5/#9, #6, #7, #11, and `PORT_PLAN.md` §A). Each section: the call in one
sentence, the concrete options with tradeoffs, my recommendation + reasoning,
and what downstream (Phase-8 areas / new widgets / extensions) hangs on it.

> Phase-8 areas are referenced by *area* (left rail / properties panel / plot
> & figure area / app shell & titlebar / sample-definitions & bar-plots /
> image-table & segmentation) — the 8.1–8.5 numbering still needs your confirm.

---

## 1. Selected-well colour — accent vs trace (`DECISIONS_NEEDED` #5/#9)

**The call.** On the left-rail plate, do selected wells render in the **accent**
colour (one blue for all, as the Step-1 port currently does) or in their
**trace** colour (each well its own series colour, per mockup §2.1 "the plate IS
the legend") — and how is that conflict resolved?

**Options.**
- **(a) Mockup wins — trace colours on the legend plate-map.** Selected wells on
  the left rail show per-trace colours; well A01 is blue because the blue line
  *is* A01. *Tradeoff:* colour-blind users — but §2.1's own fallback covers it
  (the well-ID label inside each chip + trace tooltips repeat the ID), and a
  standalone swatch-row legend (which §2.1 deletes) is no longer the answer.
  Implementation: one line — `runtime_app._refresh_sidebar_map_now` stops
  passing `setWellColors({tok: ACCENT})` for selected wells in per-well mode and
  lets `WellPlateSelector`'s built-in trace-gradient show. (Rep-set mode is a
  separate code path — it already paints rep-set colours — and is unaffected.)
- **(b) Code wins — keep accent everywhere.** *Tradeoff:* directly contradicts
  §2.1; you'd still need a separate swatch-row legend somewhere, which the
  redesign explicitly removed. Not really viable as a *design* choice — only as
  "we're not doing the legend idea yet".
- **(c) Hybrid — trace on the legend plate-map, accent/neutral on the picker
  plate-maps.** The left rail (which *is* the legend) → trace colours; the
  Sample-Definitions / Bar-Plots / Image-Table / Statistics plate-maps (which
  are "pick wells for X", not legends) → keep accent/neutral. *Tradeoff:* none
  really — this is the natural answer once you accept (a), and it's already how
  the code is shaped (those pickers use `_plate_apply_*`, the rail uses
  `WellPlateSelector`).

**Recommendation: (a) + (c) — the conflict resolves "mockup wins" for the
legend plate-map; picker plate-maps stay accent/neutral.** The "conflict" is
mostly that Step-1 deliberately chose accent as a *temporary* safe default; the
actual design (§2.1) is trace, and the swap is trivial. One caveat to confirm:
the trace-index assignment rule — `WellPlateSelector` currently colours by the
well's *plate-position rank* among the selected set (so A01 is always trace-0),
which matches "A01 always blue"; the alternative (colour by *order of
selection*) would make colours jump as you add/remove wells. Plate-position rank
is the right one; just confirming.

**Downstream.**
- *Phase-8 areas:* **left rail** (small mod — flip the colour override). No other
  area affected directly; related-but-not-blocked: the §4 open question "hover a
  trace → highlight its well" (only meaningful if the plate is the legend), and
  the removal of any residual swatch-row legend in the **plot & figure area**.
- *New widgets:* none.
- *Extensions:* none — `WellPlateSelector` already paints trace colours when no
  explicit colour override is given; the change is in
  `runtime_app._refresh_sidebar_map_now` only.

---

## 2. `_bind_getter_setter` policy — custom widgets in binding-driven panels (`DECISIONS_NEEDED` #6)

**The call.** The Properties panel's generic "register a widget → state key"
mechanism (`ExportStyleSidebar._bind_getter_setter`) only knows `QSpinBox` /
`QDoubleSpinBox` / `QComboBox` / `QCheckBox` / `QLineEdit`; the new **Statistics**
section (Error bars / Across / Show, all `SegmentedControl`-shaped) and any
future use of `Stepper` / `StyledSlider` / `ChipGroup` need a policy.

**Options.**
- **(a) Extend `_bind_getter_setter` with branches for the custom-widget shapes.**
  Add `isinstance(w, Stepper)` (`.value/.setValue/.valueChanged`),
  `isinstance(w, SegmentedControl|ChipGroup)` (`.currentData/.setCurrentData/.currentChanged`),
  `isinstance(w, StyledSlider)` (it *is* a `QSlider`, so the `QSpinBox`-ish path
  doesn't apply — `.value/.setValue/.valueChanged`). *Tradeoff:* the binding
  layer stays the single source of truth; but it grows a branch per custom-widget
  shape, and `_bind_getter_setter` imports the `widgets` package. Closed set
  (~4 shapes), so manageable. Pure duck-typing ("any widget with `.value()`")
  *doesn't* cover `SegmentedControl` (no `.value()`), so (a) is really
  "explicit branches", not "duck-type".
- **(b) Each custom widget self-describes a binding adapter.** Add a tiny
  contract — e.g. `widget.bindingAdapter() -> (getter, setter, change_signal)`
  (or a class attr `BINDING = (...)`). `_bind_getter_setter` learns one new rule:
  *if `hasattr(w, "bindingAdapter")`, use it; else fall back to the stock
  `isinstance` branches.* *Tradeoff:* the binding contract lives **on the widget**
  (a new bindable widget self-registers; the panel code never changes again);
  slightly more ceremony per widget (~3 lines); needs `SegmentedControl`/`ChipGroup`
  to grow a "set current by data value" method (a small, useful addition anyway).
- **(c) Keep custom widgets out of binding-driven panels — hand-wire them.**
  *Tradeoff:* zero binding-layer changes; but every panel that wants the v2
  stepper/segmented look has to hand-roll getter/setter/connect per control,
  *and* the Properties panel would be visually mixed (stock `QSpinBox`es among
  custom `SegmentedControl`s) unless every control is hand-wired — which defeats
  the generic mechanism entirely.

**Recommendation: (b) — a small `bindingAdapter` protocol on the custom widgets.**
It's the least-coupled: `_bind_getter_setter` gains one `hasattr` check; stock
widgets keep their branches untouched; each custom widget that wants to be
bindable ships a 3-tuple. New bindable widgets in future Phase-8 panels then
"just work" with no edit to the binding layer. If (b) feels like over-engineering
for a closed set, **(a) is an acceptable fallback** (explicit `isinstance`
branches — it's only ~4 widget shapes). **Reject (c)** — it turns the Properties
panel into a maintenance hazard and undoes the point of `_bind_getter_setter`.

**Downstream.**
- *Phase-8 areas:* **properties panel** — blocks wiring the new Statistics
  section cleanly; also affects any future global Properties rail (§2.5) that
  reuses this pattern.
- *New widgets:* none — but it adds a `bindingAdapter` (or `BINDING` attr) to
  `SegmentedControl`, `ChipGroup`, `Stepper`, `StyledSlider`, plus a
  `setCurrentByData(value)` helper on `SegmentedControl`/`ChipGroup`.
- *Extensions:* `well_viewer/views/export_style_sidebar_view.py::_bind_getter_setter`
  (one new branch). `REWIRING.md` "Things deliberately not changed" already flags
  this as a planned follow-up.

---

## 3. `PillTabBar` vs `QTabWidget` — scope of each (`DECISIONS_NEEDED` #7)

**The call.** Where does `PillTabBar` get used, and where do the existing
`QTabWidget` / `_GroupedTabBar` notebooks stay?

**Options.**
- **(a) `PillTabBar` = the channel-tabs strip only; `QTabWidget` (+ `_GroupedTabBar`)
  = everything else, restyled via QSS.** `PillTabBar` lives in the figure /
  plot-area header (`Channel 1 · Channel 2 · + Add`, per the v3 figure card).
  The Review-level notebook, the nested "Plotting" sub-notebook, and the
  secondary tab strip (`Plotting · smFISH · Statistics · …`) stay `QTabWidget`s —
  `theme.qss()`'s `QTabBar::tab` rules already give them the v2 look (accent
  underline on the active tab), and `_GroupedTabBar` keeps the group separators +
  overflow scroll arrows + page stacking + keyboard nav. *Tradeoff:* no notebook
  rebuild; one small, contained new use of `PillTabBar`.
- **(b) Also rebuild the main notebooks on `PillTabBar` + `QStackedWidget`.**
  Re-implement group separators, overflow scrolling, page switching, keyboard
  nav, drag-reorder. *Tradeoff:* full visual control over the tab strips; large
  rebuild + regression risk; and the v2/v3 mockups never show the *secondary*
  strip as pills — they show the *channel* tabs as pills — so this solves a
  problem the design didn't pose.

**Recommendation: (a).** `PillTabBar` is the channel-tabs widget; `QTabWidget`
(restyled) + `_GroupedTabBar` remain the Review notebook, the Plotting
sub-notebook, and the secondary tab strip. The v3 additions don't touch the
notebooks; (b) is gratuitous risk for no design payoff.

**Downstream.**
- *Phase-8 areas:* **plot & figure area** (it's where `PillTabBar` is wired — the
  channel switcher in the figure header); the **centre-area / tab-strip** work
  stays "restyle the existing `QTabWidget`s via QSS" (Table-1 "Secondary tab
  strip" row unchanged); the **app shell** is unaffected.
- *New widgets:* none beyond `PillTabBar` (already built) — though it'll need a
  small `addRequested` → "add a channel" wiring in the figure area, and possibly
  per-tab close affordances if channels become removable (not currently spec'd).
- *Extensions:* none functional — `_GroupedTabBar` already gets the accent
  underline via `theme.qss()`.

---

## 4. `Toast` vs `QMessageBox` — notification roles (`DECISIONS_NEEDED` #11)

**The call.** Is `Toast` strictly fire-and-forget while `QMessageBox` keeps
everything modal — or is there a third role to define?

**Options / clarification.**
- **(a) Two-role split:** `Toast` = non-blocking, auto-dismiss, no buttons, no
  return value — for "X happened, fyi" notices. `QMessageBox` = everything else
  (modal, blocking, has buttons / returns a choice). *Tradeoff:* simple, but it
  leaves the *persistent* status-bar text (`app._set_status(...)`) unaddressed —
  and some current `_set_status` calls are "X happened" (Toast material) while
  others are "current state" (status-bar material).
- **(b) Three-role split (recommended):** **`Toast`** = transient "happened-fyi"
  (`"Saved layout.awd"`, `"Figure copied (PNG)"`, `"Export done → run.png"`,
  `"3 wells had no data — skipped"`); **status bar** (`_set_status`) = persistent
  *current state* (`"96 wells loaded"`, `"Loading 12/96…"`, `"Connected"`);
  **`QMessageBox`** = modal *must-respond* (errors that gate continuing —
  `.critical`; confirmations — `.question` "Overwrite the built-in preset?";
  blocking warnings). Inline-control error styling (a bad limits value goes red,
  `_prog_lbl` turns danger) is a fourth, pre-existing pattern — unchanged, not
  Toast's job. *Tradeoff:* you must classify each notification site, but most are
  obvious.
- **(c) Toast subsumes the status bar.** *Tradeoff:* loses the persistent
  "current state" line; "Loading 12/96…" can't be a toast (it's a stream of
  states, not an event). Reject.

**Recommendation: (b) — three roles.** `Toast` is fire-and-forget transient
notices **only**; `QMessageBox` keeps everything modal / answer-bearing
(~40 sites, none migrate); `_set_status` keeps the persistent current-state line.
`Toast` does **not** replace `_set_status` wholesale — only the "X happened"
subset of *transient* `_set_status` calls migrates to `Toast`, and that migration
is **opportunistic** (do it as Phase-8 prompts touch those sites), not a sweep.
No toast queue/stacking in v1 — overlapping toasts are acceptable for now; add a
`ToastHost` queue later if it actually bites.

**Downstream.**
- *Phase-8 areas:* minimal — whichever prompts touch notification sites
  (e.g. the **plot & figure area** export flow → a "Saved → …" toast; the
  **app shell** → a "Saved" toast on file save). Nothing is *blocked*.
- *New widgets:* none beyond `Toast` (already built) — a future `ToastHost`
  (queue/stacking) is optional, not now.
- *Extensions:* none required.

---

## Summary

| # | Decision | Recommended | Blocks |
|---|---|---|---|
| 1 | Selected-well colour | **Mockup wins (a/c):** trace colours on the legend plate-map (left rail); accent/neutral on picker plate-maps | left-rail finish (1-line) |
| 2 | `_bind_getter_setter` policy | **(b):** small `bindingAdapter` protocol on the custom widgets ((a) acceptable fallback; reject (c)) | the Properties-panel Statistics section |
| 3 | `PillTabBar` vs `QTabWidget` | **(a):** `PillTabBar` = channel tabs only; `QTabWidget`(+`_GroupedTabBar`) = all notebooks, restyled via QSS | the plot-area channel switcher |
| 4 | `Toast` vs `QMessageBox` | **(b):** three roles — Toast (transient fyi) / status bar (persistent state) / QMessageBox (modal must-respond); opportunistic migration | nothing — additive |

None of these requires new widget code; #2 adds a tiny `bindingAdapter` to four
existing custom widgets, #1 is a one-line change in `runtime_app`, #3/#4 are pure
scope confirmations. Awaiting your decisions.
