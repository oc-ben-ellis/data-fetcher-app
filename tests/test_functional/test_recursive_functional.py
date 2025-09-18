import os
import shutil
import subprocess
import sys
from pathlib import Path

import boto3
import pytest

# Hardcode the list so we can explicitly add new data_registry_ids later
DATA_REGISTRY_IDS = [
    "fr",
    "us_fl",
]


FETCHER_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = FETCHER_DIR
MOCKS_DIR = FETCHER_DIR / "mocks"


def _docker_compose_cmd() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("docker or docker-compose is required for functional tests")


def _aws_client(service: str, endpoint_url: str):
    return boto3.client(
        service,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"),
        endpoint_url=endpoint_url,
    )


@pytest.fixture(scope="session")
def localstack_session() -> dict[str, str]:
    up_script = PROJECT_ROOT / "bin" / "test-env-up.sh"
    if not up_script.exists():
        pytest.skip("test-env-up.sh not found")

    # Start LocalStack and infra; capture exported env vars for this session
    # Use a random context name to avoid container name conflicts
    import secrets
    context_name = f"pytest-{secrets.token_hex(4)}"
    try:
        result = subprocess.run(
            ["bash", str(up_script), "--env-vars-only", context_name],
            check=True,
            cwd=FETCHER_DIR,
            text=True,
            capture_output=True,
            timeout=900,
        )
        # Parse export lines like: export KEY=value
        for line in (result.stdout or "").splitlines():
            if line.startswith("export ") and "=" in line:
                key, value = line[7:].split("=", 1)
                os.environ[key] = value
    except subprocess.CalledProcessError as e:
        pytest.fail(f"test-env-up.sh failed: {e.stderr}")

    # Prefer AWS_ENDPOINT_URL if provided; otherwise derive from port
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint:
        port = os.environ.get("CONFIG_TEST_ENV_LOCALSTACK_PORT", "4566")
        host = os.environ.get("CONFIG_TEST_ENV_LOCALSTACK_HOST", "localhost")
        endpoint = f"http://{host}:{port}"

    # Ensure config and storage buckets exist (idempotent)
    s3 = _aws_client("s3", endpoint)
    bucket = os.environ.get("OC_DATA_PIPELINE_CONFIG_S3_BUCKET", "oc-local-data-config")
    region = os.environ.get("AWS_DEFAULT_REGION", "eu-west-2")
    try:
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    except (ConnectionError, OSError, TimeoutError) as e:
        pytest.skip(f"LocalStack not reachable: {type(e).__name__}: {e}")
    except Exception as e:
        pytest.fail(
            f"Unexpected error connecting to LocalStack: {type(e).__name__}: {e}"
        )
    if bucket not in existing:
        params = {"Bucket": bucket}
        if region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**params)

    storage_bucket = os.environ.get(
        "OC_DATA_PIPELINE_STORAGE_S3_URL", "s3://oc-local-data-pipeline"
    ).split("//", 1)[-1]
    try:
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    except Exception:
        existing = []
    if storage_bucket not in existing:
        params = {"Bucket": storage_bucket}
        if region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**params)

    # Read redis from env if provided by script
    redis_host = os.environ.get("OC_KV_STORE_REDIS_HOST", "localhost")
    redis_port = os.environ.get("OC_KV_STORE_REDIS_PORT", "6379")

    session_data = {
        "endpoint": endpoint,
        "bucket": bucket,
        "storage_bucket": storage_bucket,
        "redis_host": redis_host,
        "redis_port": redis_port,
        "context_name": context_name,
    }

    yield session_data

    # Cleanup: Use the proper test-env-down.sh script
    down_script = PROJECT_ROOT / "bin" / "test-env-down.sh"
    if down_script.exists():
        try:
            subprocess.run(
                ["bash", str(down_script), context_name],
                check=False,
                cwd=FETCHER_DIR,
                text=True,
                capture_output=True,
                timeout=180,
            )
        except Exception:
            # Best-effort cleanup, ignore errors
            pass


