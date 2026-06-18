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

### Stage 0 自我檢查題（答得出來才算懂）

1. Django 的 project 和 app 差在哪？
2. 什麼是 MVT？各自負責什麼？
3. 一個 HTTP 請求進到 Django 到回應出去，經過哪些關卡？
4. 為什麼 settings 要分 base/dev/prod？
5. 為什麼 `SECRET_KEY` 不直接寫在程式裡？
6. WSGI 是什麼？為什麼需要它？
7. `/healthz` 做什麼？為什麼故意不碰資料庫？為什麼叫 healthz？
8. 虛擬環境是什麼？`uv` 跟 `pip + venv` 差在哪？
