# Expected Output for French SIREN API Basic Test

This directory contains the expected output structure for the French SIREN API basic test case.

## Expected S3 Structure

The fetcher should create the following S3 structure in the raw stage:

```
s3://oc-local-data-pipeline/raw/fr/data/
└── year=YYYY/month=MM/day=DD/HH-mm-ss-hex/
    ├── metadata/
    │   ├── _discovered.json          # Bundle discovery metadata
    │   ├── _completed.json           # Bundle completion metadata
    │   ├── _manifest.jsonl           # List of resources in bundle
    │   └── <resource_name>.metadata.json  # Metadata for each resource
    └── content/
        └── <resource_name>           # Actual API response files
```

## Expected Files

### Bundle Metadata Files

#### _discovered.json
Contains metadata about when the bundle was first discovered:
- `bid`: Bundle ID (format: bid:v1:fr:YYYYMMDDHHMMSS:xxxxxxxx)
- `data_registry_id`: Registry identifier (fr)
- `discovered_at`: Timestamp when bundle was found
- `primary_url`: Primary URL that was fetched
- `meta`: Additional discovery metadata

#### _completed.json
Contains metadata about when the bundle was completed:
- `bid`: Bundle ID
- `completed_at`: Timestamp when bundle was marked complete
- `resources_count`: Number of resources in the bundle
- `meta`: Additional completion metadata

#### _manifest.jsonl
JSONL file listing all resources in the bundle:
- One JSON object per line
- Each object contains resource name and metadata

### Resource Files
- Files containing the actual API responses (JSON format)
- Each file has a corresponding `.metadata.json` file with metadata about the response

### Bundle Hashes (CDC)
```
s3://oc-local-data-pipeline/raw/fr/bundle_hashes/
├── _latest                        # Pointer to latest bundle hash
└── <bundle_hash>                  # Hash file linking to BID
```

## Expected Content

The API response should contain French SIREN data in JSON format with:
- `header`: Response header with status information
- `unitesLegales`: Array of legal entities
- `curseurSuivant`: Next cursor for pagination (if applicable)

## Validation Criteria

1. **S3 Structure**: Bundle should be stored under `raw/fr/data/year=YYYY/month=MM/day=DD/HH-mm-ss-hex/`
2. **Bundle Metadata**: All required metadata files (_discovered.json, _completed.json, _manifest.jsonl) must exist
3. **Content Files**: At least one content file should exist in the content/ directory
4. **Resource Metadata**: Each content file should have a corresponding .metadata.json file
5. **CDC Support**: Bundle hashes should exist for change detection
6. **Content Format**: API responses should be valid JSON
7. **Bundle ID Format**: BID should follow the format `bid:v1:fr:YYYYMMDDHHMMSS:xxxxxxxx`
