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
| 6 | Cost optimization | ✅ | daily token + USD budget guard, 80%/hard-stop, per-user rate limit (`src/core/costguard.py`, ported from Hermes) |
| 7 | Ethics & compliance | ✅ | local keyword gate (`src/core/ethics.py`) |
| 8 | Token/usage tracking | ✅ | live counter + daily budget snapshot, exposed at `/usage`, `/budget`, `/stats` |
| 9 | Multi-agent collaboration | ✅ | coordinator → router(intent) → planner → specialist (`src/agent/coordinator.py`, `planner.py`, `specialists.py`); enable with `ENABLE_MULTI_AGENT=true`. Reuses cost guard + fallback |
| 10 | Self-optimization | 🔴 | roadmap only |
| 11 | Agent marketplace | 🔴 | roadmap only |
| 12 | Context persistence | 🟡 | users + tasks in Postgres **+ Redis short-term conversation memory** (`src/core/memory.py`); no long-term/vector memory yet |

## Automation / skills

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 13 | Web scraping | ✅ | httpx + BeautifulSoup (`src/skills/web_scraping.py`) |
| 14 | Browser automation | ✅ | Playwright headless (`src/skills/browser_automation.py`); needs `playwright install chromium` |
| 15 | Content creation | ✅ | quality-tier LLM w/ system prompt |
| 16 | Customer service | ✅ | fast-tier LLM, escalates money/account asks |
| 17 | Data analysis | ✅ | quality-tier LLM, refuses to fabricate numbers |
| 18 | Task scheduling | ✅ | APScheduler recurring/one-off jobs, persisted in Postgres, delivered via Telegram (`src/scheduler/`); `/schedule` `/schedules` `/unschedule`. Jobs run through Hermes so the cost guard applies |
| 19 | n8n integration | 🔴 | env vars present; no code |

## Production

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 20 | FastAPI endpoints | ✅ | `/health` `/usage` `/agent` `/budget` `/stats` `/credit` (`src/api/app.py`) |
| 21 | Docker deployment | ✅ | `docker-compose.yml` (bot + Postgres + Redis) + `Dockerfile`; **Redis now wired** for memory + limits |
| 22 | Logging & analytics | 🟡 | structured logging (loguru) + task log table + `/stats` aggregation + admin `/stats` command; no analytics UI |
| — | Usage limits per plan | 🟡 | daily budget + per-user rate limit enforced; not yet differentiated per subscription plan |
| — | Credit monitoring | ✅ | OpenRouter credit check (`/credit` + admin command), ported from Hermes `credit_guard.py` |
| — | Subscription plans / Stripe | 🔴 | intentionally deferred — no payment code |
| — | Web dashboard | 🔴 | roadmap only |

## Legend

- ✅ **done & tested** — implemented and covered by tests or manual verification.
- 🟡 **partial** — a real but minimal version exists; more planned.
- 🔴 **not started** — named in the plan; no code yet (some have config flags).
