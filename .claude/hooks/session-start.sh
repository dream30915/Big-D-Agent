#!/bin/bash
# SessionStart hook: install document / presentation tooling so it is available
# in Claude Code on the web sessions:
#   - pandoc   (apt)
#   - Marp CLI (npm global; needs Node.js)
#   - Quarto   (conda-forge via micromamba — avoids GitHub release downloads,
#               which the environment's egress policy commonly blocks)
#
# Runs synchronously on session start. Idempotent, non-interactive, best-effort:
# a tool that fails to install must not abort session startup.
set -uo pipefail

# Only run in the remote (Claude Code on the web) environment.
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
    $SUDO apt-get update -qq || true
    $SUDO apt-get install -y nodejs npm || echo "hook: nodejs/npm install failed (continuing)"
  fi
  if command -v npm >/dev/null 2>&1; then
    npm install -g @marp-team/marp-cli || echo "hook: marp-cli install failed (continuing)"
  else
    echo "hook: npm unavailable, skipping Marp CLI"
  fi
fi

# --- Quarto (conda-forge via micromamba) ---------------------------------------
# GitHub release downloads (the usual Quarto .deb) are frequently blocked by the
# egress policy, so install from the conda-forge channel instead.
if ! command -v quarto >/dev/null 2>&1; then
  QENV=/opt/quarto-env
  if [ ! -x "$QENV/bin/quarto" ]; then
    MMDIR=/opt/micromamba
    if [ ! -x "$MMDIR/bin/micromamba" ]; then
      mkdir -p "$MMDIR"
      curl -fsSL "https://micro.mamba.pm/api/micromamba/linux-64/latest" \
        | tar -xj -C "$MMDIR" bin/micromamba 2>/dev/null \
        || echo "hook: micromamba download failed (skipping Quarto)"
    fi
    if [ -x "$MMDIR/bin/micromamba" ]; then
      MAMBA_ROOT_PREFIX="$MMDIR/root" "$MMDIR/bin/micromamba" create -y -p "$QENV" \
        -c conda-forge quarto >/dev/null 2>&1 \
        || echo "hook: quarto conda install failed (continuing)"
    fi
  fi
  # Install a PATH wrapper that applies the conda env's activation variables
  # (deno, pandoc, typst, share path, deno_dom plugin) before running quarto.
  if [ -x "$QENV/bin/quarto" ]; then
    $SUDO tee /usr/local/bin/quarto >/dev/null << 'WRAP'
#!/bin/bash
export QUARTO_CONDA_PREFIX=/opt/quarto-env
for f in /opt/quarto-env/etc/conda/activate.d/*.sh; do [ -r "$f" ] && . "$f"; done
export QUARTO_DENO_DOM=/opt/quarto-env/lib/deno_dom.so
exec /opt/quarto-env/bin/quarto "$@"
WRAP
    $SUDO chmod +x /usr/local/bin/quarto
  fi
fi

exit 0
