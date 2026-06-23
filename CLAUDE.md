# CLAUDE.md — 縮網址服務（Django + Social Login，求職作品）

> 本檔是專案的**單一事實來源（single source of truth）與進度追蹤板**。
> **任何 Agent 開工前都先讀本檔**，依 Stage 順序實作，完成後即時更新各 Stage 的勾選與狀態，並更新「📍 目前進度」兩行。

---

## 📍 目前進度（每次開工/收工都要更新這兩行）

- **目前 Stage**：Stage 3 已完成並部署（Cloud Run，服務網址 https://shortlink-ljrbbufbfq-de.a.run.app ，Cloud SQL Postgres `asia-east1`/`db-f1-micro`、secrets 走 Secret Manager）。之後又做了一批 **Stage 3 之後的登入/UI 打磨（已在本機真人驗收，並已部署到 Cloud Run：revision `shortlink-00005`；線上 `/livez` 與 entrance 頁已驗證，提醒對外只用新格式網址 https://shortlink-ljrbbufbfq-de.a.run.app ，OAuth redirect URI 只設在這組）**：(1) 介面全英文 + 可切換 dark mode（手動切、記 localStorage）+ 按鈕 hover 改成陰影/變色（不上浮）；(2) **OpenAI 風格 email-first 登入入口**（`apps/accounts`，`/accounts/start/`）：填 email → 已註冊轉登入、未註冊轉註冊、純社群帳號轉「Continue with Google/Facebook」引導頁；(3) **跨 provider 自動連結**（同已驗證 email 用第二個 provider 登入會連到同一帳號；Facebook 設 `VERIFIED_EMAIL: True`）；(4) 修掉登入失敗時 non-field error 被吃掉、畫面無反應的 bug。決策見 [`docs/adr/0009-email-first-auth.md`](docs/adr/0009-email-first-auth.md)。**再來又做了一批登入/UX 打磨（items 5–8，現已連同下面的 items 9–10 一起部署上 Cloud Run 並真人驗收通過）**：(5) 社群登入按鈕改成 **POST**，跳過 allauth 的「Continue」中間確認頁（保留 CSRF 保護，而非關掉 `SOCIALACCOUNT_LOGIN_ON_GET`）；(6) signup 拿掉常駐的密碼規則 help text（4 個 `AUTH_PASSWORD_VALIDATORS` 照常作用，違規才出紅字）；(7) 移除登入頁「Forgot your password?」連結——無寄信基礎設施、密碼重設無法運作，且 app 是 social-login-first，移除入口好過保留會 500 的功能（reset URL 本身仍在，必要時可再擋）；(8) dev 改用 console email backend（忘記密碼不再 ConnectionRefused 500）。(5)(7) 透過 `CustomSignupForm`/`CustomLoginForm`（`ACCOUNT_FORMS`）實作；過程順手修掉一個回歸 bug：多行 `{# #}` 註解（單行限定）外漏成頁面文字，改用 `{% comment %}`。**最新一批（items 9–10，已 commit/push，且已部署上 Cloud Run、真人驗收通過：Google 登入確認會跳「選擇帳號」、線上直接打 `accounts/password/reset/` 回 404）**：(9) **Google 登入每次強制跳「選擇帳號」**——在 `SOCIALACCOUNT_PROVIDERS["google"]` 加 `"AUTH_PARAMS": {"prompt": "select_account"}`（本機真人驗收：即使只有單一帳號也會先跳出選帳號頁；`prompt=select_account` 為 Google 專屬，Facebook 無等價參數，其 `auth_type=reauthenticate` 是「重輸密碼」而非「換帳號」，故 FB 換帳號仍只能靠無痕視窗）；(10) **prod 擋掉密碼重設頁**——新增 `PASSWORD_RESET_ENABLED` 開關（`base.py`=True、`prod.py`=False、dev 繼承 base 的 True），在 `config/urls.py` 的 allauth `include` 之前、當開關關閉時用一個 `raise Http404` 的小 view（`_disabled`）覆寫掉重設入口 `accounts/password/reset/` 與信件 key 確認頁 `accounts/password/reset/key/...`（兩個 `done` 純文字頁不擋，反正入口被擋就走不到）；dev 維持可用（已用 Django test client 分別驗證 dev=200、prod=404）。**Facebook 無法由 app 端強制「選帳號」（平台限制，靠無痕視窗）。** **接著又做了一批前台 UI/UX 改造（首頁與 My Links 儀表板，已部署到 Cloud Run 並真人驗收通過：線上 `/livez` 回 ok、首頁新版登入卡與儀表板皆已上線）**：(a) 首頁改成「看登入狀態的單一入口」——未登入直接嵌入 email-first 登入（重用 `account_entrance` 表單 + allauth 社群 POST 片段），已登入則 `redirect` 到儀表板；nav 拿掉多餘的 My Links / Create / Sign In 連結（品牌字回首頁即可到達）。(b) **My Links 變成單頁儀表板**：「+ Create」改用瀏覽器原生 `<dialog>` modal 建立（POST 回 `my_links`、成功走 PRG 重導、失敗自動重開並顯示錯誤），獨立的 Create 頁／URL／view 整組移除；`my_links` view 改成同時處理 GET 顯示與 POST 建立。(c) **整張卡點擊即複製短網址**（`navigator.clipboard.writeText` + 底部 toast 回饋；短碼藍字 `target="_blank"` 開新分頁，並用 `event.stopPropagation()` 讓點藍字不誤觸複製）。(d) **點擊明細可就地展開**：預設露 3 筆，>3 筆才在區塊右上顯示扁平 SVG chevron，點擊以 inline accordion 切換「3 筆預覽 ↔ 全部點擊（`max-h-72` 可捲動）」並轉動箭頭；preview/full 都套自訂細捲軸（`::-webkit-scrollbar` + `scrollbar-width`）並用 `scrollbar-gutter: stable` 預留捲軸空間，避免展開時表格跑位。過程踩到的坑：多行 `{# #}` 註解外漏成頁面文字（同 items 5–8 的老坑，且因漏出的字裡含 `<dialog>` 還連帶造成隱形 dialog 吞掉內容，改用 `{% comment %}`）、可展開明細若放進「可點即複製」的卡片內會因事件冒泡誤觸複製（改放卡外或加 `stopPropagation`）。chevron 必須放在「包住 preview/full 的 `relative` 容器」上、而非放進會互相隱藏的 preview/full（否則展開後 chevron 跟著消失）。(e) 首頁登入卡版面對齊 entrance 頁（`max-w-sm` 窄卡、`{% comment %}element h1{% endcomment %}` 大標題、`rounded-2xl p-8`），但外層 hero 維持 `max-w-md` 讓副標題保持一行。**這批部署時踩到三個雷，已寫進 README 部署章節的「重新部署」runbook：① build 要在專案目錄（含 Dockerfile）跑，否則 `Dockerfile required`；② image path 的專案是 `shortlink-499808`（README 舊版誤寫 `shortlink-demo`，已全數修正），用錯會 push `denied`；③ 重新部署只給 `--image`，千萬別帶 `--set-secrets`（整組覆蓋，漏 `REDIS_URL` 會洗掉線上設定、`prod.py` 缺它即啟動報錯）。**
- **下一步**：items 5–10 與**前台 UI/UX 改造（首頁登入 landing + 儀表板 modal 建立／點擊複製／可展開明細 + 登入卡版面微調）皆已部署上 Cloud Run 並真人驗收通過、全部上線**（線上 `/livez` 回 ok；部署用 README 部署章節新加的「重新部署」runbook，內含 `shortlink-499808` 正確專案 ID 與「只給 `--image`、勿帶 `--set-secrets`」的眉角）。**Stage 4 — 效能（作者指定優先項）進行中**：**優化 1（重導 Redis cache-aside）已實作、本機驗證、並部署上線真人驗收通過**（revision `shortlink-00007-gt7`；prod 接 **Upstash** serverless Redis〔GCP 東京 `asia-northeast1`，free tier〕，URL 走 Secret Manager `redis-url`；`prod.py` 已設成缺 `REDIS_URL` 即啟動報錯，Dockerfile 的 build-time `collectstatic` 加了佔位 `REDIS_URL`；Upstash 後台確認線上走真 Redis〔Writes=建立的 DEL＋miss 的 SET、Reads=GET＋連線 handshake〕）。剩 DB 索引 + `EXPLAIN` 分析、非同步寫入點擊、建立/重導加 rate limiting。協作方式改為「作者本人寫所有程式碼、Claude 只逐步指導」（文件 ADR/CLAUDE.md 由 Claude 代筆）。

