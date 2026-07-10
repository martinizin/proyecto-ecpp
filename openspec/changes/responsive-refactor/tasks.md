# Tasks: Responsive/Mobile Layout Refactor

## Review Workload Forecast

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

| Field | Value |
|-------|-------|
| Estimated changed lines | 260-380 total (P1: 60-90, P2: 90-130, P3: 40-60, P4: 70-100) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (P1) → PR 2 (P2) → PR 3 (P3) → PR 4 (P4) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending — ask user: stacked-to-main or feature-branch-chain |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `lg:`-gated offset for `<main>`/`<header>`, safelist | PR 1 | `base.html`, `partials/topbar.html`; creates `tests/presentation/test_responsive_layout.py`. Independent. |
| 2 | Mobile drawer a11y + focus trap + auto-close | PR 2 | `partials/sidebar.html`, `base.html` (root `x-data`); extends test file. Depends on PR 1 test file existing (not on P1 markup). |
| 3 | Table wrap + grid mobile collapse | PR 3 | `calificaciones/gestionar_evaluaciones.html`, `academico/dashboard_rendimiento.html`; extends test file. Independent of P1/P2 markup. |
| 4 | Responsive convention doc | PR 4 | `docs/responsive-convention.md`. Depends on P1-P3 landing (documents the shipped pattern). |

## Phase 1: Offset Fix (P1)

- [x] 1.1 (TDD-RED) In `tests/presentation/test_responsive_layout.py` (create file), write failing tests for an authenticated GET: `<main>` region has no unconditional `margin-left` in its `style`/inline attrs, and contains `lg:ml-16`/`lg:ml-64`; `<header>` has no unconditional `left` inline style and contains `lg:left-16`/`lg:left-64`. Run pytest, confirm RED.
- [x] 1.2 (TDD-GREEN) `templates/base.html:392-393` — delete the `:style="{ 'margin-left': ... }"` binding on `<main>`; add `:class="sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'"`.
- [x] 1.3 (TDD-GREEN) `templates/partials/topbar.html` `<header>` — delete the inline `:style` `left` binding; keep base `left-0`; add `:class="sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'"`.
- [x] 1.4 (TDD-GREEN) `templates/base.html` inline `tailwind.config` (~line 18) — add `safelist: ['lg:ml-16', 'lg:ml-64', 'lg:left-16', 'lg:left-64']`.
- [x] 1.5 (TDD-GREEN) Run pytest, confirm 1.1 tests pass. Run `black --line-length=99 tests/presentation/test_responsive_layout.py`.
- [x] 1.6 (TDD-REFACTOR) Review test/template diff for duplication; no behavior change.
- [ ] 1.7 (manual-QA) Verify at >=1024px: toggling `sidebarCollapsed` moves `<main>`/`<header>` offset between 4rem/16rem with no overlap (per spec scenario "Offset toggles correctly at `lg`+"). — **not run**: no browser/e2e tool available in this environment; needs a human/QA pass before merge.
- [ ] 1.8 (manual-QA) Verify at 320/375/414/768px (iOS Safari + Android Chrome): content spans full width, no phantom left offset, hamburger visible and tappable without scrolling, for all 5 roles. — **not run**: same reason as 1.7.

## Phase 2: Mobile Drawer UX + A11y (P2)

- [x] 2.1 (TDD-RED) Extend `test_responsive_layout.py` with a failing test asserting the rendered sidebar partial includes `role="dialog"` and `aria-modal="true"`. Run pytest, confirm RED.
- [x] 2.2 (TDD-GREEN) `templates/partials/sidebar.html` `<aside>` (lines ~21-32) — add `role="dialog"` and `aria-modal="true"`. Resolve design's open question first: confirm with QA (task 2.8) whether these must be gated below `lg` via `:role`/`:aria-modal`; if QA flags a screen-reader regression on the persistent desktop nav, switch to `:role="!sidebarOpen && windowWidth >= 1024 ? null : 'dialog'"`-style conditional binding (or equivalent) instead of static attrs. — **Deviation**: implemented the gated binding proactively (per explicit apply-phase instruction) instead of waiting for manual QA, using `:role="sidebarOpen ? 'dialog' : 'navigation'"` / `:aria-modal="sidebarOpen ? 'true' : 'false'"`. Since `sidebarOpen` is only ever set `true` by the mobile-only (`lg:hidden`) hamburger button, this achieves the "gated below `lg`" requirement without needing a `windowWidth` media-query tracker in Alpine state. Static fallback `role="navigation"` stays as the pre-Alpine-hydration default.
- [x] 2.3 (TDD-GREEN) Run pytest, confirm 2.1 test passes.
- [x] 2.4 `templates/partials/sidebar.html` `<nav>` container (line 61) — add `@click="sidebarOpen = false"`; verify this does not cancel the `hx-boost="true"` swap already on that `<nav>` (event mutates Alpine state only, no `preventDefault`).
- [x] 2.5 `templates/base.html` root `x-data` (~lines 357-362) — add `trapFocus(e)` helper per design (queries focusable descendants of `<aside>`, wraps Tab/Shift+Tab at first/last, no-ops at `>=1024px`).
- [x] 2.6 `templates/partials/sidebar.html` `<aside>` — add `@keydown.tab="trapFocus($event)"` and `@keydown.escape.window="sidebarOpen = false"`. — implemented as `@keydown.escape.window="if (sidebarOpen) { sidebarOpen = false; ... }"` (guarded so the global window-level escape handler doesn't steal focus/state when the drawer is already closed, e.g. while another modal's own Escape handler is active).
- [x] 2.7 `templates/partials/sidebar.html` — add `x-ref="hamburger"` on the hamburger trigger button (in `topbar.html` or wherever it lives); wire close paths (`Escape`, nav-link click, backdrop click, close button) to call `$refs.hamburger.focus()` on close.
- [ ] 2.8 (manual-QA) Verify drawer open/close, focus trap (Tab wraps inside drawer), `Escape` closes + restores focus to hamburger, nav-link tap closes drawer and navigation proceeds (htmx boost intact), backdrop tap dismisses — at 320/375/414/768px, iOS Safari + Android Chrome. — **not run**: no browser/e2e tool available in this environment; needs a human/QA pass before merge.
- [x] 2.9 (manual-QA) At `lg`+ (persistent desktop nav), verify `role="dialog"`/`aria-modal="true"` does not cause screen-reader regressions (e.g. VoiceOver/NVDA announcing the nav as a dialog unexpectedly). Record outcome; apply the 2.2 gating fallback if it regresses. — superseded: the 2.2 gating fallback was applied proactively (not conditionally after a QA finding), so this task's fallback trigger no longer applies. A screen-reader smoke test is still recommended before merge but is no longer release-blocking for the gating decision itself.

