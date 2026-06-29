# Deployment — Google Cloud Run

ShortLink runs on **Google Cloud Run** (container), with **Cloud SQL** (PostgreSQL) for data,
**Secret Manager** for secrets, **Artifact Registry** for the image, and **Upstash** (serverless Redis)
for the redirect cache.

> The commands below must be run from your own terminal — they create billable cloud resources and act
> on GCP / Google / Facebook accounts that only you can operate. Replace `PROJECT_ID`,
> `INSTANCE_CONNECTION_NAME`, etc. with your own values. Everything uses region `asia-east1` (Changhua, Taiwan).

## Project values used by this project (double-check before copy-pasting)

| Item | Value |
|---|---|
| PROJECT_ID | `shortlink-499808` (project number `642047376218`) |
| Region | `asia-east1` |
| Artifact Registry repo | `shortlink` (Docker, `asia-east1`) |
| Image path | `asia-east1-docker.pkg.dev/shortlink-499808/shortlink/web:latest` |
| Cloud Run service | `shortlink` |
| Service URL (the only one to share) | https://shortlink-ljrbbufbfq-de.a.run.app |
| Production Redis | Upstash serverless (secret `redis-url`) |

> ⚠️ Steps 0–10 below are for the **first deploy from scratch**. For a routine redeploy after a
> code-only change, use the next section — do **not** rerun steps 0–10.

## Redeploy (code-only change — no secret/env changes)

```bash
cd /path/to/shortlink          # ← must run inside the project dir (the one with the Dockerfile),
                               #    otherwise the build fails with "Dockerfile required"
git commit -am "<your message>"  # commit first so the live image maps back to a known commit

# 1) Build + push (note the project is shortlink-499808, NOT shortlink-demo)
gcloud builds submit --tag asia-east1-docker.pkg.dev/shortlink-499808/shortlink/web:latest .

# 2) Deploy by swapping only the image. Do NOT pass --set-secrets / --set-env-vars here:
#    those REPLACE the whole set, so omitting any one (e.g. REDIS_URL) wipes the live config —
#    and prod.py refuses to start without REDIS_URL. Passing only --image inherits all
#    secrets/env vars from the previous revision.
gcloud run deploy shortlink \
  --image=asia-east1-docker.pkg.dev/shortlink-499808/shortlink/web:latest \
  --region=asia-east1

# 3) Confirm the container came up (i.e. config was inherited)
curl -s https://shortlink-ljrbbufbfq-de.a.run.app/livez   # should return {"status": "ok"}
```

**Three traps already baked into the steps above:** ① not running inside the project dir →
`Dockerfile required`; ② wrong project in the image path (`shortlink-demo`) → push `denied`;
③ redeploying with `--set-secrets` while forgetting `REDIS_URL` → wipes the live Redis config and the
container won't start.

---

## First deploy from scratch

### 0. Install gcloud, create the project

```bash
# Install: https://cloud.google.com/sdk/docs/install
gcloud init                                                  # log in and pick a region
gcloud projects create shortlink-499808 --name="ShortLink"   # GCP project IDs are globally unique; pick your own if recreating
gcloud config set project shortlink-499808
# At https://console.cloud.google.com/billing link this project to your billing account ($300 free credit)
```

### 1. Enable the required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 2. Create the Artifact Registry repo (stores the Docker image)

```bash
gcloud artifacts repositories create shortlink \
  --repository-format=docker \
  --location=asia-east1
```

### 3. Create Cloud SQL (PostgreSQL, smallest tier)

```bash
gcloud sql instances create shortlink-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=asia-east1 \
  --storage-size=10GB \
  --storage-auto-increase

gcloud sql databases create shortlink --instance=shortlink-db
gcloud sql users create shortlink --instance=shortlink-db --password='<choose a strong password>'

# Note this value — you'll need it below (format: PROJECT_ID:REGION:INSTANCE_NAME)
gcloud sql instances describe shortlink-db --format='value(connectionName)'
```

### 4. Put secrets into Secret Manager

```bash
INSTANCE_CONNECTION_NAME="<value from the previous step>"

# Django SECRET_KEY: generate a random value
python -c "import secrets; print(secrets.token_urlsafe(50))" | \
  gcloud secrets create django-secret-key --data-file=-

# DATABASE_URL: connects over the unix socket Cloud Run mounts
echo -n "postgres://shortlink:<password from above>@/shortlink?host=/cloudsql/${INSTANCE_CONNECTION_NAME}" | \
  gcloud secrets create database-url --data-file=-

# Google / Facebook OAuth credentials (reuse the values from your .env that worked locally;
# you'll add the production redirect URI in step 8)
echo -n "<your GOOGLE_OAUTH_CLIENT_ID>"     | gcloud secrets create google-oauth-client-id     --data-file=-
echo -n "<your GOOGLE_OAUTH_CLIENT_SECRET>" | gcloud secrets create google-oauth-client-secret --data-file=-
echo -n "<your FACEBOOK_OAUTH_CLIENT_ID>"     | gcloud secrets create facebook-oauth-client-id     --data-file=-
echo -n "<your FACEBOOK_OAUTH_CLIENT_SECRET>" | gcloud secrets create facebook-oauth-client-secret --data-file=-

# REDIS_URL: production uses Upstash serverless Redis (no VPC connector needed). At
# https://upstash.com create a Redis (provider GCP, region close to asia-east1) and copy the
# rediss:// connection string. prod.py refuses to start without REDIS_URL, so this must exist.
printf '%s' '<paste the Upstash rediss:// connection string>' | gcloud secrets create redis-url --data-file=-
```

