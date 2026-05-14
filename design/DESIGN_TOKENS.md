# All-Well Redesign v2 — Design Tokens

Source of truth: `All-Well Redesign v2.html` (look in the `:root { … }` block at the top of the inline `<style>`). All custom properties live there; everything below is named in `--kebab-case` exactly as it appears in CSS.

This document is organized for porting to **PyQt6** — Qt does not have CSS custom properties, so the recommended path is to declare these as a Python module of named constants (or as `QPalette` roles + a `QStyleSheet` template with `.format()`/`Template` substitution). Notes on Qt mapping are inline.

---

## 1. Color tokens

### 1.1 Surfaces (backgrounds, in increasing elevation)

| Token            | Hex       | Purpose                                                                         | Qt mapping                                |
|------------------|-----------|---------------------------------------------------------------------------------|-------------------------------------------|
| `--bg-titlebar`  | `#0A0E15` | Top window chrome (custom title bar / breadcrumb row).                          | `QPalette.Window` for the title frame.    |
| `--bg-app`       | `#0B0F17` | App canvas — the deepest backdrop behind every panel.                           | `QPalette.Window` (main window).          |
| `--bg-rail`      | `#0E131C` | Left rail (mode/tools) + right Properties rail base.                            | Custom role; use as dock-widget bg.       |
| `--bg-panel`     | `#131A24` | Cards and sub-panels sitting on the rail (e.g. plate card, plot card).          | `QPalette.Base`.                          |
| `--bg-elevated`  | `#1A2230` | Default button/input fill; "elevated" controls on a panel.                      | `QPalette.Button`.                        |
| `--bg-hover`     | `#212B3B` | Hover state for buttons, list rows, chips.                                      | `:hover` in QSS.                          |
| `--bg-active`    | `#2A3548` | Pressed / selected state (segmented control "on", chip "on", row selected).    | `:checked`, `:pressed` in QSS.            |

### 1.2 Borders / dividers

| Token              | Hex       | Purpose                                                                  | Qt mapping                          |
|--------------------|-----------|--------------------------------------------------------------------------|-------------------------------------|
| `--border-subtle`  | `#1B2331` | Hairlines between sections within a panel; titlebar bottom border.       | `QFrame` line, `1px solid` in QSS.  |
| `--border`         | `#2A3343` | Default control border (buttons, inputs, chips).                         | Default border in QSS.              |
| `--border-strong`  | `#3B475C` | Emphasized border — hover ring on inputs, panel splitters.               | Hover/focus border.                 |

### 1.3 Text

| Token                | Hex       | Purpose                                                                  | Qt mapping                          |
|----------------------|-----------|--------------------------------------------------------------------------|-------------------------------------|
| `--text-primary`     | `#E6E9EF` | Body copy, headings, primary labels.                                     | `QPalette.WindowText`, `Text`.      |
| `--text-secondary`   | `#98A2B3` | Labels-on-controls, secondary metadata, subtitles.                       | `QPalette.PlaceholderText` (alt).   |
| `--text-muted`       | `#5F6B7C` | Hint text, inactive segmented labels, axis tick labels.                  | `QPalette.Disabled.Text`.           |
| `--text-faint`       | `#404B5C` | Decorative separators ("·", "/"), disabled glyphs.                       | Even more disabled / decorative.    |

### 1.4 Accent (interactive / brand)

| Token            | Hex       | Purpose                                                                      | Qt mapping                         |
|------------------|-----------|------------------------------------------------------------------------------|------------------------------------|
| `--accent`       | `#6B8AFD` | Primary buttons, focus ring base, active tab underline, slider track fill.   | `QPalette.Highlight`.              |
| `--accent-hover` | `#84A0FF` | Hover state for primary buttons.                                             | `:hover` over Highlight.           |
| `--accent-dim`   | `#2C3A66` | Dimmed accent for low-emphasis selected backgrounds.                         | Tinted selection bg.               |
| `--accent-fg`    | `#F0F4FF` | Text/icon color on primary (accent-filled) buttons.                          | `QPalette.HighlightedText`.        |

### 1.5 Status

