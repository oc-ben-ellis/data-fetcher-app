import json
import os
from pathlib import Path

import boto3


def _s3_client(endpoint: str):
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"),
        endpoint_url=endpoint,
    )


def _sqs_client(endpoint: str):
    return boto3.client(
        "sqs",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"),
        endpoint_url=endpoint,
    )


def _list_keys(s3, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []) or []:
            keys.append(item["Key"])  # type: ignore[index]
    return keys


def _assert_s3_objects(endpoint: str, registry_id: str) -> None:
    bucket = "oc-local-data-pipeline"
    s3 = _s3_client(endpoint)
    base_prefix = f"raw/{registry_id}/data/"
    keys = _list_keys(s3, bucket, base_prefix)
    if not keys:
        raise AssertionError(f"No raw objects found under s3://{bucket}/{base_prefix}")

    # Find all completed bundle metadata files
    completed = [k for k in keys if k.endswith("metadata/_completed.json")]
    if not completed:
        raise AssertionError("No completed bundle metadata found in raw stage")
    
    # Expect exactly 4 bundles
    if len(completed) != 4:
        raise AssertionError(f"Expected exactly 4 bundles, but found {len(completed)}")

    # Validate each bundle structure
    for completed_key in completed:
        bundle_meta_prefix = completed_key.rsplit("metadata/_completed.json", 1)[0]
        
        # Check for manifest file
        manifest_key = f"{bundle_meta_prefix}_manifest.jsonl"
        if manifest_key not in keys:
            keys = _list_keys(s3, bucket, base_prefix)
            if manifest_key not in keys:
                raise AssertionError(f"_manifest.jsonl missing for bundle at {bundle_meta_prefix}")

        # Check for content files
        content_prefix = bundle_meta_prefix.replace("metadata/", "content/")
        content_keys = [
            k for k in keys if k.startswith(content_prefix) and not k.endswith("/")
        ]
        if not content_keys:
            raise AssertionError(f"No bundle content objects found for bundle at {content_prefix}")

        # Validate _completed.json structure
        try:
            response = s3.get_object(Bucket=bucket, Key=completed_key)
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            
            # Check required fields
            required_fields = ['bundle_hash', 'source', 'run_id', 'resources_count']
            for field in required_fields:
                if field not in metadata:
                    raise AssertionError(f"Missing required field '{field}' in {completed_key}")
            
            # Validate source is sftp
            if metadata.get('source') != 'sftp':
                raise AssertionError(f"Expected source to be 'sftp' in {completed_key}, got '{metadata.get('source')}'")
                
            # Validate resources_count is 1 (each bundle should contain 1 file)
            if metadata.get('resources_count') != 1:
                raise AssertionError(f"Expected resources_count to be 1 in {completed_key}, got {metadata.get('resources_count')}")
                
        except Exception as e:
            raise AssertionError(f"Failed to validate bundle metadata in {completed_key}: {e}")

    # Validate bundle hashes
    bundle_hashes_prefix = f"raw/{registry_id}/bundle_hashes/"
    hash_keys = _list_keys(s3, bucket, bundle_hashes_prefix)
    
    # Should have _latest file
    if not any(k.endswith("_latest") for k in hash_keys):
        raise AssertionError("bundle_hashes/_latest not found")
    
    # Should have exactly 4 bundle hash files (plus _latest = 5 total)
    hash_files = [k for k in hash_keys if not k.endswith("_latest")]
    if len(hash_files) != 4:
        raise AssertionError(f"Expected exactly 4 bundle hash files, but found {len(hash_files)}")
    
    # Validate _latest points to one of the bundle hashes
    try:
        latest_response = s3.get_object(Bucket=bucket, Key=f"{bundle_hashes_prefix}_latest")
        latest_hash = latest_response['Body'].read().decode('utf-8').strip()
        
        # Check if the latest hash file exists
        latest_hash_key = f"{bundle_hashes_prefix}{latest_hash}"
        if latest_hash_key not in hash_keys:
            raise AssertionError(f"_latest points to non-existent hash file: {latest_hash}")
            
    except Exception as e:
        raise AssertionError(f"Failed to validate _latest bundle hash: {e}")


def _assert_sqs_message(endpoint: str) -> None:
    sqs = _sqs_client(endpoint)
    # Match docker-compose default queue URL
    queue_url = f"{endpoint}/000000000000/data-pipeline-orchestration-queue"
    try:
        resp = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1
        )
    except Exception as e:
        raise AssertionError(f"Failed to receive message from SQS: {e}")
    msgs = resp.get("Messages", [])
    if not msgs:
        raise AssertionError("Expected at least one SQS message in orchestration queue")


def _assert_sftp_files_intact() -> None:
    # Verify that input files still exist on the host-mounted directory used by sftp container
    env_dir = Path(__file__).resolve().parents[2] / "environment"
    host_data_dir = env_dir / "data" / "doc"
    expected_paths = [
        host_data_dir / "cor" / "20250829c.txt",
        host_data_dir / "cor" / "20250913c.txt",
        host_data_dir / "cor" / "20250915c.txt",
        host_data_dir / "Quarterly" / "Cor" / "cordata.zip",
    ]
    for p in expected_paths:
        if not p.exists():
            raise AssertionError(f"Expected SFTP file still present: {p}")


def main() -> None:
    endpoint = os.environ["LOCALSTACK_ENDPOINT"]
    registry_id = os.environ["DATA_REGISTRY_ID"]

    _assert_s3_objects(endpoint, registry_id)
    _assert_sqs_message(endpoint)
    _assert_sftp_files_intact()


if __name__ == "__main__":
    main()
