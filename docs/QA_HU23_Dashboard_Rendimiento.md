# Auditoría QA — HU23: Dashboard de Rendimiento Académico

| Campo | Valor |
|---|---|
| Historia de Usuario | HU23 — Dashboard de Rendimiento por Curso |
| Sprint | Sprint 4 |
| Módulo | `apps/academico` |
| URL base | `/academico/dashboard-rendimiento/` |
| Roles con acceso | `inspector`, `secretaria` |
| Fecha de auditoría | 2026-06-12 (actualizado 2026-06-14) |
| Autor | QA — Proyecto ECPPP |

---

## 1. Alcance de la HU23

La HU23 cubre el dashboard de rendimiento académico que permite al inspector y secretaria:

- Visualizar métricas comparativas de calificaciones y asistencia por curso (paralelo)
- Filtrar en cascada: Período → Curso (paralelo) → Materia / Inasistencia mínima
- Ver KPIs globales: cursos analizados, promedio global, asistencia global, aprobados/reprobados
- Ver gráfico de barras de promedios con línea de aprobación en 16 pts
- Ver donut de distribución aprobados/reprobados/sin notas
- Ver gráfico de barras de % asistencia con umbral en 90%
- Ver tabla detalle por curso con mini barras de progreso y badge de estado
- Recibir feedback de estado por fila: Bien / Atención / Crítico

---

## 2. Prerequisitos de Entorno de Prueba

Antes de ejecutar cualquier caso de prueba, verificar que la base de datos tenga:

### 2.1 Datos mínimos requeridos

| Entidad | Mínimo recomendado | Propósito |
|---|---|---|
| `Periodo` | 2 períodos (1 activo, 1 inactivo) | Probar auto-selección y selector |
| `TipoLicencia` | Al menos 1 (ej. `B`) | Requerido por Período |
| `Asignatura` | Al menos 3 | Probar filtro por materia |
| `Usuario (docente)` | Al menos 2 | Datos realistas en tabla |
| `Paralelo` | ≥ 3 del período activo (de distintas asignaturas) | Probar dropdown y filtros |
| `Usuario (estudiante)` | ≥ 5 matriculados en distintos paralelos | Datos de KPIs |
| `Matricula` (estado ACTIVA) | ≥ 5 | Cálculo de promedios |
| `Evaluacion` + `Calificacion` | Variadas: algunos ≥16, algunos <16, algunos 0 | Probar colores y "Sin notas" |
| `Asistencia` | Variada: >95%, 90-94%, <90% en distintos paralelos | Probar colores asistencia |
| `Paralelo` (sin estudiantes) | 1 | Probar chip "Sin estudiantes" |
| `Paralelo` (sin calificaciones) | 1 | Probar texto "Sin notas" |

### 2.2 Usuarios de prueba

| Usuario | Rol | Propósito |
|---|---|---|
| `inspector_test` | inspector | Acceso completo HU23 |
| `secretaria_test` | secretaria | Acceso completo HU23 |
| `docente_test` | docente | Debe recibir 403 |
| `estudiante_test` | estudiante | Debe recibir 403 |

---

## 3. Suite 1 — Control de Acceso y Seguridad

### TC-01-01: Acceso como Inspector
- **Objetivo:** Verificar que el rol inspector puede acceder al dashboard
- **Pasos:**
  1. Iniciar sesión como `inspector_test`
  2. Navegar a `/academico/dashboard-rendimiento/`
- **Resultado esperado:** Página carga correctamente con código HTTP 200, breadcrumb visible, formulario de filtros presente
- **PASS / FAIL:** ___

### TC-01-02: Acceso como Secretaria
- **Objetivo:** Verificar que el rol secretaria puede acceder al dashboard
- **Pasos:**
  1. Iniciar sesión como `secretaria_test`
  2. Navegar a `/academico/dashboard-rendimiento/`
- **Resultado esperado:** HTTP 200, dashboard carga sin errores
- **PASS / FAIL:** ___

### TC-01-03: Acceso como Docente — bloqueado
- **Objetivo:** Verificar que docentes no tienen acceso
- **Pasos:**
  1. Iniciar sesión como `docente_test`
  2. Navegar a `/academico/dashboard-rendimiento/`
- **Resultado esperado:** HTTP 403 o redirect a página de acceso denegado. No se muestran datos académicos
- **PASS / FAIL:** ___

### TC-01-04: Acceso como Estudiante — bloqueado
- **Objetivo:** Verificar que estudiantes no tienen acceso
- **Pasos:**
  1. Iniciar sesión como `estudiante_test`
  2. Navegar a `/academico/dashboard-rendimiento/`
- **Resultado esperado:** HTTP 403 o redirect a acceso denegado
- **PASS / FAIL:** ___

### TC-01-05: Acceso sin autenticación — redirect a login
- **Objetivo:** Verificar que la vista requiere login
- **Pasos:**
  1. Abrir sesión de incógnito (sin cookies)
  2. Navegar directamente a `/academico/dashboard-rendimiento/`
- **Resultado esperado:** Redirect a `/usuarios/login/` (o equivalente). No se renderiza ningún dato
- **PASS / FAIL:** ___

### TC-01-06: Inyección en parámetros GET — periodo=abc
- **Objetivo:** Verificar que parámetros no numéricos en GET son rechazados
- **Pasos:**
  1. Autenticado como inspector, navegar a `/academico/dashboard-rendimiento/?periodo=abc`
- **Resultado esperado:** Redirect limpio a `/academico/dashboard-rendimiento/` (sin parámetros). No hay error 500
- **PASS / FAIL:** ___

### TC-01-07: Inyección en parámetros GET — asignatura=; DROP TABLE
- **Objetivo:** Verificar que SQL/script en params no genera error ni executa código
- **Pasos:**
  1. Autenticado como inspector, navegar a `/academico/dashboard-rendimiento/?periodo=1&asignatura=;DROP TABLE`
- **Resultado esperado:** Redirect limpio o página carga sin ejecutar nada malicioso
- **PASS / FAIL:** ___

### TC-01-08: Inasistencia con valor arbitrario — inasistencia=99
- **Objetivo:** Verificar que valores de inasistencia fuera del listado permitido son ignorados
- **Pasos:**
  1. Autenticado, navegar a `/academico/dashboard-rendimiento/?periodo=1&inasistencia=99`
- **Resultado esperado:** La página carga mostrando todos los cursos (inasistencia=99 ignorado, tratado como "Todos"). El select de inasistencia muestra "— Todos —"
- **PASS / FAIL:** ___

### TC-01-09: Paralelo de otro período — cross-period
- **Objetivo:** Verificar que filtrar por un paralelo que no pertenece al período seleccionado es ignorado
- **Pasos:**
  1. Obtener el ID de un paralelo del período B (inactivo)
  2. Navegar a `/academico/dashboard-rendimiento/?periodo=<ID-periodoA>&paralelo=<ID-paralelo-periodoB>`
- **Resultado esperado:** Se muestran TODOS los cursos del período A (el paralelo inválido se ignora). No hay error 500
- **PASS / FAIL:** ___

---

## 4. Suite 2 — Estado Inicial y Carga Automática

