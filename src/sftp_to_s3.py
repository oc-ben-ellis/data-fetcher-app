"""
SFTP to S3 Transfer Utility

This script transfers files from an SFTP server to an AWS S3 bucket.
It uses configuration from a YAML file and credentials from AWS Secrets Manager.

The script:
1. Connects to an SFTP server using credentials from AWS Secrets Manager
2. Finds a specific file based on the input date
3. Transfers the file to an S3 bucket with appropriate metadata tags
4. Logs the process for monitoring and troubleshooting
"""

import argparse
import hashlib
import json
import logging
import os
import posixpath
import sys
import uuid
from datetime import datetime, timezone
from stat import S_ISDIR

import boto3
import paramiko
import yaml
from tenacity import retry, stop_after_attempt, wait_fixed

# Create a logger
logger = logging.getLogger(__name__)


class CustomFormatter(logging.Formatter):
    """Custom formatter for logging that ensures funcName is always available"""

    def format(self, record):
        """Format the log record with consistent function name

        Args:
            record (logging.LogRecord): The log record to format

        Returns:
            str: The formatted log message
        """
        record.funcName = record.funcName if hasattr(record, "funcName") else "main"
        return super().format(record)


handler = logging.StreamHandler()
formatter = CustomFormatter("%(asctime)s - %(levelname)s - %(funcName)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_secrets_with_retry(secret_name: str, region_name: str) -> dict:
    return fetch_secrets(secret_name, region_name)


def fetch_secrets(secret_name: str, region_name: str) -> dict:
    """Retrieve ONLY credentials from AWS Secrets Manager

    Args:
        secret_name (str): The name of the secret in AWS Secrets Manager
        region_name (str): The AWS region where the secret is stored

    Returns:
        dict: The secret data containing SFTP credentials
    """
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        secrets = json.loads(response["SecretString"])

        # Validate secret structure
        required_secret_keys = ["sftp_host", "sftp_port", "sftp_user", "sftp_pass"]
        if not all(key in secrets for key in required_secret_keys):
            missing = [key for key in required_secret_keys if key not in secrets]
            raise ValueError(f"Secret missing keys: {missing}")

        # Convert port to integer
        secrets["sftp_port"] = int(secrets["sftp_port"])

        # Validate host format
        if not isinstance(secrets["sftp_host"], str):
            raise ValueError(f"Invalid host format: {secrets['sftp_host']}")
        # Validate user format
        if not isinstance(secrets["sftp_user"], str):
            raise ValueError(f"Invalid user format: {secrets['sftp_user']}")
        # Validate password format
        if not isinstance(secrets["sftp_pass"], str):
            raise ValueError(f"Invalid password format: {secrets['sftp_pass']}")
        # Validate port type
        if not isinstance(secrets["sftp_port"], int):
            raise ValueError(f"Invalid port type: {secrets['sftp_port']}")
        # Validate port range
        if not (0 < secrets["sftp_port"] < 65536):
            raise ValueError(f"Invalid port number: {secrets['sftp_port']}")

        return secrets

    except Exception as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise


def validate_config(config: dict, required_keys: list[str]) -> None:
    """Validate that all required keys are present in the configuration.

    Args:
        config (dict): The configuration dictionary.
        required_keys (list): A list of required keys.

    Raises:
        ValueError: If any required keys are missing.
    """
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"Missing configuration keys: {missing_keys}")
    # Validate the structure of the config
    if not isinstance(config["remote_dir"], str):
        raise ValueError(f"Invalid remote_dir format: {config['remote_dir']}")
    if not isinstance(config["filename_pattern"], str):
        raise ValueError(
            f"Invalid filename_pattern format: {config['filename_pattern']}"
        )
    if not isinstance(config["s3_bucket"], str):
        raise ValueError(f"Invalid s3_bucket format: {config['s3_bucket']}")
    if not isinstance(config["s3_prefix"], str):
        raise ValueError(f"Invalid s3_prefix format: {config['s3_prefix']}")


