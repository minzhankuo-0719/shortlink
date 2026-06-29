"""Production settings: secure defaults. Requires real environment variables."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# No SMTP in production, so the password-reset flow can't deliver its email and
# would just 500. Turn it off; config/urls.py then 404s the reset URLs.
PASSWORD_RESET_ENABLED = False

# Fail fast if the real secret key is not provided by the environment.
SECRET_KEY = env("SECRET_KEY")

# Require a real Redis in prod; without it CACHES would silently fall back to
# per-process LocMemCache (low hit rate, invalidation not shared across instances).
REDIS_URL = env("REDIS_URL")

# ALLOWED_HOSTS and DATABASE_URL must come from the environment (see base.py).

# Django's CSRF check compares the request's Origin header against this list
# for any "unsafe" (POST/PUT/...) request — required because ALLOWED_HOSTS
# alone doesn't satisfy it. Must include the scheme, e.g.
# "https://shortlink-xxxx-uc.a.run.app", and later the custom domain too.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Behind a TLS-terminating proxy (Cloud Run) -----------------------------
# Cloud Run terminates HTTPS and forwards the original scheme in this header,
# so Django can tell the request was secure and enforce HTTPS correctly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --- HSTS --------------------------------------------------------------------
# Tell browsers to only ever reach this site over HTTPS for the next year, so a
# network attacker can't downgrade a visitor to plain HTTP (SSL stripping).
# SECURE_SSL_REDIRECT above upgrades any stray HTTP request; HSTS makes the
# browser skip HTTP entirely on the next visit. Safe here because Cloud Run
# serves HTTPS only — there is no HTTP endpoint to lose.
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Don't expose the Django admin in production. The admin is a high-privilege,
# well-known endpoint (/admin/) that bots routinely scan and brute-force; with
# no admin route mounted there's nothing to attack. Set ENABLE_ADMIN=true in
# the environment to turn it back on temporarily when managing prod data.
# (CSP is intentionally deferred — see the security roadmap in the README.)
ENABLE_ADMIN = env.bool("ENABLE_ADMIN", default=False)

# --- Logging -----------------------------------------------------------------
# Django's own default LOGGING only sends to console when DEBUG=True; with
# DEBUG=False it instead tries to email ADMINS, which we haven't configured,
# so unhandled exceptions are silently dropped otherwise. Cloud Run captures
# anything written to stdout/stderr into Cloud Logging automatically, so a
# plain console handler is all that's needed to make 500s diagnosable.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