def _upload_configs_to_s3(
    registry_id: str, bucket: str, endpoint: str, step: str
) -> str:
    s3 = _aws_client("s3", endpoint)
    config_root = MOCKS_DIR / registry_id / "config"
    if not config_root.exists():
        raise FileNotFoundError(f"Configs not found for {registry_id}: {config_root}")

    # Clear any existing configs for this registry to avoid stale downloads
    existing = s3.list_objects_v2(Bucket=bucket, Prefix=f"configs/{registry_id}/")
    if existing.get("Contents"):
        s3.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": o["Key"]} for o in existing["Contents"]]},
        )

    # Upload recursively with key prefix equal to registry_id/
    for root, _dirs, files in os.walk(config_root):
        for name in files:
            local_path = Path(root) / name
            rel = local_path.relative_to(config_root)
            # Upload under step prefix used by app (e.g., fetcher)
            key = f"configs/{registry_id}/{step}/{rel.as_posix()}"
            s3.upload_file(str(local_path), bucket, key)
    return f"s3://{bucket}/configs/{registry_id}/{step}/"


def _create_sftp_secrets(endpoint: str) -> None:
    """Create SFTP credentials in AWS Secrets Manager for US_FL."""
    secrets_client = _aws_client("secretsmanager", endpoint)
    
    # Create the SFTP credentials secret
    secret_value = {
        "host": "host.docker.internal",
        "username": "test", 
        "password": "test",
        "port": "2222"
    }
    
    import json
    
    try:
        secrets_client.create_secret(
            Name="us-fl-sftp-credentials",
            SecretString=json.dumps(secret_value)
        )
    except secrets_client.exceptions.ResourceExistsException:
        # Secret already exists, update it
        secrets_client.update_secret(
            SecretId="us-fl-sftp-credentials",
            SecretString=json.dumps(secret_value)
        )


def _setup_sftp_mock_data() -> None:
    """Set up mock data in the SFTP server."""
    # Get the SFTP container name
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=sftp-server", "--format", "{{.Names}}"],
        check=True,
        text=True,
        capture_output=True,
    )
    container_name = result.stdout.strip()
    
    if not container_name:
        raise RuntimeError("SFTP server container not found")
    
    # Create directory structure
    subprocess.run(
        ["docker", "exec", container_name, "mkdir", "-p", "/home/test/doc/cor"],
        check=True,
    )
    subprocess.run(
        ["docker", "exec", container_name, "mkdir", "-p", "/home/test/doc/Quarterly/Cor"],
        check=True,
    )
    
    # Copy mock files from test_cases inputs
    test_cases_inputs_dir = MOCKS_DIR / "us_fl" / "test_cases" / "basic" / "inputs"
    
    # Copy daily files
    cor_dir = test_cases_inputs_dir / "cor"
    if cor_dir.exists():
        for file_path in cor_dir.glob("*.txt"):
            filename = file_path.name
            subprocess.run(
                ["docker", "cp", str(file_path), f"{container_name}:/home/test/doc/cor/{filename}"],
                check=True,
            )
    
    # Copy quarterly file
    quarterly_dir = test_cases_inputs_dir / "Quarterly" / "Cor"
    if quarterly_dir.exists():
        for file_path in quarterly_dir.glob("*.zip"):
            filename = file_path.name
            subprocess.run(
                ["docker", "cp", str(file_path), f"{container_name}:/home/test/doc/Quarterly/Cor/{filename}"],
                check=True,
            )


def _remove_sftp_secrets(endpoint: str) -> None:
    """Remove SFTP credentials from AWS Secrets Manager."""
    secrets_client = _aws_client("secretsmanager", endpoint)
    
    try:
        secrets_client.delete_secret(
            SecretId="us-fl-sftp-credentials",
            ForceDeleteWithoutRecovery=True
        )
    except secrets_client.exceptions.ResourceNotFoundException:
        # Secret doesn't exist, that's fine
        pass


def _remove_configs_from_s3(registry_id: str, bucket: str, endpoint: str) -> None:
    s3 = _aws_client("s3", endpoint)
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{registry_id}/")
    while True:
        contents = resp.get("Contents", [])
        if contents:
            s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in contents]},
            )
        if resp.get("IsTruncated"):
            resp = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=f"{registry_id}/",
                ContinuationToken=resp["NextContinuationToken"],
            )
        else:
            break


def _purge_all_test_queues(endpoint: str) -> None:
    sqs = _aws_client("sqs", endpoint)
    urls = sqs.list_queues().get("QueueUrls", [])
    for url in urls:
        try:
            sqs.purge_queue(QueueUrl=url)
            sqs.delete_queue(QueueUrl=url)
        except Exception:
            # Ignore errors to keep cleanup best-effort
            pass


