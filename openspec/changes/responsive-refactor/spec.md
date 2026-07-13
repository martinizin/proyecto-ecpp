# Responsive/Mobile Layout Refactor Specification (responsive-layout)

## Purpose

Defines observable requirements for the new `responsive-layout` capability: the
authenticated shell (`<main>`, topbar `<header>`, sidebar drawer) and data
tables/grids MUST render usably from 320px up, without regressing `lg`+
desktop behavior. Grouped by the proposal's PR slices (P1-P4).

**Testing note**: each scenario is marked **TDD-guarded** (asserted via pytest
+ Django test client on rendered markup — structural, not visual) or
**manual-QA** (interaction/pixel correctness verified against the documented
320/375/414/768/1024px x iOS Safari/Android Chrome matrix). No e2e tool is
available, so JS runtime behavior and visual rendering cannot be pytest-gated;
this mirrors the proposal's explicit testing strategy and is a spec-level
constraint, not a gap.

## Requirements

### Requirement: Main/Header Offset Gated to `lg` Breakpoint
Below `lg`, `<main>` and `<header>` SHALL NOT carry an unconditional inline
`margin-left`/`left` offset. At `lg`+, the offset SHALL follow
`sidebarCollapsed` (4rem collapsed / 16rem expanded) via `lg:`-prefixed
Tailwind classes.

#### Scenario: Rendered markup has no unconditional inline offset (TDD-guarded)
- GIVEN an authenticated GET request rendered with the Django test client
- WHEN the response HTML for `<main>` and `<header>` is parsed
- THEN neither element's `style` attribute sets `margin-left`/`left` unconditionally
- AND both elements' `class` attributes contain `lg:`-prefixed offset classes

#### Scenario: Offset toggles correctly at `lg`+ (manual-QA)
- GIVEN a viewport >=1024px with `sidebarCollapsed` toggled
- WHEN the sidebar is expanded and collapsed
- THEN the `<main>`/`<header>` offset visually matches 16rem/4rem with no overlap

### Requirement: Full-Width Content and Reachable Hamburger Below `lg`
Below `lg`, `<main>` and the topbar SHALL use the full viewport width, and the
hamburger trigger SHALL be fully visible and tappable.

#### Scenario: Mobile viewport shows full-width content (manual-QA)
- GIVEN a viewport of 320/375/414/768px on iOS Safari or Android Chrome
- WHEN an authenticated page loads for any of the 5 roles
- THEN content spans full width with no phantom left offset
- AND the hamburger icon is visible and tappable without scrolling

### Requirement: Mobile Drawer Dialog Semantics
The mobile sidebar drawer SHALL expose `role="dialog"` and `aria-modal="true"`
while open.

#### Scenario: Drawer markup exposes dialog semantics (TDD-guarded)
- GIVEN the sidebar partial is rendered
- WHEN the drawer container markup is inspected
- THEN it includes `role="dialog"` and `aria-modal="true"` attributes

### Requirement: Drawer Interaction and Focus Management
Below `lg`, tapping any sidebar nav link SHALL close the drawer. While open,
focus SHALL be trapped inside it, `Escape` SHALL close it, and closing SHALL
restore focus to the hamburger trigger. The backdrop SHALL remain and dismiss
the drawer on tap.

#### Scenario: Nav tap closes drawer (manual-QA)
- GIVEN the drawer is open on a mobile viewport
- WHEN the user taps a sidebar nav link
- THEN the drawer closes and navigation proceeds

#### Scenario: Escape closes drawer and restores focus (manual-QA)
- GIVEN the drawer is open and focus is trapped inside it
- WHEN the user presses `Escape`
- THEN the drawer closes and focus returns to the hamburger trigger

### Requirement: Table Horizontal Scroll Wrapper
Every data `<table>` under `templates/**` SHALL render inside an
`overflow-x-auto` (or equivalent) scroll wrapper.

#### Scenario: `gestionar_evaluaciones` table is wrapped (TDD-guarded)
- GIVEN the `gestionar_evaluaciones` view is rendered
- WHEN the response HTML is parsed
- THEN the `<table>` element has an `overflow-x-auto` ancestor

#### Scenario: Remaining templates audited (manual-QA / grep audit)
- GIVEN a grep audit of `templates/**` for `<table>` elements
- WHEN each match is checked
- THEN each is confirmed wrapped in `overflow-x-auto` or logged as a follow-up

### Requirement: Grid Mobile Collapse
Multi-column grids SHALL NOT use a bare (non-breakpoint-prefixed)
`grid-cols-N` (N>1) class; `dashboard_rendimiento` grids SHALL default to a
single column below `sm`/`md` and expand at the appropriate breakpoint.

#### Scenario: No bare multi-column grid classes (TDD-guarded)
- GIVEN the `dashboard_rendimiento` view is rendered
- WHEN the response HTML is parsed
- THEN no element has a bare `grid-cols-2`(+) class without an `sm:`/`md:`/`lg:` prefix

#### Scenario: Grid collapses visually on mobile (manual-QA)
- GIVEN a viewport below `sm`/`md`
- WHEN `dashboard_rendimiento` loads
- THEN grid content stacks in a single column with no overflow/clipping

### Requirement: Responsive Convention Documented
A short responsive convention (offset pattern, table-wrap pattern,
mobile-first grid/breakpoint rules) SHALL exist under `docs/` to prevent
regressions in new templates.

#### Scenario: Convention doc covers required patterns (manual-QA)
- GIVEN the convention doc is reviewed
- WHEN checked against the offset, table-wrap, and grid-breakpoint patterns
- THEN all three are documented with a code example each

## Non-Goals
`base_auth.html` iOS keyboard watch-item, custom Tailwind breakpoints/CDN
migration, `localStorage sidebarCollapsed` reset, and any non-visual/
business-logic change are out of scope (see proposal).
