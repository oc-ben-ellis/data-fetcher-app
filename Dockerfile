# Use an official Python image
FROM python:3.13-slim

# Set environment variables for Poetry
ENV POETRY_VERSION=1.8.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --create-home appuser

# Set the working directory
WORKDIR /app

# Copy only poetry files first for caching
COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry install --no-root

# Copy source code
COPY src/ /app/src/
COPY config/ /config/

RUN ls -lrta /config

# Change ownership of the working directory to the non-root user
RUN chown -R appuser:appuser /app /config

# Switch to the non-root user
USER appuser

# Add healthcheck to verify Python environment and dependencies
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys, boto3, paramiko, yaml, tenacity; sys.exit(0)"

# Set entrypoint to run the Python script
ENTRYPOINT ["python", "src/sftp_to_s3.py"]