def _clear_bucket(bucket: str, endpoint: str, prefix: str = "") -> None:
    s3 = _aws_client("s3", endpoint)
    list_kwargs = {"Bucket": bucket}
    if prefix:
        list_kwargs["Prefix"] = prefix
    resp = s3.list_objects_v2(**list_kwargs)
    while True:
        contents = resp.get("Contents", [])
        if contents:
            s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": o["Key"]} for o in contents]},
            )
        if resp.get("IsTruncated"):
            resp = s3.list_objects_v2(
                **{
                    **list_kwargs,
                    "ContinuationToken": resp["NextContinuationToken"],
                }
            )
        else:
            break


def _flush_redis(host: str, port: str | int) -> None:
    try:
        import redis  # type: ignore[import-not-found]

        client = redis.Redis(host=host, port=int(port), db=0, socket_connect_timeout=1)
        client.flushall()
    except Exception:
        # Best-effort; ignore if redis not reachable or library missing
        pass


def _clear_config_bucket(bucket: str, endpoint: str) -> None:
    # Best-effort: remove any non-registry prefixes created during tests
    s3 = _aws_client("s3", endpoint)
    resp = s3.list_objects_v2(Bucket=bucket)
    if resp.get("Contents"):
        s3.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": o["Key"]} for o in resp["Contents"]]},
        )


@pytest.fixture(params=DATA_REGISTRY_IDS, scope="module")
def registry_env(request, localstack_session):
    registry_id = request.param
    endpoint = localstack_session["endpoint"]
    bucket = localstack_session["bucket"]
    step = "fetch"

    # Upload registry configs to S3
    _upload_configs_to_s3(registry_id, bucket, endpoint, step)
    
    # Create AWS secrets for SFTP credentials
    if registry_id == "us_fl":
        print(f"Creating SFTP secrets for {registry_id}")
        _create_sftp_secrets(endpoint)
        print(f"SFTP secrets created successfully")

    # Bring up mocks for this registry (LocalStack is not managed here)
    env_dir = MOCKS_DIR / registry_id / "environment"
    if env_dir.exists():
        # Bring down any existing stack and remove orphans, ignore errors
        down_cmd = [*_docker_compose_cmd(), "down", "--remove-orphans"]
        subprocess.run(
            down_cmd,
            check=False,
            cwd=env_dir,
            text=True,
            capture_output=True,
            timeout=180,
        )

        # Bring the environment up
        print(f"Starting SFTP server for {registry_id}")
        up_cmd = [*_docker_compose_cmd(), "up", "-d"]
        result = subprocess.run(
            up_cmd,
            check=True,
            cwd=env_dir,
            text=True,
            capture_output=True,
            timeout=300,
        )
        print(f"SFTP server started: {result.stdout}")
        
        # Wait a moment for the server to be ready
        import time
        time.sleep(5)
        
        # Set up mock data in the SFTP server
        if registry_id == "us_fl":
            print(f"Setting up mock data for {registry_id}")
            _setup_sftp_mock_data()
            print(f"Mock data setup completed")

    yield {
        "registry_id": registry_id,
        "endpoint": endpoint,
        "bucket": bucket,
        "env_dir": str(env_dir) if env_dir.exists() else "",
        "redis_host": localstack_session.get("redis_host", "localhost"),
        "redis_port": localstack_session.get("redis_port", "6379"),
        "step": step,
    }

    # Tear down registry-specific environment
    if env_dir.exists():
        cmd = [*_docker_compose_cmd(), "down", "--remove-orphans"]
        subprocess.run(
            cmd, check=False, cwd=env_dir, text=True, capture_output=True, timeout=180
        )

    # Remove configs from S3
    _remove_configs_from_s3(registry_id, bucket, endpoint)
    
    # Remove SFTP secrets
    if registry_id == "us_fl":
        _remove_sftp_secrets(endpoint)


def _discover_test_cases(registry_id: str) -> list[Path]:
    tc_root = MOCKS_DIR / registry_id / "test_cases"
    if not tc_root.exists():
        return []
    return [p for p in tc_root.iterdir() if p.is_dir()]


def _run_python(path: Path, env: dict[str, str]) -> None:
    if not path.exists():
        return
    subprocess.run(
        [sys.executable, str(path)],
        check=True,
        cwd=str(path.parent),
        text=True,
        capture_output=True,
        env=env,
        timeout=300,
    )


