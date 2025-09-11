"""Main fetcher implementation and execution engine.

This module contains the core Fetcher class, FetchPlan, FetchResult, and related
components that orchestrate the data fetching process across different protocols.
"""

import asyncio
import threading
from dataclasses import dataclass

import structlog
from openc_python_common.observability.log_util import observe_around

from data_fetcher_core.core import (
    FetcherRecipe,
    FetchPlan,
    FetchRunContext,
    RequestMeta,
)
from data_fetcher_core.exceptions import (
    ConfigurationError,
    FatalError,
    NetworkError,
    ResourceError,
)
from data_fetcher_core.queue import KVStoreQueue, RequestMetaSerializer, RequestQueue

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
            plan: The fetch plan containing recipe, context, and execution parameters

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
        if not plan.recipe.bundle_locators:
            error_message = "No bundle locators configured in the fetcher recipe"
            raise ConfigurationError(error_message, "bundle_locators")

        if not plan.recipe.bundle_loader:
            error_message = "No bundle loader configured in the fetcher recipe"
            raise ConfigurationError(error_message, "bundle_loader")

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
            await run_ctx.app_config.storage.on_run_start(run_ctx, plan.recipe)

        logger.info(
            "FETCHER_RUN_STARTED",
            run_id=run_ctx.run_id,
            concurrency=plan.concurrency,
            target_queue_size=plan.target_queue_size,
            bundle_locators=len(plan.recipe.bundle_locators),
        )

        # Thread-safe locks for accessing context counters
        processed_count_lock = threading.Lock()
        errors_lock = threading.Lock()

        # Create persistent queue using kv_store
        if not run_ctx.app_config or not run_ctx.app_config.kv_store:
            _raise_kv_store_required()

        queue: RequestQueue = KVStoreQueue(
            kv_store=run_ctx.app_config.kv_store,  # type: ignore[union-attr]
            namespace=f"fetch:{run_ctx.run_id}",
            serializer=RequestMetaSerializer(),
        )

        # Coordination primitives
        locator_completion_flag = asyncio.Event()

        # Start the locator thread to manage queue population
        locator_task = asyncio.create_task(
            self._locator_thread(
                queue,
                locator_completion_flag,
                plan.target_queue_size,
                plan.recipe,
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
                    plan.recipe,
                    run_ctx,
                    processed_count_lock,
                    errors_lock,
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
        recipe: FetcherRecipe,
        run_ctx: FetchRunContext,
    ) -> None:
        """Dedicated thread that manages queue population by requesting BundleRefs from locators.

        This thread ensures there are at least target_queue_size items in the queue
        by requesting URLs from locators until the queue is full or all locators
        are exhausted.

        Args:
            queue: The persistent work queue to populate
            completion_flag: Event to signal when no more URLs are available
            target_queue_size: Target number of items to maintain in the queue
            recipe: The fetcher recipe containing bundle locators
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

                # Calculate how many URLs we need to reach target
                urls_needed = target_queue_size - current_queue_size

                # Try to get URLs from current locator
                if current_locator_index < len(recipe.bundle_locators):
                    provider = recipe.bundle_locators[current_locator_index]

                    locator_logger.debug(
                        "REQUESTING_URLS_FROM_LOCATOR",
                        locator_type=type(provider).__name__,
                        locator_index=current_locator_index,
                        urls_needed=urls_needed,
                        current_queue_size=current_queue_size,
                    )

                    # Request URLs from current locator
                    next_urls = await provider.get_next_urls(run_ctx)

                    locator_logger.debug(
                        "RECEIVED_URLS_FROM_LOCATOR",
                        locator_type=type(provider).__name__,
                        locator_index=current_locator_index,
                        url_count=len(next_urls),
                    )

                    # Add URLs to queue
                    if next_urls:
                        await queue.enqueue(next_urls)
                        new_size = await queue.size()
                        locator_logger.debug(
                            "URLS_ADDED_TO_QUEUE",
                            url_count=len(next_urls),
                            queue_size=new_size,
                        )

                    # If this locator didn't return any URLs, move to next locator
                    if not next_urls:
                        current_locator_index += 1
                        locator_logger.debug(
                            "LOCATOR_EXHAUSTED_MOVING_TO_NEXT",
                            current_locator_index=current_locator_index,
                            total_locators=len(recipe.bundle_locators),
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
                # Log the error with appropriate level based on error type
                if isinstance(e, ConfigurationError | FatalError):
                    locator_logger.exception(
                        "LOCATOR_THREAD_FATAL_ERROR",
                        error=str(e),
                        error_type=type(e).__name__,
                        locator_index=current_locator_index,
                    )
                else:
                    locator_logger.warning(
                        "LOCATOR_THREAD_ERROR",
                        error=str(e),
                        error_type=type(e).__name__,
                        locator_index=current_locator_index,
                    )

                # On error, move to next locator
                current_locator_index += 1
                if current_locator_index >= len(recipe.bundle_locators):
                    completion_flag.set()
                    break

        locator_logger.info("LOCATOR_THREAD_COMPLETED")

    async def _worker(
        self,
        worker_id: int,
        queue: RequestQueue,
        recipe: FetcherRecipe,
        run_ctx: FetchRunContext,
        processed_count_lock: threading.Lock,
        errors_lock: threading.Lock,
        completion_flag: asyncio.Event,
    ) -> None:
        """Worker process that handles requests from the queue.

        This worker only processes requests from the queue. Queue population
        is handled by the dedicated locator thread.

        Args:
            worker_id: Unique identifier for this worker
            queue: The persistent work queue to process requests from
            recipe: The fetcher recipe containing bundle loaders
            run_ctx: The fetch run context for this execution
            processed_count_lock: Thread lock for accessing processed count
            errors_lock: Thread lock for accessing error list
            completion_flag: Event to signal when no more work will be added
        """
        worker_logger = logger.bind(worker_id=worker_id)
        worker_logger.info("WORKER_STARTED", worker_id=worker_id)
        initial_size = await queue.size()
        worker_logger.info("WORKER_STARTED_WITH_QUEUE_SIZE", queue_size=initial_size)

        while True:
            try:
                # Get next request from persistent queue
                requests = await queue.dequeue(max_items=1)
                if not requests:
                    # If no work and locators are done, exit
                    if completion_flag.is_set():
                        worker_logger.info("NO_MORE_REQUESTS_WORKER_EXITING", worker_id=worker_id)
                        break
                    # Wait a bit for more work to arrive
                    await asyncio.sleep(0.1)
                    continue

                req = requests[0]

                # Ensure we have a RequestMeta object
                if not isinstance(req, RequestMeta):
                    worker_logger.error(
                        "Invalid request type in queue",
                        request_type=type(req).__name__,
                        worker_id=worker_id,
                    )
                    continue

                # Process the request
                with observe_around(worker_logger, "WORKER_PROCESS_URL", url=req.url, worker_id=worker_id):
                    await self._process_request(
                        req, recipe, run_ctx, processed_count_lock, errors_lock
                    )

            except Exception as e:
                if isinstance(e, ConfigurationError | FatalError):
                    worker_logger.exception(
                        "WORKER_FATAL_ERROR",
                        error_type=type(e).__name__,
                        worker_id=worker_id,
                        url=getattr(req, 'url', 'unknown'),  # Safe attribute access
                    )
                else:
                    worker_logger.exception(
                        "WORKER_ERROR",
                        error_type=type(e).__name__,
                        worker_id=worker_id,
                        url=getattr(req, 'url', 'unknown'),  # Safe attribute access
                    )

        worker_logger.debug("WORKER_COMPLETED")

    async def _process_request(
        self,
        req: RequestMeta,
        recipe: FetcherRecipe,
        run_ctx: FetchRunContext,
        processed_count_lock: threading.Lock,
        errors_lock: threading.Lock,
    ) -> None:
        """Process a single request through the pipeline."""
        try:
            logger.debug("REQUEST_PROCESSING", url=req.url)

            # 1. LOAD (Streaming Data Collection)
            if not recipe.bundle_loader:
                _raise_bundle_loader_required()

            # Get storage from app_config - must exist
            if not run_ctx.app_config:
                _raise_app_config_required()

            storage = run_ctx.app_config.storage  # type: ignore[union-attr]
            if not storage:
                _raise_storage_required()

            logger.debug(
                "REQUEST_LOADING_WITH_LOADER",
                url=req.url,
                loader_type=type(recipe.bundle_loader).__name__,
            )
            bundle_refs = await recipe.bundle_loader.load(  # type: ignore[attr-defined]
                req, storage, run_ctx, recipe
            )
            logger.debug(
                "REQUEST_LOADED_SUCCESSFULLY",
                url=req.url,
                bundle_count=len(bundle_refs),
            )

            # 2. Notify providers that URL was processed
            for provider in recipe.bundle_locators:
                if hasattr(provider, "handle_url_processed"):
                    logger.debug(
                        "PROVIDER_NOTIFICATION_URL_PROCESSED",
                        url=req.url,
                        provider_type=type(provider).__name__,
                    )
                    await provider.handle_url_processed(req, bundle_refs, run_ctx)

            logger.debug("REQUEST_PROCESSING_COMPLETED", url=req.url)
            with processed_count_lock:
                run_ctx.processed_count += 1

        except Exception as e:
            # Create appropriate error message based on error type
            if isinstance(e, NetworkError | ResourceError):
                error_msg = (
                    f"Network/Resource error processing request {req.url}: {e!s}"
                )
                logger.warning(
                    "REQUEST_PROCESSING_NETWORK_ERROR",
                    url=req.url,
                    error=str(e),
                    error_type=type(e).__name__,
                )
            elif isinstance(e, ConfigurationError | FatalError):
                error_msg = f"Fatal error processing request {req.url}: {e!s}"
                logger.exception(
                    "REQUEST_PROCESSING_FATAL_ERROR",
                    url=req.url,
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                error_msg = f"Error processing request {req.url}: {e!s}"
                logger.warning(
                    "REQUEST_PROCESSING_ERROR",
                    url=req.url,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            with errors_lock:
                run_ctx.errors.append(error_msg)


def run_fetcher(config_name: str, **kwargs: object) -> FetchResult:
    """Convenience function to run a fetcher with a predefined configuration.

    Args:
        config_name: Name of the configuration to use
        **kwargs: Additional parameters to override

    Returns:
        FetchResult with processing statistics
    """
    from .recipebook import get_fetcher, get_recipe_setup_function  # noqa: PLC0415

    fetcher = get_fetcher(config_name)

    # Get the configured recipe
    setup_func = get_recipe_setup_function(config_name)
    recipe = setup_func()

    # Note: The run_fetcher convenience function no longer handles app_config
    # since the fetcher is now stateless. App configuration should be handled
    # by the caller before creating the plan.

    # Extract known FetchPlan parameters from kwargs
    concurrency = kwargs.get("concurrency", 1)
    if not isinstance(concurrency, int):
        raise TypeError("Invalid concurrency type")  # noqa: TRY003

    target_queue_size = kwargs.get("target_queue_size", 100)
    if not isinstance(target_queue_size, int):
        raise TypeError("Invalid target_queue_size type")  # noqa: TRY003

    plan = FetchPlan(
        recipe=recipe,
        context=FetchRunContext(run_id=f"run_fetcher_{config_name}"),
        concurrency=concurrency,
        target_queue_size=target_queue_size,
    )

    result: FetchResult = asyncio.run(fetcher.run(plan))
    return result
