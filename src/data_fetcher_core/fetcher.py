"""Main fetcher implementation and execution engine.

This module contains the core Fetcher class, FetchPlan, FetchResult, and related
components that orchestrate the data fetching process across different protocols.
"""

import asyncio
from dataclasses import dataclass

import structlog
from openc_python_common.observability.log_util import observe_around

from data_fetcher_core.core import (
    BundleLoadResult,
    BundleRef,
    DataRegistryFetcherConfig,
    FetchPlan,
    FetchRunContext,
)
from data_fetcher_core.exceptions import (
    ConfigurationError,
    FatalError,
    NetworkError,
    ResourceError,
)
from data_fetcher_core.queue import BundleRefSerializer, KVStoreQueue, RequestQueue

# Get logger for this module
logger = structlog.get_logger(__name__)


def _raise_kv_store_required() -> None:
    """Raise error for missing kv_store."""
    error_message = "kv_store is required for persistent queue"
    raise ConfigurationError(error_message, "queue")


def _raise_bundle_loader_required() -> None:
    """Raise error for missing bundle loader."""
    error_message = "Bundle loader is required but was None"
    raise ConfigurationError(error_message, "bundle_loader")


def _raise_app_config_required() -> None:
    """Raise error for missing app config."""
    error_message = "App config is required but was None"
    raise ConfigurationError(error_message, "app_config")


def _raise_storage_required() -> None:
    """Raise error for missing storage."""
    error_message = "Storage is required in app_config but was None"
    raise ConfigurationError(error_message, "storage")


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    processed_count: int
    errors: list[str]
    context: FetchRunContext


