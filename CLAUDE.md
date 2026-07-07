# CLAUDE.md — Big-D-Agent

Guidance for AI assistants (and humans) working in this repo. Read this before
making changes.

## What this is

Big-D-Agent is a **Telegram-first AI agent**. The core loop is:

> Telegram/API message → **Hermes** decision engine → (ethics → intent → model
> route → skill or LLM) → reply, persisted to Postgres.

It is a Python 3.12 async app. One process runs both a **FastAPI** service and
the **python-telegram-bot** long-poller on a single asyncio loop
(`src/main.py`). Postgres + Redis come up alongside it via `docker compose`.

Model calls go to **OpenRouter** (OpenAI-compatible HTTP; no vendor SDK). There
are two tiers — *fast* and *quality* — chosen per intent for cost control.

## Project status — be honest about it

This is **v0.1, a working foundation**, not the finished 22-feature product in
the original master plan. When asked about a feature, check
[FEATURES.md](FEATURES.md) and state its real status. **Do not describe planned
features as done.** What is actually implemented and tested:

- Telegram bot: `/start`, `/help`, `/ping`, free-text handling.
- Hermes: ethics gate → intent classification → model routing → skill/LLM.
- OpenRouter client with usage tracking and fast-tier fallback.
- Skills: `web_scraping` (BeautifulSoup) and `browser_automation` (Playwright)
  are real; `content_creation`, `customer_service`, `data_analysis` are real
  LLM calls with tuned system prompts.
- FastAPI: `/health`, `/usage`, `/agent`.
- Postgres persistence (users, tasks) — non-fatal if the DB is down.
- Ethics gate (local keyword screen).

**Not built** (placeholders / roadmap only): payments/Stripe, subscription
enforcement, web dashboard, agent marketplace, multi-agent orchestration,
self-optimization, n8n workflows, scheduling. Feature flags for some of these
exist in config but gate no real code yet.

## Conventions

- **Language:** code, comments, commits in English. User-facing bot copy is
  bilingual (Thai + English) to match the owner's audience.
- **Config:** everything reads from `src/config.py` (`get_settings()`), which
  loads `.env`. Never read `os.environ` directly elsewhere; add a field there.
- **Secrets:** never commit `.env`. Only `.env.example` (placeholders) is
  tracked. `.gitignore` already enforces this — keep it that way.
- **Failure posture:** a chat reply must never crash on infra hiccups. DB and
  LLM failures are caught and degrade to a helpful message (see
  `db/repository.py`, `hermes.handle_message`). Preserve this.
- **Cost:** intent classification is a free keyword pass first; only spend
  tokens when needed. Route cheap tasks to the fast tier (`agent/router.py`).
- **Commits:** Conventional Commits (`feat:` / `fix:` / `docs:` / `refactor:` /
  `chore:`). First line says *why*.
- **Ask before production actions:** deploys, DB migrations, restarting live
  services, editing real `.env` / credentials — show the plan and impact first.

## How to extend

**Add a skill:**
1. Create `src/skills/<name>.py` exposing a `Skill(name, description, handler)`.
   The handler is `async def (text: str) -> SkillResult`.
2. Register it in `src/skills/__init__.py` (`SKILLS`).
3. If it should trigger on an intent, add the intent in `src/agent/intent.py`
   and map it in `_INTENT_SKILL` in `src/agent/hermes.py`.

**Add an intent:** extend `Intent` and `_RULES` in `src/agent/intent.py`
(English keywords use `\b` word boundaries; Thai keywords match as substrings —
`\b` does not work with Thai script). Decide its tier in `src/agent/router.py`.

**Add an API endpoint:** add it to `src/api/app.py`. Reuse `handle_message` from
Hermes rather than duplicating routing logic.

**Add a DB field:** edit `src/db/models.py` and mirror it in
`src/db/schema.sql`. Tables auto-create on startup via SQLAlchemy.

## Running & testing

```bash
python -m src.main     # API + bot (needs .env)
pytest -q              # tests: intent, ethics, health (no network needed)
docker compose up -d   # full stack
```

`pytest` runs without any API keys or network — the LLM is not called in tests.
Keep it that way: test routing/parsing logic, not live model output.

## Guardrails

- Keep the repo private-friendly: no real tokens, ids, or customer data in code
  or fixtures.
- The **ethics gate** (`src/core/ethics.py`) is a deliberate, auditable
  checkpoint. Don't remove it; extend its categories if needed.
- Payments and any customer-facing money flow are out of scope for now — do not
  add Stripe or charge-user logic without an explicit request.
