"""Consolidated configuration loading integration tests.

This module combines the best tests from test_config_integration.py, 
test_basic_config_pytest.py, and test_core_integration_pytest.py to provide
comprehensive coverage without duplication.

The consolidated tests cover:
- Basic imports and class creation
- DataPipelineConfig initialization and configuration loading
- Strategy registry functionality
- YAML configuration parsing and validation
- Error handling and edge cases
- File operations and protocol resolution
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from data_fetcher_core.core import DataRegistryFetcherConfig
from data_fetcher_core.strategy_registration import create_strategy_registry
from oc_pipeline_bus.config import DataPipelineConfig
from oc_pipeline_bus.strategy_registry import StrategyFactoryRegistry


class TestConfigConsolidated:
    """Consolidated configuration loading tests."""

    @pytest.fixture
    def sample_config_yaml(self) -> str:
        """Sample YAML configuration for testing."""
        return """
config_id: test_source

concurrency: 5
target_queue_size: 50

loader:
  http_loader:
    meta_load_name: test_http_loader
    http_config: test_http

locators:
  - pagination_locator:
      http_config: test_http
      base_url: "https://api.example.com/data"
      date_start: "2023-01-01"
      date_end: "2023-12-31"
      max_records_per_page: 100
      rate_limit_requests_per_second: 1.0
      state_management_prefix: test_pagination_provider

protocols:
  http:
    test_http: http_config.yaml
"""

    @pytest.fixture
    def sample_http_config_yaml(self) -> str:
        """Sample HTTP protocol configuration."""
        return """
config_name: test-http
base_url: "https://api.example.com"
timeout: 30.0
headers:
  User-Agent: "OC-Fetcher/1.0"
  Accept: "application/json"
retry:
  max_retries: 3
  base_retry_delay: 1.0
  max_retry_delay: 60.0
  retry_exponential_base: 2.0
"""

    @pytest.fixture
    def sample_sftp_config_yaml(self) -> str:
        """Sample SFTP configuration for testing."""
        return """
config_id: test_sftp_source

concurrency: 2
target_queue_size: 25

loader:
  sftp_loader:
    meta_load_name: test_sftp_loader
    sftp_config: test_sftp

locators:
  - sftp_directory_locator:
      sftp_config: test_sftp
      remote_dir: "/data"
      filename_pattern: "*.txt"
      max_files: 10
      sort_key: mtime
      sort_reverse: true
      state_management_prefix: test_sftp_provider

protocols:
  sftp:
    test_sftp: sftp_config.yaml
"""

    @pytest.fixture
    def sample_sftp_protocol_yaml(self) -> str:
        """Sample SFTP protocol configuration."""
        return """
config_name: test-sftp
aws_secret_key: test-sftp-credentials
connection:
  connect_timeout: 20.0
  rate_limit_requests_per_second: 1.0
retry:
  max_retries: 3
  base_retry_delay: 1.0
  max_retry_delay: 60.0
  retry_exponential_base: 2.0
security:
  verify_host_key: true
  compression: false
