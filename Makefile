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
	# Note: This is also set when running in VS Code terminal on host
	CONTAINER_MODE=0
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
	# Use devcontainer CLI to run commands in the dev-container environment
	RUN=@if command -v devcontainer >/dev/null 2>&1; then devcontainer exec --workspace-folder . poetry run; else ./node_modules/.bin/devcontainer exec --workspace-folder . poetry run; fi
	RUN_NO_DEPS=@if command -v devcontainer >/dev/null 2>&1; then devcontainer exec --workspace-folder . poetry run; else ./node_modules/.bin/devcontainer exec --workspace-folder . poetry run; fi
endif

# Define a function to run commands in the appropriate environment
define run_in_container
	@if [ "$(MODE)" = "local" ]; then \
		poetry run $(1); \
	else \
		if command -v devcontainer >/dev/null 2>&1; then \
			devcontainer exec --workspace-folder . poetry run $(1); \
		else \
			npx @devcontainers/cli exec --workspace-folder . poetry run $(1); \
		fi; \
	fi
endef

# Default pytest arguments for test targets
PYTEST_ARGS=-v --tb=line

# User-provided arguments (can be overridden from command line)
ARGS=

# Default number of parallel workers for tests (auto-detect CPU cores)
# Parallel execution can significantly speed up test runs, especially on multi-core systems
# Use TEST_WORKERS=1 to run tests sequentially if you encounter issues
TEST_WORKERS ?= auto

.PHONY: all-checks build/for-deployment format lint test test/not-in-parallel test/parallel test/with-coverage test/snapshot-update run run/with-observability
.PHONY: lint/black lint/ruff lint/mypy help examples debug docs docs/open headers pre-commit pre-commit/init

all-checks: format lint test/with-coverage



build/for-deployment:
	$(DOCKER) build -t "$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID)" \
	--build-arg POETRY_HTTP_BASIC_OCPY_PASSWORD \
	.

# Ensure dev-container is running for Docker mode
ensure-devcontainer:
	@if [ "$(MODE)" != "local" ]; then \
		if ! command -v devcontainer >/dev/null 2>&1; then \
			if ! command -v npx >/dev/null 2>&1; then \
				echo "Error: npx not found. Please install Node.js to use this feature."; \
				exit 1; \
			fi; \
		fi; \
		echo "Starting dev-container..."; \
		if command -v devcontainer >/dev/null 2>&1; then \
			devcontainer up --workspace-folder . --skip-post-attach; \
		else \
			npx --yes --silent @devcontainers/cli up --workspace-folder . --skip-post-attach; \
		fi; \
	fi

format: ensure-devcontainer
	-$(call run_in_container,black .)
	-$(call run_in_container,ruff check --fix .)

headers: ensure-devcontainer
	@echo "Adding standard headers to Python files..."
	$(call run_in_container,python tmp/add_headers.py)
	@echo "Headers added. Use 'make headers/dry-run' to preview changes."

headers/dry-run: ensure-devcontainer
	@echo "Previewing header changes (dry run)..."
	$(call run_in_container,python tmp/add_headers.py --dry-run)

pre-commit: ensure-devcontainer
	@echo "Installing pre-commit hooks..."
	$(call run_in_container,pre-commit install)
	@echo "Pre-commit hooks installed. They will run automatically on commit."

pre-commit/init: ensure-devcontainer
	@echo "Initializing pre-commit environments..."
	$(call run_in_container,pre-commit install-hooks)
	@echo "Pre-commit environments initialized. First run will be much faster."

lint: lint/black lint/ruff lint/mypy

lint/black: ensure-devcontainer
	$(call run_in_container,black --check .)

lint/ruff: ensure-devcontainer
	$(call run_in_container,ruff check .)

lint/mypy: ensure-devcontainer
	$(call run_in_container,mypy .)

test: ensure-devcontainer
	$(call run_in_container,pytest $(PYTEST_ARGS) -n $(TEST_WORKERS))

test/not-in-parallel: ensure-devcontainer
	$(call run_in_container,pytest $(PYTEST_ARGS))

test/parallel: ensure-devcontainer
	$(call run_in_container,pytest $(PYTEST_ARGS) -n $(TEST_WORKERS))

test/with-coverage: ensure-devcontainer
	$(call run_in_container,coverage run -m pytest $(PYTEST_ARGS) -n $(TEST_WORKERS))
	$(call run_in_container,coverage html --fail-under=0)
	@echo "Coverage report at file://$(PWD)/tmp/htmlcov/index.html"
	$(call run_in_container,coverage report)

run: ensure-devcontainer
ifeq ($(MODE),local)
	$(RUN) python -m data_fetcher.main $(ARGS)
else
	# Use devcontainer CLI for running the app
	$(RUN) python -m data_fetcher.main $(ARGS)
endif

run/with-observability:
ifeq ($(MODE),local)
	echo $(MODE)
	$(error $@ not available in MODE=$(MODE))
else
	$(error $@ not available in MODE=$(MODE) - observability requires docker-compose)
endif

help:
	@echo "Available commands:"
	@echo "  all-checks          - Run format, lint, and tests with coverage"

	@echo "  build/for-deployment - Build Docker image for deployment"
	@echo "  format              - Format code with black and ruff"
	@echo "  headers             - Add standard headers to Python files"
	@echo "  pre-commit          - Install pre-commit hooks for automatic checks"
	@echo "  pre-commit/init     - Initialize pre-commit environments (faster first run)"
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
	@echo "  - Uses DOCKER mode when running from host (uses dev-container CLI)"
	@echo "  - Can be overridden with MODE=local or MODE=docker"
	@echo ""
	@echo "Usage examples:"
	@echo "  make run ARGS=us-il"
	@echo "  make test"
	@echo "  make test/not-in-parallel"
	@echo "  make test/parallel TEST_WORKERS=4"
	@echo "  make test PYTEST_ARGS='-v -s tests/test_fetcher.py'"
	@echo "  make MODE=local run ARGS=us-fl"
	@echo "  make MODE=docker run ARGS=us-fl"
	@echo ""
	@echo "Test parallelization:"
	@echo "  TEST_WORKERS=auto  - Auto-detect CPU cores (default)"
	@echo "  TEST_WORKERS=4     - Use 4 parallel workers"
	@echo "  TEST_WORKERS=1     - Run tests sequentially"
	@echo ""
	@echo "Argument variables:"
	@echo "  ARGS               - User arguments for non-test targets (e.g., fetcher IDs)"
	@echo "  PYTEST_ARGS        - Pytest arguments (default: -v --tb=line, can be overridden)"

examples: ensure-devcontainer
	$(call run_in_container,python examples/using_config_system.py)

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

docs: ensure-devcontainer
	$(call run_in_container,build-docs)

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
