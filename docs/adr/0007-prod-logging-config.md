# ADR 0007 — 正式環境必須額外設定 `LOGGING`，否則例外被靜默吞掉

## 決策

在 [`config/settings/prod.py`](../../config/settings/prod.py) 加一段 `LOGGING` 設定，把 root logger
接上一個單純的 `logging.StreamHandler`，等級 `INFO` 以上：

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

不額外引入 Sentry 之類的第三方錯誤追蹤服務。

## 為什麼

部署到 Cloud Run 後，首頁回應 500，但翻遍 Cloud Logging（包括 stdout/stderr 跟請求層級日誌）完全找不到
任何 Python traceback。原因是 Django 的預設 `LOGGING` 設定裡：

- 「印到 console」的 handler 帶了 `require_debug_true` 過濾器，只有 `DEBUG=True` 時才生效
- `DEBUG=False`（正式環境）時，改成用 `mail_admins`（寄信通知 `ADMINS`），但這個專案沒有設定
  `ADMINS`（沒有配置寄信用的 SMTP，也不需要），於是這個 handler 直接靜默跳過

兩個 handler 都不生效的結果是：**正式環境的未處理例外完全沒有任何輸出**，不是日誌系統故障，是 Django
的預設設計就是這樣（假設你會設定 `ADMINS` 收信，或自己接上其他 `LOGGING` 設定）。

選擇單純的 console handler 而非 Sentry/第三方錯誤追蹤服務：
1. **Cloud Run 自動把容器的 stdout/stderr 收進 Cloud Logging**，不需要額外的 agent 或 SDK，
   `StreamHandler` 印到 stderr 就會自動被收集、可查詢、可設告警規則
2. 這個專案的流量規模（面試 demo）不需要 Sentry 那種「自動分組相同錯誤、寄通知、追蹤趨勢」的進階功能，
   多裝一個第三方服務、多一組 API key 要管理，對目前規模是過度設計

## 影響

- 這個設定本身就間接幫忙抓到了一個真實的 bug：把健康檢查端點從 `healthz` 改名成 `livez` 時，
  漏改了 `templates/core/home.html` 裡的 `{% url 'core:healthz' %}`，造成首頁 500
  （`NoReverseMatch`）。加上這段 `LOGGING` 之後，traceback 才終於出現在 Cloud Logging 裡，
  幾秒鐘就定位到問題
- 之後如果流量成長到需要更主動的告警（不是「我自己去查日誌」而是「出事自動通知我」），可以在這個
  `LOGGING` 設定上加一個 Cloud Logging 的告警政策，或換成 Sentry，不需要動程式碼裡其他部分
