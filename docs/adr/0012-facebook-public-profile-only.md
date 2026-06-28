# ADR 0012 — Facebook 對外登入的取捨：嘗試 public_profile-only，因 Meta 要求商家驗證而退回 email + 測試者

**狀態：已探索並退回。** 最終採用：Facebook 維持 `email` + `public_profile` + 開發模式 + 測試者名單；
「任何人都能登入」改由 **Google** 承擔（OAuth 同意畫面已發布成 In production）。本 ADR 保留下來，是為了記錄
這段探索與「Meta 要求商家驗證才能 go Live」這個關鍵發現。

## 背景

想讓**任何人**（朋友、面試官）都能用 Facebook 登入，而**不做商家驗證 (Business Verification, BV)**。
先前的卡關點是 `email`：它的進階存取 (Advanced Access) 要求 BV。而 `public_profile` 預設就有進階存取、免 BV。
直覺的解法因此是：**只請求 `public_profile`、丟掉 `email`**，就能免 BV 把 App 切 Live。

## 嘗試過的方案（已實作、已部署、已本機驗證）

1. `config/settings/base.py`：Facebook `SCOPE` 改成只剩 `["public_profile"]`、移除已失去意義的 `VERIFIED_EMAIL`。
2. 加 `SOCIALACCOUNT_EMAIL_REQUIRED = False`（搭配預設的 `SOCIALACCOUNT_AUTO_SIGNUP=True`）：讓「FB 沒給 email」
   的全新使用者**自動建帳號、不卡在 allauth 的「請補 email」中間頁**。規則來源以 Context7 查 allauth 65 文件確認。
3. `templates/core/privacy.html`：文案改成「Facebook 只取得姓名」。

部署為 revision `shortlink-00012-572`，本機真人驗證：FB 同意畫面確實只剩「姓名和大頭照」、登入無 email 中間頁、
直接進儀表板。**機制本身可運作。**

## 關鍵發現：Meta 現在「發佈 (go Live)」這步本身就要商家驗證

實際到 Meta 後台要切 Live 時發現，**本 ADR 原本的前提「public_profile 免 BV 即可 go Live」已經過時**：

- 新版後台「發佈」頁把 **商家驗證** 列為發佈的必要條件，`public_profile` only 也照擋；「發佈」鈕為灰、
  提示「由於未完成所有要求，因此無法發佈這款應用程式」。
- 把 use case 裡的 `email` 移除、把卡片上掛的未驗證商家也「移除」——商家驗證要求**依舊存在**。
- 結論：**BV 這道牆已從「`email` 進階存取」往前挪到「發佈」這個動作本身**。丟掉 email 對「對外全開」
  **毫無幫助**；不做 BV 的話，Facebook 無論如何都只能給測試者用。

## 決策：退回 email + 測試者，「任何人」交給 Google

- **還原 Facebook 為 `email` + `public_profile`**（程式碼退回 email-based）。理由：反正 BV 卡死、FB 只能測試者用，
  那留著 email 是**純賺**——把 ADR 0009 的「同已驗證 email 跨 provider 自動連結」這個亮點留住，零代價。
- **Facebook 維持開發模式 + 測試者名單**：要讓特定人（面試官）登入，就把對方加進「應用程式角色 → 測試人員」
  （用對方個人檔案網址裡的 username，非中文名字；對方需有免費 FB 開發者帳號並接受邀請）。
- **「任何人都能登入」改由 Google**：Google 的 `profile`+`email` 屬**非敏感範圍**，**不需要**商家/企業驗證即可把
  OAuth 同意畫面**發布成 In production**，任何 Google 帳號皆可登入（非敏感範圍無 100 人上限、不跳「未驗證應用程式」）。

## 影響

- 程式碼退回 email-based（探索分支未併入 main、已捨棄；唯一保留物是本 ADR）。線上 revision `shortlink-00013-7t8`。
- Google OAuth 同意畫面為 **In production**（勿退回 Testing，那是對外開放的命脈）。
- **符合作業需求**：題目要 Google + Facebook 登入皆可用——Google 對所有人可用、Facebook 對測試者可用，
  兩個 provider 都 work；三項功能（建立短網址、重導、看自己短網址的點擊成效與來源 IP）都吃 `request.user`，
  與是否拿到 email 無關。

## 學到的事（面試素材）

- Meta 近年收緊：**任何使用 Facebook 登入的 App，要 go Live 一律要商家驗證**，與請求的權限範圍無關；
  「public_profile 自動進階存取、所以免驗證即可上線」這個舊認知已不成立。
- 對「個人/求職作品」這種規模，正確取捨是**用 Google 撐起對外開放、Facebook 以測試者展示**，而不是為了一個
  email 欄位去做商家驗證。
