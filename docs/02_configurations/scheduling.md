# Scheduling

The framework provides built-in support for scheduling at the protocol level:

## SFTP Scheduling

```python
from oc_fetcher.protocols import SftpManager, ScheduledDailyGate, OncePerIntervalGate

# Create SFTP manager with scheduling
sftp_manager = SftpManager(
    credentials_provider=credentials_provider,
    daily_gate=ScheduledDailyGate(
        time_of_day="02:30",     # Run at 2:30 AM
        tz="UTC",                # Use UTC timezone
    ),
    interval_gate=OncePerIntervalGate(
        interval_seconds=24*3600,  # At least 24 hours between runs
        jitter_seconds=60,         # Add some randomness
    ),
)
```
