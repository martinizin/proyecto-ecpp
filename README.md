# ECPPP — Plataforma Academica

Sistema de gestion academica para el control de calificaciones, asistencia y solicitudes estudiantiles.

## Requisitos Previos

- Python 3.12.x
- PostgreSQL 18.x
- Git

## Instalacion

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd proyecto-ecpp

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales locales de PostgreSQL
```

## Variables de Entorno

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | `tu-clave-secreta-aqui` |
| `DJANGO_DEBUG` | Modo debug | `True` |
| `DJANGO_SETTINGS_MODULE` | Modulo de settings | `config.settings.development` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos (produccion) | `example.com,www.example.com` |
| `DATABASE_NAME` | Nombre de la base de datos | `ecppp_db` |
| `DATABASE_USER` | Usuario de PostgreSQL | `ecppp_user` |
| `DATABASE_PASSWORD` | Contrasena de PostgreSQL | `tu-contrasena` |
| `DATABASE_HOST` | Host de PostgreSQL | `localhost` |
| `DATABASE_PORT` | Puerto de PostgreSQL | `5432` |

## Ejecucion Local

```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver
```

El servidor estara disponible en `http://localhost:8000`.
El panel de administracion en `http://localhost:8000/admin/`.

## Tests

```bash
# Ejecutar tests
pytest

# Ejecutar tests con cobertura
coverage run -m pytest
coverage report

# Verificar umbral de cobertura (70%)
coverage report --fail-under=70

# Generar reporte HTML de cobertura
coverage html
# Abrir htmlcov/index.html en el navegador
```

## Linting y Formato

```bash
# Verificar estilo con flake8
flake8 .

# Verificar formato con black
black --check .

# Aplicar formato con black
black .
```

## Pipeline CI

El proyecto usa GitHub Actions (`.github/workflows/ci.yml`) que ejecuta en cada push y pull request:

1. `flake8 .` — verificacion de estilo
2. `black --check .` — verificacion de formato
3. `python manage.py migrate` — migraciones
4. `coverage run -m pytest` — tests con cobertura
5. `coverage report --fail-under=70` — umbral de cobertura

## Estructura del Proyecto

```
proyecto-ecpp/
├── config/                 # Configuracion Django
│   ├── settings/
│   │   ├── base.py         # Settings compartidos
│   │   ├── development.py  # Settings de desarrollo
│   │   └── production.py   # Settings de produccion
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                   # Aplicaciones (DDD)
│   ├── usuarios/           # Gestion de usuarios
│   ├── academico/          # Periodos, asignaturas, paralelos
│   ├── calificaciones/     # Evaluaciones
│   ├── asistencia/         # Control de asistencia
│   └── solicitudes/        # Solicitudes estudiantiles
├── templates/              # Templates HTML
├── static/                 # Archivos estaticos
├── tests/                  # Tests
├── docs/                   # Documentacion
├── requirements.txt
├── pyproject.toml
└── manage.py
```

Cada aplicacion sigue la arquitectura DDD con capas: `domain/`, `application/`, `infrastructure/`, `presentation/`.

## Contribucion

1. Crear rama desde `develop`: `git checkout -b feature/mi-feature develop`
2. Implementar cambios siguiendo las convenciones del proyecto
3. Asegurar que `flake8 .` y `black --check .` pasen sin errores
4. Asegurar que `pytest` pase y cobertura >= 70%
5. Crear pull request hacia `develop`
