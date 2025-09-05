# Documentation Guide

This guide explains how to structure and maintain the OC Fetcher documentation, including how the build system works and best practices for contributing.

## Overview

The OC Fetcher documentation uses **MkDocs** with the Material theme to create a modern, responsive documentation site. The build process automatically:

- Converts Markdown to HTML with syntax highlighting
- Generates navigation structure from configuration
- Renders Mermaid diagrams natively
- Creates a responsive, searchable documentation site

## File Structure

### Directory Layout

```
docs/
├── index.html                    # Redirect to rendered documentation
├── overview.md                   # Main overview page
├── architecture_guide.md        # Consolidated architecture guide
├── troubleshooting.md            # Troubleshooting guide
├── deployment.md                 # Deployment guide
├── testing_guide.md              # Testing guide
├── protocol_differences.md       # Protocol explanations
├── assets/                       # Images, logos, diagrams
│   ├── OC_Fetcher_Logo_New.svg
│   └── ...
├── diagrams/                     # Architecture diagrams
│   ├── svg/
│   └── png/
├── architecture/                 # Legacy architecture files
├── configurations/              # Configuration documentation
├── application_configuration/        # System configuration
├── persistence/                 # Data persistence
└── storage/                     # Storage systems
```

### File Naming Conventions

- **Main documentation**: Use descriptive names like `troubleshooting.md`, `deployment.md`
- **Subdirectory files**: Use clear, descriptive names that indicate content
- **Assets**: Use descriptive names with appropriate extensions (`.svg`, `.png`, `.jpg`)

## Build System

### How It Works

MkDocs processes documentation in the following order:

1. **Configuration**: Reads `mkdocs.yaml` for site configuration and navigation
2. **File Discovery**: Scans for Markdown files in `docs/` and subdirectories
3. **Content Processing**: Converts Markdown to HTML with syntax highlighting
4. **Plugin Processing**: Renders Mermaid diagrams and applies other plugins
5. **Template Rendering**: Applies Material theme styling and layout

### Build Commands

```bash
# Build documentation
make docs

# Build and open in browser
make docs/open

# Direct build command
poetry run mkdocs build
```

### Output Location

Built documentation is generated in `site/` with the following structure:

```
site/
├── index.html                    # Main page (from docs/index.md)
├── documentation_guide/          # Documentation guide
├── troubleshooting/              # Troubleshooting guide
├── architecture/                 # Architecture documentation
├── configurations/               # Configuration documentation
├── application_configuration/    # Application configuration
├── persistence/                  # Persistence documentation
├── storage/                      # Storage documentation
├── testing/                      # Testing documentation
├── deployment/                   # Deployment documentation
├── assets/                       # Static assets
│   ├── stylesheets/              # CSS files
│   ├── javascripts/              # JavaScript files
│   └── images/                   # Images and diagrams
└── search/                       # Search index
```

## Writing Documentation

### Markdown Formatting

The build system supports standard Markdown with extensions:

```markdown
# Main Title (H1)
## Section Title (H2)
### Subsection (H3)

**Bold text** and *italic text*

- Bullet points
- Multiple items

1. Numbered lists
2. With descriptions

`inline code` and code blocks:

```python
def example_function():
    return "Hello, World!"
```

[Link text](url) and ![Alt text](image.png)
```

### File Structure Guidelines

#### Main Documentation Files

Place high-level documentation directly in `docs/`:

```markdown
# File: docs/overview.md
# OC Fetcher Overview

Brief description of the framework...

## Key Features

- Feature 1
- Feature 2

## Quick Start

```bash
poetry run python -m data_fetcher.main us-fl
```
```

#### Subdirectory Organization

Use subdirectories for related content:

```
docs/
├── configurations/
│   ├── README.md              # Section overview and navigation
│   ├── api.md                 # API configurations
│   ├── sftp.md                # SFTP configurations
│   └── scheduling.md          # Scheduling options
```

#### README.md Files in Subdirectories

Use `README.md` files to organize subdirectory content:

```markdown
# File: docs/configurations/README.md
# Configurations Documentation

This directory contains documentation about predefined configurations.

## Recommended Reading Order

1. **[overview.md](overview.md)** - Start here for an overview
2. **[api.md](api.md)** - API-based configurations
3. **[sftp.md](sftp.md)** - SFTP configurations
4. **[scheduling.md](scheduling.md)** - Scheduling options

## Files

- `overview.md` - Configurations overview
- `api.md` - API configuration options
- `sftp.md` - SFTP configuration and setup
- `scheduling.md` - Scheduling configurations
```

### Navigation Structure

The build system automatically creates navigation based on:

1. **File location**: Files in subdirectories become subsections
2. **README.md ordering**: Numbered lists in README files determine order
3. **File names**: Used for navigation titles (extracted from H1 headers)

#### Navigation Patterns

```markdown
# In README.md files, use numbered lists for ordering:

1. **[overview.md](overview.md)** - Start here for an overview
2. **[api.md](api.md)** - API-based configurations
3. **[sftp.md](sftp.md)** - SFTP configurations
4. **[scheduling.md](scheduling.md)** - Scheduling options
```

### Code Examples

#### Syntax Highlighting

Use language-specific code blocks:

```python
# Python code
from data_fetcher_core.registry import get_fetcher

fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)
```

