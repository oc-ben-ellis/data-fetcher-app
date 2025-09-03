#!/bin/bash

# OC Fetcher Architecture Diagrams Converter
# This script converts Mermaid diagrams to PNG and SVG images using mmdc

# Check if mmdc is installed
if ! command -v mmdc &> /dev/null; then
    echo "Error: mmdc (Mermaid CLI) is not installed."
    echo "Please install it using: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

# Create output directories
mkdir -p png
mkdir -p svg

echo "Converting Mermaid diagrams to PNG and SVG images..."

# Convert each diagram
diagrams=(
    "high_level_architecture"
    "data_flow_sequence"
    "storage_architecture"
    "component_relationships"
)

for diagram in "${diagrams[@]}"; do
    echo "Converting $diagram..."

    # Convert to PNG
    mmdc -i "$diagram.mmd" -o "png/$diagram.png" -b transparent
    if [ $? -eq 0 ]; then
        echo "  ✓ Created png/$diagram.png"
    else
        echo "  ✗ Failed to create png/$diagram.png"
    fi

    # Convert to SVG
    mmdc -i "$diagram.mmd" -o "svg/$diagram.svg" -b transparent
    if [ $? -eq 0 ]; then
        echo "  ✓ Created svg/$diagram.svg"
    else
        echo "  ✗ Failed to create svg/$diagram.svg"
    fi
done

echo ""
echo "Conversion complete! Images saved in:"
echo "  - png/ directory (PNG images)"
echo "  - svg/ directory (SVG images)"
echo ""
echo "You can now include these images in your documentation."
