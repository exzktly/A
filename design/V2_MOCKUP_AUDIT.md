# V2 Mockup Audit

Compares **`design/mockup-decoded.html`** (the canonical decoded mockup) against
`design/DESIGN_NOTES.md`, `design/DESIGN_TOKENS.md`, `design/PYQT6_NOTES.md`,
and `design/PORT_PLAN.md`. The goal is to surface what the design docs miss,
what they get wrong, and what implementation work is still implied but not
tracked.

The mockup contains both a **design-intent comment** at the top of the inline
`<style>` (lines 376–399 — the eight numbered "What changed vs v1" bullets) and
the actual rendered **markup** (body, lines 1229–1973). Where the comment and
the markup disagree, **the markup is what the user has been pointing at as
"the approved design";** the comment captures earlier intent that was reverted
during the v2→reversion→v2-port chain documented in `DESIGN_NOTES.md` §2.4 /
§2.8 and `DECISIONS_NEEDED.md` #1.

Classification key, used on every row:

- **(a) Already addressed in implementation** — code matches mockup or
  conscious deferral already tracked.
- **(b) Add to design docs for tracking** — design call exists or is implicit
  in the mockup but no design doc records it.
- **(c) Add a port task to PORT_PLAN.md** — design is clear, no implementation
  exists, no current task captures the work.
- **(d) Needs a decision from the user** — design docs and mockup disagree, or
  the mockup's two layers (intent comment vs. markup) themselves disagree.

---

## 1. Top-level layout

The mockup is a single CSS grid:

```
.app   grid-template-rows: 44px 1fr 28px        (titlebar / main / statusbar)
.main  grid-template-columns: 260px 1fr 332px   (rail / center / properties)
.rail  flex-column: mode-seg → nav → plate-wrap (plate + presets + saved)
.center flex-column: ctxbar → canvas
.canvas grid-template-rows: 1fr 1fr             (two stacked figure regions)
```

### Findings

