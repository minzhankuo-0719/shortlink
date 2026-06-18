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

# collectstatic only reads template/static sources and writes to STATIC_ROOT —
# it never touches the database — so a throwaway SECRET_KEY/DATABASE_URL here
# is safe and avoids depending on real secrets at build time.
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:///build.db \
    ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput \
    && rm -f build.db

RUN chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
