# Features — status vs. the master plan

Honest status of every feature from the roadmap. ✅ done & tested · 🟡 partial /
scaffolded · 🔴 not started.

## Core

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Telegram bot interface | ✅ | `/start` `/help` `/ping` + free-text (`src/bot/`) |
| 2 | Hermes agent framework | ✅ | ethics → intent → route → skill/LLM (`src/agent/hermes.py`) |
| 3 | OpenRouter integration | ✅ | HTTP client, usage tracking, fast-tier fallback (`src/llm/openrouter.py`) |
| 4 | Intent classification | ✅ | keyword pass, EN + TH (`src/agent/intent.py`) |
| 5 | Model routing (fast/quality) | ✅ | per-intent tiers (`src/agent/router.py`) |
| 6 | Cost optimization | 🟡 | free keyword routing + tier selection; no hard budget caps yet |
| 7 | Ethics & compliance | ✅ | local keyword gate (`src/core/ethics.py`) |
| 8 | Token/usage tracking | ✅ | process-lifetime counter, exposed at `/usage` |
| 9 | Multi-agent collaboration | 🔴 | flag `ENABLE_MULTI_AGENT` exists; no orchestration built |
| 10 | Self-optimization | 🔴 | roadmap only |
| 11 | Agent marketplace | 🔴 | roadmap only |
| 12 | Context persistence | 🟡 | users + tasks persisted (Postgres); no long-term memory yet |

## Automation / skills

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 13 | Web scraping | ✅ | httpx + BeautifulSoup (`src/skills/web_scraping.py`) |
| 14 | Browser automation | ✅ | Playwright headless (`src/skills/browser_automation.py`); needs `playwright install chromium` |
| 15 | Content creation | ✅ | quality-tier LLM w/ system prompt |
| 16 | Customer service | ✅ | fast-tier LLM, escalates money/account asks |
| 17 | Data analysis | ✅ | quality-tier LLM, refuses to fabricate numbers |
| 18 | Task scheduling | 🔴 | roadmap only |
| 19 | n8n integration | 🔴 | env vars present; no code |

## Production

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 20 | FastAPI endpoints | ✅ | `/health` `/usage` `/agent` (`src/api/app.py`) |
| 21 | Docker deployment | ✅ | `docker-compose.yml` (bot + Postgres + Redis) + `Dockerfile` |
| 22 | Logging & analytics | 🟡 | structured logging (loguru) + task log table; no analytics UI |
| — | Subscription plans / Stripe | 🔴 | intentionally deferred — no payment code |
| — | Web dashboard | 🔴 | roadmap only |

## Legend

- ✅ **done & tested** — implemented and covered by tests or manual verification.
- 🟡 **partial** — a real but minimal version exists; more planned.
- 🔴 **not started** — named in the plan; no code yet (some have config flags).
