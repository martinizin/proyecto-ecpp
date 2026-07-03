# syntax=docker/dockerfile:1

# ---- Builder stage: install dependencies into an isolated venv ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build tools needed to compile any wheels that lack prebuilt binaries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage: slim image, non-root, no build tools ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# libpq5 is the only runtime system dependency (PostgreSQL client library).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user.
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

# Normalize line endings (guards against CRLF from Windows checkouts) then
# make the entrypoint executable. Runtime dirs owned by the app user;
# media/static persist via volumes.
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
