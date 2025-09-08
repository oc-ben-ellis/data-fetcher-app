# Devcontainer Configuration

This directory contains configuration files for the OC Fetcher development container.

## Features

- Base Image: Ubuntu-based development container
- Python 3.13: With Poetry package manager (via poetry feature)
- Node.js 22.18.0: For development tools like Mermaid and Puppeteer
- Docker-in-Docker: For running containers within the devcontainer
- AWS CLI: For AWS service interactions
- Git & GitHub CLI: For version control and GitHub integration
- Poetry Feature: Dedicated feature for Poetry installation and configuration

## Files

- `devcontainer.json` - Main devcontainer configuration
- `aws-config` - AWS CLI configuration
- `git-config` - Git configuration (legacy, now handled by git-ssh feature)
- `features/` - Custom devcontainer features directory
  - `poetry/` - Poetry package manager feature
  - `git-ssh/` - Git and SSH configuration feature
  - `cursor-safe/` - Cursor-specific configuration feature
- `README.md` - This file

## CLI Tool Configuration

### Paging Disabled

The devcontainer automatically configures common CLI tools to not use paging, which improves the development experience by:

- Preventing commands from hanging on pager prompts
- Making output immediately visible in the terminal
- Avoiding the need to use `| cat` or similar workarounds

Tools affected:
- AWS CLI (`AWS_PAGER=""`)
- Git (`GIT_PAGER=cat`)
- General paging (`PAGER=cat`)
- Manual pages (`MANPAGER=cat`)
- Less/More (`LESS=""`, `MORE=""`)

### Configuration Files

The following configuration files are automatically copied and sourced:

- Shell configuration: `~/.bashrc` and `~/.zshrc` configured via git-ssh feature
- Poetry environment: `~/poetry-env.sh` configured via poetry feature
- AWS CLI config: `~/.aws/config` with paging disabled
- Git config: Applied via git-ssh feature

### Environment Variables

Key environment variables set in the devcontainer:

```bash
PAGER=cat                    # Disable general paging
AWS_PAGER=""                 # Disable AWS CLI paging
GIT_PAGER=cat                # Disable Git paging
LESS=""                      # Disable less paging
MORE=""                      # Disable more paging
MANPAGER=cat                 # Disable manual paging
PYTHONUNBUFFERED=1           # Ensure Python output is not buffered
POETRY_VENV_IN_PROJECT=1     # Keep Poetry virtual environment in project (set by poetry feature)
```

## Shell Configuration

The devcontainer automatically configures both bash and zsh shells with:

### Common Settings
- Disabled paging for CLI tools (AWS, Git, etc.)
- AWS CLI configuration
- Docker settings
- Python environment variables
- Poetry environment configuration (via poetry feature)
- Development editor settings

### Agent Session Prompts

When running in Cursor agent sessions (`CURSOR_AGENT=1`), the shells automatically switch to clean, readable prompts:

- Bash: `username@hostname:current_directory$`
- Zsh: `username@hostname:current_directory$`

This prevents the literal escape sequences (`\u@\h \W $`) from being displayed.

### Installation

The configuration is automatically installed via the `postStartCommand` in `devcontainer.json`:

1. Copies shell config files to home directory
2. Sources appropriate config in `.bashrc` and `.zshrc`
3. Sets up AWS and Git configurations

## Development Workflow

1. Container Start: The devcontainer automatically sets up all configurations
2. Shell Loading: Each new shell session sources the configuration
3. CLI Tools: All tools work without paging interruptions
4. Development: Focus on coding, not CLI tool configuration

## Manual Override

If you need to temporarily enable paging for a specific command:

```bash
# Enable paging for a single command
PAGER=less aws s3 ls

# Or use the original pager
AWS_PAGER=less aws s3 ls
```

## Customization

To add more CLI tools or modify the configuration:

1. Edit `.devcontainer/shell-config.sh` for bash/zsh environment variables
2. Edit `.devcontainer/zsh-config.sh` for zsh-specific prompt or options
3. Edit `.devcontainer/aws-config` for AWS CLI settings
4. Edit `.devcontainer/features/cursor-safe/git-config.sh` for Git settings (agent sessions only)
5. Update `.devcontainer/devcontainer.json` for container-level changes

## Troubleshooting

If prompts still show escape sequences:

1. Check current shell: `echo $0`
2. Verify config is sourced: `echo $PS1`
3. Manual source: `source ~/shell-config.sh` (bash) or `source ~/zsh-config.sh` (zsh)
4. Rebuild container: If changes don't take effect

If paging is still enabled after container restart:

1. Check if configuration files exist:
   ```bash
   ls -la ~/.aws/config ~/.gitconfig ~/shell-config.sh ~/zsh-config.sh
   ```
2. Verify shell configuration is sourced:
   ```bash
   grep "shell-config.sh" ~/.bashrc || true
   grep "zsh-config.sh" ~/.zshrc || true
   ```
3. Manually source the configuration:
   ```bash
   source ~/shell-config.sh
   source ~/zsh-config.sh
   ```

## Manual Testing

Test bash prompt:
```bash
bash -c 'export CURSOR_AGENT=1 && source ~/shell-config.sh && echo "Prompt: $PS1"'
```

Test zsh prompt:
```zsh
export CURSOR_AGENT=1 && source ~/zsh-config.sh && echo "Prompt: $PS1"
```

## Benefits

- Consistent experience: All developers get the same CLI behavior
- No interruptions: Commands complete without pager prompts
- Better automation: Scripts and CI/CD work without manual intervention
- Improved productivity: Focus on development, not tool configuration
