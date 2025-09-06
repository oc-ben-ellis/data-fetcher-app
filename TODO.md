## General (going to have to keep doing this over and over)

- Review all code as majority is currently AI generated, suggest starting with tests to ensure expected behaviour is correct.
- Review documentation to ensure it's accurate, up-to-date, concise and easy to understand

## Deployment

- Get deployment working so it uploads docker image to ECR
- Add .github actions.

## Testing

- Test in playground AWS and against live US_FL SFTP and FR

## Recipes

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

## HTML Scraping Enhancements
- [ ] Implement robust HTML parsing to extract related assets (links, CSS, JS, images)
- [ ] Replace stubbed `_extract_related_urls` with actual HTML parsing logic
- [ ] Add robots.txt respect and rate limiting for related resource discovery
- [ ] Implement de-duplication and bounded crawl depth per request
- [ ] Files: `data_fetcher/bundle_loaders/http_loader.py`, new `data_fetcher/html/` helper

## Metrics and Observability
- [ ] Add counters/timers for key stages (requests queued, processed, bundle writes, retries)

## SQS Notifications
- [x] Implement SQS notification system for bundle completion
- [x] Add BundleStorageContext for async bundle lifecycle management
- [x] Update storage interface with new start_bundle/complete pattern
- [x] Add completion callbacks for loaders and locators
- [x] Implement pending completion processing for eventual consistency
- [x] Update documentation for new notification system
- [x] Make SQS notifications mandatory for PipelineStorage
