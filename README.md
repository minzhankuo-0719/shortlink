<img src="shortlink_github.png" align="left" width="150" hspace="24" vspace="8" alt="ShortLink logo"/>

*URL shortener · Google / Facebook social login · click analytics*

**Live:** https://shortlink-ljrbbufbfq-de.a.run.app

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092E20.svg)](https://www.djangoproject.com/)
[![uv](https://img.shields.io/badge/package%20manager-uv-DE5FE9)](https://docs.astral.sh/uv/)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/cache-Redis-DC382D.svg)](https://redis.io/)
[![Tailwind CSS](https://img.shields.io/badge/styles-Tailwind%20CSS-38BDF8.svg)](https://tailwindcss.com/)
[![Deploy: Cloud Run](https://img.shields.io/badge/deploy-Cloud%20Run-4285F4.svg)](https://shortlink-ljrbbufbfq-de.a.run.app)
[![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-D97757)](https://claude.com/claude-code)

<br clear="left"/>

---

## Contents

- [Project Overview](#project-overview) — what this project does
- [Demo & Verification](#demo--verification) — live URL + how to test it
- [Getting Started](#getting-started) — clone, install, run locally
- [Deployment](#deployment) — how it's hosted
- [Implementation](#implementation) — architecture + key decisions
- [Project Structure](#project-structure) — repo layout

---

## Project Overview

> ShortLink turns any long URL into a short, shareable code, then records analytics every time that code
> is visited. Authentication is social-login-first (Google / Facebook), and each user only ever sees and
> manages their own links.

| Feature | What it does |
|---|---|
| **Create short links** | Signed-in users shorten any URL; each gets a random 7-character base62 code |
| **Social login** | Sign in with **Google** or **Facebook** (OAuth via django-allauth); classic username / password also works |
| **Cross-provider account linking** | Signing in with Google and later Facebook under the same verified email lands you in the *same* account instead of a duplicate |
| **Fast redirects** | Visiting a short link issues a `302` redirect and records the visit; the lookup is cached in Redis, so the hot path usually skips the database |
| **Per-link click analytics** | For every link: total click count plus each visit's **source IP**, user agent, referer, and time |
| **Dashboard** | One page to create (in a modal), edit, and delete links; sort by newest / oldest / most-clicked / title; expand a link inline to see its click history; click a card to copy its short URL |
| **Dark mode** | Manual toggle, remembered across visits |

---

## Demo & Verification

### Demo

https://github.com/user-attachments/assets/951a009e-78dc-4662-a6f6-9d081969c89a

_End-to-end demo — sign in with Google, shorten a URL, visit it, and watch the click land on the dashboard with its source IP._

### Try it yourself

**Live URL:** https://shortlink-ljrbbufbfq-de.a.run.app

1. Open the live URL **in a real browser** (Safari / Chrome / Edge).
2. Sign in with **Google** (no allowlist — anyone can).
3. Create a short link from a long URL.
4. Open the short link → it redirects to the destination.
5. Back on the dashboard, expand the link to see the click you just made, with its source IP.

> ⚠️ **Use a real browser, not an in-app one.** Don't open the live URL from inside a messaging app's
> built-in browser (Messenger / Facebook / Instagram / LINE in-app WebView). Google's policy blocks
> OAuth inside in-app WebViews and returns `403 disallowed_useragent`. This is a Google policy, not a bug
> in this app — if you hit it, open the link in Safari or Chrome instead.

> 🔑 **Facebook login is limited to testers.** Meta now requires Business Verification to take an app
> fully live, which is overkill for a personal portfolio project, so the Facebook app stays in
> development mode and only accounts added as **testers** can log in with Facebook. To try Facebook
> login you'll need a free Facebook developer account and an invite — feel free to email me. **Google
> login has no such limit and works for anyone.**

---

## Getting Started

**Prerequisites:** Python ≥ 3.13, [uv](https://docs.astral.sh/uv/)
(install: `curl -LsSf https://astral.sh/uv/install.sh | sh`), and optionally Docker (only for the
prod-like stack below).

### 1. Setup

```bash
git clone https://github.com/minzhankuo-0719/shortlink.git
cd shortlink
uv sync                                    # installs runtime + dev deps (ruff, pre-commit)
cp .env.example .env                       # local defaults work out of the box
```

> Social login is optional locally: leave the OAuth variables in `.env` blank and those buttons simply
> don't appear — you can still use username / password. To test Google/Facebook locally, fill in the
> credentials (see [docs/deployment.md](docs/deployment.md) for where they come from). The database
> defaults to SQLite and Redis falls back to an in-memory cache, so no extra services are needed to run.

### 2. Run

```bash
uv run python manage.py migrate            # apply database migrations
uv run python manage.py createsuperuser    # create a local account to log in with
uv run python manage.py runserver          # start the dev server
```

Open <http://127.0.0.1:8000> for the app and <http://127.0.0.1:8000/livez> for the health check.

### 3. Dev tooling

```bash
uv run pre-commit install                  # run once after cloning (installs the git hook)
uv run ruff check . && uv run ruff format  # lint + format
```

### Optional — prod-like stack with Docker

Run the same container image Cloud Run uses (Gunicorn + WhiteNoise) against local Postgres and Redis, to
verify the deployment image before shipping:

```bash
docker compose up -d --build               # web + postgres + redis
docker compose exec web python manage.py createsuperuser
```

Open <http://localhost:8000>. `docker compose down -v` tears everything down, including volumes.

---

## Deployment

ShortLink is deployed on **Google Cloud Run**, backed by **Cloud SQL** (PostgreSQL), **Secret Manager**
(secrets), **Artifact Registry** (image), and **Upstash** serverless Redis (redirect cache). A single
multi-stage `Dockerfile` builds the container that runs both locally (via `docker compose`) and in the
cloud.

The full step-by-step runbook — first deploy from scratch *and* the code-only redeploy path — is in
**[docs/deployment.md](docs/deployment.md)**.

---

## Implementation

### Architecture

The Django project lives in `config/`; each feature is its own app under `apps/` (`core`, `accounts`,
`shortener`, `analytics`). Business logic sits in each app's `services.py` so views and models stay thin
and the logic is easy to test and reuse. Settings are layered (`base` / `dev` / `prod`), and every
secret or per-environment value is read from the environment (12-factor, via django-environ) rather than
hard-coded.

### Redirect hot path

```
Visitor → GET /<short_code>
   → resolve   Redis cache-aside (lookup in Redis; DB only on a miss)
   → record    Click row (source IP / user agent / referer / time)
   → 302       redirect to the destination URL
```

### Key decisions

- **Short codes — random base62, not sequential.** Codes are 7 random base62 characters from a CSPRNG
  (`secrets`), with a unique constraint and a retry on the rare collision. A sequential ID encoded to
  base62 would be trivially enumerable (and would leak how many links exist); hashing the URL would
  collide and couldn't give the same URL different codes per user.
- **302, not 301.** A `301 Moved Permanently` gets cached by the browser, so the *second* visit never
  reaches the server and the click goes unrecorded. A `302` guarantees every visit is counted.
- **Real client IP behind a proxy.** Cloud Run's front end appends the true client IP as the *last*
  `X-Forwarded-For` entry (verified against the live service), so the redirect reads the **last** entry —
  not the left-most, which a client can forge. Values a visitor injects land to the left and are ignored,
  and a malformed header is validated away to `NULL` instead of crashing the redirect. `REMOTE_ADDR` is
  only the no-proxy (local) fallback.
- **Cache-aside with signal-based invalidation.** Resolved short codes are cached in Redis (TTL 1h). A
  `post_save` / `post_delete` signal on `ShortLink` clears the cache entry, so creates, edits, and
  deletes take effect immediately — invalidation lives in one place and can't be forgotten at a call
  site.
- **Auth via django-allauth.** OAuth is delegated to a well-tested library rather than hand-rolled. On
  top of it sits the email-first entrance and cross-provider account linking by verified email.

### Database

Production uses **PostgreSQL** on Cloud SQL; locally it defaults to **SQLite** for zero-setup runs. The
choice of Postgres keeps dev/prod parity for anything SQL-specific. Indexes are deliberate: `short_code`
is unique (the redirect hot path), `(link, created_at)` is a composite index for time-ordered dashboard
queries, and `owner` is indexed for per-user link lists.

### Deployment shape

A multi-stage `Dockerfile` produces a small image running **Gunicorn** with **WhiteNoise** serving
hashed, compressed static files straight from the container. Secrets are injected from Secret Manager at
deploy time; nothing sensitive is baked into the image.

### Security

- **HTTPS only.** Behind Cloud Run's TLS proxy, HTTP is redirected to HTTPS, session/CSRF cookies are
  `Secure`, and **HSTS** (1-year `max-age`, `includeSubDomains`, `preload`) stops browsers from ever
  attempting HTTP again.
- **Admin disabled in production.** Django's `/admin/` is a high-privilege, well-known target for
  scanners and brute-force, so it isn't mounted in prod (env-gated by `ENABLE_ADMIN`) and returns 404
  there; it stays available locally for data management.
- **Un-spoofable client IP.** The source IP is read from the *last* `X-Forwarded-For` entry — the one
  Google's front end appends — so values a client injects (which land to its left) are ignored, and a
  malformed header is validated away to `NULL` rather than crashing the redirect.
- **Rate limiting.** Redirects and link creation are throttled per real client IP (django-ratelimit over
  Redis), returning `429 Too Many Requests` past the limit to blunt scraping and mass-creation abuse.
- **No third-party runtime scripts.** In production Tailwind is compiled to a small, purged stylesheet
  at image-build time (Tailwind standalone CLI → WhiteNoise) instead of being loaded from a CDN, so no
  external origin can execute script on the page. Dev keeps the zero-config CDN for fast iteration.

**Hardening roadmap:** add a Content-Security-Policy once the remaining inline scripts are refactored out.

---

## Project Structure

```
shortlink/
├── config/
│   ├── settings/             layered 12-factor settings
│   │   ├── base.py           shared config (apps, allauth, cache, DB)
│   │   ├── dev.py            local overrides
│   │   └── prod.py           secure production defaults (Cloud Run)
│   └── urls.py               root routes + email-first entrance wiring
├── apps/
│   ├── core/                 home page, /livez health check, /privacy
│   ├── accounts/             email-first sign-in entrance + custom allauth forms
│   ├── shortener/            ShortLink model, short-code service, cache-aside, signals
│   └── analytics/            Click model, client-IP parsing, record_click
├── templates/                base layout, account/, shortener/, allauth overrides
├── static/                   logo + static assets (served by WhiteNoise)
├── docs/
│   └── deployment.md         Cloud Run deployment runbook
├── Dockerfile                multi-stage build (Gunicorn + WhiteNoise)
├── docker-compose.yml        local prod-like stack (web + postgres + redis)
├── entrypoint.sh             runs migrate on container start
└── pyproject.toml / uv.lock  dependencies (managed by uv)
```
