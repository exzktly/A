# Gallery layout proposal (Phase 6.5.11a — gate)

`widgets/gallery.py` grew organically — one flat 2-column `QGridLayout` of
`("Title", builder)` cards in roughly the order widgets were built. With the
6.5.2–6.5.10 additions it's now 23 cards in arbitrary order, and some
extensions (binding adapters, the v2 `SavedSelectionsList`, the `TitleBar` /
`PlotCard` extensions) aren't called out as *extensions* — they're just cards.

This doc proposes the final organization. **No code changes until you approve
this** — then 6.5.11b reorganizes `gallery.py` to match, runs it, screenshots,
fixes layout/visual issues, re-checks the binding test, and Phase 6.5 is done.

---

## 1. Goals

1. **Coverage is obvious.** A reader (you, a future contributor) can scan the
   gallery and see *every* custom widget (6.5 deliverable #1) and *every*
   extension demonstrated (deliverable #2) — without diffing against the plan.
2. **Grouped, not flat.** Section headers so related widgets sit together
   (form controls vs. overlays vs. plate/plot vs. chrome).
3. **Each card states what it demonstrates.** Especially extensions: the card
   shows the *new* behaviour (binding round-trip, recolour popover, frameless
   toggle, publication theme, …), not just "here's the widget".
4. **Host-dependent demos are honest.** Things that need a top-level window
   (`Toast`, `Drawer`, `WindowResizeGrips`, the frameless `TitleBar`) say so and
   open a real window from a button rather than pretending to embed.
5. **No behaviour regressions.** The existing `main()` / `build_gallery()`
   entry points stay; `python widgets/gallery.py` still just works.

---

## 2. Proposed structure

`build_gallery()` becomes: titlebar strip (unchanged) → a `QScrollArea` whose
content is a `QVBoxLayout` of **sections**. Each section = a header label
(`#Caption`-ish, uppercase, with a hairline rule) followed by a responsive
grid of cards (2 columns on a normal width; the existing `_card()` helper is
reused unchanged).

```
build_gallery()
├─ header strip  (title + "Toast" + "Open drawer" buttons)          [unchanged]
└─ scroll → VBox of sections:
   §1  Form controls & inputs
   §2  Navigation & disclosure
   §3  Buttons, icons & status
   §4  Colour
   §5  Overlays & transient surfaces
   §6  Plate & plot
   §7  Window chrome
   §8  Binding harness            (a single wide card — see §4 below)
```

### §1  Form controls & inputs
| Card | Demonstrates |
|---|---|
| `ToggleSwitch` | on/off paint; **`bindingAdapter()`** noted |
| `StyledSlider` | custom groove/handle; **`bindingAdapter()`** noted |
| `Stepper` | ± buttons + field; **`bindingAdapter()`** noted |
| `SegmentedControl` | options + `setCurrentByData`; **`bindingAdapter()`** |
| `ChipGroup` | exclusive **and** multi rows; `checkedData`/`setCheckedData`; **`bindingAdapter()`** |
| `SearchInput` | placeholder + hint count |

### §2  Navigation & disclosure
| Card | Demonstrates |
|---|---|
| `PillTabBar` | tab switching |
| `CollapsibleSection` | expand/collapse, nested content |

### §3  Buttons, icons & status
| Card | Demonstrates |
|---|---|
| `IconButton` | icon set, checkable, with-text variants |
| `StatusDot` | the status palette + labels |
| `BrandTile` | the four-quadrant mark |
| `EmptyState` | icon + message + action |

### §4  Colour
| Card | Demonstrates |
|---|---|
| `GradientStrip` | `(pos,colour)` stops · flat list · callable · reversed |
| `LutSelector` | trigger + reverse/reset; popover w/ search `n / m`; `lutChanged` read-out |
| `ColorSwatchRow` | curated swatches **+ recents + Custom tile → `ColorPickerPopover`**; picked-colour read-out |
| `ColorPickerPopover` | SV square + hue strip + hex/alpha + recents; `colorPicked`/`colorCommitted` read-out |

### §5  Overlays & transient surfaces
| Card | Demonstrates |
|---|---|
| `Popover` | side × align buttons; auto-flip; Esc/outside dismiss |
| `HoverToolbarOverlay` | hover-to-reveal toolbar over a host |
| `Toast` | *(button in the header strip — needs a window)* |
| `Drawer` | *(button in the header strip — needs a window)* |

### §6  Plate & plot
| Card | Demonstrates |
|---|---|
| `WellPlateSelector` | selection / passive modes, colours, header clicks, the extended API |
| `SavedSelectionsList` | **v2 editable list** — rename / recolour popover / reorder (handle + kebab) / hide / expand-to-chips; `selectionsChanged` read-out; fed a contract-shaped `list[dict]` |
| `PlotCard` | toolbar + coords readout; **figure header + `Stat·Error` chip → stats popover**; **`setPlotTheme("screen"\|"publication")` toggle** (re-plots with `traceColors()`); read-out |

### §7  Window chrome
| Card | Demonstrates |
|---|---|
| `TitleBar` | breadcrumb/saved; **window controls · brand→menu · theme popover · ghost Open/⌘O**; **`setFramelessMode()` toggle**; **`should_use_frameless()` + `frameless_source()` read-out** |
| `WindowResizeGrips` | doc + a button that opens a frameless test window with draggable edges/corners |

### §8  Binding harness
A single full-width card "Binding round-trip" that imports
`widgets.binding_check`, runs `binding_check.run()` in-process (it returns
pass/fail per widget), and renders the result table (✓/✗ per widget) so the
deliverable-#4 guarantee is *visible in the gallery*, not just a CLI script.
(If running it in-process is awkward, fall back to a card that says "run
`python widgets/binding_check.py`" and shows the last known result — but
in-process is the goal.)

---

## 3. Card chrome (unchanged) + small additions

- Keep `_card(title, builder)` as-is (the `#Panel` framed box with a title and
  a try/except that shows the traceback inside the card if a builder throws).
- Add a tiny optional second arg: `_card(title, builder, note=None)` — when a
  `note` is given it's rendered as a `#Caption` line under the title. Most cards
  that currently bake their own "(…)" `QLabel` at the bottom move that string
  into `note` for consistency. (Pure cosmetics; skip if it bloats the diff.)
- `_section(title)` helper → returns the header label + rule widget.

## 4. Responsiveness

Keep the fixed 2-column grid per section (the window is resizable; 2 columns at
1080 px is the current behaviour and is fine). Not proposing a reflowing
flow-layout — out of scope, and the plan's 6.5.11 is "run / screenshot / fix",
not "rewrite the layout engine". If a card is naturally wide (the binding
harness, maybe `PlotCard`), it spans both columns (`grid.addWidget(card, r, 0, 1, 2)`).

## 5. Coverage checklist (what 6.5.11b must verify is present)

**New widgets (6.5.2–6.5.6, +6.5.1 harness):** `Popover` ✓ · `GradientStrip` ✓ ·
`WindowResizeGrips` ✓ · `LutSelector` ✓ · `ColorPickerPopover` ✓ ·
`binding_check` harness card ✓
**Extensions (6.5.1, 6.5.7–6.5.10):** binding adapters on Toggle/Slider/Stepper/
Segmented/Chip (noted on each §1 card) ✓ · `ColorSwatchRow` Custom-tile+recents ✓ ·
`SavedSelectionsList` v2 editable ✓ · `TitleBar` controls/brand/theme/frameless ✓ ·
`PlotCard` header/stats-popover/publication-theme ✓
**Pre-6.5 widgets:** still all present, just regrouped.

## 6. Out of scope (explicitly not doing in 6.5.11b)

- No new widgets; no behaviour changes to widgets (only their gallery cards).
- No theme/light-mode switch for the gallery chrome itself.
- No persistence of gallery state.
- No flow/masonry layout.

---

**Decision needed:** approve this grouping & the §8 in-process binding-harness
card (or tell me to keep the flat grid / change the sections / drop §8), then
6.5.11b reorganizes, runs, screenshots, fixes, and closes Phase 6.5.
