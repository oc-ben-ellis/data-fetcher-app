# Test Cases Directory

This directory contains test case configurations for functional testing of different data fetcher recipes.

## Structure

Each test case follows this structure:

```
mocks/test_cases/
├── <recipe>/                    # Recipe name (e.g., fr, us_fl)
│   └── <test_case>/            # Test case name (e.g., basic, advanced)
│       ├── inputs/             # Input configuration and sample data
│       │   ├── config.json     # Test configuration
│       │   ├── sample_input.*  # Sample input files (optional)
│       │   └── sample_input_metadata.json  # Input metadata (optional)
│       └── expected/           # Expected output structure
│           ├── README.md       # Expected output documentation
│           └── sample_output/  # Sample expected output files
│               ├── bundle.meta
│               ├── <response_file_1>
│               ├── <response_file_1>.meta
│               └── ...
```

## Test Case Types

### HTTP API Test Cases (e.g., FR)
- Use Mockoon for API mocking
- Include Mockoon environment configuration
- Test OAuth authentication and API responses
- Validate JSON response structure

### SFTP Test Cases (e.g., US_FL)
- Use SFTP mock server
- Test file download and processing
- Validate CSV file structure and content
- Check file metadata and checksums

## Configuration Files

### config.json
Contains the test configuration:
```json
{
  "description": "Test case description",
  "recipe": "recipe_name",
  "credentials": {
    "provider_type": "environment",
    "key1": "value1",
    "key2": "value2"
  },
  "storage": {
    "type": "file",
    "path": "tmp/test_output"
  },
  "additional_config": {
    "key": "value"
  }
}
```

### sample_input_metadata.json
Contains metadata about the input data:
```json
{
  "description": "Input data description",
  "file_count": 2,
  "expected_files": ["file1.csv", "file2.csv"],
  "date_range": {
    "start_date": "2025-09-01",
    "end_date": "2025-09-02"
  }
}
```

## Expected Output

The `expected/sample_output/` directory should contain:
- `bundle.meta`: Bundle metadata with required fields
- Response files: Actual data files (JSON, CSV, etc.)
- `.meta` files: Metadata for each response file

## Running Tests

Tests are automatically discovered and run by the test framework:

```bash
# Run all test cases
poetry run python -m pytest tests/test_functional/test_all_test_cases.py -v

# Run specific recipe tests
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_recipe_test_cases -v

# Run specific test case
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_basic_test_case -v
```

## Adding New Test Cases

1. Create a new directory under `mocks/test_cases/<recipe>/<test_case_name>/`
2. Add `inputs/` and `expected/` subdirectories
3. Create `config.json` with test configuration
4. Add sample input files and metadata (optional)
5. Create expected output structure in `expected/sample_output/`
6. The test framework will automatically discover and run the new test case
