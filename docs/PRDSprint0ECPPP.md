# PRD — Sprint 0: Plataforma Web Academica ECPPP

| Campo | Valor |
|-------|-------|
| **Titulo** | Product Requirements Document — Sprint 0 |
| **Proyecto** | Plataforma Web Academica ECPPP |
| **Version** | 0.1.0 |
| **Fecha** | Abril 2026 |
| **Sprint** | S0 (Incremento 0) |
| **Rango de fechas** | 23/03/2026 – 27/03/2026 |
| **Equipo** | 2 desarrolladores — Martin Jimenez, Junior Espin |
| **Metodologia** | Scrum |
| **Capacidad del sprint** | 10 puntos (30 h semanales, lunes a viernes, 2 integrantes) |
| **Estado** | Draft |

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Encabezado e Incremento 0

---

## 1. Resumen ejecutivo del Sprint 0

### 1.1 Objetivo del Sprint

Preparar el entorno de desarrollo, la arquitectura base del proyecto Django/DDD y el backlog priorizado, estableciendo los cimientos tecnicos y organizativos del equipo para que los sprints de desarrollo puedan iniciarse sin bloqueos. Este sprint abarca la configuracion del repositorio, la puesta en marcha de la base de datos PostgreSQL, el diseno de la arquitectura DDD inicial con los agregados del dominio academico, la configuracion del layout UI base y el refinamiento del backlog con criterios de aceptacion verificables.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Objetivo Sprint 0; HistoriasUsuario_Sprints_ECPPP.docx — Seccion "Sprint 0"

### 1.2 Definition of Done del Sprint 0

- [ ] Repositorio GitHub creado con estructura de ramas definida y protecciones configuradas.
- [ ] Entorno de desarrollo local funcional (venv) con instrucciones documentadas.
- [ ] Pipeline de CI basico ejecutandose sin errores (linting, tests base).
- [ ] Proyecto Django creado con configuracion de PostgreSQL y migraciones iniciales aplicadas.
- [ ] Documento de arquitectura DDD con definicion de agregados: Usuario, Periodo, Asignatura, Paralelo.
- [ ] Layout UI base integrado con Django Admin y navegacion diferenciada por rol.
- [ ] Prototipo Figma revisado con flujos de navegacion validados por rol.
- [ ] Backlog refinado con criterios de aceptacion documentados para Sprint 1.
- [ ] Todos los items SP0-xx completados con su evidencia de completitud verificada.

---

## 2. Alcance del Sprint 0

### 2.1 Incluye

| Aspecto | Detalle | Fuente |
|---------|---------|--------|
| Repositorio y CI | Configuracion de repositorio GitHub, entorno dev (venv) y CI basico (GitHub Actions) | Planificacion — Incremento 0 |
| Proyecto Django | Setup proyecto Django + PostgreSQL + migraciones iniciales | Planificacion — Tabla Sprint 0, SP0-02 |
| Arquitectura | Diseno de arquitectura DDD inicial (agregados: Usuario, Periodo, Asignatura, Paralelo) | Planificacion — Incremento 0; Requerimientos — RR028 |
| Layout UI | Configuracion de layout UI base + Django Admin + navegacion por rol | Planificacion — Tabla Sprint 0, SP0-04 |
| Prototipo Figma | Revision del prototipo Figma y validacion de flujos de navegacion por rol | Planificacion — Incremento 0 |
| Backlog | Refinamiento del backlog y criterios de aceptacion | Planificacion — Tabla Sprint 0, SP0-05 |
| Metodologia y roles | Definicion de metodologia Scrum, roles del equipo, stack tecnologico | Planificacion — Encabezado |

### 2.2 Excluye

| Aspecto | Razon |
|---------|-------|
| Implementacion de HUs funcionales | Las HU01–HU20 inician en Sprint 1 en adelante (Fuente: HistoriasUsuario — Tabla por sprint) |
| Despliegue en produccion/preproduccion | Asignado a Sprint 5 — DEP-01, DEP-02 (Fuente: Planificacion — Sprint 5) |
| Modulos de autenticacion, calificaciones, asistencia | Sprints 1–4 (Fuente: Planificacion — Incrementos 1–4) |
| Pruebas de aceptacion con stakeholders | Sprint 5 — QA-01, QA-02 (Fuente: Planificacion — Sprint 5) |
| Copilot ECPP (asistente IA) | Sprint 4 — HU17 (Fuente: Planificacion — Sprint 4) |

---

## 3. Backlog del Sprint 0

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Tabla Sprint 0; HistoriasUsuario_Sprints_ECPPP.docx — Seccion "Sprint 0"

