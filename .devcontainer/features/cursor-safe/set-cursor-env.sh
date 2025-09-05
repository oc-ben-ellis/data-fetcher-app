#!/bin/bash
# Cursor agent-specific environment configuration
# This script sets up environment variables that improve cursor agent experience

export PATH=${PATH}:$(find find /home/vscode/.cursor-server/bin/ -name remote-cli)

if [[ -n "$CURSOR_AGENT" ]]; then
    # Disable paging for all tools to prevent interactive prompts
    export PAGER=cat
    export AWS_PAGER=""
    export GIT_PAGER=cat
    export LESS=""
    export MORE=""
    export MANPAGER=cat
    export GPG_TTY=$(tty)

    # AWS CLI specific settings for non-interactive use
    export AWS_CLI_AUTO_PROMPT=off
    export AWS_CLI_USE_INSTALLER=true

    # Set a clean prompt for Agent sessions
    if [[ "$0" == *"bash"* ]] || [[ "$BASH_VERSION" ]]; then
        PS1='\u@\h:\w\$ '
    elif [[ "$0" == *"zsh"* ]] || [[ -n "$ZSH_VERSION" ]]; then
        PS1='%n@%m:%1~$ '
    fi
fi
