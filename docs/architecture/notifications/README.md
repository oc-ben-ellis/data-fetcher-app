# Notifications

The notification system provides SQS integration for bundle completion events, enabling downstream systems to be notified when data fetching operations complete.

## What are Notifications?

The notification system:
- **Sends SQS Messages**: Publishes bundle completion events to Amazon SQS
- **Enables Integration**: Allows downstream systems to react to bundle completion
- **Provides Eventual Consistency**: Handles pending completions through KV store tracking
- **Supports LocalStack**: Works with LocalStack for local development and testing

## SQS Publisher

The `SqsPublisher` class handles sending bundle completion notifications to Amazon SQS.

### **Configuration**

```python
from data_fetcher_core.notifications import SqsPublisher

# Basic SQS configuration
sqs_publisher = SqsPublisher(
    queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/bundle-completions",
    region="eu-west-2"
)

# LocalStack configuration for testing
sqs_publisher = SqsPublisher(
    queue_url="http://localhost:4566/000000000000/bundle-completions",
    region="eu-west-2",
    endpoint_url="http://localhost:4566"
)
```

### **Environment Variables**

The SQS publisher can be configured through environment variables:

```bash
# AWS Region
export AWS_REGION=eu-west-2

# For LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

### **Message Format**

SQS messages contain comprehensive bundle completion information:

```json
{
    "bundle_id": "17572488-4023-67e2-0f15-c21600a05797",
    "recipe_id": "fr",
    "primary_url": "https://api.insee.fr/entreprises/sirene/V3.11/siren",
    "resources_count": 1,
    "storage_key": "data/bundles/17572488-4023-67e2-0f15-c21600a05797/resources",
    "completion_timestamp": "2024-01-15T10:30:00Z",
    "metadata": {
        "source": "http_api",
        "run_id": "run_123",
        "resources_count": 1
    }
}
```

### **Message Attributes**

SQS messages include attributes for efficient filtering and routing:

```python
MessageAttributes={
    "bundle_id": {
        "StringValue": "17572488-4023-67e2-0f15-c21600a05797",
        "DataType": "String"
    },
    "recipe_id": {
        "StringValue": "fr",
        "DataType": "String"
    },
    "completion_timestamp": {
        "StringValue": "2024-01-15T10:30:00Z",
        "DataType": "String"
    }
}
```

## Integration with Storage

The notification system integrates seamlessly with storage components:

### **PipelineStorage Integration (Mandatory)**

PipelineStorage **requires** SQS notifications for bundle completion tracking:

```python
from data_fetcher_core.storage import PipelineStorage
from data_fetcher_core.notifications import SqsPublisher

# SQS publisher is mandatory for PipelineStorage
sqs_publisher = SqsPublisher(
    queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/bundle-completions"
)

# Create storage with mandatory SQS notifications
storage = PipelineStorage(
    bucket_name="my-data-bucket",
    sqs_publisher=sqs_publisher,  # Required parameter
    prefix="captures/2024/"
)
```

**Environment Variable Configuration:**
```bash
# Required for PipelineStorage
export OC_SQS_QUEUE_URL=https://sqs.eu-west-2.amazonaws.com/123456789012/bundle-completions
```

### **Automatic Notification**

When bundles are completed, notifications are automatically sent:

```python
# Bundle completion automatically triggers SQS notification
bundle_context = await storage.start_bundle(bundle_ref, recipe)
await bundle_context.add_resource(url, content_type, status_code, stream)
await bundle_context.complete(metadata)  # Triggers SQS notification
```

## Completion Callbacks

The notification system works in conjunction with completion callbacks:

### **Callback Execution Order**

1. **Bundle Finalization**: Storage component finalizes the bundle
2. **Callback Execution**: Storage executes completion callbacks from recipe components
3. **SQS Notification**: Bundle completion is published to SQS
4. **State Updates**: Bundle locators are notified via `handle_url_processed()`

### **Idempotent Callbacks**

Completion callbacks are designed to be idempotent, allowing safe re-execution:

```python
class MyLoader:
    async def on_bundle_complete_hook(self, bundle_ref: BundleRef) -> None:
        """Called when a bundle is completed."""
        # This method can be safely called multiple times
        # Update tracking, send notifications, etc.
        pass
