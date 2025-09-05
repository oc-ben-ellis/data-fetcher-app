#!/bin/bash
# Set AWS config for cursor agent sessions using environment variables
# This script configures AWS CLI to use the cursor-safe AWS config when CURSOR_AGENT is set

if [[ -n "$CURSOR_AGENT" ]] && [[ -f "/home/vscode/.cursor_safe/.aws-config" ]]; then
    # Set AWS config file path to use cursor-safe config
    export AWS_CONFIG_FILE="/home/vscode/.cursor_safe/.aws-config"
fi
