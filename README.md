# ShortLink

縮網址服務（面試作品）。用 Django 建立，支援 Google / Facebook 登入，登入後可建立短網址、造訪短網址會被重導到原始連結，並可在儀表板看到自己每條短網址的點擊成效與來源 IP。

**服務網址**：https://shortlink-ljrbbufbfq-de.a.run.app

## Tech Stack

- **Python 3.13 + Django 5.2 (LTS)**，套件管理用 **uv**
- **PostgreSQL**（本機/Docker，正式環境用 Cloud SQL）
- **django-allauth**（Google / Facebook OAuth）
- **HTMX + Tailwind CSS**（模板導向、低 JS）
- **DRF**（REST API，分析儀表板用）
- **ruff**（lint + format）+ **pre-commit**

完整技術選型與決策見 [`CLAUDE.md`](CLAUDE.md) 與 [`docs/adr/`](docs/adr/)。

## Quickstart（本機開發）

```bash
uv sync                                    # 安裝依賴（含 dev 工具）
cp .env.example .env                       # 複製環境變數範例，依需要調整
uv run python manage.py migrate            # 套用資料庫 migration
uv run python manage.py createsuperuser    # 建立本機測試帳號（Stage 1 用內建登入）
uv run python manage.py runserver          # 啟動本機伺服器
```

打開 http://127.0.0.1:8000 看首頁，http://127.0.0.1:8000/livez 看健康檢查。

### 開發工具

```bash
uv run pre-commit install                 # 第一次 clone 後執行一次，裝 git commit hook
uv run ruff check . && uv run ruff format  # lint + 格式化
uv run pytest                              # 跑測試（Stage 5 後）
```

## 本機 Docker（prod-like 環境）

跑跟 Cloud Run 一樣的容器（gunicorn + WhiteNoise），搭配本機 Postgres/Redis，驗證部署用的 image 沒問題：

```bash
cp .env.example .env                       # 確保有 SECRET_KEY 等變數
docker compose up -d --build               # 起 web + db + redis
docker compose exec web python manage.py createsuperuser
```

打開 http://localhost:8000，登入後建立短網址、造訪、看儀表板點擊紀錄。`docker compose down -v` 清掉容器與資料。

## 部署到 Cloud Run

> 以下指令需要你自己在終端機執行（涉及建立雲端資源、計費、以及只有你本人能操作的 GCP/Facebook/Google
> 帳號）。指令裡的 `PROJECT_ID`、`INSTANCE_CONNECTION_NAME` 等請替換成你自己的值。Region 統一用
> `asia-east1`（台灣彰化）。

### 0. 安裝 gcloud、建立專案

```bash
# 安裝：https://cloud.google.com/sdk/docs/install
gcloud init                                            # 登入並選好 region
gcloud projects create shortlink-demo --name="ShortLink"
gcloud config set project shortlink-demo
# 到 https://console.cloud.google.com/billing 把這個專案連到你的帳單帳戶（有 $300 免費額度）
```

### 1. 啟用所需 API

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 2. 建立 Artifact Registry（存 Docker image）

```bash
gcloud artifacts repositories create shortlink \
  --repository-format=docker \
  --location=asia-east1
```

### 3. 建立 Cloud SQL（Postgres，最小規格）

```bash
gcloud sql instances create shortlink-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=asia-east1 \
  --storage-size=10GB \
  --storage-auto-increase

gcloud sql databases create shortlink --instance=shortlink-db
gcloud sql users create shortlink --instance=shortlink-db --password='<選一個強密碼>'

# 記下這個值，後面會用到（格式：PROJECT_ID:REGION:INSTANCE_NAME）
gcloud sql instances describe shortlink-db --format='value(connectionName)'
```

### 4. 把 secrets 放進 Secret Manager

```bash
INSTANCE_CONNECTION_NAME="<上一步拿到的值>"

# Django SECRET_KEY：產生一個隨機值
python -c "import secrets; print(secrets.token_urlsafe(50))" | \
  gcloud secrets create django-secret-key --data-file=-

# DATABASE_URL：走 Cloud Run 掛載的 unix socket（見 docs/adr/0005）
echo -n "postgres://shortlink:<上面設的密碼>@/shortlink?host=/cloudsql/${INSTANCE_CONNECTION_NAME}" | \
  gcloud secrets create database-url --data-file=-

# Google / Facebook OAuth 憑證（沿用你 .env 裡本機測試成功的那組值，之後第 8 步再補正式網域的 redirect URI）
echo -n "<你的 GOOGLE_OAUTH_CLIENT_ID>" | gcloud secrets create google-oauth-client-id --data-file=-
echo -n "<你的 GOOGLE_OAUTH_CLIENT_SECRET>" | gcloud secrets create google-oauth-client-secret --data-file=-
echo -n "<你的 FACEBOOK_OAUTH_CLIENT_ID>" | gcloud secrets create facebook-oauth-client-id --data-file=-
echo -n "<你的 FACEBOOK_OAUTH_CLIENT_SECRET>" | gcloud secrets create facebook-oauth-client-secret --data-file=-
```

