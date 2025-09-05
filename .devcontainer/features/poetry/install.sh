#!/bin/bash
set -e

# Install Poetry if requested
if [ "$INSTALLPOETRY" = "true" ]; then
    echo "Installing Poetry..."
    pip install poetry

    # Configure Poetry to not create virtual environments
    echo "Configuring Poetry to use system Python (no virtual environments)..."
    poetry config virtualenvs.create false
    poetry config virtualenvs.in-project false
    poetry config virtualenvs.path /tmp/poetry-venvs  # Fallback path if needed
    echo "✅ Poetry configured to install packages globally"
fi

echo "✓ Poetry feature installation completed"
