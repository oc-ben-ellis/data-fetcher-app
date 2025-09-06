# Docker Usage

This guide covers how to run the Data Fetcher application using Docker and Docker Compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- AWS credentials configured (for accessing AWS CodeArtifact for Python packages)

## Building the Docker Image

### Build for Deployment

```bash
# Build the Docker image
make build/for-deployment
```

This creates an image tagged with the repository name and git commit ID.

### Build with Custom Tag

```bash
# Build with custom tag
docker build -t data-fetcher-sftp:latest .
```

## Running with Docker Compose

### Basic Usage

```bash
# Run US Florida SFTP fetcher
make run ARGS=us-fl

# Run France API fetcher
make run ARGS=fr
```

**Note**: The Makefile currently has a bug where it references `data_fetcher.main` instead of `data_fetcher_app.main`. Use the direct Docker commands below for now.

### With Observability

```bash
# Run with observability features (logging, monitoring)
make run/with-observability ARGS=us-fl
```

## Direct Docker Commands

### Run Specific Configuration

```bash
# Run US Florida configuration
docker run --rm \
  -e AWS_PROFILE=your-profile \
  data-fetcher-sftp:latest us-fl

# Run France API configuration
docker run --rm \
  -e AWS_PROFILE=your-profile \
  data-fetcher-sftp:latest fr
```

### With Environment Variables

```bash
# Run with environment variable credentials
docker run --rm \
  -e OC_CREDENTIAL_US_FL_HOST="sftp.example.com" \
  -e OC_CREDENTIAL_US_FL_USERNAME="username" \
  -e OC_CREDENTIAL_US_FL_PASSWORD="password" \
  -e OC_CREDENTIAL_PROVIDER_TYPE="environment" \
  data-fetcher-sftp:latest us-fl
```

### With Volume Mounts

```bash
# Mount local directory for output
docker run --rm \
  -v $(pwd)/output:/app/output \
  -e AWS_PROFILE=your-profile \
  data-fetcher-sftp:latest us-fl
```

## Docker Compose Configuration

The project includes a `docker-compose.yml` file for development and testing.

### Development Setup

```bash
# Set up the development environment
make setup

# Run the build pipeline
make build-pipeline

# Clean up containers
make clean-pipeline
```

### Custom Docker Compose

```yaml
version: '3.8'
services:
  data-fetcher:
    build: .
    environment:
      - AWS_PROFILE=your-profile
      - OC_CONFIG_ID=us-fl
    volumes:
      - ./output:/app/output
    command: ["us-fl"]
```

## Environment Variables

### AWS Configuration

```bash
# Set AWS profile
export AWS_PROFILE=your-profile

# Set AWS region
export AWS_REGION=eu-west-2
```

### Application Configuration

```bash
# Set configuration ID
export OC_CONFIG_ID=us-fl

# Set credential provider
export OC_CREDENTIAL_PROVIDER_TYPE=aws

# Set log level
export OC_LOG_LEVEL=INFO
```

### Credential Variables (for environment provider)

```bash
# US Florida SFTP credentials
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# France API credentials
export OC_CREDENTIAL_FR_API_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_API_CLIENT_SECRET="client-secret"
```

## Production Deployment

### AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-west-2.amazonaws.com
docker tag data-fetcher-sftp:latest <account-id>.dkr.ecr.eu-west-2.amazonaws.com/data-fetcher-sftp:latest
docker push <account-id>.dkr.ecr.eu-west-2.amazonaws.com/data-fetcher-sftp:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-fetcher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: data-fetcher
  template:
    metadata:
      labels:
        app: data-fetcher
    spec:
      containers:
      - name: data-fetcher
        image: data-fetcher-sftp:latest
        env:
        - name: OC_CONFIG_ID
          value: "us-fl"
        - name: AWS_PROFILE
          value: "default"
```

## Monitoring and Logging

### Log Output

Docker containers output structured JSON logs:

```bash
# View logs
docker logs <container-id>

# Follow logs
docker logs -f <container-id>
```

### Health Checks

```bash
# Check container status
docker ps

# Check container logs
docker logs <container-id>
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

2. **AWS Credentials Not Found**
   ```bash
   # Check AWS configuration
   aws configure list

   # Set AWS profile
   export AWS_PROFILE=your-profile
   ```

3. **Docker Build Fails**
   ```bash
   # Clean Docker cache
   docker system prune -a

   # Rebuild without cache
   docker build --no-cache -t data-fetcher-sftp:latest .
   ```

4. **Container Exits Immediately**
   ```bash
   # Check container logs
   docker logs <container-id>

   # Run interactively for debugging
   docker run -it data-fetcher-sftp:latest /bin/bash
   ```

### Debug Mode

```bash
# Run with debug logging
docker run --rm \
  -e OC_LOG_LEVEL=DEBUG \
  -e AWS_PROFILE=your-profile \
  data-fetcher-sftp:latest us-fl
```

## Best Practices

### Security

- Use AWS Secrets Manager for production credentials
- Don't hardcode credentials in Docker images
- Use least-privilege IAM roles
- Regularly update base images

### Performance

- Use multi-stage builds to reduce image size
- Mount volumes for persistent data
- Configure appropriate resource limits
- Use health checks for monitoring

### Development

- Use Docker Compose for local development
- Mount source code for live reloading
- Use development-specific environment variables
- Test with different configurations

## Examples

### Complete Workflow

```bash
# 1. Build the image
make build/for-deployment

# 2. Run with Docker Compose
make run ARGS=us-fl

# 3. Check logs
docker-compose logs app-runner

# 4. Clean up
make clean-pipeline
```

### Custom Configuration

```bash
# Run with custom environment
docker run --rm \
  -e OC_CONFIG_ID=fr \
  -e OC_CREDENTIAL_PROVIDER_TYPE=environment \
  -e OC_CREDENTIAL_FR_CLIENT_ID="your-client-id" \
  -e OC_CREDENTIAL_FR_CLIENT_SECRET="your-client-secret" \
  data-fetcher-sftp:latest fr
```
