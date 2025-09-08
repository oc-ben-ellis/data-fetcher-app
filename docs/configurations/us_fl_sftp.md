# US_FL - US Florida SFTP Fetcher Recipe

## Summary

The `us-fl` fetcher recipe downloads files from US Florida SFTP servers with date-based filtering and automatic processing. It's designed for file-based data sources with SSH authentication and directory scanning.

## Key Features

- **SSH Authentication**: Support for SSH keys and password authentication
- **Directory Scanning**: Automatic discovery of files in remote directories
- **Date-based Filtering**: Filter files by modification date (YYYYMMDD format)
- **File Pattern Matching**: Support for regex patterns and file extensions
- **Multiple Providers**: Daily files and quarterly archives
- **Automatic Processing**: Download, validate, and store files

## Usage

```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher_app.main run us-fl

# Run with environment variable credentials
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

## Fetcher Recipe Details

### SFTP Connection
- **Default Directory**: `/doc/cor` (daily files)
- **File Patterns**: `*.txt` files
- **Quarterly Files**: `/doc/Quarterly/Cor/cordata.zip`
- **Connection Timeout**: 20 seconds
- **Rate Limiting**: 2 requests/second

### File Filtering
- **Date Filter**: Files from 2023-07-28 onwards
- **Pattern Matching**: Extracts 8-digit dates (YYYYMMDD) from filenames
- **Sorting**: By modification time (newest first)

## Credential Setup

### AWS Secrets Manager (Recommended)
```bash
aws secretsmanager create-secret \
  --name "oc-fetcher/us-fl" \
  --secret-string '{
    "host": "sftp.example.com",
    "username": "username",
    "password": "password",
    "port": 22
  }'
```

### SSH Key Authentication
```bash
aws secretsmanager create-secret \
  --name "oc-fetcher/us-fl" \
  --secret-string '{
    "host": "sftp.example.com",
    "username": "username",
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
    "port": 22
  }'
```

### Environment Variables
```bash
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"
export OC_CREDENTIAL_US_FL_PORT="22"
```

## Additional Notes

### File Discovery Process
The fetcher recipe uses two providers:
1. **Daily Provider**: Scans `/doc/cor` directory for `*.txt` files
2. **Quarterly Provider**: Downloads specific quarterly archive file

### Date Filtering Logic
- Extracts 8-digit date patterns from filenames
- Compares against start date (2023-07-28)
- Processes files with dates >= start date
- Handles parsing errors gracefully

### File Processing
- **Streaming**: Large files are streamed to avoid memory issues
- **Validation**: Basic file integrity checks
- **Storage**: Files are stored with metadata and timestamps
- **Persistence**: Progress is tracked across runs

### Error Handling
- **Connection Issues**: Automatic reconnection with backoff
- **File Access Errors**: Retry with different permissions
- **Network Issues**: Connection retry with timeout
- **Storage Errors**: Retry with different storage backend

### Performance Considerations
- **Concurrent Downloads**: Configurable parallel file downloads
- **Buffer Sizes**: Optimized for network conditions
- **Memory Usage**: Streaming prevents memory overflow
- **Progress Tracking**: Detailed logging of download progress

## Strategies Used

This fetcher recipe uses the following strategies:

- **[SftpBundleLoader](strategies/sftp/loaders/sftp_loader.md)** - File downloading and progress tracking
- **[DirectorySftpBundleLocator](strategies/sftp/locators/generic_directory_bundle_locator.md)** - Directory-based file discovery
- **[FileSftpBundleLocator](strategies/sftp/locators/generic_file_bundle_locator.md)** - Specific file path processing

## How to Test

### Prerequisites

Before testing the US_FL fetcher recipe, ensure you have:
- Docker and Docker Compose installed
- Poetry environment set up
- Access to the project repository

### Quick Test Setup

The easiest way to test the US_FL fetcher recipe is using the provided test environment:

```bash
# 1. Start the test environment
cd mocks/environments/us_fl
docker-compose up -d