### 5. 授權 Cloud Run 的服務帳號

```bash
PROJECT_NUMBER=$(gcloud projects describe shortlink-demo --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding shortlink-demo \
  --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding shortlink-demo \
  --member="serviceAccount:${SA}" --role="roles/cloudsql.client"
```

### 6. Build + push image

```bash
gcloud builds submit --tag asia-east1-docker.pkg.dev/shortlink-demo/shortlink/web:latest .
```

### 7. 部署 Cloud Run

```bash
gcloud run deploy shortlink \
  --image=asia-east1-docker.pkg.dev/shortlink-demo/shortlink/web:latest \
  --region=asia-east1 \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=2 \
  --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
  --set-secrets="SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,FACEBOOK_OAUTH_CLIENT_ID=facebook-oauth-client-id:latest,FACEBOOK_OAUTH_CLIENT_SECRET=facebook-oauth-client-secret:latest" \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.prod,ALLOWED_HOSTS=.run.app"
```

部署完會印出服務網址（例如 `https://shortlink-xxxx-asia-east1.run.app`）。先記下來，下一步要用。

```bash
SERVICE_URL="<上面印出的網址>"

# CSRF_TRUSTED_ORIGINS 需要知道實際網址才能設，所以分兩步 update
gcloud run services update shortlink --region=asia-east1 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.prod,ALLOWED_HOSTS=.run.app,CSRF_TRUSTED_ORIGINS=${SERVICE_URL}"
```

`entrypoint.sh` 會在每次容器啟動時自動跑 `migrate`（見 [`docs/adr/0005`](docs/adr/0005-cloud-run-deployment.md)
的取捨說明），所以第一次部署成功、容器開始接流量時，資料庫 schema 就已經是最新的，不需要另外手動跑 migration。

### 8. 補正式網域的 OAuth redirect URI

拿到 `SERVICE_URL` 後（不管是 `*.run.app` 還是你之後綁的自訂網域），回到後台**新增**一組正式環境用的
redirect URI（保留 localhost 那組，本機開發還會用到）：

- **Google Cloud Console** → API 和服務 → 憑證 → 你的 OAuth 用戶端 → Authorized redirect URIs 加：
  `${SERVICE_URL}/accounts/google/login/callback/`
- **Facebook Developers** → 你的 App → Facebook 登入 → 設定 → Valid OAuth Redirect URIs 加：
  `${SERVICE_URL}/accounts/facebook/login/callback/`
  （注意：Facebook 對 `localhost` 的 HTTP 例外**不適用**正式網域，必須是 HTTPS——Cloud Run 預設就是 HTTPS，符合需求）

### 9.（可選）綁自訂網域

```bash
gcloud run domain-mappings create --service=shortlink --domain=<你的網域> --region=asia-east1
# 它會印出要在你的網域 DNS 後台加的記錄（通常是幾筆 CNAME），加完等 DNS 生效即可
```

綁好後，記得：
1. 在 Google/Facebook 後台**再加一組**用自訂網域的 redirect URI（同第 8 步）
2. `gcloud run services update` 把 `CSRF_TRUSTED_ORIGINS`（和需要的話 `ALLOWED_HOSTS`）改成包含新網域

### 10. 驗收

- `curl https://<服務網址>/livez` 回 `{"status": "ok"}`
- 瀏覽器開服務網址 → 用 Google 或 Facebook 登入 → 建立短網址 → 造訪短網址確認重導成功 →
  回儀表板確認看到剛才那次造訪的點擊紀錄與來源 IP

## 專案進度與文件

- [`CLAUDE.md`](CLAUDE.md)：單一事實來源，含目前進度、Roadmap、架構與關鍵決策
- [`docs/adr/`](docs/adr/)：重要技術決策（Architecture Decision Records）
- [`docs/learning-log.md`](docs/learning-log.md)：逐檔解說與學習筆記
- [`docs/interview-qa.md`](docs/interview-qa.md)：面試考點整理
