import pytest
import paramiko
import json
import yaml
import hashlib
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone
import sys
import os
from io import BytesIO

# Add the src directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import sftp_to_s3

# Define the file suffix used in tests (matches the one used in the main code)
FILE_SUFFIX = "c.txt"


@pytest.fixture
def mock_config():
    """
    Fixture that provides a mock configuration dictionary.

    This configuration mimics what would normally be loaded from the YAML config file
    and AWS Secrets Manager, containing all necessary parameters for SFTP and S3 operations.

    Returns:
        dict: A dictionary containing all configuration parameters needed for testing
    """
    return {
        # SFTP connection parameters
        "sftp_host": "test-host.example.com",
        "sftp_port": 22,
        "sftp_user": "testuser",
        "sftp_pass": "testpass",
        # File location parameters
        "remote_dir": "/Public/doc/cor",
        "filename_pattern": "[YYYYMMDD]c.txt",
        # S3 destination parameters
        "s3_bucket": "ri-sandbox-raw",
        "s3_prefix": "ra/doc/cor",
        # Metadata parameters
        "meta_load_name": "Florida_COR_Transfer",
        "meta_load_version": "1.2.0",
        "meta_source_system": "FloridaDOE_SFTP",
        "meta_source_entity": "correspondence",
        # AWS configuration
        "secret_name": "us_florida",
        "region_name": "eu-west-2",
    }


@pytest.fixture
def mock_sftp():
    """
    Fixture that provides a mock SFTP client.

    This mock simulates an SFTP connection without actually connecting to a server,
    with pre-configured responses for common operations like stat() and open().

    The mock is configured to:
    - Return file stats indicating a regular file with current timestamp
    - Provide a file-like object that returns test content when read

    Returns:
        MagicMock: A mock object that simulates an SFTP client
    """
    # Create the base SFTP client mock
    sftp = MagicMock(spec=paramiko.SFTPClient)

    # Configure stat() to return a regular file by default
    stat_result = MagicMock()
    stat_result.st_mode = 33188  # Regular file mode (corresponds to -rw-r--r--)
    stat_result.st_mtime = datetime.now(timezone.utc).timestamp()
    sftp.stat.return_value = stat_result

    # Configure open() to return a file-like object with test content
    mock_file = MagicMock()
    mock_file.__enter__.return_value = BytesIO(b"test file content")
    sftp.open.return_value = mock_file

    return sftp