| Token       | Hex       | Purpose                                                  | Qt mapping                  |
|-------------|-----------|----------------------------------------------------------|-----------------------------|
| `--success` | `#4ADE80` | "Saved" indicator, OK toasts, healthy status dot.        | Success role.               |
| `--warn`    | `#F59E0B` | Warning chip, threshold marker label.                    | Warning role.               |
| `--danger`  | `#F87171` | Destructive button text ("Clear"), error toast.          | Danger role.                |

### 1.6 Trace / data colors

These are categorical colors keyed to **wells** on the plate. Well A01 always gets trace-1, A02 always gets trace-2, etc. Selecting a well stamps that color into the chart. Wire these as a categorical palette in your Qt chart layer (e.g. `QChart.setTheme` plus a custom series-color list).

| Token         | Hex       | Purpose                                       |
|---------------|-----------|-----------------------------------------------|
| `--trace-1`   | `#5B9BF8` | First series (well A01 by default).           |
| `--trace-2`   | `#F26B6B` | Second series (well A02 by default).          |
| `--trace-3`   | `#4ADE80` | Third series.                                 |
| `--trace-4`   | `#F5A524` | Fourth series.                                |
| `--threshold` | `#F5A524` | Threshold dashed line + threshold metric chip. (Same hex as trace-4; kept under a distinct semantic name so threshold restyling does not move trace-4.) |

### 1.7 Plot chrome

| Token          | Hex       | Purpose                                              |
|----------------|-----------|------------------------------------------------------|
| `--plot-grid`  | `#1F2733` | Gridlines inside the matplotlib-style figure.        |
| `--plot-spine` | `#3A4658` | Axis spines (left & bottom).                         |

### 1.8 Selected-well gradients (NOT plain colors — for fidelity)

Selected wells use radial gradients to read as "lit chips". Each trace has its own 3-stop gradient. In PyQt6 use `QRadialGradient` centered at 35% / 30% with the same three stops.

| Well trace | Stop 0 (highlight) | Stop 0.55 (mid) | Stop 1 (deep) |
|------------|--------------------|------------------|----------------|
| trace-1    | `#84B6FF`          | `#4F87E6`        | `#2C5BB0`      |
| trace-2    | `#FF9B9B`          | `#E45656`        | `#B02C2C`      |

Additional wells extend the same pattern around trace-3 / trace-4 hues.

### 1.9 Translucent overlays (used inline, not in `:root`)

These appear inside `box-shadow` and gradient declarations and have no token name; keep them as **named constants** in your Qt build so they stay editable:

| Constant suggestion       | Value                            | Where used                                              |
|---------------------------|----------------------------------|---------------------------------------------------------|
| `INSET_HILITE`            | `rgba(255,255,255,0.28–0.30)`    | Top inset highlight on selected wells (chip "lit" look).|
| `INSET_SHADOW`            | `rgba(0,0,0,0.30)`               | Bottom inset shadow on selected wells.                  |
| `SUCCESS_GLOW`            | `rgba(74,222,128,0.12)`          | Halo around the "saved" status dot.                     |
| `FOCUS_RING_RGBA`         | `rgba(107,138,253,0.35)`         | Focus outline on inputs/sliders (`--ring-focus`).       |
| `DROP_SHADOW_MD`          | `rgba(0,0,0,0.35)`               | Soft drop shadow `--sh-2`.                              |
| `INNER_LINE_DK`           | `rgba(0,0,0,0.40)`               | Inner-line shadow `--sh-1`.                             |

---

## 2. Typography

### 2.1 Font families

| Token          | Stack                                                                              | Use                              | Qt mapping                          |
|----------------|------------------------------------------------------------------------------------|----------------------------------|-------------------------------------|
| `--font-sans`  | `'Inter', -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif`         | All UI text by default.          | `QFont("Inter", …)` w/ system fbk.  |
| `--font-mono`  | `'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace`                          | Filenames, numeric readouts (x/y coords in plot toolbar), data chips. | `QFont("JetBrains Mono", …)`. |

Embed `Inter` and `JetBrains Mono` via Qt's `QFontDatabase.addApplicationFont(...)` if you need pixel parity off the web.

### 2.2 Font sizes

