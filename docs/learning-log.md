# 學習筆記（縮網址專案）

> 用途：把每個 Stage 做了什麼、為什麼這樣做，用「零 Django 基礎」的角度記下來，方便日後複習與向面試官解釋。
> 面試「會被問的考點」另外整理在 [`interview-qa.md`](interview-qa.md)。

---

## Stage 0 — 專案地基（逐檔解說）

### 0. 全局心智模型：一個請求怎麼變成回應

當有人在瀏覽器輸入網址並按 Enter：

```
瀏覽器  ──HTTP 請求──►  網頁伺服器  ──►  WSGI  ──►  Django
 (使用者)              (gunicorn/runserver)  (翻譯官)   ├─ Middleware（層層中介處理）
                                                      ├─ urls.py（總機：這個網址該找誰？）
                                                      ├─ view（承辦人：處理並產生內容）
                                                      └─ template（把資料填進 HTML）
瀏覽器  ◄──HTTP 回應──────────────────────────────────┘
```

**大樓比喻**：
- Django 專案（`config/`）= 大樓的「管理中心」（規章 + 總機）
- app（`apps/core`）= 大樓裡的「部門」（負責一塊功能）
- WSGI = 大門口的「翻譯官」（把 HTTP 翻成 Django 懂的 Python 物件）
- urls.py = 「總機」（依網址轉接到對的承辦人）
- view = 「承辦人」（真正處理請求、產生回覆）
- template = 「公文範本」（把資料填進去變成 HTML）
- settings = 大樓的「規章制度」

Django 的正式架構叫 **MVT（Model–View–Template）**：
- **Model** = 資料怎麼存（資料庫，Stage 1 才做）
- **View** = 處理邏輯
- **Template** = 畫面長相

---

### 1. 工具層：uv / `.venv` / `pyproject.toml` / `uv.lock`

| 檔案/資料夾 | 是什麼 | 為什麼需要 |
|---|---|---|
| `.venv/` | 這個專案專屬的 Python + 套件（虛擬環境） | 套件版本隔離，不污染系統 Python |
| `pyproject.toml` | 專案身分證 + 套件購物清單（人看的）| 宣告「我需要 Django」等需求 |
| `uv.lock` | 精確收據：實際版本 + 雜湊（機器看的）| 確保各環境裝到一模一樣 → 可重現 |

> 考點：為什麼要 lock 檔？因為 `pyproject.toml` 只寫「Django 5.2 以上」，`uv.lock` 把確切版本（如 5.2.15）釘死，避免「我電腦會動、上線就壞」。

---

### 2. 「專案 vs app」

- **專案（project）= `config/`**：整個網站只有一個，放全站設定與總路由。
- **app = `apps/core/`**：功能模組，可有很多個。`core` 放「跨領域」的東西（首頁、健康檢查）。Stage 1 會加 `shortener`、`analytics`。

> 考點：project 是設定容器（一個）；app 是可重用的功能模組（多個）。

---

### 3. 逐檔解釋（按請求流動順序）

**`manage.py`** — 指令入口。你打的每個指令都透過它。關鍵那行設定「本機跑指令時預設用 dev 設定」：
```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
```

**`config/wsgi.py` / `asgi.py`** — 伺服器與 Django 的橋。上線時 gunicorn 透過 `wsgi.py` 呼叫 Django，並指定「上線用 prod 設定」。
- WSGI = 傳統同步介面（我們用這個）；ASGI = 非同步（WebSocket 等，先備用）。

**`config/settings/`（base / dev / prod）** — 設定分三層：
- `base.py`：三環境共用（載入哪些 app、資料庫、模板位置…）。
- `dev.py`：`from .base import *` 繼承後覆寫 → `DEBUG = True`（顯示詳細錯誤頁）。
- `prod.py`：→ `DEBUG = False`、強制 HTTPS、密鑰一定要從環境變數來。

兩個關鍵觀念（在 `base.py`）：
1. **密鑰不寫死**，用 `django-environ` 從環境變數讀（程式碼會上 GitHub，寫死=外洩）。
2. **資料庫用一條 `DATABASE_URL`**，本機沒設用 SQLite，上線設成 Postgres。

**`config/urls.py`** — 總路由：
```python
path("admin/", admin.site.urls),       # /admin/ → Django 內建後台
path("", include("apps.core.urls")),   # 其他 → 轉接給 core 的路由表
```
`include` = 「這段網址我不自己處理，轉給某 app 的 urls.py」。

