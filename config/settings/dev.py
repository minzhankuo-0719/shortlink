"""Development settings: convenient and verbose. Never used in production."""

from .base import *  # noqa: F403

DEBUG = True

# Hosts allowed when developing locally (incl. 0.0.0.0 for Docker port mapping).
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# No SMTP server in local dev: print emails (e.g. allauth's password-reset link)
# to the console instead of connecting to localhost:25, which is refused and
# would 500 the password-reset page. The link is logged for you to click.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
