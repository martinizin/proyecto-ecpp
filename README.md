# ECPPP — Plataforma Académica

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=martinizin_proyecto-ecpp&metric=coverage)](https://sonarcloud.io/summary/new_code?id=martinizin_proyecto-ecpp)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=martinizin_proyecto-ecpp&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=martinizin_proyecto-ecpp)

Sistema de gestión académica para el control de calificaciones, asistencia y solicitudes estudiantiles.

## Requisitos previos

- Python 3.12.x
- PostgreSQL 18.x
- Git

## Instalación

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

# 4. Instalar dependencias (incluye linters y herramientas de test;
#    requirements.txt por sí solo instala únicamente lo que corre en producción)
pip install -r requirements-dev.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales locales de PostgreSQL
```

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | `tu-clave-secreta-aqui` |
| `DJANGO_DEBUG` | Modo debug | `True` |
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.development` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos (producción) | `example.com,www.example.com` |
| `DATABASE_NAME` | Nombre de la base de datos | `ecppp_db` |
| `DATABASE_USER` | Usuario de PostgreSQL | `ecppp_user` |
| `DATABASE_PASSWORD` | Contraseña de PostgreSQL | `tu-contrasena` |
| `DATABASE_HOST` | Host de PostgreSQL | `localhost` |
| `DATABASE_PORT` | Puerto de PostgreSQL | `5432` |

## Ejecución local

```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver
```

El servidor estará disponible en `http://localhost:8000`.
El panel de administración en `http://localhost:8000/admin/`.

## Pruebas

```bash
# Ejecutar pruebas
pytest

# Ejecutar pruebas con cobertura
coverage run -m pytest
coverage report

# Verificar umbral de cobertura (70%)
coverage report --fail-under=70

# Generar reporte HTML de cobertura
coverage html
# Abrir htmlcov/index.html en el navegador
```

## Linting y formato

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

1. `flake8 .` — verificación de estilo
2. `black --check .` — verificación de formato
3. `python manage.py migrate` — migraciones
4. `coverage run -m pytest` — pruebas con cobertura
5. `coverage report --fail-under=70` — umbral de cobertura

## Documentación

- [Manual de Arquitectura](docs/manuales/architecture-manual.md)
- [Manual de Base de Datos](docs/manuales/database-manual.md)
- [Manual de Usuario](docs/manuales/user-manual.md)
- [Guía de recursos de documentación](docs/manuales/assets/README.md)

## Estructura del proyecto

```
proyecto-ecpp/
├── config/                 # Configuración Django
│   ├── settings/
│   │   ├── base.py         # Settings compartidos
│   │   ├── development.py  # Settings de desarrollo
│   │   └── production.py   # Settings de producción
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                   # Aplicaciones (DDD)
│   ├── usuarios/           # Gestión de usuarios
│   ├── academico/          # Períodos, asignaturas, paralelos
│   ├── calificaciones/     # Evaluaciones
│   ├── asistencia/         # Control de asistencia
│   └── solicitudes/        # Solicitudes estudiantiles
├── templates/              # Plantillas HTML
├── static/                 # Archivos estáticos
├── tests/                  # Pruebas
├── docs/                   # Documentación
├── requirements.txt
├── pyproject.toml
└── manage.py
```

Cada aplicación sigue la arquitectura DDD con capas: `domain/`, `application/`, `infrastructure/`, `presentation/`.

## Contribución

1. Crear rama desde `develop`: `git checkout -b feature/mi-feature develop`
2. Implementar cambios siguiendo las convenciones del proyecto
3. Asegurar que `flake8 .` y `black --check .` pasen sin errores
4. Asegurar que `pytest` pase y cobertura >= 70%
5. Crear pull request hacia `develop`
