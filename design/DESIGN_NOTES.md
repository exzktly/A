# All-Well Redesign v2 — Design Notes

This document explains **why** the v2 mockup looks the way it does. It is a companion to `DESIGN_TOKENS.md` (the *what*) and `PYQT6_NOTES.md` (the *how to build it*).

---

## 1. Problems with the old UI

The legacy All-Well interface had accumulated the standard set of "scientific tool grown organically" problems:

1. **Two competing legends.** The well plate and a matplotlib-style swatch row both told you which well was which trace, in different visual languages. Users had to look at two places to answer one question: "which trace is well A01?".
2. **Top-level plot-type subnav.** A horizontal `Line · Bar · Scatter · Distribution · Heatmap` tab row sat above the figure. It applied to *all* plots at once. Switching one plot's view forced the other to follow, which fought the comparison use case the tool exists for.
3. **Channel selector floating in space.** "Channel: W15" was a global dropdown floating above the figure, disconnected from any specific plot, despite the fact that each subplot can show a different channel.
4. **Mode = Review/Analyze given equal weight in the chrome.** In reality users live in Review ~90% of the time. Giving Analyze co-equal real estate created visual noise and made the home state feel ambiguous.
5. **Well-selection toolbar was cryptic.** "Row…" / "Col…" / "By cond." / "Clear" — abbreviated, lower-cased, with no tooltips. Required institutional knowledge to operate.
6. **Property panel had no scope.** Edits silently applied to "the active plot" with no visual indication of which plot was active. Two-plot comparisons frequently caused accidental cross-edits.
7. **Plot toolbar was always-on and dominated the chrome.** Every plot had a permanent toolbar visible regardless of intent. Combined with title, axes, and legend, the actual data got ~60% of the panel area.
8. **Panels-as-cards but charts-as-everything.** Plot panels had a single SVG that *was* the panel. There was no room for at-a-glance metrics (mean, range, threshold, n) so users had to mentally compute them from the trace.

---

## 2. What v2 changes (and why)

### 2.1 The plate IS the legend
**Change.** Selected wells inherit their trace color. Well A01 looks blue because the blue line *is* well A01. The standalone swatch-row legend is gone.

**Why.** One source of truth for the well↔trace mapping. The plate is already on screen; doubling it elsewhere wastes the user's attention.

**Trade-off.** Color-blind users still need a non-color signal — the well label inside each chip carries through as a fallback, and trace tooltips repeat the well ID.

### 2.2 Per-panel view switcher
**Change.** The horizontal `Line / Bar / Scatter / Distribution / Heatmap` subnav is gone. Each plot panel has its own inline icon switcher in its header. Plot 1 can be a line graph while plot 2 is a heatmap.

**Why.** The whole point of stacking two plots is comparing the same data across different views. Coupling them defeated the feature.

### 2.3 Channel moved into the plot panel
**Change.** "Channel: W15" is now a small chip in each plot's header, swappable per-panel.

**Why.** Channel selection follows the same logic as view-type: it belongs with the plot it affects, not in a global header.

### 2.4 Plots became data cards, not just charts
**Change.** Each plot panel is now: title + metric strip (Wells, Mean, Range, Δ, Threshold) + chart. The chart is one component inside the card, not the entire card.

**Why.** Reading the *card* without looking at the *chart* now tells you the story numerically. Useful when you've zoomed out of the figure or are reviewing many wells.

**Later reversion (matplotlib parity).** When asked to re-align with matplotlib export semantics, the per-panel metric strips and inline view switchers were pulled out and replaced with a **single shared figure canvas** holding both subplots, with one toolbar at the bottom. This matches "one PNG = one figure" export convention. The earlier per-card metric strip is preserved in v2 history under git tags as an option to bring back if export semantics aren't a constraint.

### 2.5 Property panel got scope
**Change.** A segmented control at the top of the property panel — `All / Plot 1 / Plot 2` — explicitly targets edits. Plus a `⌘K` search. Plus a live preview value (swatch, number, or label) in every section header so collapsed groups still show their state.

