# API

The FastAPI service runs on `API_PORT` (default `8000`). In production, front it
with nginx + TLS and an API key/auth layer — **the endpoints below are currently
unauthenticated.**

## `GET /health`

Liveness + configuration snapshot. Used by Docker's healthcheck.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "production",
  "telegram_configured": true,
  "openrouter_configured": true
}
```

## `GET /usage`

Token/request counters for the current process lifetime.

```json
{ "requests": 12, "prompt_tokens": 3400, "completion_tokens": 1800, "total_tokens": 5200 }
```

## `GET /budget`

Today's spend against the daily caps (resets each UTC day).

```json
{ "date": "2026-07-07", "tokens": 1500, "token_budget": 200000,
  "cost_usd": 0.01, "cost_budget_usd": 5.0 }
```

## `GET /stats`

Aggregate view: DB user/task counts, LLM usage since boot, and today's budget.

```json
{ "db": {"users": 3, "tasks": 12},
  "llm": {"requests": 12, "total_tokens": 5200},
  "budget": {"date": "2026-07-07", "tokens": 5200, "token_budget": 200000,
             "cost_usd": 0.02, "cost_budget_usd": 5.0} }
```

## `GET /credit`

Remaining OpenRouter credit in USD (`null` if unreadable / no key).

```json
{ "openrouter_credit_usd": 8.42 }
```

> These three are also available as **admin-only** Telegram commands: `/stats`,
> `/budget`, `/credit` (restricted to `TELEGRAM_ADMIN_ID`).

## `POST /agent`

Run one message through the same Hermes engine the Telegram bot uses.

Request:
```json
{ "message": "summarise https://example.com" }
```

Response:
```json
{ "reply": "📄 Example Domain\n\n- ...", "intent": "scrape", "skill": "web_scraping" }
```

`intent` is one of `scrape | browse | content | support | analyze | chat`.
`skill` is the skill that handled it, or `null` for a plain chat reply.

### curl

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/agent \
  -H 'content-type: application/json' \
  -d '{"message":"write a launch caption for a coffee shop"}'
```

## `POST /n8n/trigger`

Fire the configured n8n webhook with a JSON payload.

Request:
```json
{ "text": "kick off the onboarding flow", "extra": { "customer": "acme" } }
```

Response:
```json
{ "ok": true, "status": 200, "detail": "..." }
```

Returns `{"ok": false, "detail": "n8n is not configured ..."}` when
`N8N_WEBHOOK_URL` is unset. Also available as the admin-only `/n8n` Telegram
command.

## Notes

- Without `OPENROUTER_API_KEY`, `/agent` returns a friendly "AI unavailable"
  reply (HTTP 200) rather than erroring — check `/health` to confirm config.
- The ethics gate can refuse a request; you'll get a polite refusal with
  `intent: "chat"`.
