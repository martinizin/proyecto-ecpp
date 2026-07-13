# Design: Responsive/Mobile Layout Refactor

## Technical Approach

Pure presentation-layer refactor (Django templates + Alpine `:class` + Tailwind CDN
classes). No Python, models, DB, DDD-layer, or business-logic changes. The Alpine root
state (`sidebarOpen`, `sidebarCollapsed`, `toggleCollapse()`) at `base.html:357-362`
stays untouched; we only change how that state maps to CSS so the sidebar offset is
gated to `lg+` and the mobile drawer becomes accessible. Structural pytest guards lock
the mechanism; pixel correctness stays a documented manual-QA matrix (see proposal).

## Architecture Decisions

| Decision | Options / Tradeoff | Choice |
|---|---|---|
| Offset technique (P1) | (a) `lg:`-gated Alpine `:class`, no base `ml-*`; (b) inline `:style` + `window.matchMedia`. (b) reintroduces JS breakpoint logic, is untestable structurally, and duplicates Tailwind's `lg`. | **(a)** Remove inline `:style`; bind only `lg:`-prefixed utilities. Below `lg` there is literally no offset class, so content starts at viewport-left. |
| JIT class pickup | Play CDN regex-scans all text incl. attribute values, so `lg:ml-16/64` inside `:class="..."` is detected. Risk if a scan misses dynamic strings. | Rely on literal strings in markup **plus** a `safelist` in the inline `tailwind.config` (`base.html:18`) as belt-and-suspenders. |
| Focus trap (P2) | (a) hand-rolled minimal trap in the existing root `x-data`; (b) `x-trap` from Alpine Focus plugin — **not loaded** on the CDN build. | **(a)** Hand-roll a tiny trap. Adding a plugin = new CDN dependency + bundle, out of proportion for one drawer. |
| Drawer auto-close vs htmx boost | Closing on link tap must not cancel the boosted swap. `@click` on the `<nav>` runs on bubble AFTER htmx issues the request; setting `sidebarOpen=false` only mutates Alpine state, never `preventDefault`. | Add `@click="sidebarOpen = false"` on the `<nav>` container (one handler, event delegation), coexists with `hx-boost`. |
| Table overflow (P3) | Per-table CSS vs standard wrapper. | Standard `<div class="overflow-x-auto">` wrapper — matches Tailwind idiom, greppable. |

## File Changes

| File | Action | Change |
|---|---|---|
| `templates/base.html` | Modify | `<main>` (392-393): delete `:style` margin-left; add `:class="sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'"`. Add `safelist` to `tailwind.config`. |
| `templates/partials/topbar.html` | Modify | `<header>` (4-10): delete `:style` left; keep base `left-0`; add `:class="sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'"`. |
| `templates/partials/sidebar.html` | Modify | `<nav>` (61): add `@click="sidebarOpen = false"`. `<aside>` (21-32): add `role="dialog"` `aria-modal="true"` `:aria-hidden`/`x-trap` equivalents via root handlers; `@keydown.escape.window="sidebarOpen = false"`; focus restore to hamburger. |
| `templates/calificaciones/gestionar_evaluaciones.html` | Modify | Wrap `<table>` (56) in `<div class="overflow-x-auto">`. |
| `templates/academico/dashboard_rendimiento.html` | Modify | Line 92 `grid-cols-2` → `grid-cols-1 sm:grid-cols-2`. Line 315 already `grid-cols-2 lg:grid-cols-4` → `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`. |
| `tests/presentation/test_responsive_layout.py` | Create | Structural regression guards (below). |
| `docs/responsive-convention.md` | Create | P4 convention doc. |

## Exact Offset Markup

```html
<!-- base.html <main> -->
<main class="pt-16 min-h-screen flex flex-col transition-all duration-300"
      :class="sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'">   <!-- NO base ml-* -->

<!-- topbar.html <header> -->
<header class="fixed top-0 right-0 left-0 h-16 ... z-30 transition-all duration-300"
        :class="sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'" role="banner" hx-boost="true">
```

```js
// base.html tailwind.config — JIT safelist fallback
safelist: ['lg:ml-16', 'lg:ml-64', 'lg:left-16', 'lg:left-64'],
```

## Mobile Drawer A11y (hand-rolled trap)

Extend the root `x-data` with a helper (no new dependency):

```js
trapFocus(e) {                       // bound via @keydown.tab on <aside>
  if (window.innerWidth >= 1024) return;          // desktop: no trap
  const f = e.currentTarget.querySelectorAll(
    'a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])');
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
  else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
}
```

`<aside>` gains `role="dialog" aria-modal="true"` (mobile semantics; harmless at `lg`
where it is a persistent nav), `@keydown.escape.window="sidebarOpen=false"`,
`@keydown.tab="trapFocus($event)"`, and `x-effect`/`@click` on the hamburger to
`$refs`-restore focus to the hamburger button on close. Hamburger gets `x-ref="hamburger"`;
close paths call `$refs.hamburger.focus()`.

## Testing Strategy (strict TDD, RED→GREEN)

Location: `tests/presentation/test_responsive_layout.py` (`pytest-django`, `client`,
`force_login` per-role factory). Render via Django test client and assert on decoded HTML.
Black line-length=99.

| Requirement | Assertion | Method |
|---|---|---|
| No unconditional offset (main) | `assert "margin-left" not in html` on the `<main>` region | pytest |
| `lg:`-gated offset present | `assert "lg:ml-64" in html and "lg:ml-16" in html` | pytest |
| Header gated | `assert "left'" not in header and "lg:left-64" in html` | pytest |
| Table wrapped | render `gestionar_evaluaciones`; assert `overflow-x-auto` occurs before `<table` | pytest |
| Drawer a11y | `assert 'aria-modal="true"' in html and 'role="dialog"' in html` | pytest |
| Grid fallback | `assert "grid-cols-1" in html` on `dashboard_rendimiento` | pytest |
| Pixel/viewport 320–1024px, iOS/Android, 5 roles | DoD checklist | **manual QA** |

Audit method for P3 (documented, run manually / in review): grep
`rg -n "<table" templates/` and cross-check each hit for a nearby `overflow-x-auto`
ancestor; log misses as follow-up.

## Migration / Rollout

Template/CSS-only, staged into chained PRs (≤400 lines each), revert-per-slice:

| PR | Scope | Rollback |
|---|---|---|
| P1 | `base.html` + `topbar.html` offset + safelist + offset tests | `git revert` restores inline `:style` |
| P2 | `sidebar.html` drawer auto-close + a11y + trap + tests | revert sidebar only |
| P3 | table wrapper + grid fallbacks + structural tests | revert two templates |
| P4 | `docs/responsive-convention.md` | docs-only, no runtime impact |

## Open Questions

- [ ] Confirm in manual QA that `role="dialog"` on the persistent `lg` sidebar causes no
  screen-reader regression; if it does, gate the ARIA attrs behind an Alpine `:role`/`:aria-modal` that only applies below `lg`.
