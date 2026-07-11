#!/bin/bash
# SessionStart hook: install pandoc so document conversion (Markdown -> PDF/docx/
# HTML, etc.) is available in Claude Code on the web sessions.
#
# Runs synchronously on session start. Idempotent and non-interactive.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment. Locally, developers
# manage their own tools.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Nothing to do if pandoc is already installed (fresh containers won't have it;
# a cached container will, so this becomes a fast no-op).
if command -v pandoc >/dev/null 2>&1; then
  exit 0
fi

# Use sudo only when we're not already root.
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -qq || true
$SUDO apt-get install -y pandoc
