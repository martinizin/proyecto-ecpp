# ui-layout Specification (SP0-04)

## Purpose

Base HTML template with Tailwind CSS and Alpine.js via CDN, corporate palette, role-based navigation, login placeholder, and Django Admin branding.

## Requirements

### Requirement: Base Template

The project MUST include `templates/base.html` as the root template. It MUST include: HTML5 doctype, `<meta charset="utf-8">`, viewport meta tag, Tailwind CSS 3.4.17 CDN `<script>` tag, Alpine.js 3.15.9 CDN `<script>` tag (with `defer`), Google Fonts CDN link for Inter font, `{% block title %}`, `{% block content %}`, `{% block extra_js %}`.

The `<body>` MUST use `font-family: 'Inter', sans-serif` as default.

#### Scenario: Base template renders

- GIVEN the Django project is running
- WHEN a view extends `base.html` and is rendered
- THEN the HTML includes Tailwind CDN, Alpine.js CDN, and Inter font link

### Requirement: Tailwind Corporate Palette

The `base.html` MUST configure Tailwind's CDN inline config to extend the theme with corporate colors: `primary: '#2D5016'`, `secondary: '#4A7C2F'`, `accent: '#D4B942'`. These MUST be usable as Tailwind classes (e.g., `bg-primary`, `text-accent`).

#### Scenario: Corporate colors available

- GIVEN a template extending `base.html`
- WHEN using class `bg-primary`
- THEN the element background color is `#2D5016`

### Requirement: Navbar Partial

The project MUST include `templates/partials/navbar.html` as an includable navigation component. It MUST use Alpine.js `x-data` for responsive menu toggle (mobile hamburger). The navbar MUST display the project name/logo area and role-based navigation links.

Navigation links MUST vary by role: Estudiante (Mis Calificaciones, Mi Asistencia, Solicitudes), Docente (Mis Paralelos, Registrar Calificaciones, Registrar Asistencia), Inspector (Gestion Academica, Reportes, Solicitudes Pendientes).

Since auth is not yet implemented, the navbar SHOULD accept a mocked role context variable to demonstrate the role-based structure.

#### Scenario: Mobile menu toggle

- GIVEN the page is viewed on a mobile viewport (<768px)
- WHEN the user clicks the hamburger menu button
- THEN the navigation menu toggles visibility via Alpine.js

#### Scenario: Role-based links render

- GIVEN the template context includes `user_role='docente'`
- WHEN the navbar renders
- THEN navigation links for "Mis Paralelos", "Registrar Calificaciones", "Registrar Asistencia" are visible

### Requirement: Login Page Placeholder

The project MUST include `templates/registration/login.html` extending `base.html`. It MUST contain a centered login form placeholder with username and password fields styled with Tailwind, using the corporate color palette for the submit button. It MAY be non-functional (no auth backend wired yet).

#### Scenario: Login page accessible

- GIVEN a URL route is configured for the login view
- WHEN navigating to the login URL
- THEN a styled login form renders with corporate palette colors

### Requirement: Django Admin Branding

The project MUST customize Django Admin with: `admin.site.site_header` set to "ECPPP - Plataforma Academica", `admin.site.site_title` set to "ECPPP Admin", `admin.site.index_title` set to "Panel de Administracion".

#### Scenario: Admin shows branding

- GIVEN the project is running
- WHEN navigating to `/admin/`
- THEN the page title shows "ECPPP Admin" and the header shows "ECPPP - Plataforma Academica"

### Requirement: Template Directory Configuration

`config/settings/base.py` MUST configure `TEMPLATES[0]['DIRS']` to include `BASE_DIR / 'templates'`. The `templates/` directory MUST exist at the project root.

#### Scenario: Template resolution

- GIVEN `templates/base.html` exists at the project root
- WHEN a view renders a template extending `base.html`
- THEN Django resolves the template without `TemplateDoesNotExist` errors

## Files Affected

| File | Action |
|------|--------|
| `templates/base.html` | Create |
| `templates/partials/navbar.html` | Create |
| `templates/registration/login.html` | Create |
| `config/settings/base.py` | Modify (TEMPLATES DIRS) |
| `config/urls.py` | Modify (admin branding) |

## Dependencies

- **django-project-config** (SP0-02): requires Django project and settings.
- **ddd-architecture** (SP0-03): requires app structure for URL includes.
