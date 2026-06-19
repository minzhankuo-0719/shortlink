# 面試問題集（縮網址專案）

> 用途：把這個專案做過程中遇到、或面試可能被問到的問題收集起來，面試前快速複習。
> 格式：每題分「**簡答**（能脫口而出的 30 秒版本）」與「**延伸**（追問時能再深入的點）」。
> 維護：每次遇到值得記的概念，就往對應分類加一題。

## 目錄
- [A. 工具鏈與環境](#a-工具鏈與環境)
- [B. Django](#b-django)
- [C. 資料庫與 SQL](#c-資料庫與-sql)
- [D. 部署與 GCP](#d-部署與-gcp)
- [E. 系統設計（縮網址）](#e-系統設計縮網址)

---

## A. 工具鏈與環境

### A1. uv 和 pip / conda 有什麼差別？uv 需要虛擬環境嗎？

**簡答**
uv 是用 Rust 寫的 Python 工具，一個工具把 pip、venv、pyenv（甚至部分 poetry/conda）的角色全包了。它**仍然用標準的 `.venv` 虛擬環境**，差別是**自動建立、不用手動 `activate`**——用 `uv run <指令>` 就會在 `.venv` 裡執行。比 pip 快 10–100 倍（Rust + 全域快取 + 硬連結），而且會產生 `uv.lock` 鎖定所有依賴版本與雜湊，達成「可重現建置」。

**延伸**
- 「需要 env 嗎」的正確理解：**需要，但由 uv 自動管理**。`.venv` 一樣在專案資料夾，仍可手動 `source .venv/bin/activate`，只是平常不必。
- 和 **conda** 的取捨：conda 強在管理「非 Python 的二進位依賴」（C/CUDA、資料科學），但肥又慢；uv 專注 PyPI 套件、更輕更快，純 Python 的 web 專案用 uv 更合適。uv 也能像 pyenv 一樣下載/釘選 Python 版本。
- 和 **pip** 的關鍵差異是**鎖檔**：pip 的 `requirements.txt` 沒有真正的依賴解析；`uv.lock` 是完整解析 + 跨平台 + 帶雜湊，讓本機 / CI / 正式環境裝到一模一樣的依賴 → 可重現、可稽核。
- 指令對照：
  - `python -m venv .venv` / `conda create` → `uv venv`（或 `uv sync` 時自動建）
  - `activate` → 不需要，改用 `uv run ...`
  - `pip install x` → `uv add x`（寫進 `pyproject.toml` + `uv.lock`）
  - `pip freeze > requirements.txt` → 自動產生 `uv.lock`
  - `pip install -r requirements.txt` → `uv sync`
- 補充：`uv pip install ...` 是「pip 相容模式」（不寫 lock），但專案模式應該用 `uv add` / `uv sync`。

### A2. ruff 是什麼？為什麼用它取代 black + flake8 + isort？pre-commit 又是做什麼的？

**簡答**
ruff 是用 Rust 寫的 Python lint + format 工具，一個工具就把過去要分開裝的 **flake8（找問題）+ isort（排序 import）+ black（格式化）** 全部取代，速度快上 10–100 倍，設定也集中在 `pyproject.toml` 一處。`pre-commit` 則是 git 的 commit hook 管理器：在 `git commit` **真正落地前**自動跑一輪檢查（這裡掛了 `ruff check --fix` + `ruff format`），檢查沒過 commit 就會被擋下來，逼你先修好再 commit，避免「壞格式/明顯錯誤」進到歷史紀錄。

**延伸**
- `ruff check` ≈ flake8（找未使用變數、語法陷阱等規則違規）；`ruff format` ≈ black（統一縮排、引號、換行風格）；import 排序規則（`I`）內建在 ruff 裡，不用 isort。
- 專案目前 `select = ["E", "F", "I", "UP", "B"]`：E/F 是基本錯誤與風格、I 是 import 排序、UP 是建議用新版 Python 語法（如 `list[int]` 取代 `List[int]`）、B（bugbear）抓常見邏輯陷阱（如可變預設參數）。
- pre-commit 的 hook 設定檔是 `.pre-commit-config.yaml`；`pre-commit install` 只需執行一次（裝進 `.git/hooks/pre-commit`），之後每次 `git commit` 都會自動觸發；`pre-commit run --all-files` 可以手動對全部檔案跑一次（CI 或第一次設定時常用）。
- 為什麼要在 commit 前檢查而不是事後在 CI 才檢查？越早抓到問題成本越低——CI 還是會再跑一次當保險，但 pre-commit 讓問題在推上去之前就被擋掉。

---

## B. Django

### B1. 為什麼商業邏輯要放 `services.py`，不要直接寫在 view 或 model 裡？

**簡答**
直接寫在 view 裡（fat view）或塞進 model 方法裡（fat model）會讓邏輯只能在那一個地方用，而且測試時要連帶處理 HTTP 或 ORM 上下文，麻煩又慢。把邏輯抽成 `services.py` 裡的一般 Python 函式，view、admin、management command、未來的 DRF API 都能直接呼叫同一份邏輯，而且可以脫離 HTTP 直接單元測試。

**延伸**
- 本專案的分工：`models.py` 只定義資料長什麼樣（schema）；`services.py` 放「怎麼操作這些資料」（如 `generate_short_code`、`create_short_link`、`record_click`）；`views.py` 只負責「接 HTTP 請求、呼叫 service、回 HTTP 回應」，盡量不直接寫業務規則。
- 這不是 Django 官方強制規範（Django 預設鼓勵 fat model），是業界常見的進階慣例，目的是關注點分離（separation of concerns）。

### B2. `@login_required` 裝飾器在背後做了什麼？

**簡答**
它包住一個 view 函式，在真正執行 view 之前先檢查 `request.user.is_authenticated`。如果沒登入，直接把使用者導去 `settings.LOGIN_URL`（並在網址帶上 `?next=原本想去的頁面`），等登入成功後 `django.contrib.auth` 內建的登入流程會讀這個 `next` 參數，自動轉回使用者原本想去的頁面。

**延伸**
- 對應地，class-based view 有 `LoginRequiredMixin`；DRF（Stage 6）會用 `permission_classes = [IsAuthenticated]` 達到類似效果。
- 沒設定 `LOGIN_URL` 時 Django 預設找 `/accounts/login/`，剛好是 `django.contrib.auth.urls` 內建提供的路徑，這也是為什麼很多教學不特別設定它也能動。

### B3. `annotate()` 和 `prefetch_related()` 各解決什麼問題？

**簡答**
兩個都是為了**避免在迴圈裡對資料庫發出 N+1 次查詢**，但解決的層面不同：`annotate(click_count=Count("clicks"))` 是在**同一條 SQL** 裡用 `JOIN + GROUP BY` 順手算出聚合數字（如每條短網址的點擊數），不用每條另外查一次「這條有幾個點擊」；`prefetch_related("clicks")` 是「**多查一次、但只查一次**」，把所有相關的 `Click` 物件一次撈出來放進記憶體，之後在 Python 迴圈裡存取 `link.clicks.all()` 不會再觸發新的資料庫查詢。

**延伸**
- N+1 問題：如果列表頁有 N 條短網址，迴圈裡對每條都呼叫 `link.clicks.count()` 或 `link.clicks.all()`，會各自觸發一次資料庫查詢，總共 N+1 次（1 次查列表 + N 次查各自的點擊）。`annotate`/`prefetch_related` 都是把多次查詢壓縮成固定的 1～2 次。
- `select_related`（用於 `ForeignKey`/`OneToOne`，走 SQL JOIN）跟 `prefetch_related`（用於反向 FK 或 ManyToMany，背後是分開查詢再用 Python 組裝）的差別也是常見追問點。

---

## C. 資料庫與 SQL

### C1. `unique=True` 為什麼能讓重導變快？它跟「索引」的關係是什麼？

**簡答**
在資料庫裡幫一個欄位加 `unique=True`，Django/資料庫會自動在這個欄位上建一個**唯一索引（unique index）**。索引讓資料庫不用整張表逐筆比對（全表掃描，O(n)）就能找到一筆資料，而是像查字典一樣直接定位（接近 O(log n)）。`ShortLink.short_code` 是重導這個熱路徑（hot path）唯一查詢條件，沒有索引的話，短網址表一旦變大，每次重導都要掃過全表比對字串，會越來越慢。

**延伸**
- `unique=True` 同時做了兩件事：「資料完整性約束」（不允許兩條短網址撞同一個 code）+「自動建索引」（查詢加速），這也是為什麼短碼產生服務要在寫入前先檢查碰撞——不然 `unique` 約束會讓資料庫直接報錯。
- 本專案另一個複合索引是 `Click` 的 `(link, created_at)`：因為儀表板查詢的型態固定是「給一條 link，依時間排序拿最近幾筆點擊」，複合索引讓這個查詢一次用到兩個欄位的順序，比各自建單欄索引更有效率。

---

## D. 部署與 GCP

### D1. 健康檢查端點為什麼叫 `/livez`？那個 z 是什麼？為什麼不叫 `/healthz`？

**簡答**
`z` 結尾源自 Google 的命名慣例（z-pages，如 `/healthz`、`/statusz`、`/varz`）。加 `z` 是為了**避免和真實業務網址撞名**，一看就知道是「給系統/機器用的內部診斷端點」。Kubernetes 後來把舊版語意模糊的 `/healthz` 拆成更精確的 `/livez`（存活檢查）跟 `/readyz`（就緒檢查），這個專案選用較新、較精確的 `/livez`。

**延伸**
- 健康檢查端點應**輕量、不依賴資料庫/外部服務**，否則某個依賴慢就會讓健康檢查誤判服務掛掉。
- k8s 區分 **liveness（還活著嗎？掛了就重啟）** 與 **readiness（準備好接流量了嗎？沒好就先別導流量進來）**，分別對應 `/livez`、`/readyz`。
- 實際部署到 Cloud Run 後踩到一個坑：Cloud Run 在共用的 `*.run.app` 網域上把完全比對 `/healthz` 這個路徑保留給自己內部使用，不會轉送到使用者的容器——即使程式裡定義了這個路由，外部請求一樣會被攔在外層回一個 Google 自己的通用 404，跟程式或部署設定無關。這是把端點改名成 `/livez` 的直接原因，排查過程跟決策見 [`docs/adr/0006-livez-not-healthz.md`](adr/0006-livez-not-healthz.md)。

---

## E. 系統設計（縮網址）

### E1. 短碼怎麼設計？為什麼不用自增 ID 轉 base62 或對網址做 hash？

**簡答**
採用「隨機 base62 + unique 檢查 + 碰撞重試」：用密碼學安全的隨機數產生器（`secrets`）隨機取樣 7 個字元，寫入前檢查資料庫有沒有撞號，撞到就重抽。否決自增 ID 轉 base62 是因為**可被列舉**（依序造訪 `/1`、`/2`…就能爬出全站短網址與使用量規模）；否決對網址做 hash 是因為**會碰撞**，且**無法讓不同使用者對同一個網址各自擁有不同短碼**。完整推理見 [`docs/adr/0001-short-code-generation.md`](adr/0001-short-code-generation.md)。

**延伸**
- 7 碼 base62 ≈ 62⁷ ≈ 3.5 兆種組合，隨機碰撞機率極低，重試上限設 5 次，超過視為異常直接拋例外而不是默默無限重試。
- 用 `secrets` 而非 `random` 的關鍵差異：`random` 的演算法可被預測（知道種子或夠多輸出能推算後續值），`secrets` 是密碼學安全的隨機來源，避免短碼被有心人猜出。

### E2. 重導為什麼用 302 而不是 301？

**簡答**
301（永久重導）會被瀏覽器**快取在本機**，使用者第一次點擊後，之後同一台裝置上的點擊**不會再發請求到我們的伺服器**，點擊數會被嚴重低估。302（暫時重導）則確保每次點擊都重新打到伺服器，由伺服器決定要跳去哪裡，這樣 `Click` 紀錄才不會漏記。完整推理見 [`docs/adr/0002-redirect-302-not-301.md`](adr/0002-redirect-302-not-301.md)。

**延伸**
- 代價是每次點擊都要打到伺服器、查一次資料庫，這是 Stage 4 要引入 Redis cache-aside 快取重導的原因——cache-aside 解決的是「伺服器內部查資料庫」的延遲，跟 301/302 解決的「瀏覽器到伺服器要不要發請求」是兩個不同層面的問題，不能混為一談（不能說「為了效能改用 301」，那會犧牲數據正確性）。

### E3. 來源 IP 怎麼解析？`X-Forwarded-For` 為什麼不能直接信任？

**簡答**
先檢查 `X-Forwarded-For` 標頭（反向代理寫入的真實使用者 IP），沒有才退回 Django 預設的 `REMOTE_ADDR`（直接跟伺服器建立連線的那一方）。本機開發沒有反向代理，這個標頭通常不存在，會自然退回 `REMOTE_ADDR`。`X-Forwarded-For` 之所以不能無條件信任，是因為它只是個普通 HTTP 標頭，**任何客戶端都可以自己塞假值**；只有在「請求一定會經過我們信任的反向代理，且代理會覆寫掉用戶端自己塞的值」的部署環境下（如 Stage 3 的 Cloud Run），這個標頭才可信。完整推理見 [`docs/adr/0003-client-ip-parsing.md`](adr/0003-client-ip-parsing.md)。

**延伸**
- 嚴謹的做法應該明確指定「只信任反向代理鏈中特定位置寫入的值」，避免客戶端在自己這端塞多層偽造 IP 來混淆。`django-ipware` 這類套件會處理這些邊界情況，Stage 8 打磨階段可以考慮換上。
- 這題也是「分散式系統裡，誰是可信邊界（trust boundary）」這個更大概念的具體案例：信任一個值之前，要先確認它是從哪個元件寫入的，而不是看標頭名稱就直接信。

---

## F. 認證與 OAuth（Stage 2：django-allauth）

### F1. 為什麼用 django-allauth 而不是自己寫 OAuth？

**簡答**
OAuth 流程本身不難理解，但細節容易做錯且後果是安全漏洞：CSRF/state 參數防護、token 過期重新整理、第一次社群登入要不要自動建立帳號、email 相同時要不要自動關聯到既有帳號等。這些都應該交給一個被大量專案驗證、持續維護安全更新的套件，而不是自己重新實作——這本身就是一個「資深判斷」：知道什麼該自己寫、什麼該用經驗證的工具。

**延伸**
- `django-allauth` 是 Django 生態圈最主流的認證套件，同時支援傳統帳密登入與一大堆第三方供應商（Google/Facebook/GitHub…）的社群登入，介面統一。

### F2. 「核心邏輯跟登入方式解耦」具體是怎麼做到的？

**簡答**
`apps/shortener`、`apps/analytics` 從頭到尾只依賴 `request.user`（一個 Django `User` 物件）跟 `@login_required`，完全不知道、也不需要知道這個使用者是用「帳號密碼」還是「Google/Facebook」登入的。Stage 1 用 `django.contrib.auth.urls` 提供登入頁，Stage 2 換成 `include("allauth.urls")`——只有 `config/urls.py`、`config/settings/base.py`（`AUTHENTICATION_BACKENDS`、`INSTALLED_APPS`）跟模板裡的 URL name 需要改，`shortener`/`analytics` 的 model、service、view 一行都沒動。

**延伸**
- 這跟「依賴抽象，不依賴實作」是同一個設計原則：上層程式碼（shortener）依賴的是 `request.user` 這個抽象介面，不是「使用者怎麼登入」這個實作細節，所以實作細節（登入方式）可以自由替換。

### F3. 為什麼 OAuth 憑證放環境變數，不是存進資料庫（`SocialApp` 表）？

**簡答**
延續專案一開始就定下的 12-factor 原則：`SECRET_KEY`、`DATABASE_URL` 都已經是「環境變數 → settings」這條路徑。allauth 0.48.0 之後支援直接在 `SOCIALACCOUNT_PROVIDERS["<provider>"]["APPS"]` 設定憑證，不再強制要求 `django.contrib.sites` 與資料庫裡的 `SocialApp` 紀錄，少一層設定、部署到 Cloud Run 後憑證直接走 Secret Manager 就好，不用多寫一支「上 admin 手動填表」的部署步驟。完整推理見 [`docs/adr/0004-social-login-credentials.md`](adr/0004-social-login-credentials.md)。

**延伸**
- 設定裡的 `_oauth_app()` helper 在憑證缺漏時回傳空列表 `[]`，不是回傳一筆空字串的假 app。原因是 allauth 用「這個 provider 有沒有至少一個 app」判斷登入頁要不要顯示對應按鈕；回傳 `[]` 才能讓「沒填憑證」跟「使用者完全看不到這個按鈕」保持一致，避免出現一個點下去註定失敗的按鈕。

### F4. `AUTHENTICATION_BACKENDS` 裡兩個 backend 分別負責什麼？

**簡答**
`django.contrib.auth.backends.ModelBackend` 負責傳統「使用者名稱 + 密碼」登入（Django admin、Stage 1 的帳號都靠它）；`allauth.account.auth_backends.AuthenticationBackend` 負責 allauth 自己的登入流程，包含把社群登入回來的身分對應回資料庫裡的 `User`。Django 會依序詢問列表裡的每個 backend，第一個成功驗證的就採用——兩條登入路徑最終都產生同一種 `User` 物件，下游程式碼不用區分。