### 5. Grant the Cloud Run service account access

```bash
PROJECT_NUMBER=$(gcloud projects describe shortlink-499808 --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding shortlink-499808 \
  --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding shortlink-499808 \
  --member="serviceAccount:${SA}" --role="roles/cloudsql.client"
```

### 6. Build + push the image

```bash
gcloud builds submit --tag asia-east1-docker.pkg.dev/shortlink-499808/shortlink/web:latest .
```

### 7. Deploy to Cloud Run

```bash
gcloud run deploy shortlink \
  --image=asia-east1-docker.pkg.dev/shortlink-499808/shortlink/web:latest \
  --region=asia-east1 \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=2 \
  --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,REDIS_URL=redis-url:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,FACEBOOK_OAUTH_CLIENT_ID=facebook-oauth-client-id:latest,FACEBOOK_OAUTH_CLIENT_SECRET=facebook-oauth-client-secret:latest" \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.prod,ALLOWED_HOSTS=.run.app"
```

The deploy prints the service URL (e.g. `https://shortlink-xxxx-asia-east1.run.app`). Note it — the next
step needs it.

```bash
SERVICE_URL="<the URL printed above>"

# CSRF_TRUSTED_ORIGINS needs the real URL, so set it in a second update
gcloud run services update shortlink --region=asia-east1 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.prod,ALLOWED_HOSTS=.run.app,CSRF_TRUSTED_ORIGINS=${SERVICE_URL}"
```

`entrypoint.sh` runs `migrate` on every container start, so once the first deploy succeeds and the
container starts taking traffic, the database schema is already up to date — no separate manual migration
is needed.

### 8. Add the production OAuth redirect URI

Once you have `SERVICE_URL` (whether `*.run.app` or a custom domain you map later), go back to each
console and **add** a production redirect URI (keep the localhost one for local development):

- **Google Cloud Console** → APIs & Services → Credentials → your OAuth client → Authorized redirect URIs,
  add: `${SERVICE_URL}/accounts/google/login/callback/`
- **Facebook Developers** → your App → Facebook Login → Settings → Valid OAuth Redirect URIs, add:
  `${SERVICE_URL}/accounts/facebook/login/callback/`
  (Note: Facebook's HTTP exception for `localhost` does **not** apply to production domains — it must be
  HTTPS, which Cloud Run is by default.)

### 9. (Optional) Map a custom domain

```bash
gcloud run domain-mappings create --service=shortlink --domain=<your domain> --region=asia-east1
# It prints the DNS records to add at your domain registrar (usually a few CNAMEs); add them and wait for DNS to propagate
```

After mapping, remember to:
1. Add **another** redirect URI using the custom domain in the Google/Facebook consoles (same as step 8)
2. `gcloud run services update` to include the new domain in `CSRF_TRUSTED_ORIGINS` (and `ALLOWED_HOSTS` if needed)

### 10. Verify

- `curl https://<service URL>/livez` returns `{"status": "ok"}`
- In a browser, open the service URL → sign in with Google or Facebook → create a short link → visit it to
  confirm the redirect works → return to the dashboard and confirm the click and source IP are recorded

---

## Notes

- **Default domains:** Cloud Run serves both a new-format URL (`https://shortlink-ljrbbufbfq-de.a.run.app`)
  and an old-format one (`https://shortlink-642047376218.asia-east1.run.app`). The OAuth redirect URI and
  `CSRF_TRUSTED_ORIGINS` are only configured for the new format, so **always share the new-format URL** —
  the old one fails login with `redirect_uri_mismatch` (known behaviour, not a bug).
- **`/livez`, not `/healthz`:** Cloud Run reserves the exact path `/healthz` on the shared `*.run.app`
  domain for its own internal use, so external requests never reach the container — the health-check
  endpoint is named `/livez` instead.
- **Production logging:** Django's default `LOGGING` only writes to the console when `DEBUG=True`; with
  `DEBUG=False` and no `ADMINS` configured, exceptions would be silently dropped. `config/settings/prod.py`
  adds a console handler so 500s always land in Cloud Logging.