class Fetcher:
    """Main fetcher class that orchestrates frontier providers, loaders, and storage."""

    def __init__(self) -> None:
        """Initialize the fetcher."""

    async def run(self, plan: FetchPlan) -> FetchResult:
        """Run the fetcher with the given plan.

        Args:
            plan: The fetch plan containing configuration, context, and execution parameters

        Returns:
            FetchResult with processing statistics
        """
        # Use the context from the plan
        run_ctx = plan.context

        # Ensure run_id is set in the context
        if not run_ctx.run_id:
            error_message = "run_id is required in FetchRunContext but was not provided"
            raise ConfigurationError(error_message, "fetch_run_context")

        # Validate that we have the required components
        if not plan.config.locators:
            error_message = "No locators configured in the fetcher configuration"
            raise ConfigurationError(error_message, "locators")

        if not plan.config.loader:
            error_message = "No loader configured in the fetcher configuration"
            raise ConfigurationError(error_message, "loader")

        # Call on_run_start hook on storage component (if it exists)
        if (
            run_ctx.app_config
            and run_ctx.app_config.storage
            and hasattr(run_ctx.app_config.storage, "on_run_start")
        ):
            logger.info(
                "CALLING_STORAGE_ON_RUN_START_HOOK",
                storage_type=type(run_ctx.app_config.storage).__name__,
            )
            await run_ctx.app_config.storage.on_run_start(run_ctx, plan.config)

        logger.info(
            "FETCHER_RUN_STARTED",
            run_id=run_ctx.run_id,
            concurrency=plan.concurrency,
            target_queue_size=plan.target_queue_size,
            locators=len(plan.config.locators),
        )

        # Create persistent queue using kv_store
        if not run_ctx.app_config or not run_ctx.app_config.kv_store:
            _raise_kv_store_required()

        queue: RequestQueue = KVStoreQueue(
            kv_store=run_ctx.app_config.kv_store,  # type: ignore[union-attr]
            namespace=f"fetch:{run_ctx.run_id}",
            serializer=BundleRefSerializer(),
        )

        # Coordination primitives
        locator_completion_flag = asyncio.Event()

        # Start the locator thread to manage queue population
        locator_task = asyncio.create_task(
            self._locator_thread(
                queue,
                locator_completion_flag,
                plan.target_queue_size,
                plan.config,
                run_ctx,
            )
        )

        # Start workers
        workers = []
        for worker_id in range(plan.concurrency):
            worker = asyncio.create_task(
                self._worker(
                    worker_id,
                    queue,
                    plan.config,
                    run_ctx,
                    locator_completion_flag,
                )
            )
            workers.append(worker)
            logger.debug("WORKER_STARTED", worker_id=worker_id)

        # Log initial queue size
        initial_size = await queue.size()
        logger.info("INITIAL_QUEUE_SIZE", queue_size=initial_size)

        # Wait for locator thread to complete (no more URLs available)
        await locator_task
        logger.info("LOCATOR_THREAD_COMPLETED", run_id=run_ctx.run_id)

        # Wait for all workers to complete (they will process remaining items in queue)
        await asyncio.gather(*workers, return_exceptions=True)
        logger.info("ALL_WORKERS_COMPLETED", run_id=run_ctx.run_id)

        # Clean up queue resources
        await queue.close()

        # If nothing was processed and we have errors, treat run as failed
        if run_ctx.processed_count == 0 and run_ctx.errors:
            # Raise a fatal error so the caller can exit non-zero gracefully
            raise FatalError(
                f"Fetch run failed with {len(run_ctx.errors)} error(s) and 0 items processed"
            )

        return FetchResult(
            processed_count=run_ctx.processed_count,
            errors=run_ctx.errors,
            context=run_ctx,
        )

    async def _locator_thread(
        self,
        queue: RequestQueue,
        completion_flag: asyncio.Event,
        target_queue_size: int,
        config: DataRegistryFetcherConfig,
        run_ctx: FetchRunContext,
    ) -> None:
        """Dedicated thread that manages queue population by requesting BundleRefs from locators.

        This thread ensures there are at least target_queue_size items in the queue
        by requesting bundle refs from locators until the queue is full or all locators
        are exhausted.

        Args:
            queue: The persistent work queue to populate
            completion_flag: Event to signal when no more bundle refs are available
            target_queue_size: Target number of items to maintain in the queue
            config: The fetcher configuration containing bundle locators
            run_ctx: The fetch run context for this execution
        """
        locator_logger = logger.bind(component="locator_thread")
        locator_logger.info(
            "LOCATOR_THREAD_STARTED", target_queue_size=target_queue_size
        )

        current_locator_index = 0

        while not completion_flag.is_set():
            try:
                current_queue_size = await queue.size()

                # If queue is already at or above target size, wait a bit
                if current_queue_size >= target_queue_size:
                    await asyncio.sleep(0.1)
                    continue

                # Calculate how many bundle refs we need to reach target
                bundle_refs_needed = target_queue_size - current_queue_size

                # Try to get bundle refs from current locator
                if current_locator_index < len(config.locators):
                    provider = config.locators[current_locator_index]

                    locator_logger.debug(
                        "REQUESTING_BUNDLE_REFS_FROM_LOCATOR",
                        locator_type=type(provider).__name__,
                        locator_index=current_locator_index,
                        bundle_refs_needed=bundle_refs_needed,
                        current_queue_size=current_queue_size,
                    )

                    # Request bundle refs from current locator
                    next_bundle_refs = await provider.get_next_bundle_refs(
                        run_ctx, bundle_refs_needed
                    )

                    locator_logger.debug(
                        "RECEIVED_BUNDLE_REFS_FROM_LOCATOR",
                        locator_type=type(provider).__name__,
                        locator_index=current_locator_index,
                        bundle_ref_count=len(next_bundle_refs),
                    )

                    # Guard: Check if locator returned more than requested
                    if len(next_bundle_refs) > bundle_refs_needed:
                        error_msg = (
                            f"Locator {type(provider).__name__} returned {len(next_bundle_refs)} "
                            f"bundle refs but only {bundle_refs_needed} were requested"
                        )
                        locator_logger.error(
                            "LOCATOR_RETURNED_TOO_MANY_BUNDLE_REFS",
                            locator_type=type(provider).__name__,
                            returned_count=len(next_bundle_refs),
                            requested_count=bundle_refs_needed,
                        )
                        raise ConfigurationError(error_msg, "bundle_locator")

                    # Add bundle refs to queue
                    if next_bundle_refs:
                        await queue.enqueue(next_bundle_refs)
                        new_size = await queue.size()
                        locator_logger.debug(
                            "BUNDLE_REFS_ADDED_TO_QUEUE",
                            bundle_ref_count=len(next_bundle_refs),
                            queue_size=new_size,
                        )

                    # If this locator didn't return any bundle refs, move to next locator
                    if not next_bundle_refs:
                        current_locator_index += 1
                        locator_logger.debug(
                            "LOCATOR_EXHAUSTED_MOVING_TO_NEXT",
                            current_locator_index=current_locator_index,
                            total_locators=len(config.locators),
                        )
                else:
                    # All locators exhausted
                    final_size = await queue.size()
                    locator_logger.info(
                        "ALL_LOCATORS_EXHAUSTED_SETTING_COMPLETION_FLAG",
                        queue_size=final_size,
                    )
                    completion_flag.set()
                    break

            except Exception as e:
                # Fail-fast policy: any locator failure aborts the run
                if isinstance(e, ConfigurationError | FatalError):
                    locator_logger.exception(
                        "LOCATOR_THREAD_FATAL_ERROR",
                        error=str(e),
                        error_type=type(e).__name__,
                        locator_index=current_locator_index,
                    )
                else:
                    locator_logger.exception(
                        "LOCATOR_THREAD_ERROR",
                        error=str(e),
                        error_type=type(e).__name__,
                        locator_index=current_locator_index,
                    )

                completion_flag.set()
                # Raise a fatal error so the task bubbles up and terminates run
                raise

        locator_logger.info("LOCATOR_THREAD_COMPLETED")

    async def _worker(
        self,
        worker_id: int,
        queue: RequestQueue,
        config: DataRegistryFetcherConfig,
        run_ctx: FetchRunContext,
        completion_flag: asyncio.Event,
    ) -> None:
        """Worker process that handles requests from the queue.

        This worker only processes requests from the queue. Queue population
        is handled by the dedicated locator thread.

        Args:
            worker_id: Unique identifier for this worker
            queue: The persistent work queue to process requests from
            config: The fetcher configuration containing bundle loaders
            run_ctx: The fetch run context for this execution
            processed_count_lock: Thread lock for accessing processed count
            errors_lock: Thread lock for accessing error list
            completion_flag: Event to signal when no more work will be added
        """
        worker_logger = logger.bind(worker_id=worker_id)
        worker_logger.info("WORKER_STARTED", worker_id=worker_id)
        initial_size = await queue.size()
        worker_logger.info("WORKER_STARTED_WITH_QUEUE_SIZE", queue_size=initial_size)

        bundle_ref: BundleRef | None = None
        while True:
            try:
                # Get next request from persistent queue
                requests = await queue.dequeue(max_items=1)
                if not requests:
                    # If no work and locators are done, exit
                    if completion_flag.is_set():
                        worker_logger.info(
                            "NO_MORE_REQUESTS_WORKER_EXITING", worker_id=worker_id
                        )
                        break
                    # Wait a bit for more work to arrive
                    await asyncio.sleep(0.1)
                    continue

                bundle_ref = requests[0]
                if not isinstance(bundle_ref, BundleRef):
                    worker_logger.error(
                        "Invalid queue item type",
                        item_type=type(bundle_ref).__name__,
                        worker_id=worker_id,
                    )
                    continue

                # Process the request
                with observe_around(
                    worker_logger.bind(bid=str(getattr(bundle_ref, "bid", "unknown"))),
                    "WORKER_PROCESS_URL",
                    worker_id=worker_id,
                ):
                    await self._process_request(bundle_ref, config, run_ctx)

            except Exception as e:
                bid_str = str(getattr(bundle_ref, "bid", "unknown"))
                if isinstance(e, ConfigurationError | FatalError):
                    worker_logger.exception(
                        "WORKER_FATAL_ERROR",
                        error_type=type(e).__name__,
                        worker_id=worker_id,
                        bid=bid_str,
                    )
                else:
                    worker_logger.exception(
                        "WORKER_ERROR",
                        error_type=type(e).__name__,
                        worker_id=worker_id,
                        bid=bid_str,
                    )

        worker_logger.debug("WORKER_COMPLETED")

    async def _process_request(
        self,
        bundle: BundleRef,
        config: DataRegistryFetcherConfig,
        run_ctx: FetchRunContext,
    ) -> None:
        """Process a single request through the pipeline."""
        try:
            logger.debug("REQUEST_PROCESSING", bid=str(bundle.bid))

            # 1. LOAD (Streaming Data Collection)
            if not config.loader:
                _raise_bundle_loader_required()

            # Get storage from app_config - must exist
            if not run_ctx.app_config:
                _raise_app_config_required()

            storage = run_ctx.app_config.storage  # type: ignore[union-attr]
            if not storage:
                _raise_storage_required()

            logger.debug(
                "REQUEST_LOADING_WITH_LOADER",
                loader_type=type(config.loader).__name__,
            )
            load_result: BundleLoadResult = await config.loader.load(
                bundle, storage, run_ctx, config
            )
            logger.debug(
                "REQUEST_LOADED_SUCCESSFULLY",
                bid=str(bundle.bid),
                bundle_resources=len(load_result.resources),
            )

            # 2. Notify providers that URL was processed
            for provider in config.locators:
                if hasattr(provider, "handle_url_processed"):
                    logger.debug(
                        "PROVIDER_NOTIFICATION_URL_PROCESSED",
                        bid=str(bundle.bid),
                        provider_type=type(provider).__name__,
                    )
                    await provider.handle_url_processed(bundle, load_result, run_ctx)

            logger.debug("REQUEST_PROCESSING_COMPLETED", bid=str(bundle.bid))
            run_ctx.processed_count += 1

        except Exception as e:
            # Create appropriate error message based on error type
            if isinstance(e, NetworkError | ResourceError):
                error_msg = (
                    f"Network/Resource error processing bundle {bundle.bid!s}: {e!s}"
                )
                logger.warning(
                    "REQUEST_PROCESSING_NETWORK_ERROR",
                    bid=str(bundle.bid),
                    error=str(e),
                    error_type=type(e).__name__,
                )
            elif isinstance(e, ConfigurationError | FatalError):
                error_msg = f"Fatal error processing bundle {bundle.bid!s}: {e!s}"
                logger.exception(
                    "REQUEST_PROCESSING_FATAL_ERROR",
                    bid=str(bundle.bid),
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                error_msg = f"Error processing bundle {bundle.bid!s}: {e!s}"
                logger.warning(
                    "REQUEST_PROCESSING_ERROR",
                    bid=str(bundle.bid),
                    error=str(e),
                    error_type=type(e).__name__,
                )

            run_ctx.errors.append(error_msg)


def run_fetcher(config_name: str, **kwargs: object) -> FetchResult:
    """Convenience function to run a fetcher with a predefined configuration.

    Args:
        config_name: Name of the configuration to use
        **kwargs: Additional parameters to override

    Returns:
        FetchResult with processing statistics
    """
    from .config_registry import get_config_setup_function, get_fetcher  # noqa: PLC0415

    fetcher = get_fetcher(config_name)

    # Get the configured configuration
    setup_func = get_config_setup_function(config_name)
    config = setup_func()

    # Note: The run_fetcher convenience function no longer handles app_config
    # since the fetcher is now stateless. App configuration should be handled
    # by the caller before creating the plan.

    # Extract known FetchPlan parameters from kwargs
    concurrency = kwargs.get("concurrency", 1)
    if not isinstance(concurrency, int):
        raise TypeError("Invalid concurrency type")

    target_queue_size = kwargs.get("target_queue_size", 100)
    if not isinstance(target_queue_size, int):
        raise TypeError("Invalid target_queue_size type")

    plan = FetchPlan(
        config=config,
        context=FetchRunContext(run_id=f"run_fetcher_{config_name}"),
        concurrency=concurrency,
        target_queue_size=target_queue_size,
    )

    result: FetchResult = asyncio.run(fetcher.run(plan))
    return result
