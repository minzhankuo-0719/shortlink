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
THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]
LOCAL_APPS = [
    "apps.accounts",
    "apps.core",
    "apps.shortener",
    "apps.analytics",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collectstatic's output straight from the container — no separate
    # CDN/bucket needed for a low-traffic app. Must sit right after security
    # middleware and before everything else, per WhiteNoise's own docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth needs to inspect/modify the request on every view, e.g. to
    # surface its messages and handle its account-related redirects.
    "allauth.account.middleware.AccountMiddleware",
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

# WhiteNoise's manifest storage hashes filenames for far-future cache headers
# and gzip/brotli-compresses them at collectstatic time, so prod serves
# static assets efficiently straight out of the container.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Use 64-bit integer primary keys by default.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth (django-allauth) ---------------------------------------------------
# Stage 1 used Django's built-in auth views; Stage 2 swaps the login flow to
# allauth (Google/Facebook) without touching shortener/analytics — both still
# just read `request.user`, set by whichever backend below authenticated them.
LOGIN_URL = "account_entrance"  # our email-first entrance, not allauth's login
LOGIN_REDIRECT_URL = "shortener:my_links"

AUTHENTICATION_BACKENDS = [
    # Needed for Django admin and the original username/password login.
    "django.contrib.auth.backends.ModelBackend",
    # allauth's own backend, used for the social (Google/Facebook) login flow.
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Accept either username or email on the login form — our Stage 1 accounts
# only have a username, but allauth-created social accounts get an email.
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
# No mail server configured yet, so don't require clicking a verification link.
ACCOUNT_EMAIL_VERIFICATION = "none"

# Account linking across providers by verified email. Without this, signing in
# with Google and later with Facebook under the *same* email creates two
# separate accounts (allauth's safe default). We turn it on because both of our
# providers (Google, Facebook) verify the email they hand us, so "same verified
# email == same person" is a claim we can trust: a social login whose verified
# email matches an existing account logs into that account, and AUTO_CONNECT
# links the new provider to it. Only safe with providers that verify email —
# see docs/adr/0009-email-first-auth.md.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True


def _oauth_app(client_id_var: str, secret_var: str) -> list[dict[str, str]]:
    """Build allauth's `APPS` list for one provider from env vars.

    Returns an empty list if either value is missing, so an unconfigured
    provider has *no* app at all (allauth's `get_providers` then correctly
    hides its login button) instead of a broken app with empty credentials.
    """
    client_id = env(client_id_var, default="")
    secret = env(secret_var, default="")
    if not client_id or not secret:
        return []
    return [{"client_id": client_id, "secret": secret, "key": ""}]


# Credentials come from environment variables (never hard-coded into the
# repo). See docs/adr/0004-social-login-credentials.md for why an
# unconfigured provider must end up with an empty APPS list, not one with
# blank values.
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": _oauth_app("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"),
        "SCOPE": ["profile", "email"],
        "OAUTH_PKCE_ENABLED": True,
    },
    "facebook": {
        "APPS": _oauth_app("FACEBOOK_OAUTH_CLIENT_ID", "FACEBOOK_OAUTH_CLIENT_SECRET"),
        "SCOPE": ["email", "public_profile"],
        "METHOD": "oauth2",
        # Facebook's provider hard-codes the email as unverified because its
        # Graph API exposes no reliable per-email "verified" signal (its
        # `verified` field is about the *account*, not the email). We opt in to
        # trusting it so that email-based account linking (see
        # SOCIALACCOUNT_EMAIL_AUTHENTICATION) also works in the Facebook
        # direction. Honoured via the adapter's is_email_verified() ->
        # cleanup_email_addresses() "force verified" step. See
        # docs/adr/0009-email-first-auth.md for the trust trade-off.
        "VERIFIED_EMAIL": True,
    },
}