def _run_app_container(
    registry_id: str, endpoint: str, bucket: str, extra_env: dict[str, str]
) -> None:
    # Run the fetcher via docker compose app-container to mimic production
    # Derive LocalStack port from environment or endpoint
    port = os.environ.get("CONFIG_TEST_ENV_LOCALSTACK_PORT")
    if not port:
        try:
            port = endpoint.rsplit(":", 1)[1]
            if "/" in port:
                port = port.split("/")[0]
        except Exception:
            # If we can't parse the port, this is a serious error
            raise RuntimeError(f"Could not determine LocalStack port from endpoint: {endpoint}")

    compose_cmd = (
        ["docker", "compose"] if shutil.which("docker") else ["docker-compose"]
    )
    cmd = [
        *compose_cmd,
        "run",
        "--rm",
        "--user",
        "1000:1000",
        "-e",
        f"CONFIG_TEST_ENV_LOCALSTACK_PORT={port}",
        "-e",
        f"OC_DATA_PIPELINE_CONFIG_S3_BUCKET={bucket}",
        "-e",
        f"OC_DATA_PIPELINE_DATA_REGISTRY_ID={registry_id}",
        "-e",
        "OC_DATA_PIPELINE_STAGE=raw",
        "-e",
        "OC_DATA_PIPELINE_STEP=fetch",
        # Ensure KV store is configured for Redis and reachable from container
        "-e",
        "DATA_FETCHER_APP_KVSTORE=redis",
        "-e",
        "DATA_FETCHER_APP_LOG_LEVEL=DEBUG",
        "-e",
        "PYTHONPATH=/code/src",
        # Back-compat vars used by some components
        "-e",
        "OC_KVSTORE_TYPE=redis",
        "-e",
        f"OC_KV_STORE_REDIS_HOST={extra_env.get('redis_host', 'host.docker.internal')}",
        "-e",
        f"OC_KV_STORE_REDIS_PORT={extra_env.get('redis_port', '6379')}",
        "app-container",
        "poetry",
        "run",
        "python",
        "-m",
        "data_fetcher_app.main",
        "run",
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            cwd=FETCHER_DIR,
            text=True,
            capture_output=True,
            timeout=1800,
        )
    except subprocess.CalledProcessError as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        # Write error details to a file for debugging
        with open("/tmp/app_run_error.log", "w") as f:
            f.write(f"APP RUN FAILED (exit {exc.returncode})\n")
            f.write(f"STDOUT:\n{out}\n")
            f.write(f"STDERR:\n{err}\n")
        print(f"APP RUN FAILED (exit {exc.returncode})")
        print(f"STDOUT:\n{out}")
        print(f"STDERR:\n{err}")
        pytest.fail(
            f"app run failed (exit {exc.returncode})\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        )


@pytest.mark.parametrize("_case", [0])
def test_recursive_functional(registry_env, _case):
    registry_id = registry_env["registry_id"]
    endpoint = registry_env["endpoint"]
    bucket = registry_env["bucket"]
    storage_bucket = registry_env.get("storage_bucket", "oc-local-data-pipeline")

    env_cleanup = MOCKS_DIR / registry_id / "environment" / "cleanup.py"

    for case_dir in _discover_test_cases(registry_id):
        # Per-case env
        base_env = {
            "DATA_REGISTRY_ID": registry_id,
            "LOCALSTACK_ENDPOINT": endpoint,
            "OC_DATA_PIPELINE_CONFIG_S3_BUCKET": bucket,
            "PYTHONUNBUFFERED": "1",
        }
        # Include redis connection details for app-container
        if registry_env.get("redis_host"):
            base_env["redis_host"] = registry_env["redis_host"]
        if registry_env.get("redis_port"):
            base_env["redis_port"] = str(registry_env["redis_port"])

        # Prepare
        _run_python(case_dir / "prepare.py", base_env)

        # Run app
        _run_app_container(registry_id, endpoint, bucket, base_env)

        # Expect
        _run_python(case_dir / "expectation.py", base_env)

        # Cleanup between tests
        # - Clear storage S3 (only storage, configs remain untouched)
        _clear_bucket(storage_bucket, endpoint)
        # - Purge SQS queues
        _purge_all_test_queues(endpoint)
        # - Flush Redis
        _flush_redis(
            registry_env.get("redis_host", "localhost"),
            registry_env.get("redis_port", "6379"),
        )
        # - Reset registry-specific mock environment if cleanup.py exists
        if env_cleanup.exists():
            _run_python(env_cleanup, base_env)
