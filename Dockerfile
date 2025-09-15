#checkov:skip=CKV_DOCKER_2: See adr 0003-checkov-suppresions.md
FROM --platform=linux/amd64 python:3.13-alpine3.22

RUN apk add --no-cache curl cargo libffi-dev postgresql-dev gcc musl-dev

RUN pip install poetry

WORKDIR "/code"

# move poetry cache outside root's home directory
# so virtualenvs are available to all users
RUN mkdir -p "/opt/poetry-cache"
ENV POETRY_CACHE_DIR=/opt/poetry-cache

RUN addgroup -S appuser && adduser -S -G appuser appuser
RUN chgrp appuser "/opt/poetry-cache" && chmod g+w "/opt/poetry-cache"

# install a base layer with our dependencies as these will change less frequently
COPY pyproject.toml ./
# Copy local wheel files
COPY .devcontainer/wheels/*.whl /tmp/wheels/
# Fix ownership of copied files
RUN chown -R appuser:appuser /code /tmp/wheels
# Install dependencies without lock file to avoid local repository references
# Install local wheels first using poetry
RUN poetry install --no-ansi --no-interaction --only=main --no-root
RUN poetry run pip install /tmp/wheels/*.whl

# copy over our actual code
COPY ./ ./

# Install the package itself (without --no-root)
RUN poetry install --no-ansi --no-interaction --only=main

USER appuser

# Default command shows help
CMD ["poetry", "run", "python", "-m", "data_fetcher_app.main", "--help"]
