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

---

## B. Django

_（待補）_

---

## C. 資料庫與 SQL

_（待補）_

---

## D. 部署與 GCP

### D1. 健康檢查端點為什麼叫 `/healthz`？那個 z 是什麼？

**簡答**
這是源自 Google 的命名慣例（z-pages，如 `/healthz`、`/statusz`、`/varz`）。結尾加 `z` 是為了**避免和真實業務網址撞名**，一看就知道是「給系統/機器用的內部診斷端點」。Kubernetes 把它標準化成 `/healthz`（存活）、`/readyz`（就緒），現在是雲端原生的通用慣例。

**延伸**
- 健康檢查端點應**輕量、不依賴資料庫/外部服務**，否則某個依賴慢就會讓健康檢查誤判服務掛掉。
- k8s 區分 **liveness（還活著嗎？掛了就重啟）** 與 **readiness（準備好接流量了嗎？沒好就先別導流量進來）**，分別對應 `/livez`、`/readyz`。
- Cloud Run 也會用健康檢查決定要不要把這個容器實例列為可用。

---

## E. 系統設計（縮網址）

_（待補）_
