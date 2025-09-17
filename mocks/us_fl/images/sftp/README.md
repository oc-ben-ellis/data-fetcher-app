# US Florida SFTP Mock Server

This directory contains a mock SFTP server for testing the US Florida SFTP configuration in the OC Fetcher project.

## Overview

The mock server simulates the real US Florida SFTP server with:
- SFTP server running on port 22
- User authentication (testuser/testpass)
- Directory structure matching the real server
- Mock data files for testing

## Directory Structure

The mock server provides the following directory structure:
```
/home/testuser/
├── doc/
│   ├── cor/                    # Daily files directory
│   │   ├── 20250829c.txt
│   │   ├── 20250913c.txt
│   │   └── 20250915c.txt
│   └── Quarterly/
│       └── Cor/
│           └── cordata.zip     # Quarterly archive
```

## Mock Data

### Daily Files
- **20250829c.txt**: Oldest date file (08/29/2025) with Florida business registration data
- **20250913c.txt**: Middle date file (09/13/2025) with Florida business registration data
- **20250915c.txt**: Most recent date file (09/15/2025) with Florida business registration data

Each daily file contains business entity registration records in fixed-width format including:
- Document numbers (starting with L, P, F, M prefixes)
- Entity names and types
- Address information
- Registered agent details

### Quarterly File
- **cordata.zip**: Quarterly corporate data archive for Q3 2025 (July-September)

## Usage

### Building the Image
```bash
cd mocks/us_fl/images/sftp
docker build -t us_fl_sftp_mock .
```

### Running the Mock Server
```bash
docker run -p 2222:22 us_fl_sftp_mock
```

### Testing SFTP Connection
```bash
# Test SFTP connection
sftp -P 2222 testuser@localhost

# Or using scp
scp -P 2222 testuser@localhost:/doc/cor/20250829c.txt ./
```

### Using with Docker Compose
The mock server is designed to work with the docker-compose environment in `mocks/environments/us_fl/`.

## Test Integration

The mock SFTP server is integrated into the test suite through:

1. **Container Fixture**: `sftp_server_container()` in `tests/test_functional/test_us_fl.py`
2. **Credential Setup**: Test secrets configured in `tests/conftest.py`
3. **Fetcher Configuration**: US_FL configuration modified to use mock endpoints
4. **Verification**: Tests verify that bundles are created with mock data

## Configuration

### SFTP Server Settings
- **Image**: `atmoz/sftp:latest`
- **User**: `testuser`
- **Password**: `testpass`
- **Port**: 22 (mapped to 2222 for testing)
- **Home Directory**: `/home/testuser`

### Test Credentials
When using this mock server for testing, use these credentials:
- **Host**: `localhost` (or container IP)
- **Port**: `2222` (mapped port)
- **Username**: `testuser`
- **Password**: `testpass`

## Manual Testing

To manually test the US_FL configuration against this mock server:

1. Start the mock server:
   ```bash
   docker run -p 2222:22 us_fl_sftp_mock
   ```

2. Set up test credentials:
   ```bash
   export OC_CREDENTIAL_PROVIDER_TYPE=environment
   export OC_CREDENTIAL_US_FL_HOST="localhost"
   export OC_CREDENTIAL_US_FL_USERNAME="testuser"
   export OC_CREDENTIAL_US_FL_PASSWORD="testpass"
   export OC_CREDENTIAL_US_FL_PORT="2222"
   ```

3. Run the fetcher:
   ```bash
   poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
   ```

This will test the complete US_FL SFTP workflow against the mock server.
