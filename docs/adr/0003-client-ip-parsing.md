# ADR 0003 — 來源 IP 解析：優先讀 X-Forwarded-For

## 決策

`apps/analytics/services.py` 的 `get_client_ip(request)` 先檢查 `X-Forwarded-For` 標頭（取第一段），沒有才退回 Django 預設的 `REMOTE_ADDR`。

## 為什麼

`REMOTE_ADDR` 是 Django 看到的「直接跟它建立 TCP 連線的那一方」的 IP。本機開發時這就是真正的使用者 IP（沒有任何中間層），所以 `REMOTE_ADDR` 夠用。

但 Stage 3 上線後，服務會跑在 **Cloud Run** 上，使用者的請求是先打到 Google 的反向代理/負載平衡器，代理再轉發給我們的容器——這時 `REMOTE_ADDR` 看到的會是**代理伺服器的 IP**，不是使用者的 IP。反向代理會把「它收到的真實來源 IP」寫進 `X-Forwarded-For` 這個標頭再轉發過來，所以正式環境要看這個標頭才能拿到使用者的真實 IP。

現在（Stage 1，還沒上線）就把這個邏輯寫好，是為了：
1. Stage 3 部署時**不用再回頭改 `analytics` 的程式碼**，核心邏輯已經是正確的。
2. 提前在程式碼裡留一個清楚的註解/ADR，標明「這個欄位的正確性，取決於部署環境有沒有可信的反向代理」。

## 安全考量（重要，否則這個欄位形同造假）

`X-Forwarded-For` 是一個**普通的 HTTP 標頭**，任何客戶端都可以在發請求時自己塞一個假值進去（例如 `curl -H "X-Forwarded-For: 1.2.3.4"`）。

- **本機開發 / Stage 1**：我們前面沒有反向代理，所以 Django 直接面對外部請求——這時如果信任 `X-Forwarded-For`，等於信任使用者自己宣稱的 IP，**完全可以偽造**，因此本機環境這個標頭多半不存在，函式會自然退回 `REMOTE_ADDR`（也就是 `127.0.0.1`）。
- **Stage 3 上 Cloud Run 後**：Cloud Run 的反向代理會在轉發請求前，**覆寫/清除**用戶端自己塞的 `X-Forwarded-For`，換成它自己量到的真實來源 IP，所以這個標頭在那個環境下才是可信的。
- 結論：`X-Forwarded-For` 可不可信，**完全取決於它是不是由「我們信任的反向代理」寫入的**，不是這個標頭本身有什麼特殊性質。日後如果要更嚴謹，應該用 `django-ipware` 之類的套件，或明確設定「只信任反向代理寫在標頭最後一段的值」，避免使用者在自己這端硬塞多層偽造 IP。Stage 1 先求邏輯正確、有文件留痕，嚴謹的多層代理鏈處理留給 Stage 8 打磨。