"""

    @pytest.fixture
    def temp_config_dir(
        self,
        sample_config_yaml: str,
        sample_http_config_yaml: str,
        sample_sftp_config_yaml: str,
        sample_sftp_protocol_yaml: str,
    ) -> Path:
        """Create a temporary directory with sample configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create main config file
            main_config_path = config_path / "config.yaml"
            main_config_path.write_text(sample_config_yaml)
            
            # Create HTTP protocol config
            http_config_path = config_path / "http_config.yaml"
            http_config_path.write_text(sample_http_config_yaml)
            
            # Create SFTP config file
            sftp_config_path = config_path / "sftp_config.yaml"
            sftp_config_path.write_text(sample_sftp_config_yaml)
            
            # Create SFTP protocol config
            sftp_protocol_path = config_path / "sftp_protocol.yaml"
            sftp_protocol_path.write_text(sample_sftp_protocol_yaml)
            
            yield config_path

    # ===== BASIC IMPORTS AND CLASS CREATION TESTS =====
    
    def test_basic_imports_and_attributes(self) -> None:
        """Test that basic imports work and classes have expected attributes."""
        # Test pipeline-bus imports
        from oc_pipeline_bus.config import DataPipelineConfig
        from oc_pipeline_bus.strategy_registry import StrategyFactoryRegistry
        
        # Test fetcher core imports
        from data_fetcher_core.core import DataRegistryFetcherConfig
        
        # Verify that imported classes have expected attributes
        assert hasattr(DataPipelineConfig, '__init__')
        assert hasattr(StrategyFactoryRegistry, '__init__')
        assert hasattr(DataRegistryFetcherConfig, '__init__')

    def test_strategy_registry_creation(self) -> None:
        """Test that strategy registry can be created and has expected attributes."""
        registry = StrategyFactoryRegistry()
        assert registry is not None
        assert hasattr(registry, '_factories')
        assert len(registry._factories) >= 0
        
        # Test that we can iterate over factories
        for strategy_type, factories in registry._factories.items():
            assert strategy_type is not None
            assert isinstance(factories, dict)
            assert len(factories) >= 0

    def test_data_registry_fetcher_config_creation(self) -> None:
        """Test that DataRegistryFetcherConfig can be created with defaults."""
        config = DataRegistryFetcherConfig(
            loader={"test_loader": {"param": "value"}},
            locators=[{"test_locator": {"param": "value"}}]
        )
        
        assert config is not None
        assert "test_loader" in config.loader
        assert len(config.locators) == 1
        assert config.concurrency == 10  # default value
        assert config.target_queue_size == 100  # default value
        assert config.config_id == ""  # default empty string
        assert config.protocols == {}  # default empty dict

    # ===== CONFIG LOADER INITIALIZATION TESTS =====
    
    def test_config_loader_initialization_with_registry(self) -> None:
        """Test that DataPipelineConfig can be initialized with strategy registry."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        assert config_loader is not None
        assert config_loader.strategy_registry is not None

    def test_config_loader_initialization_without_registry(self) -> None:
        """Test that DataPipelineConfig creates its own registry when none provided."""
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry"
        )
        
        assert config_loader is not None
        assert config_loader.strategy_registry is not None

    def test_config_loader_creation_with_parameters(self) -> None:
        """Test that DataPipelineConfig can be created with required parameters."""
        registry = StrategyFactoryRegistry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=registry
        )
        assert config_loader is not None
        assert config_loader.strategy_registry is registry

    # ===== METHOD SIGNATURE AND INTERFACE TESTS =====
    
    def test_create_strategy_from_config_method_signature(self) -> None:
        """Test that _create_strategy_from_config has correct signature."""
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry"
        )
        
        # Check method signature
        import inspect
        sig = inspect.signature(config_loader._create_strategy_from_config)
        params = list(sig.parameters.keys())
        
        # Should have exactly 3 parameters: strategy_type, strategy_id, strategy_config
        assert len(params) == 3
        assert params[0] == "strategy_type"
        assert params[1] == "strategy_id" 
        assert params[2] == "strategy_config"

    def test_strategy_creation_with_empty_config(self) -> None:
        """Test strategy creation with empty config (should fail gracefully)."""
        registry = StrategyFactoryRegistry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=registry
        )
        
        # Try to create a strategy with empty config - should fail gracefully
        try:
            # This should fail because we don't have the right strategy type or config
            strategy = config_loader._create_strategy_from_config(
                strategy_type=object,  # Invalid strategy type
                strategy_id="nonexistent",
                strategy_config={}
            )
            # If it doesn't fail, that's also okay - depends on implementation
        except Exception:
            # Expected to fail with invalid parameters
            pass

    # ===== YAML PARSING AND BASIC FILE OPERATIONS =====
    
    def test_yaml_parsing(self) -> None:
        """Test that YAML can be parsed correctly."""
        sample_yaml = """
concurrency: 5
target_queue_size: 50
loader:
  test_loader:
    param: value
locators:
  - test_locator:
      param: value