```

## Pending Completion Processing

The system handles eventual consistency through pending completion processing:

### **Startup Recovery**

Storage components can process pending completions on startup:

```python
class PipelineStorage:
    async def on_run_start(self, context: FetchRunContext, recipe: FetcherRecipe) -> None:
        """Process any pending SQS notifications from previous runs."""
        await self._process_pending_completions(context, recipe)
```

### **KV Store Tracking**

Pending completions are tracked in the KV store:

```python
# Pending completion key format
key = f"sqs_notifications:pending:{recipe_id}:{bundle_id}"

# Pending completion data
data = {
    "bundle_ref": bundle_ref.to_dict(),
    "metadata": metadata,
    "timestamp": datetime.now(UTC).isoformat()
}
```

### **Recovery Process**

1. **Scan for Pending**: Find all pending completion keys for the recipe
2. **Re-execute Callbacks**: Execute completion callbacks for pending bundles
3. **Re-send Notifications**: Send SQS notifications for pending bundles
4. **Cleanup**: Remove pending completion keys from KV store

## Error Handling

The notification system includes comprehensive error handling:

### **SQS Errors**

```python
try:
    await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)
except Exception as e:
    logger.exception(
        "Failed to send bundle completion notification to SQS",
        bundle_id=str(bundle_ref.bid),
        recipe_id=recipe_id,
        error=str(e)
    )
    # Notification failure doesn't prevent bundle completion
```

### **Callback Errors**

```python
try:
    await locator.on_bundle_complete_hook(bundle_ref)
except Exception as e:
    logger.exception(
        "Error executing locator completion callback",
        error=str(e),
        bundle_id=str(bundle_ref.bid),
        recipe_id=recipe_id
    )
    # Callback failure doesn't prevent bundle completion
```

## Local Development

The notification system supports LocalStack for local development:

### **LocalStack Setup**

```bash
# Start LocalStack
docker run -d -p 4566:4566 localstack/localstack

# Create SQS queue
aws --endpoint-url=http://localhost:4566 sqs create-queue \
    --queue-name bundle-completions
```

### **LocalStack Configuration**

```python
sqs_publisher = SqsPublisher(
    queue_url="http://localhost:4566/000000000000/bundle-completions",
    region="eu-west-2",
    endpoint_url="http://localhost:4566"
)
```

## Best Practices

### **Performance**
- Use appropriate SQS message attributes for filtering
- Implement efficient callback execution
- Handle notification failures gracefully

### **Reliability**
- Design callbacks to be idempotent
- Implement proper error handling
- Use KV store for pending completion tracking

### **Security**
- Validate SQS message content
- Handle sensitive metadata appropriately
- Implement proper access controls

### **Testing**
- Test with LocalStack for local development
- Validate message format and attributes
- Test error conditions and recovery

## Examples

### **Basic SQS Integration**

```python
from data_fetcher_core.storage import PipelineStorage
from data_fetcher_core.notifications import SqsPublisher

# Configure SQS publisher
sqs_publisher = SqsPublisher(
    queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/bundle-completions",
    region="eu-west-2"
)

# Configure storage with SQS notifications
storage = PipelineStorage(
    bucket_name="my-data-bucket",
    sqs_publisher=sqs_publisher
)

# Use in recipe
recipe = create_fetcher_config()
recipe.storage = storage
```

### **Custom Completion Callback**

```python
class TrackingLoader:
    async def on_bundle_complete_hook(self, bundle_ref: BundleRef) -> None:
        """Track bundle completion for analytics."""
        # Update tracking database
        await self.tracking_db.update_completion(bundle_ref.bid)

        # Send custom notification
        await self.custom_notifier.notify(bundle_ref)
```

### **Pending Completion Recovery**

```python
class CustomStorage(PipelineStorage):
    async def on_run_start(self, context: FetchRunContext, recipe: FetcherRecipe) -> None:
        """Process pending completions with custom logic."""
        pending_keys = await context.app_config.kv_store.scan(
            f"sqs_notifications:pending:{recipe.recipe_id}:*"
        )

        for key in pending_keys:
            # Custom recovery logic
            await self._recover_pending_completion(key, recipe)
```

## Next Steps

- **[Storage](../storage/README.md)** - Learn about storage integration
- **[Orchestration](../orchestration/README.md)** - Understand how notifications fit into the overall system
- **[State Management](../state_management/README.md)** - Learn about KV store integration
