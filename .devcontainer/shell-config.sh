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

# Set a clean prompt for Agent sessions
if [[ -n "$CURSOR_AGENT" ]]; then
  # For bash, set a simple prompt
  if [[ "$0" == *"bash"* ]] || [[ "$BASH_VERSION" ]]; then
    PS1='\u@\h:\w\$ '
  fi
fi

echo "✓ Shell configuration loaded - paging disabled for CLI tools"
