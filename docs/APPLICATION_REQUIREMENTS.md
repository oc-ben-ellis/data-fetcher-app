## Application Functional Requirements

### 1) Purpose and Scope
- **Purpose**: Provide a composable, streaming-first Python framework to fetch resources from heterogeneous remote sources and store them in a standardized package with metadata for downstream ETL.
- **In Scope**: Orchestration, configuration-driven runs, HTTP(S) and SFTP fetching, streaming storage with decorators (e.g., WARC, unzip), credential management, logging, scheduling, and persistence/kv store.
- **Out of Scope**: Downstream ETL processing, data modeling beyond packaging, visualization.

### 2) Core Concepts and Actors
- **Fetcher**: Orchestrates fetching via a two-phase pipeline with concurrency.
- **Bundle Locator**: Produces URLs/targets to fetch (e.g., API pagination, SFTP directories/files).
- **Bundle Loader**: Fetches a single target and streams content to storage (HTTP/S, SFTP, API).
- **Storage**: Base storages (local files, S3) plus composable decorators (e.g., unzip, WARC, bundle resources).
- **Protocol Manager**: Cross-cutting policies (rate limiting, scheduling) for protocols (HTTP, SFTP).
- **Fetch Context/Plan**: Holds runtime configuration and execution parameters (e.g., concurrency).

### 3) Configuration System
- The system MUST support named configurations discoverable and runnable by ID.
  - CLI MUST accept a configuration name argument; listing available configurations MUST be supported.
  - Programmatic access via `oc_fetcher.registry.get_fetcher(config_name: str)` MUST return a configured fetcher ready to run with a `FetchPlan`.
- Built-in configurations MUST include at least:
  - `us-fl` (SFTP batch processing)
  - `fr` (HTTP/API fetcher)
- Configuration MUST allow:
  - Concurrency and timeout settings
  - Selection/config of protocol managers (rate limits, scheduling)
  - Storage backend and decorator stack
  - Logging/monitoring options
  - Environment-specific overrides (dev/staging/prod) and sensitive settings via env

### 4) CLI Requirements
- Provide a CLI entry point `python -m oc_fetcher.main [CONFIG]`.
  - If no config is provided, the CLI MUST list available configurations.
  - Support `--credentials-provider {aws,env}` with default `aws`.
  - Respect `OC_CONFIG_ID` environment variable as a default configuration identifier.
- CLI MUST print help and examples upon `--help`.

### 5) Programmatic API
- Provide `get_fetcher(config_name: str)` to obtain a configured `Fetcher`.
- `Fetcher.run(plan: FetchPlan)` coroutine MUST execute a full run and return a `FetchResult` with status and context (and errors if any).
- Programmatic users MUST be able to override or augment configuration settings before run.

### 6) Protocol Support and Policies
- **HTTP(S)**:
  - MUST support streaming downloads via an HTTP client without loading entire files in memory.
  - MUST support rate limiting/scheduling via protocol manager.
- **SFTP**:
  - MUST support connection via username/password or key material from credentials provider.
  - MUST support pattern-based directory/file locating, including date-based file patterns.
  - MUST support streaming file transfers directly to storage.
  - MUST support enterprise-grade setup: secrets management and upload to S3.
- **Protocol Managers**:
  - MUST coordinate cross-cutting concerns (rate limits, scheduling).
  - MUST be pluggable per configuration.

### 7) Frontier and Loading
- **Bundle Locators** MUST:
  - Enumerate targets to process (e.g., file paths, URLs, paginated endpoints).
  - Be composable to support directory listing, single-file, generic, and pagination use cases.
- **Bundle Loaders** MUST:
  - Stream payloads directly to storage (no full-RAM buffering).
  - Attach or emit metadata needed for downstream bundling.
  - Integrate with storage decorators (e.g., on-the-fly WARC wrapping).

### 8) Storage and Decorators
- **Base Storage**:
  - MUST support local file storage.
  - MUST support S3 storage; users MUST be able to configure bucket, key prefixes, and credentials resolution consistent with the credential provider.
- **Storage Decorators**:
  - MUST allow stacking (e.g., unzip → warc → bundle).
  - WARC decorator MUST format streaming data into WARC during transfer.
  - Unzip decorator MUST extract archives and route their contents to underlying storage.
- All storage write operations MUST be streaming-friendly and fault-tolerant where possible.

### 9) Credentials Management
- The system MUST support multiple credential providers:
  - `aws`: AWS Secrets Manager (default).
  - `env`: Environment variables.
- Environment variable naming MUST convert configuration IDs with hyphens to uppercase underscores (e.g., `us-fl` → `US_FL`) for variable prefixes.
- Example env variables MUST follow `OC_CREDENTIAL_{CONFIG}_{NAME}` format (e.g., `OC_CREDENTIAL_US_FL_HOST`, `..._USERNAME`, `..._PASSWORD`, `..._CLIENT_ID`, `..._CLIENT_SECRET`).

