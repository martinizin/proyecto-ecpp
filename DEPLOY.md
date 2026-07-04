# Guía de despliegue ECPPP — desde cero

Esta guía te lleva de **cero a producción**: un servidor con la plataforma ECPPP
corriendo sobre HTTPS, con base de datos, caché, backups automáticos y despliegue
continuo (CD). Está escrita para alguien que **nunca desplegó nada**. Seguí los
pasos en orden y no te saltees ninguno.

> Tiempo estimado la primera vez: **1 a 2 horas** (la mayoría es esperar
> descargas y la propagación del DNS).

---

## Qué vas a desplegar

Todo corre en **un solo servidor** con Docker. No necesitás instalar Python,
PostgreSQL ni Nginx a mano: Docker levanta cada servicio en su propio contenedor.

| Servicio | Contenedor | Para qué sirve | Público |
|----------|-----------|----------------|:-------:|
| **web** | Gunicorn + Django | La aplicación ECPPP | No |
| **db** | PostgreSQL 16 | Base de datos principal | No |
| **redis** | Redis 7 | Caché y rate-limiting (exportaciones HU27) | No |
| **caddy** | Caddy 2 | Puerta de entrada: HTTPS automático y reverse proxy | **Sí (80/443)** |

```
Internet ──> Caddy (443, HTTPS) ──> web (Gunicorn) ──> db (PostgreSQL)
                  │                        └────────> redis (caché)
                  └── sirve /media/ desde un volumen persistente
```

**Idea clave:** solo Caddy está expuesto a internet. `db` y `redis` viven en una
red interna privada y nadie los alcanza desde afuera. Los datos (base de datos y
archivos subidos) viven en **volúmenes** que sobreviven a los redeploys.

---

## Ruta rápida (el mapa completo)

1. Crear un servidor (Oracle Cloud gratis, o Hetzner ~€4/mes).
2. Abrir los puertos 80 y 443.
3. Instalar Docker en el servidor.
4. Clonar el repositorio en el servidor.
5. Crear el archivo `.env` con tus claves y contraseñas.
6. Apuntar tu dominio (o un subdominio gratis) al servidor.
7. `docker compose up -d` → primer despliegue.
8. Crear el usuario administrador.
9. Cargar los secrets en GitHub → los próximos deploys son automáticos.
10. Activar los backups automáticos (cron).

Cada paso está detallado abajo.

---

## Requisitos previos (antes de empezar)

- [ ] Una **cuenta de GitHub** con acceso a este repositorio (`martinizin/proyecto-ecpp`).
- [ ] Una **tarjeta de crédito/débito** (Oracle y Hetzner la piden para verificar; Oracle no cobra en el tier gratis).
- [ ] Una **API key de OpenAI** (para el copiloto — https://platform.openai.com/api-keys).
- [ ] Credenciales **SMTP** para enviar emails (Gmail, Brevo, Mailgun, o el correo institucional).
- [ ] Un **dominio** (opcional; si no tenés, usamos DuckDNS gratis en el Paso 6).
- [ ] En tu PC: una terminal con **SSH** (en Windows: PowerShell o Git Bash ya lo traen).

---

## Paso 1 — Crear el servidor

Elegí **una** opción. Las dos usan exactamente el mismo `docker-compose.yml`.

### Opción A (recomendada, gratis): Oracle Cloud Always Free

1. Registrate en https://www.oracle.com/cloud/free/ (tier "Always Free").
2. En la consola: **Compute → Instances → Create Instance**.
3. Configurá:
   - **Image:** Canonical Ubuntu 22.04.
   - **Shape:** `VM.Standard.A1.Flex` (ARM) — poné **2 OCPU / 12 GB** (gratis para siempre).
   - **SSH keys:** subí tu clave pública, o generá una y **guardá la privada** (la vas a necesitar).
4. Creá la instancia y anotá su **IP pública**.

> ⚠️ **Gotcha de Oracle (importante):** Oracle bloquea los puertos por defecto en
> DOS lugares. Tenés que abrir el 80 y el 443 en ambos:
>
> **a) En la consola** (red virtual): VCN → Security List → Add Ingress Rules →
> agregá `0.0.0.0/0` TCP puerto `80` y otra para el `443`.
>
> **b) En el servidor** (firewall interno de la imagen Ubuntu de Oracle):
> ```sh
> sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
> sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
> sudo netfilter-persistent save
> ```
> Si te salteás esto, el sitio "no carga" aunque todo lo demás esté bien.

### Opción B (pago, ~€4-8/mes, cero fricción): Hetzner Cloud

