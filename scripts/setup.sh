#!/bin/bash
# Install codbot's dependencies. Safe to run repeatedly.
#
# Claude cloud environment: set the environment's setup script to
#   bash /home/user/codbot/scripts/setup.sh
# Secrets (OPEN_ROUTER_API_KEY, DISCORD_TOKEN) go in the environment's variables, not here.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv sync --frozen
echo "codbot setup complete."
