SHELL=/bin/bash
DOCKER=BUILDKIT_PROGRESS=plain docker
DOCKER_COMPOSE=USER_ID=$$(id -u) GROUP_ID=$$(id -g) BUILDKIT_PROGRESS=plain docker-compose
GIT_REPOSITORY_NAME=$$(basename `git rev-parse --show-toplevel`)
GIT_COMMIT_ID=$$(git rev-parse --short HEAD)

# Default parameter values
AWS_PROFILE ?= default
DATE ?= $(shell date +%Y%m%d)
ENV ?= play
SOURCE_ID ?=
AWS_REGION = eu-west-2
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text --profile $(AWS_PROFILE))
ECR_REPOSITORY ?= data-fetcher-sftp

# Auto-detect if we're running inside a container
# Check for common container environment variables
ifdef REMOTE_CONTAINERS
	# Dev Container environment
	CONTAINER_MODE=1
else ifdef DOCKER_CONTAINER
	# Docker container environment
	CONTAINER_MODE=1
else ifdef KUBERNETES_SERVICE_HOST
	# Kubernetes environment
	CONTAINER_MODE=1
else ifdef AWS_EXECUTION_ENV
	# AWS Lambda/ECS environment
	CONTAINER_MODE=1
else ifdef CONTAINER
	# Generic container environment
	CONTAINER_MODE=1
else ifeq ($(USER),vscode)
	# Dev Container environment (detected by USER=vscode)
	CONTAINER_MODE=1
else ifeq ($(TERM_PROGRAM),vscode)
	# Dev Container environment (detected by TERM_PROGRAM=vscode)
	CONTAINER_MODE=1
else
	# Check if /.dockerenv file exists (Docker container indicator)
	CONTAINER_MODE=$$(shell ls /.dockerenv >/dev/null 2>&1 && echo 1 || echo 0)
endif

# Set LOCAL mode automatically if in container, unless explicitly overridden
ifdef CONTAINER_MODE
	ifeq ($(CONTAINER_MODE),1)
		ifeq ($(MODE),)
			MODE=local
		endif
	endif
endif

ifeq ($(MODE), local)
	RUN=poetry run
	RUN_NO_DEPS=poetry run
else
	RUN=$(DOCKER_COMPOSE) --profile run-app run --rm fetcher poetry run
	RUN_NO_DEPS=$(DOCKER_COMPOSE) run --rm --no-deps fetcher poetry run
endif

ARGS=-v --tb=line
# Default number of parallel workers for tests (auto-detect CPU cores)
# Parallel execution can significantly speed up test runs, especially on multi-core systems
# Use TEST_WORKERS=1 to run tests sequentially if you encounter issues
TEST_WORKERS ?= auto

.PHONY: all-checks build/for-local build/for-deployment format lint test test/not-in-parallel test/parallel test/with-coverage test/snapshot-update run run/with-observability
.PHONY: lint/black lint/ruff lint/mypy help examples debug docs docs/open headers pre-commit

all-checks: format lint test/with-coverage

build/for-local:
	$(DOCKER_COMPOSE) build fetcher

build/for-deployment:
	$(DOCKER) build -t "$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID)" \
	--build-arg POETRY_HTTP_BASIC_OCPY_USERNAME \
	--build-arg POETRY_HTTP_BASIC_OCPY_PASSWORD \
	.

format:
	-$(RUN_NO_DEPS) black .
	-$(RUN_NO_DEPS) ruff check --fix .

headers:
	@echo "Adding standard headers to Python files..."
	$(RUN_NO_DEPS) python tmp/add_headers.py
	@echo "Headers added. Use 'make headers/dry-run' to preview changes."

headers/dry-run:
	@echo "Previewing header changes (dry run)..."
	$(RUN_NO_DEPS) python tmp/add_headers.py --dry-run

pre-commit:
	@echo "Installing pre-commit hooks..."
	$(RUN_NO_DEPS) pre-commit install
	@echo "Pre-commit hooks installed. They will run automatically on commit."

lint: lint/black lint/ruff lint/mypy

lint/black:
	$(RUN_NO_DEPS) black --check .

lint/ruff:
	$(RUN_NO_DEPS) ruff .

lint/mypy:
	$(RUN_NO_DEPS) mypy .

test:
	$(RUN) pytest $(ARGS) -n $(TEST_WORKERS)

test/not-in-parallel:
	$(RUN) pytest $(ARGS)

test/parallel:
	$(RUN) pytest $(ARGS) -n $(TEST_WORKERS)