1. Registrate en https://www.hetzner.com/cloud y entrá a la Hetzner Cloud Console.
2. **Add Server** y configurá:
   - **Location:** **Ashburn, VA (US East)** — es el datacenter de Hetzner más
     cercano a Ecuador (mejor latencia que Alemania/Finlandia).
   - **Image:** Ubuntu 22.04.
   - **Type:** familia **CPX** (AMD/x86 — la que hay en US).
     - `CPX21` (3 vCPU / 4 GB) → recomendado, cómodo para el stack (~€8/mes).
     - `CPX11` (2 vCPU / 2 GB) → mínimo viable si querés gastar menos (~€4/mes).
   - **SSH keys:** subí tu clave pública (o generá una y guardá la privada).
   - **Firewalls:** creá uno que permita entrada TCP en `22`, `80` y `443`.
3. **Create & Buy now**. Anotá la **IP pública** que te asigna.

> **Importante (arquitectura):** la familia CPX es **x86/amd64**. El pipeline de
> CD construye la imagen multi-arquitectura (amd64 + arm64), así que corre en
> Hetzner CPX sin cambios. El usuario SSH por defecto en Hetzner es `root`.

### Conectarte al servidor

```sh
ssh ubuntu@<IP_DEL_SERVIDOR>      # Oracle usa el usuario "ubuntu"
# En Hetzner el usuario suele ser "root"
```

---

## Paso 2 — Instalar Docker en el servidor

Una sola línea instala Docker + Compose:

```sh
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Cerrá sesión (`exit`) y volvé a entrar por SSH para que el cambio de grupo tome
efecto. Verificá:

```sh
docker --version
docker compose version
```

---

## Paso 3 — Traer el código al servidor

```sh
git clone https://github.com/martinizin/proyecto-ecpp.git
cd proyecto-ecpp
git checkout develop
```

> El directorio se llama `proyecto-ecpp`. Ese nombre importa: los volúmenes de
> Docker se prefijan con él (ej. `proyecto-ecpp_media`).

---

## Paso 4 — Crear el archivo `.env` (el corazón de la config)

Todas las claves, contraseñas y ajustes viven en un archivo `.env` que **nunca se
sube a GitHub** (ya está en `.gitignore`). Hay una plantilla lista en el repo:

```sh
cp deploy/env.production.example .env
nano .env
```

La plantilla (también reproducida acá abajo) trae **completá los valores marcados**:

```env
# --- Django ---
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=PEGAR_CLAVE_GENERADA_ABAJO
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ecppp.edu.ec,www.ecppp.edu.ec
DJANGO_DOMAIN=ecppp.edu.ec
DJANGO_COLLECTSTATIC=1

# --- Base de datos (PostgreSQL) ---
# NO pongas DATABASE_HOST ni DATABASE_PORT: el compose los fija a db:5432.
DATABASE_NAME=ecppp
DATABASE_USER=ecppp
DATABASE_PASSWORD=PONER_UNA_CONTRASEÑA_FUERTE

# --- Caché (Redis) ---
REDIS_URL=redis://redis:6379/0

# --- OpenAI (copiloto) ---
OPENAI_API_KEY=sk-REEMPLAZAR_CON_TU_KEY
COPILOT_MODEL=gpt-4o-mini

# --- Email (SMTP) --- (reemplazá example.com por tu proveedor real)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=usuario@example.com
EMAIL_HOST_PASSWORD=REEMPLAZAR_CON_TU_PASSWORD_SMTP
DEFAULT_FROM_EMAIL=no-reply@example.com

