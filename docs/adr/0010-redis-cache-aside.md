# ADR 0010 — 重導熱路徑用 Redis cache-aside

## 背景

重導(造訪短網址)是本服務的熱路徑:一條連結建立一次,卻可能被點幾萬次。
原本每次重導都查一次資料庫把 `short_code` 換成 `original_url`(見
`apps/shortener/views.py` 的 `redirect_short_link`)。`original_url` 幾乎不會變,
卻被重複查上萬次——這是典型「讀多寫少、結果穩定」的快取場景。

## 決策

在重導的「解析」步驟前加一層 **cache-aside(旁路快取)**,後端用 Redis:

- 查快取 → 命中(hit)就直接用,不碰資料庫。
- 沒命中(miss)→ 查一次資料庫 → 把結果寫回快取 → 再用。

實作在 `apps/shortener/services.py` 的 `resolve_active_link()`,快取的值是
`(link_id, original_url)` 這個 tuple——只存重導真正需要的兩個值(id 用來寫點擊、
url 用來跳轉),而不是整個 model row:payload 更小,且命中時連「載入一個完整
ShortLink 物件」都省了。為配合這點,`record_click()` 改成收 `link_id` 而非
ShortLink 實例(Django 的外鍵可直接以 `link_id=<int>` 設定關聯)。

設定在 `config/settings/base.py` 的 `CACHES`,由 `REDIS_URL` 環境變數決定後端;
沒設時 fallback 成 process-local 的 `LocMemCache`,所以缺 Redis 也能 `runserver`——
cache-aside 的程式邏輯完全相同,只有後端不同。

## 失效(這層最關鍵)

快取是資料庫的副本,副本沒跟上就會給出**過期資料**。本服務用兩層保險:

1. **主動失效**:用 `post_save` / `post_delete` 訊號(`apps/shortener/signals.py`,
   在 `apps.py` 的 `ready()` 註冊),只要 ShortLink 被存檔或刪除——不管來自建立流程、
   未來的編輯／停用 view、Django admin、還是管理指令——就刪掉那個 `short_code` 的快取。
   把失效集中在訊號、而不是散在每個呼叫點,是為了「一個地方寫對,永遠不會在某個
   call site 漏掉」。
2. **TTL(1 小時)**:每筆快取設存活時間,萬一主動失效漏了,最多錯一小時就自我修正。

刻意**不做負快取**(不快取「查無此碼」的結果):404 在這裡很少見,省下負快取就免去
「之後這個碼被建立時要清掉那筆不存在記錄」的失效複雜度。

## 代價與取捨

- 多一個相依元件(Redis)與一條「資料庫↔快取可能不一致」的路徑;用主動失效 + TTL
  把不一致窗口壓到趨近於零、最差一小時。
- **已知限制**:`QuerySet.update()` 與 `bulk_create()` 會繞過 `.save()`,**不觸發訊號**,
  那類批次改動不會自動失效(只能等 TTL)。本專案的連結變更都走 `.save()` / `.delete()`
  (admin、表單),不受影響;若日後引入批次更新,需在該處手動呼叫 `invalidate_short_code()`。
- `LocMemCache` fallback 是 per-process、不跨實例共享,僅供本機無 Redis 時方便開發;
  正式環境一定要給 `REDIS_URL`,否則多個 Cloud Run 實例各有各的快取、命中率低、
  失效不跨實例。部署時應讓 `prod.py` 在缺 `REDIS_URL` 時啟動報錯,避免悄悄落回 LocMemCache。
- 與 ADR 0002(302 不用 301)互補:301 省的是「瀏覽器↔伺服器」的網路往返但會漏記
  點擊;cache-aside 省的是「伺服器↔資料庫」的查詢延遲又**不**犧牲點擊記錄。兩者解決
  不同層的成本。

## 驗證

用 Django 內建測試框架(獨立測試 DB + `CaptureQueriesContext`)確認:首次解析 = 1 次
DB 查詢、再次解析 = 0 次 DB 查詢;修改 URL 後訊號清快取、下次解析拿到新值;停用的連結
解析回 `None`(走 404)。

## 部署(實況)

prod Redis 選 **Upstash**(serverless、免 VPC connector、free tier、GCP 東京
`asia-northeast1`)。`rediss://` URL 放進 Secret Manager(`redis-url`),`gcloud run deploy
--update-secrets REDIS_URL=redis-url:latest` 帶入;`prod.py` 加 `REDIS_URL = env("REDIS_URL")`
(無 default)讓缺值時啟動即報錯,杜絕悄悄落回 LocMemCache。

**踩坑**:Dockerfile 在 build 階段跑 `collectstatic`,而它 import 的是 `config.settings.prod`。
prod 一旦多了「必填」的 `REDIS_URL`,build 就會因為環境沒這個變數而失敗(`ImproperlyConfigured`)。
解法是在那行 `collectstatic` 加一個佔位 `REDIS_URL=redis://placeholder:6379`(跟既有的
`SECRET_KEY`/`DATABASE_URL` 佔位同理)——collectstatic 不會真的連 Redis,佔位值也只存在於該行、
不留進 image,執行期仍由 Secret Manager 注入真值。**通則:prod 每新增一個必填環境變數,記得同步
更新 build-time 的佔位。**

線上以 Upstash 後台確認確實走真 Redis:`Writes` 來自「建立連結的失效 `DEL`」+「cache miss 的
`SET`」,`Reads` 來自「重導的 `GET`」+「redis-py 每條新連線的 handshake 指令」(Cloud Run scale-to-zero
後冷啟動會重開連線,故指令數不與「建幾條/點幾次」1:1 對應)。