def load_config_from_s3(bucket, key, source_id=None):
    """Load configuration from an S3 bucket.

    Args:
        bucket (str): The S3 bucket name
        key (str): The S3 object key
        source_id (str, optional): The source identifier to load configuration for.
            If provided, only the configuration for this source is returned.

    Returns:
        dict: The configuration data

    Raises:
        ValueError: If the source_id is not found in the configuration
        Exception: If there's an error loading the configuration
    """
    try:
        # Initialize S3 client
        s3 = boto3.client("s3")

        # Get the file content from S3
        logger.info(f"Loading configuration from s3://{bucket}/{key}")
        response = s3.get_object(Bucket=bucket, Key=key)

        # Read the file content
        file_content = response["Body"].read().decode("utf-8")

        # Parse YAML content
        all_configs = yaml.safe_load(file_content)
        logger.info("Successfully loaded configuration from S3")

        # If no source_id is provided, return all configurations
        if source_id is None:
            logger.info("No source_id provided, returning all configurations")
            return all_configs

        # If source_id is provided, validate and return that specific configuration
        if source_id not in all_configs:
            raise ValueError(f"Source ID '{source_id}' not found in configuration")

        config = all_configs[source_id]
        logger.info(f"Loaded configuration for source: {source_id}")

        # Validate required YAML config keys
        required_yaml_keys = [
            "remote_dir",
            "filename_pattern",
            "s3_bucket",
            "s3_prefix",
            "meta_load_name",
            "meta_load_version",
            "meta_source_system",
            "meta_source_entity",
            "secret_name",
            "region_name",
        ]

        validate_config(config, required_yaml_keys)
        return config

    except Exception as e:
        logger.error(f"Failed to load configuration from S3: {e}")
        raise


def load_config(source_id: str) -> dict:
    """Load and validate configuration from YAML file or S3

    Args:
        source_id (str): The source identifier to load configuration for.

    Returns:
        dict: The configuration data from the YAML file

    Raises:
        ValueError: If the source_id is not found in the configuration
        Exception: If there's an error loading or validating the configuration
    """
    # Check if S3 configuration is provided via environment variables
    config_s3_bucket = os.environ.get("CONFIG_S3_BUCKET")
    config_s3_key = os.environ.get("CONFIG_S3_KEY")

    # If S3 configuration is provided, try to load from S3 first
    if config_s3_bucket and config_s3_key:
        try:
            return load_config_from_s3(config_s3_bucket, config_s3_key, source_id)
        except Exception as e:
            logger.warning(f"Failed to load from S3, falling back to local file: {e}")
            # Fall back to local file if S3 loading fails

    # Load from local YAML file
    try:
        # Load from YAML (non-sensitive config)
        config_path = os.path.join("/config", "sftp_config.yaml")
        logger.info(f"Loading configuration from local file: {config_path}")
        with open(config_path) as f:
            all_configs = yaml.safe_load(f)

        if source_id not in all_configs:
            raise ValueError(f"Source ID '{source_id}' not found in configuration")
        config = all_configs[source_id]
        logger.info(f"Loaded configuration for source: {source_id}")

        # Validate required YAML config keys
        required_yaml_keys = [
            "remote_dir",
            "filename_pattern",
            "s3_bucket",
            "s3_prefix",
            "meta_load_name",
            "meta_load_version",
            "meta_source_system",
            "meta_source_entity",
            "secret_name",
            "region_name",
        ]

        validate_config(config, required_yaml_keys)
        return config

    except Exception as e:
        logger.error(f"Config error: {e}")
        raise


def _is_file(sftp: paramiko.SFTPClient, path: str) -> bool:
    """Check if path is a regular file

    Args:
        sftp (paramiko.SFTPClient): The SFTP client
        path (str): The path to check

    Returns:
        bool: True if the path is a regular file, False if it's a directory

    Raises:
        paramiko.SFTPError: If there's an error accessing the file
    """
    try:
        return not S_ISDIR(sftp.stat(path).st_mode)
    except paramiko.SFTPError as e:
        logger.error(f"Error checking file status: {e}")
        raise


def generate_s3_key(s3_prefix: str, filename: str) -> str:
    """Generate the S3 key for the file

    Args:
        s3_prefix (str): The S3 prefix from the config
        filename (str): The filename to use

    Returns:
        str: The full S3 key
    """
    return posixpath.join(s3_prefix, filename)


def find_remote_file(
    sftp: paramiko.SFTPClient, remote_dir: str, remote_filename: str
) -> str:
    """Find the remote file on SFTP Server

    Args:
        sftp (paramiko.SFTPClient): The SFTP client
        remote_dir (str): The remote directory to search in
        remote_filename (str): The filename to look for

    Returns:
        str: The full path to the remote file

    Raises:
        FileNotFoundError: If the file is not found
    """
    try:
        remote_path = posixpath.join(remote_dir, remote_filename)
        logger.info(f"Looking for file: {remote_path}")
        sftp.chdir(remote_dir)

        if _is_file(sftp, remote_path):
            logger.info(f"File found: {remote_path}")
            return remote_path
        else:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
    except Exception as e:
        logger.error(f"Error finding remote file: {e}")
        raise