**`apps/core/urls.py`** — core 的路由：
```python
path("", views.home, name="home"),
path("healthz", views.healthz, name="healthz"),
```
`name=...` 給網址取代號，模板用 `{% url 'core:home' %}` 產生網址，不寫死。

**`apps/core/views.py`** — view 就是「收 request、回 response」的函式：
```python
def home(request):
    return render(request, "core/home.html")   # 模板 → HTML
def healthz(request):
    return JsonResponse({"status": "ok"})       # 直接回 JSON
```
`healthz` 是**健康檢查端點**：上線後 Cloud Run 會定期戳它，回 200 代表服務活著，掛了就自動重啟。故意**不碰資料庫**，避免被慢的依賴拖垮。

**`templates/`** — 畫面範本，用**模板繼承**：`base.html` 是共用外框並用 `{% block %}` 挖空，`home.html` 用 `{% extends %}` 繼承後只填自己的內容（共用部分只寫一次）。

---

### 4. 用 `/healthz` 走一遍完整流程

打開 `網址/healthz`：
1. 請求到伺服器（本機 `runserver`），WSGI 翻成 `request` 物件。
2. 經過 middleware。
3. `config/urls.py` 看是 `/healthz` → 轉給 `apps/core/urls.py`。
4. 比對到 `path("healthz", views.healthz)` → 呼叫 `healthz`。
5. 回傳 `JsonResponse({"status": "ok"})`。
6. Django 變成 HTTP 回應送回瀏覽器 → 看到 `{"status": "ok"}`。

---

### 5. 為什麼叫 `healthz`（那個 z）

源自 **Google** 的命名慣例 **z-pages**（`/healthz`、`/statusz`、`/varz`…）。加 `z` 是為了**避免和真實業務網址撞名**，一看就知道是「給系統用的內部端點」。**Kubernetes** 把它標準化（`/healthz`、`/livez`、`/readyz`），成為雲端原生通用語。用 `/healthz` 能展現對 k8s/雲端慣例的熟悉（本職缺加分條件含 GKE）。

---

### 6. Stage 0 收尾：ruff + pre-commit + README

**ruff** 裝成 dev 依賴（`uv add --dev ruff pre-commit`，只在開發機需要，不會跟著上線），設定寫在 `pyproject.toml` 的 `[tool.ruff]`：
```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```
這取代了過去 Python 圈常見的「flake8 + isort + black」三件套——ruff 一個工具用 Rust 重寫了它們的功能，速度快很多，設定也只要一處。

**pre-commit** 是「在 `git commit` 真正寫進歷史之前，自動跑一輪檢查」的機制。設定檔 `.pre-commit-config.yaml` 掛了：
- `ruff-check --fix` + `ruff-format`：檢查並自動修正程式碼風格
- `trailing-whitespace` / `end-of-file-fixer` / `check-yaml`：抓常見小毛病（行尾多餘空白、檔案沒有結尾換行、YAML 語法錯誤）

跑 `uv run pre-commit install` 把這串檢查掛進 `.git/hooks/pre-commit`（只需做一次），之後每次 commit 都會自動跑；第一次手動驗證全部檔案用 `uv run pre-commit run --all-files`。

**README.md** 是給「第一次看到這個 repo 的人」（包含面試官）的入口：專案是什麼、技術選型、3 行指令能跑起來、進度看哪裡。跟 `CLAUDE.md`（給協作 Agent 的詳細事實來源）分工：README 對外、CLAUDE.md 對內。

---

## Stage 1 — 核心功能（逐檔解說）

### 0. 這次做了什麼

「用內建帳號登入 → 建立短網址 → 造訪短網址被 302 重導到原始網址 → 在儀表板看到點擊數與來源 IP」整條路徑全部接通。刻意**不碰 OAuth**（Stage 2 才做），這樣核心邏輯先獨立驗證過，之後換登入方式時，`shortener` / `analytics` 的程式碼幾乎不用改。

### 1. 為什麼要有「儀表板」、它到底是什麼

職缺信件規格寫「可看到自己縮網址的點擊成效與來源 IP」——這句話換成工程語言，就是要做一個**登入後才能看的頁面，把資料庫裡跟自己有關的資料查出來，整理成人看得懂的畫面**。這個頁面就叫「儀表板（dashboard）」。它不是什麼特殊技術，本質是：

```
資料庫查詢（ORM） -> view 把查詢結果包成 context -> template 把 context 畫成 HTML
```

