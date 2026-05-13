# Reconciliation Plan — re-anchoring the implementation to the v2 mockup

Plan only. No code changes. Companion to `design/V2_MOCKUP_AUDIT.md` (which
catalogued every gap and contradiction) and `design/mockup-decoded.html`
(canonical source of truth).

The single user-approved divergence: **the right Properties rail is
collapsible** (default expanded, toggle in the titlebar). Every other
contradiction reconciles toward the mockup body markup.

> **Status — locked decisions (2026-05-13).** Section 8's open questions
> have been resolved by the user; the locked answers are summarised at the
> very top of §8. The phase deliverables in §4 already reflect these
> answers in the text below. **Q11 (Log tray target) is the one remaining
> ambiguity** — execution of Phase 13 won't start until it's resolved.

---

## Section 1 — Scope summary

### Group A — Six major contradictions to reconcile

| ID | Contradiction | Reconciliation target | Audit ref |
|---|---|---|---|
| **A1** | Section tabs live in a horizontal centre `QTabWidget`. | Move to a vertical accent-bar nav in the **left rail** between the mode-seg and the plate. | §1.1, §2.2, §7 |
| **A2** | Outer mode switch is a top-of-window `QTabWidget` (Review / Analyze tabs); spec says Analyze is a dashed-rail drawer trigger. | Replace with a top-of-rail `mode-seg` SegmentedControl (Review / Analyze). No drawer. | §1.2, §2.1, §7 |
| **A3** | Every plot tab is its own `PlotCard` with a per-card view-switcher, channel chip, and toolbar. | Single shared figure canvas inside the Plotting section with N stacked subplots, **one** persistent bottom toolbar, **one** horizontal `ctxbar.subnav` choosing plot type for the whole canvas. | §3.1, §3.5, §3.7, §7 |
| **A4** | Channel selector is per-card. | One global channel chip in `ctxbar.right`. | §3.2, §7 |
| **A5** | Theme combo deleted; single dark theme. | Restore a small titlebar segmented theme toggle. | §1.5, §5.3, §7 |
| **A6** | Export-style sidebar is a 680-px floating dock that *replaces* the canvas while visible. | Permanent **332-px right rail**, third column, scope-segmented + ⌘K search + seven sections + header previews — **collapsible** (the exception). | §1.4, §4, §7 |

### Group B — Smaller mockup-only items to add

All from audit §8, with a small handful that surfaced during Group A planning:

| ID | Item | Audit ref |
|---|---|---|
| B1  | Breadcrumb (`Experiments › 2019 › <file>` + mono file chip) in titlebar | §1.5 / §5.4 |
| B2  | Version pill (`v2.4.1`) next to wordmark | §1.5 / §5.5 |
| B3  | Refresh action (icon button) in titlebar actions group | §1.5 |
| B4  | Statusbar three-column layout (status text · kbd-hint group · `Log ▴` tray) | §1.6 / §5.9 |
| B5  | `Count` aside on rail nav rows (e.g. `Plotting [5]`) | §2.2 |
| B6  | `SelectionChip` pill on the plate header (`2 / 96` with leading check) | §2.3 / §5.1 |
| B7  | `Invert` preset + rename `None`→`Clear` + relabel `All`→`All 96` + 1-line plate tip | §2.4 |
| B8  | Compact `SavedSelectionsList` variant for the rail (dot + name + meta only) | §2.5 |
| B9  | `Add panel` ctxbar button | §3.3 |
| B10 | "click a trace to filter properties" hint pill in ctxbar | §3.4 |
| B11 | `Configure subplots` and `Edit axes/curve` figure-toolbar buttons | §3.6 |
| B12 | Scope segmented (`All / Plot 1 / Plot 2`) at the top of the Properties rail | §4.A |
| B13 | `⌘K` `SearchInput` at the top of the Properties rail (mount the existing widget) | §4.B |
| B14 | Live-preview value in **every** Properties section header (not just some) | §4.C |
| B15 | `RangePair` widget (used in Limits and Layout sections) | §4.K |
| B16 | `kbd` glyph helper + global shortcuts (`⌘O` Open, `⌘K` Search, `⌘E` Export) | §5.2 |
| B17 | `preview-strip` inline live preview row at the top of `Lines & Markers` | §5.6 |
| B18 | Plate cut-corner ornament (triangle clipping top-left to rail bg) | §5.8 |
| B19 | Radial-gradient selected-well rendering + inset highlight/shadow | §5.11 |
| B20 | Rail "Saved" h6 with right-aligned count (`Saved [3]`) | §2.5 |
| B21 | `Profile & Format` section (Profile select + format chips) inside the Properties rail | §4 / §4.H |
| B22 | The `Layout` section's `Spacing` chips (Tight / Constrained / Manual), `Well order` select, and `Aspect` RangePair | §4.7 |
| B23 | Hideable / collapsible right rail with toggle + default expanded **(the exception)** | new |

### Group C — Doc / decision updates (deferred to the end of execution, listed now so they don't get lost)