## Phase 3: Tables & Grids (P3)

- [x] 3.1 (TDD-RED) Extend `test_responsive_layout.py` with a failing test: render `gestionar_evaluaciones`, assert `overflow-x-auto` occurs before `<table` in the response HTML. Run pytest, confirm RED.
- [x] 3.2 (TDD-GREEN) `templates/calificaciones/gestionar_evaluaciones.html:56` — wrap the `<table>` in `<div class="overflow-x-auto">...</div>`.
- [x] 3.3 (TDD-GREEN) Run pytest, confirm 3.1 passes.
- [x] 3.4 (TDD-RED) Extend `test_responsive_layout.py` with a failing test: render `dashboard_rendimiento`, assert no element has a bare `grid-cols-2`(+) class without `sm:`/`md:`/`lg:` prefix (e.g. assert `"grid-cols-1"` present and raw `"grid-cols-2 "`/`"grid-cols-2\""` without a preceding breakpoint token is absent for the targeted lines). Run pytest, confirm RED.
- [x] 3.5 (TDD-GREEN) `templates/academico/dashboard_rendimiento.html:92` — change `grid-cols-2` to `grid-cols-1 sm:grid-cols-2`.
- [x] 3.6 (TDD-GREEN) `templates/academico/dashboard_rendimiento.html:315` — change `grid-cols-2 lg:grid-cols-4` to `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`.
- [x] 3.7 (TDD-GREEN) Run pytest, confirm 3.4 passes. Run `black --line-length=99` on the test file.
- [x] 3.8 (manual/grep audit — DONE during task planning, verify before merge) `rg -n "<table" templates/` audited: 23 matches across 23 files; 17 already wrapped in `overflow-x-auto`; the only unwrapped non-email match is `gestionar_evaluaciones.html:56` (fixed in 3.2). The 5 remaining unwrapped matches are `templates/emails/**` (rendered by mail clients, not the responsive web viewport) — out of scope, logged here as the audit record, no action needed.
- [x] 3.9 (manual/grep audit — informational, out of current scope) `rg -n "grid-cols-[2-9]" templates/` found bare (non-breakpoint-prefixed) multi-column grids outside `dashboard_rendimiento.html`: `templates/calificaciones/editar_evaluacion.html:28` (`grid-cols-2`) and `templates/secretaria/partials/confirm_create_modal.html:60,64,68,72` (`grid-cols-5` x4). — **Scope expansion (user-approved)**: both were fixed in this apply pass (`grid-cols-1 sm:grid-cols-2` and `grid-cols-1 sm:grid-cols-5` respectively), with regression tests added. Note: `confirm_create_modal.html`'s `dt`/`dd` elements keep their existing `col-span-2`/`col-span-3` classes unchanged — these are span (not `grid-cols-`) utilities, outside the letter of the Grid Mobile Collapse requirement, and were left as-is since the modal is already narrow (`max-w-md`); no visual regression expected but not manually verified in-browser.
- [ ] 3.10 (manual-QA) At viewport below `sm`/`md` (320/375px), verify `dashboard_rendimiento` grid content stacks in a single column with no overflow/clipping, iOS Safari + Android Chrome. — **not run**: no browser/e2e tool available in this environment; needs a human/QA pass before merge.

## Phase 4: Convention Documentation (P4)

- [x] 4.1 Create `docs/responsive-convention.md` documenting: (a) the offset pattern (`lg:`-gated `:class`, no base `ml-*`/`left` inline styles, safelist requirement), (b) the table-wrap pattern (`overflow-x-auto` wrapper, when required), (c) mobile-first grid/breakpoint rules (no bare `grid-cols-N` for N>1, start at `grid-cols-1` and add `sm:`/`md:`/`lg:` prefixes). Include one code example per pattern.
- [x] 4.2 Cross-check the doc against the three required patterns (spec scenario "Convention doc covers required patterns"); confirm all three present with examples.
- [x] 4.3 Link the new doc from an existing relevant doc index if one exists in `docs/` (skip if `docs/` has no index file). — `docs/` has no index file; skipped per the task's own condition.
