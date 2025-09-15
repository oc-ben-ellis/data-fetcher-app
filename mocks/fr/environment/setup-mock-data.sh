#!/bin/bash

# Setup Mock Data for French SIREN API Test Environment
# This script verifies the mock API is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up mock data for French SIREN API environment...${NC}"

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}Error: Docker containers are not running. Please run 'docker-compose up -d' first.${NC}"
    exit 1
fi

# Get the container name
CONTAINER_NAME=$(docker-compose ps -q siren-api)

if [ -z "$CONTAINER_NAME" ]; then
    echo -e "${RED}Error: SIREN API container not found. Please check docker-compose status.${NC}"
    exit 1
fi

echo -e "${YELLOW}Found SIREN API container: $CONTAINER_NAME${NC}"

# Get the port from environment or use default
SIREN_PORT=${SIREN_API_PORT:-5001}

echo -e "${YELLOW}Testing SIREN API endpoints on port $SIREN_PORT...${NC}"

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
if curl -f -s http://localhost:$SIREN_PORT/health > /dev/null; then
    echo -e "${GREEN}✓ Health endpoint is working${NC}"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
    echo -e "${YELLOW}Container logs:${NC}"
    docker-compose logs siren-api
    exit 1
fi

# Test OAuth token endpoint
echo -e "${YELLOW}Testing OAuth token endpoint...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:$SIREN_PORT/token \
  -H "Authorization: Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0")

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ OAuth token endpoint is working${NC}"
    echo -e "${YELLOW}Token response: $TOKEN_RESPONSE${NC}"
else
    echo -e "${RED}✗ OAuth token endpoint failed${NC}"
    echo -e "${YELLOW}Response: $TOKEN_RESPONSE${NC}"
    exit 1
fi

# Test SIREN data endpoint
echo -e "${YELLOW}Testing SIREN data endpoint...${NC}"
SIREN_RESPONSE=$(curl -s "http://localhost:$SIREN_PORT/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer mock_access_token_12345")

if echo "$SIREN_RESPONSE" | grep -q "unitesLegales"; then
    echo -e "${GREEN}✓ SIREN data endpoint is working${NC}"
    echo -e "${YELLOW}SIREN response: $SIREN_RESPONSE${NC}"
else
    echo -e "${RED}✗ SIREN data endpoint failed${NC}"
    echo -e "${YELLOW}Response: $SIREN_RESPONSE${NC}"
    exit 1
fi

# Test LocalStack
echo -e "${YELLOW}Testing LocalStack...${NC}"
LOCALSTACK_PORT=${LOCALSTACK_PORT:-4566}

if curl -f -s http://localhost:$LOCALSTACK_PORT/_localstack/health > /dev/null; then
    echo -e "${GREEN}✓ LocalStack is working${NC}"
else
    echo -e "${RED}✗ LocalStack health check failed${NC}"
    echo -e "${YELLOW}LocalStack logs:${NC}"
    docker-compose logs localstack
    exit 1
fi

echo -e "${GREEN}Mock data setup and verification completed successfully!${NC}"
echo -e "${GREEN}You can now test the FR configuration.${NC}"
echo ""
echo -e "${YELLOW}Test endpoints:${NC}"
echo -e "  Health: http://localhost:$SIREN_PORT/health"
echo -e "  Token:  http://localhost:$SIREN_PORT/token"
echo -e "  SIREN:  http://localhost:$SIREN_PORT/entreprises/sirene/V3.11/siren?q=siren:00*"
echo -e "  S3:     http://localhost:$LOCALSTACK_PORT"