`apps/shortener/views.py` 的 `my_links` 就是這支「承辦人」：查出 `request.user` 自己擁有的 `ShortLink`，用 `annotate(click_count=Count("clicks"))` 順手在同一次查詢裡算出每條的點擊數（不用每條另外查一次，省掉 N+1 查詢問題），再用 `prefetch_related("clicks")` 把每條的點擊紀錄一次性撈出來（同樣是避免迴圈裡每條都各查一次資料庫）。Stage 1 先做「列表頁直接展開最近幾筆點擊」這個最簡單版本，Stage 6 才會升級成圖表。

### 2. Model 落地：MVT 的 M 終於用到

Stage 0 的 MVT 心智模型裡，Model 一直是空的（沒有資料庫表）。這次新增兩個 app：
- `apps/shortener/models.py` 的 `ShortLink`：一條短網址記錄，`owner` 是 `ForeignKey` 指回 Django 內建的 `User`（`settings.AUTH_USER_MODEL`，不直接寫 `User` 是為了將來如果換成自訂使用者模型，這裡不用改）。
- `apps/analytics/models.py` 的 `Click`：一筆點擊記錄，`link` 是 `ForeignKey` 指回 `ShortLink`。

寫完 model 要跑兩個指令：
- `makemigrations`：Django 比對 model 程式碼跟「上一次記錄的狀態」，把差異寫成一份 migration 檔（`apps/shortener/migrations/0001_initial.py`），這是「打算對資料庫做什麼改動」的說明書，會進版控。
- `migrate`：真正把 migration 檔案套用到資料庫，建出實際的表。

> 考點：migration 是「改動計畫」，跟資料庫實際狀態是兩件事；同一份程式碼在不同環境（本機/CI/正式）各自 `migrate` 一次，資料庫結構才會一致。

### 3. `services.py`：為什麼商業邏輯不寫在 view 或 model 裡

`apps/shortener/services.py` 的 `generate_short_code()` / `create_short_link()`，`apps/analytics/services.py` 的 `get_client_ip()` / `record_click()`，都是「做事的邏輯」，不是「接請求」或「定義資料表」。如果這些邏輯直接寫在 view 函式裡（叫做 **fat view**）或塞進 model 的方法裡（**fat model**），會有兩個問題：
1. 之後想在別的地方重用（例如 Stage 6 的 DRF API、或一個管理用的命令稿）就要複製貼上。
2. 程式碼變得難測試——測試一個 view 要連帶處理 HTTP request/response，但測試「短碼產生器有沒有正確避開碰撞」根本不需要 HTTP。

`services.py` 把「邏輯」單獨抽出來，變成一般的 Python 函式，可以被 view、admin、command、API 共用，也能被單獨測試（Stage 5 會補上 pytest）。

### 4. 短碼產生：`secrets` 模組

`generate_short_code()` 用 `secrets.choice`，不是 `random.choice`。`random` 模組是給「模擬/遊戲」用的，它的演算法是可預測的（知道種子或夠多輸出就能推算下一個值）；`secrets` 是 Python 內建的**密碼學安全**隨機數來源，專門設計給「會影響安全性」的場景（這裡是短碼，如果可被預測，等於可以被有心人猜出別人的短網址）。完整取捨見 [`docs/adr/0001-short-code-generation.md`](adr/0001-short-code-generation.md)。

### 5. View 與 URL：`@login_required`、`redirect()`、404

`apps/shortener/views.py` 三支 view：
- `create_link`：`@login_required` 是一個**裝飾器（decorator）**，包住 view 函式，會在執行前先檢查 `request.user` 有沒有登入——沒登入就自動轉去 `LOGIN_URL`（設定在 `config/settings/base.py`），登入完再轉回來。這就是「未登入導向登入頁」的標準做法，不用自己寫 if/else。
- `my_links`：見上面第 1 點。
- `redirect_short_link`：用 `get_object_or_404` 查短碼，查不到（或 `is_active=False`）就自動回 404，不用自己寫 try/except；查到就呼叫 `record_click()` 記一筆點擊，再用 `redirect(link.original_url)` 跳轉——Django 的 `redirect()` 預設就是 302，這個選擇的理由見 [`docs/adr/0002-redirect-302-not-301.md`](adr/0002-redirect-302-not-301.md)。

URL 設計上，`apps/shortener/urls.py` 把 `<str:short_code>` 這個「萬用字元」路由放在**最後一條**，因為 Django 是按順序比對 urlpatterns，如果把它放前面，"links/new"、"links/" 這些更明確的路徑反而會被它先吃掉（短碼也可能剛好叫 "links"）。

