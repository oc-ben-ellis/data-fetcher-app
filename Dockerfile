#checkov:skip=CKV_DOCKER_2: See adr 0003-checkov-suppresions.md
FROM --platform=linux/amd64 python:3.13-alpine3.22

RUN apt-get update && apt-get install -y curl cargo libffi-dev libpq-dev gcc && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

# move poetry cache outside root's home directory
# so virtualenvs are available to all users
RUN mkdir -p "/opt/poetry-cache"
ENV POETRY_CACHE_DIR=/opt/poetry-cache

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chgrp appuser "/opt/poetry-cache" && chmod g+w "/opt/poetry-cache"
USER appuser

WORKDIR "/code"

# placeholders for CodeArtifact repository credentials
ARG POETRY_HTTP_BASIC_OCPY_USERNAME="x"
ARG POETRY_HTTP_BASIC_OCPY_PASSWORD="x"

# Set environment variables for Poetry authentication
ENV POETRY_HTTP_BASIC_OCPY_USERNAME=${POETRY_HTTP_BASIC_OCPY_USERNAME}
ENV POETRY_HTTP_BASIC_OCPY_PASSWORD=${POETRY_HTTP_BASIC_OCPY_PASSWORD}

# install a base layer with our dependencies as these will change less frequently
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi --no-interaction

# copy over our actual code
COPY ./ ./

# poetry install again to get the actual application
RUN poetry install

# Default command shows help
CMD ["poetry", "run", "python", "-m", "data_fetcher_app.main", "--help"]