# --- Gunicorn (opcional) ---
GUNICORN_WORKERS=3
```

Guardá con `Ctrl+O`, `Enter`, `Ctrl+X`.

### Generar la `DJANGO_SECRET_KEY`

Debe ser larga y aleatoria. Generala así (en tu PC o en el servidor):

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copiá el resultado en `DJANGO_SECRET_KEY`.

### Referencia rápida de variables

| Variable | Obligatoria | Qué es |
|----------|:-----------:|--------|
| `DJANGO_SECRET_KEY` | ✅ | Clave criptográfica de Django. Larga y secreta. |
| `DJANGO_ALLOWED_HOSTS` | ✅ | Dominios/IP permitidos, separados por coma. |
| `DJANGO_DOMAIN` | ✅ | Dominio que Caddy usa para pedir el certificado HTTPS. |
| `DJANGO_COLLECTSTATIC` | ✅ | `1` en producción (junta los archivos estáticos). |
| `DATABASE_PASSWORD` | ✅ | Contraseña de PostgreSQL. Fuerte. |
| `REDIS_URL` | ✅ | Conexión a Redis (dejá el valor de la plantilla). |
| `OPENAI_API_KEY` | ✅* | Necesaria para el copiloto. |
| `EMAIL_*` | ✅* | Necesarias para notificaciones por email. |
| `DATABASE_NAME` / `DATABASE_USER` | — | Default `ecppp`. |
| `GUNICORN_WORKERS` | — | Default `3`. |

\* Obligatoria si usás esa funcionalidad.

---

## Paso 5 — Apuntar el dominio al servidor (DNS)

Caddy saca el certificado HTTPS **solo** cuando el dominio ya apunta al servidor.

### Si tenés dominio propio (ej. `ecppp.edu.ec`)

En el panel de tu proveedor de DNS, creá:

| Tipo | Nombre | Valor |
|------|--------|-------|
| A | `@` (o `ecppp.edu.ec`) | `<IP_DEL_SERVIDOR>` |
| A | `www` | `<IP_DEL_SERVIDOR>` |

La propagación puede tardar de minutos a unas horas. Verificá con
`nslookup ecppp.edu.ec`.

### Si NO tenés dominio (gratis, para la defensa): DuckDNS

1. Entrá a https://www.duckdns.org, logueate y creá un subdominio, ej. `ecppp`.
2. Poné la IP de tu servidor en el campo "current ip" → **update**.
3. Tu URL será `ecppp.duckdns.org`. Usá ese valor en `DJANGO_DOMAIN` y
   `DJANGO_ALLOWED_HOSTS` del `.env`.

---

## Paso 6 — Primer despliegue

Desde el directorio `proyecto-ecpp` en el servidor:

```sh
docker compose up -d --build
```

Esto construye la imagen, levanta los 4 servicios, corre las migraciones y junta
los estáticos. Mirá el progreso:

```sh
docker compose logs -f web
```

Cuando veas `Listening at: http://0.0.0.0:8000`, está arriba. Cortá con `Ctrl+C`
(solo corta el log, no los contenedores).

### Crear el usuario administrador

```sh
docker compose exec web python manage.py createsuperuser
```

Seguí las preguntas (email, contraseña). Con este usuario entrás al `/admin/`.

### (Opcional) Cargar datos de demostración

```sh
docker compose exec web python manage.py seed_sprint4
```

### Verificar

Abrí en el navegador `https://TU_DOMINIO/health/`. Deberías ver:

```json
{"status": "ok", "db": true, "cache": true}
```

Y `https://TU_DOMINIO/` te lleva al login. ✅

> La **primera** carga puede tardar ~30 segundos mientras Caddy obtiene el
> certificado de Let's Encrypt. Es normal.

---

## Paso 7 — HTTPS (ya está, automático)

No hay nada que configurar. Caddy detecta `DJANGO_DOMAIN`, pide el certificado a
Let's Encrypt y renueva solo. Requiere que el **puerto 80 esté abierto** (por eso
el Paso 1). Si el certificado no sale, revisá el Troubleshooting.

---

## Paso 8 — Despliegue continuo (CD): deploys automáticos

A partir de acá, **cada vez que mergees a `develop`**, GitHub construye la imagen y
la despliega solo en el servidor. Para habilitarlo, cargá 4 secrets en GitHub.

En el repo: **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP del servidor. **Cambiar de Oracle a Hetzner = cambiar solo este valor.** |
| `SSH_USER` | Usuario SSH (`ubuntu` en Oracle, `root` en Hetzner). |
| `SSH_KEY` | Contenido **completo** de tu clave SSH **privada**. |
| `DEPLOY_PATH` | Ruta al proyecto en el servidor, ej. `/home/ubuntu/proyecto-ecpp`. |

El registro de imágenes (GHCR) lo maneja el `GITHUB_TOKEN` incorporado — no hace
falta otro token.

**Cómo probarlo:** hacé un cambio menor, mergealo a `develop`, y mirá la pestaña
**Actions**. El workflow `CD` construye, publica y despliega. En el servidor,
`docker compose ps` mostrará el contenedor `web` recién reiniciado.

> El primer deploy manual (Paso 6) es necesario porque el `.env` y el código tienen
> que estar en el servidor antes de que el CD pueda actualizarlos.

---

## Paso 9 — Backups automáticos

Los scripts ya están en el repo. Primero preparate el directorio de backups:

```sh
sudo mkdir -p /var/backups/ecppp
sudo chown $USER /var/backups/ecppp
chmod +x scripts/*.sh
```

Editá el crontab:

```sh
crontab -e
```

Agregá estas líneas (ajustá la ruta si clonaste en otro lado):