### 6. 內建登入：`django.contrib.auth.urls`

Stage 1 故意不自己寫登入邏輯，直接在 `config/urls.py` 加一行 `include("django.contrib.auth.urls")`，Django 內建就會提供 `/accounts/login/`、`/accounts/logout/` 等一整組 view。我們只需要補一個 `templates/registration/login.html`（Django 找登入模板的固定路徑），畫面就會用我們的樣式呈現。Stage 2 接 allauth 時，這行會換成 allauth 的 urls，但 `request.user` 這個介面對 `shortener`/`analytics` 完全不變——這就是「核心邏輯跟登入方式解耦」的具體做法。

### 7. Client IP 解析的安全陷阱

`get_client_ip()` 看起來只是兩行 if/else，但背後有一個重要的安全概念：`X-Forwarded-For` 這個標頭**任何人都可以偽造**，只有在「請求一定會經過我們信任的反向代理，且代理會覆寫這個標頭」的部署環境下才可信。完整推理見 [`docs/adr/0003-client-ip-parsing.md`](adr/0003-client-ip-parsing.md)。本機開發時這個標頭不存在，函式會退回 `REMOTE_ADDR`（也就是 `127.0.0.1`）。

### 8. Tailwind（CDN 版）

`templates/base.html` 的 `<head>` 加了一行 `<script src="https://cdn.tailwindcss.com">`。這是 Tailwind 的「零設定」用法：瀏覽器載入這支 script 後，它會掃描頁面上所有 HTML 的 class（例如 `class="bg-white border rounded p-4"`），即時生成對應的 CSS。優點是不用任何建置流程（不用 Node.js/npm/webpack），缺點是這支 script 本身偏大、且沒有把「沒用到的樣式」剔除（purge），不適合正式上線。Stage 1 求快、求畫面看得過去；如果之後要正式打磨（Stage 8），會換成 Tailwind CLI 安裝，從原始碼掃描需要的 class，產生一份精簡的 CSS 檔案。

### Stage 1 自我檢查題（答得出來才算懂）

1. `makemigrations` 跟 `migrate` 差在哪？為什麼兩個都需要？
2. 為什麼商業邏輯要放 `services.py`，不要直接寫在 view 裡？
3. `@login_required` 在背後做了什麼？
4. 為什麼短碼產生用 `secrets` 而不是 `random`？
5. 為什麼重導要用 302 不是 301？
6. `X-Forwarded-For` 為什麼不能直接信任？什麼情況下它才可信？
7. `annotate(Count(...))` 跟 `prefetch_related` 各解決什麼問題？
8. 儀表板本質上是什麼？跟「查資料庫 + 排版」有什麼關係？

---

## Stage 2：Social Login（django-allauth）

### 1. 為什麼用 django-allauth，不自己寫 OAuth

OAuth 流程看起來簡單（跳到 Google → 使用者同意 → 跳回我們的網站帶一個 code），但細節很多陷阱：CSRF/state 參數防護、token 過期重新整理、第一次登入要不要自動建立帳號、同一個 email 在我們系統已有帳號時要不要自動關聯、各家供應商 API 形狀都不同……這些都是「資安相關、容易做錯」的程式碼，業界標準做法是交給一個被大量專案驗證過的套件，而不是自己刻一份。`django-allauth` 是 Django 生態圈最主流的選擇。

### 2. 安裝後多了哪些 app

`config/settings/base.py` 的 `THIRD_PARTY_APPS` 多了 5 個：
- `allauth`、`allauth.account`：帳號核心（登入/登出/signup/密碼）
- `allauth.socialaccount`：社群登入框架本身
- `allauth.socialaccount.providers.google`、`.facebook`：各供應商的 OAuth 細節（API endpoint、要哪些 scope）

每多裝一個 provider，就是多 import 一個 `providers.<name>` app，框架其餘部分不用改。

### 3. `AUTHENTICATION_BACKENDS` 在做什麼

Django 的登入機制其實是「依序問過一串 backend：你認得這個帳密／token 嗎？」。我們現在有兩個 backend：
- `ModelBackend`：Django 內建，負責「使用者名稱 + 密碼」這種傳統登入（Stage 1 建的帳號就是靠它認證）。
- `allauth.account.auth_backends.AuthenticationBackend`：負責 allauth 自己的登入流程（包含社群登入完成後，把「Google 這個人」對應回我們資料庫的哪個 `User`）。

