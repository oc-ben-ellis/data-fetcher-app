#!/bin/zsh
# Zsh configuration for OC Fetcher devcontainer
# This file sets up proper prompts for zsh in agent sessions

# Set a clean prompt for Agent sessions in zsh
if [[ -n "$CURSOR_AGENT" ]]; then
  # Use zsh-specific prompt format
  PS1='%n@%m:%1~$ '
  # Alternative simple prompt
  # PS1='%n@%m:%1~$ '
fi

echo "✓ Zsh configuration loaded for agent sessions"