| # | Item | What the mockup says | What our docs say | Classification |
|---|---|---|---|---|
| 1.1 | **Section tabs (`Plotting · smFISH · Statistics · Image Table · Segmentation · Review CSV · Sample Definitions · Batch Export`) live in the LEFT RAIL, between the Mode segmented control and the plate.** | `<nav class="nav">` at lines 1274–1284, beneath a "Section" h6 caption. Vertical list of 8 anchors, accent-dim background on the active one, 2-px left accent bar. The `Plotting` row carries a `<span class="count">5</span>` aside. | `PORT_PLAN.md` Table 1 line 26 says "Secondary tab strip … restyle via QSS only (keep `QTabWidget`/`QTabBar`)" — i.e. stay at the top of the centre column. `DECISIONS_NEEDED.md` #7 explicitly resolves "secondary tab strip stays a `QTabWidget`". `OPEN_DECISIONS.md` #3 same. `PYQT6_NOTES.md` §20 puts the TabBar in `CenterPanel.ContextBar`, not the rail. | **(d) decision required** — direct contradiction between the canonical mockup and three resolved design decisions. This is the navigation-restructure the user has been asking about. Either the docs are wrong (then re-resolve the decisions toward the rail) or the mockup is stale (then the docs are right and the mockup needs an annotation). |
| 1.2 | **Mode is a `mode-seg` segmented control with `Review` / `Analyze` at the top of the rail.** | Lines 1265–1271. `Analyze` is a peer segment, *not* a dashed-border rail trigger, *not* a drawer launcher. | `DESIGN_NOTES.md` §2.7 ("Mode demoted") says "Analyze becomes a single dashed-border rail trigger that opens a drawer". `PORT_PLAN.md` Table 1 line 48 same ("dashed-rail trigger + slide-in drawer"). The `nav.analyze` CSS class at line 643 is present but **unused** in the body. | **(d) decision required** — the markup contradicts §2.7, the rationale, and the port-plan row. The Drawer widget is already built and (per this session) wired to the Help button; no Analyze drawer is wired. |
| 1.3 | **Rail width is fixed at 260px.** | `.main { grid-template-columns: 260px 1fr 332px; }` (line 567). Same as titlebar's `.tb-brand` column. | `PORT_PLAN.md` does not specify rail width. `DESIGN_TOKENS.md` does not call out a layout-column constant. | **(b) add to design docs** — minor; a layout-tokens table would catch this and the next row. |
| 1.4 | **Properties panel is 332px wide.** | Same line, third column. | Implementation has the *export-style sidebar* at 575→680 px (the latest fix this session). The mockup's right panel is much narrower. | **(d) decision required** — the export-style sidebar in the current code path is the floating dock that *replaces* the canvas, not a permanent rail. The mockup shows it as a permanent third column, always visible, 332 px. Which model are we porting to: permanent right rail, or current toggle dock? |
| 1.5 | **Titlebar is a single 44px row with three columns** (`.tb-brand 260px` / `.tb-crumb 1fr` / `.tb-actions auto`). Carries: brand logo + `All-Well` wordmark + `v2.4.1` version chip · breadcrumb (`Experiments › 2019 › <file>` with mono file chip) · dataset tail (`· 96 wells · 8 timepoints`) · refresh icon · `Dark`/`Light` segmented theme toggle · primary `Open` button with `⌘O` kbd hint. | Lines 1234–1258. | `PORT_PLAN.md` Table 1 lines 24 + 41 + the v3-decision in §A say: keep native frame, restyle the in-window header strip, **delete the theme combo**, single dark theme. `DESIGN_NOTES.md` §6.5 says "frameless" is the original spec but is **superseded for v1 by the native-frame note**. | Implementation currently has: brand tile + wordmark + dataset chip + StatusDot + Open/Help/Presentation/Refresh icon buttons. Theme switch **deleted** (DECISIONS #4). Breadcrumb (`Experiments › 2019 › …`) and version chip — **not present** in the header. Refresh icon, `⌘O` kbd hint on Open — **not present**. **(c) port tasks**: add breadcrumb display, version pill, `⌘O` shortcut+hint on Open. **(d) decision required**: light theme — DECISIONS #4 deleted the combo, but the mockup still shows it. |
| 1.6 | **Statusbar is a 28px row, three columns**: status text (`● Ready.` green dot + "Properties scoped to all plots · 2 wells · channel W15") · keyboard hint group (`⌘E export · ⌘K find prop`) · tray button (`Log ▴`). | Lines 1965–1976. | Implementation has a status bar with progress + status label, but no scope status / kbd hint group / `Log` tray. | **(c) port task** — populate the statusbar with the three groups; add `⌘E` / `⌘K` keyboard shortcuts. |

---

## 2. The left rail (in order, top to bottom)

```
rail
├── rail-section #1   "Mode" — mode-seg [Review / Analyze]
├── rail-section #2   "Section" h6 + nav [8 vertical items, accent-active]
└── plate-wrap        plate-head + plate-grid + presets + saved
```

| # | Subsection | Mockup detail | Doc coverage |
|---|---|---|---|
| 2.1 | **Mode segmented (Review/Analyze)** | mode-seg pattern (track + checked-pill); see 1.2 above. | Contradicts §2.7 and `PORT_PLAN.md` Table 1 row 48. **(d)** |
| 2.2 | **Section nav** (`Plotting [5]`, `smFISH`, `Statistics`, `Image Table`, `Segmentation`, `Review CSV`, `Sample Definitions`, `Batch Export`) | A flat vertical list of `<a>` rows; the active row has `--accent-dim` bg + a 2-px left accent bar (lines 624–629 of CSS). Inactive rows are muted. Each row has a leading Lucide icon. The `Plotting` row carries a `count` aside ("5") — presumably the count of plot sub-tabs inside Plotting. | Contradicts `PORT_PLAN.md` Table 1 row 26 + DECISIONS #7. The "count chip" sub-behaviour is unique to the rail and has no doc trace. **(d)** for relocation; **(b)** for the count chip. |
| 2.3 | **96-Well Plate** with `plate-head` ("96-Well Plate" h6 + selection chip `2 / 96` with a check icon) | Lines 1286–1295. `sel-chip` is a pill with `--accent-dim` bg and accent text, mono numerics. | Implementation has the WellPlateSelector but the *count chip* is rendered separately ("Selected: N / 96" label, plain text); no chip pill, no check icon. **(c)** port task — add the chip styling + check icon. |
| 2.4 | **Quick-select row** (`All 96`, `Invert`, `Clear`) with tooltips. Below the row, a 1-line tip: *"click a row letter or column number on the plate to select that whole row/column."* | Lines 1297–1305. Three buttons in `.presets`; `Clear` is `class="danger"` (red hover). | Implementation has `All / None` (the legacy v1 toolbar). `Invert` doesn't exist as a control. The tip line is absent. `DESIGN_NOTES.md` §2.6 documents the change (`All 96 / Invert / Clear`) but PORT_PLAN.md doesn't enumerate `Invert`. **(c)** port task — add `Invert`; rename `None` → `Clear`; relabel `All` → `All 96`; add the tip line. |
| 2.5 | **Saved list** (h6 "Saved [3]" + 3 rows). Each row: `dot` (8px square w/ trace colour) + name + meta column (`A01–A04` / `B01–B12` / `12 wells`). Pure read-only here — no kebab, no eye, no drag handle. | Lines 1306–1326. | `DESIGN_NOTES.md` §6.3 *and* `PORT_PLAN.md` Table 1 row 31 *and* the `SavedSelectionsList` widget all describe a much richer interaction model: drag handle / eye / dot / inline rename / count chip / kebab / expandable chips / footer `From selection` + `Import…`. The rail version in the mockup is the **read-only / glance** variant. The full editor lives on the Sample Definitions tab. | **(b) add to design docs** — the rail "Saved" list is a *condensed* variant of the editable SavedSelectionsList. The widget should expose a `compact=True` mode (drop the editing chrome). |

---

## 3. Center column

```
center
├── ctxbar    horizontal subnav [Line / Bar / Scatter / Distribution / Heat Map]
│             + right group [Channel chip · "click a trace to filter" hint · Add panel · Export figure]
└── canvas    grid 1fr 1fr (two stacked figures)
    └── figure (.figure)
        ├── figure-canvas SVG with TWO subplots inside one SVG
        └── figure-toolbar  always-on, three icon groups + coords readout
```

| # | Item | Mockup detail | Doc coverage |
|---|---|---|---|
| 3.1 | **`ctxbar.subnav` is present and horizontal** — exactly the "top-level plot-type subnav" the design-intent comment at line 383 says was *removed*. | Lines 1335–1346. | `DESIGN_NOTES.md` §2.2 says "the horizontal subnav is gone". `DECISIONS_NEEDED.md` #1 says "per-plot cards … each with its own view-switcher". The mockup body markup **disagrees with both**. The hidden block at line 1493 is labelled *"legacy markup retained but hidden so existing script selectors keep working"* — i.e. the per-card markup is the *legacy* in this file. | **(d) decision required — the central nav contradiction.** Either the mockup markup is the source of truth (then we keep `ctxbar.subnav` and walk back DECISIONS #1) or the design comment is (then we delete `ctxbar.subnav` and the mockup's body is stale). Implementation currently follows DECISIONS #1 (per-card view-switchers exist in every plot tab). |
| 3.2 | **Channel selector lives in `ctxbar.right`, not the plot card.** Pill button: trace-coloured dot · `W15 — W1594` · chevron-down. | Line 1341. | `DESIGN_NOTES.md` §2.3 says "Channel moved into the plot panel" (per-panel chip). The mockup contradicts. Implementation currently follows §2.3 — channel selector is in each plot tab's controls strip, not a global header. | **(d) decision required.** |
| 3.3 | **`Add panel` button** in ctxbar. | Line 1343. | `DECISIONS_NEEDED.md` #1 mentions a multi-card "Plot 1 + Plot 2" comparison scope but defers it. No port task. **(c)** *if* multi-card scope is ever in scope. |
| 3.4 | **"click a trace to filter properties" hint pill** in ctxbar. | Line 1342. | No doc coverage. Implies hover/click on a trace narrows the Properties panel scope to "this plot, this trace". | **(b)** doc the interaction; **(c)** port task if we adopt it. |
| 3.5 | **Single shared figure** containing two SVG subplots, ONE always-on `.figure-toolbar` at the bottom. | Lines 1349–1492. The two stacked subplots ("Mean W1594 Intensity" / "Fraction of cells above threshold") share one SVG `viewBox`, one set of axis labels, one toolbar. | Direct contradiction with DECISIONS #1 (per-card). Same as 3.1. **(d)** |
| 3.6 | **Figure toolbar groups**: Group 1 [Home, Back, Forward] · Group 2 [Pan, Zoom-rect] · Group 3 [Configure subplots, Edit axes/curve, Save figure] · then coords readout `x = 4.32 · y = 921.4` (mono, tabular-nums, right-aligned). | Lines 1471–1490. | Implementation has `widgets.MplToolbar` with [Home, Back, Forward, Pan, Zoom, Save] and a coords readout. **Missing**: `Configure subplots`, `Edit axes/curve`. **(c)** port task to add these (or document why they're omitted — Configure-Subplots is currently flagged "Deferred" in the migration table). |
| 3.7 | **`.figure-toolbar` is always-on** (no hover-fade in CSS) but `DESIGN_NOTES.md` §2.8 explicitly says it should be hover-revealed. The reversion note at end of §2.8 says "the single-canvas matplotlib model came back, the per-panel hover toolbar was replaced with one persistent bottom toolbar". | CSS at 828–849. | Same contradiction chain as 3.1, 3.5. Implementation today: always-on `MplToolbar`. **(d)** |
| 3.8 | **No metric-strip between title and chart** in the visible markup. (The legacy plot-card block at 1495+ has one — `Wells · Mean · Range · Δ vs t0 · Threshold` — but it's `hidden`.) | Lines 1494–1606 are inside `<div hidden="">`. | `DESIGN_NOTES.md` §2.4 says metric strip is the v2 change; the reversion note demoted it; DECISIONS #1 re-elevated per-card → metric strip implicitly back. Implementation has **no metric strip on any plot card**. **(d)** if per-card stays, **(c)** to actually build the strip. |
| 3.9 | **No per-card publication/screen toggle** in mockup ctxbar or figure header. | Body markup at 1334–1490. | `DESIGN_NOTES.md` §6.1 says each figure header carries a `Screen` / `Publication` toggle. The mockup precedes the v3 additions; §6.1 was added later. Implementation has this toggle per-card. **(a) already addressed**. |
| 3.10 | **No Stats chip** in mockup ctxbar or figure header. | Body. | `DESIGN_NOTES.md` §6.2 says the figure header has a `Stats · SEM` chip whose click opens a popover. Implementation currently has `make_band_controls` band toggles on the controls row, no Stats chip. **(c)** port task if Stats chip popover is in scope; otherwise **(d)** to formally drop it. |

---

## 4. Right column (Properties panel)

The mockup's Properties panel is **332 px wide** and shows seven sections, all
expanded by default in this static render. Sections, in order:

| # | Mockup section | Header preview chip text | Fields |
|---|---|---|---|
| 4.1 | **Profile & Format** | `Custom · PNG` | `Profile` select (Custom / Publication / Slide / Print A4) · `Format` chips (PNG / SVG / PDF / TIFF). |
| 4.2 | **Axes** | `22 · 22 · 22` | `Axis size` slider · `Tick size` slider · `Title size` slider · `X rotation` chips (0°/30°/45°/90°) · `Tick vis.` chips (Major/Minor/Both/None) · `Tick dir` chips (In/Out/In-Out) · `Tick len` stepper. |
| 4.3 | **Legend** | `On · best · 12pt` | `Show legend` toggle · `In-plot box` toggle · `Size` stepper · `Location` select (Best / Upper right / Upper left / Lower right / Lower left / Outside right). |
| 4.4 | **Lines & Markers** | swatch row (`■ ■`) | inline `preview-strip` (mini SVG of the line+markers) · `Line width` slider · `Marker size` slider · `Marker edge` stepper. |
| 4.5 | **Grid** | `On · 0.25 · ‒‒` | `Show grid` toggle · `Opacity` slider · `Line style` chips (— / - - / · / -·). |
| 4.6 | **Limits & Scale** | `auto · auto` | `X limits` range-pair (two inputs with — separator) · `Y limits` range-pair · `X log` toggle · `Y log` toggle. |
| 4.7 | **Layout** | `Constrained` | `Spacing` chips (Tight / Constrained / Manual) · `Well order` select · `Aspect` range-pair (1.618 × 1.000). |

### Findings

| # | Item | Notes | Classification |
|---|---|---|---|
| 4.A | **Scope segmented (`All` / `Plot 1` / `Plot 2`)** at the top of the panel — `All` selected; `Plot 1` and `Plot 2` carry coloured dots from the trace palette. | Lines 1699–1707. The scope segments map to `--trace-1` / `--trace-2`. Filter-by-trace (3.4) presumably narrows scope further. | `DESIGN_NOTES.md` §2.5 covers it. Implementation: no scope segmented — the export-style sidebar applies globally. **(c)** port task — add the scope segmented to the Properties panel and route edits accordingly. |
| 4.B | **Search input with `⌘K` hint** at the top. | Lines 1709–1713. | Widget `SearchInput` exists in `widgets/`; never mounted. `OPEN_DECISIONS.md` §6.5.7 marks `SearchInput` as "built but unmounted". **(c)** port task — mount above the Properties body and wire local property-filter. (DESIGN_NOTES §4 calls out the open question "⌘K should probably be global".) |
| 4.C | **Live-preview value in every section header** (the `<span class="preview">…</span>` next to each h3). E.g. Axes header shows `22 · 22 · 22`; Grid header shows `On · 0.25 · ‒‒`. | Every `.pg-head` in the body. | `CollapsibleSection.setValueWidget` exists; implementation populates it for **some** sections (per the session work) but not every section per the mockup spec. **(c)** port task — populate header previews for all Properties sections to mockup parity. |
| 4.D | **No `Data` section.** | Mockup body 1717–1955. | `DESIGN_NOTES.md` §6.2 references a "Data" section ("between Data and Appearance"). Neither the mockup body nor §2 of DESIGN_NOTES specifies what `Data` contains. **(b) doc gap** — either remove the `Data`-section reference in §6.2 or add a section spec. **(d)** if user wants it built. |
| 4.E | **No `Statistics` section.** | Mockup body. | `DESIGN_NOTES.md` §6.2 explicitly designs a Statistics section with `Error bars` / `Across` / `Show`. The mockup itself (v2 base) precedes §6.2 (round-2 addition) so it predictably lacks it. Implementation has `make_band_controls` on the plot card controls row, not in Properties. **(c)** port task — add Statistics section per §6.2. |
| 4.F | **No `Annotations` section.** | Mockup body. | `PORT_PLAN.md` Table 1 row 32 lists "Annotations" as an expected Properties section (`Appearance, Threshold, Axes, Legend, Annotations`). Mockup doesn't have it; current code doesn't either. **(b) doc gap** — drop the reference or spec it. |
| 4.G | **No `Threshold` section.** | The mockup figure SVG draws a `threshold · 50 AU` dashed line, but there is no Properties section controlling it. | `PORT_PLAN.md` row 32 lists "Threshold" as a Properties section. The legacy threshold control was a slider beneath the figure (still present in v1 code, removed for the heatmap per this session). **(d)** clarify where threshold lives in v2 — Properties section, figure-card chip popover, or plate-attached control. |
| 4.H | **Profile & Format section** with export profile + format chip group. | Lines 1718–1738. | Implementation has these in the floating "Export Style" sidebar that opens via the per-card sliders button. The mockup has them in the *Properties* panel directly — i.e. there is one unified panel, not "Properties" + "Export Style". **(d) decision required** — unify or keep two? |
| 4.I | **No save-preset affordance shown beyond the bookmark-plus icon in `.props-head`.** | Line 1693. | Implementation has a "Save Preset" button at the bottom of the Export Style sidebar. **(b)** doc the icon-vs-button decision. |
| 4.J | **Reset + Collapse icon buttons in `.props-head`.** | Lines 1694–1695. | Implementation has Reset; no Collapse-the-properties-panel affordance (because the panel is the floating dock, not a permanent column). **(d)** ties to 1.4 / 4.H — depends on the permanent-vs-toggle decision. |
| 4.K | **`Range-pair` widget** (two inputs separated by a glyph). | Used in Limits (X/Y limits, with `–` separator) and Layout (Aspect, with `×` separator). | `widgets/` has no `RangePair` widget. Implementation uses two adjacent QLineEdits. **(b)** add the widget to PYQT6_NOTES catalogue; **(c)** small widget extraction task. |

---

## 5. Component / state details visible in the mockup

| # | Item | Mockup detail | Status |
|---|---|---|---|
| 5.1 | **Selection-chip pattern** (e.g. `2 / 96`, `3` next to "Saved") | small pill, accent-dim bg, accent text, mono numerics, optional leading icon | Implementation uses plain `QLabel`s here. **(b)** add a `SelectionChip` (or extend `IconButton`) note in `PYQT6_NOTES.md`. |
| 5.2 | **`kbd` glyphs in primary buttons + statusbar** (`⌘O` on Open, `⌘K` on search, `⌘E ⌘K` in statusbar) | `<span class="kbd">⌘O</span>` styled in mono with subtle bg | No coverage in PYQT6_NOTES or PORT_PLAN. **(b)** + **(c)** — doc the pattern, build a kbd-hint helper, wire shortcuts. |
| 5.3 | **Theme segmented in titlebar (`Dark` / `Light`)** | Lines 1251–1254. | DECISIONS #4 deleted the theme combo entirely; mockup still shows it. **(d)** confirm: stay deleted, or re-add as `Dark / Light / System` per `DESIGN_NOTES.md` §6.5? |
| 5.4 | **Breadcrumb in titlebar** with mono file chip and trailing dataset stat (`· 96 wells · 8 timepoints`) | Lines 1240–1247. | Not implemented; tracked as 1.5/**(c)** above. |
| 5.5 | **Version pill (`v2.4.1`) next to wordmark.** | Line 1239. | Not implemented. **(c)** trivial port task. |
| 5.6 | **The `preview-strip` row at the top of Lines & Markers** — an inline mini-SVG showing the current line+marker style as a live preview. | Lines 1838–1844. | Not implemented. **(b)** + **(c)** — doc the pattern (it's distinct from the header `<span class="preview">` chip), and add a port task or accept the gap. |
| 5.7 | **Well states** — only `default`, `hover`, `selected[data-trace=N]`. No `disabled` / `no-data` state in the mockup CSS (`.well`, `.well:hover`, `.well.sel`). | CSS 700–717. | Implementation has additional states ("no data", "muted/hidden") inherited from v1. **(b)** doc the additional state set in `PORT_PLAN.md` Table 2 row "WellPlate"; **(a)** already implemented. |
| 5.8 | **Plate cut-corner ornament** (`.plate::before` triangle clipping top-left corner to rail bg). | CSS 685–692. | Not present in `WellPlateSelector`. Pure decoration. **(b)** note it; **(c)** optional port task. |
| 5.9 | **`tray` button in statusbar** (`Log ▴`) | Line 1976. | Not implemented. **(c)** port task — wire to a collapsible log drawer or panel. Drawer widget already exists. |
| 5.10 | **No tooltips, no popovers, no modals, no dialogs in the mockup body.** Hover-only interactions are implied by `:hover` CSS rules. The design-intent comment at line 397 ("hover-only icon strip + kebab") implies a kebab `Popover` but no kebab is *visible* in this static render. | — | The `Popover` widget exists in implementation. **(a)** the widget; **(d)** what specifically uses it: stats popover (§6.2), saved-selections kebab (§6.3), LUT selector (§6.4), titlebar theme switcher (§6.5). Each needs its own port task. |
| 5.11 | **Trace-color rendering on selected wells** uses a `radial-gradient` (lighter top-left fall to deeper bottom-right) + inset highlight/shadow. | CSS 707–717. | Implementation in `WellPlateSelector` uses a flat fill + accent ring. **(b)** doc the spec; **(c)** small visual-fidelity port task. |
| 5.12 | **Plate column/row labels are clickable** (the mockup JS at line 2010–2014 toggles whole row/column on click — "click a row letter or column number" wired). | Body script. | Implementation: `WellPlateSelector.setRowColumnSelectable(True)` exists and is enabled. **(a) already addressed**. |
| 5.13 | **Mode-seg, scope-seg, ctxbar-subnav, mode-seg use the same script** (one querySelectorAll('.chips, .seg, …').forEach) — i.e. they all share the "one-of-N" pattern. | Body script line 2065–2074. | Implementation has these as separate widgets (`SegmentedControl`, `ChipGroup`). **(a) already addressed**. |

---

## 6. Modals, dialogs, drawers, overlays

Direct mockup audit: **none rendered**. The static mockup does not include any
floating surfaces. Doc-implied overlays:

| Source | Overlay | Status |
|---|---|---|
| `DESIGN_NOTES.md` §2.7 | Analyze drawer (rail trigger) | Not built (mode-seg used Analyze instead); **(d)** 1.2 |
| `DESIGN_NOTES.md` §6.2 | Stats popover from figure header chip | Not built; **(c)** |
| `DESIGN_NOTES.md` §6.3 | Saved-selections kebab popover | Built (kebab → QMenu); **(a)** |
| `DESIGN_NOTES.md` §6.4 | Custom color picker popover (SV square + hue strip) | Built (`ColorPickerPopover`); not mounted on the curated swatch row's Custom tile (`ColorSwatchRow` lacks the Custom escape hatch). **(c)** |
| `DESIGN_NOTES.md` §6.4 | LUT selector popover (4-category list) | Built (`LutSelector`); **(a)** |
| `DESIGN_NOTES.md` §6.5 | Theme switcher popover from titlebar sun/moon | Not built; tied to 1.5/5.3 **(d)** |
| `DESIGN_NOTES.md` §6.5 | Brand-logo dropdown menu (Open / Recent / Preferences / About / Quit) | Not built. **(c)** if titlebar gains a brand-logo menu. |
| `PORT_PLAN.md` Table 1 row 49 | Toast | Built + wired this session (`_toast` helper). **(a)** |
| Implementation | Help drawer (info button → quick-help) | Built this session. **(a)** |

---

## 7. The mockup vs. our resolved decisions — summary of contradictions

Listed once, with cross-references back into the table.

| Decision in our docs | What the mockup shows | Section |
|---|---|---|
| `PORT_PLAN.md` line 26 + `DECISIONS_NEEDED.md` #7 + `OPEN_DECISIONS.md` #3: secondary tab strip stays `QTabWidget` in the centre column | 8 section tabs live in the LEFT RAIL above the plate | **1.1 / 2.2** |
| `DESIGN_NOTES.md` §2.7: Analyze becomes a dashed-rail drawer trigger | Analyze is the second segment in a `Review / Analyze` mode-seg at the top of the rail | **1.2 / 2.1** |
| `DECISIONS_NEEDED.md` #1: per-plot cards with hover toolbars and per-card view-switchers | Single shared figure canvas, two subplots inside one SVG, single always-on bottom toolbar, horizontal `ctxbar.subnav` for plot type | **3.1 / 3.5 / 3.7** |
| `DESIGN_NOTES.md` §2.3: channel chip per-card | Single global channel chip in `ctxbar.right` | **3.2** |
| `PORT_PLAN.md` Table 1 row 41 + `DECISIONS_NEEDED.md` #4 (resolved): theme combo deleted; single dark theme | `Dark / Light` segmented in titlebar | **5.3** |
| `DECISIONS_NEEDED.md` #4: keep native window frame, restyle in-window header | Custom titlebar; the markup doesn't reveal whether the OS frame is hidden, but the chrome (44 px row with brand-tile + version pill + breadcrumb + dataset chip + theme seg + Open w/ kbd) maps to the original frameless v2 spec, not to the simpler restyled header | **1.5 / 5.4 / 5.5** |

For each of these the question is the same: **was the mockup superseded by a
later decision (in which case the doc trail is correct and the mockup is now
out of date)** *or* **were the later decisions wrong and the mockup is what
should be built?** A single answer can be given per row.

---

## 8. Items the mockup specifies that are absent in **all** docs

Pure design surface area without any markdown-doc trace:

- **§1.1** — vertical section nav in the left rail (the navigation restructure).
- **§1.4** — properties panel as a *permanent* third column (332 px), not a floating dock.
- **§1.5** — breadcrumb (`Experiments › 2019 › <file>`) with mono file chip + dataset tail.
- **§1.5 / §5.5** — version pill (`v2.4.1`) next to wordmark.
- **§1.5** — refresh action in the titlebar actions group.
- **§1.6** — statusbar three-column layout with scope-status / kbd-hint group / tray button.
- **§2.2** — count-aside on a nav row (`Plotting [5]`).
- **§2.3** — selection chip styling (pill, accent-dim, mono, leading check).
- **§2.4** — "Invert" preset + the rail tip-line below the preset row.
- **§2.5** — read-only **compact** variant of `SavedSelectionsList` (rail Saved list).
- **§3.3** — `Add panel` ctxbar button.
- **§3.4** — `click a trace to filter properties` interaction.
- **§3.6** — `Configure subplots` and `Edit axes/curve` figure-toolbar buttons.
- **§4.A / 4.B / 4.C** — Scope segmented + `⌘K` search + universal header previews on every Properties section.
- **§4.K** — `RangePair` widget pattern.
- **§5.1** — `SelectionChip` pattern (count pill).
- **§5.2** — `kbd` hint glyphs on buttons + statusbar; `⌘O` / `⌘K` / `⌘E` shortcuts.
- **§5.6** — `preview-strip` inline live-preview row at the top of Lines & Markers.
- **§5.7 / §5.11** — exact well-state palette (no `disabled` / `no-data` in mockup) + radial-gradient selected-well rendering.
- **§5.8** — plate cut-corner ornament.
- **§5.9** — `Log ▴` tray button in the statusbar.

Each of these is **(b)** for doc tracking and most are **(c)** for a port task.

---

## 9. Items our docs specify that the mockup does **not** show

Reverse direction — design-doc commitments without mockup support:

| Doc reference | Item | Likely classification |
|---|---|---|
| `DESIGN_NOTES.md` §6.2 | `Statistics` Properties section | **(c)** valid round-2 addition; mockup predates it. |
| `DESIGN_NOTES.md` §6.2 | `Stats · SEM` chip popover in figure header | **(c)** same. |
| `DESIGN_NOTES.md` §6.1 | `Screen` / `Publication` per-card toggle + `preview only` chip | **(a)** implemented; mockup predates the v3 round. |
| `DESIGN_NOTES.md` §6.4 | LUT selector with searchable popover, 4 categories | **(a)**. |
| `DESIGN_NOTES.md` §6.4 | Custom-tile escape hatch on `ColorSwatchRow` | **(c)** still owed. |
| `DESIGN_NOTES.md` §6.5 | Brand-logo dropdown (Open / Recent / Preferences / About / Quit) | **(c)** if titlebar gains a brand menu; **(d)** otherwise. |
| `PORT_PLAN.md` Table 1 row 32 | "Annotations" Properties section | **(d)** drop or spec. |
| `PORT_PLAN.md` Table 1 row 32 | "Threshold" Properties section | **(d)** see 4.G. |
| `DESIGN_NOTES.md` §6.3 | `Saved selections` editor with full toolbar (drag, eye, recolour, kebab, expand, footer) | **(a)** the widget; the rail in the mockup shows only the *compact* read-only view. |

---

## 10. Recommended next actions (no code change here — proposing only)

1. **Resolve the navigation restructure (§1.1 / §2.2).** One user decision
   either way unlocks 6–8 downstream port tasks.
2. **Resolve the single-canvas-vs-per-card question for v2 (§3.1 / §3.5 /
   §3.7).** Three docs (DESIGN_NOTES.md §2.4 / §2.8, DECISIONS_NEEDED.md #1)
   disagree with the mockup body. Re-confirm DECISIONS #1, or revert.
3. **Resolve "permanent Properties rail vs. floating dock" (§1.4 / §4.H /
   §4.J).** Affects whether the export-style sidebar becomes a column or
   stays a dock.
4. **Resolve the theme switcher (§5.3) and titlebar fidelity (§1.5).** Either
   the mockup's titlebar elements (breadcrumb, version pill, Light/Dark seg,
   refresh, `⌘O`) are port tasks, or DECISIONS #4 trumps and these are
   formally dropped.
5. **Annotate `design/mockup-decoded.html`** with a header comment listing
   which post-mockup decisions supersede which parts of its body markup — so
   future readers know which contradictions are deliberate.
6. **Add the missing tracking sections to design docs** for items in §8 (all
   the (b) rows): rail section nav, compact `SavedSelectionsList`, statusbar
   layout, `RangePair`, `SelectionChip`, `kbd` hints, `preview-strip`, well
   gradient rendering.
7. **After the four resolutions above, add the resulting (c) tasks to
   PORT_PLAN.md** under a new "Mockup-parity gaps" section.
