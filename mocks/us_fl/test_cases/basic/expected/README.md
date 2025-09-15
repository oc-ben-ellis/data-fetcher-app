# Expected Output for US FL SFTP Test

This directory contains the expected output structure for the US FL SFTP test case.

## Expected Structure

The fetcher should create the following output structure:

```
tmp/test_output/
└── bundle_<BID>/
    ├── bundle.meta
    ├── <sftp_file_1>
    ├── <sftp_file_1>.meta
    ├── <sftp_file_2>
    └── <sftp_file_2>.meta
```

## Expected Files

### bundle.meta
Contains metadata about the bundle:
- `bid`: Bundle ID (UUID)
- `primary_url`: Primary SFTP path that was accessed
- `resources_count`: Number of resources in the bundle
- `storage_key`: Path to the bundle directory
- `meta`: Additional metadata

### SFTP Files
- Files downloaded from the SFTP server
- Each file has a corresponding `.meta` file with metadata about the file

## Expected Content

The SFTP files should contain CSV data with:
- Proper CSV headers
- Data rows with appropriate formatting
- Valid CSV structure

## Validation Criteria

1. **File Count**: Should have at least 1 bundle directory
2. **Bundle Structure**: Each bundle should have a `bundle.meta` file
3. **Content Format**: SFTP files should be valid CSV format
4. **Metadata**: Each file should have a corresponding `.meta` file
5. **Bundle Metadata**: `bundle.meta` should contain required fields
