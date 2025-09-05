# Poetry Feature

This devcontainer feature installs and configures Poetry package manager for Python development.

## Features

- Installs Poetry package manager
- Configures Poetry virtual environment settings
- Sets up proper PATH for Poetry virtual environment
- Creates temporary `pyproject.toml` if no project exists
- Pre-creates virtual environment with `poetry install`
- Installs pre-commit hooks

## Usage

Add this feature to your `devcontainer.json`:

```json
{
    "features": {
        "./features/poetry": {
            "installPoetry": true,
            "installPreCommit": true
        }
    }
}
```

## Options

- `installPoetry` (boolean, default: true): Install Poetry package manager
- `installPreCommit` (boolean, default: true): Install pre-commit hooks and include pre-commit as a dependency

## Virtual Environment Pre-setup

The feature automatically creates a virtual environment even if no `pyproject.toml` exists:

1. **Checks for existing project**: Looks for `pyproject.toml` in the project directory
2. **Creates temporary project**: If none exists, creates a minimal `pyproject.toml` with:
   - Basic project metadata (name, version, description, author)
   - Python 3.13 dependency
   - Pre-commit dependency (if `installPreCommit` is enabled)
   - Poetry build system configuration
3. **Pre-creates virtual environment**: Runs `poetry install --no-root` to create the virtual environment
4. **Ready for development**: The virtual environment is immediately available

This is particularly useful for:
- New projects where you want to start with a Poetry environment
- Projects that don't yet have a `pyproject.toml` file
- Development containers that need a Python environment ready immediately

## Environment Variables

This feature sets the following environment variables:

- `POETRY_VENV_IN_PROJECT=1`: Keep Poetry virtual environment in project directory
- `PYTHONUNBUFFERED=1`: Ensure Python output is not buffered
- `PATH`: Adds Poetry virtual environment bin directory to PATH

## Dependencies

This feature requires the Python feature to be installed first:

```json
{
    "features": {
        "ghcr.io/devcontainers/features/python:1": {
            "version": "3.13"
        },
        "./features/poetry": {}
    }
}
```
