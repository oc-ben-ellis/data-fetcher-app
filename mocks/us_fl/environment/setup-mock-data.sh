#!/bin/bash

# Setup Mock Data for US Florida SFTP Test Environment
# This script copies mock data files from test_cases inputs into the SFTP container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up mock data for US Florida SFTP environment...${NC}"

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}Error: Docker containers are not running. Please run 'docker-compose up -d' first.${NC}"
    exit 1
fi

# Get the container name
CONTAINER_NAME=$(docker-compose ps -q sftp-server)

if [ -z "$CONTAINER_NAME" ]; then
    echo -e "${RED}Error: SFTP server container not found. Please check docker-compose status.${NC}"
    exit 1
fi

echo -e "${YELLOW}Found SFTP container: $CONTAINER_NAME${NC}"

# Get the script directory and find test_cases inputs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_CASES_INPUTS_DIR="$SCRIPT_DIR/../test_cases/basic/inputs"

# Check if test_cases inputs directory exists
if [ ! -d "$TEST_CASES_INPUTS_DIR" ]; then
    echo -e "${RED}Error: Test cases inputs directory not found at $TEST_CASES_INPUTS_DIR${NC}"
    exit 1
fi

# Create mock data directory structure in container
echo -e "${YELLOW}Creating directory structure...${NC}"
docker exec $CONTAINER_NAME mkdir -p /home/test/doc/cor
docker exec $CONTAINER_NAME mkdir -p /home/test/doc/Quarterly/Cor

# Copy mock daily files from test_cases inputs
echo -e "${YELLOW}Copying mock daily files from test_cases inputs...${NC}"

# Copy daily files from test_cases inputs
if [ -d "$TEST_CASES_INPUTS_DIR/cor" ]; then
    for file in "$TEST_CASES_INPUTS_DIR/cor"/*.txt; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo -e "${YELLOW}Copying $filename...${NC}"
            docker cp "$file" "$CONTAINER_NAME:/home/test/doc/cor/$filename"
        fi
    done
else
    echo -e "${RED}Error: Daily files directory not found at $TEST_CASES_INPUTS_DIR/cor${NC}"
    exit 1
fi

# Copy quarterly file from test_cases inputs
echo -e "${YELLOW}Copying mock quarterly file from test_cases inputs...${NC}"
if [ -d "$TEST_CASES_INPUTS_DIR/Quarterly/Cor" ]; then
    for file in "$TEST_CASES_INPUTS_DIR/Quarterly/Cor"/*.zip; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo -e "${YELLOW}Copying $filename...${NC}"
            docker cp "$file" "$CONTAINER_NAME:/home/test/doc/Quarterly/Cor/$filename"
        fi
    done
else
    echo -e "${RED}Error: Quarterly files directory not found at $TEST_CASES_INPUTS_DIR/Quarterly/Cor${NC}"
    exit 1
fi

# Verify files were created
echo -e "${YELLOW}Verifying mock data...${NC}"
echo "Daily files:"
docker exec $CONTAINER_NAME ls -la /home/test/doc/cor/
echo "Quarterly files:"
docker exec $CONTAINER_NAME ls -la /home/test/doc/Quarterly/Cor/

echo -e "${GREEN}Mock data setup completed successfully!${NC}"
echo -e "${GREEN}You can now test the US_FL configuration.${NC}"