The scale is intentionally tight — this is an information-dense desktop tool.

| Token          | Size  | Intended use                                                                    |
|----------------|-------|---------------------------------------------------------------------------------|
| `--fs-caption` | 11 px | Section labels (uppercase eyebrow "h6"), tick labels, secondary chips.          |
| `--fs-small`   | 12 px | Buttons, segmented control text, breadcrumb, status bar, most input text.      |
| `--fs-body`    | 13 px | Default body, list rows, property labels.                                       |
| `--fs-emph`    | 14 px | Emphasized inline labels (brand wordmark, control values).                      |
| `--fs-h3`      | 15 px | Panel sub-titles ("Quick select", "Selection").                                 |
| `--fs-h2`      | 17 px | Plot card titles, dialog titles.                                                |

### 2.3 Weights

Three weights are used. Map to `QFont.Weight`:

| Weight        | CSS value | Used for                                                       | Qt              |
|---------------|-----------|----------------------------------------------------------------|-----------------|
| Regular       | 400       | Body, paragraph text.                                          | `Weight.Normal` |
| Medium        | 500       | Buttons, labels-on-controls, breadcrumb file chip.             | `Weight.Medium` |
| Semibold      | 600       | Brand wordmark, primary-button text, titles, threshold marker. | `Weight.DemiBold` |
| Bold          | 700       | Loaded for completeness; rare in UI (large numeric readouts).  | `Weight.Bold`   |

### 2.4 Line height & letter-spacing

| Property           | Value         | Use                                                       |
|--------------------|---------------|-----------------------------------------------------------|
| Default leading    | `1.45`        | Body text in `body { font: 400 13px/1.45 var(--font-sans); }`. |
| Tight leading      | `1` or `1.1`  | Button labels, single-line chips.                         |
| Tight tracking     | `-0.01em`     | Brand wordmark; nothing else.                             |
| Wide tracking      | `+0.08em`     | Uppercase eyebrow `h6` section labels (rail headers).     |
| OpenType features  | `'cv11','ss01','tnum'` | Inter stylistic alternates + tabular numbers (so column alignment in metric strips holds). In Qt: `QFont.setFeatures([…])` or `setStyleStrategy`. |

---

## 3. Spacing scale

Linear 4-px scale. Stored as `--s-{n}`.

| Token   | Value | Common use                                                            |
|---------|-------|-----------------------------------------------------------------------|
| `--s-1` | 4 px  | Icon ↔ label gap inside a button; tightest gutter.                    |
| `--s-2` | 8 px  | Default control gap (chip spacing, segmented buttons).                |
| `--s-3` | 12 px | Field-row gap inside a properties section; padding inside cards.      |
| `--s-4` | 16 px | Padding inside panels, gap between section blocks.                    |
| `--s-5` | 20 px | Slightly larger panel padding.                                        |
| `--s-6` | 24 px | Outer gutter between major panels (plate ↔ figure).                   |
| `--s-8` | 32 px | Rare — large empty-state padding.                                     |

Qt mapping: use as `QLayout.setContentsMargins(s4, s4, s4, s4)` and `QLayout.setSpacing(s2)` consistently across forms.

---

## 4. Border radius

| Token       | Value | Use                                                                       |
|-------------|-------|---------------------------------------------------------------------------|
| `--r-xs`    | 3 px  | File-chip in breadcrumb, brand logo tile, tiny inline indicators.         |
| `--r-sm`    | 5 px  | Buttons, inputs, chips — the dominant radius across the UI.               |
| `--r-md`    | 8 px  | Cards (plot card, plate card, properties panel sections).                 |
| `--r-lg`    | 12 px | Floating overlays (toasts, drawers, modal dialogs).                       |
| `--r-pill`  | 999 px| Status dot rings, fully-rounded count badges.                             |

Qt mapping: `border-radius` in QSS, or `QPainterPath.addRoundedRect(…)` for custom-drawn surfaces.

---

## 5. Shadows / elevation

Two semantic shadow tokens plus a focus-ring.

