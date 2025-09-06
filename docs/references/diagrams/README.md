# OC Fetcher Diagrams

This directory contains Mermaid diagram source files that visualize the OC Fetcher architecture. These diagrams are rendered dynamically in the documentation using MkDocs' built-in Mermaid support.

## Available Diagrams

1. **`high_level_architecture.mmd`** - Overview of all components and their relationships
2. **`data_flow_sequence.mmd`** - Step-by-step data flow through the system
3. **`storage_architecture.mmd`** - Storage stack and data transformation flow
4. **`component_relationships.mmd`** - Detailed component interactions and dependencies
5. **`module_hierarchy.mmd`** - Module organization and dependencies

## How It Works

The diagrams are embedded directly in the documentation as inline Mermaid code blocks. MkDocs renders them dynamically using the `mermaid2` plugin, which means:

- ✅ **Always up-to-date** - Diagrams reflect the current source code
- ✅ **Responsive** - Automatically scale for different screen sizes
- ✅ **Theme-aware** - Use the site's color scheme
- ✅ **No maintenance** - No need to regenerate static images
- ✅ **Interactive** - Can be zoomed and panned in the browser

## Viewing the Diagrams

The diagrams are embedded in the following documentation pages:

- **High Level Architecture**: [Architecture Overview](../../architecture/overview/README.md#high-level-architecture)
- **Data Flow Sequence**: [Architecture Overview](../../architecture/overview/README.md#data-flow-sequence)
- **Component Relationships**: [Architecture Overview](../../architecture/overview/README.md#component-relationships)
- **Storage Architecture**: [Storage Architecture](../../architecture/storage/README.md#visual-architecture-diagram)
- **Module Hierarchy**: [Architecture Overview](../../architecture/overview/README.md#visual-representation)

## Editing Diagrams

To modify a diagram:

1. Edit the corresponding `.mmd` file in this directory
2. The changes will automatically appear in the documentation when you build the site
3. No need to convert to static images

## Mermaid Syntax

The diagrams use standard Mermaid syntax:

- **Graph diagrams**: `graph TB`, `graph LR`, `graph TD`
- **Sequence diagrams**: `sequenceDiagram`
- **Styling**: `style` directives for colors and formatting

## Online Tools

For editing and previewing diagrams, you can use:

1. **Mermaid Live Editor**: [mermaid.live](https://mermaid.live)
   - Copy the `.mmd` file content
   - Paste into the editor
   - Preview changes before committing

2. **VS Code**: Use the Mermaid extension to preview diagrams
3. **GitHub**: Mermaid diagrams render automatically in GitHub markdown files

## Diagram Descriptions

### High Level Architecture
Shows the main components of the OC Fetcher framework including Bundle Locators, Protocol Managers, Bundle Loaders, Storage Layer, and Supporting Systems. Illustrates how data flows from external sources through the system to storage.

### Data Flow Sequence
Sequence diagram showing the step-by-step process of how a fetch operation works, from initial request through data loading, storage, and completion.

### Storage Architecture
Focuses on the composable storage system, showing how data transforms through decorators (Unzip → Bundle) before reaching base storage implementations.

### Component Relationships
Detailed view of how all components relate to each other, organized by layers (Core, Frontier, Protocol, Loader, Storage, Supporting Systems).

### Module Hierarchy
Shows the organization of the codebase into focused, modular packages and their dependencies.
