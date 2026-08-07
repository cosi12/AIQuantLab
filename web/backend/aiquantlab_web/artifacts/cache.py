"""按目录指纹失效的进程内缓存。

artifact 变化后指纹随之变化，缓存自动失效。不使用磁盘或跨进程缓存。
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


class FingerprintCache(Generic[T]):
    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, T]] = {}
        self._lock = Lock()

    def resolve(self, key: str, fingerprint: str, factory: Callable[[], T]) -> T:
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None and cached[0] == fingerprint:
                return cached[1]
        value = factory()
        with self._lock:
            self._entries[key] = (fingerprint, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