狀態圖例：⬜ 未開始｜🟡 進行中｜✅ 完成

---

## 1. 專案目標與繳交需求

面試作品。不只要「會動」，而是用**工程決策**展現資深判斷力，同時讓作者**完全看懂每一行**（即使由 AI 撰寫）。

**功能需求（信件規格）**
1. 用 **Django** 建立縮網址服務，支援 **Google + Facebook Login**
2. 登入後可建立縮網址
3. 縮完的網址可前往指定連結
4. 可看到自己縮網址的**點擊成效與來源 IP**

**繳交**：GitHub repo + 服務網址　|　**期限**：6/29（一）

**✅ 可繳交門檻 = 完成 Stage 0–3**（核心功能齊全 + Google/FB 登入 + 已部署有公開網址）。
Stage 4 之後皆為**持續加分**。**Stage 4（效能）為作者指定的優先項**。

## 2. 對齊職缺（差異化重點，面試時要能逐點對應）

| 職缺條件 | 在本專案如何命中 | 落在哪個 Stage |
|---|---|---|
| 必要：懂 Django | 整個後端：ORM、allauth、服務層、DRF | Stage 1–6 |
| 必要：懂 git 協作 | feature branch + PR、Conventional Commits、CI | 全程 / Stage 5 |
| 必要：懂 SQL | 設計過的 schema 與索引、raw SQL 分析查詢 + `EXPLAIN` | Stage 4 / 6 |
| 加分：GCP（GAE/GKE/GCF/GCR） | **Cloud Run** + **Cloud SQL** + Artifact Registry + Secret Manager | Stage 3 / 5 |
| 加分：vue/react | **React 點擊分析儀表板**（吃 DRF API） | Stage 7 |
| 必要：懂 Flask | （選配）獨立 **Flask redirect 微服務**，一專案展示兩框架 | Stage 7 |
| 「漂亮的程式碼、遵循規範」 | ruff + mypy + pre-commit、type hints、服務層分離 | 全程 |
| 「分享讓新知變知識」 | ADR + 架構文件 + `docs/interview-qa.md` 本身即此特質的證據 | 全程 / Stage 8 |

