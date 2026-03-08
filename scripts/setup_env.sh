#!/usr/bin/env bash
# Setup script for nanochat-lab: installs uv, configures PATH, and creates the venv.
# Usage: source scripts/setup_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

UV_ENV_FILE="$HOME/.local/bin/env"

# --- Install uv if not already present ---
if command -v uv &>/dev/null; then
    echo "uv is already installed: $(uv --version)"
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    if [ -f "$UV_ENV_FILE" ]; then
        # shellcheck disable=SC1090
        . "$UV_ENV_FILE"
        echo "uv installed: $(uv --version)"
    else
        echo "Error: uv installed but $UV_ENV_FILE not found." >&2
        return 1 2>/dev/null || exit 1
    fi
fi

# --- Persist uv PATH in ~/.bashrc ---
BASHRC="$HOME/.bashrc"
SOURCE_LINE=". \"$UV_ENV_FILE\""

if [ -f "$BASHRC" ] && grep -qF "$UV_ENV_FILE" "$BASHRC"; then
    echo "~/.bashrc already sources uv env"
else
    echo "" >> "$BASHRC"
    echo "# uv (added by nanochat setup_env.sh)" >> "$BASHRC"
    echo "$SOURCE_LINE" >> "$BASHRC"
    echo "Added uv source line to ~/.bashrc"
fi

# --- Create / sync the venv ---
echo "Running uv sync --extra gpu in $REPO_ROOT ..."
cd "$REPO_ROOT"
uv sync --extra gpu

echo ""
echo "Setup complete. Activate the venv with:"
echo "  source $REPO_ROOT/.venv/bin/activate"
