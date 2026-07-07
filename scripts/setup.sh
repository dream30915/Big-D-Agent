#!/usr/bin/env bash
# ============================================================================
#  Big-D-Agent — one-shot setup for a fresh Ubuntu VPS.
#  Installs Docker (if missing), prepares .env, and starts the stack.
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "🚀 Big-D-Agent setup ($REPO_DIR)"

if ! command -v docker >/dev/null 2>&1; then
  echo "🐳 installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "📝 created .env from template — EDIT IT before the bot can work:"
  echo "   - TELEGRAM_BOT_TOKEN  (from @BotFather)"
  echo "   - OPENROUTER_API_KEY  (from https://openrouter.ai/keys)"
  echo "   - TELEGRAM_ADMIN_ID   (from @userinfobot)"
  echo "   - DATABASE_PASSWORD   (choose a strong value)"
  echo
  echo "Run 'nano .env', then re-run this script to start."
  exit 0
fi

echo "🐳 building + starting stack..."
docker compose up -d --build

echo "⏳ waiting for health..."
sleep 8
docker compose ps
curl -fsS http://localhost:8000/health && echo || echo "(health not ready yet — check: docker compose logs bot)"