### TC-02-01: Estado inicial sin parámetros — período activo auto-seleccionado
- **Objetivo:** Verificar que al cargar la página sin params, se auto-selecciona el período activo
- **Pasos:**
  1. Autenticado como inspector
  2. Navegar a `/academico/dashboard-rendimiento/` (sin parámetros)
- **Resultado esperado:**
  - El select de "Período académico" muestra el período activo (marcado con "✓ activo") como seleccionado
  - Se muestran KPIs y gráficos del período activo
  - Los chips de filtros activos muestran el nombre del período
- **PASS / FAIL:** ___

### TC-02-02: Estado inicial sin período activo en BD
- **Objetivo:** Verificar comportamiento cuando no hay ningún período activo
- **Pasos:**
  1. Desactivar todos los períodos en la BD temporalmente
  2. Navegar a `/academico/dashboard-rendimiento/`
- **Resultado esperado:**
  - El select de período muestra "— Elige un período —"
  - Se muestra el panel vacío con ícono y texto "Selecciona un período académico para empezar"
  - No se muestran KPIs ni gráficos
  - El botón "Aplicar filtros" aparece deshabilitado (opacity-50)
- **PASS / FAIL:** ___

### TC-02-03: Panel vacío sin período — texto instructivo
- **Objetivo:** Verificar que el estado inicial guía al usuario correctamente
- **Pasos:**
  1. Navegar a la URL sin params (o después de limpiar todos los filtros)
  2. Observar el área bajo el formulario
- **Resultado esperado:**
  - Ícono de gráficas (gris)
  - Texto "Selecciona un período académico para empezar"
  - Sub-texto "Usa el paso 1 del filtro de arriba."
- **PASS / FAIL:** ___

---

## 5. Suite 3 — Filtros en Cascada

### TC-03-01: Paso 1 — selector de período muestra todos los períodos
- **Objetivo:** Verificar que el dropdown de período lista todos los períodos disponibles
- **Pasos:**
  1. Cargar el dashboard
  2. Abrir el select de "Período académico"
- **Resultado esperado:**
  - Primera opción: "— Elige un período —"
  - Listados todos los períodos ordenados por `fecha_inicio` DESC
  - Formato: `{nombre} ({codigo_licencia})` + " ✓ activo" para el activo
- **PASS / FAIL:** ___

### TC-03-02: Paso 2 — dropdown de Curso deshabilitado hasta seleccionar período
- **Objetivo:** Verificar que el select de Curso está bloqueado sin período
- **Pasos:**
  1. Asegurarse de que no hay período seleccionado en el formulario
  2. Observar el campo "Curso"
- **Resultado esperado:**
  - Select con atributo `disabled`
  - Aparece en gris (`bg-gray-50 text-gray-400`)
  - El texto de ayuda dice "Primero selecciona un período."
  - El indicador numérico "2" aparece en gris (no en primary)
- **PASS / FAIL:** ___

### TC-03-03: Paso 2 — cursos se cargan dinámicamente al seleccionar período
- **Objetivo:** Verificar que Alpine.js filtra los paralelos al elegir período
- **Pasos:**
  1. Seleccionar un período que tenga ≥ 2 paralelos
  2. Observar el dropdown de Curso inmediatamente (sin hacer submit)
- **Resultado esperado:**
  - El select de Curso se habilita
  - Las opciones aparecen dinámicamente (sin recargar la página)
  - El texto de ayuda muestra "N curso(s) disponibles. Deja en blanco para ver todos."
  - El indicador "2" cambia a color primary
- **PASS / FAIL:** ___

### TC-03-04: Paso 2 — período sin cursos muestra mensaje correcto
- **Objetivo:** Verificar el mensaje cuando el período no tiene paralelos
- **Pasos:**
  1. Seleccionar un período que no tenga paralelos creados
  2. Observar el área del paso 2
- **Resultado esperado:**
  - El select aparece con `disabled`
  - El texto de ayuda dice "Sin cursos disponibles para este período."
- **PASS / FAIL:** ___

### TC-03-05: Paso 2 — cambiar período limpia el curso seleccionado
- **Objetivo:** Verificar que al cambiar el período, el curso anterior se resetea
- **Pasos:**
  1. Seleccionar Período A → seleccionar Curso X del período A
  2. Cambiar al Período B (sin hacer submit)
- **Resultado esperado:**
  - El select de Curso vuelve a "— Todos los cursos del período —"
  - Los options de Curso se actualizan para mostrar los del Período B
  - El campo Materia también se resetea a "— Todas las materias —"
- **PASS / FAIL:** ___

### TC-03-06: Paso 3 — sub-filtros deshabilitados sin período
- **Objetivo:** Verificar que los sub-filtros de Materia e Inasistencia están bloqueados
- **Pasos:**
  1. Cargar la página sin período seleccionado
  2. Observar los cards del paso 3
- **Resultado esperado:**
  - Los dos cards del paso 3 tienen `opacity-50`
  - Ambos selects tienen atributo `disabled`
  - No se puede interactuar con ellos
- **PASS / FAIL:** ___

### TC-03-07: Paso 3 — sub-filtros se habilitan al elegir período
- **Objetivo:** Verificar que los sub-filtros se activan con período seleccionado
- **Pasos:**
  1. Seleccionar un período en el paso 1 (sin hacer submit)
  2. Observar los cards del paso 3
- **Resultado esperado:**
  - Los cards recuperan opacidad normal (sin opacity-50)
  - Los selects ya no tienen `disabled`
  - Se puede abrir y seleccionar opciones
- **PASS / FAIL:** ___

### TC-03-08: Filtro por materia — solo muestra cursos de esa asignatura
- **Objetivo:** Verificar que el filtro de asignatura funciona correctamente
- **Pasos:**
  1. Seleccionar un período con ≥ 3 paralelos de distintas asignaturas
  2. Hacer submit con solo el período
  3. Anotar la cantidad de cursos en la tabla
  4. Volver, seleccionar una asignatura específica, hacer submit
- **Resultado esperado:**
  - Resultado filtrado muestra SOLO los cursos de esa asignatura
  - KPIs se recalculan para el subconjunto filtrado
  - Chip de filtro activo muestra el código de la asignatura
- **PASS / FAIL:** ___

### TC-03-09: Filtro por inasistencia — umbral 10%
- **Objetivo:** Verificar que el filtro de inasistencia mínima excluye cursos con buena asistencia
- **Pasos:**
  1. Seleccionar período con paralelos de distinto % asistencia
  2. Seleccionar inasistencia "≥ 10%", hacer submit
- **Resultado esperado:**
  - Solo aparecen cursos donde `(100 - porcentaje_asistencia) >= 10`, es decir, asistencia ≤ 90%
  - Los cursos con asistencia ≥ 90% quedan fuera
  - Chip "Inasist. ≥ 10%" aparece en el área de filtros activos
- **PASS / FAIL:** ___

### TC-03-10: Filtro combinado — curso + materia
- **Objetivo:** Verificar que múltiples filtros se aplican en conjunto
- **Pasos:**
  1. Seleccionar período + curso específico + materia específica
  2. Hacer submit
- **Resultado esperado:**
  - Si el curso seleccionado pertenece a la materia seleccionada: se muestra 1 resultado
  - Si no pertenece: se muestra el empty state "Sin resultados para los filtros aplicados"
  - KPIs reflejan solo el subconjunto
