"""Production settings: secure defaults. Requires real environment variables."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# No SMTP in production, so the password-reset flow can't deliver its email and
# would just 500. Turn it off; config/urls.py then 404s the reset URLs.
PASSWORD_RESET_ENABLED = False

# Fail fast if the real secret key is not provided by the environment.
SECRET_KEY = env("SECRET_KEY")

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

# Additional hardening (HSTS, CSP, etc.) is layered on in the polishing stage.

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
