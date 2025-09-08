#!/bin/bash
set -e

# This feature creates a separate .cursor_safe/.gitconfig file and configures shells
# to use it when CURSOR_AGENT is set, completely isolating agent git config

echo "Setting up cursor-safe git configuration..."

# Create .cursor_safe directory in user's home
# Use the actual user's home directory, not root's
USER_HOME="/home/vscode"
CURSOR_DIR="$USER_HOME/.cursor_safe"
mkdir -p "$CURSOR_DIR"

# Copy the agent-specific git config file
CURSOR_GITCONFIG="$CURSOR_DIR/.gitconfig"
cp "$(dirname "$0")/agent.gitconfig" "$CURSOR_GITCONFIG"

# Copy the agent-specific AWS config file
CURSOR_AWSCONFIG="$CURSOR_DIR/.aws-config"
cp "$(dirname "$0")/agent.aws-config" "$CURSOR_AWSCONFIG"

# Copy the script that sets GIT_CONFIG when CURSOR_AGENT is set
CURSOR_SAFE_DIR="/usr/local/share/cursor-safe"
mkdir -p "$CURSOR_SAFE_DIR"

cp "$(dirname "$0")/set-git-config.sh" "$CURSOR_SAFE_DIR/set-git-config.sh"
cp "$(dirname "$0")/set-aws-config.sh" "$CURSOR_SAFE_DIR/set-aws-config.sh"
chmod +x "$CURSOR_SAFE_DIR/set-git-config.sh"
chmod +x "$CURSOR_SAFE_DIR/set-aws-config.sh"

# Copy the script that sets cursor agent-specific environment variables
cp "$(dirname "$0")/set-cursor-env.sh" "$CURSOR_SAFE_DIR/set-cursor-env.sh"
chmod +x "$CURSOR_SAFE_DIR/set-cursor-env.sh"

# Append cursor-safe sourcing to shell rc files to make the feature self-contained
CURSOR_SAFE_SOURCE="# Cursor-safe configuration (auto-added by cursor-safe feature)
if [[ -f \"/usr/local/share/cursor-safe/set-cursor-env.sh\" ]]; then
    source \"/usr/local/share/cursor-safe/set-cursor-env.sh\"
fi
if [[ -f \"/usr/local/share/cursor-safe/set-git-config.sh\" ]]; then
    source \"/usr/local/share/cursor-safe/set-git-config.sh\"
fi
if [[ -f \"/usr/local/share/cursor-safe/set-aws-config.sh\" ]]; then
    source \"/usr/local/share/cursor-safe/set-aws-config.sh\"
fi"

# Add to bashrc if not already present
if ! grep -q "cursor-safe feature" "$USER_HOME/.bashrc" 2>/dev/null; then
    echo "$CURSOR_SAFE_SOURCE" >> "$USER_HOME/.bashrc"
fi

# Add to zshrc if not already present
if ! grep -q "cursor-safe feature" "$USER_HOME/.zshrc" 2>/dev/null; then
    echo "$CURSOR_SAFE_SOURCE" >> "$USER_HOME/.zshrc"
fi
echo "✓ Cursor-safe configuration feature installed"
echo "  - Created $CURSOR_GITCONFIG"
echo "  - Created $CURSOR_AWSCONFIG"
echo "  - Created $CURSOR_SAFE_DIR/set-git-config.sh"
echo "  - Created $CURSOR_SAFE_DIR/set-aws-config.sh"
echo "  - Created $CURSOR_SAFE_DIR/set-cursor-env.sh"
echo "  - Added sourcing to .bashrc and .zshrc (self-contained feature)"