- **PASS / FAIL:** ___

### TC-03-11: Botón "Limpiar" resetea todos los filtros
- **Objetivo:** Verificar que el link "Limpiar" borra todos los filtros
- **Pasos:**
  1. Aplicar 3 filtros activos (período + curso + materia)
  2. Hacer clic en "Limpiar"
- **Resultado esperado:**
  - Redirect a `/academico/dashboard-rendimiento/` (sin query params)
  - Se re-aplica el período activo automáticamente
  - No quedan chips de filtros activos anteriores (excepto el período activo)
- **PASS / FAIL:** ___

### TC-03-12: Chips de filtros activos — visibilidad correcta
- **Objetivo:** Verificar que los chips representan fielmente los filtros aplicados
- **Pasos:**
  1. Aplicar período + curso + inasistencia ≥ 5%
  2. Verificar la sección "Filtros activos:"
- **Resultado esperado:**
  - Chip violeta/primary para el nombre del período
  - Chip azul para el nombre del curso
  - Chip ámbar "Inasist. ≥ 5%"
  - No aparece chip de materia (no se seleccionó)
- **PASS / FAIL:** ___

---

## 6. Suite 4 — Comportamiento Alpine.js (Interactividad Frontend)

### TC-04-01: Script JSON de paralelos carga correctamente
- **Objetivo:** Verificar que el bloque JSON embebido en la página es válido
- **Pasos:**
  1. Abrir la página en cualquier estado
  2. Abrir DevTools → Elements → buscar `<script id="paralelos-data">`
  3. Copiar el contenido y pegarlo en `JSON.parse(...)` en la consola
- **Resultado esperado:**
  - `JSON.parse(...)` no lanza error
  - El resultado es un array de objetos con propiedades: `id`, `nombre`, `periodo_id`, `asignatura_id`
  - No hay entidades HTML escapadas (`&quot;`, `&lt;`, etc.) en los valores
- **PASS / FAIL:** ___

### TC-04-02: Indicadores numéricos del stepper cambian de color
- **Objetivo:** Verificar que los pasos 2 y 3 se iluminan al elegir período
- **Pasos:**
  1. Cargar la página sin período → observar indicadores 2 y 3 (deben estar grises)
  2. Seleccionar un período en el dropdown (sin submit)
  3. Observar los indicadores 2 y 3
- **Resultado esperado:**
  - Sin período: indicadores 2 y 3 con fondo `bg-gray-200 text-gray-400`
  - Con período: indicadores 2 y 3 con fondo primary (color del sistema)
- **PASS / FAIL:** ___

### TC-04-03: Selección de curso persiste al hacer submit
- **Objetivo:** Verificar que el curso seleccionado antes del submit aparece seleccionado después
- **Pasos:**
  1. Seleccionar período + curso específico
  2. Hacer submit con "Aplicar filtros"
  3. Observar el select de Curso al recargar
- **Resultado esperado:**
  - El select de Curso muestra la misma opción que se eligió antes del submit (no "— Todos los cursos —")
  - Los datos mostrados corresponden a ese curso
- **PASS / FAIL:** ___

### TC-04-04: Spinner y texto "Cargando…" al hacer submit
- **Objetivo:** Verificar el feedback visual al enviar el formulario
- **Pasos:**
  1. Seleccionar un período
  2. Hacer clic en "Aplicar filtros" — observar el botón DURANTE la carga
- **Resultado esperado:**
  - El ícono de lupa desaparece
  - Aparece un spinner animado (`animate-spin`)
  - El texto cambia de "Aplicar filtros" a "Cargando…"
  - El botón queda deshabilitado (no se puede hacer doble click)
- **Nota:** Este comportamiento es muy breve. Puede necesitarse throttling de red (DevTools → Network → Slow 3G) para apreciarlo
- **PASS / FAIL:** ___

### TC-04-05: Botón "Aplicar filtros" deshabilitado sin período
- **Objetivo:** Verificar que no se puede enviar el formulario sin período
- **Pasos:**
  1. Cargar la página fresca
  2. Sin seleccionar período, intentar hacer clic en "Aplicar filtros"
- **Resultado esperado:**
  - El botón tiene atributo `disabled`
  - Apariencia: `opacity-50 cursor-not-allowed`
  - No se envía el formulario
  - El cursor al pasar sobre el botón muestra "no-drop" o similar
- **PASS / FAIL:** ___

---

## 7. Suite 5 — KPIs y Cards de Resumen

### TC-05-01: Card "Cursos analizados" — sin filtro de curso
- **Objetivo:** Verificar el KPI cuando se ven todos los cursos de un período
- **Pasos:**
  1. Seleccionar período con 5 paralelos, sin filtro de curso
  2. Observar card "Cursos analizados"
- **Resultado esperado:**
  - Número grande: `5`
  - No aparece texto "de X" (porque no hay filtro que reduzca el número)
- **PASS / FAIL:** ___

### TC-05-02: Card "Cursos analizados" — con filtro de curso activo
- **Objetivo:** Verificar que el KPI muestra "X de Y" cuando hay filtro
- **Pasos:**
  1. Período con 5 paralelos → filtrar por un curso específico
  2. Observar card "Cursos analizados"
- **Resultado esperado:**
  - Número grande: `1` (solo el curso filtrado)
  - Aparece texto secundario "de 5" en gris
- **PASS / FAIL:** ___

### TC-05-03: Card "Promedio global" — colores según umbral
- **Objetivo:** Verificar los umbrales de color del promedio global
- **Pasos:**
  1. Crear escenario con promedio global ≥ 16 → verificar color verde
  2. Crear escenario con promedio 14–15 → verificar color ámbar
  3. Crear escenario con promedio < 14 → verificar color rojo
- **Resultado esperado:**
  - ≥ 16: `text-green-600`
  - 14–15.99: `text-amber-500`
  - < 14: `text-red-600`
  - Siempre muestra `/20` como sub-texto gris
- **PASS / FAIL:** ___

### TC-05-04: Card "Asistencia global" — colores según umbral
- **Objetivo:** Verificar umbrales de color de asistencia global
- **Pasos:**
  1. Escenario con asistencia ≥ 95% → verificar azul
  2. Escenario 90–94% → verificar ámbar
  3. Escenario < 90% → verificar rojo
- **Resultado esperado:**
  - ≥ 95%: `text-blue-600`
  - 90–94.9%: `text-amber-500`
  - < 90%: `text-red-600`
- **PASS / FAIL:** ___

### TC-05-05: Card "Aprobados / Reprobados" — valores separados
- **Objetivo:** Verificar que los números de aprobados y reprobados son correctos
- **Pasos:**
  1. Con datos conocidos (ej. 3 aprobados, 2 reprobados)
  2. Observar la card
- **Resultado esperado:**
  - Número verde: cantidad de aprobados
  - Separador `/` en gris claro
  - Número rojo: cantidad de reprobados
  - La suma de ambos debe ser igual o menor que el total de estudiantes matriculados
- **PASS / FAIL:** ___

---

## 8. Suite 6 — Gráfico de Barras: Promedio de Notas

