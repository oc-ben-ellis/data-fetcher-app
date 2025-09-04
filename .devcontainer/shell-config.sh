#!/bin/bash
# Shell configuration for OC Fetcher devcontainer
# This file disables paging for common CLI tools to improve development experience

# Disable paging for all tools
export PAGER=cat
export AWS_PAGER=""
export GIT_PAGER=cat
export LESS=""
export MORE=""
export MANPAGER=cat

# AWS CLI specific settings
export AWS_CLI_AUTO_PROMPT=off
export AWS_CLI_USE_INSTALLER=true

# Git specific settings
export GIT_TERMINAL_PROGRESS=1

# Docker specific settings
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Python/poetry settings
export PYTHONUNBUFFERED=1
export POETRY_VENV_IN_PROJECT=1

# Development convenience
export EDITOR=code
export VISUAL=code

# GPG convenience alias - bypass agent detection for manual runs
alias configure-gpg='CURSOR_AGENT="" source /workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh'

# CRITICAL: Set up Poetry virtual environment PATH first for proper shell prompt
# This ensures tools like pre-commit are available immediately
if command -v poetry >/dev/null 2>&1; then
    POETRY_VENV_PATH=$(poetry env info --path 2>/dev/null || echo "")
    if [[ -n "$POETRY_VENV_PATH" && -d "$POETRY_VENV_PATH/bin" ]]; then
        export PATH="$POETRY_VENV_PATH/bin:$PATH"
    fi
fi

# CRITICAL: Configure GPG early to avoid prompt issues
export GPG_TTY=$(tty)
if [[ -z "${GPG_CONFIGURED:-}" ]] && [[ -z "$CURSOR_AGENT" ]]; then
  # Run the GPG configuration script (not source to avoid shell closure issues)
  if [[ -f "/workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh" ]]; then
    bash /workspaces/data-fetcher-sftp/.devcontainer/configure-gpg-interactive.sh
    export GPG_CONFIGURED=1
  fi
fi

# Set a clean prompt for Agent sessions
if [[ -n "$CURSOR_AGENT" ]]; then
  # For bash, set a simple prompt
  if [[ "$0" == *"bash"* ]] || [[ "$BASH_VERSION" ]]; then
    PS1='\u@\h:\w\$ '
  fi
fi

echo "✓ Shell configuration loaded - paging disabled for CLI tools"