## 3. 技術選型（每一項都要能對面試官說「為什麼」）

- **Python 3.13 + Django 5.2 (LTS)**；**uv** 管套件（快、有 `uv.lock`，可重現建置）
- **django-allauth**：Google/FB OAuth 業界標準；不自刻 OAuth（安全性交給經驗證套件＝資深取捨）
- **PostgreSQL**：prod 用 Cloud SQL、本機用 docker-compose（dev/prod parity，不上 SQLite）
- **Redis**（Django 內建 redis cache backend）：重導熱路徑快取 + rate limiting
- **HTMX + Tailwind CSS**：模板導向、低 JS、互動好、程式碼全在 Django 內最好懂
- **django-environ**（12-factor 設定）、**Gunicorn + WhiteNoise**（容器內 server + 靜態檔）
- **DRF + drf-spectacular**（Stage 6）：OpenAPI/Swagger，並餵 React 儀表板
- **pytest + pytest-django + factory_boy + coverage**（Stage 5）
- **ruff（lint+format）+ mypy + pre-commit**、**GitHub Actions**（CI/CD）
- **Docker 多階段 build + docker-compose**（同一份 Dockerfile 直上 Cloud Run）；**user-agents** 解析 UA

## 4. 架構與資料模型

Django project 放 `config/`，功能切 app（皆置於 `apps/` 套件下）：
- `apps/core`：跨領域（首頁、`/livez` 健康檢查）
- `apps/accounts`：allauth 認證、使用者 profile
- `apps/shortener`：`ShortLink` 模型、建立/重導、**短碼產生服務**
- `apps/analytics`：`Click` 模型、聚合查詢、儀表板
- `apps/api`：DRF（Stage 6）

