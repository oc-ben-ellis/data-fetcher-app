#!/bin/bash
# Shell configuration for OC Fetcher devcontainer
# This file disables paging for common CLI tools to improve development experience


# Git specific settings
export GIT_TERMINAL_PROGRESS=1

# Docker specific settings
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Python settings
export PYTHONUNBUFFERED=1

# Development convenience
export EDITOR=code
export VISUAL=code

# GPG convenience alias - bypass agent detection for manual runs
alias configure-gpg='CURSOR_AGENT="" source /home/vscode/configure-gpg-interactive.sh'

# Note: Poetry virtual environment PATH is now handled by the poetry feature

# CRITICAL: Configure GPG early to avoid prompt issues
export GPG_TTY=$(tty)
if [[ -z "${GPG_CONFIGURED:-}" ]] && [[ -z "$CURSOR_AGENT" ]]; then
  # Run the GPG configuration script (not source to avoid shell closure issues)
  if [[ -f "/home/vscode/configure-gpg-interactive.sh" ]]; then
    bash /home/vscode/configure-gpg-interactive.sh
    export GPG_CONFIGURED=1
  fi
fi


echo "✓ Shell configuration loaded"