### TC-06-01: Gráfico renderiza con datos
- **Objetivo:** Verificar que el canvas de promedios se renderiza correctamente
- **Pasos:**
  1. Seleccionar un período con ≥ 2 cursos y calificaciones cargadas
  2. Observar la sección "Calificaciones"
- **Resultado esperado:**
  - El canvas `chartPromedios` es visible
  - Se muestran barras verticales, una por curso
  - El eje Y tiene escala 0–20
  - Existe una línea horizontal punteada roja en y=16
- **PASS / FAIL:** ___

### TC-06-02: Gráfico de barras — colores según promedio
- **Objetivo:** Verificar que cada barra tiene el color correcto
- **Pasos:**
  1. Tener cursos con promedio ≥16 (verde), 14–15 (ámbar), <14 (rojo)
  2. Observar el gráfico
- **Resultado esperado:**
  - Barras verdes: `rgba(22,163,74,0.80)` para promedio ≥ 16
  - Barras ámbar: `rgba(245,158,11,0.80)` para 14–15.99
  - Barras rojas: `rgba(220,38,38,0.80)` para < 14
- **PASS / FAIL:** ___

### TC-06-03: Gráfico de barras — no se deforman con pocos cursos
- **Objetivo:** Verificar que con solo 1 o 2 cursos, las barras no son excesivamente anchas
- **Pasos:**
  1. Filtrar para mostrar solo 1 o 2 cursos
  2. Observar el ancho de las barras
- **Resultado esperado:**
  - El ancho de cada barra no supera ~48px (`maxBarThickness: 48`)
  - Las barras no ocupan todo el ancho del canvas
  - La visualización es proporcional y legible
- **PASS / FAIL:** ___

### TC-06-04: Gráfico de barras — leyenda de colores visible
- **Objetivo:** Verificar los indicadores de la leyenda
- **Pasos:**
  1. Observar el encabezado del card "Promedio de notas por curso"
- **Resultado esperado:**
  - Cuadrado verde + "≥ 16"
  - Cuadrado ámbar + "14–15"
  - Cuadrado rojo + "< 14"
  - Línea punteada roja + "Aprobación"
- **PASS / FAIL:** ___

### TC-06-05: Tooltip del gráfico al hacer hover
- **Objetivo:** Verificar que el tooltip muestra el promedio al pasar el cursor
- **Pasos:**
  1. Hover sobre cualquier barra del gráfico de promedios
- **Resultado esperado:**
  - Tooltip aparece con el nombre del curso y el valor del promedio
  - No hay error en consola
- **PASS / FAIL:** ___

---

## 9. Suite 7 — Gráfico Donut: Distribución de Estudiantes

### TC-07-01: Donut renderiza correctamente
- **Objetivo:** Verificar que el donut se renderiza con 3 segmentos
- **Pasos:**
  1. Con datos que incluyan aprobados, reprobados y estudiantes sin notas
  2. Observar el canvas `chartDistribucion`
- **Resultado esperado:**
  - Gráfico de tipo donut visible
  - 3 segmentos: verde (aprobados), rojo (reprobados), gris (sin notas)
  - Centro hueco (`cutout: 68%`)
- **PASS / FAIL:** ___

### TC-07-02: Leyenda del donut muestra porcentajes
- **Objetivo:** Verificar que los porcentajes en la leyenda son correctos
- **Pasos:**
  1. Con datos conocidos (ej. 3 aprobados, 1 reprobado, 1 sin notas = 5 total)
  2. Observar la leyenda bajo el donut
- **Resultado esperado:**
  - "Aprobados: 3 (60%)"
  - "Reprobados: 1 (20%)"
  - "Sin notas aún: 1 (20%)"
  - Los porcentajes suman ~100% (puede haber redondeo por `widthratio`)
- **PASS / FAIL:** ___

### TC-07-03: Tooltip del donut muestra porcentaje
- **Objetivo:** Verificar que el tooltip incluye el porcentaje calculado dinámicamente
- **Pasos:**
  1. Hover sobre cualquier segmento del donut
- **Resultado esperado:**
  - Formato: ` Aprobados: 3 (60.0%)`
  - No hay error en consola
- **PASS / FAIL:** ___

### TC-07-04: Donut con todos los estudiantes sin notas
- **Objetivo:** Verificar comportamiento cuando no hay calificaciones
- **Pasos:**
  1. Filtrar por un curso que no tenga calificaciones cargadas
  2. Observar el donut
- **Resultado esperado:**
  - Todo el donut en gris (segmento "Sin notas aún")
  - Leyenda: Aprobados: 0 (0%), Reprobados: 0 (0%), Sin notas: N (100%)
- **PASS / FAIL:** ___

---

## 10. Suite 8 — Gráfico de Barras: % Asistencia

### TC-08-01: Gráfico de asistencia renderiza correctamente
- **Objetivo:** Verificar que el canvas de asistencia se muestra
- **Pasos:**
  1. Con período con ≥ 2 cursos y registros de asistencia
  2. Observar la sección "Asistencia"
- **Resultado esperado:**
  - Canvas `chartAsistencia` visible
  - Barras verticales, una por curso
  - Eje Y de 0 a 100 (porcentaje)
  - Línea horizontal punteada roja en y=90 (umbral mínimo)
- **PASS / FAIL:** ___

### TC-08-02: Colores de barras según % asistencia
- **Objetivo:** Verificar la codificación de color por rango de asistencia
- **Pasos:**
  1. Tener cursos con asistencia ≥95%, 90–94%, <90%
  2. Observar los colores de las barras
- **Resultado esperado:**
  - Azul `rgba(37,99,235,0.80)`: asistencia ≥ 95%
  - Índigo `rgba(99,102,241,0.75)`: asistencia 90–94%
  - Rojo `rgba(220,38,38,0.80)`: asistencia < 90%
- **PASS / FAIL:** ___

### TC-08-03: Barras de asistencia no son excesivamente anchas
- **Objetivo:** Verificar que `maxBarThickness: 48` aplica también a este gráfico
- **Pasos:**
  1. Filtrar a 1 solo curso
  2. Observar el ancho de la barra en el gráfico de asistencia
- **Resultado esperado:**
  - La barra tiene ancho razonable (≤ 48px), no ocupa todo el canvas
- **PASS / FAIL:** ___

### TC-08-04: Panel "Resumen asistencia" — color y texto según umbral
- **Objetivo:** Verificar que el panel derecho de asistencia cambia de estado visualmente
- **Pasos:**
  1. Escenario con asistencia global ≥ 95%
  2. Escenario con asistencia global 90–94%
  3. Escenario con asistencia global < 90%
- **Resultado esperado:**
  - ≥ 95%: número en `text-blue-600`, texto "Asistencia óptima" en azul
  - 90–94.9%: número en `text-indigo-500`, texto "En nivel de alerta" en índigo
  - < 90%: número en `text-red-600`, texto "Asistencia crítica" en rojo
- **PASS / FAIL:** ___

---

## 11. Suite 9 — Tabla de Detalle por Curso

### TC-09-01: Tabla muestra todas las columnas
- **Objetivo:** Verificar que la tabla tiene las 9 columnas requeridas
- **Pasos:**
  1. Con cualquier resultado, observar el encabezado de la tabla
