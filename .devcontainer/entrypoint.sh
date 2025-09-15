#!/usr/bin/env bash
set -euo pipefail

# Set default USER if not set
USER=${USER:-vscode}

# Ensure docker group inside container matches host docker.sock GID
DOCKER_SOCK=${DOCKER_SOCK:-/var/run/docker.sock}
if [ -S "$DOCKER_SOCK" ]; then
  SOCK_GID=$(stat -c '%g' "$DOCKER_SOCK")
  if ! getent group docker >/dev/null 2>&1; then
    sudo groupadd -g "$SOCK_GID" docker || true
  else
    CURRENT_GID=$(getent group docker | cut -d: -f3)
    if [ "$CURRENT_GID" != "$SOCK_GID" ]; then
      sudo groupmod -g "$SOCK_GID" docker || true
    fi
  fi
  if ! id -nG "$USER" | tr ' ' '\n' | grep -q '^docker$'; then
    sudo usermod -aG docker "$USER" || true
  fi
fi

# Fix GPG permissions if volume mounted
if [ -d "$HOME/.gnupg" ]; then
  chmod 700 "$HOME/.gnupg" || true
  find "$HOME/.gnupg" -type f -exec chmod 600 {} + || true
fi

# One-time Poetry install for services/fetcher
STAMP_FILE=.poetry_installed
if [ -f "pyproject.toml" ]; then
  if [ ! -f "/tmp/$STAMP_FILE" ]; then
    (
      # Install wheel files first if they exist
      if [ -d "/tmp/wheels" ] && [ "$(ls -A /tmp/wheels/*.whl 2>/dev/null)" ]; then
        echo "Installing wheel files from /tmp/wheels..."
        poetry add /tmp/wheels/*.whl --no-ansi --no-interaction
      fi
      poetry install
      touch "/tmp/$STAMP_FILE"
    ) || true
  fi
fi

exec "$@"