### 10) Persistence and KV Store
- Provide a global key-value store abstraction for caching and state:
  - MUST support at least in-memory and Redis-like backends as documented.
  - MUST allow storing run state, deduplication keys, and processing markers.
- Fetchers and managers MUST be able to leverage the KV store for caching and deduping.

### 11) Concurrency and Orchestration
- The fetcher MUST implement a two-phase pipeline and concurrent worker model:
  - Workers consume tasks from a shared queue, avoid race conditions, and shut down gracefully when work is exhausted.
  - Concurrency level MUST be configurable via the fetch plan/config.

### 12) Logging and Observability
- MUST use structured logging via `structlog` with context variables and JSON output.
- Logs MUST include component, configuration ID, and request context where applicable.
- SHOULD allow integration with external log collectors via standard output.

### 13) Error Handling and Resilience
- The system MUST:
  - Record and expose errors in `FetchResult`.
  - Support retry/backoff policies where appropriate.
  - Fail individual tasks without crashing the entire run when feasible.
  - Provide clear error diagnostics in logs.

### 14) Scheduling
- The framework MUST support daily and interval-based scheduling options at the configuration level, enabling batch or periodic runs.
- Schedulers SHOULD be pluggable and configurable per use case.

### 15) Testing and Examples
- Provide runnable examples demonstrating:
  - Basic programmatic usage (`examples/basic_usage_example.py`).
  - Persistence usage (`examples/persistence_example.py`).
  - Credential provider usage (`examples/credential_provider_example.py`).
- Include unit tests for protocols and core flows; tests MUST be runnable via `poetry run pytest`.

### 16) Dev Environment and Tooling
- Provide a DevContainer for consistent setup (Docker-in-Docker friendly).
- Provide Make targets for quality:
  - `make format`, `make lint/docstrings`, `make headers`, `make pre-commit`, `make all-checks`.
- Code MUST follow PEP 257 and Google-style docstrings with module headers as documented.

### 17) Deployment
- MUST be deployable in containerized environments (Docker/Kubernetes).
- Documentation MUST cover production requirements, monitoring, security, and scaling guidelines.
- Runtime MUST support passing configuration and credential settings via environment.

### 18) Documentation
- Rendered documentation MUST be buildable (`make docs` / `poetry run build-docs`) and navigable.
- Documentation MUST align with current code (APIs, examples) and follow the project’s documentation guide, including internal links and assets.

### Acceptance Criteria (selected, testable)
- Running `poetry run python -m oc_fetcher.main` lists available configurations.
- Running `poetry run python -m oc_fetcher.main us-fl` with valid credentials streams SFTP files to configured storage with logs.
- Running `poetry run python -m oc_fetcher.main fr` fetches API resources via HTTP streaming and stores results with configured decorators.
- `get_fetcher("us-fl")` returns a fetcher that completes `await fetcher.run(plan)` with a `FetchResult` capturing success/errors.
- Environment credential selection works with `--credentials-provider env` and documented env var names.
- Storage decorators can be stacked and operate in streaming fashion without loading entire payloads into memory.
- `make all-checks` passes on a clean checkout.
- Documentation builds without errors; examples run as documented.

### Future Requirements
- Deployment: Publish Docker images to ECR; add GitHub Actions workflows.
- Testing: Validate in playground AWS and against live `us-fl` SFTP and `fr` API.
- Monitoring & Observability: Provide metrics for performance and alerts for anomalies.
- Configurations: Review `us-fl` and `fr` logic for parity with existing bots. Add WebDriver and WebScraper bot configurations.
- Protocols: Add WebDriver protocol. Evaluate/implement POP3 protocol for email/couchdrop ingestion.
- S3 & Metadata: Agree S3 folder naming/structure for bundles. Agree metadata approach (e.g., OpenLineage). Align storage building/bundling with agreed metadata and structure.
- Persistence: Finalize approach (Elasticache/Redis vs DynamoDB vs Aurora vs sqlite3) with cost considerations. Plan migration strategy from sqlite3 to Redis/DynamoDB/Aurora if needed.

### Requirements Requiring Further Clarification
- Connection Management: Confirm connection pooling/reuse, authentication, and rate limiting behavior under multi-connection concurrency for SFTP and HTTP.
- Command/Retry Semantics: Define higher-level orchestration commands (e.g., refresh_bundle by company_number/URL) that can update persistence to trigger retries/reloads on subsequent runs.
- Monitoring Scope: Specify required metrics (throughput, error rates, queue depths, latency percentiles), sinks (CloudWatch, Prometheus), and alert thresholds.
- S3 Structure & Metadata: Decide on canonical S3 key schema and required metadata schema (e.g., OpenLineage fields) for bundles and derivatives.
- Cost Targets for Persistence: Establish acceptable monthly cost budgets to guide datastore selection and scaling policies.
- Web-Data Ingestion Strategy: Clarify when to use WebDriver vs POP3 for email-based inputs and how they integrate with existing locator/loader abstractions and scheduling.
