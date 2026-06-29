# syntax=docker/dockerfile:1

# --- builder ------------------------------------------------------------
# Resolves and installs dependencies into a venv using uv (same tool/lock
# file as local dev), kept in its own stage so build tools never ship in the
# final image.
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./
# --no-install-project: dependencies only, the project itself has no code
# to install (it's a Django project run in place, not a packaged library).
RUN uv sync --frozen --no-dev --no-install-project

# --- tailwind -------------------------------------------------------------
# Compiles the production stylesheet with Tailwind's standalone CLI (a single
# binary, no Node toolchain). It scans the templates and emits a small, purged
# CSS file, so prod serves its own stylesheet instead of the dev-only Play CDN.
FROM debian:bookworm-slim AS tailwind
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG TAILWIND_VERSION=v3.4.19
RUN curl -fsSL -o /usr/local/bin/tailwindcss \
      "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64" \
    && chmod +x /usr/local/bin/tailwindcss
COPY tailwind.config.js ./
COPY tailwind/input.css ./tailwind/input.css
COPY templates ./templates
RUN tailwindcss -i ./tailwind/input.css -o ./static/css/app.css --minify

# --- runtime --------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Cloud SQL's unix-socket connection (see docs/adr/0005) needs this directory
# to exist as a mount point; harmless when running outside Cloud Run too.
RUN mkdir -p /cloudsql

RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

COPY --from=builder /app/.venv /app/.venv
COPY . .

# Bring in the compiled Tailwind stylesheet (built in the tailwind stage) so
# collectstatic below picks it up and WhiteNoise serves it with a hashed name.
COPY --from=tailwind /app/static/css/app.css ./static/css/app.css

# collectstatic only reads template/static sources and writes to STATIC_ROOT —
# it never touches the database or Redis — so throwaway placeholder values here
# are safe and avoid depending on real secrets at build time.
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:///build.db \
    ALLOWED_HOSTS=localhost \
    REDIS_URL=redis://placeholder:6379 \
    python manage.py collectstatic --noinput \
    && rm -f build.db

RUN chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
