"""Main fetcher implementation and execution engine.

This module contains the core Fetcher class, FetchPlan, FetchResult, and related
components that orchestrate the data fetching process across different protocols.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

from .core import FetchContext, FetchPlan, FetchRunContext, RequestMeta

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    processed_count: int
    errors: list[str]
    context: FetchRunContext


class Fetcher:
    """Main fetcher class that orchestrates frontier providers, loaders, and storage."""

    def __init__(self, ctx: FetchContext):
        """Initialize the fetcher with the given context.

        Args:
            ctx: The fetch context containing bundle locators, loader, and storage.
        """
        self.ctx = ctx
        self.run_ctx = FetchRunContext()
        self._processed_count = 0
        self._errors: list[str] = []

    async def run(self, plan: FetchPlan) -> FetchResult:
        """Run the fetcher with the given plan.

        Args:
            plan: The fetch plan containing requests and context

        Returns:
            FetchResult with processing statistics
        """
        # Initialize the run context
        self.run_ctx = plan.context

        # If run_id is not set in the context, try to get it from the fetcher context
        if not self.run_ctx.run_id and hasattr(self.ctx, "fetcher_id"):
            self.run_ctx.run_id = self.ctx.fetcher_id

        logger.info(
            "Starting fetcher run",
            run_id=self.run_ctx.run_id,
            concurrency=plan.concurrency,
            initial_requests=len(plan.requests),
            bundle_locators=len(self.ctx.bundle_locators),
        )

        # Coordination primitives
        provider_lock = asyncio.Lock()
        completion_flag = asyncio.Event()
        q: asyncio.Queue[RequestMeta] = asyncio.Queue()

        # Add initial requests to queue
        for req in plan.requests:
            await q.put(req)

        # Get initial URLs from bundle locators
        async with provider_lock:
            for provider in self.ctx.bundle_locators:
                logger.debug(
                    "Getting initial URLs from provider",
                    provider_type=type(provider).__name__,
                )
                initial_urls = await provider.get_next_urls(self.run_ctx)
                logger.debug(
                    "Received initial URLs from provider",
                    provider_type=type(provider).__name__,
                    url_count=len(initial_urls),
                )
                for req in initial_urls:
                    await q.put(req)
                    logger.debug(
                        "Added URL to queue", url=req.url, queue_size=q.qsize()
                    )

        # Start workers
        workers = []
        for worker_id in range(plan.concurrency):
            worker = asyncio.create_task(
                self._worker(worker_id, q, provider_lock, completion_flag)
            )
            workers.append(worker)
            logger.debug("Started worker", worker_id=worker_id)

        # Log initial queue size
        logger.info("Initial queue size", queue_size=q.qsize())

        # Wait for all workers to complete
        await asyncio.gather(*workers)
        logger.info("All workers completed", run_id=self.run_ctx.run_id)

        return FetchResult(
            processed_count=self._processed_count,
            errors=self._errors,
            context=self.run_ctx,
        )

    async def _worker(
        self,
        worker_id: int,
        q: asyncio.Queue,
        provider_lock: asyncio.Lock,
        completion_flag: asyncio.Event,
    ) -> None:
        """Worker process that handles requests from the queue."""
        worker_logger = logger.bind(worker_id=worker_id)
        worker_logger.debug("Worker started")
        worker_logger.info("Worker started with queue size", queue_size=q.qsize())

        while not completion_flag.is_set():
            try:
                # Get next request with timeout
                req = await asyncio.wait_for(q.get(), timeout=5.0)

                # Process the request
                worker_logger.debug("Processing request", url=req.url)
                await self._process_request(req)

                # Mark task as done
                q.task_done()

            except asyncio.TimeoutError:
                worker_logger.info(
                    "Worker timeout", queue_size=q.qsize(), queue_empty=q.empty()
                )
                # Check if we should get more URLs from providers
                if q.empty() and not completion_flag.is_set():
                    async with provider_lock:
                        if q.empty() and not completion_flag.is_set():
                            new_urls_found = False
                            for provider in self.ctx.bundle_locators:
                                worker_logger.debug(
                                    "Getting next URLs from provider",
                                    provider_type=type(provider).__name__,
                                )
                                next_urls = await provider.get_next_urls(self.run_ctx)
                                worker_logger.debug(
                                    "Received next URLs from provider",
                                    provider_type=type(provider).__name__,
                                    url_count=len(next_urls),
                                )
                                for next_req in next_urls:
                                    await q.put(next_req)
                                    new_urls_found = True

                            if not new_urls_found:
                                worker_logger.debug(
                                    "No new URLs found, setting completion flag"
                                )
                                completion_flag.set()
                else:
                    # Queue is not empty, continue processing
                    continue

            except Exception as e:
                # Log error and continue
                worker_logger.error("Worker error", error=str(e), exc_info=True)

        worker_logger.debug("Worker completed")

    async def _process_request(self, req: RequestMeta) -> None:
        """Process a single request through the pipeline."""
        try:
            logger.debug("Processing request", url=req.url)

            # 1. LOAD (Streaming Data Collection)
            if self.ctx.bundle_loader:
                logger.debug(
                    "Loading request with loader",
                    url=req.url,
                    loader_type=type(self.ctx.bundle_loader).__name__,
                )
                bundle_refs = await self.ctx.bundle_loader.load(
                    req, self.ctx.storage, self.run_ctx
                )
                logger.debug(
                    "Request loaded successfully",
                    url=req.url,
                    bundle_count=len(bundle_refs),
                )
            else:
                logger.debug("No loader configured, skipping load phase", url=req.url)
                bundle_refs = []

            # 2. Notify providers that URL was processed
            for provider in self.ctx.bundle_locators:
                if hasattr(provider, "handle_url_processed"):
                    logger.debug(
                        "Notifying provider of processed URL",
                        url=req.url,
                        provider_type=type(provider).__name__,
                    )
                    await provider.handle_url_processed(req, bundle_refs, self.run_ctx)

            logger.debug("Request processing completed", url=req.url)
            self._processed_count += 1

        except Exception as e:
            error_msg = f"Error processing request {req.url}: {str(e)}"
            logger.error(
                "Error processing request", url=req.url, error=str(e), exc_info=True
            )
            self._errors.append(error_msg)


def run_fetcher(config_name: str, **kwargs: Any) -> FetchResult:
    """Convenience function to run a fetcher with a predefined configuration.

    Args:
        config_name: Name of the configuration to use
        **kwargs: Additional parameters to override

    Returns:
        FetchResult with processing statistics
    """
    from .registry import get_fetcher

    fetcher = get_fetcher(config_name)
    plan = FetchPlan(requests=[], context=fetcher.run_ctx, **kwargs)

    return asyncio.run(fetcher.run(plan))