| Token          | Value                                                | Use                                                            |
|----------------|------------------------------------------------------|----------------------------------------------------------------|
| `--sh-1`       | `0 1px 0 rgba(0,0,0,0.40)`                           | Hairline drop on segmented-control "on" pill; subtle separation between adjacent controls. |
| `--sh-2`       | `0 4px 12px rgba(0,0,0,0.35)`                        | Floating overlay shadow (drawer, dropdown, toast).             |
| `--ring-focus` | `0 0 0 2px rgba(107,138,253,0.35)`                   | Focus outline on inputs, steppers, sliders (replaces native `outline`). |

PyQt6 has no native `box-shadow`. Implement with `QGraphicsDropShadowEffect` (set `blurRadius`, `offset`, `color`):

```python
shadow = QGraphicsDropShadowEffect()
shadow.setBlurRadius(12)
shadow.setOffset(0, 4)
shadow.setColor(QColor(0, 0, 0, int(0.35 * 255)))
widget.setGraphicsEffect(shadow)
```

For the focus ring, draw a 2px outline inside `paintEvent` or set `border: 2px solid rgba(107,138,253,0.35)` on `:focus` in QSS. Insets used by the "lit well" effect are not box-shadows in Qt — render them with `QPainter` overlays (a top highlight line and a bottom shadow line) on the gradient-filled well rectangle.

---

## 6. Component-specific notes

A few non-token visual specs you'll need when reconstructing controls 1:1:

- **Buttons**
  - Height 28 px (implicit from `padding: 6px 10px` + 12-px text + 1-px border).
  - Default: `bg-elevated` fill, `border-subtle` border, `text-primary` text.
  - Primary: `accent` fill+border, `accent-fg` text, `600` weight; hover swaps to `accent-hover`.
  - Ghost: transparent until hover, then `bg-panel`.
  - Icon size 14 px, stroke-width 1.75 (Lucide icons).

- **Segmented control**
  - Track: `bg-panel` with `1px solid border-subtle`, radius `--r-sm`.
  - Item "on": `bg-elevated` + `--sh-1`.

- **Inputs / steppers**
  - Height 28 px, radius `--r-sm`, mono-numeric text uses `tabular-nums` feature.
  - Focus: border becomes `--accent`, plus `--ring-focus` outer ring.

- **Plot card**
  - Card: `bg-panel`, radius `--r-md`, `1px solid border-subtle`.
  - Inside: title row (17 px / 600), then metric strip (11 px caption + 13 px values), then SVG figure with `--plot-grid` gridlines, `--plot-spine` axes, threshold dashed at `--threshold`.
  - Toolbar at bottom: 28 px row of icon buttons grouped by matplotlib convention (home/back/forward · pan/zoom · configure/save), right-aligned `x = … · y = …` coords in `--font-mono`.

- **Well plate**
  - Wells: 24 × 24 px circles, 4 × 4 px gap.
  - Default fill `--bg-elevated`, border `--border`.
  - Selected: radial gradient per trace index (see §1.8), plus inset highlight/shadow combo.
  - Row letters (A–H) and column numbers (1–12) use `--text-muted` 11 px; they're clickable headers that select the whole row/column.

---

## 7. Suggested Python token module (sketch)

```python
# tokens.py
from PyQt6.QtGui import QColor, QFont

class C:
    BG_APP        = QColor("#0B0F17")
    BG_RAIL       = QColor("#0E131C")
    BG_PANEL      = QColor("#131A24")
    BG_ELEVATED   = QColor("#1A2230")
    BG_HOVER      = QColor("#212B3B")
    BG_ACTIVE     = QColor("#2A3548")
    BG_TITLEBAR   = QColor("#0A0E15")

    BORDER_SUBTLE = QColor("#1B2331")
    BORDER        = QColor("#2A3343")
    BORDER_STRONG = QColor("#3B475C")

    TEXT_PRIMARY   = QColor("#E6E9EF")
    TEXT_SECONDARY = QColor("#98A2B3")
    TEXT_MUTED     = QColor("#5F6B7C")
    TEXT_FAINT     = QColor("#404B5C")

    ACCENT       = QColor("#6B8AFD")
    ACCENT_HOVER = QColor("#84A0FF")
    ACCENT_DIM   = QColor("#2C3A66")
    ACCENT_FG    = QColor("#F0F4FF")

    SUCCESS = QColor("#4ADE80")
    WARN    = QColor("#F59E0B")
    DANGER  = QColor("#F87171")

    TRACE = ["#5B9BF8", "#F26B6B", "#4ADE80", "#F5A524"]
    THRESHOLD = QColor("#F5A524")

    PLOT_GRID  = QColor("#1F2733")
    PLOT_SPINE = QColor("#3A4658")

class S:
    S1, S2, S3, S4, S5, S6, S8 = 4, 8, 12, 16, 20, 24, 32

class R:
    XS, SM, MD, LG, PILL = 3, 5, 8, 12, 999

class T:
    CAPTION, SMALL, BODY, EMPH, H3, H2 = 11, 12, 13, 14, 15, 17

def font(size=T.BODY, weight=QFont.Weight.Normal, mono=False):
    f = QFont("JetBrains Mono" if mono else "Inter", size)
    f.setWeight(weight)
    return f
```

