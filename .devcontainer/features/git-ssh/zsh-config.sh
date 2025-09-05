#!/bin/zsh
# Zsh configuration for OC Fetcher devcontainer
# This file sets up proper prompts for zsh in agent sessions



# GPG convenience alias - bypass agent detection for manual runs
alias configure-gpg='CURSOR_AGENT="" source /home/vscode/configure-gpg-interactive.sh'

# GPG Configuration - only run if not already configured and not in agent mode
if [[ -z "${GPG_CONFIGURED:-}" ]] && [[ -z "$CURSOR_AGENT" ]]; then
  # Source the GPG configuration script
  if [[ -f "/home/vscode/configure-gpg-interactive.sh" ]]; then
    source /home/vscode/configure-gpg-interactive.sh
    export GPG_CONFIGURED=1
  fi
fi

echo "✓ Zsh configuration loaded for agent sessions"
