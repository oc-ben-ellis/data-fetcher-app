# Expected Output for French SIREN API Basic Test

This directory contains the expected output structure for the French SIREN API basic test case.

## Expected Structure

The fetcher should create the following output structure:

```
tmp/test_output/
└── bundle_<BID>/
    ├── bundle.meta
    ├── <api_response_file>
    └── <api_response_file>.meta
```

## Expected Files

### bundle.meta
Contains metadata about the bundle:
- `bid`: Bundle ID (UUID)
- `primary_url`: Primary URL that was fetched
- `resources_count`: Number of resources in the bundle
- `storage_key`: Path to the bundle directory
- `meta`: Additional metadata

### API Response Files
- Files containing the actual API responses
- Each file has a corresponding `.meta` file with metadata about the response

## Expected Content

The API response should contain French SIREN data in JSON format with:
- `header`: Response header with status information
- `unitesLegales`: Array of legal entities
- `curseurSuivant`: Next cursor for pagination (if applicable)

## Validation Criteria

1. **File Count**: Should have at least 1 bundle directory
2. **Bundle Structure**: Each bundle should have a `bundle.meta` file
3. **Content Format**: API responses should be valid JSON
4. **Metadata**: Each response file should have a corresponding `.meta` file
5. **Bundle Metadata**: `bundle.meta` should contain required fields
