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

## Notes

- Without `OPENROUTER_API_KEY`, `/agent` returns a friendly "AI unavailable"
  reply (HTTP 200) rather than erroring — check `/health` to confirm config.
- The ethics gate can refuse a request; you'll get a polite refusal with
  `intent: "chat"`.
