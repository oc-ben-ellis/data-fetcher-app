from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FileFilter(Protocol):
    def __call__(self, filename: str) -> bool:  # pragma: no cover - structural
        ...
