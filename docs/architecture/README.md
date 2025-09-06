# Architecture Documentation

This directory contains comprehensive documentation about the OC Fetcher architecture and design.

## Recommended Reading Order

1. **[Overview](overview/README.md)** - Start here for a high-level introduction to the architecture
2. **[Run ID](run_id/README.md)** - Understand the Run ID system for execution identification and tracing
3. **[Bundle ID (BID)](bid/README.md)** - Understand the BID system for bundle identification and tracing
4. **[Orchestration](orchestration/README.md)** - Learn how the fetcher.py works and uses recipes to configure behavior
5. **[ProtocolConfig](protocol_config/README.md)** - Understand the ProtocolConfig architecture for connection management
6. **[Recipes](recipes/README.md)** - Understand how recipes are structured and built
7. **[Locators](locators/README.md)** - Explore what locators are and their purpose
8. **[Loaders](loaders/README.md)** - Learn about loaders and their structure
9. **[Storage](storage/README.md)** - Understand the storage architecture
10. **[Notifications](notifications/README.md)** - Learn about SQS notifications and bundle completion events
11. **[State Management](state_management/README.md)** - Learn about state management via the KV store
12. **[Retry Engine](retry_engine/README.md)** - Understand retry logic and error handling

## Architecture Overview

The OC Fetcher framework is built around a composable, streaming-first architecture that coordinates three main components: **Bundle Locators**, **Bundle Loaders**, and **Storage**. The main `Fetcher` class orchestrates these components in a two-phase pipeline, with **Protocol Managers** handling cross-cutting concerns like rate limiting and scheduling. The framework uses **ProtocolConfig** objects to define protocol-specific settings, enabling multiple connection pools per manager.

### Core Architecture Principles

1. **Composable Design** - Components can be mixed and matched to create different fetching configurations
2. **Streaming-First** - Data flows through the system without loading entire files into memory
3. **Protocol Independence** - Managers handle protocol-specific concerns while loaders focus on data fetching
4. **Configuration-Driven** - ProtocolConfig objects define connection settings, enabling multiple pools per manager
5. **Extensibility** - New locators, loaders, and storage backends can be easily added

## Quick Navigation

- **[Architecture Overview](overview/README.md)** - High-level system overview and principles
- **[Run ID](run_id/README.md)** - Execution identification and tracing system
- **[Bundle ID (BID)](bid/README.md)** - Bundle identification and tracing system
- **[Orchestration](orchestration/README.md)** - How the fetcher coordinates components
- **[ProtocolConfig](protocol_config/README.md)** - Protocol configuration and connection management
- **[Recipes](recipes/README.md)** - Configuration and recipe system
- **[Locators](locators/README.md)** - URL generation and discovery
- **[Loaders](loaders/README.md)** - Data fetching and streaming
- **[Storage](storage/README.md)** - Data persistence and transformation
- **[Notifications](notifications/README.md)** - SQS notifications and bundle completion events
- **[State Management](state_management/README.md)** - State management and caching
- **[Retry Engine](retry_engine/README.md)** - Retry logic and error handling

## Interactive Diagrams

The architecture documentation includes interactive Mermaid diagrams that are rendered dynamically and will automatically update when the source code changes.

## Key Features

- **Concurrent Processing**: Multiple workers process requests simultaneously
- **Queue-Based URL Generation**: New URLs are generated only when the queue is empty
- **Thread-Safe Coordination**: Proper locking prevents race conditions
- **Completion Coordination**: Workers coordinate shutdown when no more URLs are available
- **URL Processing Callbacks**: Bundle locators are notified when URLs are successfully processed
- **Protocol-Level Rate Limiting**: Rate limiting is handled at the protocol level for better performance
- **Scheduling Support**: Built-in support for daily and interval-based scheduling
