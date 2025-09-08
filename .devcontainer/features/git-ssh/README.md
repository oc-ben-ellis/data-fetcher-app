# Git SSH and GPG Configuration Feature

This devcontainer feature configures Git with SSH and GPG signing support, providing a seamless development experience for secure Git operations.

## Features

- **GPG Signing**: Automatic configuration of GPG signing for Git commits and tags
- **SSH Support**: SSH agent configuration and key management
- **Interactive Setup**: User-friendly GPG key selection and configuration
- **Shell Integration**: Automatic configuration in both bash and zsh shells
- **Key Persistence**: Option to save selected GPG keys for future use

## Configuration Options

- `enableGpgSigning` (default: true): Enable GPG signing for Git commits and tags
- `enableSshAgent` (default: true): Enable SSH agent forwarding and configuration
- `configureShell` (default: true): Configure shell with GPG and SSH environment variables

## How It Works

1. **Automatic Detection**: When you open a shell, it automatically detects available GPG keys
2. **Agent Detection**: If running in an agent environment (like Cursor AI), it skips interactive prompts and shows status
3. **Key Selection**:
   - Uses the key specified in `.gpg_key` file if present and valid
   - If no `.gpg_key` file or invalid key, prompts user interactively
   - Falls back to first available key if user presses Enter
4. **Git Configuration**: Automatically configures Git to sign commits and tags
5. **Key Persistence**: Optionally saves the selected key to `.gpg_key` file for future use

## Usage

### Automatic Configuration

When you open a shell, the feature will:

1. **Detect available GPG keys** from mounted host directories
2. **Check for saved preferences** in `.gpg_key` file
3. **Prompt for key selection** if no preference is found
4. **Configure Git signing** with the selected key
5. **Set up SSH agent** (keys are loaded on-demand)

### Manual Configuration

You can manually configure GPG at any time by running:

```bash
configure-gpg
```

### SSH Key Management

SSH keys are **automatically loaded** when you perform Git operations that require SSH (like `git push` or `git pull`). This means:

- ✅ **No password prompts on shell startup** - keys are only loaded when needed
- ✅ **Automatic loading for Git operations** - no manual intervention required
- ✅ **Transparent operation** - Git handles SSH key loading behind the scenes

#### Manual SSH Key Loading

You can also manually load SSH keys at any time by running:

```bash
load-ssh-keys
```

This will:
1. Load all available SSH keys from `~/.ssh/`
2. Prompt for passphrases only when needed
3. Display a confirmation message when keys are loaded

### Key Management

#### Option 1: Use Your Preferred GPG Key

1. Find your GPG key ID:
   ```bash
   gpg --list-secret-keys --keyid-format=long
   ```

2. Add your key ID to the `.gpg_key` file:
   ```bash
   echo "YOUR_16_CHARACTER_KEY_ID" > .gpg_key
   ```

3. Open a new shell or run `configure-gpg` to apply the configuration

#### Option 2: Interactive Selection

If no `.gpg_key` file exists or contains an invalid key, the system will:

1. **Show available keys** with their details
2. **Prompt you to enter** your preferred GPG key ID
3. **Validate the key** and check if it exists
4. **Ask if you want to save** the key to `.gpg_key` file for future use
5. **Fall back to first available key** if you just press Enter

#### Option 3: Use First Available Key

Simply press Enter when prompted, and the system will automatically use the first available GPG key.

## Interactive Experience

When you open a shell without a valid `.gpg_key` file, you'll see something like:

```
🔐 Configuring GPG signing...
📋 Found 2 GPG key(s)
Available keys:
  • 1234567890ABCDEF - John Doe <john@example.com>
  • FEDCBA0987654321 - Jane Smith <jane@example.com>

📋 No GPG key specified in .gpg_key file
💡 To find your GPG key ID, run: gpg --list-secret-keys --keyid-format=long
   Look for a line like: sec   rsa4096/1234567890ABCDEF 2023-01-01 [SC]
   The key ID is the 16-character hex string after the slash

🔑 Please enter your GPG key ID (16-character hex string) or press Enter to use the first available key:
```

## Verification

After opening a shell or running the configuration, verify GPG signing is working:

```bash
# Check if GPG signing is configured
git config --global user.signingkey
git config --global commit.gpgsign

# Test with a commit
git commit --allow-empty -m "Test GPG signing"

# Verify the commit is signed
git log --show-signature -1
```

## Troubleshooting

- **No GPG keys found**: Ensure your GPG keys are properly mounted from the host
- **Key not found**: Verify the key ID in `.gpg_key` matches an available key
- **Signing fails**: You may need to enter your passphrase for the first commit
- **SSH issues**:
  - Check that SSH keys are properly mounted and have correct permissions
  - SSH keys are automatically loaded for Git operations, but you can manually run `load-ssh-keys` if needed
  - If you get "Permission denied" errors, check that your SSH keys are properly configured and accessible

## Files

- `.gpg_key` - Contains your preferred GPG key ID (ignored by git)
- `devcontainer-feature.json` - Feature configuration and options
- `install.sh` - Installation script that sets up the environment
- `configure-gpg-interactive.sh` - Interactive GPG configuration script
- `shell-config.sh` - Bash shell configuration that loads GPG setup
- `zsh-config.sh` - Zsh shell configuration that loads GPG setup
- `~/.local/bin/git-ssh-wrapper` - Git SSH wrapper that automatically loads SSH keys
- `README.md` - This documentation

## Dependencies

This feature requires:
- `ghcr.io/devcontainers/features/git:1` (installed automatically)
- GPG keys mounted from host (via devcontainer mounts)
- SSH keys mounted from host (via devcontainer mounts)
