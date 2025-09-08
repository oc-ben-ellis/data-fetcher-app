#!/bin/bash

# Git SSH and GPG Configuration Feature
# This script configures Git with SSH and GPG signing support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Feature options
ENABLE_GPG_SIGNING=${ENABLE_GPGSIGNING:-true}
ENABLE_SSH_AGENT=${ENABLE_SSHAGENT:-true}
CONFIGURE_SHELL=${CONFIGURESHELL:-true}

echo -e "${BLUE}🔧 Installing Git SSH and GPG Configuration Feature...${NC}"

# Install GPG if not already installed
if ! command -v gpg >/dev/null 2>&1; then
    echo -e "${YELLOW}📦 Installing GPG...${NC}"
    apt-get update
    apt-get install -y gnupg2
fi

# Install SSH client if not already installed
if ! command -v ssh >/dev/null 2>&1; then
    echo -e "${YELLOW}📦 Installing SSH client...${NC}"
    apt-get update
    apt-get install -y openssh-client
fi

# Create necessary directories
mkdir -p /home/vscode/.gnupg
mkdir -p /home/vscode/.ssh

# Set proper permissions
chmod 700 /home/vscode/.gnupg
chmod 700 /home/vscode/.ssh

# Configure GPG if enabled
if [ "$ENABLE_GPG_SIGNING" = "true" ]; then
    echo -e "${BLUE}🔐 Configuring GPG...${NC}"

    # Set GPG TTY
    echo 'export GPG_TTY=$(tty)' >> /home/vscode/.bashrc
    echo 'export GPG_TTY=$(tty)' >> /home/vscode/.zshrc

    # Copy GPG configuration script
    cp "$(dirname "$0")/configure-gpg-interactive.sh" /home/vscode/
    chmod +x /home/vscode/configure-gpg-interactive.sh

    # Create GPG convenience alias
    echo 'alias configure-gpg="CURSOR_AGENT=\"\" source /home/vscode/configure-gpg-interactive.sh"' >> /home/vscode/.bashrc
    echo 'alias configure-gpg="CURSOR_AGENT=\"\" source /home/vscode/configure-gpg-interactive.sh"' >> /home/vscode/.zshrc
fi

# Configure SSH if enabled
if [ "$ENABLE_SSH_AGENT" = "true" ]; then
    echo -e "${BLUE}🔑 Configuring SSH...${NC}"

    # Start SSH agent (but don't automatically add keys)
    echo 'eval "$(ssh-agent -s)"' >> /home/vscode/.bashrc
    echo 'eval "$(ssh-agent -s)"' >> /home/vscode/.zshrc

    # Create helper function to add SSH keys when needed
    echo 'load-ssh-keys() {' >> /home/vscode/.bashrc
    echo '    if [ -d ~/.ssh ] && [ "$(ls -A ~/.ssh)" ]; then' >> /home/vscode/.bashrc
    echo '        echo "Loading SSH keys..."' >> /home/vscode/.bashrc
    echo '        ssh-add ~/.ssh/id_* 2>/dev/null || true' >> /home/vscode/.bashrc
    echo '        echo "SSH keys loaded. You can now use git push/pull operations."' >> /home/vscode/.bashrc
    echo '    else' >> /home/vscode/.bashrc
    echo '        echo "No SSH keys found in ~/.ssh/"' >> /home/vscode/.bashrc
    echo '    fi' >> /home/vscode/.bashrc
    echo '}' >> /home/vscode/.bashrc

    echo 'load-ssh-keys() {' >> /home/vscode/.zshrc
    echo '    if [ -d ~/.ssh ] && [ "$(ls -A ~/.ssh)" ]; then' >> /home/vscode/.zshrc
    echo '        echo "Loading SSH keys..."' >> /home/vscode/.zshrc
    echo '        ssh-add ~/.ssh/id_* 2>/dev/null || true' >> /home/vscode/.zshrc
    echo '        echo "SSH keys loaded. You can now use git push/pull operations."' >> /home/vscode/.zshrc
    echo '    else' >> /home/vscode/.zshrc
    echo '        echo "No SSH keys found in ~/.ssh/"' >> /home/vscode/.zshrc
    echo '    fi' >> /home/vscode/.zshrc
    echo '}' >> /home/vscode/.zshrc

    # Configure Git to automatically load SSH keys when needed
    echo -e "${BLUE}🔧 Configuring Git SSH integration...${NC}"

    # Create a wrapper script that loads SSH keys before Git operations
    mkdir -p /home/vscode/.local/bin
    cat > /home/vscode/.local/bin/git-ssh-wrapper << 'EOF'
#!/bin/bash
# Git SSH wrapper that automatically loads SSH keys when needed

# Check if SSH agent is running and has keys loaded
if ! ssh-add -l >/dev/null 2>&1; then
    # SSH agent not running or no keys loaded, try to load them
    if [ -d ~/.ssh ] && [ "$(ls -A ~/.ssh)" ]; then
        echo "🔑 Loading SSH keys for Git operation..."
        ssh-add ~/.ssh/id_* 2>/dev/null || true
    fi
fi

# Execute the original SSH command
exec ssh "$@"
EOF

    chmod +x /home/vscode/.local/bin/git-ssh-wrapper

    # Configure Git to use our wrapper
    git config --global core.sshCommand "/home/vscode/.local/bin/git-ssh-wrapper"
fi

# Configure shell if enabled
if [ "$CONFIGURE_SHELL" = "true" ]; then
    echo -e "${BLUE}🐚 Configuring shell...${NC}"

    # Copy shell configuration scripts
    cp "$(dirname "$0")/shell-config.sh" /home/vscode/
    cp "$(dirname "$0")/zsh-config.sh" /home/vscode/
    chmod +x /home/vscode/shell-config.sh
    chmod +x /home/vscode/zsh-config.sh

    # Source configuration in shell profiles
    echo 'source ~/shell-config.sh' >> /home/vscode/.bashrc
    echo 'source ~/zsh-config.sh' >> /home/vscode/.zshrc
fi

# Set ownership
chown -R vscode:vscode /home/vscode/.gnupg
chown -R vscode:vscode /home/vscode/.ssh
chown -R vscode:vscode /home/vscode/.local 2>/dev/null || true
chown vscode:vscode /home/vscode/configure-gpg-interactive.sh 2>/dev/null || true
chown vscode:vscode /home/vscode/shell-config.sh 2>/dev/null || true
chown vscode:vscode /home/vscode/zsh-config.sh 2>/dev/null || true

echo -e "${GREEN}✅ Git SSH and GPG Configuration Feature installed successfully!${NC}"
echo -e "${YELLOW}💡 Run 'configure-gpg' to set up GPG signing after opening a new shell${NC}"
echo -e "${YELLOW}🔑 SSH keys will be automatically loaded when you use git push/pull operations${NC}"
echo -e "${YELLOW}💡 You can also manually run 'load-ssh-keys' if needed${NC}"
