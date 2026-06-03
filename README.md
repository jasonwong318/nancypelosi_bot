# 免費市場報告 Telegram Bot

這是一個免費部署優先的 MVP：

1. GitHub Actions 按時間自動執行 Python。
2. Python 嘗試用 Longbridge OpenAPI 取得實時 quote。
3. Google News RSS 抓市場新聞。
4. Gemini API 免費層生成正體中文市場報告。
5. Telegram Bot API 發送到你的 chat。

## 我建議的部署選擇

首選：GitHub Actions。

原因：
- 你已經使用過 GitHub。
- 不需要 VPS 月費。
- Python SDK 最方便直接跑 Longbridge。
- 可以用 GitHub Secrets 保存 Telegram、Gemini、Longbridge token。

Cloudflare Workers 也可行，但免費層 CPU 限制較緊，而且 Python SDK / Longbridge SDK / 較長 LLM 請求不如 GitHub Actions 順手。Cloudflare 更適合之後做一個手動觸發 webhook，例如 `/report`。

## 需要準備的帳戶 / Token

必需：
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GEMINI_API_KEY`

Longbridge OpenAPI 批核後再加入：
- `LONGBRIDGE_APP_KEY`
- `LONGBRIDGE_APP_SECRET`
- `LONGBRIDGE_ACCESS_TOKEN`

未加入 Longbridge credentials 時，程式會明確指出未能取得實時股價，不會編造數據。

## GitHub 部署步驟

1. 建立一個 GitHub repo。
2. 把本資料夾全部上傳到 repo 根目錄。
3. 到 repo 的 `Settings > Secrets and variables > Actions`。
4. 在 `Secrets` 加入：
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - `LONGBRIDGE_APP_KEY`
   - `LONGBRIDGE_APP_SECRET`
   - `LONGBRIDGE_ACCESS_TOKEN`
5. 在 `Variables` 可選加入：
   - `GEMINI_MODEL`
   - `PORTFOLIO_SYMBOLS`
   - `WATCHLIST_SYMBOLS`
   - `NEWS_QUERIES`
6. 到 `Actions > Market Report Bot > Run workflow` 手動測試。

## 定時時間

目前 workflow 設定為香港時間：

- 08:30，週一至週五
- 12:30，週一至週五
- 21:30，週一至週五

GitHub Actions 使用 UTC，所以檔案內看到的是：

- `30 0 * * 1-5`
- `30 4 * * 1-5`
- `30 13 * * 1-5`

## 本地測試

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Windows PowerShell 可以手動複製 `.env.example` 為 `.env`，再填入 token。

## LLM 免費部署

建議用 Gemini API 免費層，模型先用：

```text
gemini-2.5-flash-lite
```

它適合每日幾次市場報告。免費層資料可能會被用作改善產品；如果你非常在意私隱或不想資料被用於改善模型，就要升級 paid tier 或改用本地 LLM/VPS，但那就未必完全免費。

## 重要限制

- GitHub scheduled workflow 不是交易級排程，可能有延遲；用於每日市場簡報可以接受。
- Google News RSS 不是完整新聞資料庫，只是免費新聞來源。
- 真正「實時、真實」股價要等 Longbridge OpenAPI 和相應 quote 權限批核。
- 報告只作資訊整理，不構成投資建議。