| ID | Nombre exacto | Descripcion | Puntos | Dependencias | Responsable sugerido | Output verificable |
|----|---------------|-------------|--------|--------------|----------------------|-------------------|
| SP0-01 | Configuracion de repositorio GitHub, entorno dev/staging y CI basico | Crear repositorio con estructura de ramas, configurar entorno de desarrollo local (venv + pip), y pipeline CI basico con GitHub Actions (flake8, black --check, pytest, coverage) | 2 | Ninguna | Dev A (Martin) | Repositorio GitHub activo con README, `.gitignore`, ramas `main`/`develop`, pipeline CI ejecutandose en verde |
| SP0-02 | Setup proyecto Django + PostgreSQL + migraciones iniciales | Crear proyecto Django con configuracion de base de datos PostgreSQL, estructura de apps inicial y migraciones base aplicadas | 2 | SP0-01 | Dev B (Junior) | Proyecto Django funcional, `manage.py runserver` sin errores, conexion a PostgreSQL verificada, migraciones aplicadas |
| SP0-03 | Diseno de arquitectura DDD (agregados, entidades, repositorios) | Disenar y documentar la arquitectura DDD del dominio academico: definir agregados (Usuario, Periodo, Asignatura, Paralelo), entidades, value objects y repositorios | 3 | SP0-02 | Dev A (Martin) + Dev B (Junior) | Documento de arquitectura DDD (`docs/arquitectura-ddd.md` o similar) con diagramas de agregados, entidades y repositorios |
| SP0-04 | Configuracion de layout UI base + Django Admin + navegacion por rol | Configurar el layout base de la interfaz (templates, CSS corporativo, sistema de diseno) con Django Admin habilitado y navegacion diferenciada para Estudiante, Docente e Inspector | 2 | SP0-02, SP0-03 | Dev B (Junior) | Templates base renderizando correctamente, Django Admin accesible, navegacion por rol visible en la UI |
| SP0-05 | Refinamiento del backlog y criterios de aceptacion | Revisar y refinar el backlog del Sprint 1, verificar criterios de aceptacion de HU01–HU06, validar estimaciones y prioridades | 1 | Ninguna | Dev A (Martin) + Dev B (Junior) | Backlog del Sprint 1 documentado con criterios de aceptacion verificados y estimaciones confirmadas |
| **Total** | | | **10** | | | |

---

## 4. Detalle por item del Sprint 0

### 4.1 SP0-01 — Configuracion de repositorio GitHub, entorno dev/staging y CI basico

**Proposito:**
Establecer la infraestructura base de control de versiones, entornos de desarrollo y pipeline de integracion continua para que el equipo pueda trabajar de forma colaborativa desde el Sprint 1 sin bloqueos tecnicos.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Incremento 0, Tabla Sprint 0

**Pasos tecnicos sugeridos:**

1. Crear repositorio en GitHub con nombre `proyecto-ecpp` (o segun convencion del equipo).
2. Configurar `.gitignore` para Python/Django (incluir `__pycache__`, `.env`, `db.sqlite3`, `*.pyc`, `media/`, `staticfiles/`).
3. Crear ramas iniciales: `main` (produccion), `develop` (integracion).
4. Configurar reglas de proteccion en `main`: requerir PR con al menos 1 aprobacion.
5. Crear entorno de desarrollo local con `venv` + `requirements.txt` (pip freeze).
6. Configurar pipeline CI basico (GitHub Actions) con: linting (`flake8`), verificacion de formato (`black --check`), ejecucion de tests (`pytest`), cobertura (`coverage.py`), verificacion de migraciones.
7. Documentar instrucciones de setup en `README.md`.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Repositorio GitHub creado y accesible para ambos desarrolladores.
- [ ] `.gitignore` configurado correctamente para Python/Django.
- [ ] Ramas `main` y `develop` creadas con protecciones en `main`.
- [ ] Entorno de desarrollo local reproducible (documentado en README).
- [ ] Pipeline CI ejecutandose en cada push/PR a `develop` sin errores.
- [ ] Al menos un commit de prueba pasa el pipeline exitosamente.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Permisos de GitHub mal configurados | Verificar acceso de ambos devs antes de cerrar el item |
| Pipeline CI falla por dependencias | Fijar versiones en `requirements.txt` |

**Evidencia de completitud:**
- URL del repositorio GitHub con ramas visibles.
- Captura o enlace al pipeline CI ejecutandose en verde.
- Archivo `README.md` con instrucciones de setup.

---

### 4.2 SP0-02 — Setup proyecto Django + PostgreSQL + migraciones iniciales

**Proposito:**
Crear el proyecto Django base con la configuracion de base de datos PostgreSQL funcional y las migraciones iniciales aplicadas, proporcionando el esqueleto sobre el cual se construiran todos los modulos funcionales.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Incremento 0, Tabla Sprint 0; Requerimientos_ECPPP.docx — RR028 (arquitectura monolitica Django), RR029 (despliegue, variables de entorno)

**Pasos tecnicos sugeridos:**