```bash
# Shell commands
poetry run python -m data_fetcher.main us-fl
make docs
```

```yaml
# YAML configuration
version: '3.8'
services:
  oc-fetcher:
    build: .
    environment:
      - OC_STORAGE_TYPE=s3
```

#### Inline Code

Use backticks for inline code references:

- Function names: `get_fetcher()`
- Configuration names: `us-fl`, `fr`
- File paths: `docs/overview.md`

### Images and Diagrams

#### Supported Formats

- **SVG**: Preferred for diagrams (automatically converted to PNG)
- **PNG**: For screenshots and complex images
- **JPG**: For photographs

#### Image Placement

```markdown
# Reference images in docs/assets/
![OC Fetcher Logo](assets/OC_Fetcher_Logo_New.png)

# Reference diagrams in docs/diagrams/
![Architecture Diagram](diagrams/svg/high_level_architecture.svg)
```

#### SVG Processing

SVG files are automatically converted to PNG for better browser compatibility:

1. Place SVG files in `docs/assets/` or `docs/diagrams/svg/`
2. Build system converts them to PNG
3. HTML references PNG versions automatically

### Internal Links

#### File References

```markdown
# Link to other documentation files
See the [Architecture Guide](architecture_guide.md) for details.

# Link to subdirectory files
Check [API Configurations](configurations/api.md) for examples.

# Link to external resources
Visit [OpenCorporates](https://opencorporates.com) for more information.
```

#### Section References

```markdown
# Link to specific sections
See [Installation](#installation) for setup instructions.

# Link to subsections
Check [Docker Deployment](#docker-deployment) for container setup.
```

## Best Practices

### Content Organization

1. **Start with overview**: Each section should have a clear overview
2. **Use consistent structure**: Follow established patterns
3. **Keep it concise**: Focus on essential information
4. **Include examples**: Provide working code examples
5. **Cross-reference**: Link related content appropriately

### Writing Style

1. **Clear headings**: Use descriptive, hierarchical headings
2. **Consistent terminology**: Use the same terms throughout
3. **Active voice**: Write in active voice when possible
4. **Step-by-step instructions**: Break complex processes into steps
5. **Error handling**: Include common issues and solutions

### Code Examples

1. **Working examples**: Ensure all code examples work
2. **Context**: Provide sufficient context for examples
3. **Error handling**: Show how to handle errors
4. **Best practices**: Demonstrate recommended patterns

### Maintenance

1. **Regular updates**: Keep documentation current with code changes
2. **Version consistency**: Ensure examples match current API
3. **Link validation**: Check that internal links work
4. **Build testing**: Test documentation builds successfully

## Troubleshooting

### Common Issues

#### Build Errors

```bash
# Missing dependencies
pip install poetry
poetry install

# Build fails
poetry run mkdocs build
```

#### Navigation Issues

- **Missing README.md**: Add README.md to subdirectories for proper ordering
- **Incorrect file names**: Use descriptive, consistent naming
- **Broken links**: Check internal link syntax

#### Image Problems

- **SVG not converting**: Ensure CairoSVG is installed
- **Missing images**: Check file paths and extensions
- **Wrong size**: Optimize images for web display

### Debugging

#### Check Build Output

```bash
# Verbose build output
poetry run mkdocs build --verbose

# Check generated files
ls -la site/
```

#### Validate Links

```bash
# Check for broken links in generated HTML
grep -r "href=" site/ | grep -v "http"
```

#### Test Navigation

1. Open `site/index.html` in browser
2. Navigate through all sections
3. Check that links work correctly
4. Verify images display properly

## Contributing

### Adding New Documentation

1. **Create file**: Add new `.md` file in appropriate location
2. **Add to navigation**: Update README.md if in subdirectory
3. **Test build**: Run `make docs` to verify
4. **Review**: Check generated HTML in browser

### Updating Existing Documentation

1. **Edit file**: Modify the source `.md` file
2. **Rebuild**: Run `make docs` to regenerate
3. **Test**: Verify changes appear correctly
4. **Commit**: Include both source and rendered files

### Documentation Standards

1. **Follow structure**: Use established patterns and conventions
2. **Test examples**: Ensure all code examples work
3. **Update navigation**: Keep README.md files current
4. **Cross-reference**: Link related content appropriately

## Advanced Features

### Custom CSS

The build system generates CSS automatically, but you can customize:

1. **Modify theme**: Edit `mkdocs.yaml` configuration
2. **Add custom styles**: Extend the CSS generation
3. **Theme changes**: Update color schemes and fonts

### Extensions

The build system supports Markdown extensions:

- **Code highlighting**: Automatic syntax highlighting
- **Tables**: Full table support with styling
- **Footnotes**: Reference-style footnotes
- **Definition lists**: Term-definition pairs

### Asset Management

1. **SVG conversion**: Automatic PNG generation
2. **Image optimization**: Web-optimized output
3. **Path handling**: Automatic path resolution
4. **Caching**: Efficient rebuild process

## Summary

The OC Fetcher documentation system provides:

- **Automatic build process** with `make docs`
- **Structured navigation** based on file organization
- **Modern styling** with responsive design
- **Asset processing** for images and diagrams
- **Cross-referencing** with internal links
- **Extensible system** for customizations

Follow the established patterns and use `make docs` after any changes to keep the documentation current and well-organized.
