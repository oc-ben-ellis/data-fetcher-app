## General

- Review all code as majority is currently AI generated, suggest starting with tests to ensure expected behaviour is correct.
- Review documentation to ensure it's accurate, up-to-date, concise and easy to understand

## Deployment

- Get deployment working so it uploads docker image to ECR
- Add .github actions.

## Testing

- Test in playground AWS and against live US_FL SFTP and FR

## Monitoring

- Add some observility so we get metrics we can use to measure performance and add alerting for odd behaviours.

## Configurations

- Review US_FL to ensure logic matches existing bot
- Review FR to ensure logic matches existing bot
- Add WebDriver and WebScraper bot configurations

## S3

- Agree on S3 folder naming and structure for bundles
- Agree on metadata approach (Open Lineage?)
- Update Storage / Building to match agreed upon metadata approach
- Update Storage / Bundling to match agreed upon S3 structure

## Protocols

- Review SFTP and HTTP protocols to ensure they are re-using/pooling connections correctly and the authentication and rate limiting works when using multiple connections.
- Add Protocol for WebDriver
- Add Protocol for POP3 (Can we use this instead of webdriver for reading e-mails/couchdrop?)

## Persistence

- Review Persistence logic and agree approach (Elasticache/DynamoDB/Aurora/sqlite3?) - Keep costs in mind as some of my estimates are in the $10,000's per month.
- Discuss / Agree migration strategy for sqlite3 -> Redis/DynamoDB/Aurora if required

## Commands

- Discuss retry/reload options for parsers / higher level orchestration in the case of corrupted or bad resources. Perhaps introduce a "command" concept that can be used to modify the persistence using the fetcher (i.e. refresh_bundle command given a company_number or URL to reload, command_processor updates persistence so the bundle will be retried/reloaded on next run)

## Data Fetcher Application TODOs (from PDF comparison)

## Downstream Notifications (SQS)
- [ ] Implement an SQS publisher to emit messages upon successful bundle processing
- [ ] Define the message schema and ensure it includes necessary metadata (fetcher_id, bundle key(s), count, timestamps)
- [ ] Wire SQS publisher into bundle close/commit points in storage layer
- [ ] Add configurable SQS queue URL and message attributes via environment variables
- [ ] Files: `data_fetcher/fetcher.py`, `data_fetcher/storage/*` (new `notifications/sqs_publisher.py`), `data_fetcher/global_configuration`

## CLI Enhancements
- [ ] Add `--list-configs` or `list` command to print available configuration IDs
- [ ] Ensure CLI provides clear and concise output for configuration discovery
- [ ] Files: `data_fetcher/main.py`, `data_fetcher/registry.py`

## HTML Scraping Enhancements
- [ ] Implement robust HTML parsing to extract related assets (links, CSS, JS, images)
- [ ] Replace stubbed `_extract_related_urls` with actual HTML parsing logic
- [ ] Add robots.txt respect and rate limiting for related resource discovery
- [ ] Implement de-duplication and bounded crawl depth per request
- [ ] Files: `data_fetcher/bundle_loaders/http_loader.py`, new `data_fetcher/html/` helper

## FTP Protocol Support
- [ ] Add `FtpManager` with rate limiting, retries, and connection pooling
- [ ] Implement matching `FtpLoader` for FTP data fetching
- [ ] Ensure parity with SFTP features (directory listing, file streaming, pattern filtering)
- [ ] Files: `data_fetcher/protocols/ftp_manager.py`, `data_fetcher/bundle_loaders/ftp_loader.py`, `data_fetcher/factory.py`

## Checksum/ETag Handling for Storage
- [ ] Add optional content checksum calculation (sha256) for uploads
- [ ] Implement ETag handling and store in metadata
- [ ] Add validation for re-uploads or duplicate detection if configured
- [ ] Files: `data_fetcher/storage/s3_storage.py`, `data_fetcher/storage/file_storage.py`

## Lineage Integration
- [ ] Wire existing lineage bundle (`data_fetcher/storage/lineage_storage.py`) into default storage builder
- [ ] Add config flags to enable lineage emission
- [ ] Add optional lineage publishing to SQS/Kinesis/OTEL
- [ ] Files: `data_fetcher/storage/builder.py`, `data_fetcher/global_storage.py`

## Metrics and Observability
- [ ] Add counters/timers for key stages (requests queued, processed, bundle writes, retries)
- [ ] Implement pluggable metrics interface for Prometheus/OTEL
- [ ] Add metrics hooks to fetcher, loaders, and protocol managers
- [ ] Files: `data_fetcher/fetcher.py`, `data_fetcher/bundle_loaders/*`, protocol managers

## Configuration Parity and Examples
- [ ] Ensure examples include both HTTP/API and SFTP configurations
- [ ] Add FTP configuration example once implemented
- [ ] Provide config for enabling SQS notifications, lineage, and checksums
- [ ] Files: `data_fetcher/configurations/*`, `docs/02_configurations/`

## State Management Enhancements
- [ ] Add explicit "resume token" in `FetchRunContext`
- [ ] Add CLI flag to resume from last successful position
- [ ] Enhance locator state persistence with resume capabilities
- [ ] Files: `data_fetcher/core.py`, `data_fetcher/bundle_locators/*`, `data_fetcher/main.py`

## Hybrid Approach Sample
- [ ] Create configuration that composes API and SFTP locators together for single run plan
- [ ] Document hybrid fetching strategies and provide examples
- [ ] Files: `data_fetcher/configurations/*`, `data_fetcher/registry.py`

## Retry/Backoff Policy Surfacing
- [ ] Expose per-config override knobs for HTTP/SFTP retry settings
- [ ] Add environment variable support for max retries, base delay, jitter
- [ ] Make retry policies configurable per protocol manager
- [ ] Files: `data_fetcher/protocols/http_manager.py`, `data_fetcher/protocols/sftp_manager.py`, `data_fetcher/factory.py`

## Documentation Updates
- [ ] Update docs to include SQS notification schema
- [ ] Document new CLI list command usage
- [ ] Add HTML scraper behavior documentation
- [ ] Document FTP support once implemented
- [ ] Add lineage/checksums enablement instructions
- [ ] Files: `docs/01_architecture/*`, `docs/05_storage/*`, `docs/02_configurations/*`, `docs/APPLICATION_REQUIREMENTS.md`

## Development Ergonomics
- [ ] Add example environment for S3/SQS local endpoints (LocalStack)
- [ ] Demonstrate full local run (capture, store, notify)
- [ ] Create `.env.example` with all configurable options
- [ ] Files: `docs/07_deployment/`, `.env.example`, `Makefile`
