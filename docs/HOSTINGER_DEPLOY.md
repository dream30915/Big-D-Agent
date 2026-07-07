# Deploying on a Hostinger VPS (Ubuntu)

## 1. Connect + prepare

```bash
ssh root@YOUR_VPS_IP
apt-get update && apt-get upgrade -y
apt-get install -y git curl
```

## 2. Clone + configure

```bash
git clone https://github.com/dream30915/big-d-agent.git
cd big-d-agent
cp .env.example .env
nano .env      # set TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, TELEGRAM_ADMIN_ID, DATABASE_PASSWORD
```

## 3. One-shot setup script

`scripts/setup.sh` installs Docker if needed, creates `.env` from the template
on first run, then builds and starts the stack:

```bash
bash scripts/setup.sh      # first run: creates .env, tells you to edit it
nano .env                  # fill in keys
bash scripts/setup.sh      # second run: builds + starts + health-checks
```

Or do it manually:

```bash
curl -fsSL https://get.docker.com | sh
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
docker compose logs -f bot
```

## 4. Browser automation (optional)

The `browser_automation` skill needs Chromium. It runs inside the `bot`
container; install the browser there once:

```bash
docker compose exec bot playwright install --with-deps chromium
```

## 5. Security checklist

- Postgres and Redis are bound to `127.0.0.1` in `docker-compose.yml` — keep
  them off the public internet.
- The API (`:8000`) is also localhost-bound. To expose it, put **nginx + TLS +
  an API key** in front; do not publish the raw port.
- `.env` holds real secrets — it is gitignored. Never commit it.
- Set a strong `DATABASE_PASSWORD`.
- Restrict who can talk to the bot if needed via `TELEGRAM_ADMIN_ID` (enforce in
  a handler — not enforced by default yet).

## 6. Updating

```bash
cd big-d-agent
git pull
docker compose up -d --build
```

## 7. Logs & health

```bash
docker compose logs -f bot          # live logs
curl http://localhost:8000/health   # config + liveness
curl http://localhost:8000/usage    # token usage
```
