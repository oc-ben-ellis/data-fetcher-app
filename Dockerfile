#checkov:skip=CKV_DOCKER_2: See adr 0003-checkov-suppresions.md
FROM --platform=linux/amd64 python:3.11-alpine3.18

RUN apk add --no-cache curl cargo libffi-dev postgresql-dev gcc musl-dev

RUN pip install poetry

# move poetry cache outside root's home directory
# so virtualenvs are available to all users
RUN mkdir -p "/opt/poetry-cache"
ENV POETRY_CACHE_DIR=/opt/poetry-cache

RUN addgroup -S appuser && adduser -S appuser -G appuser
RUN chgrp appuser "/opt/poetry-cache" && chmod g+w "/opt/poetry-cache"
USER appuser

WORKDIR "/code"

# placeholders for CodeArtifact repository credentials
ARG POETRY_HTTP_BASIC_OCPY_USERNAME="x"
ARG POETRY_HTTP_BASIC_OCPY_PASSWORD="x"

# install a base layer with our dependencies as these will change less frequently
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi --no-interaction

# copy over our actual code
COPY ./ ./

# poetry install again to get the actual application
RUN poetry install

# Default command shows help
CMD ["poetry", "run", "python", "-m", "data_fetcher.main", "--help"]