- **Resultado esperado:**
  Columnas presentes en orden: Curso | Asignatura | Docente | Estudiantes | Promedio | % Aprobación | % Asistencia | % Reprobación | **Estado**
- **PASS / FAIL:** ___

### TC-09-02: Fila con barra lateral de color (border-left)
- **Objetivo:** Verificar el indicador visual de estado por fila
- **Pasos:**
  1. Curso con promedio ≥16 y asistencia ≥90%
  2. Curso con promedio 14–15 o asistencia 90–94%
  3. Curso con promedio <14 y asistencia <90%
- **Resultado esperado:**
  - Verde (`border-l-green-500`): promedio ≥16 AND asistencia ≥90%
  - Ámbar (`border-l-amber-400`): promedio ≥14 OR asistencia ≥90% (pero no ambos en verde)
  - Rojo (`border-l-red-500`): ninguna condición de verde/ámbar
- **PASS / FAIL:** ___

### TC-09-03: Mini barra de progreso — Promedio
- **Objetivo:** Verificar la micro-barra bajo el número de promedio
- **Pasos:**
  1. Observar la celda "Promedio" de cualquier fila con calificaciones
- **Resultado esperado:**
  - Número del promedio visible en color apropiado
  - Barra delgada (h-1, w-12) debajo del número
  - El ancho de la barra corresponde a `promedio/20 * 100%`
  - El color de la barra coincide con el del texto (verde/ámbar/rojo)
- **PASS / FAIL:** ___

### TC-09-04: Mini barra de progreso — % Aprobación
- **Objetivo:** Verificar la micro-barra de aprobación
- **Pasos:**
  1. Observar la celda "% Aprobación" con datos conocidos (ej. 60%)
- **Resultado esperado:**
  - Chip verde con "60%"
  - Barra verde delgada con ancho del 60% del contenedor
- **PASS / FAIL:** ___

### TC-09-05: Mini barra de progreso — % Asistencia
- **Objetivo:** Verificar la micro-barra de asistencia con colores correctos
- **Pasos:**
  1. Fila con asistencia ≥95%, 90–94%, <90%
- **Resultado esperado:**
  - ≥95%: número azul + barra azul
  - 90–94%: número índigo + barra índigo
  - <90%: número rojo + barra roja
- **PASS / FAIL:** ___

### TC-09-06: Badge "Estado" por fila
- **Objetivo:** Verificar el badge de estado general combinado
- **Pasos:**
  1. Fila con promedio ≥16 AND asistencia ≥90%
  2. Fila con promedio ≥14 OR asistencia ≥90% (pero no ambos en verde)
  3. Fila con promedio <14 AND asistencia <90%
- **Resultado esperado:**
  1. Badge "Bien" en verde (`bg-green-50 text-green-700`)
  2. Badge "Atención" en ámbar (`bg-amber-50 text-amber-700`)
  3. Badge "Crítico" en rojo (`bg-red-50 text-red-700`)
- **PASS / FAIL:** ___

### TC-09-07: Celda "Promedio" — muestra "Sin notas" cuando corresponde
- **Objetivo:** Verificar el estado especial para cursos sin calificaciones
- **Pasos:**
  1. Filtrar o tener un curso donde promedio_general = 0 (sin calificaciones)
  2. Observar la celda Promedio de esa fila
- **Resultado esperado:**
  - NO muestra "0" ni "0.0"
  - Muestra texto en cursiva gris: "Sin notas"
  - La mini barra no aparece
- **PASS / FAIL:** ___

### TC-09-08: Curso sin estudiantes — chip "Sin estudiantes"
- **Objetivo:** Verificar la alerta visual para paralelos vacíos
- **Pasos:**
  1. Tener un paralelo con 0 matrículas activas
  2. Observar la celda "Curso" de esa fila
- **Resultado esperado:**
  - El nombre del curso aparece normalmente
  - Junto al nombre: chip gris pequeño con texto "Sin estudiantes"
  - La celda "Estudiantes" muestra "0"
- **PASS / FAIL:** ___

### TC-09-09: Código de asignatura en chip monospace
- **Objetivo:** Verificar el estilo del código de asignatura
- **Pasos:**
  1. Observar la columna "Asignatura" de cualquier fila
- **Resultado esperado:**
  - Código de asignatura en chip gris con `font-mono` (ej. "LT-101")
  - Nombre completo de la asignatura en texto normal junto al chip
- **PASS / FAIL:** ___

### TC-09-10: Tabla con scroll horizontal en pantalla angosta
- **Objetivo:** Verificar que la tabla no rompe el layout en móvil
- **Pasos:**
  1. Abrir el dashboard en resolución 375px de ancho (iPhone SE)
  2. Bajar a la sección "Detalle por curso"
- **Resultado esperado:**
  - La tabla tiene scroll horizontal (`overflow-x-auto`)
  - El contenido de las celdas no se desborda fuera del contenedor
  - El resto de la página (fuera de la tabla) no tiene scroll horizontal
- **PASS / FAIL:** ___

---

## 12. Suite 10 — Estados Especiales y Casos Borde

### TC-10-01: Empty state — período seleccionado pero sin resultados
- **Objetivo:** Verificar el panel de "Sin resultados"
- **Pasos:**
  1. Seleccionar un período que tenga cursos
  2. Aplicar filtro de asignatura que no pertenezca a ningún paralelo de ese período
- **Resultado esperado:**
  - No se muestran KPIs ni gráficos
  - Aparece panel vacío: ícono de barras, "Sin resultados para los filtros aplicados"
  - Sub-texto: "Prueba con un curso o materia distinta, o limpia los filtros."
  - Link "Limpiar filtros" funcional que regresa a estado limpio
- **PASS / FAIL:** ___

### TC-10-02: Un solo curso — gráficos no se deforman
- **Objetivo:** Verificar que los gráficos manejan correctamente 1 solo punto de datos
- **Pasos:**
  1. Filtrar para mostrar solo 1 curso
  2. Observar ambos gráficos de barras
- **Resultado esperado:**
  - Los gráficos muestran 1 barra
  - La barra tiene ancho razonable (no se expande al 100% del canvas)
  - La línea de umbral (16 pts / 90%) sigue visible
- **PASS / FAIL:** ___

### TC-10-03: Período sin ningún paralelo — tabla vacía
- **Objetivo:** Verificar que se muestra empty state si el período existe pero no tiene paralelos
- **Pasos:**
  1. Crear un período sin paralelos asociados o seleccionar uno vacío
  2. Aplicar filtros con ese período
- **Resultado esperado:**
  - Empty state con "Sin resultados para los filtros aplicados"
  - No hay error 500
- **PASS / FAIL:** ___

### TC-10-04: Promedio exactamente en umbral — 16.00
- **Objetivo:** Verificar que el umbral exacto se clasifica correctamente
- **Pasos:**
  1. Curso con promedio_general = 16.00 exacto
  2. Observar el color del promedio en la tabla y la barra
- **Resultado esperado:**
  - Color verde (el umbral ≥ 16 es inclusivo)
  - Mini barra verde con ancho de 80% (16/20 * 100)
  - Badge "Bien" si la asistencia también es ≥ 90%