兩個都列出來，代表「使用者名稱密碼」跟「Google/Facebook」兩條路都能成功登入，`request.user` 最後拿到的都是同一種 Django `User` 物件，`shortener`/`analytics` 完全不用區分使用者是怎麼登入的。

### 4. 為什麼不需要 `django.contrib.sites`

allauth 比較舊的教學常會要求裝 `django.contrib.sites` 並設定 `SITE_ID = 1`，因為早期版本把每個 OAuth app 的憑證存在資料庫的 `SocialApp` 表，需要 sites framework 來決定「這個 app 屬於哪個網域」。0.48.0 之後，allauth 支援直接在 `settings.py` 的 `SOCIALACCOUNT_PROVIDERS["<provider>"]["APPS"]` 寫憑證（我們採用的方式），這條路徑完全不依賴 sites framework，少一層設定、少一個資料表。詳細取捨見 [`docs/adr/0004-social-login-credentials.md`](adr/0004-social-login-credentials.md)。

### 5. 憑證為什麼用環境變數，不是寫在程式碼或資料庫

延續 Stage 0 就定下的 12-factor 原則（`SECRET_KEY`/`DATABASE_URL` 都走環境變數）。`_oauth_app()` 這個 helper 函式（`config/settings/base.py`）刻意做了一件小事：**如果環境變數沒填，回傳空列表，不是回傳一個「憑證是空字串」的假 app**。原因是 allauth 用「這個 provider 有沒有至少一個 app」來決定登入頁要不要顯示對應的按鈕；如果硬塞一個空字串的 app，按鈕會出現但點下去必定失敗。回傳空列表，才能讓「沒設定 Google 憑證」跟「使用者根本沒看到 Google 按鈕」這兩件事保持一致，使用者體驗上不會看到一個註定壞掉的按鈕。

### 6. URL 名稱從 `login`/`logout` 換成 `account_login`/`account_logout`

Stage 1 用 Django 內建的 `django.contrib.auth.urls`，登入頁的 URL name 叫 `login`。換成 `include("allauth.urls")` 後，allauth 自己的登入頁叫 `account_login`、登出叫 `account_logout`（這是 allauth 套件自己定義的名稱，跟 Django 內建的不是同一套）。所以 `LOGIN_URL` 設定值跟 `templates/base.html` 裡所有 `{% url 'login' %}` 都要跟著換成新名稱，否則會在 reverse URL 的時候直接報錯（`NoReverseMatch`）——這也是為什麼前面強調「核心邏輯解耦」指的是 `shortener`/`analytics` 不用改，不是「完全不用碰任何程式碼」。

### 7. 沒有真的 Google/Facebook 憑證之前，畫面會怎樣

`SOCIALACCOUNT_PROVIDERS` 裡兩個 provider 的 `APPS` 在沒填環境變數時都是空列表，所以 allauth 的登入頁範本（`{% get_providers %}` 找不到任何 provider）就只會顯示使用者名稱/密碼表單，跟 Stage 1 的體驗幾乎一樣——這是刻意設計的，讓我們現在就能先驗證「程式碼接得起來、不會炸」，之後只要去 Google Cloud Console / Facebook 開發者後台申請真的憑證、填進 `.env`，重啟伺服器，按鈕就會自動冒出來，不用再改一行程式碼。

### Stage 2 自我檢查題（答得出來才算懂）

1. `AUTHENTICATION_BACKENDS` 裡兩個 backend 分別負責什麼？為什麼兩個都要留著？
2. allauth 0.48.0 之後為什麼不強制需要 `django.contrib.sites`？
3. 為什麼 `_oauth_app()` 在憑證缺漏時要回傳 `[]`，而不是回傳一個空字串的 app？
4. 為什麼 OAuth 憑證要放環境變數，不是寫在程式碼或存進資料庫？
5. 如果完全沒有設定任何 Google/Facebook 憑證，使用者還能不能登入？登入頁會長什麼樣？

---

### Stage 0 自我檢查題（答得出來才算懂）

1. Django 的 project 和 app 差在哪？
2. 什麼是 MVT？各自負責什麼？
3. 一個 HTTP 請求進到 Django 到回應出去，經過哪些關卡？
4. 為什麼 settings 要分 base/dev/prod？
5. 為什麼 `SECRET_KEY` 不直接寫在程式裡？
6. WSGI 是什麼？為什麼需要它？
7. `/healthz` 做什麼？為什麼故意不碰資料庫？為什麼叫 healthz？
8. 虛擬環境是什麼？`uv` 跟 `pip + venv` 差在哪？