**商業邏輯放各 app 的 `services.py`**（避免 fat view/model）。設定分層在 `config/settings/{base,dev,prod}.py`。

實際結構：
```
pyproject.toml / uv.lock   manage.py   .env.example
config/settings/{base,dev,prod}.py   config/{urls,wsgi,asgi}.py
apps/{core,accounts,shortener,analytics,api}/  (models / services / views / urls / tests)
templates/   static/   docs/{architecture.md, adr/, learning-log.md, interview-qa.md}   .github/workflows/ci.yml
```

**資料模型**
- `ShortLink`：`owner`(FK)、`original_url`、`short_code`(**unique, indexed**)、`is_active`、`created_at/updated_at`、選配 `title`/`expires_at`
- `Click`：`link`(FK, indexed)、`created_at`(indexed)、`ip_address`、`user_agent`、`referer`、解析後 `device/browser/os`
- 索引：`short_code` unique（重導熱路徑）、`(link, created_at)` 複合（時間序）、`owner`（列表）

## 5. 關鍵設計決策（寫成 `docs/adr/`，是「驚艷點」）

1. **短碼產生**：隨機 base62（7 碼 ≈ 3.5 兆）+ unique constraint + 碰撞重試。論述為何不用「自增 ID 轉 base62」（可列舉、洩漏規模）或「URL hash」（碰撞、無法 per-user）。
2. **重導用 302 而非 301**：301 會被瀏覽器快取 → **漏記點擊**；302 確保每次點擊都記得到。
3. **來源 IP 解析**：Cloud Run 在反向代理後，需正確讀 `X-Forwarded-For` 取真實 client IP（並注意可偽造），不可直接用 `REMOTE_ADDR`。

## 6. 開發守則 / 給後續 Agent 的協作守則

- **開工前先讀本檔**，從「📍 目前進度」找到要做的 Stage；**依序做、不跳階**。
- **小步可審查**：一個功能一個 commit，**Conventional Commits**（`feat:`/`fix:`/`docs:`…）；feature branch + PR。
- **commit message 不要寫 Stage 編號**（如「Stage 1」「Stage 2」）。Stage 是這份內部進度文件的階段劃分，不是給外部讀 git log 的人看的概念；commit message 只描述這次改動本身做了什麼（例如 `feat: add shortener app with short link creation`），不要參照內部階段名稱。
- 程式碼要**作者本人能逐行看懂**：type hints + docstring + 適當註解；實作每塊先解釋「做什麼/為什麼」。
- 用 **Context7** 拉當前版本的 Django/allauth/DRF 文件，勿憑舊記憶。
- 關鍵決策寫進 `docs/adr/`；學習重點寫進 `docs/learning-log.md`；**面試可能被問的概念整理進 `docs/interview-qa.md`**（含簡答 + 延伸）。
- **完成一個 Stage 前先跑該 Stage 的「完成定義」驗收**，通過後才把 checkbox 打勾、更新狀態與「📍 目前進度」兩行。

## 7. 常用指令（隨 Stage 逐步成形）

```bash
uv sync                                   # 安裝依賴
docker compose up -d                      # 起 web + postgres + redis（Stage 3 後）
uv run python manage.py migrate           # 套用 migration
uv run python manage.py runserver         # 本機開發（預設 config.settings.dev）
uv run pytest                             # 測試（Stage 5 後）
uv run ruff check . && uv run mypy .      # lint + 型別
gcloud run deploy ...                     # 部署 Cloud Run（Stage 3 後）
```

> 設定模組：`manage.py` 預設 `config.settings.dev`；`wsgi.py`/`asgi.py` 預設 `config.settings.prod`；可用 `DJANGO_SETTINGS_MODULE` 覆寫。

---

