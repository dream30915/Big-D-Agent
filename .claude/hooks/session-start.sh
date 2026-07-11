#!/bin/bash
# SessionStart hook: install document / presentation tooling so it is available
# in Claude Code on the web sessions:
#   - pandoc  (apt)
#   - Marp CLI (npm global, needs Node.js)
#   - Quarto  (deb from GitHub releases)
#
# Runs synchronously on session start. Idempotent, non-interactive, and best-effort:
# an individual tool that fails to install must not abort session startup.
set -uo pipefail

# Only run in the remote (Claude Code on the web) environment. Local developers
# manage their own tools.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi
export DEBIAN_FRONTEND=noninteractive

# --- pandoc (apt) --------------------------------------------------------------
if ! command -v pandoc >/dev/null 2>&1; then
  $SUDO apt-get update -qq || true
  $SUDO apt-get install -y pandoc || echo "hook: pandoc install failed (continuing)"
fi

# --- Marp CLI (npm global; needs Node.js) --------------------------------------
if ! command -v marp >/dev/null 2>&1; then
  if ! command -v npm >/dev/null 2>&1; then
    # Node is normally preinstalled; fall back to apt if it is genuinely missing.
    $SUDO apt-get update -qq || true
    $SUDO apt-get install -y nodejs npm || echo "hook: nodejs/npm install failed (continuing)"
  fi
  if command -v npm >/dev/null 2>&1; then
    npm install -g @marp-team/marp-cli || echo "hook: marp-cli install failed (continuing)"
  else
    echo "hook: npm unavailable, skipping Marp CLI"
  fi
fi

# --- Quarto (deb from GitHub releases) -----------------------------------------
# Downloads a release asset from github.com. If the environment's egress policy
# blocks GitHub release downloads (HTTP 403), this step is skipped without
# failing the hook.
if ! command -v quarto >/dev/null 2>&1; then
  QVER="1.5.56"
  QDEB="$(mktemp -d)/quarto-${QVER}-linux-amd64.deb"
  if curl -fsSL -o "$QDEB" \
      "https://github.com/quarto-dev/quarto-cli/releases/download/v${QVER}/quarto-${QVER}-linux-amd64.deb"; then
    $SUDO apt-get install -y "$QDEB" || echo "hook: quarto install failed (continuing)"
    rm -f "$QDEB"
  else
    echo "hook: could not download Quarto (egress policy may block GitHub releases); skipping"
  fi
fi

exit 0
