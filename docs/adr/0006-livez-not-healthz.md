# ADR 0006 — 健康檢查端點改名 `/livez`，不用 `/healthz`

## 決策

把健康檢查端點從 `/healthz` 改名為 `/livez`，沿用 Kubernetes 現代慣例裡專指「存活檢查」的命名
（k8s 後來把舊版合併語意的 `/healthz` 拆成 `/livez`（存活）跟 `/readyz`（就緒）兩個更精確的端點）。

## 為什麼

部署到 Cloud Run 後實測發現：用 `curl https://<服務>.run.app/healthz` 一直收到一個帶 Google 機器人
圖案的通用 404 頁面，但同一個服務的其他路徑（`/`、`/links/`）都正常。逐步排查（檢查 IAM、ingress、
容器日誌、revision 設定、`gcloud run services proxy`、Cloud Run 請求層級日誌）後確認：

- `/` 與 `/links/` 的請求都能在 Cloud Run 的請求日誌裡查到，回應帶 `server: Google Frontend` 與
  `x-cloud-trace-context` 標頭，代表請求真的進到 Cloud Run、被我們的容器處理
- `/healthz`（不帶斜線）的請求**完全沒有出現在 Cloud Run 的請求日誌裡**，且回應沒有上述兩個標頭
- 改成 `/healthz/`（帶斜線）测試,請求就能進到容器（拿到我們 Django 自己回的 404,因為 urlconf 沒
  定義帶斜線的版本)，證實只有「完全比對 `/healthz`」這個精確路徑被攔截

結論：Cloud Run（或它前面的 Google Front End）在共用的 `*.run.app` 網域上,把 `/healthz` 這個精確
路徑保留給自己內部的健康檢查機制用，不會轉送到使用者的容器，無論程式裡有沒有定義這個路由。這跟我們
的程式碼或部署設定都無關，是平台層級的保留字。

選 `/livez` 而不是隨便挑一個避開衝突的名字：
1. **跟既有的 z-pages/k8s 慣例敘事一致，甚至更精確**：[`docs/learning-log.md`](../learning-log.md)
   跟 [`docs/interview-qa.md`](../interview-qa.md) 本來就有一段「為什麼叫 `healthz`，那個 z 是什麼」
   的說明,提到 Kubernetes 把它標準化成 `/healthz`、`/livez`、`/readyz`。改用 `/livez` 不是為了繞過
   問題硬改名,而是換成這組慣例裡語意更明確、且不會撞到 Cloud Run 保留字的那一個
2. 這個服務目前只需要「存活檢查」（容器活著、能回應就好),不需要「就緒檢查」（例如等資料庫連線池
   warm up 才回 ready）那種更複雜的語意,`/livez` 完全夠用，不需要額外做 `/readyz`

## 影響

- `apps/core/urls.py`、`apps/core/views.py` 的路由與 view 名稱從 `healthz` 改成 `livez`
- 之後若綁自訂網域（不是走共用的 `*.run.app`），這個保留字限制理論上不會存在,但既然 `/livez` 已經
  是更精確的命名,不需要再改回去
- README、CLAUDE.md、`docs/learning-log.md`、`docs/interview-qa.md` 裡所有 `/healthz` 的提及都同步
  改成 `/livez`
