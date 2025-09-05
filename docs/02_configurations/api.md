# API Configurations

The OC Fetcher framework provides comprehensive support for API-based fetching with authentication, pagination handling, and rate limiting. API configurations are designed to work with REST APIs, GraphQL endpoints, and other HTTP-based data sources.

## API Configuration Features

### **Authentication Support**
- **Bearer Token**: Simple token-based authentication
- **Basic Authentication**: Username/password authentication
- **OAuth**: OAuth 2.0 authentication flows
- **API Keys**: Header-based API key authentication

### **Pagination Handling**
- **Cursor-based**: Support for cursor-based pagination
- **Offset-based**: Support for offset/limit pagination
- **Page-based**: Support for page number pagination
- **Custom**: Custom pagination strategies

### **Rate Limiting**
- **Request Rate Limiting**: Configurable requests per second/minute
- **Burst Handling**: Graceful handling of rate limit bursts
- **Retry Logic**: Automatic retry with exponential backoff
- **Circuit Breaker**: Protection against failing endpoints

## Available API Configurations

### **Generic API Configuration**
```python
from data_fetcher_core.configurations import ApiConfiguration

class GenericApiConfig(ApiConfiguration):
    def __init__(self):
        super().__init__()
        self.name = "generic-api"
        self.description = "Generic API fetching configuration"

    def build(self):
        return self.builder \
            .use_http_manager() \
            .use_api_loader() \
            .use_api_pagination_locator() \
            .build()
```

### **Custom API Configuration**
```python
from data_fetcher_core.configurations import ApiConfiguration

class CustomApiConfig(ApiConfiguration):
    def __init__(self, base_url: str, auth_token: str):
        super().__init__()
        self.base_url = base_url
        self.auth_token = auth_token

    def build(self):
        return self.builder \
            .use_http_manager(
                rate_limit=10,  # 10 requests per second
                timeout=30
            ) \
            .use_api_loader(
                base_url=self.base_url,
                auth_token=self.auth_token
            ) \
            .use_api_pagination_locator(
                pagination_strategy="cursor"
            ) \
            .build()
```

## API Components

### **ApiLoader**
The `ApiLoader` component handles API requests with authentication and response processing:

```python
from data_fetcher_core.bundle_loaders import ApiLoader
from data_fetcher_core.protocols import HttpManager

# Create API loader with authentication
http_manager = HttpManager(
    rate_limit=10,
    timeout=30
)

api_loader = ApiLoader(
    http_manager=http_manager,
    base_url="https://api.example.com",
    auth_token="your-api-token"
)
```

### **ApiPaginationBundleLocator**
The `ApiPaginationBundleLocator` handles URL generation for paginated APIs:

```python
from data_fetcher_core.bundle_locators import ApiPaginationBundleLocator

# Create pagination locator
locator = ApiPaginationBundleLocator(
    base_url="https://api.example.com/endpoint",
    pagination_strategy="cursor",
    page_size=100
)
```

## Authentication Mechanisms

### **Bearer Token Authentication**
```python
from data_fetcher_core.protocols import BearerTokenAuthenticationMechanism

auth = BearerTokenAuthenticationMechanism("your-api-token")
http_manager = HttpManager(auth_mechanism=auth)
```

### **Basic Authentication**
```python
from data_fetcher_core.protocols import BasicAuthenticationMechanism

auth = BasicAuthenticationMechanism("username", "password")
http_manager = HttpManager(auth_mechanism=auth)
```

### **OAuth Authentication**
```python
from data_fetcher_core.protocols import OAuthAuthenticationMechanism

auth = OAuthAuthenticationMechanism(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.example.com/token"
)
http_manager = HttpManager(auth_mechanism=auth)
```

## Pagination Strategies

### **Cursor-based Pagination**
```python
from data_fetcher_core.bundle_locators import CursorPaginationStrategy

strategy = CursorPaginationStrategy(
    cursor_param="next_cursor",
    response_cursor_path="data.next_cursor"
)
```

### **Offset-based Pagination**
```python
from data_fetcher_core.bundle_locators import OffsetPaginationStrategy

strategy = OffsetPaginationStrategy(
    offset_param="offset",
    limit_param="limit",
    page_size=100
)
```

### **Page-based Pagination**
```python
from data_fetcher_core.bundle_locators import PagePaginationStrategy

strategy = PagePaginationStrategy(
    page_param="page",
    page_size_param="size",
    page_size=100
)
```

## Usage Examples

### **Simple API Fetch**
```python
from data_fetcher import run_fetcher

# Run API configuration
result = await run_fetcher(
    "generic-api",
    base_url="https://api.example.com",
    auth_token="your-token"
)
```

### **Custom API Configuration**
```python
from data_fetcher_core.configurations import CustomApiConfig

# Create custom configuration
config = CustomApiConfig(
    base_url="https://api.example.com",
    auth_token="your-token"
)

# Run configuration
result = await config.run()
```

### **Programmatic API Usage**
```python
from data_fetcher_core.core import FetchContext, FetchPlan
from data_fetcher_core.bundle_loaders import ApiLoader
from data_fetcher_core.bundle_locators import ApiPaginationBundleLocator

# Create components
loader = ApiLoader(http_manager, "https://api.example.com", "token")
locator = ApiPaginationBundleLocator("https://api.example.com/endpoint")

# Create context
context = FetchContext(
    bundle_loader=loader,
    bundle_locators=[locator]
)

# Create plan
plan = FetchPlan(requests=[], context=context, concurrency=2)

# Run fetcher
fetcher = Fetcher(context)
result = await fetcher.run(plan)
```

## Key Features

- **Flexible Authentication**: Support for multiple authentication mechanisms
- **Pagination Handling**: Built-in support for common pagination strategies
- **Rate Limiting**: Configurable rate limiting and retry logic
- **Error Handling**: Robust error handling with retry mechanisms
- **Response Processing**: Automatic response parsing and metadata extraction
- **Extensible**: Easy to create custom API configurations
- **Monitoring**: Built-in logging and monitoring capabilities
