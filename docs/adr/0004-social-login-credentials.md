# ADR 0004 — OAuth 憑證放環境變數，不用 SocialApp 資料表

## 決策

Google/Facebook 的 `client_id`/`secret` 透過 `config/settings/base.py` 的 `SOCIALACCOUNT_PROVIDERS["<provider>"]["APPS"]` 從環境變數讀入，**不**使用 allauth 較舊版本常見的「在 Django admin 建一筆 `SocialApp` 資料表紀錄」的做法。

`_oauth_app()` helper 在 `client_id`/`secret` 任一缺漏時回傳空列表 `[]`，而不是塞一筆 `client_id=""` 的假紀錄。

## 為什麼

1. **跟現有的 12-factor 設定模式一致**：`SECRET_KEY`、`DATABASE_URL` 都已經是「環境變數 → `django-environ` → settings」這條路徑，OAuth 憑證沒道理換一套機制（存資料庫），這樣 prod 上 Cloud Run 時只要照樣放進 Secret Manager 即可，不需要額外寫一支「部署後手動上 admin 填表」的步驟。
2. **不需要 `django.contrib.sites`**：allauth 0.48.0 之後，只要走 `SOCIALACCOUNT_PROVIDERS` 設定式的 `APPS`，就不強制要求啟用 sites framework 與設定 `SITE_ID`（這是舊版教學常見、但現在已经是選配的複雜度，省下不用）。
3. **「未設定 = 完全不显示該按鈕」必須是真的沒有 app，而不是空字串的 app**：allauth 用 `get_providers()` 決定要不要在登入頁渲染某個 provider 的按鈕，判斷依據是「這個 provider 有沒有至少一個 app」。如果我們無條件塞一筆 `{"client_id": "", "secret": ""}`，技術上「有 app」，按鈕會出現，但點下去就會在 OAuth 那一步失敗（因為 Google/Facebook 收到空的 client_id）。所以 `_oauth_app()` 故意在憑證不齊時回傳 `[]`，讓「沒填憑證」跟「这個 provider 不存在」的行為完全一致：登入頁就只剩使用者名稱/密碼登入，不會出现一個會壞掉的按鈕。

## 影響

- 在拿到真的 Google/Facebook OAuth 憑證之前，整個登入流程（含 Stage 1 的帳號密碼登入）都正常運作，不會因為 Stage 2 的設定而壞掉。
- 之後只要把四個環境變數（`GOOGLE_OAUTH_CLIENT_ID`/`SECRET`、`FACEBOOK_OAUTH_CLIENT_ID`/`SECRET`）填進 `.env`，重啟伺服器，對應的登入按鈕就會自動出現，**不需要改任何程式碼**。
