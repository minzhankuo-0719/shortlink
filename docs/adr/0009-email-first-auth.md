# ADR 0009 — Email-first 登入入口、跨 provider 自動連結、與 unique-email 不變量

## 背景

Stage 3 完成後做登入頁打磨時，作者希望登入體驗更像 OpenAI/ChatGPT：**先只填 email，再依這個 email
是否已註冊，決定要登入還是註冊**（identifier-first / email-first）。這牽動了帳號識別與連結的一連串決策，
集中記錄於本 ADR。

## 決策

### 1. Email-first 入口（`apps/accounts`）

新增 `apps/accounts`，把登入「正門」改成單一 email 欄位的 entrance 頁（`/accounts/start/`，`LOGIN_URL`
指向它）：

- 送出 email 後，`entrance` view 判斷這個 email 屬於哪種情況再轉址：
  - **沒註冊過** → allauth 的 `account_signup`（email 由 allauth 的 `SignupView.get_initial` 自動預填）
  - **已註冊、有密碼** → allauth 的 `account_login`（我們用 `PrefillLoginView` 子類把 email 預填進 login 欄位）
  - **已註冊、純社群帳號（沒密碼）** → 自訂的 social-only 引導頁（見第 3 點）
- 實際的認證與建檔仍交給 allauth；`apps/accounts` 只負責「把使用者導到對的 allauth 頁面」，不自刻登入邏輯。

**取捨（user enumeration）**：依「email 是否存在」分流，等於對外洩漏某 email 有沒有註冊。這是這種 UX 本質上
的代價（OpenAI 也一樣），靠 allauth 內建的 login/signup rate limiting 緩解。

### 2. 跨 provider 自動連結（verified email）

```python
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
```

allauth 預設**不**自動合併不同 provider 的同 email 帳號（安全考量）。我們開啟：當一個社群登入帶著
**已驗證**的 email、而這 email 已屬於某個既有帳號時，直接登入該帳號並把新 provider 連上去。前提是
Google/Facebook 都會驗證 email，「同已驗證 email == 同一人」這個信任才成立。已實測：用 Google 登入一個
原本只有 Facebook 的 email，會連到同一個帳號（不會多出第三個帳號）。

### 3. Facebook `VERIFIED_EMAIL: True`

allauth 的 Facebook provider 在 `extract_email_addresses` 把 email 寫死成 `verified=False`，因為 Graph
API 的 `verified` 欄位指的是「**帳號**有沒有驗證」，不是「**這個 email** 有沒有驗證」，API 沒有可信的 per-email
驗證訊號。我們在 provider 設定加 `"VERIFIED_EMAIL": True` 明確選擇信任 Facebook 的 email，這樣第 2 點的自動
連結在 Facebook 方向也能成立。生效路徑：`SocialAccountAdapter.is_email_verified()` → `cleanup_email_addresses()`
裡的「force verified」迴圈會把它升級成 `verified=True`。對比 Google 走 OpenID Connect、本來就帶 per-email
的 `email_verified` 宣告，所以 Google 預設就是 verified。

### 4. 純社群帳號的引導頁（social-only）

純社群（沒密碼）帳號若被導到密碼登入頁，使用者永遠填不出對的密碼。所以 entrance 偵測到「有帳號、但
`has_usable_password()` 為 False、且有連結的 social provider」時，改導到 `/accounts/continue/`
（`account_social_only`），只顯示該帳號實際用過的 provider 的「Continue with Google／Facebook」按鈕，不給
死的密碼框。

### 5. 修掉被吃掉的表單層級錯誤

我們自訂的 `templates/allauth/elements/fields.html` 是用 `for bound_field in form` 逐欄位渲染，這會**跳過
表單層級（non-field）錯誤**——allauth 的「帳號或密碼不正確」就是 non-field error，導致登入失敗時畫面毫無
反應。已在該檔最上方補上 `form.non_field_errors` 的渲染。（allauth 預設的 `fields.html` 是 `{{ form.as_p }}`，
本來就含 non-field errors；我們客製成逐欄位渲染時漏掉了。）

## 為什麼這樣是對的（unique-email 不變量）

身分的主鍵是**不會變的 `(provider, uid)`，不是可變的 email**。allauth 的查找順序（`SocialLogin.lookup`）：
先用 `(provider, uid)` 找既有 SocialAccount，**找不到才**用已驗證 email 找。所以：

- 自動連結只發生在「某 provider 的 uid **第一次**出現、且帶著對到既有帳號的已驗證 email」那一瞬間。uid 一旦
  綁定，之後 email 怎麼變都**不會回溯改綁**——這正是防帳號接管的安全性質（否則有人把自己的 provider email
  改成你的就能併進你的帳號）。

我們**保留 `ACCOUNT_UNIQUE_EMAIL=True`**（unique 作用在 `EmailAddress` 表）。這帶來一個關鍵不變量：
**一個 email 當作 `EmailAddress` 全庫最多一筆，只屬於一個帳號**。因此：

- 「兩個獨立帳號都綁同一個 email」在資料層建不出來：先擁有者之外，其他帳號要登記同一個 email 會撞唯一約束。
- 之後再接 Apple/GitHub 等任何 provider，用已驗證 email A 登入時，`filter_users_by_email` 先查 `EmailAddress`
  （unique → 至多一個擁有者），命中已驗證的那筆後**會跳過掃描 `User.email` 欄位的後備步驟**，所以結果收斂到
  唯一帳號，**不會有「要連哪一個」的歧義**。
- 只要守住 unique email，「email → 唯一帳號」這個不變量對 N 個 provider 都成立。

（殘角：`UNIQUE_EMAIL` 管不到 Django `User.email` 欄位本身；但只要有已驗證的 `EmailAddress` 命中就會跳過該
欄位掃描，實務上仍收斂到單一帳號。要徹底加固可另對 `User.email` 加唯一約束 / 確保帳號都經 allauth 建立。）

## 已知限制與後續工作

- **uid 先綁定、email 後變動** 的情況不會自動合併（例如：FB 帳號在還沒對到某 email 時就先建檔，之後才補上
  跟別人撞的 email）。這是刻意的安全行為，正解是**由本人發起的明確連結**：登入既有帳號後到 allauth 內建的
  `socialaccount_connections`（`/accounts/social/connections/`）主動把 provider 連上。
- **後續構想（尚未實作，已記在專案記憶）**：
  1. 把第 2 點的「靜默自動連結」改成**先詢問**「是否把這個 provider 連到同 email 的既有帳號」（雙向）。注意
     「拒絕就另開獨立同 email 帳號」與 unique email 衝突——維持 unique email 的話，拒絕只能是「取消」。
  2. 主頁/帳號頁加「管理已連結帳號」入口，指向 `socialaccount_connections`。

## 影響

- 登入正門從 allauth 的 `account_login` 換成 `account_entrance`；`account_login` 仍存在（被 `PrefillLoginView`
  接管同一路徑），allauth 內部與 `@login_required` 的轉址行為不受影響。
- 新增依賴的 allauth 行為設定都集中在 `config/settings/base.py` 的 auth 區塊，並在註解標明前提與本 ADR。
