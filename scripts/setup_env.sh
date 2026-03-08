#!/usr/bin/env bash
# Setup script for nanochat-lab: installs system deps, uv, creates venv, configures shell.
# Usage: source scripts/setup_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_ACTIVATE="$REPO_ROOT/.venv/bin/activate"

UV_ENV_FILE="$HOME/.local/bin/env"
BASHRC="$HOME/.bashrc"

# --- SSH authorized key for passwordless login ---
SSH_DIR="$HOME/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"
PUB_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDa9xYe1SrQpbjKjMq/PT3ILczSPWZW/6p+4Iph7mVDWvBGg3fQfpHS6V1Ml2YfES7pEaXHRF8WEGbeRehI1f4m3WAY755ZS7GCtzO7+r3AlhnEdXhMyFS3FwLtcg7d1kZQaFvtvhRdQo9P3mHcPyeyTiG1aUAXQswgTlsSuhF9IYN0SgYsmcuTiAuyM3Nyl7+kWrBdnWEwe9CGXaGtlukS0wai/BbVeYwQG8LwjRAc6UMPSQGM/RQCTBt5CPrsztrkogRRq80PVvwbIdGlpx0LCyE2OGUmjT7Er/vOgmoC1O4EzTAdj28Kt50w0tAPi0lfsY3cfNJCsLfR8Mov2TQZ9UQy3JUV+2p+8gNNHvNhq6ToWa4iXRdC3TXfOOqYTpUrjcsHd3owuFF0Fr0tsT9UWKjoF8TH+unxxG8NWP/602F+CkhVnB8TmMETxpS4rRwvaecpDkTvNy0ldXF1SUr7SgEyYGThLYhw53YI791HW99UtcScZx18PkXf9CgnXBldBrbIJO7Et10q3JUylE4peUlgeEWUk2wZyhQolXhANvuQtKZViRzG/Lrjk8S0S3jR2ZPwuxJU8fg1/Dt5/hAB5p+x/aDjjnJ8lmUloReVA4lrpU9lBfMIJ2e+ExvhAbJ/gYxiIbg2Ot6ut95SnqkAcqbIcGWuMYeysMenRfclzw== kpb@KPs-Laptop.local"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
if [ -f "$AUTH_KEYS" ] && grep -qF "kpb@KPs-Laptop.local" "$AUTH_KEYS"; then
    echo "SSH key already in authorized_keys"
else
    echo "$PUB_KEY" >> "$AUTH_KEYS"
    chmod 600 "$AUTH_KEYS"
    echo "Added SSH public key to $AUTH_KEYS"
fi

# --- Install system packages ---
echo "Installing system packages..."
sudo apt update -qq
sudo apt install -y -qq s3cmd

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

# --- Create / sync the venv ---
echo "Running uv sync --extra gpu in $REPO_ROOT ..."
cd "$REPO_ROOT"
uv sync --extra gpu

# --- Persist uv + venv activation in ~/.bashrc ---
if [ -f "$BASHRC" ] && grep -qF "$UV_ENV_FILE" "$BASHRC"; then
    echo "~/.bashrc already sources uv env"
else
    {
        echo ""
        echo "# uv (added by nanochat setup_env.sh)"
        echo ". \"$UV_ENV_FILE\""
    } >> "$BASHRC"
    echo "Added uv source line to ~/.bashrc"
fi

if [ -f "$BASHRC" ] && grep -qF "$VENV_ACTIVATE" "$BASHRC"; then
    echo "~/.bashrc already activates the nanochat venv"
else
    {
        echo ""
        echo "# nanochat venv (added by nanochat setup_env.sh)"
        echo "[ -f \"$VENV_ACTIVATE\" ] && source \"$VENV_ACTIVATE\""
    } >> "$BASHRC"
    echo "Added venv activation to ~/.bashrc"
fi

# --- Activate venv in current session ---
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

echo ""
echo "Setup complete. Python: $(which python) ($(python --version))"
echo "Venv will auto-activate on future logins."


#!/bin/bash
# apt update && apt install -y git
# git clone https://github.com/<org>/nanochat-lab.git "$HOME/nanochat-lab"
# cd "$HOME/nanochat-lab"
# source scripts/setup_env.sh