| ID | Doc | What to flip |
|---|---|---|
| C1 | `DECISIONS_NEEDED.md` #1 | "per-plot cards … HoverToolbarOverlay in scope" → re-resolve to single shared figure canvas (mockup body); HoverToolbarOverlay dropped. |
| C2 | `DECISIONS_NEEDED.md` #4 | **No change** under Q2 locked answer (Dark only). Annotate the row with a reference to this reconciliation plan noting the mockup divergence is parked until Light theme is in scope. |
| C3 | `DECISIONS_NEEDED.md` #7 | "secondary tab strip stays QTabWidget" → re-resolve to vertical rail nav. |
| C4 | `OPEN_DECISIONS.md` #3 | Matches C3 — flip same way. |
| C5 | `PORT_PLAN.md` Table 1 row 26 ("Secondary tab strip") | "restyle via QSS only" → "rebuild as vertical rail nav (RailNav widget)". |
| C6 | `PORT_PLAN.md` Table 1 row 32 ("Properties panel") | Reword from `PropertiesPanel + SegmentedControl + SearchInput + N CollapsibleSection` (already correct in spirit) — confirm permanent third column, drop "no unified panel today" framing now that it IS being built; note hideable. |
| C7 | `PORT_PLAN.md` Table 1 row 36 ("Plot toolbar always-on → hover-revealed") | Reverse — toolbar is **always-on, single, at bottom of shared figure**. HoverToolbarOverlay marked dropped. |
| C8 | `PORT_PLAN.md` Table 1 row 41 ("Theme combo … delete") | **No reversal** under Q2. Annotate with the mockup divergence note. |
| C9 | `PORT_PLAN.md` Table 1 row 48 ("Analyze … drawer") | Reverse — keep as top-of-rail mode-seg peer; no drawer. |
| C10 | `PORT_PLAN.md` Section D | Re-issue the 8.x prompt mapping. |
| C11 | `DESIGN_NOTES.md` §2.2 | Replace with "single shared canvas, ctxbar.subnav drives plot type for whole canvas". |
| C12 | `DESIGN_NOTES.md` §2.3 | Replace with "channel chip is global in ctxbar.right". |
| C13 | `DESIGN_NOTES.md` §2.4 + reversion note | Keep the reversion as the live spec; drop the v2-port-decision counter-revert. |
| C14 | `DESIGN_NOTES.md` §2.7 | Replace "dashed-rail drawer trigger" with "top-of-rail SegmentedControl peer". |
| C15 | `DESIGN_NOTES.md` §2.8 + reversion note | Toolbar reverts to always-on persistent bottom. HoverToolbarOverlay dropped. |
| C16 | `DESIGN_NOTES.md` §6.5 | **No reversal** under Q2. Add a footnote referencing this plan and noting the divergence is parked. |
| C17 | `mockup-decoded.html` | Add a top-comment annotation noting it is canonical and that §2.2 / §2.4 / §2.7 / §2.8 of DESIGN_NOTES (which described an earlier per-card iteration) have been reversed by re-anchoring. |

---

## Section 2 — Dependency analysis

```
                ┌───────────────────────────────────────────────┐
                │  WIDGET ROUND (Phase 9)                       │
                │  RailNav · SelectionChip · RangePair ·        │
                │  KbdHint · CollapsibleRail · TitleBar v2 ·    │
                │  StatusBar groups                             │
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  APP-SHELL RESTRUCTURE (Phase 10)             │
                │  A1 section nav · A2 mode seg · A5 theme ·    │
                │  A6 rail shell (empty inside) ·               │
                │  B1 B2 B3 B4 B5 B6 B20 B23                    │
                │  ── all sections still render existing content│
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  PLOT MODEL SWAP (Phase 11)                   │
                │  A3 single canvas · A4 global channel chip ·  │
                │  B9 B10 B11                                    │
                │  ── Plotting section reorganised; others kept │
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  PROPERTIES RAIL POPULATION (Phase 12)        │
                │  A6 inside · B12 B13 B14 B15 B21 B22          │
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  POLISH / DETAIL PASS (Phase 13)              │
                │  B7 B8 B16 B17 B18 B19                        │
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  DOC RECONCILIATION (Phase 14)                │
                │  C1..C17                                       │
                └───────────────────────────────────────────────┘
```

### A-item dependency matrix

| | A1 nav | A2 mode | A3 canvas | A4 channel | A5 theme | A6 props rail |
|---|---|---|---|---|---|---|
| **A1 nav** | — | hard: A1 and A2 both want rail real-estate; do them together | weak | none | none | weak: width of rail affects centre width |
| **A2 mode** | hard | — | none | none | none | none |
| **A3 canvas** | weak | none | — | hard: A4 depends on ctxbar that A3 builds | none | medium: rail-shrink frees centre width |
| **A4 channel** | none | none | hard | — | none | none |
| **A5 theme** | none | none | none | none | — | none |
| **A6 rail** | weak | none | medium | none | none | — |

**Implications:**
- A1 and A2 must land in the same phase — both restructure the left rail.
- A3 and A4 must land in the same phase — A4 lives in the ctxbar that A3 introduces.
- A5 and A6 are independent of everything else; A6 has internal structure (the rail shell vs. its contents) that splits naturally between Phase 10 and Phase 12.

### Group B clustering

| Cluster | Group B items | Lands in |
|---|---|---|
| Titlebar polish | B1, B2, B3, B16 | Phase 10 (with A5) |
| Statusbar | B4, B16 (statusbar half) | Phase 10 |
| Rail polish | B5, B6, B7, B8, B20 | B5/B6/B20 in Phase 10; B7/B8 in Phase 13 |
| ctxbar polish | B9, B10, B11 | Phase 11 (with A3) |
| Properties polish | B12, B13, B14, B15, B21, B22 | Phase 12 |
| Plate visual fidelity | B18, B19 | Phase 13 |
| Lines & Markers polish | B17 | Phase 13 |
| Hideable rail | B23 | Phase 10 (initial), refined in Phase 12 |

### Existing widget consumption

