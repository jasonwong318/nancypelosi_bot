# Market Report Bot

Free scheduled investment intelligence MVP:

1. GitHub Actions runs the Python job on schedule.
2. Longbridge OpenAPI is the primary market data source after credentials are added.
3. Yahoo Finance chart API is used only as a temporary fallback when Longbridge is not connected.
4. Google News RSS supplies free news headlines.
5. Yahoo Finance chart API supplies basic macro indicators: VIX, US10Y, DXY, gold, oil.
6. An OpenAI-compatible chat LLM generates a Traditional Chinese scheduled investment memo — Volcengine Ark (`ARK_API_KEY`) if set, otherwise Zhipu GLM (`ZHIPU_API_KEY`).
7. Telegram sends the memo.

## Required GitHub Secrets

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Set exactly one LLM provider secret:

```text
ARK_API_KEY      # Volcengine Ark (takes priority if both are set)
ZHIPU_API_KEY    # Zhipu GLM (fallback)
```

Add these after Longbridge OpenAPI is approved:

```text
LONGBRIDGE_APP_KEY
LONGBRIDGE_APP_SECRET
LONGBRIDGE_ACCESS_TOKEN
```

Optional Phase 2 placeholder:

```text
ACCOUNT_POSITIONS_JSON
```

Use `ACCOUNT_POSITIONS_JSON` only if you want to provide manual positions. Example:

```json
[{"symbol":"TSLA.US","quantity":10,"cost_basis":180}]
```

IBKR is not connected in this MVP. The account layer is reserved so the report will not invent cash, margin, P&L, or position sizes.

## Optional GitHub Variables

```text
LLM_MODEL       # default: ark-code-latest (Ark) or glm-4.7-flash (GLM)
LLM_ENDPOINT    # override the chat completions URL entirely
PORTFOLIO_SYMBOLS
WATCHLIST_SYMBOLS
NEWS_QUERIES
```

Default portfolio:

```text
TSLA.US,VOO.US,0941.HK,0883.HK,2802.HK,3416.HK,MRVL.US,LITE.US,9988.HK,9888.HK,3896.HK
```

Default watchlist:

```text
NVDA.US,AAPL.US,GOOGL.US,AMZN.US,0700.HK,0100.HK,2513.HK
```

## Schedule

GitHub Actions uses UTC. Current Hong Kong schedule:

```text
08:30 HKT, Monday-Friday
12:30 HKT, Monday-Friday
21:30 HKT, Monday-Friday
```

## Expected Action Logs

When the workflow runs, check these lines:

```text
Quote status:
Quote count:
Macro item count:
News query count:
News item count:
Account status:
Risk status:
```

Without Longbridge credentials:

```text
Quote status: longbridge_missing_using_yahoo_fallback
```

With valid Longbridge credentials:

```text
Quote status: ok
```

## Report Sections

The Telegram memo uses this structure:

```text
Executive Summary
Macro Overview
Holdings & Watchlist
Risk Dashboard
AI Insights
Data Quality Notes
```

Ticker-to-company mapping comes only from `report_bot/symbols.py`. This avoids the LLM guessing or misidentifying Hong Kong tickers and ETFs.

## Important Limits

- This is not investment advice.
- GitHub scheduled workflows can be delayed.
- Google News RSS is a free headline source, not a complete news database.
- Yahoo fallback is not a replacement for Longbridge real-time market data.
- The current risk score is symbol-level only. True beta, VaR, drawdown, margin, and P&L require account data such as IBKR in a future phase.
