# 🤖 Big-D-Agent

A Telegram-first AI agent. Messages are classified by intent, routed to the
right cost/quality model tier on **OpenRouter**, and handled by pluggable
**skills** (web scraping, browser automation, content, support, analysis). It
ships with a **FastAPI** service (`/health`, `/usage`, `/agent`), **Postgres**
persistence, and **Redis**, all wired for `docker compose up`.

> Status: **v0.2 — working foundation.** The core loop (Telegram → Hermes →
> OpenRouter/skills → reply) is implemented and tested, now with a **cost guard**
> (daily token/USD budget + per-user rate limit), **Redis-backed conversation
> memory**, and **admin stats/credit** commands. Advanced features from the
> roadmap (payments, marketplace, multi-agent, dashboard) are **not** built yet
> — see [FEATURES.md](FEATURES.md) for the honest status of each.

## Quick start (local, Docker)

```bash
git clone https://github.com/dream30915/big-d-agent.git
cd big-d-agent
cp .env.example .env
nano .env            # fill in the 3 required keys (below)
docker compose up -d --build
curl http://localhost:8000/health
docker compose logs -f bot
```

Then open your bot in Telegram and send `/start`.

### The 3 things you must set in `.env`

| Var | Where to get it |
|-----|-----------------|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `OPENROUTER_API_KEY` | <https://openrouter.ai/keys> |
| `TELEGRAM_ADMIN_ID` | [@userinfobot](https://t.me/userinfobot) |

Also set a strong `DATABASE_PASSWORD`. Everything else has sane defaults.

> The bot starts even without a Telegram token — the API and `/health` come up
> and a warning is logged. This lets you test the HTTP surface before you have a
> token.

## How a message flows

```
Telegram message
      │
      ▼
  Hermes (src/agent/hermes.py)
      ├─ 1. rate + budget guard (src/core/costguard.py)   ← before any spend
      ├─ 2. ethics gate         (src/core/ethics.py)
      ├─ 3. classify intent     (src/agent/intent.py)     ← cheap, no tokens
      ├─ 4. route to model      (src/agent/router.py)     ← fast vs quality tier
      └─ 5. run skill or chat   (src/skills/*, src/llm/openrouter.py)
      │        └─ chat uses per-user memory (src/core/memory.py)
      ▼
   reply (Telegram + persisted to Postgres; tokens/cost recorded)
```

### Commands & endpoints added in v0.2

| Admin command | API endpoint | Shows |
|---------------|-------------|-------|
| `/stats` | `GET /stats` | user/task counts, LLM usage, today's budget |
| `/budget` | `GET /budget` | today's token/USD spend vs caps |
| `/credit` | `GET /credit` | remaining OpenRouter credit (USD) |

Cost guard, rate limit, and memory all use **Redis** when available and fall
back to in-process state if it isn't — the bot never crashes on a Redis outage.

## Commands

| Command | Does |
|---------|------|
| `/start` | Welcome + registers the user |
| `/help` | Usage help |
| `/ping` | Liveness check → `pong` |
| *(any text)* | Auto-classified and handled |

## Local development (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in keys
python -m src.main         # starts API + bot
pytest -q                  # run tests
```

## Layout

```
src/
  main.py            entrypoint — runs FastAPI + Telegram bot on one loop
  config.py          typed settings (pydantic-settings)
  agent/             hermes (decision engine), intent, model router
  llm/               openrouter (client+fallback), pricing (USD estimate), credits
  skills/            web_scraping, browser_automation, content, support, analysis
  bot/               telegram application + handlers (incl. admin commands)
  api/app.py         FastAPI: /health, /usage, /agent, /budget, /stats, /credit
  db/                SQLAlchemy models, async engine, repository, schema.sql
  core/              logging, ethics, store (redis+fallback), costguard, memory
tests/               intent, ethics, health, costguard, memory
docs/                API.md, HOSTINGER_DEPLOY.md
```

See [CLAUDE.md](CLAUDE.md) for conventions and how to extend the agent, and
[docs/HOSTINGER_DEPLOY.md](docs/HOSTINGER_DEPLOY.md) to deploy on a VPS.
