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
│   │   ├── 20230728_daily_data.txt
│   │   ├── 20230729_daily_data.txt
│   │   └── 20240101_daily_data.txt
│   └── Quarterly/
│       └── Cor/
│           └── cordata.zip     # Quarterly archive
```

## Mock Data

### Daily Files
- **20230728_daily_data.txt**: Start date file (should be included)
- **20230729_daily_data.txt**: After start date (should be included)
- **20240101_daily_data.txt**: Future date (should be included)

### Quarterly File
- **cordata.zip**: Quarterly corporate data archive

## Usage

### Building the Image
```bash
cd mocks/images/us_fl_sftp
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
scp -P 2222 testuser@localhost:/doc/cor/20230728_daily_data.txt ./
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