1. Crear proyecto Django: `django-admin startproject config .` (o nombre acordado).
2. Configurar `settings.py` para PostgreSQL: `DATABASES` con variables de entorno (`os.environ` o `django-environ`).
3. Crear archivo `.env.example` con variables requeridas (sin valores sensibles).
4. Instalar dependencias base: `Django`, `psycopg2-binary`, `djangorestframework`, `python-dotenv` o `django-environ`.
5. Ejecutar `python manage.py migrate` para aplicar migraciones iniciales de Django.
6. Verificar conexion a PostgreSQL con `python manage.py dbshell` o script de prueba.
7. Crear superusuario inicial para Django Admin: `python manage.py createsuperuser`.
8. Crear apps iniciales segun dominio DDD (puede coordinarse con SP0-03).

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Proyecto Django creado con estructura de directorios limpia.
- [ ] Conexion a PostgreSQL verificada (migraciones aplicadas sin errores).
- [ ] `manage.py runserver` inicia sin errores en `http://localhost:8000`.
- [ ] Django Admin accesible en `/admin/` con superusuario funcional.
- [ ] Archivo `.env.example` creado con las variables necesarias documentadas.
- [ ] `requirements.txt` o `pyproject.toml` con dependencias fijadas.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| PostgreSQL no instalado en maquina local | Documentar instalacion o usar Docker para PostgreSQL |
| Conflicto de versiones Django/PostgreSQL | Fijar versiones compatibles en requirements |

**Evidencia de completitud:**
- Proyecto Django arrancando en local (captura de `runserver`).
- Django Admin funcional (captura de `/admin/`).
- Migraciones aplicadas (output de `python manage.py showmigrations`).

---

### 4.3 SP0-03 — Diseno de arquitectura DDD (agregados, entidades, repositorios)

**Proposito:**
Definir y documentar la arquitectura Domain-Driven Design del dominio academico, estableciendo los agregados, entidades, value objects y repositorios que guiaran la implementacion de todos los modulos funcionales en sprints posteriores.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Incremento 0 (agregados: Usuario, Periodo, Asignatura, Paralelo); Requerimientos_ECPPP.docx — RR028 (arquitectura monolitica DDD, agregados, entidades, repositorios, cobertura 70%)

**Pasos tecnicos sugeridos:**

1. Identificar los bounded contexts del dominio academico a partir de los requerimientos (RR001–RR030).
2. Definir los agregados raiz confirmados por la planificacion: Usuario, Periodo, Asignatura, Paralelo.
3. Identificar agregados adicionales derivados de los requerimientos: Evaluacion, Asistencia, Solicitud (Fuente: RR028).
4. Para cada agregado, documentar: entidades, value objects, invariantes de negocio, repositorio.
5. Diagramar las relaciones entre agregados (puede usarse PlantUML, Mermaid o draw.io).
6. Definir la estructura de capas DDD en Django: presentacion, aplicacion, dominio, infraestructura (Fuente: RR028).
7. Crear la estructura de directorios en el proyecto Django que refleje las capas DDD.
8. Revisar el prototipo Figma para validar que los agregados cubren todos los flujos de navegacion por rol.

> **Nota sobre "Curso":** El termino "Curso" aparece en documentos fuente como sinonimo informal de "Paralelo" o "asignatura matriculada". **Decision del equipo:** en codigo y documentacion tecnica se usa exclusivamente "Paralelo". "Curso" queda reservado para el lenguaje de la UI orientado al usuario final.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Documento de arquitectura DDD creado (ej: `docs/arquitectura-ddd.md`).
- [ ] Agregados raiz definidos: Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Asistencia, Solicitud.
- [ ] Para cada agregado: entidades, value objects e invariantes documentados.
- [ ] Diagrama de relaciones entre agregados incluido.
- [ ] Estructura de capas DDD mapeada a la estructura de directorios de Django.
- [ ] Prototipo Figma revisado — flujos de navegacion por rol validados.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Sobre-ingenieria en la definicion de agregados | Comenzar con los agregados confirmados (Usuario, Periodo, Asignatura, Paralelo), iterar en sprints posteriores |
| Falta de experiencia del equipo en DDD | Consultar referencias (Evans, Vernon) y mantener diseno simple |
| Prototipo Figma no disponible o desactualizado | Solicitar acceso al Figma actualizado al inicio del sprint |

**Evidencia de completitud:**
- Documento `docs/arquitectura-ddd.md` con agregados, entidades y diagramas.
- Estructura de directorios DDD visible en el repositorio.
- Acta de revision del prototipo Figma (comentarios o checklist firmado).

---

### 4.4 SP0-04 — Configuracion de layout UI base + Django Admin + navegacion por rol

**Proposito:**
Configurar la capa de presentacion base del proyecto: templates HTML, CSS corporativo segun el sistema de diseno aprobado, Django Admin funcional y navegacion diferenciada por rol (Estudiante, Docente, Inspector), para que los sprints de desarrollo tengan una base visual consistente.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Incremento 0, Tabla Sprint 0; Requerimientos_ECPPP.docx — RR027 (sistema de diseno: paleta corporativa, tipografia Inter, componentes reutilizables)

