import os
from pathlib import Path


def main() -> None:
    # Ensure any input artifacts are in place. FR uses HTTP mocks so minimal setup here.
    inputs = Path(__file__).parent / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    # Optionally upload additional resources to S3 via LOCALSTACK if needed in future
    _ = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    _ = os.environ.get("OC_DATA_PIPELINE_CONFIG_S3_BUCKET", "local-config")


if __name__ == "__main__":
    main()