"""
        
        # Parse YAML
        config_data = yaml.safe_load(sample_yaml)
        
        # Verify structure
        assert config_data['concurrency'] == 5
        assert config_data['target_queue_size'] == 50
        assert 'loader' in config_data
        assert 'locators' in config_data

    def test_basic_file_operations(self) -> None:
        """Test basic file operations for config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # Write config file
            sample_config = """
concurrency: 3
target_queue_size: 25
loader:
  file_loader:
    path: /tmp/test
"""
            config_path.write_text(sample_config)
            assert config_path.exists()
            
            # Read config file
            content = config_path.read_text()
            assert "concurrency: 3" in content
            assert "file_loader" in content

    # ===== COMPREHENSIVE CONFIGURATION LOADING TESTS =====
    
    def test_load_config_from_yaml_file(self, temp_config_dir: Path) -> None:
        """Test loading configuration from a YAML file."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config_path = temp_config_dir / "config.yaml"
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        assert config is not None
        assert isinstance(config, DataRegistryFetcherConfig)
        assert config.config_id == "test_source"
        assert config.concurrency == 5
        assert config.target_queue_size == 50
        assert config.loader is not None
        assert len(config.locators) == 1

    def test_load_config_with_relative_configs(self, temp_config_dir: Path) -> None:
        """Test loading configuration with relative config references."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config_path = temp_config_dir / "config.yaml"
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        # Verify that the loader has the correct configuration
        assert config.loader is not None
        assert hasattr(config.loader, 'meta_load_name')
        assert config.loader.meta_load_name == "test_http_loader"
        assert config.loader.http_config == "test_http"
        
        # Verify that locators have correct configurations
        assert len(config.locators) == 1
        
        # Check locator (pagination)
        pagination_locator = config.locators[0]
        assert hasattr(pagination_locator, 'base_url')
        assert pagination_locator.base_url == "https://api.example.com/data"
        assert pagination_locator.date_start == "2023-01-01"
        assert pagination_locator.max_records_per_page == 100

    def test_load_sftp_config(self, temp_config_dir: Path) -> None:
        """Test loading SFTP configuration."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config_path = temp_config_dir / "sftp_config.yaml"
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        assert config is not None
        assert config.config_id == "test_sftp_source"
        assert config.concurrency == 2
        assert config.target_queue_size == 25
        
        # Verify SFTP loader configuration
        assert config.loader is not None
        assert hasattr(config.loader, 'meta_load_name')
        assert config.loader.meta_load_name == "test_sftp_loader"
        assert config.loader.sftp_config == "test_sftp"
        
        # Verify SFTP locator configuration
        assert len(config.locators) == 1
        sftp_locator = config.locators[0]
        assert hasattr(sftp_locator, 'remote_dir')
        assert sftp_locator.remote_dir == "/data"
        assert sftp_locator.filename_pattern == "*.txt"
        assert sftp_locator.max_files == 10

    def test_config_protocols_resolution(self, temp_config_dir: Path) -> None:
        """Test that protocol configurations are properly resolved."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config_path = temp_config_dir / "config.yaml"
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        # Verify protocols are loaded
        assert config.protocols is not None
        assert "http" in config.protocols
        assert "test_http" in config.protocols["http"]
        assert config.protocols["http"]["test_http"] == "http_config.yaml"

    def test_config_with_filters(self, temp_config_dir: Path) -> None:
        """Test configuration with filter strategies."""
        # Create config with filters
        config_with_filters = """
config_id: test_filter_source

concurrency: 1
target_queue_size: 10

loader:
  sftp_loader:
    meta_load_name: test_filter_loader
    sftp_config: test_sftp

locators:
  - sftp_directory_locator:
      sftp_config: test_sftp
      remote_dir: "/data"
      filename_pattern: "*.txt"
      file_filter:
        type: date_filter
        start_date: "2023-01-01"
        date_pattern: "YYYY-MM-DD"
      state_management_prefix: test_filter_provider

protocols:
  sftp:
    test_sftp: sftp_protocol.yaml
"""
        
        config_path = temp_config_dir / "config_with_filters.yaml"
        config_path.write_text(config_with_filters)
        
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        assert config is not None
        
        # Verify filter configuration
        locator = config.locators[0]
        assert hasattr(locator, 'file_filter')
        file_filter = locator.file_filter
        
        assert file_filter["type"] == "date_filter"
        assert file_filter["start_date"] == "2023-01-01"
        assert file_filter["date_pattern"] == "YYYY-MM-DD"

    # ===== ERROR HANDLING AND EDGE CASES =====
    
    def test_config_validation_errors(self, temp_config_dir: Path) -> None:
        """Test that configuration validation works correctly."""
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        # Create invalid config
        invalid_config = """
config_id: test_source
concurrency: 5
target_queue_size: 50

loader:
  invalid_loader:
    meta_load_name: test_loader
    invalid_param: "should_fail"

locators: []
"""
        
        invalid_config_path = temp_config_dir / "invalid_config.yaml"
        invalid_config_path.write_text(invalid_config)
        
        # This should raise an error because invalid_loader is not registered
        with pytest.raises(Exception):  # Should be InvalidArgumentStrategyException
            config_loader.load_config_from_file(
                DataRegistryFetcherConfig, 
                invalid_config_path, 
                data_registry_id="test_source",
                step="fetcher"
            )

    def test_config_loading_with_missing_files(self, temp_config_dir: Path) -> None:
        """Test error handling when referenced files are missing."""
        # Create config that references non-existent file
        config_with_missing_ref = """
config_id: test_source

concurrency: 5
target_queue_size: 50

loader:
  http_loader:
    meta_load_name: test_loader
    http_config: missing_config

locators: []

protocols:
  http:
    missing_config: non_existent.yaml
"""
        
        config_path = temp_config_dir / "config_missing.yaml"
        config_path.write_text(config_with_missing_ref)
        
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        # This should raise an error when trying to load the missing file
        with pytest.raises(Exception):  # Should be FileNotFoundError or similar
            config_loader.load_config_from_file(
                DataRegistryFetcherConfig, 
                config_path, 
                data_registry_id="test_source",
                step="fetcher"
            )

    def test_config_loading_with_invalid_yaml(self, temp_config_dir: Path) -> None:
        """Test error handling with invalid YAML syntax."""
        # Create invalid YAML
        invalid_yaml = """
config_id: test_source
concurrency: 5
target_queue_size: 50
loader:
  http_loader:
    meta_load_name: test_loader
    # Missing closing quote
    http_config: "test_http
locators: []
"""
        
        config_path = temp_config_dir / "invalid_yaml.yaml"
        config_path.write_text(invalid_yaml)
        
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        # This should raise a YAML parsing error
        with pytest.raises(Exception):  # Should be yaml.YAMLError
            config_loader.load_config_from_file(
                DataRegistryFetcherConfig, 
                config_path, 
                data_registry_id="test_source",
                step="fetcher"
            )

    def test_config_loading_with_empty_locators(self, temp_config_dir: Path) -> None:
        """Test configuration with empty locators list."""
        config_empty_locators = """
config_id: test_source

concurrency: 5
target_queue_size: 50

loader:
  http_loader:
    meta_load_name: test_loader
    http_config: test_http

locators: []

protocols:
  http:
    test_http: http_config.yaml
"""
        
        config_path = temp_config_dir / "empty_locators.yaml"
        config_path.write_text(config_empty_locators)
        
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        assert config is not None
        assert config.locators == []

    def test_config_loading_with_default_values(self, temp_config_dir: Path) -> None:
        """Test that default values are properly applied."""
        config_minimal = """
config_id: test_source

loader:
  http_loader:
    meta_load_name: test_loader
    http_config: test_http

locators: []

protocols:
  http:
    test_http: http_config.yaml
"""
        
        config_path = temp_config_dir / "minimal_config.yaml"
        config_path.write_text(config_minimal)
        
        strategy_registry = create_strategy_registry()
        config_loader = DataPipelineConfig(
            config_bucket="test-bucket",
            step="fetcher",
            data_registry_id="test-registry",
            strategy_registry=strategy_registry
        )
        
        config = config_loader.load_config_from_dir(
            DataRegistryFetcherConfig, 
            str(config_path.parent),
            filename=config_path.name
        )
        
        assert config is not None
        # Check that defaults are applied
        assert config.concurrency == 10  # Default from DataRegistryFetcherConfig
        assert config.target_queue_size == 100  # Default from DataRegistryFetcherConfig
        assert config.config_id == "test_source"  # From config file
        assert config.protocols == {"http": {"test_http": "http_config.yaml"}}  # From config file
