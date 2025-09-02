.PHONY: help install update test test-verbose test/with-coverage lint format clean build/for-local build/for-deployment push-to-ecr run run-local debug docker-lint pre-commit check all-checks

# Default parameter values
AWS_PROFILE ?= default
DATE ?= $(shell date +%Y%m%d)
ENV ?= play
SOURCE_ID ?=
AWS_REGION = eu-west-2
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text --profile $(AWS_PROFILE))
ECR_REPOSITORY ?= data-fetcher-sftp

# Default target
.DEFAULT_GOAL := help

# Python settings
PYTHON := python3
POETRY := poetry

# Project settings
PROJECT_NAME := data-fetcher-sftp

GIT=git
GIT_REPOSITORY_NAME=$$(basename `$(GIT) rev-parse --show-toplevel`)
GIT_COMMIT_ID=$$($(GIT) rev-parse --short HEAD)


# Directories
SRC_DIR := src
TEST_DIR := tests

check:
	@echo "Checking project settings..."
	@echo "Project Name: $(PROJECT_NAME)"
	@echo "AWS Profile: $(AWS_PROFILE)"
	@echo "AWS Region: $(AWS_REGION)"
	@echo "AWS Account ID: $(AWS_ACCOUNT_ID)"
	@echo "ECR Repository: $(ECR_REPOSITORY)"
	@echo "Date: $(DATE)"
	@echo "Environment: $(ENV)"
	@echo "Source ID: $(SOURCE_ID)"
	@echo "GIT: $(GIT)"
	@echo "Git Repository Name: $(GIT_REPOSITORY_NAME)"
	@echo "Git Commit ID: $(GIT_COMMIT_ID)"
	@echo "Mode: $(MODE)"
	@echo "Run Command: $(RUN)"
	@echo "Run No Deps Command: $(RUN_NO_DEPS)"
	@echo "SRC_DIR: $(SRC_DIR)"
	@echo "TEST_DIR: $(TEST_DIR)"
	@echo "PYTHON: $(PYTHON)"
	@echo "POETRY: $(POETRY)"
	@echo "Done."

# Colors for terminal output
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(YELLOW)$(PROJECT_NAME) Makefile$(NC)"
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies using Poetry
	@echo "Installing dependencies..."
	$(POETRY) install

update: ## Update dependencies to their latest versions
	@echo "Updating dependencies..."
	$(POETRY) update


all-checks: format lint test/with-coverage

lint: ## Run linting checks
	@echo "Running linting checks..."
	$(POETRY) run black $(SRC_DIR) $(TEST_DIR)

format: ## Format code using black and ruff
	@echo "Formatting code..."
	$(POETRY) run black $(SRC_DIR) $(TEST_DIR)

build/for-local: ## Build Docker image for local testing
	@echo "Building Docker image for local testing..."
	docker build -t "$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID)" .

build/for-deployment: ## Build Docker image for deployment (amd64 architecture)
	@echo "Building Docker image for deployment (amd64 architecture)..."
	docker buildx build --platform linux/amd64 -t "$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID)" .

push-to-ecr-play: build/for-deployment ## Push Docker image to ECR
	@echo "Pushing Docker image to ECR..."
	@echo "Authenticating with ECR..."
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	@echo "Tagging image for ECR..."
	docker tag "$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID)" "$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):$(GIT_COMMIT_ID)"
	@echo "Pushing image to ECR..."
	docker push "$(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):$(GIT_COMMIT_ID)"

run-local: ## Run the application locally using Poetry (make run-local DATE=YYYYMMDD ENV=play SOURCE_ID=us_florida)
	@echo "Running application locally with date $(DATE), environment $(ENV), and source ID $(SOURCE_ID)..."
	$(POETRY) run python $(SRC_DIR)/sftp_to_s3.py $(DATE) $(ENV) $(SOURCE_ID)

run: build/for-local ## Run the application in Docker (make run DATE=YYYYMMDD ENV=play SOURCE_ID=us_florida)
	@echo "Running Docker container with date $(DATE), environment $(ENV), and source ID $(SOURCE_ID)..."
	@echo "Mounting AWS config from $(HOME)/.aws to /home/appuser/.aws in container"
	docker run --rm \
		-v $(HOME)/.aws:/home/appuser/.aws:ro \
		-e AWS_PROFILE=$(AWS_PROFILE) \
		-e AWS_SDK_LOAD_CONFIG=1 \
		$(GIT_REPOSITORY_NAME):$(GIT_COMMIT_ID) $(DATE) $(ENV) $(SOURCE_ID)

test: ## Run tests
	@echo "Running tests..."
	$(POETRY) run pytest $(TEST_DIR)

test-verbose: ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	$(POETRY) run pytest -v $(TEST_DIR)

test/with-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(POETRY) run pytest --cov=$(SRC_DIR) $(TEST_DIR) --cov-report=term-missing

clean: ## Clean up build artifacts and cache files
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