| Widget | Used by | Action |
|---|---|---|
| `PlotCard` | every plot tab | **deprecated by A3**; survives as the inner canvas widget for non-Plotting sections (smFISH, Stats, etc.) until those are reconsidered. Strip per-card chrome on Plotting only. |
| `MplToolbar` | per-card | **single instance** at bottom of shared Plotting canvas. |
| `SegmentedControl` | various | reused for mode-seg (A2), theme (A5), scope (B12), `Spacing` chips (B22). |
| `CollapsibleSection` | export-style sidebar | reused; `setValueWidget` now populated for every section (B14). |
| `WellPlateSelector` | sidebar, GROUPS, Stats, etc. | reused; needs visual polish (B18, B19). |
| `SavedSelectionsList` | Sample Definitions, Bar Plots | reused; needs **compact mode** (B8). |
| `IconButton` | titlebar, plot-card | extend for `kbd` overlay (B16). |
| `Stepper`, `StyledSlider`, `ColorSwatchRow`, `LutSelector`, `Popover`, `Drawer`, `Toast`, `EmptyState` | various | reused unchanged. |
| `SearchInput` | built but unmounted | mount in Properties rail (B13). |
| `HoverToolbarOverlay` | unused | **delete** as part of C7. |
| `TitleBar` widget (frameless mode) | not mounted | optionally activated (still gated on DECISIONS #4 — see Q1). |

---

## Section 3 — Custom widget gap

| Widget | New / extend | Purpose | API sketch | Consumed by | Complexity |
|---|---|---|---|---|---|
| **`RailNav`** | new | Vertical accent-bar nav for the left rail (`Plotting [5]`, `smFISH`, …). One-of-N selectable; accent-dim row bg + 2-px left accent on active row; supports leading Lucide icon + trailing `count` aside. | `addItem(label, icon=None, key=None, count=None) → row`, `setCurrentKey(key)`, `currentKey()`, `setCount(key, n)`; signal `currentChanged(key)`. `bindingAdapter()`. | A1 | small |
| **`SelectionChip`** | new | Pill-style count chip (`2 / 96` with leading check). Variants: `accent-dim` (selection count), `muted` (saved count `[3]`). | ctor `(text, *, icon=None, variant="accent")`, `setText(text)`. | B6, B20, B5 (via RailNav.count) | small |
| **`RangePair`** | new | Two `QLineEdit`s with a configurable separator glyph (`–`, `×`, `–`). | ctor `(*, separator="–", placeholder_low, placeholder_high)`, `value() → (low, high)`, `setValue(low, high)`; signal `editingFinished(low, high)`. `bindingAdapter()`. | B15, B22 | small |
| **`KbdHint`** | new | Inline `⌘O`-style mono glyph (a `QLabel` with QSS). Standalone or composable with `IconButton`. | ctor `(text)`. Static helper `IconButton.setKbdHint(text)` to overlay. | B16, statusbar | trivial |
| **`CollapsibleRail`** (or extension of existing `Drawer`-pattern container) | new | The right-side Properties rail container. Permanent column, fixed width, animated collapse to a 24-px gutter via `QPropertyAnimation` on `maximumWidth`. Emits `collapsedChanged(bool)`. | ctor `(content_widget, *, width=332, collapsed=False)`, `setCollapsed(bool)`, `isCollapsed()`, `toggle()`; signal `collapsedChanged(bool)`. | A6, B23 | medium |
| **`StatusBar` (v2)** | extend existing | Three-column layout (status text · kbd-hint group · tray button); host `StatusDot`. | builder fn `build_status_bar(parent)` returning a `QWidget` with named children `status_label`, `kbd_group`, `tray_btn`. | B4 | small |
| **`TitleBar` (v2 chrome)** | extend existing | Native frame (per current DECISIONS #4); adds breadcrumb area, mono file chip, version pill, refresh `IconButton`, kbd-hinted `Open` primary button, rail-collapse toggle (for A6/B23). **No theme switcher** (Q2 locked). | extend current header builder in `all_well.py`; expose `set_breadcrumb(parts: list[str])`, `set_file(path: str)`, `set_dataset_stats(s: str)`, `set_rail_collapsed(bool)`. Signals `openRequested`, `refreshRequested`, `railCollapseToggled(bool)`. | B1, B2, B3, B16 (Open hint), Q1 toggle | medium |
| **`SavedSelectionsList.compactMode`** | extend existing | Add a render mode that strips drag handle / eye / kebab / expand and renders one read-only row per entry (dot + name + meta). Same model, lighter delegate. | `setCompact(bool)`; default False. | B8 | small |
| **`PlotCanvas`** (single-shared figure widget) | new (or major refactor of `PlotCard` into "card chrome optional" mode) | Hosts 1–4 stacked matplotlib subplots in **one** `Figure` (Q3), one bottom `MplToolbar`, one `coords` readout. Each subplot has **independent axes** (Q10). Knows how to switch its renderer between line / bar / scatter / distribution / heatmap; the same type applies to all subplots (Q5). Subplot order = insertion order, fixed (Q12). | ctor `(parent, *, subplots=2, max_subplots=4)`, `setPlotType(name)`, `addPanel()` (no-op past `max_subplots`, returns `False`), `removePanel(idx)` (no-op if only 1 remains), `subplotCount() → int`, `figure`, `canvas`. Signals `plotTypeChanged(name)`, `subplotCountChanged(n)`. | A3, Q3, Q5, Q10, Q12 | **large** |
| **`PreviewStrip`** | new (small) | Inline mini-SVG-style preview row inside a Properties section (`Lines & Markers`). A custom-painted QWidget that draws a polyline + markers reflecting the current line-width/marker-size/color. | ctor `(parent)`, `setStyle(*, line_width, marker_size, color)`. | B17 | small |

**Total: 9 new widgets / 3 substantive extensions.** Comparable to Phase 6.5's
widget round in scope. All listed widgets get a gallery demo and `__main__`
entry-point per the standing Phase 6.5 rule.

---

## Section 4 — Phased execution plan

Numbering: this work is **Phase 9 onward** (Phase 8 was the screen-port that
this reconciliation effectively re-does). Each phase ends with the app
running and runtime-QA-able.

### Phase 9 — Widget round (pre-flight)

**Goal.** Land every new widget and extension Phase 10–13 will consume, in
isolation, with gallery demos. No app-shell touch yet.

**Items.** All of Section 3.

**Prereqs.** None.

**Deliverables.**
- `widgets/rail_nav.py`, `widgets/selection_chip.py`, `widgets/range_pair.py`, `widgets/kbd_hint.py`, `widgets/collapsible_rail.py`, `widgets/preview_strip.py`, `widgets/plot_canvas.py`
- Extensions in `widgets/title_bar.py`, `widgets/saved_selections_list.py` (compact mode), `widgets/icon_button.py` (kbd overlay), `widgets/status_dot.py` (no change but consumed)
- `widgets/__main__` / gallery entries for each new widget
- Unit-style `__main__` demos that run standalone with `python -m widgets.<name>`

**Runtime QA.**
- Open each widget's `__main__` demo. Confirm the visual matches the mockup excerpt for that widget (cross-reference against `mockup-decoded.html`).
- `RailNav` demo: 8 items, click-to-activate, accent-bar moves, count aside renders.
- `CollapsibleRail` demo: click toggle, panel animates closed to 24-px gutter and back.
- `PlotCanvas` demo: add/remove subplot, switch plot type — matplotlib re-renders without flicker.
- App itself still runs unchanged (this phase doesn't modify the app).

---

### Phase 10 — App-shell restructure

**Goal.** Replace the current `QMainWindow → QTabWidget (outer) → centre_view (inner notebook)` stack with the mockup's three-column layout. **All section content keeps rendering as today**; only the chrome around it changes.

**Items.** **A1, A2, A6 (shell only, contents deferred), B1, B2, B3, B4, B6, B20, B23.** (A5 parked per Q2; B5 dropped per Q8.)

**Prereqs.** Phase 9.

**Deliverables.**
- `all_well.py` rewired: drop outer `QTabWidget`; build top-level grid (`titlebar`/`main`/`statusbar`) per mockup CSS at line 467–471.
- New `well_viewer/views/app_shell_view.py` (or fold into `all_well.py`) building rail + center + right-rail containers.
- `well_viewer/views/centre_view.py` rewired: replace `_GroupedTabBar`+`QTabWidget` with a `QStackedWidget` driven by `RailNav.currentChanged`.
- Titlebar gains: BrandTile + wordmark + `v2.4.1` pill + breadcrumb area (built from dataset path, Q7) + mono file chip + dataset stats + refresh `IconButton` + Help button + presentation toggle + rail-collapse toggle (Q1) + primary Open button with `⌘O` `KbdHint`. **No theme switcher** (Q2).
- Statusbar gains: three groups (`StatusDot + status_label`, `KbdHint × 3`, tray button).
- Right rail: a `CollapsibleRail` mounted as the third column, default expanded. Its content is **the existing export-style sidebar contents, ported in-place** (no scope segmented / search / new layout yet — that's Phase 12). The sidebar's old "floating dock" mount path is bridged so the sliders IconButton still works (toggling the rail's collapse state).
- Mode-seg `Review / Analyze` at top of rail; Review wires to the existing review widget, Analyze wires to the existing analyze widget (whichever was inside the old outer QTabWidget's tabs).
- `.main` grid: `400px 1fr 332px` (Q9 rail width override; mockup's 260 widened for plate breathing room).
- Plate-wrap rebuilt in the rail with the existing `WellPlateSelector` widget. Mockup `sel-chip` rendered as a `SelectionChip` in `plate-head`.
- `Saved [3]` h6 + read-only `SavedSelectionsList(compact=True)` mounted under presets.

**Runtime QA.**
- App opens; the outer Review/Analyze tabs are gone — replaced by a top-of-rail Review/Analyze toggle.
- Rail has the 8 section items vertically; clicking each navigates without errors; the active row shows the 2-px accent bar.
- Plate map, plate count chip, Quick-select row, Saved list all render correctly. Plate still selects wells; row/column clicks still work.
- Right rail is visible by default; toggling collapse from titlebar slides it closed; clicking the sliders IconButton on any plot expands it (legacy entry point).
- Titlebar shows brand + version + breadcrumb (initially: the dataset path; full multi-level breadcrumb is Phase 13) + theme toggle + Open.
- Statusbar shows green dot + "Ready." + kbd hints + Log tray. (Tray button non-functional this phase.)
- Switching theme to Light visibly inverts the chrome (or stays dark if Q2 limits us — see §8).

---

### Phase 11 — Plot canvas model swap (Plotting section only)

**Goal.** Refactor the Plotting section to the mockup's single shared canvas; consolidate channel selection; restore the ctxbar.

**Items.** **A3, A4, B9, B10, B11.**

**Prereqs.** Phase 10.

**Deliverables.**
- `well_viewer/tabs/plotting_section_view.py` (new) builds the centre content for the `Plotting` section:
  - `ctxbar` (subnav: Line / Bar / Scatter / Distribution / Heat Map; right group: Channel chip · "click a trace to filter" hint · `Add panel` ghost button · `Export figure` button).
  - One `PlotCanvas` underneath that hosts the configured subplots (default 2 to match mockup).
- `widgets/plot_canvas.py` (from Phase 9) wired to delegate to the existing controllers: `line_graphs_controller`, `bar_plots_controller`, `scatter_controller`, `distribution_controller`, `heatmap_controller`. Switching the subnav swaps the active renderer for **all** subplots simultaneously (Q5). Per-subplot axes are **independent** (Q10).
- One persistent `MplToolbar` at the bottom of the canvas. Add `Configure subplots` (delegates to mpl `figure.subplots_adjust` dialog) and `Edit axes/curve` (delegates to `NavigationToolbar2QT.edit_parameters`) buttons (B11, Q6 confirms both).
- **Multi-subplot management (Q3)**: `PlotCanvas` supports 1–4 subplots; `Add panel` ctxbar button calls `addPanel()` (caps at 4 with a Toast on over-cap); each subplot title row gets a small `×` `IconButton` that calls `removePanel(idx)` (disabled when only 1 subplot remains). Subplot order is fixed = insertion order (Q12).
- Delete per-card chrome from `line_graphs_tab_view.py`, `bar_plots_tab_view.py`, `scatter_cells_tab_view.py`, `scatter_agg_tab_view.py`, `distribution_tab_view.py`, `heatmap_tab_view.py` — they become thin renderers attached to the shared canvas.
- Other sections (smFISH, Statistics, Image Table, Segmentation, Review CSV, Sample Definitions, Batch Export) keep their existing layouts; they live in their own QStackedWidget pages and are untouched this phase.
- `make_band_controls` band toggles re-home into the Properties rail's Statistics section (deferred to Phase 12); for this phase they remain visually present in the controls strip below the canvas (a small holdover).

**Runtime QA.**
- Open the Plotting section. One unified figure card; two stacked subplots inside one canvas; one toolbar at the bottom.
- ctxbar.subnav switches Line ↔ Bar ↔ Scatter ↔ Distribution ↔ Heat Map; both subplots redraw with the new renderer.
- Channel chip changes the active channel for the whole canvas; both subplots reflect the new channel.
- Save-figure (toolbar Save) exports the entire canvas as one PNG.
- All other sections (smFISH, Statistics, etc.) still work as before.
- Presentation-mode toggle still flips publication ↔ screen styling.

---

### Phase 12 — Properties rail population

**Goal.** Bring the right rail to mockup parity — scope segmented, search, full section list with header previews.

**Items.** **A6 (inside the shell), B12, B13, B14, B15, B21, B22.**

**Prereqs.** Phase 10 (shell), Phase 11 (so the per-card controls are gone and Properties is the only place to edit them).

**Deliverables.**
- `well_viewer/views/properties_rail_view.py` (new) builds the rail interior:
  - `props-head`: title, save-preset / reset / collapse `IconButton`s.
  - Scope `SegmentedControl` (`All` / `Plot 1` / `Plot 2`) — Plot N segments carry trace dots.
  - `SearchInput` (the existing `widgets/search_input.py`) with `⌘K` shortcut.
  - **Eight** `CollapsibleSection`s — mockup's seven plus a new `Statistics` section (Q4 / DESIGN_NOTES §6.2). Order: Profile & Format · **Statistics** · Axes · Legend · Lines & Markers · Grid · Limits & Scale · Layout.
  - `Statistics` section content (Q4): `Error bars` chips (None / SEM / SD / 95% CI), `Across` chips (Replicates / FOV), `Show` chips (Mean / Mean + spread / All points). Header preview reads e.g. `SEM · spread`.
  - Every section header carries a live-preview value (B14) — populated from `_export_style_prefs`.
  - `Limits & Scale.X limits` / `Y limits` / `Layout.Aspect` use the new `RangePair` widget.
  - `Lines & Markers` gets a `PreviewStrip` (B17 lives here too).
  - `Layout.Spacing` is a `chips`-style three-way `SegmentedControl` (Tight / Constrained / Manual).
  - `Layout.Well order` is a `QComboBox` with the existing well-order data.
  - Band controls (SEM/SD/FOV/Spread) re-home into the new `Statistics` section (Q4 locked); the temporary holdover strip from Phase 11 is removed.
- The old floating-dock entry point retires: the sliders `IconButton` now just expands the rail (no separate dock created).
- `_export_style_prefs` getter/setter machinery is re-wired through `bindingAdapter()` exactly as today; only the host widget changes.

**Runtime QA.**
- Right rail shows all seven sections; every collapsed-state header carries a live-preview value chip.
- `⌘K` focuses the search input; typing filters / highlights matching property rows.
- Scope segmented switches between All / Plot 1 / Plot 2 — Plot 1 edits a property and only that subplot changes; Plot 2 likewise; All edits affect both.
- RangePair widgets accept low/high values, separator glyph renders correctly.
- Changing any property in the rail still re-renders the canvas (the binding pipeline survives).
- Collapse the rail; the canvas expands to fill. Expand it back; everything restores.

---

### Phase 13 — Polish / detail pass

**Goal.** Close out every remaining Group B item.

**Items.** **B7, B8 (refinements), B16 (global shortcuts), B17, B18, B19, B4-`Log` tray** (gated on Q11).

**Prereqs.** Phase 10–12 (so all surfaces exist to polish).

**Deliverables.**
- `B7`: rail Quick-select row gains `Invert` button, `None`→`Clear` (red hover), `All`→`All 96`; tip line beneath.
- `B8`: SavedSelectionsList compact mode polish — re-check rendering at narrow rail widths.
- `B16`: `⌘O` / `⌘K` / `⌘E` global shortcuts wired via `QShortcut`; statusbar shows them in mono kbd glyphs; titlebar `Open` button shows `⌘O` overlay.
- `B17`: `PreviewStrip` integrated into Lines & Markers (the actual draw — Phase 12 mounted the placeholder).
- `B18`: Plate cut-corner ornament via `QPainter` (or QSS clip-path) — applied to the rail plate frame.
- `B19`: `WellPlateSelector` selected wells repaint with a radial-gradient fill + inset highlight/shadow per mockup CSS at lines 707–717.

**Runtime QA.**
- `Invert` toggles the selection correctly; `Clear` deselects all wells with a red hover state.
- `⌘O` opens the dataset dialog; `⌘K` focuses Properties search; `⌘E` triggers export of the active figure.
- Lines & Markers preview-strip live-updates when the user drags Line width / Marker size sliders.
- Selected wells have the gradient appearance — visibly richer than the previous flat-fill.
- Plate frame's top-left corner shows the cut-corner ornament against the rail bg.

---

### Phase 14 — Doc reconciliation

**Goal.** Update every design doc whose decisions are now reversed.

**Items.** **C1 – C17.**

**Prereqs.** Phase 10–13. Docs update *after* the implementation they describe.

**Deliverables.**
- `DECISIONS_NEEDED.md`: re-resolve items #1, #4, #7 with new resolution + reference to mockup-decoded.html.
- `OPEN_DECISIONS.md`: same for #3.
- `PORT_PLAN.md`: rewrite rows 26, 32, 36, 41, 48; rewrite §D phase mapping.
- `DESIGN_NOTES.md`: rewrite §2.2, §2.3, §2.4, §2.7, §2.8, §6.5.
- `mockup-decoded.html`: append a header comment marking it canonical and listing the doc reversals.
- New `design/V2_MOCKUP_AUDIT.md` "Resolved" section appended in-place noting each contradiction's resolution.

**Runtime QA.** N/A (doc-only). Cross-read the updated docs against the implementation to confirm parity.

---

## Section 5 — Risk register

| Risk | Where | Mitigation |
|---|---|---|
| **R1. Single shared canvas regresses cross-plot functionality.** Phase 11 swap may break controllers that assume per-card axis ownership (especially heatmap layout and stats overlays). | A3, Phase 11 | Land per-renderer one at a time inside Phase 11 (line → bar → scatter → distribution → heatmap), each as a separate runtime-QA checkpoint inside the phase. If the existing controllers can't be coerced into the shared canvas, fall back to a "one matplotlib `Figure` per visible subplot" model (still one toolbar, still one ctxbar) — same UX, less ambitious. |
| **R2. `runtime_app.py` rewires.** This session showed repeated mistakes there. Phase 10–11 must touch it. | A1, A2, A3, A6 | Push as much new layout as possible into new modules (`app_shell_view.py`, `plotting_section_view.py`, `properties_rail_view.py`); have `runtime_app.py` import + mount them rather than grow more inline construction. Each Phase 10 deliverable is a sub-commit so any single bad edit is small. |
| **R3. Theme system needs a second mode.** | A5, Phase 10 | **CLOSED by Q2 (Dark only).** No second mode in scope; mockup divergence noted. Revisit when Light theme is on the roadmap. |
| **R4. Selections-model migration interaction.** Phase 8.0 v1→v2 migration is fresh. Re-shaping the Sample Definitions tab inside Phase 10 could disturb it. | A1, B8 | Do **not** touch the Sample Definitions tab interior during Phase 10 — only relocate it into a stack page. The full SavedSelectionsList in the centre stays the editable model; the rail `Saved` list is a compact *read-only* mirror reading the same `app._selections` array. |
| **R5. Floating dock removal breaks existing keyboard / UI paths.** Today's sliders `IconButton` opens a dock that *replaces* the canvas. Phase 12 retires the dock. | A6, Phase 12 | Phase 10 already bridges the legacy entry point (sliders button → expand rail). Phase 12 only changes the rail's contents; the entry point stays the same. The only "user-visible" change is that the canvas is no longer hidden when the rail opens (the canvas instead shrinks). |
| **R6. ctxbar.subnav semantics are ambiguous.** | A3 | **CLOSED by Q5 (whole canvas).** |
| **R7. Scope creep on Group B polish.** 23 small items can sprawl. | All B | Hard cap Phase 13 at one commit per item, with the user QA-ing the phase end. Anything that grows beyond a single small commit gets split into its own follow-up. |
| **R8. `PlotCanvas` is a large widget.** Combines matplotlib lifecycle, renderer registry, and the ctxbar wiring. | Phase 9 | Build the canvas in Phase 9 with **placeholder renderers** (just `ax.plot([1,2,3])`); wire real controllers only in Phase 11. That way the widget is testable in isolation in Phase 9 even before the renderers are integrated. |
| **R9. Mockup absences (no Statistics section in mockup body) might cause us to delete useful controls.** DESIGN_NOTES §6.2 designed a Statistics section; mockup body doesn't show one. | Phase 12, Q4 | Treat Q4 as binding: user picks whether Statistics becomes its own section (re-instates §6.2) or folds into Profile & Format. Either is acceptable; we don't lose the SEM/SD controls. |
| **R10. Mockup's hideable rail collapse animation is unspecified.** Mockup is static; no transition spec. | Phase 9 (CollapsibleRail), Phase 10 | Default to a 180-ms `QPropertyAnimation` on `maximumWidth` (matches the existing `Drawer` cadence). Easy to tweak later. |

---

## Section 6 — Doc updates (the lists, again, with the specific edits each doc needs)

Restated explicitly so this phase isn't forgotten. **Apply only after the implementation lands** (Phase 14).

- **`DECISIONS_NEEDED.md`**
  - #1 — flip to single shared canvas. Note the reversal date and link to mockup-decoded.html + reconciliation plan.
  - #4 — flip to native frame + restored Dark/Light theme seg.
  - #7 — flip to vertical rail nav.
- **`OPEN_DECISIONS.md`**
  - #3 — same as #7 above.
- **`PORT_PLAN.md`** Table 1
  - row 26 (Secondary tab strip): "rebuild as vertical rail `RailNav`".
  - row 32 (Properties panel): permanent 332-px third column, hideable, scope-segmented + ⌘K search + 7 sections + header previews.
  - row 36 (Plot toolbar): always-on, single, at bottom of shared canvas; `HoverToolbarOverlay` dropped.
  - row 41 (Theme combo): keep as titlebar `SegmentedControl`.
  - row 48 (Analyze mode): top-of-rail SegmentedControl peer; drawer dropped.
  - §D (phase mapping): re-issue 8.x prompts; reference Phase 9–14 of this plan.
- **`DESIGN_NOTES.md`**
  - §2.2 — replace per-card view-switcher language with single-canvas + ctxbar.subnav.
  - §2.3 — replace per-card channel chip with global ctxbar channel chip.
  - §2.4 / §2.8 — keep the reversion as the spec; drop the v2-port counter-revert paragraphs.
  - §2.7 — replace drawer language with top-of-rail SegmentedControl peer.
  - §6.5 — re-instate the theme switcher segmented (Q2 decides which themes).
- **`mockup-decoded.html`** — append a top-of-body HTML comment marking it canonical and noting which DESIGN_NOTES sections it reverses.

---

## Section 7 — Out of scope / explicit deferrals

| Item | Why deferred |
|---|---|
| **Stage D mutation flip** (Phase 8.0's outstanding direct-write removal) | Independent of mockup parity. Continue in parallel. |
| **Composition affordance for `SavedSelectionsList`** | Already shipped (the editable list); compact-mode for the rail is what this plan adds. The full composition UX inside the editable list stays. |
| **Frameless `TitleBar` mode** | DECISIONS #4 still says native frame; Phase 14 doc updates don't change that — we only re-add the theme switcher to the in-window header. Frameless can be revisited later. |
| **Multi-subplot dynamic add/remove** beyond the default 2 | `Add panel` ctxbar button can be stubbed initially (Q3). Real implementation only if user asks. |
| **`Configure subplots` / `Edit axes/curve` dialog content** | Wire the buttons to the matplotlib defaults (mpl provides both dialogs). Bespoke replacements are not in scope. |
| **High-contrast theme** | DESIGN_NOTES §6.5 mentions it. Out of scope unless Q2 asks for it. |
| **The smFISH / Statistics / Image Table / Segmentation / Review CSV / Sample Definitions / Batch Export sections' interiors** | Phase 11 only reorganises Plotting. Other sections keep their current layouts. If any of those want the same canvas treatment, that's a separate plan. |
| **Brand-logo dropdown menu (Open / Recent / Preferences / About / Quit)** | DESIGN_NOTES §6.5 spec, not in the mockup body. Skip unless requested. |
| **Audit refresh after Phase 11** | One narrow audit (`SavedSelectionsList` compact mode against the rail's narrow width) may be useful — built into Phase 13's QA. No separate plan needed. |

---

## Section 8 — Open questions for the user

### Locked answers (2026-05-13)

| Q | Locked answer | Implication |
|---|---|---|
| **Q1** | **Titlebar icon button only** for rail collapse toggle. | TitleBar gains a `panel-right-close` / `panel-right-open` IconButton bound to `CollapsibleRail.toggle()`. No rail-edge handle. |
| **Q2** | **Dark only** for now. | A5 (titlebar theme segmented) is **dropped from Phase 10**; the mockup divergence is acknowledged. C2 / C8 / C16 doc updates **stay as deferral notes** rather than reversals — i.e. DECISIONS #4 remains in effect, with a `// see RECONCILIATION_PLAN.md` annotation. No theme switcher widget is mounted; the segmented control is **not** built. (When Light theme is implemented, we revisit.) |
| **Q3** | **Configurable 1–4 subplots**, with `Add panel` and per-subplot remove. | `PlotCanvas` ctor gains `max_subplots=4`; `addPanel()` / `removePanel(idx)` work; `Add panel` ctxbar button is live (not stubbed); each subplot's title row gets a small `×` remove affordance. |
| **Q4** | **Own `Statistics` section in Properties** per DESIGN_NOTES §6.2. | Phase 12 deliverables add a Statistics `CollapsibleSection` between Profile & Format and Axes; SEM/SD/FOV controls move there from the controls strip. |
| **Q5** | **ctxbar.subnav governs the whole canvas.** | Switching subnav re-renders every subplot using the chosen plot type's controller. Confirms R6 mitigation. |
| **Q6** | **Build all three** of `Add panel`, `Configure subplots`, `Edit axes/curve`. | `Configure subplots` and `Edit axes/curve` wrap matplotlib's built-in dialogs (`Figure.subplots_adjust` flow + `NavigationToolbar2QT.edit_parameters`). |
| **Q7** | **Synthesise the breadcrumb from the dataset path.** | TitleBar's `set_breadcrumb` consumes the dataset `Path` and splits last 2–3 parents into the trail (e.g. `parent / dataset_name / out`). No workspace registry. |
| **Q8** | **Drop the count aside on rail nav rows.** | `RailNav.addItem(..., count=None)` API still exists but no nav rows wire it. Spec note: leave the API in place for later use. |
| **Q9** | **Rail width = 400 px** (was 260 px in the mockup). | `.main` grid becomes `400px 1fr 332px`. Titlebar grid first column matches (`grid-template-columns: 400px 1fr auto`). Plate map gets visibly more breathing room than the mockup shows. **Mockup divergence acknowledged** — this is a deliberate ergonomic call over mockup parity. |
| **Q10** | **Independent X axes** per subplot. | `PlotCanvas` does not share/link axes; each subplot owns its full axis pair. |
| **Q11** | **STILL OPEN.** Pick one: bottom log panel · Drawer with recent logs · stub. | Blocks the Phase 13 `Log ▴` tray work only — every other phase is unblocked. |
| **Q12** | **Fixed subplot order.** | Order = insertion order; no drag-reorder of subplots; `removePanel` re-indexes 0..N-1 silently. |

### Locked answers — knock-on effects on the plan

- **Group A reduces to five contradictions in play.** A5 (theme switcher) is parked under Q2's "Dark only" answer; doc-update C2 / C8 / C16 become "leave DECISIONS #4 standing; annotate the mockup divergence" instead of "flip the resolution".
- **Phase 9 widget round drops the titlebar theme-segmented build.** Net widget-round delta: −1 small item.
- **Phase 11 grows slightly** to cover dynamic 1–4 subplot management (`Add panel` button live; per-subplot `×` button). Still inside the single-phase envelope.
- **Phase 12 grows** by one Properties section (Statistics, Q4).
- **Phase 10 grows trivially** with the path-based breadcrumb synthesiser (Q7).
- **Section 5 risk R3 (theme system second mode) is closed** — Light theme is out of scope.
- **Section 5 risk R6 (ctxbar.subnav semantics) is closed** — Q5 answer locked.

### Original 12 questions (kept for traceability)

**Q1.** **Hideable Properties rail toggle placement.** I'd propose the titlebar (a `IconButton` with a `panel-right-close` Lucide glyph, paired with `panel-right-open` when collapsed) as the primary control. Two alternatives:
- **(a) titlebar only** (recommended) — single discoverable affordance.
- **(b) rail-edge handle** — a thin vertical strip on the rail's left edge with a chevron; click to toggle.
- **(c) both** — titlebar + edge handle.
**Default:** I will use (a) unless you say otherwise.

**Q2.** **Theme switcher options.** The mockup shows **Dark / Light** only. DESIGN_NOTES §6.5 specifies **Dark / Light / System** + an opt-in High-contrast toggle. Which?
- **(a) Dark only** — keep current behaviour, just visually restore the segmented for future-proofing.
- **(b) Dark / Light** (mockup default — recommended).
- **(c) Dark / Light / System.**
- **(d) Dark / Light / System + High contrast toggle** (DESIGN_NOTES §6.5).

**Q3.** **Multi-subplot.** The mockup body shows **two stacked subplots** in the Plotting canvas. Implementation question:
- **(a) fixed at 2 subplots** — simplest; `Add panel` button is a stub or hidden.
- **(b) configurable 1–4 subplots** with `Add panel` / per-subplot remove — bigger lift.

**Q4.** **Statistics section in Properties rail.** DESIGN_NOTES §6.2 designs a `Statistics` section (Error bars / Across / Show). The mockup body doesn't have one. Options:
- **(a)** Add the Statistics section per §6.2 (between Profile & Format and Axes), and move the SEM/SD/FOV band toggles there. **Recommended.**
- **(b)** Fold SEM/SD into the existing `Lines & Markers` section.
- **(c)** Keep band toggles on the controls strip below the canvas (don't move them into Properties).

**Q5.** **ctxbar.subnav semantics.** When the user switches the subnav from Line to Bar in a 2-subplot Plotting canvas:
- **(a)** Both subplots switch to Bar — the subnav governs the whole canvas. (Matches mockup body markup — recommended.)
- **(b)** Only the "active" subplot switches; each subplot has its own per-subplot type. (Matches the original v2 intent in DESIGN_NOTES §2.2, but contradicts the mockup body.)

**Q6.** **`Add panel`, `Configure subplots`, `Edit axes/curve` toolbar buttons.** All three appear in the mockup. Confirm we implement all three (with reasonable defaults — `Configure subplots` and `Edit axes/curve` can wrap matplotlib's built-in dialogs)?

**Q7.** **Breadcrumb data source.** Mockup shows `Experiments › 2019 › <file>` — three levels. Do we have a workspace / project / file taxonomy in mind, or for v1 should we just split the dataset path into "parent dir / dataset name / out subfolder" as a stand-in?

**Q8.** **Plotting nav row count aside (`Plotting [5]`).** What does 5 mean?
- **(a)** 5 = the number of plot subtypes in the ctxbar (Line/Bar/Scatter/Distribution/Heat Map) — static.
- **(b)** 5 = count of currently-displayed subplots / loaded plot states — dynamic.
- **(c)** Drop the count aside entirely.

**Q9.** **Rail width 260 px feels narrow for the plate at v1 dataset sizes.** Mockup pegs the rail at 260 px (matching the plate's natural 12-column layout). Are we OK with that or should the rail be wider?

**Q10.** **The mockup's two-subplot canvas uses one shared X axis (timepoint).** If a user mixes views (Line top + Bar bottom — but with Q5(a) they'd both be the same view), do we keep the shared X or let each subplot have its own?

**Q11.** **`Log ▴` statusbar tray.** What does it open?
- **(a)** A bottom-docked logs panel.
- **(b)** A Drawer with recent app log entries.
- **(c)** Stub/dead for now; design later.

**Q12.** **Sub-plot ordering.** Mockup shows `Mean intensity` on top, `Fraction of cells above threshold` on bottom. Is the order fixed, user-reorderable, or determined by a metric definition?

---

## Section 9 — After approval

Execute one phase per turn. Between phases:
1. I commit the phase's work on the current branch and push.
2. You runtime-QA against the phase's checklist.
3. We do one quick reconciliation turn for any defects before starting the next phase.
4. Phase 14 (docs) only runs after Phase 13 is QA-green.

If at any point during execution an unforeseen design ambiguity appears, I will surface it in chat **before** writing code for it — same discipline as Section 8.

— end of plan —
