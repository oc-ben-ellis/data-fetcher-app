#!/bin/bash
set -e

# Install Poetry if requested
if [ "$INSTALLPOETRY" = "true" ]; then
    echo "Installing Poetry..."
    pip install poetry
fi

# Project dependencies will be installed by postCreateCommand
# Skip poetry install during feature installation to avoid issues

# Install Mermaid CLI if requested
if [ "$INSTALLMERMAID" = "true" ]; then
    echo "Installing Mermaid CLI..."
    npm install -g @mermaid-js/mermaid-cli
fi

# Install Puppeteer if requested
if [ "$INSTALLPUPPETEER" = "true" ]; then
    echo "Installing Puppeteer and Chrome headless shell..."
    npx puppeteer browsers install chrome-headless-shell

    # Install system dependencies for Puppeteer
    apt-get update && apt-get install -y \
        libglib2.0-0t64 \
        libgbm1 \
        libdbus-1-3 \
        libgtk-3-0t64 \
        libnss3 \
        libxss1 \
        libasound2t64
fi