Build your `QStyleSheet` template by formatting in these constants, e.g.:

```python
QSS = f"""
QPushButton {{
    background: {C.BG_ELEVATED.name()};
    border: 1px solid {C.BORDER_SUBTLE.name()};
    color: {C.TEXT_PRIMARY.name()};
    padding: 6px 10px;
    border-radius: {R.SM}px;
    font-size: {T.SMALL}px;
}}
QPushButton:hover  {{ background: {C.BG_HOVER.name()}; }}
QPushButton:pressed{{ background: {C.BG_ACTIVE.name()}; }}
"""
```

---

## 8. Where each token actually appears

If you need to spot-check what a token controls, search the inline `<style>` block of `All-Well Redesign v2.html` for the token name. Every usage is direct (`var(--token)`); there are no chained aliases.

---

## 9. Additions (round 2 — addressing port gaps)

New tokens introduced by `All-Well Additions v3.html` to cover functional areas the v2 mockup didn't address (plot theme, publication export, free-form color picker, LUT selector, native-titlebar fallback). All other tokens above are unchanged.

### 9.1 Publication-preview surface

Used when the user toggles **Publication preview** in the figure header, and as the default background for **exported** figures. This is a *plot-canvas* theme, not an app-chrome theme — the surrounding panel stays dark even while the figure interior is white. In matplotlib, swap `rcParams` (`figure.facecolor`, `axes.facecolor`, `axes.edgecolor`, `xtick/ytick.color`, `text.color`, `grid.color`) to these values.

| Token              | Hex       | Purpose                                                                     |
|--------------------|-----------|-----------------------------------------------------------------------------|
| `--pub-bg`         | `#FFFFFF` | Figure facecolor — pure white for print/paper.                              |
| `--pub-bg-subtle`  | `#F8F9FB` | Off-white for axes facecolor when a slight inset reads better than pure white.|
| `--pub-text`       | `#1A1D24` | Title/label text on the white surface.                                      |
| `--pub-text-muted` | `#4C5360` | Tick labels, secondary annotations.                                         |
| `--pub-grid`       | `#E5E7EB` | Gridlines in publication mode.                                              |
| `--pub-spine`      | `#4C5360` | Axis spines in publication mode (slightly heavier than `--pub-text-muted` to anchor the plot). |

Publication-mode trace colors are darkened variants of `--trace-*` (deeper blue `#1F4FB0`, deeper red `#B02C2C`, etc.) chosen for AA contrast against `--pub-bg`. Maintain a parallel `TRACE_PUB = [...]` list in `tokens.py`.

### 9.2 Token module additions

Append to `tokens.py`:

```python
class CPub:
    BG          = QColor("#FFFFFF")
    BG_SUBTLE   = QColor("#F8F9FB")
    TEXT        = QColor("#1A1D24")
    TEXT_MUTED  = QColor("#4C5360")
    GRID        = QColor("#E5E7EB")
    SPINE       = QColor("#4C5360")

    TRACE = ["#1F4FB0", "#B02C2C", "#2E8C50", "#B5781A"]
```

No new spacing, radius, shadow, or type tokens were needed — round-2 additions reuse the existing scale.
