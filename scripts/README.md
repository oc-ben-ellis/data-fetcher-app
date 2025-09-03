# Documentation Builder

This directory contains scripts for building and maintaining the OC Fetcher documentation.

## Build Documentation

The documentation builder converts markdown files to HTML with modern styling and navigation.

### Using Poetry (Recommended)

```bash
# Build documentation
poetry run build-docs

# Or using the Makefile
make docs
```

### Using Makefile

```bash
# Build documentation
make docs

# Build and open in browser (Linux/Mac)
make docs/open
```

## What Gets Built

The builder processes the following files:
- `README.md` → `docs/rendered/index.html`
- `docs/*.md` → `docs/rendered/*.html`

## Features

- **Modern Styling**: Clean, responsive design with syntax highlighting
- **Navigation**: Sidebar navigation with all documentation pages
- **Syntax Highlighting**: Code blocks are highlighted using Pygments
- **Internal Links**: Automatically converts `.md` links to `.html` links
- **Asset Copying**: Copies images and diagrams from `docs/diagrams/` to `docs/rendered/assets/`
- **Responsive Design**: Works on desktop and mobile devices

## Output Structure

```
docs/rendered/
├── index.html              # Main documentation page (from README.md)
├── architecture.html       # Architecture documentation
├── storage.html           # Storage documentation
├── ...                    # Other documentation pages
└── assets/
    ├── style.css          # Main stylesheet
    ├── pygments.css       # Syntax highlighting styles
    └── ...                # Images and diagrams
```

## Customization

The styling can be customized by modifying the CSS in `scripts/build_docs.py`. The template uses Jinja2 for HTML generation.

## Dependencies

- `markdown`: Markdown to HTML conversion
- `jinja2`: HTML templating
- `pygments`: Syntax highlighting

These are automatically installed as dev dependencies in `pyproject.toml`.