**Why.** Eliminates the "which plot am I editing?" guess. Search makes a property panel with 40+ controls feel like a property panel with 10.

### 2.6 Smarter well selection
**Change.** "All / None" replaced with **All 96 / Invert / Clear**. Row/column selection is moved into the plate itself — clicking a row letter or column number selects that whole row/column. A "Saved selections" list with colored dots maps each saved set to a condition.

**Why.** The four-button row never told you what the buttons did. Now there are three buttons that say what they do (with tooltips), and the more advanced operations live where they belong — directly on the plate.

### 2.7 Mode demoted
**Change.** Review is the implicit home. Analyze becomes a single dashed-border rail trigger that opens a drawer. The Review/Analyze segmented control is gone.

**Why.** Reflects actual usage. Removes one mental click ("which mode am I in?") from every session.

### 2.8 Hover-only plot toolbar
**Change.** Home / pan / zoom / export / more lives in a hover-revealed icon strip on each panel. Invisible at rest; present when you reach for it.

**Why.** The toolbar is reached for ~5% of the time but consumed ~15% of the panel height permanently. Hover-reveal returns that space to the data.

**Later reversion.** When the single-canvas matplotlib model came back, the per-panel hover toolbar was replaced with one persistent bottom toolbar on the shared figure. The hover-reveal pattern is documented here for cases where individual subplots get isolated panels again.

---

## 3. What's intentionally different from a "modern web" redesign

Several conventional modern-web moves were considered and rejected:

- **No card shadows on internal panels.** Dark-theme scientific UIs read better with hairline borders + flat fills. Shadows here are reserved for *floating* surfaces (drawer, toast, dropdown), where they signal elevation has actual meaning ("this is overlay-z, dismiss me to return").
- **No drop-cap headings or oversized titles.** The information density is the point. Every pixel of chrome competes with data. Type tops out at 17px and that is on purpose.
- **No emoji, no decorative iconography.** Icons are functional (Lucide line icons at 1.75 stroke) and only appear when they replace text or augment a label. Decorative icons in section headers were tried and removed.
- **Tabular numerals everywhere, mono for any numeric readout.** `font-variant-numeric: tnum` on every column of numbers. The plot toolbar coords readout is `JetBrains Mono` not because monospace is fashionable but because the digits stop dancing when you pan.
- **No accent gradients.** The accent (#6B8AFD) is a flat solid. Modern dark UIs love iridescent gradients on primary buttons; here they would compete with the trace colors that are doing the actual signaling work.
- **No motion on data.** Hover-reveals, drawer slide-ins, and tooltips animate. The chart never animates. The data is the data — if a number changes, you want to *see* the change, not see it choreographed.

---

## 4. Open questions / things to validate

- **Plate-as-legend at high well counts.** If a user selects 24 wells, the plate still works as a legend but the eye-trace from chart back to plate gets harder. May need a secondary hover-link (hover trace → highlight well, currently one-way).
- **Saved selections + condition dots.** Assumes a Sample Definitions table exists. If it doesn't, the dot colors fall back to neutral grey and the feature degrades.
- **`⌘K` on the property panel.** Probably should be the global search and not panel-local. Worth testing.
- **The "Invert" affordance.** Power users will love it; novices may not understand the inversion concept. Tooltip helps but real usage will tell.

---

## 5. Reference

| File                              | Purpose                                                              |
|-----------------------------------|----------------------------------------------------------------------|
| `All-Well Redesign v2.html`       | Editable source mockup (CSS inline, fonts external).                |
| `All-Well Redesign v2 (standalone).html` | Self-contained build (fonts + icons inlined, offline-ready).   |
| `DESIGN_TOKENS.md`                | Color/type/spacing/radius/shadow token reference for porting.        |
| `PYQT6_NOTES.md`                  | Catalog of mockup components that need custom Qt widgets.            |
| `DESIGN_NOTES.md`                 | (this file) Why the redesign is shaped this way.                     |