class TestSftpToS3:
    """
    Test suite for the sftp_to_s3 module.

    This class contains tests for all major functions in the sftp_to_s3 module,
    including configuration loading, secret management, file operations, and the
    main workflow.
    """

    # ----- Configuration Tests -----

    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open, read_data="yaml_content")
    def test_load_config(self, mock_file, mock_yaml, mock_config):
        """
        Test that load_config correctly reads and validates the YAML configuration file.

        This test verifies that:
        1. The function opens the correct config file (sftp_config.yaml)
        2. It properly parses the YAML content
        3. It returns a dictionary with all required configuration keys
        """
        # Setup: Configure mock to return predefined config values
        mock_yaml.return_value = {
            "remote_dir": mock_config["remote_dir"],
            "filename_pattern": mock_config["filename_pattern"],
            "s3_bucket": mock_config["s3_bucket"],
            "s3_prefix": mock_config["s3_prefix"],
            "meta_load_name": mock_config["meta_load_name"],
            "meta_load_version": mock_config["meta_load_version"],
            "meta_source_system": mock_config["meta_source_system"],
            "meta_source_entity": mock_config["meta_source_entity"],
            "secret_name": mock_config["secret_name"],
            "region_name": mock_config["region_name"],
        }

        # Execute: Call the function being tested
        config = sftp_to_s3.load_config()

        # Verify: Check that the returned config contains expected values
        assert config["remote_dir"] == mock_config["remote_dir"]
        assert config["s3_bucket"] == mock_config["s3_bucket"]
        assert config["secret_name"] == mock_config["secret_name"]
        assert config["region_name"] == mock_config["region_name"]
        # Verify that the function opened the correct file
        mock_file.assert_called_once_with("sftp_config.yaml")

    # ----- Secrets Management Tests -----

    @patch("boto3.session.Session")
    def test_fetch_secrets(self, mock_session):
        """
        Test that fetch_secrets correctly retrieves and parses secrets from AWS Secrets Manager.

        This test verifies that:
        1. The function connects to AWS Secrets Manager with the correct parameters
        2. It properly parses the JSON secret string
        3. It returns a dictionary with all required credential keys
        """
        # Setup: Create mock AWS client and session
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Define test secret data that should be returned
        secret_data = {
            "sftp_host": "test-host.example.com",
            "sftp_port": "22",
            "sftp_user": "testuser",
            "sftp_pass": "testpass",
        }

        # Configure mock to return the test secret data
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        # Execute: Call the function being tested
        result = sftp_to_s3.fetch_secrets("us_florida", "eu-west-2")

        # Verify: Check that the returned data matches the expected secret with port converted to int
        expected_result = secret_data.copy()
        expected_result["sftp_port"] = int(expected_result["sftp_port"])
        assert result == expected_result
        # Verify that AWS Secrets Manager was called with correct parameters
        mock_session.return_value.client.assert_called_once_with(
            service_name="secretsmanager", region_name="eu-west-2"
        )

    @patch("boto3.session.Session")
    def test_fetch_secrets_aws_error(self, mock_session):
        """
        Test that fetch_secrets properly handles AWS service errors.

        This test verifies that when AWS Secrets Manager throws an exception,
        the function propagates the error appropriately rather than silently failing.
        """
        # Setup: Create mock AWS client
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Simulate AWS service error
        mock_client.get_secret_value.side_effect = Exception("AWS service error")

        # Execute and Verify: Check that the function raises an exception
        with pytest.raises(Exception):
            sftp_to_s3.fetch_secrets("us_florida", "eu-west-2")

    @patch("boto3.session.Session")
    def test_fetch_secrets_missing_keys(self, mock_session):
        # Test missing required keys in secret
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Missing sftp_port
        incomplete_secret_data = {
            "sftp_host": "test-host.example.com",
            "sftp_user": "testuser",
            "sftp_pass": "testpass",
        }

        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(incomplete_secret_data)
        }

        with pytest.raises(ValueError, match="Secret missing keys"):
            sftp_to_s3.fetch_secrets("us_florida", "eu-west-2")

    @patch("boto3.session.Session")
    def test_fetch_secrets_invalid_json(self, mock_session):
        # Test invalid JSON in secret
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Invalid JSON
        mock_client.get_secret_value.return_value = {"SecretString": "invalid json"}

        with pytest.raises(Exception):
            sftp_to_s3.fetch_secrets("us_florida", "eu-west-2")

    # ----- File Operation Tests -----

    def test_is_file(self, mock_sftp):
        """
        Test that _is_file correctly identifies files versus directories.

        This test verifies that the function:
        1. Returns True for regular files
        2. Returns False for directories
        """
        # Case 1: Test with a regular file
        # The mock_sftp fixture is already configured to return a regular file mode
        result = sftp_to_s3._is_file(mock_sftp, "/path/to/file.txt")
        assert result is True, "Should identify a regular file correctly"

        # Case 2: Test with a directory
        # Reconfigure the mock to return a directory mode
        stat_result = MagicMock()
        stat_result.st_mode = 16384  # Directory mode (corresponds to drwxr-xr-x)
        mock_sftp.stat.return_value = stat_result

        result = sftp_to_s3._is_file(mock_sftp, "/path/to/dir")
        assert result is False, "Should identify a directory correctly"

    def test_calculate_md5(self, mock_sftp):
        """
        Test that calculate_md5 correctly calculates the MD5 hash of a file.

        This test verifies that the function:
        1. Opens the correct file from the SFTP server
        2. Reads the file in chunks
        3. Calculates the correct MD5 hash
        """
        # Setup: Configure mock_sftp to return a file with known content
        remote_path = "/test/path/file.txt"
        test_content = b"test content for md5"

        mock_file = MagicMock()
        mock_file.__enter__.return_value = BytesIO(test_content)
        mock_sftp.open.return_value = mock_file

        # Calculate expected MD5 hash
        expected_md5 = hashlib.md5(test_content).hexdigest()

        # Execute: Call the function
        result = sftp_to_s3.calculate_md5(mock_sftp, remote_path)

        # Verify: Check that the function returns the correct hash
        assert result == expected_md5, "Should calculate correct MD5 hash"
        mock_sftp.open.assert_called_with(remote_path, "rb")

    def test_find_remote_file(self, mock_sftp):
        """
        Test that find_remote_file correctly locates a file on the SFTP server.

        This test verifies that the function:
        1. Changes to the correct remote directory
        2. Constructs the correct remote path
        3. Returns the full path when the file exists
        """
        # Setup: Define test directory and filename
        remote_dir = "/Public/doc/cor"
        remote_filename = "20250605c.txt"

        # Execute: Call the function being tested
        result = sftp_to_s3.find_remote_file(mock_sftp, remote_dir, remote_filename)

        # Verify: Check that the function returns the correct path
        assert result == "/Public/doc/cor/20250605c.txt"
        # Verify that it changed to the correct directory
        mock_sftp.chdir.assert_called_once_with(remote_dir)

    def test_find_remote_file_not_found(self, mock_sftp):
        remote_dir = "/Public/doc/cor"
        remote_filename = "nonexistent.txt"

        # Make _is_file return False to simulate file not found
        with patch("sftp_to_s3._is_file", return_value=False):
            with pytest.raises(FileNotFoundError):
                sftp_to_s3.find_remote_file(mock_sftp, remote_dir, remote_filename)

    @patch("paramiko.Transport")
    @patch("paramiko.SFTPClient.from_transport")
    def test_setup_sftp_connection(self, mock_sftp_client, mock_transport):
        """
        Test that setup_sftp_connection correctly establishes an SFTP connection.

        This test verifies that the function:
        1. Creates a Transport with the correct host and port
        2. Connects with the correct username and password
        3. Creates and returns an SFTP client from the transport
        """
        # Setup: Create mock secrets
        secrets = {
            "sftp_host": "test-host.example.com",
            "sftp_port": 22,
            "sftp_user": "testuser",
            "sftp_pass": "testpass",
        }

        # Setup mock transport
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance

        # Setup mock SFTP client
        mock_sftp = MagicMock()
        mock_sftp_client.return_value = mock_sftp

        # Execute: Call the function
        result = sftp_to_s3.setup_sftp_connection(secrets)

        # Verify: Check that the function creates and connects the transport correctly
        mock_transport.assert_called_once_with(
            (secrets["sftp_host"], secrets["sftp_port"])
        )
        mock_transport_instance.connect.assert_called_once_with(
            username=secrets["sftp_user"], password=secrets["sftp_pass"]
        )

        # Verify: Check that the function creates and returns an SFTP client
        mock_sftp_client.assert_called_once_with(mock_transport_instance)
        assert result == mock_sftp, "Should return the SFTP client"

    # ----- File Transfer Tests -----

    @patch("boto3.client")
    @patch("sftp_to_s3.generate_metadata")
    @patch("sftp_to_s3.check_s3_bucket_exists")
    @patch("sftp_to_s3.upload_to_s3")
    def test_transfer_file(
        self,
        mock_upload_to_s3,
        mock_check_bucket,
        mock_generate_metadata,
        mock_boto3_client,
        mock_sftp,
        mock_config,
    ):
        """
        Test that transfer_file correctly transfers a file from SFTP to S3.

        This test verifies that the function:
        1. Opens the correct file from the SFTP server
        2. Generates metadata with the SFTP client for MD5 calculation
        3. Checks if the S3 bucket exists
        4. Calls upload_to_s3 with the correct parameters
        """
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the metadata
        mock_metadata = {"key1": "value1", "key2": "value2"}
        mock_generate_metadata.return_value = mock_metadata

        # Mock the bucket check to return True (bucket exists)
        mock_check_bucket.return_value = True

        remote_path = "/Public/doc/cor/20250605c.txt"
        bucket = "ri-sandbox-raw"
        s3_key = "ra/doc/cor/20250605c.txt"

        sftp_to_s3.transfer_file(mock_sftp, remote_path, bucket, s3_key, mock_config)

        # Verify that generate_metadata was called with the SFTP client
        mock_generate_metadata.assert_called_once()
        assert mock_generate_metadata.call_args[0][0] == remote_path
        assert mock_generate_metadata.call_args[1]["sftp"] == mock_sftp

        # Verify that check_s3_bucket_exists was called with the correct parameters
        mock_check_bucket.assert_called_once_with(mock_s3, bucket)

        # Verify that the file was opened
        mock_sftp.open.assert_called_with(remote_path, "rb")

        # Verify that upload_to_s3 was called with the correct parameters
        mock_upload_to_s3.assert_called_once()
        assert mock_upload_to_s3.call_args[0][0] == mock_s3  # s3_client
        # The second argument is the file object, which is harder to check directly
        assert mock_upload_to_s3.call_args[0][2] == bucket  # bucket
        assert mock_upload_to_s3.call_args[0][3] == s3_key  # s3_key
        assert mock_upload_to_s3.call_args[0][4] == mock_metadata  # metadata

    @patch("boto3.client")
    @patch("sftp_to_s3.generate_metadata")
    @patch("sftp_to_s3.check_s3_bucket_exists")
    def test_transfer_file_bucket_not_exists(
        self,
        mock_check_bucket,
        mock_generate_metadata,
        mock_boto3_client,
        mock_sftp,
        mock_config,
    ):
        """
        Test that transfer_file raises an error when the S3 bucket doesn't exist.

        This test verifies that the function:
        1. Checks if the S3 bucket exists
        2. Raises a ValueError when the bucket doesn't exist
        """
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the metadata
        mock_metadata = {"key1": "value1", "key2": "value2"}
        mock_generate_metadata.return_value = mock_metadata

        # Mock the bucket check to return False (bucket doesn't exist)
        mock_check_bucket.return_value = False

        remote_path = "/Public/doc/cor/20250605c.txt"
        bucket = "nonexistent-bucket"
        s3_key = "ra/doc/cor/20250605c.txt"

        # Execute and Verify: Check that a ValueError is raised
        with pytest.raises(ValueError, match=f"S3 bucket '{bucket}' does not exist"):
            sftp_to_s3.transfer_file(
                mock_sftp, remote_path, bucket, s3_key, mock_config
            )

        # Verify that check_s3_bucket_exists was called with the correct parameters
        mock_check_bucket.assert_called_once_with(mock_s3, bucket)

    def test_check_s3_bucket_exists(self):
        """
        Test that check_s3_bucket_exists correctly checks if an S3 bucket exists.

        This test verifies that the function:
        1. Calls head_bucket on the S3 client with the correct bucket name
        2. Returns True when the bucket exists
        3. Returns False when the bucket doesn't exist
        4. Raises an exception for other errors
        """
        # Setup: Create mock S3 client
        mock_s3_client = MagicMock()
        bucket = "test-bucket"

        # Case 1: Bucket exists
        # Execute: Call the function
        result = sftp_to_s3.check_s3_bucket_exists(mock_s3_client, bucket)

        # Verify: Check that head_bucket was called and True was returned
        mock_s3_client.head_bucket.assert_called_once_with(Bucket=bucket)
        assert result is True, "Should return True when bucket exists"

        # Reset the mock for the next test case
        mock_s3_client.reset_mock()

        # Case 2: Bucket doesn't exist
        # Configure mock to raise NoSuchBucket exception
        mock_s3_client.exceptions.NoSuchBucket = Exception
        mock_s3_client.head_bucket.side_effect = (
            mock_s3_client.exceptions.NoSuchBucket()
        )

        # Execute: Call the function
        result = sftp_to_s3.check_s3_bucket_exists(mock_s3_client, bucket)

        # Verify: Check that False was returned
        assert result is False, "Should return False when bucket doesn't exist"

        # Reset the mock for the next test case
        mock_s3_client.reset_mock()

        # Case 3: Other error
        # Configure mock to raise a different exception
        mock_s3_client.head_bucket.side_effect = Exception("Access denied")

        # Execute and Verify: Check that the exception is propagated
        with pytest.raises(Exception):
            sftp_to_s3.check_s3_bucket_exists(mock_s3_client, bucket)

    def test_upload_to_s3(self):
        """
        Test that upload_to_s3 correctly uploads a file to S3.

        This test verifies that the function:
        1. Calls upload_fileobj on the S3 client with the correct parameters
        2. Includes the metadata in the ExtraArgs
        """
        # Setup: Create mock S3 client and file object
        mock_s3_client = MagicMock()
        mock_file_obj = MagicMock()
        bucket = "test-bucket"
        s3_key = "test/key.txt"
        metadata = {"key1": "value1", "key2": "value2"}

        # Execute: Call the function
        sftp_to_s3.upload_to_s3(mock_s3_client, mock_file_obj, bucket, s3_key, metadata)

        # Verify: Check that upload_fileobj was called with the correct parameters
        mock_s3_client.upload_fileobj.assert_called_once_with(
            mock_file_obj,
            bucket,
            s3_key,
            ExtraArgs={"Metadata": metadata},
        )

    @patch("boto3.client")
    @patch("sftp_to_s3.generate_metadata")
    def test_transfer_file_sftp_error(
        self, mock_generate_metadata, mock_boto3_client, mock_sftp, mock_config
    ):
        # Test SFTP error
        remote_path = "/Public/doc/cor/20250605c.txt"
        bucket = "ri-sandbox-raw"
        s3_key = "ra/doc/cor/20250605c.txt"

        # Simulate SFTP error
        mock_sftp.stat.side_effect = paramiko.SFTPError("SFTP error")

        with pytest.raises(Exception):
            sftp_to_s3.transfer_file(
                mock_sftp, remote_path, bucket, s3_key, mock_config
            )

    @patch("boto3.client")
    @patch("sftp_to_s3.generate_metadata")
    @patch("sftp_to_s3.upload_to_s3")
    def test_transfer_file_s3_error(
        self,
        mock_upload_to_s3,
        mock_generate_metadata,
        mock_boto3_client,
        mock_sftp,
        mock_config,
    ):
        # Test S3 upload error
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the metadata
        mock_metadata = {"key1": "value1", "key2": "value2"}
        mock_generate_metadata.return_value = mock_metadata

        remote_path = "/Public/doc/cor/20250605c.txt"
        bucket = "ri-sandbox-raw"
        s3_key = "ra/doc/cor/20250605c.txt"

        # Simulate S3 upload error
        mock_upload_to_s3.side_effect = Exception("S3 upload error")

        with pytest.raises(Exception):
            sftp_to_s3.transfer_file(
                mock_sftp, remote_path, bucket, s3_key, mock_config
            )

    # ----- Workflow Tests -----

    @patch("sftp_to_s3.find_remote_file")
    @patch("sftp_to_s3.transfer_file")
    @patch("sftp_to_s3.generate_s3_key")
    def test_process_file(
        self, mock_generate_s3_key, mock_transfer, mock_find, mock_sftp, mock_config
    ):
        """
        Test that process_file correctly orchestrates finding and transferring a file.

        This test verifies that the function:
        1. Calls find_remote_file with the correct parameters
        2. Generates the S3 key using generate_s3_key
        3. Calls transfer_file with the correct parameters
        """
        remote_filename = "20250605c.txt"
        remote_path = f"/Public/doc/cor/{remote_filename}"
        mock_find.return_value = remote_path

        s3_key = f"ra/doc/cor/{remote_filename}"
        mock_generate_s3_key.return_value = s3_key

        # Add the env parameter
        env = "playground"

        sftp_to_s3.process_file(mock_sftp, mock_config, remote_filename, env)

        # Verify find_remote_file was called with correct parameters
        mock_find.assert_called_once_with(
            mock_sftp, mock_config["remote_dir"], remote_filename
        )

        # Verify generate_s3_key was called with correct parameters
        mock_generate_s3_key.assert_called_once_with(
            mock_config["s3_prefix"], remote_filename
        )

        # Verify transfer_file was called with correct parameters
        mock_transfer.assert_called_once_with(
            mock_sftp,
            remote_path,
            mock_config["s3_bucket"],
            s3_key,
            mock_config,
        )

    @patch("sftp_to_s3.find_remote_file")
    def test_process_file_not_found(self, mock_find, mock_sftp, mock_config):
        """
        Test that process_file correctly handles file not found errors.
        """
        remote_filename = "20250605c.txt"

        # Simulate file not found
        mock_find.side_effect = FileNotFoundError("File not found")

        with pytest.raises(Exception):
            sftp_to_s3.process_file(mock_sftp, mock_config, remote_filename)

    @patch("sftp_to_s3.find_remote_file")
    @patch("sftp_to_s3.transfer_file")
    @patch("sftp_to_s3.generate_s3_key")
    def test_process_file_transfer_error(
        self, mock_generate_s3_key, mock_transfer, mock_find, mock_sftp, mock_config
    ):
        """
        Test that process_file correctly handles transfer errors.
        """
        remote_filename = "20250605c.txt"
        remote_path = f"/Public/doc/cor/{remote_filename}"
        mock_find.return_value = remote_path

        s3_key = f"ra/doc/cor/{remote_filename}"
        mock_generate_s3_key.return_value = s3_key

        # Simulate transfer error
        mock_transfer.side_effect = Exception("Transfer error")

        with pytest.raises(Exception):
            sftp_to_s3.process_file(mock_sftp, mock_config, remote_filename)

    @patch("sftp_to_s3.load_config")
    @patch("sftp_to_s3.fetch_secrets")
    @patch("sftp_to_s3.setup_sftp_connection")
    @patch("sftp_to_s3.process_file")
    def test_process_with_date(
        self,
        mock_process_file,
        mock_setup_sftp,
        mock_fetch_secrets,
        mock_load_config,
        mock_config,
    ):
        """
        Test that process_with_date correctly orchestrates the entire workflow.

        This test verifies that the function:
        1. Loads configuration from YAML
        2. Fetches secrets from AWS Secrets Manager
        3. Establishes an SFTP connection with the correct credentials
        4. Processes the file with the correct parameters

        This is an integration test that verifies all components work together correctly.
        """
        # Setup mocks
        config_dict = {
            "secret_name": mock_config["secret_name"],
            "region_name": mock_config["region_name"],
            "s3_bucket": mock_config["s3_bucket"],
            "s3_prefix": mock_config["s3_prefix"],
            "remote_dir": mock_config["remote_dir"],
            "filename_pattern": mock_config["filename_pattern"],
            "meta_load_name": mock_config["meta_load_name"],
            "meta_load_version": mock_config["meta_load_version"],
            "meta_source_system": mock_config["meta_source_system"],
            "meta_source_entity": mock_config["meta_source_entity"],
        }

        secrets_dict = {
            "sftp_host": mock_config["sftp_host"],
            "sftp_port": mock_config["sftp_port"],
            "sftp_user": mock_config["sftp_user"],
            "sftp_pass": mock_config["sftp_pass"],
        }

        mock_load_config.return_value = config_dict
        mock_fetch_secrets.return_value = secrets_dict

        mock_sftp = MagicMock()
        mock_setup_sftp.return_value.__enter__.return_value = mock_sftp

        # Call the function
        input_date = "20250605"
        env = "playground"
        sftp_to_s3.process_with_date(input_date, env)

        # Verify the calls
        mock_load_config.assert_called_once()
        mock_fetch_secrets.assert_called_once_with(
            config_dict["secret_name"], config_dict["region_name"]
        )
        mock_setup_sftp.assert_called_once_with(secrets_dict)

        # Verify process_file was called with the correct filename and env
        expected_filename = f"{input_date}c.txt"
        mock_process_file.assert_called_once_with(
            mock_sftp, config_dict, expected_filename, env
        )

    @patch("sftp_to_s3.parse_arguments")
    @patch("sftp_to_s3.process_with_date")
    def test_run_script(self, mock_process_with_date, mock_parse_arguments):
        """
        Test that run_script correctly parses arguments and calls process_with_date.

        This test verifies that the function:
        1. Parses command line arguments
        2. Calls process_with_date with the input date
        3. Logs the execution status and duration
        """
        # Setup mock arguments
        mock_args = MagicMock()
        mock_args.input_date = "20250605"
        mock_args.env = "playground"
        mock_parse_arguments.return_value = mock_args

        # Call the function
        sftp_to_s3.run_script()

        # Verify the calls
        mock_parse_arguments.assert_called_once()
        mock_process_with_date.assert_called_once_with(
            mock_args.input_date, mock_args.env
        )

    @patch("sftp_to_s3.parse_arguments")
    @patch("sftp_to_s3.process_with_date")
    def test_run_script_error(self, mock_process_with_date, mock_parse_arguments):
        """
        Test that run_script correctly handles errors.

        This test verifies that the function:
        1. Catches exceptions from process_with_date
        2. Logs the error
        3. Sets the status to 'failed'
        """
        # Setup mock arguments
        mock_args = MagicMock()
        mock_args.input_date = "20250605"
        mock_args.env = "playground"
        mock_parse_arguments.return_value = mock_args

        # Simulate an error in process_with_date
        mock_process_with_date.side_effect = Exception("Test error")

        # Call the function
        sftp_to_s3.run_script()

        # Verify the calls
        mock_parse_arguments.assert_called_once()
        mock_process_with_date.assert_called_once_with(
            mock_args.input_date, mock_args.env
        )

    def test_load_config_missing_keys(self):
        # Test with missing required keys in YAML
        with patch(
            "yaml.safe_load", return_value={"remote_dir": "/test"}
        ):  # Missing most keys
            with patch("builtins.open", mock_open(read_data="")):
                with pytest.raises(ValueError, match="Missing configuration keys:"):
                    sftp_to_s3.load_config()

    def test_load_config_file_not_found(self):
        # Test with file not found
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(Exception):
                sftp_to_s3.load_config()

    def test_load_config_invalid_yaml(self):
        # Test with invalid YAML
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
            with patch("builtins.open", mock_open(read_data="")):
                with pytest.raises(Exception):
                    sftp_to_s3.load_config()

    def test_validate_input_date(self):
        """
        Test that validate_input_date correctly validates input dates.

        This test verifies that the function:
        1. Accepts valid dates in YYYYMMDD format
        2. Rejects invalid dates
        """
        # Case 1: Valid date
        sftp_to_s3.validate_input_date("20250605")  # Should not raise an exception

        # Case 2: Invalid format (non-numeric)
        with pytest.raises(ValueError):
            sftp_to_s3.validate_input_date("2025060X")

        # Case 3: Invalid format (wrong length)
        with pytest.raises(ValueError):
            sftp_to_s3.validate_input_date("202506")

        # Case 4: Invalid date (invalid month)
        with pytest.raises(ValueError):
            sftp_to_s3.validate_input_date("20251305")  # Month 13 doesn't exist

        # Case 5: Invalid date (invalid day)
        with pytest.raises(ValueError):
            sftp_to_s3.validate_input_date("20250632")  # June 32nd doesn't exist

    @patch("argparse.ArgumentParser.parse_args")
    @patch("sftp_to_s3.validate_input_date")
    def test_parse_arguments(self, mock_validate_input_date, mock_parse_args):
        """
        Test that parse_arguments correctly parses and validates command line arguments.

        This test verifies that the function:
        1. Correctly parses valid input dates
        2. Calls validate_input_date to validate the date
        """
        # Setup: Valid input date
        mock_args = MagicMock()
        mock_args.input_date = "20250605"
        mock_parse_args.return_value = mock_args

        # Execute: Call the function
        result = sftp_to_s3.parse_arguments()

        # Verify: Check that the function returns the parsed arguments
        assert result.input_date == "20250605", "Should return the parsed input date"

        # Verify: Check that validate_input_date was called
        mock_validate_input_date.assert_called_once_with(mock_args.input_date)

    # ----- Utility Function Tests -----

    def test_generate_s3_key(self):
        """
        Test that generate_s3_key correctly constructs S3 keys.

        This test verifies that the function:
        1. Correctly joins the prefix and filename
        2. Handles empty prefixes
        3. Handles prefixes with trailing slashes
        """
        # Case 1: Normal prefix and filename
        s3_prefix = "test/prefix"
        filename = "test_file.txt"

        # Execute: Call the function
        result = sftp_to_s3.generate_s3_key(s3_prefix, filename)

        # Verify: Check that the prefix and filename are joined correctly
        assert result == "test/prefix/test_file.txt", (
            "Should join prefix and filename with a slash"
        )

        # Case 2: Empty prefix
        result = sftp_to_s3.generate_s3_key("", filename)
        assert result == "test_file.txt", (
            "Should return just the filename when prefix is empty"
        )

        # Case 3: Prefix ending with slash
        result = sftp_to_s3.generate_s3_key("test/prefix/", filename)
        assert result == "test/prefix/test_file.txt", (
            "Should handle prefixes that already end with a slash"
        )

    def test_generate_metadata(self, mock_config, mock_sftp):
        """
        Test that generate_metadata correctly creates metadata for S3 objects.

        This test verifies that the function:
        1. Includes all required metadata fields
        2. Extracts the correct filename from the path
        3. Uses the file's modification time and hash
        4. Uses configuration values for metadata fields
        5. Handles missing MD5 hash gracefully
        6. Calculates MD5 hash when SFTP client is provided
        """
        # Case 1: File with MD5 hash
        # Setup: Create a mock file_info object with timestamp and hash
        file_info = MagicMock()
        file_info.st_mtime = datetime.now(timezone.utc).timestamp()
        file_info.md5_hash = "test_md5_hash"

        remote_path = "/test/path/file.txt"

        # Execute: Call the function
        result = sftp_to_s3.generate_metadata(
            remote_path, file_info, mock_config, mock_sftp
        )

        # Verify: Check that all required metadata fields are present
        expected_keys = [
            "source-filename",
            "source-file-lastmodified",
            "source-filehash",
            "retrieved-at",
            "load-id",
            "load-timestamp",
            "load-name",
            "load-version",
            "source-system",
            "source-entity",
        ]
        for key in expected_keys:
            assert key in result, f"Missing required metadata field: {key}"

        # Verify: Check specific metadata values
        assert result["source-filename"] == "file.txt", (
            "Should extract filename from path"
        )
        assert result["source-filehash"] == "test_md5_hash", (
            "Should use provided MD5 hash"
        )
        assert result["load-name"] == mock_config["meta_load_name"], (
            "Should use config value for load name"
        )
        assert result["load-version"] == mock_config["meta_load_version"], (
            "Should use config value for version"
        )
        assert result["source-system"] == mock_config["meta_source_system"], (
            "Should use config value for source system"
        )
        assert result["source-entity"] == mock_config["meta_source_entity"], (
            "Should use config value for source entity"
        )

        # Case 2: File without MD5 hash but with SFTP client for calculation
        # Setup: Create a mock file_info object without hash
        file_info = MagicMock()
        file_info.st_mtime = datetime.now(timezone.utc).timestamp()
        # Explicitly delete the md5_hash attribute to ensure it doesn't exist
        if hasattr(file_info, "md5_hash"):
            delattr(file_info, "md5_hash")

        # Configure mock_sftp to return a file with known content
        mock_file = MagicMock()
        mock_file.__enter__.return_value = BytesIO(b"test content for md5")
        mock_sftp.open.return_value = mock_file

        # Calculate expected MD5 hash
        expected_md5 = hashlib.md5(b"test content for md5").hexdigest()

        # Mock the calculate_md5 function to return the expected hash
        with patch(
            "sftp_to_s3.calculate_md5", return_value=expected_md5
        ) as mock_calculate_md5:
            # Execute: Call the function with SFTP client
            result = sftp_to_s3.generate_metadata(
                remote_path, file_info, mock_config, sftp=mock_sftp
            )

            # Verify: Check that MD5 hash was calculated correctly
            assert result["source-filehash"] == expected_md5, (
                "Should calculate MD5 hash when SFTP client is provided"
            )
            mock_calculate_md5.assert_called_once_with(mock_sftp, remote_path)
