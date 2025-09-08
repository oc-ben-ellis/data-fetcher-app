# Cursor Safe Configuration Feature

This DevContainer feature provides git and AWS configuration that only applies to cursor agent shell sessions.

## What it does

- Applies git configuration only when `CURSOR_AGENT` environment variable is set
- Applies AWS CLI configuration only when `CURSOR_AGENT` environment variable is set
- Sets up git aliases and settings optimized for automated environments
- Configures AWS CLI with non-interactive settings for automated environments
- Prevents interference with user's personal configuration in interactive sessions
- Provides the same configuration as the original files but in a cursor-safe manner

## Usage

Add this feature to your `devcontainer.json`:

```json
{
    "features": {
        "./features/cursor-safe": {
            "enableAliases": true,
            "setEditor": true
        }
    }
}
```

## Options

- `enableAliases` (boolean, default: true): Enable git aliases for common commands
- `setEditor` (boolean, default: true): Set git editor to VS Code

## How it works

1. The feature installs scripts to `/usr/local/share/cursor-safe/`
2. These scripts check for the `CURSOR_AGENT` environment variable
3. Git configuration is only applied when running in a cursor agent session
4. Interactive user sessions remain unaffected

## Configuration Applied

When `CURSOR_AGENT` is set, the following configurations are applied:

### Git Configuration
- **Core settings**: pager=cat, autocrlf=input, filemode=false
- **Branch settings**: defaultBranch=main
- **Push settings**: default=simple
- **Pull settings**: rebase=false
- **Color settings**: ui=auto
- **Aliases** (if enabled): st, co, br, ci, unstage, last, visual

### AWS CLI Configuration
- **Pager settings**: cli_pager= (disabled)
- **Prompt settings**: cli_auto_prompt=off
- **Timestamp format**: cli_timestamp_format=iso8601
- **URL handling**: cli_follow_urlparam=false
- **Pager type**: cli_pager_use_bat=false

### Environment Variables
- **Paging**: PAGER=cat, AWS_PAGER="", GIT_PAGER=cat
- **AWS CLI**: AWS_CLI_AUTO_PROMPT=off, AWS_CLI_USE_INSTALLER=true
- **Other tools**: LESS="", MORE="", MANPAGER=cat

## Integration

This feature is designed to work with the existing shell configuration system. The configurations will be automatically applied when:

1. A cursor agent session is detected (`CURSOR_AGENT` is set)
2. The shell configuration sources the agent config scripts
3. Git and AWS CLI will use the cursor-safe configurations

## Dependencies

This feature requires the git feature to be installed first (handled automatically via `installsAfter`).