```cron
# Backup de base de datos cada 6 horas
0 */6  * * * cd /home/ubuntu/proyecto-ecpp && ./scripts/backup_db.sh    >> /var/log/ecppp-backup.log 2>&1
# Backup de archivos (media) cada 12 horas
0 */12 * * * cd /home/ubuntu/proyecto-ecpp && ./scripts/backup_media.sh >> /var/log/ecppp-backup.log 2>&1
```

Los backups van a `/var/backups/ecppp/` con **retención de 30 días** (los viejos se
borran solos). Probalos a mano una vez:

```sh
./scripts/backup_db.sh
./scripts/backup_media.sh
```

**Restaurar:** el procedimiento completo está en `scripts/restore.md`.

---

## Paso 10 — Smoke test post-deploy

Verificá que todo lo esencial responde:

```sh
BASE_URL=https://TU_DOMINIO ./scripts/smoke_e2e.sh
```

Chequea el health, la página de login y el gate de autenticación. Debe terminar
en `SMOKE PASS`.

---

## Operación del día a día

| Necesito… | Comando |
|-----------|---------|
| Actualizar la app | Mergeá a `develop` (el CD lo hace solo). Manual: `git pull && docker compose up -d --build` |
| Ver logs de la app | `docker compose logs -f web` |
| Ver logs de Caddy (HTTPS) | `docker compose logs -f caddy` |
| Estado de los servicios | `docker compose ps` |
| Reiniciar todo | `docker compose restart` |
| Entrar a la app (shell Django) | `docker compose exec web python manage.py shell` |
| Backup manual ya | `./scripts/backup_db.sh && ./scripts/backup_media.sh` |

### Rollback (volver a una versión anterior)

Cada deploy usa una etiqueta de imagen inmutable (el commit SHA). Para volver atrás:

```sh
cd /home/ubuntu/proyecto-ecpp
echo "ECPPP_IMAGE=ghcr.io/martinizin/proyecto-ecpp:<SHA_ANTERIOR>" > .env.image
docker compose --env-file .env --env-file .env.image up -d
```

El `<SHA_ANTERIOR>` lo encontrás en la pestaña Actions o en el historial de commits.

---

## Troubleshooting (problemas comunes)

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| El sitio "no carga" en el navegador | Puertos 80/443 cerrados (Oracle) | Abrí los puertos en la Security List **y** con `iptables` (Paso 1). |
| HTTPS no funciona / certificado inválido | El DNS todavía no apunta al servidor, o el puerto 80 está cerrado | Verificá `nslookup TU_DOMINIO` y que el 80 esté abierto. Esperá unos minutos. |
| `502 Bad Gateway` | El contenedor `web` no arrancó | `docker compose logs web` para ver el error (suele ser una var faltante en `.env`). |
| `password authentication failed` | `.env` cambiado después de crear el volumen de DB | El volumen guarda las credenciales originales. Para empezar limpio: `docker compose down -v` (⚠️ borra la DB local) y volvé a subir. |
| Estáticos (CSS) no cargan | Faltó `DJANGO_COLLECTSTATIC=1` | Agregalo al `.env` y `docker compose up -d`. |
| El CD falla en el paso "Deploy over SSH" | Faltan secrets o el servidor no está listo | Cargá los 4 secrets (Paso 8) y confirmá que podés entrar por SSH manualmente. |
| Backups vacíos | El contenedor `db` no estaba corriendo | El script falla a propósito si el dump queda vacío. Levantá el stack y reintentá. |

---

## Checklist final

- [ ] Servidor creado, puertos 80/443 abiertos (Oracle: en ambos lugares).
- [ ] Docker instalado (`docker compose version` responde).
- [ ] Repo clonado en `develop`.
- [ ] `.env` completo con `DJANGO_SECRET_KEY`, `DATABASE_PASSWORD`, `OPENAI_API_KEY`, `EMAIL_*`.
- [ ] Dominio (o DuckDNS) apuntando a la IP del servidor.
- [ ] `docker compose up -d` levantó los 4 servicios.
- [ ] `https://TU_DOMINIO/health/` responde `{"status":"ok",...}`.
- [ ] Usuario administrador creado.
- [ ] 4 secrets cargados en GitHub (CD funcionando).
- [ ] Cron de backups activo (`crontab -l` los muestra).
- [ ] `smoke_e2e.sh` termina en `SMOKE PASS`.

---

## Referencias

- `deploy/README.md` — referencia técnica rápida (variables, CD, cron, rollback).
- `scripts/restore.md` — cómo restaurar un backup.
- `docker-compose.yml` — definición de los 4 servicios.
- `.github/workflows/cd.yml` — el pipeline de despliegue continuo.
- `docs/manuales/architecture-manual.md` — arquitectura del sistema (HU29).