## 8. 分階段 Roadmap（由簡到繁；Stage 0–3 = 可繳交）

> 每個 Stage：**目標 → 任務（checkbox）→ 完成定義（驗收）**。Agent 完成後更新狀態與勾選。

### Stage 0 — 專案地基　狀態：✅ 完成
**目標**：可運行的 Django 骨架 + 工具鏈 + repo + 本檔落地成 `CLAUDE.md`。
- [x] `uv` 起專案、安裝 Django、建立 `config/`（含 settings 分層 base/dev/prod + django-environ）
- [x] 首頁 view + `/livez` 健康檢查端點（`apps/core`）
- [x] 把計畫落地成 `CLAUDE.md`、`docs/` 初始化（已有 `docs/interview-qa.md`）
- [x] `.gitignore` + `.env.example`
- [x] ruff + pre-commit + README 骨架
- [x] `gh` 建立 GitHub repo、首次 commit/push
**完成定義**：`runserver` 本機可開首頁；`/livez` 回 200（✅ 已驗證）；pre-commit 通過；已 push 上 GitHub。

### Stage 1 — 核心功能（本機 MVP，先用 Django 內建登入）　狀態：✅ 完成
**目標**：本機就能「建立短網址 → 重導 → 看點擊數與來源 IP」（先用內建 auth，**刻意把 OAuth 風險與核心邏輯解耦**）。
- [x] `shortener`：`ShortLink` 模型 + migration；`services.py` 短碼產生（隨機 base62 + 碰撞重試）
- [x] 登入後的建立短網址表單（綁 `request.user`）+ 我的短網址列表
- [x] 重導 view：依 `short_code` 取 `original_url` 並 **302** 跳轉
- [x] `analytics`：`Click` 模型；重導時記錄 `ip / user_agent / referer / created_at`
- [x] 儀表板顯示每條短網址的點擊數與來源 IP；Tailwind 基本版型
**完成定義**：本機用內建帳號登入後，建立→造訪→重導成功，且儀表板看得到點擊數與來源 IP。（✅ 已用 Django test client 跑過一次完整流程驗證）

**備註（這次開工決定，供下一個 Agent 接續時參考）**：
- 沒有建立 `apps/accounts`，直接在 `config/urls.py` 用 `include("django.contrib.auth.urls")` 撐住登入/登出；Stage 2 接 allauth 時再正式生出 `apps/accounts`。
- Tailwind 目前是 CDN 版（`<script src="https://cdn.tailwindcss.com">`），零設定但未 purge，正式打磨（Stage 8）再換成 CLI 安裝。
- 三個關鍵決策（短碼產生、302 重導、X-Forwarded-For 解析）已寫成 `docs/adr/0001~0003`。

### Stage 2 — Social Login（Google + Facebook）　狀態：✅ 完成
**目標**：用 django-allauth 接上 Google/FB 登入（`request.user` 抽象不變，核心程式碼幾乎不動）。
- [x] 安裝設定 django-allauth（`INSTALLED_APPS`/`AUTHENTICATION_BACKENDS`/`MIDDLEWARE`、`config/urls.py` 換成 `include("allauth.urls")`、`SOCIALACCOUNT_PROVIDERS` 從環境變數讀 Google/Facebook 憑證，缺憑證時該 provider 的登入按鈕自動不顯示）；已用 Django test client 驗證帳密登入/登出在新設定下仍正常
- [x] Google provider（OAuth consent + 憑證）——已在 Google Cloud Console 申請，填進 `.env`
- [x] Facebook provider（FB App，dev mode + 自己當測試者即可）；本機 redirect URI（`http://localhost:8000/...`，FB 對 `localhost` 自動允許 HTTP）——已在 Facebook Developer 後台申請；正式環境的 redirect URI 留待 Stage 3 部署後補上
- [x] 登入/登出頁（沿用 allauth 內建範本，尚未套 Tailwind 樣式）；未登入導向登入；secrets 走環境變數（見 [`docs/adr/0004-social-login-credentials.md`](docs/adr/0004-social-login-credentials.md)）
**完成定義**：本機可用 Google 與 Facebook 帳號登入並建立/查看自己的短網址。**✅ 已通過真人瀏覽器測試：Google、Facebook 皆登入成功，且能建立/查看短網址。**
**備註**：沒有另外建立 `apps/accounts`——allauth 本身已是一個完整的 app，目前不需要自訂 profile model，沿用 allauth 內建的 `account`/`socialaccount` app 即可；若之後需要自訂使用者欄位再評估是否要加 `apps/accounts`。

