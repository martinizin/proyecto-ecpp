# Responsive / Mobile Layout Convention

This document defines the three patterns new templates MUST follow so the
authenticated shell and any data-heavy view stay usable from 320px up,
without regressing `lg`+ (>=1024px) desktop behavior.

It codifies the outcome of the `responsive-refactor` change
(`openspec/changes/responsive-refactor/`). See that change's `spec.md` for
the full requirement list and `tests/presentation/test_responsive_layout.py`
for the structural pytest guards that enforce patterns 1 and 2 below.

## 1. Offset pattern — `lg:`-gated Alpine `:class`, never a base `ml-*`/`left`

The authenticated shell's sidebar-aware offset (`<main>`'s `margin-left`,
the topbar `<header>`'s `left`) must **never** carry an unconditional
inline style or an unprefixed base Tailwind class. Below `lg`, there is
**no offset at all** — content starts at the viewport edge and the sidebar
becomes an off-canvas drawer instead of a persistent column. At `lg`+, the
offset follows `sidebarCollapsed` via `lg:`-prefixed utility classes bound
through Alpine's `:class`.

```html
<!-- base.html <main> -->
<main class="pt-16 min-h-screen flex flex-col transition-all duration-300"
      :class="sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'">   <!-- NO base ml-* -->

<!-- topbar.html <header> -->
<header class="fixed top-0 right-0 left-0 h-16 ... z-30 transition-all duration-300"
        :class="sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'" role="banner">
```

Because these classes only ever appear inside an Alpine `:class` ternary
(never as a bare literal token elsewhere on the page), also add them to the
Tailwind Play CDN's `safelist` in `base.html`'s inline `tailwind.config` as
a belt-and-suspenders guard against the JIT text-scanner missing them:

```js
tailwind.config = {
  // ...
  safelist: ['lg:ml-16', 'lg:ml-64', 'lg:left-16', 'lg:left-64'],
}
```

**Rule of thumb:** if you introduce a new `lg:`-gated dynamic class pair,
add both variants to the `safelist`.

## 2. Table-wrap pattern — `overflow-x-auto` around every `<table>`

Every data `<table>` under `templates/**` must render inside a horizontal
scroll wrapper. Without it, wide tables overflow the viewport on mobile and
either break the layout or become unreadable.

```html
<div class="overflow-x-auto">
  <table class="w-full text-sm text-left">
    <!-- ... -->
  </table>
</div>
```

This is required even when the table already sits inside another scrollable
or bordered container — the wrapper is what gives the table itself a
horizontal scroll boundary independent of its parent's width.

## 3. Mobile-first grid/breakpoint rules — no bare `grid-cols-N` (N>1)

Never use an unprefixed `grid-cols-N` where `N > 1`. Multi-column grids must
start at a single column (`grid-cols-1`) and expand at the appropriate
breakpoint (`sm:`, `md:`, `lg:`), so content stacks cleanly below that
breakpoint instead of squeezing into columns too narrow to read.

```html
<!-- Wrong — always 2 columns, even on a 320px phone -->
<div class="grid grid-cols-2 gap-3">...</div>

<!-- Right — 1 column by default, 2 columns from `sm` up -->
<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">...</div>

<!-- Right — stacks further breakpoints as columns increase -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">...</div>
```

## Enforcement

Patterns 1 (offset) and 2 (table-wrap) and 3 (grid) are guarded by
structural pytest assertions in
`tests/presentation/test_responsive_layout.py`, which render real
authenticated pages via the Django test client and assert on the decoded
HTML. Pixel-level and JS-runtime correctness (drawer open/close, focus
trap, viewport behavior below `lg`) are verified manually against the
320/375/414/768/1024px x iOS Safari/Android Chrome matrix documented in
`openspec/changes/responsive-refactor/spec.md`, since no e2e tool is
available in this project yet.

When adding a new authenticated template with a table or a multi-column
grid, follow patterns 2 and 3 above. When touching the shell itself
(`base.html`, `partials/topbar.html`, `partials/sidebar.html`), follow
pattern 1 and keep the `safelist` in sync.