test/with-coverage:
	$(RUN) coverage run -m pytest $(ARGS) -n $(TEST_WORKERS)
	$(RUN_NO_DEPS) coverage html --fail-under=0
	@echo "Coverage report at file://$(PWD)/tmp/htmlcov/index.html"
	$(RUN_NO_DEPS) coverage report

run:
ifeq ($(MODE),local)
	$(RUN) python -m oc_fetcher.main $(ARGS)
else
	$(DOCKER_COMPOSE) --profile run-app up
endif

run/with-observability:
ifeq ($(MODE),local)
	echo $(MODE)
	$(error $@ not available in MODE=$(MODE))
else
	$(DOCKER_COMPOSE) --profile run-app -f docker-compose.yml -f docker-compose.observability.yml up
endif

help:
	@echo "Available commands:"
	@echo "  all-checks          - Run format, lint, and tests with coverage"
	@echo "  build/for-local     - Build Docker image for local development"
	@echo "  build/for-deployment - Build Docker image for deployment"
	@echo "  format              - Format code with black and ruff"
	@echo "  headers             - Add standard headers to Python files"
	@echo "  pre-commit          - Install pre-commit hooks for automatic checks"
	@echo "  lint                - Run all linters"
	@echo "  test                - Run tests in parallel (default, faster)"
	@echo "  test/not-in-parallel - Run tests sequentially (fallback)"
	@echo "  test/parallel      - Run tests in parallel (explicit)"
	@echo "  test/with-coverage - Run tests with coverage report (parallel)"
	@echo "  run                 - Run the fetcher (use ARGS=<fetcher_id>)"
	@echo "  docs                - Build HTML documentation from markdown files"
	@echo "  docs/open           - Build and open documentation in browser"
	@echo "  examples            - Run example scripts"
	@echo "  debug               - Show environment detection and mode settings"
	@echo ""
	@echo "Mode detection:"
	@echo "  - Automatically detects container environments (Docker, DevContainer, etc.)"
	@echo "  - Uses LOCAL mode (poetry run) when in containers"
	@echo "  - Uses DOCKER mode when running from host"
	@echo "  - Can be overridden with MODE=local or MODE=docker"
	@echo ""
	@echo "Usage examples:"
	@echo "  make run ARGS=us-il"
	@echo "  make test ARGS=tests/test_fetcher.py"
	@echo "  make test/not-in-parallel ARGS=tests/test_fetcher.py"
	@echo "  make test/parallel TEST_WORKERS=4 ARGS=tests/test_fetcher.py"
	@echo "  make MODE=local run ARGS=us-fl"
	@echo "  make MODE=docker run ARGS=us-fl"
	@echo ""
	@echo "Test parallelization:"
	@echo "  TEST_WORKERS=auto  - Auto-detect CPU cores (default)"
	@echo "  TEST_WORKERS=4     - Use 4 parallel workers"
	@echo "  TEST_WORKERS=1     - Run tests sequentially"

examples:
	$(RUN) python examples/using_config_system.py

debug:
	@echo "Environment detection:"
	@echo "  REMOTE_CONTAINERS: $(REMOTE_CONTAINERS)"
	@echo "  DOCKER_CONTAINER: $(DOCKER_CONTAINER)"
	@echo "  KUBERNETES_SERVICE_HOST: $(KUBERNETES_SERVICE_HOST)"
	@echo "  AWS_EXECUTION_ENV: $(AWS_EXECUTION_ENV)"
	@echo "  CONTAINER: $(CONTAINER)"
	@echo "  USER: $(USER)"
	@echo "  TERM_PROGRAM: $(TERM_PROGRAM)"
	@echo "  /.dockerenv exists: $$(shell ls /.dockerenv >/dev/null 2>&1 && echo yes || echo no)"
	@echo ""
	@echo "Mode settings:"
	@echo "  CONTAINER_MODE: $(CONTAINER_MODE)"
	@echo "  MODE: $(MODE)"
	@echo "  RUN command: $(RUN)"
	@echo "  RUN_NO_DEPS command: $(RUN_NO_DEPS)"

docs:
	$(RUN_NO_DEPS) build-docs

docs/open:
	$(RUN_NO_DEPS) build-docs
	@echo "Opening documentation in browser..."
	@if command -v xdg-open >/dev/null 2>&1; then \
		xdg-open docs/rendered/index.html; \
	elif command -v open >/dev/null 2>&1; then \
		open docs/rendered/index.html; \
	else \
		echo "Please open docs/rendered/index.html in your browser"; \
	fi