### Stage 3 — 部署上 Cloud Run　狀態：✅ 完成　← ✅ **可繳交里程碑**
**目標**：服務有公開 HTTPS 網址，正式環境全流程可用。
- [x] 多階段 Dockerfile + Gunicorn + WhiteNoise；docker-compose 本機 parity（已在本機用 `docker compose`
  跑通 prod-like 容器的完整流程：`/livez`、WhiteNoise 靜態檔、登入、建立短網址、302 重導、點擊記錄）
- [x] 部署 Cloud Run；資料庫接 Cloud SQL（Postgres，`shortlink-db`，`asia-east1`，`db-f1-micro`）；
  secrets 走 Secret Manager（`SECRET_KEY`/`DATABASE_URL`/四個 OAuth 憑證）
- [x] 正式網域設定 OAuth callback + `CSRF_TRUSTED_ORIGINS`；跑 migration；`/livez` 正常
- [x] README 補上部署 runbook 與服務網址欄位（服務網址：https://shortlink-ljrbbufbfq-de.a.run.app ）
**完成定義**：以公開網址用 Google/FB 登入 → 建立短網址 → 造訪重導 → 看到點擊與來源 IP。**此時即可繳交。**
**✅ 已通過真人瀏覽器測試：Google、Facebook 皆登入成功，並完整跑過建立短網址 → 造訪重導 → 儀表板看到點擊數與來源 IP。**
**備註**：
- 詳細 gcloud 指令清單見 README「部署到 Cloud Run」章節；關鍵決策見
  [`docs/adr/0005-cloud-run-deployment.md`](docs/adr/0005-cloud-run-deployment.md)
- 部署過程踩到兩個坑，已修正並記錄：(1) Cloud Run 在共用 `*.run.app` 網域上把 `/healthz` 這個精確路徑
  保留給自己內部使用，外部請求永遠連不到容器，把健康檢查端點改名成 `/livez`（見
  [`docs/adr/0006-livez-not-healthz.md`](docs/adr/0006-livez-not-healthz.md)）；(2) Django 預設只在
  `DEBUG=True` 時把例外印到 console，正式環境 `DEBUG=False` 又沒設 `ADMINS`，例外會被靜默吞掉，已在
  `config/settings/prod.py` 加上 `LOGGING` 設定確保錯誤一定會進 Cloud Logging（見
  [`docs/adr/0007-prod-logging-config.md`](docs/adr/0007-prod-logging-config.md)）
- Cloud Run 預設網域有新舊兩種格式同時生效（`https://shortlink-ljrbbufbfq-de.a.run.app` 新格式 /
  `https://shortlink-642047376218.asia-east1.run.app` 舊格式），目前只在新格式那組設定了 OAuth
  redirect URI 與 `CSRF_TRUSTED_ORIGINS`，**對外都只使用/分享新格式網址**，舊格式網址登入會因
  `redirect_uri_mismatch` 失敗（已知行為，非 bug）
- 完整踩坑紀錄（含 Cloud SQL edition/tier、Cloud Run 請求層級日誌怎麼查）寫在
  [`docs/learning-log.md`](docs/learning-log.md) 的「Stage 3 — 部署上 Cloud Run（踩坑紀錄）」；
  對應的面試問答見 [`docs/interview-qa.md`](docs/interview-qa.md) D1–D3

