import os

import boto3


def _s3_client(endpoint: str):
    return boto3.client(
        "s3",
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


def main() -> None:
    # Inputs from test harness
    endpoint = os.environ["LOCALSTACK_ENDPOINT"]
    registry_id = os.environ["DATA_REGISTRY_ID"]

    # Pipeline storage bucket follows oc-<env>-data-pipeline (env=local in tests)
    bucket = "oc-local-data-pipeline"

    s3 = _s3_client(endpoint)

    # Expect at least one raw bundle under raw/<registry_id>/data/
    # Structure: raw/{data_registry_id}/data/year=YYYY/month=MM/day=DD/HH-mm-ss-hex/
    base_prefix = f"raw/{registry_id}/data/"
    keys = _list_keys(s3, bucket, base_prefix)
    if not keys:
        raise AssertionError(f"No raw objects found under s3://{bucket}/{base_prefix}")

    # Find one bundle folder by locating a _completed.json in metadata/
    completed = [k for k in keys if k.endswith("metadata/_completed.json")]
    if not completed:
        raise AssertionError("No completed bundle metadata found in raw stage")

    # For the same bundle, ensure required metadata files exist
    # Derive bundle prefix by stripping trailing 'metadata/_completed.json'
    bundle_meta_prefix = completed[0].rsplit("metadata/_completed.json", 1)[0]

    # Check for _discovered.json (bundle discovery metadata)
    discovered_key = f"{bundle_meta_prefix}_discovered.json"
    if discovered_key not in keys:
        # Refresh listing for safety
        keys = _list_keys(s3, bucket, base_prefix)
        if discovered_key not in keys:
            raise AssertionError("_discovered.json missing for bundle")

    # Check for _manifest.jsonl (list of resources in bundle)
    manifest_key = f"{bundle_meta_prefix}_manifest.jsonl"
    if manifest_key not in keys:
        # Refresh listing for safety
        keys = _list_keys(s3, bucket, base_prefix)
        if manifest_key not in keys:
            raise AssertionError("_manifest.jsonl missing for completed bundle")

    # Check for content files and their metadata
    content_prefix = bundle_meta_prefix.replace("metadata/", "content/")
    content_keys = [
        k for k in keys if k.startswith(content_prefix) and not k.endswith("/")
    ]
    if not content_keys:
        raise AssertionError("No bundle content objects found in raw stage")

    # For each content file, ensure there's a corresponding metadata file
    for content_key in content_keys:
        content_filename = content_key.split("/")[-1]
        content_meta_key = f"{bundle_meta_prefix}{content_filename}.metadata.json"
        if content_meta_key not in keys:
            # Refresh listing for safety
            keys = _list_keys(s3, bucket, base_prefix)
            if content_meta_key not in keys:
                raise AssertionError(
                    f"Metadata file missing for content: {content_filename}"
                )

    # CDC: bundle hashes should exist
    bundle_hashes_prefix = f"raw/{registry_id}/bundle_hashes/"
    hash_keys = _list_keys(s3, bucket, bundle_hashes_prefix)
    if not any(k.endswith("_latest") for k in hash_keys):
        raise AssertionError("bundle_hashes/_latest not found")

    # Verify at least one bundle hash file exists (not just _latest)
    hash_files = [
        k for k in hash_keys if not k.endswith("_latest") and not k.endswith("/")
    ]
    if not hash_files:
        raise AssertionError("No bundle hash files found in bundle_hashes directory")


if __name__ == "__main__":
    main()
