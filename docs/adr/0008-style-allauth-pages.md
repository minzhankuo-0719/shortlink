# ADR 0008 — 用 allauth 的 element/layout 機制套用 Tailwind 樣式，不逐頁改範本

## 決策

不去複寫 `account/login.html`、`account/signup.html`、`account/logout.html` 等每一個 allauth 頁面範本，
而是只蓋掉兩種檔案：

1. **`templates/allauth/layouts/base.html`**：讓所有 allauth 頁面改成繼承我們專案的 `templates/base.html`
   外框（同一套 nav/Tailwind CDN），而不是 allauth 套件內建的空白外框
2. **`templates/allauth/elements/*.html`**（`h1`/`h2`/`p`/`form`/`field`/`fields`/`button`/`button_group`/
   `hr`/`alert`/`provider`/`provider_list`）：allauth 用一套叫 `{% element %}`/`{% slot %}` 的標籤系統把
   「標題」「按鈕」「輸入框」這些 UI 元件抽成獨立小範本，目的就是讓套件本身不綁定任何 CSS 框架，專案只要
   蓋掉這些小範本，就能讓**所有** allauth 頁面（登入、註冊、登出、忘記密碼、社群帳號管理…）一次套用同一套
   樣式，不需要逐頁複製貼上

Tailwind class 沿用既有頁面（`templates/shortener/create.html`、`apps/shortener/forms.py`）已經用的
那組（`border rounded px-3 py-2 w-full` 輸入框、`bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700`
主要按鈕），不是另外設計一套新樣式。

## 為什麼

1. **改動面積小、維護成本低**：allauth 套件本身有十幾個頁面範本（login/signup/logout/password_reset/
   password_change/email 管理/社群帳號連結…），逐一複寫每個頁面範本，等於每次 allauth 升級新增頁面
   （例如他們陸續加的 passkey、MFA 相關頁面）都要記得跟著新增一份複寫版；蓋掉 layout + elements 這兩層，
   新頁面只要用到既有的 `{% element %}` 標籤，會**自動**套用我們的樣式，不用額外維護
2. **這是 allauth 官方文件記載、支援的客製化機制**（用 Context7 拉了 `django-allauth` 最新文件確認），
   不是繞過套件設計的 hack
3. **不引入新的 CSS 框架**：繼續用專案已經選定的 Tailwind CDN 版，跟 CLAUDE.md 技術選型一致

## 實作上的兩個技術細節（容易踩雷，記錄下來）

1. **`{% block %}` 標籤不能跨行重複使用同一個名字**：一開始想在 `templates/allauth/layouts/base.html`
   裡同時「包一層 wrapper 顯示 Django 訊息」又「保留一個 `content` 區塊給 `login.html` 等頁面填」，
   兩者都叫 `content` 會讓 Django 在解析模板時直接報錯（同一個檔案裡不能有兩個同名 `{% block %}`，
   不管是否巢狀）。更根本的原因是 `login.html` 覆寫 `content` 區塊時**沒有呼叫 `{{ block.super }}`**，
   代表任何寫在我們自己 `content` 覆寫版裡的內容都會被整個丟棄——所以「顯示 Django 訊息」這件事改放到
   真正的根模板 `templates/base.html`（它沒有 `{% extends %}`，裡面除了 block 以外的內容都會正常渲染，
   不會被任何子模板覆蓋掉），讓首頁、建立短網址、登入頁全部共用同一套訊息顯示邏輯，而不是只有 allauth
   頁面才有
2. **Django 模板標籤不能跨行**：`{% ... %}` 標籤內部如果包含真的換行字元，Django 的 tokenizer（用來
   切出 `{% %}` 區塊的正規表達式）找不到同一個標籤的結束符號，會直接讓整個標籤解析失敗、報出語意上完全
   無關的錯誤（例如「不認識 `endelement` 這個標籤」）。一開始為了好讀把 `{% element field
   unlabeled=... name=... ... %}` 這種長標籤拆成多行，整個壞掉；改成全部擠在一行才正常。

## 影響

- 之後如果要從 Tailwind CDN 換成 daisyUI（作者表達過的意向：先用 Tailwind，之後想換可以全部換成
  daisyUI），改動範圍就是這幾個 `allauth/elements/*.html` 加上 `templates/base.html`/各頁面既有的
  class，因為 daisyUI 本身是疊在 Tailwind 上的元件庫（提供 `btn`/`input`/`card` 這類語意化 class），
  不需要重新設計頁面結構
- 新增 allauth 頁面（例如之後要做密碼修改、社群帳號管理介面）幾乎不需要額外造型工作，會自動套用這裡
  定義的樣式
