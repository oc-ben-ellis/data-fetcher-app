# Scripts Directory

This directory contains utility scripts for the OC Fetcher project.

## Available Scripts

### Class Naming Check

`check_class_naming.py` - Validates that class names follow the project's naming conventions.

```bash
# Run class naming check
poetry run python scripts/check_class_naming.py
```

## Documentation

The project now uses **MkDocs** for documentation instead of custom build scripts. See the main project documentation for details on:

- Building documentation: `make docs`
- Development server: `make docs/serve`
- Deployment: `make docs/deploy`

For more information, run:
```bash
make docs/help
```
