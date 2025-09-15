# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=alpine:3.22
FROM ${BASE_IMAGE}

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYENV_ROOT=/opt/pyenv \
    PATH=/opt/pyenv/bin:/opt/pyenv/shims:$PATH

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
        cargo \
        ca-certificates

# Install pyenv and Python 3.13
RUN git clone https://github.com/pyenv/pyenv.git "$PYENV_ROOT" \
    && mkdir -p "$PYENV_ROOT/plugins" \
    && echo 'export PYENV_ROOT=/opt/pyenv' >> /etc/profile \
    && echo 'export PATH="/opt/pyenv/bin:/opt/pyenv/shims:$PATH"' >> /etc/profile \
    && echo 'eval "$(pyenv init -)"' >> /etc/profile \
    && echo 'export PYENV_ROOT=/opt/pyenv' >> /etc/bash/bashrc \
    && echo 'export PATH="/opt/pyenv/bin:/opt/pyenv/shims:$PATH"' >> /etc/bash/bashrc \
    && echo 'eval "$(pyenv init -)"' >> /etc/bash/bashrc || true

# Build and set Python 3.13 as global
ARG PYTHON_VERSION=3.13
RUN /bin/bash -lc 'pyenv install "$PYTHON_VERSION"' \
    && pyenv global "$PYTHON_VERSION" \
    && python -V \
    && pip -V

# Create non-root user with sudo and grant access to pyenv directory
RUN addgroup -g ${USER_GID} ${USERNAME} \
    && adduser -D -s /bin/bash -u ${USER_UID} -G ${USERNAME} ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && chown -R ${USERNAME}:${USERNAME} ${PYENV_ROOT}

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

## Copy entrypoint and set permissions as root
COPY .devcontainer/entrypoint.sh /usr/local/bin/devcontainer-entrypoint
RUN chmod +x /usr/local/bin/devcontainer-entrypoint

## Switch to non-root user for development tooling installs
USER ${USERNAME}

# Ensure user-local bin is on PATH for poetry and tools
ENV PATH=/home/${USERNAME}/.local/bin:/opt/pyenv/bin:/opt/pyenv/shims:$PATH

# Install Poetry for the non-root user (no root pip warning)
RUN pip install --no-cache-dir --user "poetry==${POETRY_VERSION}" \
    && sudo ln -sf "/home/${USERNAME}/.local/bin/poetry" /usr/local/bin/poetry \
    || true

# Prepare directories for SSH/GPG
RUN mkdir -p /home/${USERNAME}/.ssh /home/${USERNAME}/.gnupg \
    && chmod 700 /home/${USERNAME}/.ssh /home/${USERNAME}/.gnupg



WORKDIR /workspace

ENV SHELL=/bin/bash \
    GPG_TTY=/dev/tty

ENTRYPOINT ["/usr/local/bin/devcontainer-entrypoint"]
CMD ["sleep", "infinity"]


