# ADR 0005 — Cloud Run 部署方式：Dockerfile、靜態檔、資料庫連線、Secrets、Migration

## 決策

1. **Cloud SQL 連線用 Cloud Run 內建的 unix socket，不額外裝 Cloud SQL Python Connector 套件**：
   部署時用 `gcloud run deploy --add-cloudsql-instances <INSTANCE_CONNECTION_NAME>`，Cloud Run 會
   把連線 socket 掛在 `/cloudsql/<INSTANCE_CONNECTION_NAME>`；`DATABASE_URL` 直接指向這個路徑
   （`postgres://user:pass@/dbname?host=/cloudsql/...`），`django-environ` 會把 `host` 查詢參數
   原樣放進 `DATABASES["default"]["OPTIONS"]`，psycopg 照一般 unix socket 連線處理。
2. **靜態檔用 WhiteNoise，不開額外的 GCS bucket/CDN**：`collectstatic` 在 Docker build 時跑、
   用 `CompressedManifestStaticFilesStorage` 產生帶 hash 檔名與 gzip/brotli 壓縮的檔案，容器內直接服務。
3. **所有 secrets（`SECRET_KEY`、`DATABASE_URL`、OAuth 憑證）放 Secret Manager，用
   `gcloud run deploy --set-secrets` 注入成環境變數**，不寫死在 Dockerfile/git。
4. **migration 在容器啟動時的 `entrypoint.sh` 跑（`migrate --noinput` 後才 exec gunicorn）**。

## 為什麼

1. **Cloud SQL unix socket 而非 Python Connector**：Cloud Run 原生支援這條路徑，不需要在
   `requirements`/`pyproject.toml` 多裝一個 `cloud-sql-python-connector` 套件、也不用在程式碼裡
   額外寫一段「用 connector 取得連線」的邏輯。對外部依賴更少、設定更貼近一般 `DATABASE_URL`
   12-factor 模式（見 `config/settings/base.py` 原本就有的 `env.db()`），跟現有架構一致。
2. **WhiteNoise 而非 GCS/CDN**：這個服務流量小（面試作品 demo 等級），多開一個 bucket + 設定
   CORS/快取規則的維運成本，不值得換來的效能差異。等真的需要更高流量再評估換掉（CLAUDE.md
   Stage 8 打磨清單可以再討論）。
3. **Secret Manager 而非把憑證寫進環境變數/`gcloud run deploy --set-env-vars`**：純環境變數會
   留在 Cloud Run revision 設定與 `gcloud run services describe` 的輸出裡，任何有專案唸權限的人
   都看得到明文；Secret Manager 有自己的存取控制（`roles/secretmanager.secretAccessor`）與版本管理，
   也跟 [`docs/adr/0004-social-login-credentials.md`](0004-social-login-credentials.md) 「OAuth 憑證
   走環境變數、不進 git」的精神一致——只是 prod 環境的「環境變數來源」換成 Secret Manager 而不是
   `.env` 檔。
4. **on-boot migrate 的取捨**：把 `migrate` 放進 `entrypoint.sh`、每次容器啟動都跑，最大的風險是
   多個 instance 同時冷啟動時對同一個資料庫搶著跑 migration（理論上可能互相鎖等待或極端情況下
   衝突）。對這個專案目前的規模（低流量、`--max-instances` 設很小、單一 revision 的面試作品）
   這個風險可以接受，換來的是「不用再多開一個 Cloud Run Job 跑 migration、部署流程少一步」的簡單性。
   如果之後流量成長到需要多 instance 常駐，正確做法是把 migration 抽成獨立的
   [Cloud Run Job](https://cloud.google.com/run/docs/create-jobs)，在部署流程裡先跑 Job、
   等它成功才讓新 revision 開始收流量。

## 影響

- 部署只需要一個 Docker image（`Dockerfile`），不需要分開維護「跑 migration 用」跟「serve 用」
  兩份程式碼或兩個 image。
- 之後要綁自訂網域時，只要重新 `gcloud run services update --set-env-vars CSRF_TRUSTED_ORIGINS=...`
  即可，不用改程式碼或重新 build image（見 `config/settings/prod.py` 的 `CSRF_TRUSTED_ORIGINS`）。
- 如果之後做 Stage 5 的 CI/CD，這個 Dockerfile 可以直接被 GitHub Actions 拿去 build + push，
  不需要為 CI 另寫一份。
