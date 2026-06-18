# ShortLink

縮網址服務（面試作品）。用 Django 建立，支援 Google / Facebook 登入，登入後可建立短網址、造訪短網址會被重導到原始連結，並可在儀表板看到自己每條短網址的點擊成效與來源 IP。

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

打開 http://127.0.0.1:8000 看首頁，http://127.0.0.1:8000/healthz 看健康檢查。

### 開發工具

```bash
uv run pre-commit install                 # 第一次 clone 後執行一次，裝 git commit hook
uv run ruff check . && uv run ruff format  # lint + 格式化
uv run pytest                              # 跑測試（Stage 5 後）
```

## 專案進度與文件

- [`CLAUDE.md`](CLAUDE.md)：單一事實來源，含目前進度、Roadmap、架構與關鍵決策
- [`docs/adr/`](docs/adr/)：重要技術決策（Architecture Decision Records）
- [`docs/learning-log.md`](docs/learning-log.md)：逐檔解說與學習筆記
- [`docs/interview-qa.md`](docs/interview-qa.md)：面試考點整理