- **PASS / FAIL:** ___

### TC-10-05: Asistencia exactamente en umbral — 90.0%
- **Objetivo:** Verificar que 90% exacto no se clasifica como crítico
- **Pasos:**
  1. Curso con porcentaje_asistencia = 90.00 exacto
  2. Observar color en gráfico y tabla
- **Resultado esperado:**
  - Color índigo/alerta (rango 90–94%)
  - Panel "Resumen asistencia" muestra "En nivel de alerta"
  - Badge de fila: si promedio también ≥ 14, muestra "Atención"
- **PASS / FAIL:** ___

### TC-10-06: Integración de datos — promedios coinciden entre gráfico y tabla
- **Objetivo:** Verificar consistencia entre la visualización del gráfico y los datos de la tabla
- **Pasos:**
  1. Seleccionar un período con ≥ 2 cursos con calificaciones
  2. Leer el promedio de cada barra del gráfico
  3. Comparar con los valores de la columna "Promedio" en la tabla
- **Resultado esperado:**
  - Los valores en el gráfico y la tabla son idénticos para cada curso
  - El orden de las barras en el gráfico coincide con el orden de filas en la tabla
- **PASS / FAIL:** ___

---

## 13. Suite 11 — Integridad de Datos (Lógica de Negocio)

### TC-11-01: Promedio global = promedio de promedios por curso
- **Objetivo:** Verificar el cálculo del KPI de promedio global
- **Pasos:**
  1. Con datos conocidos: 2 cursos con promedio 18.0 y 14.0 respectivamente
  2. Observar KPI "Promedio global"
- **Resultado esperado:**
  - KPI muestra 16.0 (promedio aritmético de 18 + 14 / 2)
- **PASS / FAIL:** ___

### TC-11-02: Asistencia global = promedio de porcentajes de asistencia
- **Objetivo:** Verificar el cálculo de asistencia global
- **Pasos:**
  1. 2 cursos: asistencia 95% y 85% respectivamente
  2. Observar KPI "Asistencia global"
- **Resultado esperado:**
  - KPI muestra 90.0% (promedio de 95 + 85 / 2)
- **PASS / FAIL:** ___

### TC-11-03: Total aprobados + reprobados + en_curso ≤ total matrículas
- **Objetivo:** Verificar la coherencia en la suma de estudiantes
- **Pasos:**
  1. Con datos conocidos, observar los totales en el donut y KPIs
- **Resultado esperado:**
  - `total_aprobados + total_reprobados + total_en_curso` ≤ suma de `total_estudiantes` de todos los cursos
  - No hay estudiantes contados dos veces
- **PASS / FAIL:** ___

### TC-11-04: Tasa de aprobación + reprobación ≤ 100%
- **Objetivo:** Verificar que los porcentajes de la tabla no superan el 100%
- **Pasos:**
  1. Observar todas las filas de la tabla
  2. Sumar `tasa_aprobacion + tasa_reprobacion` para cada fila
- **Resultado esperado:**
  - Para cada fila: `tasa_aprobacion + tasa_reprobacion ≤ 100%`
  - La diferencia representa estudiantes sin calificaciones aún (en_curso)
- **PASS / FAIL:** ___

### TC-11-05: Filtro por inasistencia es consistente con los datos de asistencia
- **Objetivo:** Verificar que el umbral de inasistencia filtra correctamente
- **Pasos:**
  1. Aplicar filtro "≥ 10%" de inasistencia
  2. Observar los % de asistencia de los cursos resultantes
- **Resultado esperado:**
  - Todos los cursos mostrados tienen `porcentaje_asistencia ≤ 90%`
  - Los cursos con asistencia > 90% no aparecen
- **PASS / FAIL:** ___

---

## 14. Suite 12 — Responsividad y Adaptación de Pantalla

### TC-12-01: Layout en móvil (375px — iPhone SE)
- **Objetivo:** Verificar que el dashboard es usable en móvil
- **Pasos:**
  1. Abrir DevTools → responsive mode → 375px ancho
  2. Navegar por toda la página con filtros aplicados
- **Resultado esperado:**
  - Formulario de filtros ocupa ancho completo
  - KPIs en grid 2 columnas (`grid-cols-2`)
  - Gráficos reducen su tamaño pero siguen legibles
  - Tabla tiene scroll horizontal contenido
  - No hay elementos que se superpongan
  - Chips de filtros activos hacen wrap correctamente
- **PASS / FAIL:** ___

### TC-12-02: Layout en tablet (768px — iPad)
- **Objetivo:** Verificar el layout intermedio
- **Pasos:**
  1. Pantalla de 768px de ancho
  2. Navegar con datos completos
- **Resultado esperado:**
  - Dropdowns de filtros tienen `sm:max-w-sm`
  - Los sub-filtros del paso 3 están en 2 columnas (`sm:grid-cols-2`)
  - KPIs pueden estar en 2 o 4 columnas según breakpoint
- **PASS / FAIL:** ___

### TC-12-03: Layout en desktop (1280px+)
- **Objetivo:** Verificar el layout completo en pantalla grande
- **Pasos:**
  1. Resolución 1280px o más
  2. Navegar con datos completos
- **Resultado esperado:**
  - KPIs en 4 columnas (`lg:grid-cols-4`)
  - Gráficos de barras ocupan `lg:col-span-2` (2/3 del ancho)
  - Panel lateral (donut / resumen asistencia) ocupa 1/3
  - Tabla muestra todas las columnas sin scroll horizontal
- **PASS / FAIL:** ___

---

## 15. Suite 13 — UX y Accesibilidad Básica

### TC-13-01: Breadcrumb es funcional
- **Objetivo:** Verificar que el link del breadcrumb lleva al dashboard principal
- **Pasos:**
  1. Hacer clic en "Inicio" del breadcrumb
- **Resultado esperado:**
  - Redirige a la página de inicio/dashboard del usuario
  - No genera 404
- **PASS / FAIL:** ___

### TC-13-02: Labels asociados a sus inputs (accesibilidad)
- **Objetivo:** Verificar que cada `<label>` tiene su `for` correcto
- **Pasos:**
  1. Inspeccionar el HTML del formulario
  2. Verificar que `for="f-periodo"` → `id="f-periodo"` coinciden, igualmente para todos los demás
- **Resultado esperado:**
  - `label[for="f-periodo"]` → `select#f-periodo`
  - `label[for="f-paralelo"]` → `select#f-paralelo`
  - `label[for="f-asignatura"]` → `select#f-asignatura`
  - `label[for="f-inasistencia"]` → `select#f-inasistencia`
  - Al hacer clic en un label, el select correspondiente recibe el foco
- **PASS / FAIL:** ___

### TC-13-03: Título de página es correcto
- **Objetivo:** Verificar el `<title>` del documento
- **Pasos:**
  1. Observar la pestaña del navegador
- **Resultado esperado:**
  - Tab muestra "Dashboard de Rendimiento Académico" (o con el prefijo del sistema)
- **PASS / FAIL:** ___

### TC-13-04: Tooltip del gráfico no genera errores en consola
- **Objetivo:** Verificar que no hay errores de JavaScript al interactuar
- **Pasos:**
  1. Abrir DevTools → Console
  2. Hacer hover sobre cada gráfico
  3. Aplicar y cambiar filtros