### Stage 4 — 效能（作者指定優先）　狀態：🟡 進行中
**目標**：重導熱路徑與點擊寫入最佳化，並能用數據/`EXPLAIN` 講出來。
- [x] 重導走 **Redis cache-aside**（短碼→`(id, url)` tuple，TTL 1h + `post_save`/`post_delete` 訊號失效；`record_click` 改收 `link_id`；無 `REDIS_URL` 時 fallback `LocMemCache`）。已用 Django 測試框架驗證 miss=1／hit=0 query、改 URL 後失效、停用回 `None`。決策見 [`docs/adr/0010-redis-cache-aside.md`](docs/adr/0010-redis-cache-aside.md)。**已部署上線（revision `shortlink-00007-gt7`，prod 接 Upstash 東京、`REDIS_URL` 走 Secret Manager、`prod.py` 缺 `REDIS_URL` 即報錯、Dockerfile collectstatic 加佔位值），Upstash 後台確認線上走真 Redis。**
- [ ] DB 索引落實 + `EXPLAIN` 分析（SQL 訊號）；寫進 `docs/adr/`
- [ ] **非同步寫入點擊**（不阻塞重導）；302 決策落地並記錄
- [ ] 建立/重導加 **rate limiting**
- [ ] **12-factor Concurrency**：調校 Gunicorn worker 數量（目前未特別設定，靠 Cloud Run 多實例擴展，行程內部還是單 worker）
- [ ] **12-factor Admin processes**：`migrate` 改用獨立的 Cloud Run Job 跑，不要繼續放在 `entrypoint.sh` 跟著每個容器實例啟動時重複跑（目前的 race condition 取捨見 `entrypoint.sh` 註解）
**完成定義**：重導命中快取免查 DB；有 before/after 量測或 `EXPLAIN` 說明；點擊記錄不影響重導延遲。

### Stage 5 — 測試 + CI/CD　狀態：⬜
**目標**：可信賴的自動化。
- [ ] pytest + pytest-django + factory_boy + coverage（核心路徑覆蓋）
- [ ] GitHub Actions：lint + mypy + test
- [ ]（選配）CD：push 後自動部署 Cloud Run（Artifact Registry）
**完成定義**：CI 綠燈；覆蓋率報告產出；（若做 CD）merge 後自動上線。

### Stage 6 — 分析升級 + REST API　狀態：⬜
**目標**：更完整的成效分析與可文件化的 API。
- [ ] HTMX 即時更新的儀表板：時間序圖、referer/UA（device/browser/OS）解析
- [ ] DRF API（短網址 CRUD + 點擊統計）+ drf-spectacular（Swagger 互動文件）
**完成定義**：儀表板有圖表與來源拆解；`/api/docs` 可互動測試 API。

### Stage 7 — 加分訊號（vue/react、Flask）　狀態：⬜
**目標**：直接命中職缺加分條件。
- [ ] **React 分析儀表板**（吃 Stage 6 的 DRF API）→ vue/react 加分
- [ ]（選配）**Flask redirect 微服務** → 一專案展示 Django + Flask
**完成定義**：React 儀表板能呈現點擊分析；（若做）Flask 服務能重導並記錄點擊。

### Stage 8 — 打磨與文件　狀態：⬜
**目標**：把「資深」訊號收尾。
- [ ] ADR 補齊、`docs/architecture.md` + 架構圖、README 截圖/GIF、demo 資料
- [ ] 安全標頭（CSP/HSTS 等）、IP 匿名化/GDPR 註記
**完成定義**：README 完整、文件齊全、安全基線到位。

---

## 9. 風險與眉角（先知道才不會卡關）

- **OAuth 設定耗時**：Google consent screen + 憑證；FB App 用 dev mode + 測試者即可；需設 localhost 與 prod 兩組 redirect URI。預留時間。
- **Cloud Run ↔ Cloud SQL**：用 Cloud SQL connector/unix socket；secrets 走 Secret Manager。
- **Redis on GCP**：Memorystore 需 Serverless VPC connector（成本/設定）；**Upstash serverless Redis 作零摩擦備援**，取捨記進 ADR。
- **代理後取真實 IP**：Cloud Run 帶 `X-Forwarded-For`，務必正確解析（且注意可偽造）。
- **GCP $300 免費額度**足夠 demo；Cloud Run/Cloud SQL 設最小規格、scale-to-zero。