# 2. Wait for services to be ready (check logs)
docker-compose logs -f

# 3. Setup mock data in the SFTP container
./setup-mock-data.sh

# 4. Set up test credentials
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_US_FL_HOST="localhost"
export OC_CREDENTIAL_US_FL_USERNAME="testuser"
export OC_CREDENTIAL_US_FL_PASSWORD="testpass"
export OC_CREDENTIAL_US_FL_PORT="2222"

# 5. Run the fetcher
cd /workspaces/data-fetcher-sftp

# Option A: Run Locally (for debugging)
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env

# Option B: Run via Docker (app-runner)
# First, build the application image
make build/for-deployment

# Then run via docker-compose app-runner
make run ARGS=us-fl
```

### Running the Fetcher

You can run the fetcher in two ways:

#### Option A: Run Locally (for debugging)
```bash
# From the project root
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_US_FL_HOST="localhost"
export OC_CREDENTIAL_US_FL_USERNAME="testuser"
export OC_CREDENTIAL_US_FL_PASSWORD="testpass"
export OC_CREDENTIAL_US_FL_PORT="2222"

# Run the fetcher locally
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

#### Option B: Run via Docker (app-runner)
```bash
# From the project root
# First, build the application image
make build/for-deployment

# Run via docker-compose app-runner
make run ARGS=us-fl
```

**Note**: The docker approach will use the project's docker-compose setup with the app-runner service.

### Manual Testing Steps

#### 1. Verify SFTP Connection
```bash
# Test SFTP access to the mock server
sftp -P 2222 testuser@localhost

# Once connected, explore the directory structure:
ls /doc/cor/
ls /doc/Quarterly/Cor/

# Download a test file
get /doc/cor/20230728_daily_data.txt
exit
```

#### 2. Verify S3 Access (LocalStack)
```bash
# Configure AWS CLI for LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Create a test bucket
aws s3 mb s3://test-bucket

# List buckets to verify
aws s3 ls
```

#### 3. Run End-to-End Test
```bash
# Ensure credentials are set (as shown above)
# Run the fetcher from project root
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

#### 4. Verify Results
```bash
# Check that bundles were created in S3
aws s3 ls s3://test-bucket/ --recursive

# Download and inspect a bundle
aws s3 cp s3://test-bucket/[bundle-path] ./test-bundle.json
cat test-bundle.json
```

### Test Environment Details

The test environment includes:

- **Mock SFTP Server**:
  - Port: 2222 (mapped from container port 22)
  - Credentials: testuser/testpass
  - Mock data: Daily files (20230728, 20230729, 20240101) and quarterly archive

- **LocalStack**:
  - Port: 4566
  - Services: S3, Secrets Manager
  - Region: us-east-1
  - Credentials: test/test

### Troubleshooting

#### Services Not Starting
```bash
# Check service health
docker-compose ps

# View detailed logs
docker-compose logs sftp-server
docker-compose logs localstack

# Restart services
docker-compose restart
```

#### Connection Issues
```bash
# Verify ports are available
netstat -tlnp | grep -E ":(2222|4566)"

# Check container status
docker-compose ps
```

#### Data Issues
```bash
# Rebuild images with fresh data
docker-compose build --no-cache

# Remove volumes and restart (clears all data)
docker-compose down -v
docker-compose up -d
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (clears all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Integration with Automated Tests

The test environment is designed to work with the existing test suite. Functional tests in `tests/test_functional/test_us_fl.py` automatically use these mock services when running:

```bash
# Run functional tests
poetry run pytest tests/test_functional/test_us_fl.py -v
```

For more detailed information about the test environment, see [US FL Test Setup](../testing/mock_environments/us_fl_test_setup.md).

## Related Documentation

- **[Creating a Recipe](creating_a_recipe.md)** - How to create new fetcher recipes
- **[Application Configuration](../user_guide/application_configuration.md)** - System configuration
- **[Command Line Usage](../user_guide/command_line_usage.md)** - Running fetcher recipes
