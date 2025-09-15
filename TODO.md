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

## Retry Logic / Failure handling

- Review this and update as needed

## Metrics and Observability
- [ ] Add counters/timers for key stages (requests queued, processed, bundle writes, retries)
