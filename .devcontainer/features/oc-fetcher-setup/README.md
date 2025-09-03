# OC Fetcher Development Setup Feature

This DevContainer feature sets up the development environment for OC Fetcher projects.

## What it does

- Installs Poetry package manager
- Installs project dependencies via `poetry install`
- Installs Mermaid CLI for diagram generation
- Installs Puppeteer and Chrome headless shell with required system dependencies

## Usage

Add this feature to your `devcontainer.json`:

```json
{
    "features": {
        "./features/oc-fetcher-setup": {
            "installPoetry": true,
            "installMermaid": true,
            "installPuppeteer": true
        }
    }
}
```

## Options

- `installPoetry` (boolean, default: true): Install Poetry package manager
- `installMermaid` (boolean, default: true): Install Mermaid CLI for diagram generation
- `installPuppeteer` (boolean, default: true): Install Puppeteer and Chrome headless shell

## Dependencies

This feature requires the Python feature to be installed first (handled automatically via `installsAfter`).
