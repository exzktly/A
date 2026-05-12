# Porting the Approved Mockup to Your Framework

A step-by-step plan for handing the redesign to Claude Code and getting a clean, faithful port — not a "we converted the HTML and lost half the design" port.

The HTML mockup is a *target*, not a spec. Claude Code needs help translating target → spec → code. Each step below is its own conversation turn (or its own PR) with its own review gate.

---

## Step 1 — Establish the design tokens in your framework's language first

Before touching any widget, translate the CSS custom properties from the mockup into whatever your framework uses for theming. For PyQt that's a QSS stylesheet plus a Python dict of color/spacing constants. For Tkinter it's a theme dict or `ttk.Style` configuration.

**Prompt:**

> Read the approved HTML mockup. Extract every design token (colors, typography sizes/weights, spacing values, border radii, shadows) and produce a single `theme.py` (or equivalent) that defines them as constants, plus a base stylesheet that applies the foundational tokens app-wide. Don't touch any widget code yet — I want to review the tokens first.

This is the foundation. If the tokens are wrong, everything built on them is wrong. Reviewing them in isolation is fast.

---

## Step 2 — Component inventory and mapping

Now map mockup components to current codebase components, identifying what's reusable, what needs to be replaced, and what's missing.

**Prompt:**

> Compare the approved mockup to the current UI code. Produce a table with three columns: (1) mockup component, (2) current code equivalent (file and class/function), (3) port strategy — one of 'restyle existing', 'rebuild existing', 'new component', 'delete'. Don't write any code yet. Flag anything in the mockup that has no clear equivalent or that will need architectural changes.

This catches the hard parts early. The "rebuild" and "new component" entries are where most of the work lives, and you want to know about them before you start.

---

## Step 3 — Port one component end-to-end as a pattern

Pick the riskiest or most distinctive component (for All-Well, probably the well plate selector or a property panel section) and port just that one, fully, including its integration into the main window. This becomes the reference pattern for everything else.

**Prompt:**

> Port the [well plate selector] component from the mockup to our codebase. Produce the new widget class, integrate it into the main window where the current selector lives, and make sure it actually runs. The goal is to establish the pattern we'll follow for the rest of the components — so prioritize code clarity and structural quality over speed. After it's working, write a short note describing the patterns established (file organization, naming, how styling is applied, how state flows) that we'll reuse for the other components.

Why one at a time, end-to-end: a half-ported app is unrunnable and unreviewable. One fully-ported component is testable, screenshottable, and gives you a concrete pattern to critique before it's repeated 15 times.

---

## Step 4 — Port the remaining components against the established pattern

Now batch the rest, but with explicit reference to the pattern.

**Prompt:**

> Following the patterns established in the well plate selector port (see [file]), now port the property panel sections. Each section (Profile & Format, Axes, Legend, etc.) should be a separate widget class composed into a container. Maintain consistency with the established naming and styling approach.

Do these one section/area at a time, not all at once. Review each before moving on. The temptation is to say "now port everything else" — resist it. You'll get a sprawling diff that's hard to review and easy to ship with regressions.

---

## Step 5 — The matplotlib integration (this is its own beast)

Matplotlib plots embedded in a Qt/Tk app are the trickiest part of the port because the plot styling has to match the chrome but matplotlib has its own styling system. Treat this as a dedicated step.

**Prompt:**

> The mockup shows plots with dark backgrounds matching the panel chrome, custom-styled axes, and a redesigned toolbar replacing the default matplotlib navigation toolbar. Produce: (1) a matplotlib rcParams configuration or stylesheet that makes plots match our design tokens, (2) a custom navigation toolbar widget that replaces NavigationToolbar2QT with the redesigned controls from the mockup, (3) a wrapper class for embedding plots so styling is applied consistently everywhere we use them.

This will probably require iteration. Matplotlib's styling system has quirks (fonts, tick formatting, legend backgrounds) that don't map cleanly to CSS thinking.

---

## Step 6 — Visual regression check

After everything is ported, do a side-by-side check against the mockup.

**Prompt:**

> Take a screenshot of the running app and compare it to the approved mockup. List every visual difference you can identify, organized by severity (breaks the design intent / noticeable / minor). For each, propose a fix. Don't fix anything yet — I want to triage first.

This is where you catch the "it's mostly right but the property panel padding is off and the toggle states look wrong" issues. Triaging the list lets you decide what's worth fixing vs what's acceptable drift.

---

## Step 7 — Behavior parity check

Visual port done, but does it still work? Verify that every interaction in the old app still works in the new one.

**Prompt:**

> Produce a checklist of every user interaction in the original app (selecting wells, switching tabs, editing properties, exporting, etc.). For each, verify it still works in the ported version. Flag anything that's broken or where the behavior changed unintentionally.

This catches the things that quietly broke during the visual port — a signal that got disconnected, a state that's no longer wired up, a callback that's pointing at the old widget.

---

## Two meta-tips for the whole sequence

**Commit between every step.** Each step above should be its own commit (or PR). A redesign port is a long chain of changes and you want clean rollback points. Tell Claude Code to commit after each successful step.

**Run the app between every step.** "Did Claude Code produce something that runs?" is a different question from "did Claude Code produce reasonable-looking code?" Catch broken builds at the step boundary, not at the end.

---

## Failure conditions to watch for

- The tokens file has hardcoded values scattered across widget files → Step 1 wasn't done properly; fix the foundation before continuing
- A component "ports" but its parent layout breaks → integration wasn't actually tested; require running screenshots, not just code
- Matplotlib plots still look like default matplotlib → Step 5 was skipped or rushed; the rcParams must be applied globally before any figure is created
- The new app looks great but a button no longer does anything → Step 7 catches this, but only if you actually run through the checklist manually
