# OC Fetcher Diagrams

This directory contains Mermaid diagram files that visualize the OC Fetcher architecture.

## Available Diagrams

1. **`high_level_architecture.mmd`** - Overview of all components and their relationships
2. **`data_flow_sequence.mmd`** - Step-by-step data flow through the system
3. **`storage_architecture.mmd`** - Storage stack and data transformation flow
4. **`component_relationships.mmd`** - Detailed component interactions and dependencies

## Converting to Images

### Prerequisites

1. **Install Node.js** (if not already installed)
2. **Install Mermaid CLI**:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```

### Automatic Conversion

Use the provided script to convert all diagrams at once:

```bash
cd docs/diagrams
./convert_diagrams.sh
```

This will create:
- `png/` directory with PNG images
- `svg/` directory with SVG images

### Manual Conversion

Convert individual diagrams:

```bash
# Convert to PNG
mmdc -i high_level_architecture.mmd -o high_level_architecture.png

# Convert to SVG
mmdc -i high_level_architecture.mmd -o high_level_architecture.svg

# With transparent background
mmdc -i high_level_architecture.mmd -o high_level_architecture.png -b transparent
```

### Command Options

- `-i <input>`: Input Mermaid file
- `-o <output>`: Output image file
- `-b <background>`: Background color (e.g., `transparent`, `white`)
- `-w <width>`: Output width in pixels
- `-H <height>`: Output height in pixels

## Using the Images

Once converted, you can include the images in your documentation:

### Markdown
```markdown
![High Level Architecture](diagrams/png/high_level_architecture.png)
```

### HTML
```html
<img src="diagrams/svg/high_level_architecture.svg" alt="High Level Architecture" />
```

## Online Tools

If you prefer not to install the CLI, you can use online tools:

1. **Mermaid Live Editor**: [mermaid.live](https://mermaid.live)
   - Copy the `.mmd` file content
   - Paste into the editor
   - Export as PNG/SVG

2. **GitHub**: Mermaid diagrams render automatically in GitHub markdown files

3. **VS Code**: Use the Mermaid extension to preview and export diagrams

## Diagram Descriptions

### High Level Architecture
Shows the main components of the OC Fetcher framework including Bundle Locators, Protocol Managers, Bundle Loaders, Storage Layer, and Supporting Systems. Illustrates how data flows from external sources through the system to storage.

### Data Flow Sequence
Sequence diagram showing the step-by-step process of how a fetch operation works, from initial request through data loading, storage, and completion.

### Storage Architecture
Focuses on the composable storage system, showing how data transforms through decorators (Unzip → WARC → Bundle) before reaching base storage implementations.

### Component Relationships
Detailed view of how all components relate to each other, organized by layers (Core, Frontier, Protocol, Loader, Storage, Supporting Systems).
