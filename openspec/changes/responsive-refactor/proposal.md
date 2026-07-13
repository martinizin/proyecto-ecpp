# Proposal: Responsive/Mobile Layout Refactor (responsive-refactor)

## Intent
The collapsible-sidebar feature regressed mobile. `<main>` (`base.html:392-393`) and `<header>` (`topbar.html:7`) apply an **unconditional inline `:style`** left offset (16rem/4rem) that ignores Tailwind breakpoints, so on phones content is pushed off-screen and the hamburger — the only way to open the menu — is nearly unreachable. This breaks the authenticated experience for EVERY role (estudiante, docente, inspector, secretaria, director). The client asked for a complete responsive sweep so mobile is fixed and consistent across all screens, without regressing. Jira: QA responsive.

## Scope

### In Scope
- **P1 Offset fix (critical):** replace inline `:style` offsets with `lg:`-gated Tailwind classes (0 margin below `lg`, correct at `lg+`) in `base.html` + `topbar.html`.
- **P2 Mobile drawer UX + a11y:** close drawer on nav-link tap; add `role="dialog"`/`aria-modal`, focus trap, `Escape`-to-close (`sidebar.html`).
- **P3 Table/grid responsive audit:** wrap `gestionar_evaluaciones.html:56` table in `overflow-x-auto`; give `dashboard_rendimiento.html` grids a mobile 1-col fallback; grep-audit remaining `templates/**`.
- **P4 Convention doc:** short responsive convention (offset pattern, `overflow-x-auto` for tables, mobile-first grids) to prevent recurrence.

### Out of Scope
- `base_auth.html` iOS `h-screen` keyboard watch-item (verified not the reported break).
- Custom Tailwind breakpoints / migrating off the CDN build.
- Resetting `localStorage` `sidebarCollapsed` (verified visually inert below `lg`).
- Any non-visual/business-logic change.

## Capabilities
### New Capabilities
- `responsive-layout`: server-rendered shell (main/header/sidebar/tables/grids) MUST be usable and content-complete from 320px up, with the sidebar offset gated to `lg+`.
### Modified Capabilities
- None.

## Approach
Pure template/Alpine/CSS refactor — no Python, no models, no DB. Swap unconditional inline offsets for breakpoint-gated `:class`; harden the Alpine drawer; normalize table/grid wrappers; document the convention. **Delivery: single SDD change, staged into chained PRs** (P1 urgent → P2 → P3+P4) to respect the 400-line review budget while still delivering the full sweep the client asked for.

### Testing strategy (strict_tdd, no e2e tool)
- **TDD-guarded (pytest + Django test client, RED→GREEN):** assert rendered `<main>`/`<header>` contain NO unconditional inline `margin-left`/`left` offset and DO contain `lg:`-gated classes; assert `gestionar_evaluaciones` table renders inside an `overflow-x-auto` wrapper; assert drawer markup exposes `aria-modal`/`role="dialog"`.
- **Manual QA (documented, cannot be automated):** pixel/viewport correctness at 320/375/414/768/1024px on iOS Safari + Android Chrome, across all 5 role dashboards + one list/table page each. Listed as an explicit DoD checklist item, not a code gate.

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `templates/base.html` | Modified | `lg:`-gate `<main>` offset |
| `templates/partials/topbar.html` | Modified | `lg:`-gate header offset |
| `templates/partials/sidebar.html` | Modified | Drawer auto-close + a11y |
| `templates/calificaciones/gestionar_evaluaciones.html` | Modified | `overflow-x-auto` wrapper |
| `templates/academico/dashboard_rendimiento.html` | Modified | Mobile 1-col grid fallback |
| `tests/` (template-render) | New | Structural regression guards |
| `docs/` responsive convention | New | Recurrence guard |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Visual correctness unverifiable in CI | High | Documented manual-QA matrix as DoD; structural tests guard the mechanism |
| Grep audit misses a template | Med | P3 audit + convention doc; follow-up ticket if found |
| Scope creep beyond confirmed defects | Med | Non-goals fixed; audit normalizes only, no redesign |
| Chained PRs left unfinished after P1 | Med | All slices tracked in one change; verify gates on full scope |

## Rollback Plan
Template/CSS-only and staged — revert per-PR. Each slice is an independent commit touching known files; `git revert` restores prior markup with zero data/migration impact.

## Dependencies
- None. No new libraries; CDN Tailwind/Alpine already present.

## Success Criteria (Definition of Done)
- [ ] From 320px up, authenticated pages show no phantom left offset; hamburger fully visible/tappable for all 5 roles.
- [ ] Rendered `<main>`/`<header>` have no unconditional inline offset; `lg:` classes present (pytest green).
- [ ] Mobile drawer closes on nav tap and on `Escape`; exposes `aria-modal`/`role="dialog"`; focus trapped while open.
- [ ] `gestionar_evaluaciones` table scrolls horizontally within `overflow-x-auto` (pytest green); no bare `grid-cols-2` breakage.
- [ ] Responsive convention documented.
- [ ] Manual-QA matrix (320/375/414/768/1024px, iOS Safari + Android Chrome) signed off.
- [ ] Coverage ≥ 70%; each PR ≤ 400 changed lines.
