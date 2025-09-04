#!/bin/zsh
# Zsh configuration for OC Fetcher devcontainer
# This file sets up proper prompts for zsh in agent sessions

# GPG convenience alias - bypass agent detection for manual runs
alias configure-gpg='CURSOR_AGENT="" source /workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh'

# Set a clean prompt for Agent sessions in zsh
if [[ -n "$CURSOR_AGENT" ]]; then
  # Use zsh-specific prompt format
  PS1='%n@%m:%1~$ '
  # Alternative simple prompt
  # PS1='%n@%m:%1~$ '
fi

# GPG Configuration - only run if not already configured and not in agent mode
if [[ -z "${GPG_CONFIGURED:-}" ]] && [[ -z "$CURSOR_AGENT" ]]; then
  # Source the GPG configuration script
  if [[ -f "/workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh" ]]; then
    source /workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh
    export GPG_CONFIGURED=1
  fi
fi

echo "✓ Zsh configuration loaded for agent sessions"