def calculate_md5(sftp: paramiko.SFTPClient, remote_path: str) -> str:
    """Calculate the MD5 hash of a file on SFTP Server

    Args:
        sftp (paramiko.SFTPClient): The SFTP client
        remote_path (str): The path to the remote file

    Returns:
        str: The MD5 hash of the file
    """
    logger.info(f"Calculating MD5 for: {remote_path}")
    md5_hash = hashlib.md5()
    with sftp.open(remote_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def generate_metadata(
    remote_path: str,
    file_info: paramiko.SFTPAttributes,
    config: dict,
    sftp: paramiko.SFTPClient,
) -> dict:
    """Generate metadata for the file

    Args:
        remote_path (str): The path to the remote file
        file_info: The file stat information
        config (dict): The configuration dictionary
        sftp (paramiko.SFTPClient, optional): The SFTP client for MD5 calculation

    Returns:
        dict: The metadata dictionary
    """
    load_id = str(uuid.uuid4())
    current_time = datetime.now(timezone.utc).isoformat()

    # Calculate MD5 hash if sftp client is provided
    md5_hash = ""

    if hasattr(file_info, "md5_hash"):
        md5_hash = file_info.md5_hash
    else:
        md5_hash = calculate_md5(sftp, remote_path)

    # Create metadata dictionary
    return {
        "source-system": config["meta_source_system"],
        "source-entity": config["meta_source_entity"],
        "source-filename": posixpath.basename(remote_path),
        "source-file-lastmodified": datetime.fromtimestamp(
            file_info.st_mtime, timezone.utc
        ).isoformat(),
        "source-filehash": md5_hash,
        "retrieved-at": current_time,
        "load-name": config["meta_load_name"],
        "load-version": config["meta_load_version"],
        "load-id": load_id,
        "load-timestamp": current_time,
    }


def check_s3_bucket_exists(s3_client: boto3.client, bucket: str) -> bool:
    """
    Check if an S3 bucket exists and is accessible.

    Args:
        s3_client (boto3.client): The S3 client
        bucket (str): The name of the S3 bucket to check

    Returns:
        bool: True if the bucket exists and is accessible, False otherwise

    Raises:
        Exception: If there's an error other than NoSuchBucket
    """
    try:
        s3_client.head_bucket(Bucket=bucket)
        logger.info(f"S3 bucket '{bucket}' exists and is accessible")
        return True
    except s3_client.exceptions.NoSuchBucket:
        logger.error(f"S3 bucket '{bucket}' does not exist")
        return False
    except Exception as e:
        logger.error(f"Error checking S3 bucket '{bucket}': {e}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def upload_to_s3(
    s3_client: boto3.client,
    file_obj: object,
    bucket: str,
    s3_key: str,
    metadata: dict,
) -> None:
    """Upload a file to S3 with retries."""
    logger.info(f"Uploading to S3: s3://{bucket}/{s3_key}")
    s3_client.upload_fileobj(
        file_obj,
        bucket,
        s3_key,
        ExtraArgs={"Metadata": metadata},
    )


def transfer_file(
    sftp: paramiko.SFTPClient, remote_path: str, bucket: str, s3_key: str, config: dict
) -> None:
    """Transfer file from SFTP Server to S3 and add metadata tags

    Args:
        sftp (paramiko.SFTPClient): The SFTP client
        remote_path (str): The path to the remote file
        bucket (str): The S3 bucket name
        s3_key (str): The S3 key for the file
        config (dict): The configuration dictionary

    Raises:
        ValueError: If the S3 bucket does not exist
        Exception: For other errors during transfer
    """
    try:
        # Initialize S3 client
        s3 = boto3.client("s3")

        # Check if the S3 bucket exists
        if not check_s3_bucket_exists(s3, bucket):
            error_msg = f"S3 bucket '{bucket}' does not exist or is not accessible"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get file information
        logger.info(f"Getting file info for: {remote_path}")
        file_info = sftp.stat(remote_path)

        # Generate metadata
        metadata = generate_metadata(remote_path, file_info, config, sftp=sftp)
        logger.info(f"Generated metadata: {metadata}")

        # Upload to S3
        with sftp.open(remote_path, "rb") as f:
            upload_to_s3(s3, f, bucket, s3_key, metadata)
            # Log success
            logger.info(
                f"Successfully Transferred: {remote_path} -> s3://{bucket}/{s3_key}"
            )

    except Exception as e:
        logger.error(f"Failed to transfer {remote_path} to s3://{bucket}/{s3_key}: {e}")
        raise


def process_file(
    sftp: paramiko.SFTPClient, config: dict, remote_filename: str, env: str
) -> None:
    """Process a single file by finding it and transferring it to S3.

    Args:
        sftp (paramiko.SFTPClient): The SFTP client
        config (dict): The configuration dictionary
        remote_filename (str): The name of the remote file to process.
    """
    try:
        remote_dir = config["remote_dir"]
        # Find the remote file
        remote_path = find_remote_file(sftp, remote_dir, remote_filename)
        logger.info(f"Found remote file: {remote_path}")

        s3_bucket = config["s3_bucket"].replace("[env]", env)
        logger.info(f"Using S3 bucket: {s3_bucket}")

        # Generate S3 key using the helper function
        s3_key = generate_s3_key(config["s3_prefix"], remote_filename)
        logger.info(f"Generated S3 key: {s3_key}")
        transfer_file(sftp, remote_path, s3_bucket, s3_key, config)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise


def setup_sftp_connection(secrets: dict) -> paramiko.SFTPClient:
    """Establish an SFTP connection."""
    transport = paramiko.Transport((secrets["sftp_host"], secrets["sftp_port"]))
    transport.connect(username=secrets["sftp_user"], password=secrets["sftp_pass"])
    return paramiko.SFTPClient.from_transport(transport)


def process_with_date(input_date: str, env: str, source_id: str = None) -> None:
    """Process files with the given input date

    This function orchestrates the file processing:
    1. Fetches secrets from AWS Secrets Manager
    2. Establishes SFTP connection
    3. Processes the directory to find and transfer files

    Args:
        input_date (str): The input date in YYYYMMDD format
        env (str): The environment (play, dev, idp, prod)
        source_id (str, optional): The source identifier to process.
            If provided, only the configuration for this source is used.

    Returns:
        None: This function doesn't return anything

    Raises:
        SystemExit: If there's a configuration error or critical error
    """

    try:
        # Load configuration for the specified source
        config = load_config(source_id)
        # Fetch secrets using config values
        secrets = fetch_secrets(config["secret_name"], config["region_name"])
        logger.info("Configuration and secrets loaded successfully.")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    try:
        # Establish SFTP connection using secrets
        with setup_sftp_connection(secrets) as sftp:
            logger.info("SFTP connection established.")

            # Get the filename pattern from the config and replace the date placeholder
            filename_pattern = config["filename_pattern"]
            remote_filename = filename_pattern.replace("[YYYYMMDD]", input_date)
            logger.info(f"Using remote filename: {remote_filename}")

            # Process the file
            process_file(sftp, config, remote_filename, env)

    except Exception as e:
        logger.error(f"Critical error during file processing: {e}")
        sys.exit(1)
    finally:
        logger.info("Script execution completed.")


def validate_source_id(source_id: str, config: dict = None) -> None:
    """Validate the source identifier.

    Args:
        source_id (str): The source identifier to validate.
        config (dict): The configuration dictionary to check against.

    Raises:
        ValueError: If the source_id is None or not found in the configuration.
    """
    if source_id is None:
        raise ValueError("source_id is required")


def validate_input_date(input_date: str) -> None:
    """Validate the input date format (YYYYMMDD)."""
    try:
        datetime.strptime(input_date, "%Y%m%d")
    except ValueError as e:
        raise ValueError(
            "input_date must be in YYYYMMDD format (e.g., 20230101)"
        ) from e


def validate_env(env: str) -> None:
    """Validate the environment."""
    if env not in ["play", "dev", "idp", "prod"]:
        raise ValueError("env must be one of 'play', 'dev', 'idp' or 'prod'")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments

    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Transfer files from SFTP server to S3 bucket",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("input_date", help="Input date in YYYYMMDD format", type=str)
    parser.add_argument("env", help="Environment (play, dev, idp, prod)", type=str)
    parser.add_argument(
        "source_id",
        help="Source identifier (e.g., us_florida, us_texas)",
        type=str,
        default=None,
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate input_date
    validate_input_date(args.input_date)
    logger.info(f"Parsed input date: {args.input_date}")

    # Validate environment
    validate_env(args.env)
    logger.info(f"Environment: {args.env}")

    # Validate source_id
    validate_source_id(args.source_id)
    logger.info(f"Source ID: {args.source_id}")

    return args


def run_script() -> None:
    """Run the script with proper setup and teardown.

    This function:
    1. Sets up logging with a unique process ID
    2. Parses command line arguments
    3. Calls the main function with the input date
    4. Logs the execution status and duration
    5. Handles exceptions and ensures proper cleanup
    """
    # Record start time and generate a unique process ID for tracking
    start_time = datetime.now()
    process_id = str(uuid.uuid4())

    # Log the start of the process with tracking information
    logger.info(
        {
            "process_id": process_id,
            "job_name": "data-fetcher-sftp",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    try:
        # Parse command line arguments
        args = parse_arguments()

        # Execute the main workflow
        process_with_date(args.input_date, args.env, args.source_id)

        # Set success status if no exceptions occurred
        status = "success"

    except Exception as e:
        # Log any unhandled exceptions
        logger.error(f"Critical error: {e}")
        status = "failed"

    finally:
        # Calculate execution time and log final status
        end_time = datetime.now()
        logger.info(
            {
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status if "status" in locals() else "failed",
                "duration_sec": (end_time - start_time).total_seconds(),
            }
        )


if __name__ == "__main__":
    """Script entry point when run directly."""
    run_script()
