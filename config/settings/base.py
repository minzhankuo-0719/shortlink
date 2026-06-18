"""
Base settings shared by every environment.

`dev.py` and `prod.py` import everything from here and override only what differs.
Secrets and per-environment values are read from environment variables (the
12-factor approach) via `django-environ` — never hard-coded into the repo.
"""

from pathlib import Path

import environ

# Repo root. This file is config/settings/base.py, so three .parent hops:
#   base.py -> settings/ -> config/ -> <repo root>
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Environment variables --------------------------------------------------
# `env(...)` reads from the OS environment; the tuples below declare the type
# and a default so a missing variable fails loudly instead of silently.
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
# Load a local .env file if present (git-ignored). Real environment variables
# (and GCP Secret Manager in production) always take precedence over the file.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# --- Applications -----------------------------------------------------------
# Grouped so it is obvious which apps are Django's, which are third-party, and
# which are ours. Our apps live under the `apps/` package.
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS: list[str] = []
LOCAL_APPS = [
    "apps.core",
    "apps.shortener",
    "apps.analytics",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide templates live here; app templates are auto-discovered.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---------------------------------------------------------------
# Configured by a single DATABASE_URL (e.g. postgres://user:pass@host:5432/db).
# Defaults to local SQLite so the project runs with zero setup; production must
# supply a real DATABASE_URL (enforced in prod.py).
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# --- Password validation ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ---------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True  # Store timestamps in UTC, render in TIME_ZONE.

# --- Static files -----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # `collectstatic` target (served in prod)
STATICFILES_DIRS = [BASE_DIR / "static"]  # our source static files

# Use 64-bit integer primary keys by default.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth ---------------------------------------------------------------
# Built-in auth views (django.contrib.auth.urls) for Stage 1; Stage 2 swaps
# the login flow to django-allauth (Google/Facebook) without touching the
# shortener/analytics core logic.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "shortener:my_links"
