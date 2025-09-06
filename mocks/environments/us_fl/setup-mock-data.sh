#!/bin/bash

# Setup Mock Data for US Florida SFTP Test Environment
# This script copies mock data files into the SFTP container

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

# Create mock data directory structure in container
echo -e "${YELLOW}Creating directory structure...${NC}"
docker exec $CONTAINER_NAME mkdir -p /home/testuser/doc/cor
docker exec $CONTAINER_NAME mkdir -p /home/testuser/doc/Quarterly/Cor

# Create mock daily files
echo -e "${YELLOW}Creating mock daily files...${NC}"

# File 1: Start date file (should be included)
docker exec $CONTAINER_NAME sh -c 'cat > /home/testuser/doc/cor/20230728_daily_data.txt << EOF
Mock daily data for 20230728_daily_data.txt
Generated at 2023-07-28T10:00:00
Sample corporate data content
This is daily business registration data
Contains licensing and corporate information
Company: ABC Corp, License: FL123456, Date: 2023-07-28
Company: XYZ LLC, License: FL789012, Date: 2023-07-28
EOF'

# File 2: After start date (should be included)
docker exec $CONTAINER_NAME sh -c 'cat > /home/testuser/doc/cor/20230729_daily_data.txt << EOF
Mock daily data for 20230729_daily_data.txt
Generated at 2023-07-29T10:00:00
Sample corporate data content
This is daily business registration data
Contains licensing and corporate information
Company: DEF Inc, License: FL345678, Date: 2023-07-29
Company: GHI Corp, License: FL901234, Date: 2023-07-29
EOF'

# File 3: Future date (should be included)
docker exec $CONTAINER_NAME sh -c 'cat > /home/testuser/doc/cor/20240101_daily_data.txt << EOF
Mock daily data for 20240101_daily_data.txt
Generated at 2024-01-01T10:00:00
Sample corporate data content
This is daily business registration data
Contains licensing and corporate information
Company: JKL LLC, License: FL567890, Date: 2024-01-01
Company: MNO Corp, License: FL123789, Date: 2024-01-01
EOF'

# Create mock quarterly file
echo -e "${YELLOW}Creating mock quarterly file...${NC}"
docker exec $CONTAINER_NAME sh -c 'cat > /home/testuser/doc/Quarterly/Cor/cordata.zip << EOF
Mock quarterly corporate data
This is a ZIP file containing quarterly data
Quarter: Q3 2023
Companies: 1500
Licenses: 1200
Generated: 2023-10-01
EOF'

# Set proper ownership
echo -e "${YELLOW}Setting file ownership...${NC}"
docker exec $CONTAINER_NAME chown -R 1000:1000 /home/testuser/

# Verify files were created
echo -e "${YELLOW}Verifying mock data...${NC}"
echo "Daily files:"
docker exec $CONTAINER_NAME ls -la /home/testuser/doc/cor/
echo "Quarterly files:"
docker exec $CONTAINER_NAME ls -la /home/testuser/doc/Quarterly/Cor/

echo -e "${GREEN}Mock data setup completed successfully!${NC}"
echo -e "${GREEN}You can now test the US_FL configuration.${NC}"
