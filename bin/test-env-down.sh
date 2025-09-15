#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker &>/dev/null; then
  echo "docker is required" >&2
  exit 1
fi

if ! command -v terraform &>/dev/null; then
  echo "terraform is required to run destroy" >&2
  exit 1
fi

# Usage: test-env-down.sh [context_name] [port] [host]
# If args not provided, read from CONFIG_TEST_ENV_CONTEXT, CONFIG_TEST_ENV_LOCALSTACK_PORT, CONFIG_TEST_ENV_LOCALSTACK_HOST

CTX_NAME=${1:-${CONFIG_TEST_ENV_CONTEXT:-}}
PORT=${2:-${CONFIG_TEST_ENV_LOCALSTACK_PORT:-}}
HOST_ADDR=${3:-${CONFIG_TEST_ENV_LOCALSTACK_HOST:-localhost}}

if [ -z "${CTX_NAME}" ] || [ -z "${PORT}" ]; then
  echo "Missing context and/or port. Provide as arguments or set environment variables:" >&2
  echo "  export CONFIG_TEST_ENV_CONTEXT=<context>" >&2
  echo "  export CONFIG_TEST_ENV_LOCALSTACK_PORT=<port>" >&2
  echo "  export CONFIG_TEST_ENV_LOCALSTACK_HOST=<host>   # defaults to localhost" >&2
  echo "Or call: bash bin/test-env-down.sh <context> <port>" >&2
  exit 1
fi

CONTAINER_NAME="localstack-${CTX_NAME}"
DATA_DIR="tmp/.localstack"

echo "Stopping LocalStack container ${CONTAINER_NAME}..."
docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true

# Use LocalStack AWS env for terraform destroy
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2

TF_DIR="$(dirname "$0")/../infra/terraform"
if [ -d "$TF_DIR" ]; then
  echo "Destroying Terraform stack (env=local) against endpoint http://${HOST_ADDR}:${PORT} ..."
  (
    cd "$TF_DIR"
    terraform destroy -auto-approve -var env=local -var aws_use_localstack=true -var aws_region=eu-west-2 -var "aws_localstack_endpoint=http://${HOST_ADDR}:${PORT}" || true
  )
fi

echo "Done. To remove persisted data, delete ./${DATA_DIR}"
