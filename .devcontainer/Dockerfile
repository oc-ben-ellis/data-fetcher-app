#checkov:skip=CKV_DOCKER_2: See adr 0003-checkov-suppresions.md
FROM alpine:3.22

RUN apk add --no-cache \
    ca-certificates \
    curl \
    git \
    gnupg \
    pinentry \
    openssh-client \
    pkgconfig \
    build-base \
    shadow \
    sudo \
    tzdata \
    unzip \
    jq \
    less \
    iproute2 \
    aws-cli \
    bash \
    openssl-dev \
    bzip2-dev \
    zlib-dev \
    libffi-dev \
    readline-dev \
    sqlite-dev \
    xz-dev \
    tk-dev \
    linux-headers \
    rust \
    cargo

# Set up pyenv environment
ENV PYENV_ROOT=/opt/pyenv \
    PATH=/opt/pyenv/bin:/opt/pyenv/shims:$PATH \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Install pyenv and Python 3.13
RUN mkdir -p /opt/pyenv \
    && git clone https://github.com/pyenv/pyenv.git /opt/pyenv \
    && mkdir -p /opt/pyenv/plugins \
    && echo 'export PYENV_ROOT=/opt/pyenv' >> /etc/profile \
    && echo 'export PATH="/opt/pyenv/bin:/opt/pyenv/shims:$PATH"' >> /etc/profile \
    && echo 'eval "$(pyenv init -)"' >> /etc/profile \
    && echo 'export PYENV_ROOT=/opt/pyenv' >> /etc/bash/bashrc \
    && echo 'export PATH="/opt/pyenv/bin:/opt/pyenv/shims:$PATH"' >> /etc/bash/bashrc \
    && echo 'eval "$(pyenv init -)"' >> /etc/bash/bashrc || true

# Build and set Python 3.13 as global
ARG PYTHON_VERSION=3.13
RUN /bin/bash -lc 'source /etc/profile && pyenv install "$PYTHON_VERSION"' \
    && /bin/bash -lc 'source /etc/profile && pyenv global "$PYTHON_VERSION"' \
    && /bin/bash -lc 'source /etc/profile && python -V' \
    && /bin/bash -lc 'source /etc/profile && pip -V'

# Install Docker CLI (for host-docker via socket) and compose plugin
RUN apk add --no-cache docker-cli docker-compose

# Install BuildKit from Alpine community repository
RUN apk add --no-cache buildkit

# Install Terraform CLI from HashiCorp releases
RUN wget https://releases.hashicorp.com/terraform/1.7.2/terraform_1.7.2_linux_amd64.zip \
    && unzip terraform_1.7.2_linux_amd64.zip \
    && mv terraform /usr/local/bin/ \
    && chmod +x /usr/local/bin/terraform \
    && rm terraform_1.7.2_linux_amd64.zip \
    && terraform -v

RUN /bin/bash -lc 'source /etc/profile && pip install poetry'

WORKDIR "/code"

# move poetry cache outside root's home directory
# so virtualenvs are available to all users
RUN mkdir -p "/opt/poetry-cache"
ENV POETRY_CACHE_DIR=/opt/poetry-cache

RUN addgroup -S appuser \
    && adduser -S -G appuser -h /home/appuser -s /bin/bash appuser \
    && mkdir -p /home/appuser \
    && chown -R appuser:appuser /home/appuser
RUN chgrp appuser "/opt/poetry-cache" && chmod g+w "/opt/poetry-cache"

# install a base layer with our dependencies as these will change less frequently
COPY pyproject.toml ./
# Copy local wheel files
# Allow missing wheels dir in devcontainer context; copy if present
COPY .devcontainer/wheels/ /tmp/wheels/
# Fix ownership of copied files
RUN chown -R appuser:appuser /code /tmp/wheels
# Install dependencies without lock file to avoid local repository references
# Install local wheels first using poetry
RUN /bin/bash -lc 'source /etc/profile && poetry install --no-ansi --no-interaction --only=main --no-root'
RUN if [ -d /tmp/wheels ] && ls -1 /tmp/wheels/*.whl >/dev/null 2>&1; then \
      /bin/bash -lc 'source /etc/profile && poetry run pip install /tmp/wheels/*.whl'; \
    fi

# copy over our actual code
COPY ./ ./

# Install the package itself (without --no-root)
# Regenerate lock to reflect updated dependency pins, then install
RUN /bin/bash -lc 'source /etc/profile && poetry lock --no-ansi --no-interaction' && \
    /bin/bash -lc 'source /etc/profile && poetry install --no-ansi --no-interaction --only=main'

ENV SHELL=/bin/bash \
    GPG_TTY=/dev/tty

USER appuser

# Ensure user-local bin is on PATH for poetry and tools
ENV PATH=/home/appuser/.local/bin:/opt/pyenv/bin:/opt/pyenv/shims:$PATH

CMD ["sleep", "infinity"]
