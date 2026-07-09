## Exploration: Responsive/mobile layout breakage (responsive-refactor)

### Current State
Authenticated pages use `templates/base.html` with a fixed-left-sidebar shell (`templates/partials/sidebar.html`, `templates/partials/topbar.html`). The sidebar is collapsible on desktop (`w-64` <-> `w-16`, state `sidebarCollapsed`, persisted in `localStorage`) and off-canvas on mobile (`-translate-x-full` unless `sidebarOpen`, toggled via hamburger). Unauthenticated pages use a separate `templates/base_auth.html` (login/2FA/reset) which does NOT include sidebar/topbar and is structurally fine for mobile. Tailwind is pure CDN (`cdn.tailwindcss.com/3.4.17`) with an inline `tailwind.config` (theme.extend only: colors/fontFamily/boxShadow, no custom breakpoints) duplicated verbatim in both base.html and base_auth.html. htmx boost swaps only `#main-content`; Alpine state (`sidebarOpen`, `sidebarCollapsed`) lives on `<body>`, outside the swapped region, so it correctly survives boosted navigation.

### Root Cause (CONFIRMED — validates user hypothesis)
1. `templates/base.html:392-393` — `<main>` has an Alpine `:style` binding applied unconditionally regardless of viewport:
   `:style="{ 'margin-left': sidebarCollapsed ? '4rem' : '16rem' }"`
   Inline styles always win over Tailwind classes and are NOT gated by any `lg:` breakpoint check.
2. `templates/partials/topbar.html:7` — same defect on the fixed header:
   `:style="{ 'left': sidebarCollapsed ? '4rem' : '16rem' }"`

On mobile (<1024px), the sidebar itself is correctly off-canvas (`-translate-x-full`, only overridden by `lg:translate-x-0` — sidebar.html:22-29), so it occupies zero width when closed. But `<main>` and `<header>` still permanently reserve 16rem (256px, expanded) or 4rem (64px, collapsed) of left space via inline styles that ignore breakpoints. On a 375px-wide phone this leaves ~119px (or ~311px) for all page content, and pushes the topbar — which contains the ONLY mobile hamburger trigger — mostly or fully off-screen, making it hard/impossible to open the menu. This is a genuine regression introduced by the collapsible-sidebar feature (both bindings compute the same 4rem/16rem values the desktop collapse toggle uses, with no responsive gate).

### Secondary/Contributing Defects Found
- `templates/partials/sidebar.html`: none of the nav `<a>` links inside `nav.sidebar-nav` set `sidebarOpen = false`. Only the explicit close button (line 50) and the backdrop `@click` (line 14) close the drawer. On mobile, tapping a nav item boosts navigation but leaves the drawer open over the new page until the user manually dismisses it. (UX defect, not root cause.)
- Mobile drawer (`<aside>`) lacks `role="dialog"`/`aria-modal="true"` when open, no focus trap, no `Escape`-to-close binding. A11y gap explicitly called out in the exploration brief.
- `templates/calificaciones/gestionar_evaluaciones.html:56` — has `<table class="w-full text-sm text-left">` with NO `overflow-x-auto` wrapper. Verified by diffing all templates containing `<table>` (23, incl. 6 irrelevant email templates) against those wrapping with `overflow-x-auto` (17) — this is the one production-relevant page missing the wrapper. All other list/table pages (usuario_list, ant/listado, registrar_calificaciones, mi_libreta, detalle_validacion, auditoria_calificaciones, supervision, registrar_asistencia, historial_asistencia, tipo_licencia_list, periodo_list, mi_horario, dashboard_rendimiento, asignatura_list) correctly wrap tables.
- `templates/academico/dashboard_rendimiento.html:92,315` — `grid-cols-2` stat-card grids with no single-column mobile fallback (2 cols may be tight at 320-375px but is a minor issue, not breakage).
- `templates/copilot/widget.html` — NOT a defect: chat panel already uses `max-w-[calc(100vw-2rem)]` and `max-h-[calc(100vh-3rem)]`, safe on narrow phones.
- `templates/base_auth.html` — NOT affected by the sidebar bug (separate template, no sidebar/topbar included). Structurally sound (`px-4` wrapper, `max-w-md` card, responsive `px-6 sm:px-8` padding). Minor watch-item: `h-screen overflow-hidden` on `<body>` could clip a long form (e.g. `registro.html`) combined with a mobile on-screen keyboard, but this is unrelated to the reported "breaks badly" complaint and out of primary scope.
- Grids across `usuarios/dashboard.html` and `reportes/hub.html` correctly use mobile-first `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3/4` patterns — no defect there.
- The collapse-toggle floating button (sidebar.html:529-544) is correctly gated `hidden lg:flex` — not a bug.

### Affected Areas
- `templates/base.html` (line 392-393) — root cause, `<main>` margin-left
- `templates/partials/topbar.html` (line 4-10) — root cause, `<header>` left offset (also hides the mobile hamburger)
- `templates/partials/sidebar.html` — secondary: nav links don't close mobile drawer; drawer lacks focus-trap/aria-modal/Escape handling
- `templates/calificaciones/gestionar_evaluaciones.html` (line 56) — missing `overflow-x-auto` table wrapper
- `templates/academico/dashboard_rendimiento.html` (lines 92, 315) — `grid-cols-2` without mobile-1-col fallback (low severity)
- `templates/base_auth.html` — verified NOT affected (separate shell), low-severity watch item only

