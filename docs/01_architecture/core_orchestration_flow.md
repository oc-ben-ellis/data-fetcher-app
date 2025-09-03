# Core Orchestration Flow

The fetcher operates in a coordinated pipeline with multiple workers processing URLs concurrently. The main `Fetcher` class orchestrates these components in a two-phase pipeline.

## Two-Phase Pipeline

### Phase 1: Initialization
The fetcher starts by setting up coordination primitives and getting initial URLs from all bundle locators.

### Phase 2: Worker Processing
Multiple workers process requests from a shared queue, with coordination mechanisms to prevent race conditions and ensure proper completion.

## Detailed Flow

### INITIALIZATION PHASE:
1. **Create coordination primitives**:
   - `bundle_locator_lock`: prevents multiple workers from calling bundle locators simultaneously
   - `completion_flag`: signals when no more work is available

2. **Get initial URLs from all bundle locators**:
   - For each bundle locator
   - Call `get_next_urls()` to get initial URLs
   - Add all URLs to the processing queue

### WORKER PROCESSING LOOP:
For each worker processing a URL request:

1. **LOAD PHASE** (Streaming Data Collection):
   - Call `bundle_loader.load()` with the request
   - Stream data to storage
   - Return bundle references

2. **NOTIFICATION PHASE**:
   - For each bundle locator
   - If bundle locator has `handle_url_processed()` method
   - Call `handle_url_processed()` with request and bundle references

3. **URL GENERATION PHASE** (only when queue is empty):
   - Check if queue is empty AND completion flag is not set
   - Acquire bundle locator lock to prevent race conditions
   - For each bundle locator:
     - Call `get_next_urls()` to get new URLs
     - Add new URLs to queue
     - Track if any new URLs were found
   - If no new URLs found, set completion flag

### COMPLETION:
- Workers continue until queue is empty AND completion flag is set
- All workers coordinate shutdown when no more work is available

## Coordination Mechanisms

### **Bundle Locator Lock**
- Prevents multiple workers from calling bundle locators simultaneously
- Ensures thread-safe URL generation
- Prevents race conditions during URL discovery

### **Completion Flag**
- Signals when no more work is available
- Workers check this flag during timeout periods
- Allows graceful shutdown when all URLs are processed

### **Request Queue**
- Thread-safe queue holding pending requests
- Workers process requests concurrently
- New URLs are added when queue is empty

## Worker Lifecycle

1. **Start**: Worker begins processing requests from queue
2. **Process**: Worker fetches data and streams to storage
3. **Notify**: Worker notifies locators of completed requests
4. **Generate**: Worker may trigger new URL generation if queue is empty
5. **Complete**: Worker shuts down when no more work is available

## Key Features

- **Concurrent Processing**: Multiple workers process requests simultaneously
- **Queue-Based URL Generation**: New URLs are generated only when the queue is empty
- **Thread-Safe Coordination**: Proper locking prevents race conditions
- **Completion Coordination**: Workers coordinate shutdown when no more URLs are available
- **URL Processing Callbacks**: Bundle locators are notified when URLs are successfully processed
- **Protocol-Level Rate Limiting**: Rate limiting is handled at the protocol level for better performance
- **Scheduling Support**: Built-in support for daily and interval-based scheduling