**Pasos tecnicos sugeridos:**

1. Crear template base (`base.html`) con estructura HTML semantica, bloque de contenido y navegacion.
2. Instalar y configurar Tailwind CSS 3.x: crear `tailwind.config.js`, definir los colores corporativos como tema, configurar proceso de build (CLI o PostCSS).
3. Integrar la paleta cromatica corporativa como variables del tema Tailwind: verde primario `#2D5016`, secundario `#4A7C2F`, amarillo `#D4B942`, escala de grises (Fuente: RR027).
4. Configurar tipografia Inter como fuente principal en Tailwind (Fuente: RR027).
5. Instalar Alpine.js para interactividad minima (dropdowns, toggles, modales) — sin SPA.
6. Implementar navegacion responsive diferenciada por rol: menus distintos para Estudiante, Docente e Inspector.
7. Personalizar Django Admin con branding basico del proyecto (logo, colores).
8. Crear componentes reutilizables base con clases Tailwind: botones, tablas, formularios, tarjetas (Fuente: RR027).
9. Verificar que la interfaz es responsive (compatible con moviles — Fuente: RR026).
10. Revisar contra el [prototipo Figma](https://www.figma.com/make/wHHZTwiWVdUUbOlVb33jO2/Prototipo-Web-Acad%C3%A9mico-ECPP--Copia-?t=jR8TIKaIwUqHD4c6-1) para consistencia visual.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Template base (`base.html`) creado con bloques de contenido.
- [ ] Paleta corporativa aplicada: `#2D5016`, `#4A7C2F`, `#D4B942` (Fuente: RR027).
- [ ] Tipografia Inter integrada (Fuente: RR027).
- [ ] Navegacion por rol visible (al menos estructura de menus diferenciados).
- [ ] Django Admin accesible y personalizado con branding basico.
- [ ] Interfaz responsive verificada en al menos 2 resoluciones (desktop + movil).

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Falta de assets del diseno (iconos, logo) | Solicitar al inicio del sprint; usar placeholders temporales |
| Complejidad de la navegacion por rol sin autenticacion aun | Implementar estructura de menus con datos mockeados; la logica de permisos se agrega en Sprint 1 |

**Evidencia de completitud:**
- Templates renderizando en el navegador con la paleta corporativa.
- Django Admin personalizado (captura de pantalla).
- Verificacion responsive (capturas en desktop y movil).

---

### 4.5 SP0-05 — Refinamiento del backlog y criterios de aceptacion

**Proposito:**
Revisar y refinar el backlog del Sprint 1 (HU01–HU06), verificar que los criterios de aceptacion Gherkin estan completos y son verificables, validar las estimaciones en puntos Fibonacci y confirmar prioridades con el equipo.

> **Fuente:** Planificacion_Sprints_Capstone_ECPP.docx — Tabla Sprint 0, Sprint 1; HistoriasUsuario_Sprints_ECPPP.docx — HU01–HU06 con escenarios Gherkin

**Pasos tecnicos sugeridos:**

1. Revisar las 6 HUs del Sprint 1: HU01 (Registro, 3 pts), HU02 (Login, 3 pts), HU03 (Recuperacion contrasena, 2 pts), HU04 (Perfil, 2 pts), HU05 (Periodos academicos, 3 pts), HU06 (Licencias/asignaturas/paralelos, 3 pts).
2. Verificar que cada HU tiene escenarios Gherkin completos (Dado/Cuando/Entonces).
3. Validar que las estimaciones suman 16 puntos (capacidad Sprint 1 con feriado Semana Santa).
4. Identificar dependencias entre HUs del Sprint 1 (ej: HU05 y HU06 dependen de HU01/HU02 para autenticacion).
5. Documentar cualquier pregunta abierta o criterio ambiguo para resolver con stakeholders.
6. Actualizar el backlog en Jira con las HUs refinadas, estimaciones y criterios de aceptacion.

**Criterios de aceptacion tecnicos (DoD):**

- [ ] Las 6 HUs del Sprint 1 revisadas con criterios de aceptacion completos.
- [ ] Estimaciones validadas: total 16 puntos (consistente con capacidad reducida por Semana Santa).
- [ ] Dependencias entre HUs identificadas y documentadas.
- [ ] Preguntas abiertas listadas (si las hay) con responsable de resolucion.
- [ ] Backlog actualizado en Jira.

**Riesgos y mitigacion:**

| Riesgo | Mitigacion |
|--------|-----------|
| Criterios de aceptacion ambiguos en alguna HU | Marcar como TODO y resolver antes de iniciar Sprint 1 |
| Desacuerdo en estimaciones | Usar planning poker entre los 2 devs; consenso o promedio |

**Evidencia de completitud:**
- Backlog del Sprint 1 documentado con las 6 HUs, puntos y criterios.
- Lista de preguntas abiertas (si las hay) con estado de resolucion.

---

## 5. Requerimientos trazables al Sprint 0

> **Fuente:** Requerimientos_ECPPP.docx — Tabla de requerimientos; Planificacion_Sprints_Capstone_ECPP.docx — Tabla Sprint 0

**Nota:** El Sprint 0 no implementa HUs funcionales (HU01–HU20 inician en Sprint 1). Sin embargo, varios requerimientos no funcionales impactan directamente las tareas de setup e infraestructura del Sprint 0.

### 5.1 Requerimientos funcionales trazables

No aplica directamente. Las HU01–HU20 se implementan a partir del Sprint 1. Sin embargo, SP0-05 (refinamiento del backlog) prepara las HUs del Sprint 1 para su implementacion.

| HU | Nombre | Sprint de implementacion | Relacion con SP0 |
|----|--------|--------------------------|-------------------|
| HU01 | Registro de usuario | Sprint 1 | SP0-05 refina sus criterios de aceptacion |
| HU02 | Inicio de sesion | Sprint 1 | SP0-05 refina sus criterios de aceptacion |
| HU03 | Recuperacion de contrasena | Sprint 1 | SP0-05 refina sus criterios de aceptacion |
| HU04 | Gestion de perfil de usuario | Sprint 1 | SP0-05 refina sus criterios de aceptacion |
| HU05 | Gestion de periodos academicos | Sprint 1 | SP0-05 refina sus criterios de aceptacion |
| HU06 | Gestion de licencias, asignaturas y paralelos | Sprint 1 | SP0-05 refina sus criterios de aceptacion |

### 5.2 Requerimientos no funcionales trazables

| RR | Enunciado resumido | SP0-xx relacionado | Evidencia |
|----|--------------------|--------------------|-----------|
| RR027 | Sistema de diseno: paleta `#2D5016`, `#4A7C2F`, `#D4B942`, tipografia Inter, componentes reutilizables | SP0-04 | Templates con paleta y tipografia aplicadas |
| RR028 | Arquitectura monolitica DDD: capas presentacion/aplicacion/dominio/infraestructura; agregados; API REST con DRF; cobertura minima 70% en dominio | SP0-03 | Documento de arquitectura DDD con agregados y estructura de capas |
| RR029 | Despliegue en VPS, variables de entorno, Nginx, HTTPS | SP0-01 (parcial: `.env.example`, CI) | `.env.example`, pipeline CI |
| RR021 | Control de acceso por roles, cifrado, HTTPS | SP0-04 (navegacion por rol — estructura) | Menus diferenciados por rol en templates |
| RR026 | Interfaz responsive, flujos claros por rol | SP0-04 | Verificacion responsive desktop + movil |

---

## 6. Decisiones de arquitectura y stack

### 6.A Decisiones confirmadas por documentos

Las siguientes decisiones estan explicitamente documentadas en las fuentes del proyecto:

| Decision | Detalle | Fuente |
|----------|---------|--------|
| Lenguaje backend | Python | Planificacion — Encabezado; Requerimientos — Encabezado |
| Framework web | Django | Planificacion — Encabezado; Requerimientos — RR028, RR029 |
| Base de datos | PostgreSQL | Planificacion — Encabezado; Requerimientos — RR024, RR025 |
| Arquitectura | Monolitica con Domain-Driven Design (DDD) | Requerimientos — RR028 |
| Capas DDD | Presentacion, Aplicacion, Dominio, Infraestructura | Requerimientos — RR028 |
| Agregados del dominio | Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Asistencia, Solicitud. Nota: "Curso" queda reservado para la UI; en codigo y documentacion se usa "Paralelo" | Planificacion — Incremento 0; Requerimientos — RR028; Decision de equipo |
| API REST interna | Django REST Framework (DRF) | Requerimientos — RR028, RR030 |
| Metodologia | Scrum | Planificacion — Encabezado |
| Cifrado de contrasenas | bcrypt o Argon2 | Requerimientos — RR021 |
| Protocolo de transmision | HTTPS/TLS | Requerimientos — RR021, RR029 |
| Proxy inverso | Nginx con SSL (Let's Encrypt) | Requerimientos — RR029 |
| Correo electronico | SMTP/Email (OTP, recuperacion, notificaciones) | Requerimientos — RR030 |
| Sistema de diseno | Paleta: `#2D5016`, `#4A7C2F`, `#D4B942`; Tipografia: Inter; Componentes reutilizables | Requerimientos — RR027 |
| Cobertura de tests | Minimo 70% en capa de dominio | Requerimientos — RR028 |
| Infraestructura produccion | VPS Linux (unico artefacto Django + PostgreSQL) | Requerimientos — RR029 |
| Navegadores compatibles | Chrome 110+, Firefox 110+, Safari 16+, Edge 110+ | Requerimientos — RR030 |
| Formatos de exportacion | PDF y Excel (.xlsx) | Requerimientos — RR030 |
| Cumplimiento normativo | ISO/IEC 27001 (seguridad); ISO/IEC 25010 (calidad); Resolucion ANT 005-DIR-2022-ANT | Requerimientos — RR021–RR023 |

### 6.B Decisiones confirmadas por el equipo (stack y herramientas)

Las siguientes decisiones fueron confirmadas por el equipo de desarrollo y complementan las decisiones de los documentos fuente:

| Decision | Detalle | Fuente |
|----------|---------|--------|
| Version de Python | 3.12.x | Decision de equipo |
| Version de Django | 5.1.x | Decision de equipo |
| Version de PostgreSQL | 18.x | Decision de equipo |
| Entorno de desarrollo | venv + pip freeze (`requirements.txt`) | Decision de equipo |
| Produccion | Nginx + Gunicorn + systemd | Decision de equipo |
| CI/CD | GitHub Actions | Decision de equipo |
| Linting / Formatting | flake8 + black (configuracion en `pyproject.toml`) | Decision de equipo |
| Testing | pytest + pytest-django + coverage.py + factory-boy | Decision de equipo |
| Framework CSS | Tailwind CSS 3.4.17 (CDN, sin build step, compatible con Django templates) | Decision de equipo |
| Interactividad JS | Alpine.js 3.15.9 (CDN, interactividad ligera en templates, sin SPA) | Decision de equipo |
| Prototipo Figma | [Prototipo Web Academico ECPP](https://www.figma.com/make/wHHZTwiWVdUUbOlVb33jO2/Prototipo-Web-Acad%C3%A9mico-ECPP--Copia-?t=jR8TIKaIwUqHD4c6-1) | Decision de equipo |
| Convencion de ramas | `main` / `develop` / `feature/*` / `hotfix/*` | Decision de equipo |
| Distribucion del equipo | Dev A (Frontend + UI) / Dev B (Backend + BDD) | Decision de equipo |
| Gestion del proyecto | Jira | Decision de equipo |

### 6.C Decisiones pendientes por confirmar

No quedan decisiones pendientes. Todas las preguntas de stack y herramientas han sido resueltas.

---

## 7. Estructura inicial del proyecto

> **Nota:** La estructura de carpetas se basa en la arquitectura DDD confirmada en RR028. La convencion de ramas y distribucion del equipo fueron confirmadas por el equipo.

### 7.1 Convencion de ramas Git (confirmada)

```
main          ← codigo estable, desplegable
develop       ← integracion continua
feature/SP0-xx-descripcion  ← ramas de feature por item del sprint
hotfix/descripcion          ← correcciones urgentes en main
```

- Naming: `feature/SP0-01-repo-setup`, `feature/HU01-registro-usuario`
- Versionado: Semantic Versioning (`0.1.0` para Sprint 0, `0.2.0` para Sprint 1, etc.)
- PRs: de `feature/*` hacia `develop`; de `develop` hacia `main` al cierre de sprint.

### 7.2 Distribucion del equipo (confirmada)

| Rol | Responsable | Alcance |
|-----|-------------|---------|
| Dev A — Frontend + UI | Por definir (Martin o Junior) | Templates, Tailwind CSS, Alpine.js, navegacion por rol, componentes reutilizables, responsive |
| Dev B — Backend + BDD | Por definir (Martin o Junior) | Django, PostgreSQL, DDD, API REST (DRF), migraciones, tests, CI |

> **TODO:** confirmar quien toma cada rol (Frontend vs Backend).

### 7.3 Estructura de carpetas propuesta

Basada en la arquitectura DDD confirmada en RR028 y el stack confirmado:

```
proyecto-ecpp/
├── config/                    # Configuracion Django (settings, urls, wsgi, asgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                      # Aplicaciones Django organizadas por bounded context
│   ├── usuarios/              # Agregado: Usuario
│   │   ├── domain/            # Entidades, value objects, repositorios (interfaces)
│   │   ├── application/       # Casos de uso, servicios de aplicacion
│   │   ├── infrastructure/    # Implementaciones de repositorios, adaptadores
│   │   └── presentation/      # Views, serializers, templates
│   ├── academico/             # Agregados: Periodo, Asignatura, Paralelo (nota: "Curso" solo en UI)
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── calificaciones/        # Agregado: Evaluacion
│   ├── asistencia/            # Agregado: Asistencia
│   └── solicitudes/           # Agregado: Solicitud (rectificaciones, justificaciones)
├── templates/                 # Templates globales (base.html, navegacion)
├── static/                    # Archivos estaticos (CSS compilado, JS, imagenes)
│   ├── css/                   # Output de Tailwind CSS
│   └── js/                    # Alpine.js y scripts minimos
├── docs/                      # Documentacion del proyecto
├── tests/                     # Tests globales e integracion
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions pipeline
├── .env.example
├── requirements.txt           # pip freeze (venv)
├── pyproject.toml             # Configuracion flake8, black, pytest, coverage
├── tailwind.config.js         # Configuracion Tailwind CSS 3.x
├── manage.py
└── README.md
```

---

## 8. Configuracion de entorno

### 8.1 Variables de entorno

> **Fuente:** Requerimientos_ECPPP.docx — RR029: "Variables de entorno para gestion de configuraciones sensibles (credenciales de BD, claves API, SMTP) sin almacenamiento en repositorio."

**TODO: confirmar valores especificos con el equipo.** Las siguientes variables son derivadas de los requerimientos y el stack confirmado (Python 3.12.x, Django 5.1.x, PostgreSQL 18.x):

```env
# Base de datos (Fuente: RR029)
DATABASE_NAME=ecppp_db
DATABASE_USER=ecppp_user
DATABASE_PASSWORD=<definir>
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Django
DJANGO_SECRET_KEY=<generar>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Email/SMTP (Fuente: RR030 — envio de OTP, recuperacion, notificaciones)
EMAIL_HOST=<definir>
EMAIL_PORT=<definir>
EMAIL_HOST_USER=<definir>
EMAIL_HOST_PASSWORD=<definir>
EMAIL_USE_TLS=True
```

### 8.2 CI basico (GitHub Actions — confirmado)

Pipeline basico para Sprint 0 usando las herramientas confirmadas por el equipo:

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: ecppp_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: flake8 .
      - run: black --check .
      - run: python manage.py migrate
        env:
          DATABASE_NAME: ecppp_test
          DATABASE_USER: test_user
          DATABASE_PASSWORD: test_pass
          DATABASE_HOST: localhost
          DATABASE_PORT: 5432
      - run: coverage run -m pytest
        env:
          DATABASE_NAME: ecppp_test
          DATABASE_USER: test_user
          DATABASE_PASSWORD: test_pass
          DATABASE_HOST: localhost
          DATABASE_PORT: 5432
      - run: coverage report --fail-under=70
```

---

## 9. Riesgos del Sprint 0

| # | Riesgo | Probabilidad | Impacto | Mitigacion | Responsable |
|---|--------|-------------|---------|-----------|-------------|
| R1 | ~~Acceso al prototipo Figma no disponible o desactualizado~~ — **MITIGADO**: [Enlace Figma confirmado](https://www.figma.com/make/wHHZTwiWVdUUbOlVb33jO2/Prototipo-Web-Acad%C3%A9mico-ECPP--Copia-?t=jR8TIKaIwUqHD4c6-1). Verificar que ambos devs tienen acceso de lectura | Baja | Bajo | Verificar acceso de ambos devs el dia 1. Si el enlace caduca, solicitar nuevo enlace | Dev A (Martin) |
| R2 | Falta de experiencia del equipo en DDD — sobrediseno o subdiseno de agregados en SP0-03 | Media | Medio | Limitar SP0-03 a los 5 agregados confirmados en la planificacion. Consultar referencias (Evans, Vernon). Iterar en sprints posteriores | Dev A + Dev B |
| R3 | Problemas de configuracion de PostgreSQL en maquinas locales — retrasa SP0-02 | Baja | Alto | Preparar alternativa Docker Compose para PostgreSQL. Documentar instalacion paso a paso en README | Dev B (Junior) |
| R4 | Sprint de 5 dias (1 semana) con 10 puntos y 5 items — riesgo de no completar todo si surgen bloqueos | Media | Alto | Priorizar SP0-01 y SP0-02 (criticos para Sprint 1). SP0-05 puede extenderse al dia 1 del Sprint 1 si es necesario | Dev A + Dev B |
| R5 | ~~Decisiones de stack no confirmadas~~ — **MITIGADO**: Stack completo confirmado (ver seccion 6.B). Solo quedan pendientes: herramienta de gestion, versiones exactas de Tailwind/Alpine | Baja | Bajo | Resolver las 3 preguntas pendientes de seccion 6.C en la reunion de planificacion | Dev A (Martin) |
| R6 | Pipeline CI falla por dependencias o configuracion de servicios (PostgreSQL en CI) | Baja | Medio | Fijar versiones en requirements.txt. Usar servicio PostgreSQL en GitHub Actions con variables hardcodeadas para CI | Dev A (Martin) |

---

## 10. Metricas de exito del Sprint 0

| # | Metrica | Criterio de exito | Metodo de verificacion |
|---|---------|-------------------|----------------------|
| M1 | Todos los items SP0-xx completados | 5/5 items marcados como "Done" con evidencia de completitud | Revision del tablero del sprint al cierre (27/03) |
| M2 | Pipeline CI en verde | Al menos 1 ejecucion exitosa del pipeline CI con linting + tests + migraciones | Enlace al pipeline ejecutado en GitHub Actions |
| M3 | Proyecto Django funcional en local | `manage.py runserver` ejecuta sin errores; Django Admin accesible; conexion a PostgreSQL verificada | Demo en la reunion de cierre del Sprint 0 |
| M4 | Documento de arquitectura DDD completo | Documento con los agregados definidos (Usuario, Periodo, Asignatura, Paralelo, Evaluacion, Asistencia, Solicitud), entidades, value objects, diagramas de relaciones y estructura de capas | Archivo `docs/arquitectura-ddd.md` (o similar) commiteado en el repositorio |
| M5 | Layout UI base con paleta corporativa | Templates renderizando con colores `#2D5016`, `#4A7C2F`, `#D4B942`, tipografia Inter, navegacion por rol | Capturas de pantalla en desktop y movil incluidas en la evidencia del item SP0-04 |
| M6 | Backlog Sprint 1 refinado | 6 HUs (HU01–HU06) con criterios de aceptacion verificados, estimaciones confirmadas (16 pts), dependencias documentadas | Backlog en Jira actualizado |
| M7 | Velocidad real vs planificada | Comparar puntos completados (objetivo: 10) vs planificados (10) para calibrar velocidad del equipo | Registro al cierre del sprint; usar como input para ajustar Sprint 1 |

---

## 11. Conflictos detectados entre documentos

Tras la revision cruzada de los 3 documentos fuente, se identificaron los siguientes conflictos o inconsistencias:

### 11.1 Agregado "Curso" vs estructura academica — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | Planificacion — Incremento 0 menciona agregado "Curso"; Requerimientos — RR028 menciona "Curso" como agregado |
| **Inconsistencia** | Los requerimientos funcionales (RR005–RR007) hablan de "Periodo", "Asignatura", "Paralelo" y "Licencia", pero no definen explicitamente un agregado "Curso" como entidad independiente. En las HUs, "curso" se usa como sinonimo informal de "paralelo" o "asignatura matriculada" |
| **Resolucion** | **Decision del equipo:** en codigo y documentacion tecnica se usa exclusivamente "Paralelo" como agregado del dominio. "Curso" queda reservado para el lenguaje de la UI orientado al usuario final. No existe un agregado "Curso" en el modelo DDD |

### 11.2 Capacidad Sprint 4 — nota sobre feriado inconsistente — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | HistoriasUsuario_Sprints_ECPPP.docx — Capacidades por sprint |
| **Inconsistencia** | Sprint 4 (11/05–22/05) indicaba "Capacidad reducida a 18 puntos por feriado Batalla de Pichincha", pero el feriado (24 mayo) cae en Sprint 5, no en Sprint 4 |
| **Resolucion** | **Decision del equipo:** Sprint 4 queda en **20 puntos** (sin feriados que lo afecten). Sprint 5 baja a **18 puntos** por el feriado de Batalla de Pichincha (25 mayo 2026). Total del proyecto se mantiene en **100 puntos** (10 + 16 + 20 + 18 + 20 + 18 = 102 → nota: el total ajustado sube a 102; verificar si se reasignan 2 puntos o se acepta el aumento) |

### 11.3 Parciales: tipo de evaluacion "Parcial 10h" no reflejado en HUs — RESUELTO

| Conflicto | Detalle |
|-----------|---------|
| **Donde** | Requerimientos — RR008: "Parcial 2 – 10h, Parcial 4 – 10h"; HU08 y HU10 no mencionan la distincion "Parcial 10h" |
| **Inconsistencia** | RR008 distingue parciales teoricos (Parcial 1, Parcial 3) de parciales practicos de 10 horas (Parcial 2 – 10h, Parcial 4 – 10h), pero HU08 y HU10 listan los 4 parciales sin esta distincion |
| **Resolucion** | **Decision del equipo:** ampliar los criterios de aceptacion de HU08 (Registro de calificaciones) y HU10 (Flujo de rectificacion) para incluir explicitamente el tipo de evaluacion "Parcial 10h" (parciales practicos). No se crean HUs nuevas; se agregan escenarios que contemplen la seleccion del tipo de parcial (teorico vs practico 10h). Esto impacta el modelo de datos de Evaluacion en SP0-03 (agregar atributo `tipo_parcial` o similar) |

---

## 12. Referencias

| # | Documento | Archivo | Version | Fecha |
|---|-----------|---------|---------|-------|
| 1 | Planificacion de Sprints — Capstone ECPP | `Planificacion_Sprints_Capstone_ECPP.docx` | 1.0 | Marzo 2026 |
| 2 | Levantamiento de Requerimientos — Plataforma Web Academica ECPPP | `Requerimientos_ECPPP.docx` | 1.0 | Marzo 2026 |
| 3 | Historias de Usuario y Criterios de Aceptacion — ECPPP | `HistoriasUsuario_Sprints_ECPPP.docx` | 1.0 | Marzo 2026 |

---

*Documento generado como parte del Sprint 0 del proyecto Plataforma Web Academica ECPPP.*
*Estado: Draft — pendiente de revision y aprobacion por el equipo.*