- **Resultado esperado:**
  - Sin errores (`TypeError`, `ReferenceError`, etc.) en consola
  - Máximo: advertencias no críticas de libraries CDN
- **PASS / FAIL:** ___

---

## 15. Suite 14 — Gráfico de Línea: Tendencia por Evaluación

### TC-14-01: Sección oculta sin curso seleccionado
- **Objetivo:** Verificar que el gráfico de tendencia no aparece hasta seleccionar un curso
- **Pasos:**
  1. Autenticado como inspector
  2. Seleccionar un período sin elegir curso específico (paso 2 = "Todos los cursos del período")
  3. Hacer submit
- **Resultado esperado:**
  - La sección "Tendencia por evaluación" no es visible en la página
  - El canvas `chartTendencia` no está presente en el DOM visible
  - Las secciones de Calificaciones y Asistencia aparecen normalmente
- **PASS / FAIL:** ___

### TC-14-02: Gráfico aparece al seleccionar un curso — spinner durante fetch
- **Objetivo:** Verificar que al elegir un curso, el gráfico de tendencia aparece con feedback de carga
- **Pasos:**
  1. Con un período seleccionado, elegir un curso específico en el dropdown del paso 2 (sin hacer submit)
  2. Observar el área bajo la sección "Calificaciones" inmediatamente
- **Resultado esperado:**
  - La sección "Tendencia por evaluación" aparece (Alpine.js `x-show="paralelo"`)
  - Se muestra spinner animado con texto "Cargando tendencia…"
  - Tras unos instantes, el spinner desaparece y el canvas con el gráfico de línea es visible
  - **Nota:** Para observar el spinner usar DevTools → Network → throttling "Slow 3G"
- **PASS / FAIL:** ___

### TC-14-03: Gráfico de línea — estructura y escala correcta
- **Objetivo:** Verificar la anatomía visual del gráfico de tendencia
- **Pasos:**
  1. Seleccionar un curso que tenga ≥ 2 evaluaciones con calificaciones registradas
  2. Observar el gráfico de línea
- **Resultado esperado:**
  - Gráfico de tipo línea visible en el canvas `chartTendencia`
  - Un punto por cada tipo de evaluación con calificaciones (Parcial 1, Parcial 2, etc.)
  - Las evaluaciones están ordenadas cronológicamente (parcial1 → parcial2_10h → ... → examen_final)
  - Eje Y: escala 0–20 con marcas cada 4 pts
  - Línea horizontal punteada roja en y=16 (mínimo de aprobación)
  - El área bajo la línea tiene relleno violeta tenue
- **PASS / FAIL:** ___

### TC-14-04: Colores de puntos según promedio de la evaluación
- **Objetivo:** Verificar la codificación de color de los puntos de la línea
- **Pasos:**
  1. Seleccionar un curso con evaluaciones cuyos promedios sean: una ≥16, una entre 14–15, una <14
  2. Observar los colores de los puntos en el gráfico
- **Resultado esperado:**
  - Punto verde (`rgba(22,163,74,1)`): evaluación con promedio ≥ 16
  - Punto ámbar (`rgba(245,158,11,1)`): promedio entre 14 y 15.99
  - Punto rojo (`rgba(220,38,38,1)`): promedio < 14
  - Todos los puntos tienen borde blanco visible (para destacar sobre el relleno)
- **PASS / FAIL:** ___

### TC-14-05: Tooltip del gráfico de línea
- **Objetivo:** Verificar el contenido del tooltip al hacer hover sobre un punto
- **Pasos:**
  1. Con el gráfico de tendencia visible, pasar el cursor sobre cualquier punto
- **Resultado esperado:**
  - Tooltip muestra: ` Promedio: X.XX / 20`
  - Segunda línea: ` ✓ Sobre el mínimo` (si ≥ 16) o ` ✗ Bajo el mínimo` (si < 16)
  - El tooltip de la línea de aprobación (y=16) **no aparece** (está filtrado)
  - Sin errores en la consola del navegador
- **PASS / FAIL:** ___

### TC-14-06: Cambiar período limpia el gráfico de tendencia
- **Objetivo:** Verificar que al cambiar el período, el gráfico de tendencia desaparece
- **Pasos:**
  1. Seleccionar período A + curso específico → gráfico de tendencia visible
  2. Cambiar el período a B en el dropdown (sin hacer submit)
- **Resultado esperado:**
  - La sección "Tendencia por evaluación" desaparece (`x-show="paralelo"` → false)
  - El nombre del curso en el encabezado de la sección también desaparece
  - El gráfico anterior es destruido (no hay instancias de Chart.js huérfanas)
- **PASS / FAIL:** ___

### TC-14-07: Evaluación sin calificaciones — punto vacío en la línea
- **Objetivo:** Verificar el comportamiento cuando una evaluación no tiene calificaciones registradas
- **Pasos:**
  1. Seleccionar un curso que tenga una evaluación creada pero sin notas ingresadas (promedio = null)
  2. Observar el gráfico de tendencia
- **Resultado esperado:**
  - El label de esa evaluación aparece en el eje X
  - El punto correspondiente no se renderiza (valor `null`)
  - Si hay puntos a ambos lados, la línea los conecta saltando el null (`spanGaps: true`)
  - El tooltip en esa posición no muestra valor
- **PASS / FAIL:** ___

### TC-14-08: Nombre del curso en el encabezado de la sección
- **Objetivo:** Verificar que el nombre del curso seleccionado aparece en el título
- **Pasos:**
  1. Seleccionar curso "Paralelo A — Conducción Básica" en el dropdown
  2. Esperar a que el gráfico cargue
  3. Observar el encabezado de la sección "Tendencia por evaluación"
- **Resultado esperado:**
  - El encabezado muestra: `Tendencia por evaluación — Paralelo A — Conducción Básica`
  - El nombre corresponde exactamente al curso seleccionado
  - No se muestra si el gráfico aún está cargando
- **PASS / FAIL:** ___

### TC-14-09: Carga automática con `?paralelo=X` en la URL
- **Objetivo:** Verificar que el gráfico se inicializa automáticamente al cargar la página con un curso pre-seleccionado
- **Pasos:**
  1. Construir la URL con `?tipo_licencia=X&periodo=Y&paralelo=Z`
  2. Navegar directamente a esa URL (F5 / nueva pestaña)
- **Resultado esperado:**
  - Al cargar la página, el gráfico de tendencia aparece sin necesidad de interacción
  - El `init()` de Alpine.js llama a `fetchTendencia()` automáticamente
  - Los datos corresponden al curso Z
- **PASS / FAIL:** ___

### TC-14-10: Error de red — feedback de error
- **Objetivo:** Verificar el estado de error cuando el fetch al API falla
- **Pasos:**
  1. DevTools → Network → seleccionar la request al API de tendencia → "Block request URL"
  2. Seleccionar un curso en el dropdown
- **Resultado esperado:**
  - El spinner desaparece
  - Aparece el mensaje de error: "No se pudo cargar la tendencia. Intenta de nuevo."
  - No hay error sin manejar en la consola del navegador (el `catch` lo captura)
  - El resto de la página (otros gráficos) sigue funcionando normalmente
