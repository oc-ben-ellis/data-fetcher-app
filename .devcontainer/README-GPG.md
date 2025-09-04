# GPG Signing Configuration

This devcontainer automatically configures GPG signing for Git commits based on your available GPG keys when you open a shell.

## How It Works

1. **Automatic Detection**: When you open a shell, it automatically detects available GPG keys
2. **Agent Detection**: If running in an agent environment (like Cursor AI), it skips interactive prompts and shows status
3. **Key Selection**:
   - Uses the key specified in `.gpg_key` file if present and valid
   - If no `.gpg_key` file or invalid key, prompts user interactively
   - Falls back to first available key if user presses Enter
4. **Git Configuration**: Automatically configures Git to sign commits and tags
5. **Key Persistence**: Optionally saves the selected key to `.gpg_key` file for future use

## Setup Instructions

### Option 1: Use Your Preferred GPG Key

1. Find your GPG key ID:
   ```bash
   gpg --list-secret-keys --keyid-format=long
   ```

2. Add your key ID to the `.gpg_key` file:
   ```bash
   echo "YOUR_16_CHARACTER_KEY_ID" > .gpg_key
   ```

3. Open a new shell or run `configure-gpg` to apply the configuration

### Option 2: Interactive Selection

If no `.gpg_key` file exists or contains an invalid key, the system will:

1. **Show available keys** with their details
2. **Prompt you to enter** your preferred GPG key ID
3. **Validate the key** and check if it exists
4. **Ask if you want to save** the key to `.gpg_key` file for future use
5. **Fall back to first available key** if you just press Enter

### Option 3: Use First Available Key

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

## Manual Configuration

You can also manually configure GPG at any time by running:

```bash
configure-gpg
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

## Files

- `.gpg_key` - Contains your preferred GPG key ID (ignored by git)
- `.devcontainer/configure-gpg-interactive.sh` - Interactive configuration script
- `.devcontainer/shell-config.sh` - Shell configuration that loads GPG setup
- `.devcontainer/zsh-config.sh` - Zsh configuration that loads GPG setup
- `.devcontainer/devcontainer.json` - Container configuration with GPG mounts
