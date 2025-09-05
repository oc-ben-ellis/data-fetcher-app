#!/bin/bash
# Set GIT_CONFIG to use cursor-specific config when CURSOR_AGENT is set
if [[ -n "$CURSOR_AGENT" ]] && [[ -f "/home/vscode/.cursor_safe/.gitconfig" ]]; then
    export GIT_CONFIG="/home/vscode/.cursor_safe/.gitconfig"
fi