- **PASS / FAIL:** ___

---

## 16. Matriz de Trazabilidad — Criterios de Aceptación

| Criterio de Aceptación (HU23) | Casos de Prueba que lo validan |
|---|---|
| Solo inspector y secretaria acceden al dashboard | TC-01-01, TC-01-02, TC-01-03, TC-01-04, TC-01-05 |
| Parámetros GET maliciosos o inválidos son rechazados | TC-01-06, TC-01-07, TC-01-08, TC-01-09 |
| Período activo se pre-selecciona automáticamente | TC-02-01 |
| Estado vacío muestra mensaje claro sin período | TC-02-02, TC-02-03 |
| Filtro en cascada: Período → Curso → Materia/Inasistencia | TC-03-01 a TC-03-12 |
| Dropdown de Curso carga dinámicamente (Alpine.js) | TC-04-01, TC-04-02, TC-04-03 |
| Botón submit deshabilitado sin período | TC-04-05 |
| Spinner y loading al enviar formulario | TC-04-04 |
| KPIs reflejan correctamente los datos filtrados | TC-05-01 a TC-05-05, TC-11-01, TC-11-02 |
| Gráfico de barras de promedios con línea en 16 pts | TC-06-01 a TC-06-05 |
| Donut de distribución con porcentajes en leyenda | TC-07-01 a TC-07-04 |
| Gráfico de barras de asistencia con umbral en 90% | TC-08-01 a TC-08-04 |
| Tabla con mini barras de progreso y badge Estado | TC-09-01 a TC-09-09 |
| Texto "Sin notas" cuando no hay calificaciones | TC-09-07 |
| Chip "Sin estudiantes" en paralelos vacíos | TC-09-08 |
| Empty state cuando filtros no arrojan resultados | TC-10-01 |
| Barras de gráficos no excesivamente anchas con pocos datos | TC-06-03, TC-08-03, TC-10-02 |
| Integridad lógica de cálculos (promedios, tasas, sumas) | TC-11-01 a TC-11-05 |
| Diseño responsivo en móvil, tablet y desktop | TC-12-01, TC-12-02, TC-12-03 |
| Gráfico de línea de tendencia oculto sin curso seleccionado | TC-14-01 |
| Gráfico de tendencia carga dinámicamente vía API fetch | TC-14-02, TC-14-09 |
| Estructura y escala correcta del gráfico de línea | TC-14-03 |
| Colores de puntos según promedio por evaluación | TC-14-04 |
| Tooltip del gráfico de tendencia | TC-14-05 |
| Cambio de período destruye y oculta el gráfico de tendencia | TC-14-06 |
| Evaluación sin calificaciones — punto null en la línea | TC-14-07 |
| Nombre del curso en encabezado de sección | TC-14-08 |
| Estado de error cuando el fetch al API falla | TC-14-10 |

---

## 17. Registro de Ejecución

Completar durante la sesión de pruebas:

| ID | Descripción corta | Resultado | Observaciones | Fecha |
|---|---|---|---|---|
| TC-01-01 | Acceso inspector | | | |
| TC-01-02 | Acceso secretaria | | | |
| TC-01-03 | Bloqueo docente | | | |
| TC-01-04 | Bloqueo estudiante | | | |
| TC-01-05 | Sin auth → redirect | | | |
| TC-01-06 | periodo=abc redirect | | | |
| TC-01-07 | SQL en params | | | |
| TC-01-08 | inasistencia=99 ignorado | | | |
| TC-01-09 | Paralelo cross-period | | | |
| TC-02-01 | Período activo auto-carga | | | |
| TC-02-02 | Sin período activo en BD | | | |
| TC-02-03 | Panel vacío texto correcto | | | |
| TC-03-01 | Selector período lista todos | | | |
| TC-03-02 | Curso bloqueado sin período | | | |
| TC-03-03 | Cursos dinámicos Alpine.js | | | |
| TC-03-04 | Período sin cursos | | | |
| TC-03-05 | Cambio período limpia curso | | | |
| TC-03-06 | Step 3 deshabilitado sin período | | | |
| TC-03-07 | Step 3 habilita con período | | | |
| TC-03-08 | Filtro por materia | | | |
| TC-03-09 | Filtro por inasistencia 10% | | | |
| TC-03-10 | Filtro combinado | | | |
| TC-03-11 | Limpiar filtros | | | |
| TC-03-12 | Chips filtros activos | | | |
| TC-04-01 | JSON de paralelos válido | | | |
| TC-04-02 | Stepper colores dinámicos | | | |
| TC-04-03 | Curso persiste al recargar | | | |
| TC-04-04 | Spinner al enviar | | | |
| TC-04-05 | Botón disabled sin período | | | |
| TC-05-01 a TC-05-05 | KPI cards | | | |
| TC-06-01 a TC-06-05 | Gráfico promedios | | | |
| TC-07-01 a TC-07-04 | Donut distribución | | | |
| TC-08-01 a TC-08-04 | Gráfico asistencia | | | |
| TC-09-01 a TC-09-10 | Tabla detalle | | | |
| TC-10-01 a TC-10-06 | Casos borde | | | |
| TC-11-01 a TC-11-05 | Integridad datos | | | |
| TC-12-01 a TC-12-03 | Responsividad | | | |
| TC-13-01 a TC-13-04 | UX / Accesibilidad | | | |
| TC-14-01 | Tendencia oculta sin curso | | | |
| TC-14-02 | Spinner durante fetch tendencia | | | |
| TC-14-03 | Gráfico línea estructura y escala | | | |
| TC-14-04 | Colores de puntos por promedio | | | |
| TC-14-05 | Tooltip gráfico de tendencia | | | |
| TC-14-06 | Cambio período limpia tendencia | | | |
| TC-14-07 | Evaluación sin notas — punto null | | | |
| TC-14-08 | Nombre curso en encabezado | | | |
| TC-14-09 | Carga automática con ?paralelo=X | | | |
| TC-14-10 | Error de red — feedback error | | | |

---

## 18. Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| `JSON.parse()` falla si los nombres de cursos tienen caracteres especiales (`"`, `'`, `<`) | Baja | Alto | Verificar TC-04-01; los nombres pasan por `json.dumps()` de Python que escapa correctamente |
| El spinner no es visible en conexiones rápidas (localhost) | Alta | Bajo | Normal en dev; probar con throttling de red para demostrar |
| `widthratio` puede redondear % del donut incorrectamente | Media | Bajo | Suma puede ser 99% o 101% por redondeo entero; es esperado |
| `promedio_general == 0` puede ser válido (promedio real de 0) | Baja | Medio | La condición actual trata 0 como "Sin notas"; si un curso puede tener promedio real 0, revisar lógica |
| Paralelo con `docente = None` muestra "—" | Confirmado | Bajo | Implementado correctamente en `services.py` línea 681–685 |
| Alpine.js no carga si CDN falla | Muy baja | Alto | Sin Alpine, los dropdowns dinámicos y el spinner no funcionan. Los filtros de período/materia/inasistencia siguen funcionando (son `<select>` normales) |

---

*Documento generado para Sprint 4 — HU23 | Proyecto ECPPP*