### Approaches
1. **Surgical/minimal fix** — Gate `<main>`/`<header>` offsets behind `lg:`: replace unconditional inline `:style` bindings with Tailwind `:class` toggling (`lg:ml-16`/`lg:ml-64` with no base margin, so offset is 0 below `lg` and correct at `lg+`) — pure CSS, no JS matchMedia needed. Add `sidebarOpen=false` handling on nav-link taps. Wrap `gestionar_evaluaciones.html` table in `overflow-x-auto`.
   - Pros: small diff (~4 files), directly fixes the confirmed regression, low risk, fast, fits CDN-Tailwind (JIT class detection works fine client-side).
   - Cons: no reusable pattern to prevent recurrence; doesn't add a11y hardening unless added as explicit line items; other undiscovered mobile issues may remain (audit was grep-based, not full manual QA).
   - Effort: Low.

2. **Systematic shared responsive layer** — Same root-cause fix as #1, PLUS: a documented/reusable pattern for any future fixed-position element needing sidebar-aware offset; a `.overflow-x-auto` table-wrapper convention enforced via review checklist or lightweight CI grep check; full focus-trap + `aria-modal` + `Escape` handling for the mobile drawer; audit/normalize bare `grid-cols-2` usages.
   - Pros: prevents recurrence of this defect class, raises a11y baseline, catches systemic gaps beyond the one found table.
   - Cons: larger surface area, slower to ship, harder to fit the project's own 400-line PR review budget (openspec/config.yaml Review Workload Guard), higher regression risk touching more templates.
   - Effort: Medium-High.

3. **Staged hybrid (RECOMMENDED)** — Ship approach 1 as a small, urgent PR first (fixes the reported "breaks badly" bug + the one missed table). Follow with a second change/PR for the systemic hardening items from approach 2 (drawer a11y, table-wrap convention, grid audit).
   - Pros: fastest fix for the actual user complaint; keeps each PR within the project's existing 400-line review budget and chained-PR conventions (already codified in `openspec/config.yaml`); doesn't block urgent fix behind broader hardening scope.
   - Cons: requires discipline to actually schedule/ship the follow-up change instead of treating "mobile works now" as done.
   - Effort: Low (PR1) + Medium (PR2).

### Recommendation
Approach 3 (staged hybrid). The project already enforces `strict_tdd: true` and a 400-line PR review budget in `openspec/config.yaml`; bundling the urgent regression fix with broader a11y/table-convention hardening risks blowing that budget and delaying the fix users are actively complaining about. Ship the root-cause fix + the one missed table wrap first; schedule hardening separately.

### Risks
- Strict TDD is active project-wide (`openspec/config.yaml`: `strict_tdd: true`, `test_command: pytest`), but the test layers show **e2e/browser testing is "not planned"** (no playwright/selenium). There is no automated way to assert real viewport/CSS rendering. Proposal phase MUST decide the testing strategy for this template/Alpine/CSS-only change — options: (a) pytest + Django test client + HTML/class-string assertions (e.g., assert rendered `<main>` output does NOT contain the unconditional inline margin-left string, assert `lg:` prefixed classes are present) as a regression guard without full browser rendering, or (b) explicit manual-QA exception documented in the proposal. This is a hard blocker for "RED→GREEN→REFACTOR" framing required by `openspec/config.yaml` proposal rules.
- `sidebarCollapsed` is persisted in `localStorage` per-browser; if a user collapses on desktop then resizes/uses the same browser on mobile, the stored `true` value has no visual effect once the CSS fix lands (collapse toggle button is already `hidden lg:flex`) — should be verified as inert, not reset, to avoid unnecessary added complexity.
- Grep-based defect inventory is not exhaustive; a full manual pass across all ~80 templates was not performed (out of scope/budget for exploration phase).

### Open Questions for Proposal Phase
1. Testing strategy under strict TDD given no e2e tool — accept pytest+Django-test-client HTML-assertion regression tests, or document a manual-QA exception?
2. Is `gestionar_evaluaciones.html`'s missing `overflow-x-auto` in scope for this change, or a separate quick-fix ticket?
3. Is the "drawer doesn't auto-close on mobile nav tap" UX defect in scope now or deferred to the hardening follow-up?
4. Is mobile-drawer a11y hardening (focus trap, `aria-modal`, `Escape`) in scope now or a follow-up HU?
5. Confirm `sidebarCollapsed` needs no explicit reset logic below `lg` (should be visually inert once offset fix lands).
6. Any target device/browser QA matrix (iOS Safari address-bar viewport-height quirks affect `h-screen` in base_auth.html, watch-item only)?
7. Delivery strategy: two staged PRs (recommended) vs. one larger PR under `size:exception`?

### Ready for Proposal
Yes. Root cause is confirmed with exact file:line references, defect inventory is categorized by severity, and a staged recommendation is ready. The testing-strategy gap under strict TDD (open question #1) should be resolved explicitly at proposal time since it affects the RED→GREEN→REFACTOR plan required by project rules.
