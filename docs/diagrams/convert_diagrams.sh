#!/bin/bash

# OC Fetcher Architecture Diagrams Converter
# This script converts Mermaid diagrams to PNG and SVG images using Docker

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not running."
    echo "Please install Docker and ensure it's running."
    exit 1
fi

# Mermaid Docker image
MERMAID_IMAGE="minlag/mermaid-cli"

# Pull the Mermaid Docker image if not already available
echo "Ensuring Mermaid Docker image is available..."
docker pull "$MERMAID_IMAGE" > /dev/null 2>&1

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
    "module_hierarchy"
)

for diagram in "${diagrams[@]}"; do
    echo "Converting $diagram..."

    # Convert to PNG using Docker
    docker run --rm \
        -v "$(pwd):/data" \
        -w /data \
        "$MERMAID_IMAGE" \
        -i "/data/$diagram.mmd" \
        -o "/data/png/$diagram.png" \
        -b transparent
    if [ $? -eq 0 ]; then
        echo "  ✓ Created png/$diagram.png"
    else
        echo "  ✗ Failed to create png/$diagram.png"
    fi

    # Convert to SVG using Docker
    docker run --rm \
        -v "$(pwd):/data" \
        -w /data \
        "$MERMAID_IMAGE" \
        -i "/data/$diagram.mmd" \
        -o "/data/svg/$diagram.svg" \
        -b transparent
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
