from dataclasses import dataclass

from data_fetcher_core.credentials import CredentialProvider
from data_fetcher_core.kv_store import KeyValueStore
from data_fetcher_core.storage import Storage


@dataclass
class FetcherConfig:
    """Fetcher configuration container."""

    credential_provider: CredentialProvider
    kv_store: KeyValueStore
    storage: Storage
